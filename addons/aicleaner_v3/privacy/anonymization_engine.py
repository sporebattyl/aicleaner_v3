"""
Anonymization Engine for Privacy Pipeline
Applies redaction effects to detected privacy-sensitive regions
"""

import logging
import time
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .privacy_config import PrivacyConfig, RedactionMode
from .dag_processor import ProcessingContext, DetectionResult


@dataclass
class AnonymizationResult:
    """Result from anonymization process"""
    anonymized_image: np.ndarray
    regions_processed: int
    processing_time: float
    redaction_stats: Dict[str, int]
    metadata: Dict[str, Any]


class AnonymizationEngine:
    """
    Engine for applying anonymization effects to detected privacy regions
    
    Features:
    - Multiple redaction modes (blur, pixelate, black box)
    - Region expansion for better coverage
    - Optimized processing for AMD 780M
    - Batch processing of similar regions
    """
    
    def __init__(self, config: PrivacyConfig):
        """
        Initialize anonymization engine
        
        Args:
            config: Privacy pipeline configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Redaction mode mappings
        self.redaction_functions = {
            RedactionMode.BLUR: self._apply_blur,
            RedactionMode.PIXELATE: self._apply_pixelate,
            RedactionMode.BLACK_BOX: self._apply_black_box
        }
        
        self.logger.info("Anonymization Engine initialized")
    
    async def anonymize_image(self, context: ProcessingContext) -> AnonymizationResult:
        """
        Apply anonymization to all detected privacy regions
        
        Args:
            context: Processing context with detection results
            
        Returns:
            AnonymizationResult with anonymized image
        """
        start_time = time.time()
        
        try:
            # Start with original image
            anonymized_image = context.original_image.copy()
            
            # Collect all regions to anonymize
            all_regions = self._collect_regions(context)
            
            if not all_regions:
                self.logger.info("No privacy regions detected - returning original image")
                return AnonymizationResult(
                    anonymized_image=anonymized_image,
                    regions_processed=0,
                    processing_time=time.time() - start_time,
                    redaction_stats={},
                    metadata={"status": "no_regions"}
                )
            
            # Merge overlapping regions
            merged_regions = self._merge_overlapping_regions(all_regions)
            self.logger.info(f"Merged {len(all_regions)} regions into {len(merged_regions)} non-overlapping regions")
            
            # Apply anonymization by type
            redaction_stats = {}
            for region_type, regions in merged_regions.items():
                if regions:
                    redaction_mode = self._get_redaction_mode(region_type)
                    anonymized_image = await self._apply_redaction_batch(
                        anonymized_image, regions, redaction_mode
                    )
                    redaction_stats[region_type] = len(regions)
            
            processing_time = time.time() - start_time
            total_regions = sum(redaction_stats.values())
            
            self.logger.info(f"Anonymized {total_regions} regions in {processing_time:.3f}s")
            
            return AnonymizationResult(
                anonymized_image=anonymized_image,
                regions_processed=total_regions,
                processing_time=processing_time,
                redaction_stats=redaction_stats,
                metadata={
                    "redaction_modes": {k: self._get_redaction_mode(k).value for k in redaction_stats.keys()},
                    "expansion_factor": self.config.redaction.expansion_factor,
                    "original_regions": len(all_regions),
                    "merged_regions": sum(len(regions) for regions in merged_regions.values())
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Anonymization failed after {processing_time:.3f}s: {e}")
            
            return AnonymizationResult(
                anonymized_image=context.original_image,
                regions_processed=0,
                processing_time=processing_time,
                redaction_stats={},
                metadata={"error": str(e)}
            )
    
    def _collect_regions(self, context: ProcessingContext) -> List[Dict[str, Any]]:
        """
        Collect all detected regions from different detection nodes
        
        Args:
            context: Processing context with detection results
            
        Returns:
            List of region dictionaries with type and bounding box info
        """
        all_regions = []
        
        # Process each detection result
        for node_type, detection_result in context.detection_results.items():
            if not detection_result or not detection_result.bounding_boxes:
                continue
            
            # Map node types to region types for redaction mode selection
            region_type = self._map_node_to_region_type(node_type)
            
            for i, bbox in enumerate(detection_result.bounding_boxes):
                confidence = detection_result.confidences[i] if i < len(detection_result.confidences) else 1.0
                label = detection_result.labels[i] if i < len(detection_result.labels) else "unknown"
                
                # Expand bounding box
                expanded_bbox = self._expand_bounding_box(
                    bbox, 
                    context.original_image.shape,
                    self.config.redaction.expansion_factor
                )
                
                all_regions.append({
                    'bbox': expanded_bbox,
                    'original_bbox': bbox,
                    'region_type': region_type,
                    'node_type': node_type,
                    'label': label,
                    'confidence': confidence
                })
        
        return all_regions
    
    def _map_node_to_region_type(self, node_type: str) -> str:
        """Map detection node type to region type for redaction mode selection"""
        mapping = {
            'face_detection': 'face',
            'object_detection': 'object',
            'text_detection': 'text',
            'pii_analysis': 'pii'
        }
        return mapping.get(node_type, 'general')
    
    def _expand_bounding_box(self, bbox: Tuple[int, int, int, int], 
                           image_shape: Tuple[int, int, int], 
                           expansion_factor: float) -> Tuple[int, int, int, int]:
        """
        Expand bounding box by given factor while staying within image bounds
        
        Args:
            bbox: Original bounding box (x1, y1, x2, y2)
            image_shape: Image shape (height, width, channels)
            expansion_factor: Factor to expand box by
            
        Returns:
            Expanded bounding box
        """
        x1, y1, x2, y2 = bbox
        height, width = image_shape[:2]
        
        # Calculate expansion
        w = x2 - x1
        h = y2 - y1
        
        expand_w = int(w * (expansion_factor - 1) / 2)
        expand_h = int(h * (expansion_factor - 1) / 2)
        
        # Apply expansion with bounds checking
        new_x1 = max(0, x1 - expand_w)
        new_y1 = max(0, y1 - expand_h)
        new_x2 = min(width, x2 + expand_w)
        new_y2 = min(height, y2 + expand_h)
        
        return (new_x1, new_y1, new_x2, new_y2)
    
    def _merge_overlapping_regions(self, regions: List[Dict[str, Any]]) -> Dict[str, List[Tuple]]:
        """
        Merge overlapping regions by type to avoid double redaction
        
        Args:
            regions: List of region dictionaries
            
        Returns:
            Dictionary mapping region types to lists of merged bounding boxes
        """
        # Group regions by type
        regions_by_type = {}
        for region in regions:
            region_type = region['region_type']
            if region_type not in regions_by_type:
                regions_by_type[region_type] = []
            regions_by_type[region_type].append(region['bbox'])
        
        # Merge overlapping regions within each type
        merged_by_type = {}
        for region_type, bboxes in regions_by_type.items():
            merged_by_type[region_type] = self._merge_overlapping_boxes(bboxes)
        
        return merged_by_type
    
    def _merge_overlapping_boxes(self, boxes: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
        """
        Merge overlapping bounding boxes
        
        Args:
            boxes: List of bounding boxes (x1, y1, x2, y2)
            
        Returns:
            List of merged bounding boxes
        """
        if not boxes:
            return []
        
        # Sort boxes by x1 coordinate
        sorted_boxes = sorted(boxes)
        merged = [sorted_boxes[0]]
        
        for current in sorted_boxes[1:]:
            last_merged = merged[-1]
            
            # Check for overlap
            if self._boxes_overlap(last_merged, current):
                # Merge boxes
                merged[-1] = (
                    min(last_merged[0], current[0]),
                    min(last_merged[1], current[1]),
                    max(last_merged[2], current[2]),
                    max(last_merged[3], current[3])
                )
            else:
                merged.append(current)
        
        return merged
    
    def _boxes_overlap(self, box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int]) -> bool:
        """Check if two bounding boxes overlap"""
        x1a, y1a, x2a, y2a = box1
        x1b, y1b, x2b, y2b = box2
        
        return not (x2a < x1b or x2b < x1a or y2a < y1b or y2b < y1a)
    
    def _get_redaction_mode(self, region_type: str) -> RedactionMode:
        """
        Get redaction mode for region type
        
        Args:
            region_type: Type of region (face, object, text, pii)
            
        Returns:
            RedactionMode to use
        """
        mode_mapping = {
            'face': self.config.redaction.face_mode,
            'object': RedactionMode.BLACK_BOX,  # Default for objects
            'text': self.config.redaction.pii_text_mode,
            'pii': self.config.redaction.pii_text_mode,
            'general': RedactionMode.BLUR  # Default fallback
        }
        
        return mode_mapping.get(region_type, RedactionMode.BLUR)
    
    async def _apply_redaction_batch(self, image: np.ndarray, 
                                   regions: List[Tuple[int, int, int, int]], 
                                   redaction_mode: RedactionMode) -> np.ndarray:
        """
        Apply redaction to multiple regions in batch
        
        Args:
            image: Image to modify
            regions: List of bounding boxes to redact
            redaction_mode: Redaction mode to apply
            
        Returns:
            Modified image
        """
        if not regions:
            return image
        
        redaction_func = self.redaction_functions.get(redaction_mode, self._apply_blur)
        
        # Apply redaction to each region
        for bbox in regions:
            image = redaction_func(image, bbox)
        
        return image
    
    def _apply_blur(self, image: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Apply Gaussian blur to region
        
        Args:
            image: Image to modify
            bbox: Bounding box (x1, y1, x2, y2)
            
        Returns:
            Modified image
        """
        x1, y1, x2, y2 = bbox
        
        if x2 <= x1 or y2 <= y1:
            return image
        
        # Extract region
        region = image[y1:y2, x1:x2].copy()
        
        if region.size > 0:
            # Apply Gaussian blur
            kernel_size = self.config.redaction.blur_kernel_size
            blurred = cv2.GaussianBlur(region, (kernel_size, kernel_size), 0)
            
            # Replace region in image
            image[y1:y2, x1:x2] = blurred
        
        return image
    
    def _apply_pixelate(self, image: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Apply pixelation effect to region
        
        Args:
            image: Image to modify
            bbox: Bounding box (x1, y1, x2, y2)
            
        Returns:
            Modified image
        """
        x1, y1, x2, y2 = bbox
        
        if x2 <= x1 or y2 <= y1:
            return image
        
        # Extract region
        region = image[y1:y2, x1:x2].copy()
        
        if region.size > 0:
            # Calculate downscale factor
            block_size = self.config.redaction.pixelate_block_size
            h, w = region.shape[:2]
            
            new_h = max(1, h // block_size)
            new_w = max(1, w // block_size)
            
            # Downscale and upscale to create pixelation effect
            small = cv2.resize(region, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            pixelated = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
            
            # Replace region in image
            image[y1:y2, x1:x2] = pixelated
        
        return image
    
    def _apply_black_box(self, image: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Apply solid black rectangle to region
        
        Args:
            image: Image to modify
            bbox: Bounding box (x1, y1, x2, y2)
            
        Returns:
            Modified image
        """
        x1, y1, x2, y2 = bbox
        
        if x2 <= x1 or y2 <= y1:
            return image
        
        # Fill region with black
        image[y1:y2, x1:x2] = 0
        
        return image
    
    def get_redaction_preview(self, image: np.ndarray, regions: List[Dict[str, Any]]) -> np.ndarray:
        """
        Generate preview image showing what will be redacted
        
        Args:
            image: Original image
            regions: Regions that will be redacted
            
        Returns:
            Preview image with redaction regions highlighted
        """
        preview = image.copy()
        
        # Draw rectangles around regions that will be redacted
        colors = {
            'face': (0, 255, 0),      # Green for faces
            'object': (255, 0, 0),    # Blue for objects
            'text': (0, 255, 255),    # Yellow for text
            'pii': (0, 0, 255),       # Red for PII
            'general': (128, 128, 128) # Gray for general
        }
        
        for region in regions:
            bbox = region['bbox']
            region_type = region['region_type']
            color = colors.get(region_type, colors['general'])
            
            x1, y1, x2, y2 = bbox
            cv2.rectangle(preview, (x1, y1), (x2, y2), color, 2)
            
            # Add label
            label = f"{region_type}: {region['label']}"
            cv2.putText(preview, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        return preview
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for anonymization
        
        Returns:
            Dictionary with performance metrics
        """
        return {
            "redaction_modes_available": [mode.value for mode in RedactionMode],
            "current_config": {
                "face_mode": self.config.redaction.face_mode.value,
                "license_plate_mode": self.config.redaction.license_plate_mode.value,
                "pii_text_mode": self.config.redaction.pii_text_mode.value,
                "blur_kernel_size": self.config.redaction.blur_kernel_size,
                "pixelate_block_size": self.config.redaction.pixelate_block_size,
                "expansion_factor": self.config.redaction.expansion_factor
            }
        }