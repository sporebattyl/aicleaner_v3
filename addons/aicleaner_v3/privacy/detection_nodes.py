"""
Detection Nodes for Privacy Pipeline
Implements specific detection nodes for faces, objects, text, and PII
"""

import asyncio
import logging
import time
import cv2
import numpy as np
import re
from typing import Dict, List, Optional, Any, Tuple
import onnxruntime as ort

from .dag_processor import ProcessingNode, DetectionResult, ProcessingContext
from .privacy_config import PrivacyConfig, PrivacyLevel
from .model_manager import ModelManager


class FaceDetectionNode(ProcessingNode):
    """
    Face detection node using ONNX models optimized for AMD 780M
    
    Supports:
    - YuNet (Speed)
    - RetinaFace (Balanced) 
    - SCRFD (Paranoid)
    """
    
    def __init__(self, config: PrivacyConfig, model_manager: ModelManager):
        super().__init__("face_detection", config)
        self.model_manager = model_manager
        
    def is_enabled_for_level(self, privacy_level: PrivacyLevel) -> bool:
        """Face detection enabled for all privacy levels"""
        return True
    
    async def process(self, context: ProcessingContext) -> Optional[DetectionResult]:
        """
        Detect faces in the image
        
        Args:
            context: Processing context with image data
            
        Returns:
            DetectionResult with face bounding boxes
        """
        start_time = time.time()
        
        try:
            # Get face detection model for current privacy level
            model_session = await self.model_manager.get_model("face_detection", context.privacy_level)
            if not model_session:
                self.logger.error("Face detection model not available")
                return None
            
            # Prepare input image
            input_image, scale_x, scale_y = self._prepare_input(
                context.original_image, 
                model_session.input_shape
            )
            
            # Run inference
            faces, confidences = await self._run_inference(model_session, input_image)
            
            # Scale boxes back to original image coordinates
            scaled_faces = self._scale_boxes(faces, scale_x, scale_y)
            
            # Filter faces by confidence threshold
            min_confidence = self.config.face_detection.models.get(
                "default", 
                type('obj', (object,), {"confidence_threshold": 0.7})()
            ).confidence_threshold
            
            filtered_faces = []
            filtered_confidences = []
            for face, conf in zip(scaled_faces, confidences):
                if conf >= min_confidence:
                    filtered_faces.append(face)
                    filtered_confidences.append(conf)
            
            processing_time = time.time() - start_time
            
            self.logger.info(f"Detected {len(filtered_faces)} faces in {processing_time:.3f}s")
            
            return DetectionResult(
                node_type="face_detection",
                bounding_boxes=filtered_faces,
                confidences=filtered_confidences,
                labels=["face"] * len(filtered_faces),
                processing_time=processing_time,
                metadata={
                    "model_used": model_session.model_path,
                    "input_shape": model_session.input_shape,
                    "total_detections": len(faces),
                    "filtered_detections": len(filtered_faces),
                    "confidence_threshold": min_confidence
                }
            )
            
        except Exception as e:
            self.logger.error(f"Face detection failed: {e}")
            return None
    
    def _prepare_input(self, image: np.ndarray, target_shape: tuple) -> Tuple[np.ndarray, float, float]:
        """
        Prepare input image for model inference
        
        Args:
            image: Original image
            target_shape: Model input shape (batch, channels, height, width)
            
        Returns:
            Tuple of (prepared_image, scale_x, scale_y)
        """
        h, w = image.shape[:2]
        target_h, target_w = target_shape[-2:]
        
        # Calculate scaling factors
        scale_x = w / target_w
        scale_y = h / target_h
        
        # Resize image
        resized = cv2.resize(image, (target_w, target_h))
        
        # Convert to RGB and normalize
        if len(resized.shape) == 3:
            resized = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        # Prepare for ONNX (NCHW format)
        input_image = resized.transpose(2, 0, 1).astype(np.float32)
        input_image = input_image / 255.0
        input_image = np.expand_dims(input_image, axis=0)
        
        return input_image, scale_x, scale_y
    
    async def _run_inference(self, model_session, input_image) -> Tuple[List, List]:
        """
        Run face detection inference
        
        Args:
            model_session: ONNX model session
            input_image: Prepared input image
            
        Returns:
            Tuple of (bounding_boxes, confidences)
        """
        # Get input/output names
        input_name = model_session.session.get_inputs()[0].name
        output_names = [output.name for output in model_session.session.get_outputs()]
        
        # Run inference
        outputs = model_session.session.run(output_names, {input_name: input_image})
        
        # Parse outputs based on model type
        return self._parse_face_outputs(outputs)
    
    def _parse_face_outputs(self, outputs) -> Tuple[List, List]:
        """
        Parse face detection model outputs
        
        Args:
            outputs: Raw model outputs
            
        Returns:
            Tuple of (bounding_boxes, confidences)
        """
        # Generic parsing - adjust based on specific model format
        if len(outputs) >= 2:
            # Format: [boxes, scores] or [boxes, scores, landmarks]
            boxes = outputs[0]
            scores = outputs[1]
            
            faces = []
            confidences = []
            
            for i in range(boxes.shape[0]):
                if len(boxes.shape) == 3:  # Batch dimension
                    box = boxes[0, i]
                    score = scores[0, i] if len(scores.shape) == 2 else scores[i]
                else:
                    box = boxes[i]
                    score = scores[i]
                
                if score > 0.1:  # Minimum threshold for parsing
                    # Convert to (x1, y1, x2, y2) format
                    x1, y1, x2, y2 = box[:4]
                    faces.append((int(x1), int(y1), int(x2), int(y2)))
                    confidences.append(float(score))
            
            return faces, confidences
        
        return [], []
    
    def _scale_boxes(self, boxes: List[Tuple], scale_x: float, scale_y: float) -> List[Tuple]:
        """Scale bounding boxes back to original image coordinates"""
        scaled_boxes = []
        for x1, y1, x2, y2 in boxes:
            scaled_boxes.append((
                int(x1 * scale_x),
                int(y1 * scale_y), 
                int(x2 * scale_x),
                int(y2 * scale_y)
            ))
        return scaled_boxes


class ObjectDetectionNode(ProcessingNode):
    """
    Object detection node for privacy-sensitive objects
    
    Detects:
    - Screens (laptops, phones, TVs)
    - Documents (books, papers)
    - License plates (specialized model)
    """
    
    def __init__(self, config: PrivacyConfig, model_manager: ModelManager):
        super().__init__("object_detection", config)
        self.model_manager = model_manager
        
        # Privacy-sensitive object classes (COCO class IDs)
        self.privacy_classes = {
            'laptop': 63,
            'tv': 62,
            'cell phone': 67,
            'book': 73,
            'car': 2,  # For license plate context
            'truck': 7,
            'bus': 5
        }
        
    def is_enabled_for_level(self, privacy_level: PrivacyLevel) -> bool:
        """Object detection enabled for Balanced and Paranoid levels"""
        return privacy_level in [PrivacyLevel.BALANCED, PrivacyLevel.PARANOID]
    
    async def process(self, context: ProcessingContext) -> Optional[DetectionResult]:
        """
        Detect privacy-sensitive objects
        
        Args:
            context: Processing context with image data
            
        Returns:
            DetectionResult with object bounding boxes
        """
        start_time = time.time()
        
        try:
            # Get object detection model
            model_session = await self.model_manager.get_model("object_detection", context.privacy_level)
            if not model_session:
                self.logger.error("Object detection model not available")
                return None
            
            # Prepare input
            input_image, scale_x, scale_y = self._prepare_yolo_input(
                context.original_image,
                model_session.input_shape
            )
            
            # Run inference
            detections = await self._run_yolo_inference(model_session, input_image)
            
            # Filter for privacy-sensitive objects
            privacy_objects = self._filter_privacy_objects(detections)
            
            # Scale back to original coordinates
            scaled_objects = self._scale_detections(privacy_objects, scale_x, scale_y)
            
            # Detect license plates if Balanced/Paranoid mode
            license_plates = []
            if context.privacy_level in [PrivacyLevel.BALANCED, PrivacyLevel.PARANOID]:
                license_plates = await self._detect_license_plates(context, scale_x, scale_y)
            
            # Combine all detections
            all_boxes = [obj['box'] for obj in scaled_objects] + [lp['box'] for lp in license_plates]
            all_confidences = [obj['confidence'] for obj in scaled_objects] + [lp['confidence'] for lp in license_plates]
            all_labels = [obj['label'] for obj in scaled_objects] + [lp['label'] for lp in license_plates]
            
            processing_time = time.time() - start_time
            
            self.logger.info(f"Detected {len(all_boxes)} privacy-sensitive objects in {processing_time:.3f}s")
            
            return DetectionResult(
                node_type="object_detection",
                bounding_boxes=all_boxes,
                confidences=all_confidences,
                labels=all_labels,
                processing_time=processing_time,
                metadata={
                    "model_used": model_session.model_path,
                    "general_objects": len(scaled_objects),
                    "license_plates": len(license_plates),
                    "privacy_classes": list(self.privacy_classes.keys())
                }
            )
            
        except Exception as e:
            self.logger.error(f"Object detection failed: {e}")
            return None
    
    def _prepare_yolo_input(self, image: np.ndarray, target_shape: tuple) -> Tuple[np.ndarray, float, float]:
        """Prepare input for YOLO model"""
        h, w = image.shape[:2]
        target_size = target_shape[-1]  # Assuming square input
        
        # Calculate scale to maintain aspect ratio
        scale = min(target_size / w, target_size / h)
        new_w, new_h = int(w * scale), int(h * scale)
        
        # Resize and pad
        resized = cv2.resize(image, (new_w, new_h))
        
        # Create padded image
        padded = np.full((target_size, target_size, 3), 114, dtype=np.uint8)
        padded[:new_h, :new_w] = resized
        
        # Convert to RGB and normalize
        padded = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
        input_image = padded.transpose(2, 0, 1).astype(np.float32) / 255.0
        input_image = np.expand_dims(input_image, axis=0)
        
        return input_image, w / new_w, h / new_h
    
    async def _run_yolo_inference(self, model_session, input_image):
        """Run YOLO inference"""
        input_name = model_session.session.get_inputs()[0].name
        output_names = [output.name for output in model_session.session.get_outputs()]
        
        outputs = model_session.session.run(output_names, {input_name: input_image})
        return outputs[0]  # YOLO output format
    
    def _filter_privacy_objects(self, detections) -> List[Dict]:
        """Filter detections for privacy-sensitive objects"""
        privacy_objects = []
        
        for detection in detections[0]:  # Remove batch dimension
            if len(detection) >= 6:  # x, y, w, h, conf, class_id, ...
                x, y, w, h, conf, class_id = detection[:6]
                
                # Check if this is a privacy-sensitive class
                for label, coco_id in self.privacy_classes.items():
                    if int(class_id) == coco_id and conf > 0.5:
                        privacy_objects.append({
                            'box': (int(x - w/2), int(y - h/2), int(x + w/2), int(y + h/2)),
                            'confidence': float(conf),
                            'label': label
                        })
                        break
        
        return privacy_objects
    
    def _scale_detections(self, detections: List[Dict], scale_x: float, scale_y: float) -> List[Dict]:
        """Scale detections back to original coordinates"""
        scaled = []
        for det in detections:
            x1, y1, x2, y2 = det['box']
            scaled.append({
                'box': (int(x1 * scale_x), int(y1 * scale_y), int(x2 * scale_x), int(y2 * scale_y)),
                'confidence': det['confidence'],
                'label': det['label']
            })
        return scaled
    
    async def _detect_license_plates(self, context: ProcessingContext, scale_x: float, scale_y: float) -> List[Dict]:
        """Detect license plates using specialized model"""
        try:
            # Get license plate detection model
            lp_model = await self.model_manager.get_model("license_plate_detection", context.privacy_level)
            if not lp_model:
                return []
            
            # Prepare input
            input_image, lp_scale_x, lp_scale_y = self._prepare_yolo_input(
                context.original_image,
                lp_model.input_shape
            )
            
            # Run inference
            lp_detections = await self._run_yolo_inference(lp_model, input_image)
            
            # Parse license plate detections
            license_plates = []
            for detection in lp_detections[0]:
                if len(detection) >= 5:
                    x, y, w, h, conf = detection[:5]
                    if conf > 0.6:  # Higher threshold for license plates
                        license_plates.append({
                            'box': (
                                int((x - w/2) * lp_scale_x),
                                int((y - h/2) * lp_scale_y),
                                int((x + w/2) * lp_scale_x),
                                int((y + h/2) * lp_scale_y)
                            ),
                            'confidence': float(conf),
                            'label': 'license_plate'
                        })
            
            return license_plates
            
        except Exception as e:
            self.logger.warning(f"License plate detection failed: {e}")
            return []


class TextDetectionNode(ProcessingNode):
    """
    Text detection node using PaddleOCR
    
    Detects text regions that may contain PII
    """
    
    def __init__(self, config: PrivacyConfig, model_manager: ModelManager):
        super().__init__("text_detection", config)
        self.model_manager = model_manager
        
    def is_enabled_for_level(self, privacy_level: PrivacyLevel) -> bool:
        """Text detection enabled for Balanced and Paranoid levels"""
        return privacy_level in [PrivacyLevel.BALANCED, PrivacyLevel.PARANOID]
    
    async def process(self, context: ProcessingContext) -> Optional[DetectionResult]:
        """
        Detect text regions in image
        
        Args:
            context: Processing context with image data
            
        Returns:
            DetectionResult with text region bounding boxes
        """
        start_time = time.time()
        
        try:
            # Get text detection model
            model_session = await self.model_manager.get_model("text_detection", context.privacy_level)
            if not model_session:
                self.logger.error("Text detection model not available")
                return None
            
            # Prepare input for PaddleOCR
            input_image = self._prepare_paddle_input(context.original_image)
            
            # Run text detection
            text_boxes = await self._run_paddle_inference(model_session, input_image)
            
            # Convert to standard bounding box format
            standard_boxes = self._convert_text_boxes(text_boxes)
            
            processing_time = time.time() - start_time
            
            self.logger.info(f"Detected {len(standard_boxes)} text regions in {processing_time:.3f}s")
            
            return DetectionResult(
                node_type="text_detection",
                bounding_boxes=standard_boxes,
                confidences=[0.9] * len(standard_boxes),  # PaddleOCR doesn't provide confidence
                labels=["text"] * len(standard_boxes),
                processing_time=processing_time,
                metadata={
                    "model_used": model_session.model_path,
                    "text_regions": len(standard_boxes)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Text detection failed: {e}")
            return None
    
    def _prepare_paddle_input(self, image: np.ndarray) -> np.ndarray:
        """Prepare input for PaddleOCR model"""
        # PaddleOCR expects RGB image in range [0, 255]
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        return image.astype(np.float32)
    
    async def _run_paddle_inference(self, model_session, input_image):
        """Run PaddleOCR text detection inference"""
        # Note: This is a simplified version
        # In practice, you'd need to implement PaddleOCR's preprocessing/postprocessing
        input_name = model_session.session.get_inputs()[0].name
        
        # Resize to model input size
        h, w = input_image.shape[:2]
        target_h, target_w = model_session.input_shape[-2:]
        
        resized = cv2.resize(input_image, (target_w, target_h))
        processed = resized.transpose(2, 0, 1) / 255.0
        processed = np.expand_dims(processed, axis=0)
        
        outputs = model_session.session.run(None, {input_name: processed})
        
        # Post-process outputs to get text boxes
        return self._postprocess_paddle_output(outputs[0], w / target_w, h / target_h)
    
    def _postprocess_paddle_output(self, output, scale_x: float, scale_y: float):
        """Post-process PaddleOCR output to get text boxes"""
        # Simplified post-processing
        # In practice, this would involve contour detection and filtering
        text_boxes = []
        
        # Apply threshold to get binary mask
        threshold = 0.3
        binary = (output[0, 0] > threshold).astype(np.uint8)
        
        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            if cv2.contourArea(contour) > 100:  # Minimum area threshold
                x, y, w, h = cv2.boundingRect(contour)
                # Scale back to original coordinates
                text_boxes.append([
                    [x * scale_x, y * scale_y],
                    [(x + w) * scale_x, y * scale_y],
                    [(x + w) * scale_x, (y + h) * scale_y],
                    [x * scale_x, (y + h) * scale_y]
                ])
        
        return text_boxes
    
    def _convert_text_boxes(self, text_boxes) -> List[Tuple]:
        """Convert text boxes to standard (x1, y1, x2, y2) format"""
        standard_boxes = []
        
        for box in text_boxes:
            if len(box) >= 4:
                # Extract coordinates
                xs = [point[0] for point in box]
                ys = [point[1] for point in box]
                
                x1, y1 = min(xs), min(ys)
                x2, y2 = max(xs), max(ys)
                
                standard_boxes.append((int(x1), int(y1), int(x2), int(y2)))
        
        return standard_boxes


class PIIAnalysisNode(ProcessingNode):
    """
    PII (Personally Identifiable Information) analysis node
    
    Analyzes text regions to identify PII that should be redacted
    """
    
    def __init__(self, config: PrivacyConfig, model_manager: ModelManager):
        super().__init__("pii_analysis", config)
        self.model_manager = model_manager
        
        # PII patterns for rule-based detection
        self.pii_patterns = {
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'phone': re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
            'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            'credit_card': re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
            'address': re.compile(r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr)\b', re.IGNORECASE)
        }
    
    def is_enabled_for_level(self, privacy_level: PrivacyLevel) -> bool:
        """PII analysis enabled for Balanced and Paranoid levels"""
        return privacy_level in [PrivacyLevel.BALANCED, PrivacyLevel.PARANOID]
    
    async def process(self, context: ProcessingContext) -> Optional[DetectionResult]:
        """
        Analyze detected text regions for PII
        
        Args:
            context: Processing context with image data and text detection results
            
        Returns:
            DetectionResult with PII-containing text regions
        """
        start_time = time.time()
        
        try:
            # Get text detection results from previous node
            text_detection = context.detection_results.get("text_detection")
            if not text_detection:
                self.logger.warning("No text detection results available for PII analysis")
                return None
            
            pii_boxes = []
            pii_confidences = []
            pii_labels = []
            
            # Analyze each text region
            for i, text_box in enumerate(text_detection.bounding_boxes):
                # Extract text from image region
                text_content = self._extract_text_from_region(context.original_image, text_box)
                
                if text_content:
                    # Check for PII patterns
                    pii_types = self._detect_pii_patterns(text_content)
                    
                    if pii_types:
                        pii_boxes.append(text_box)
                        pii_confidences.append(0.9)  # High confidence for pattern matches
                        pii_labels.append(f"pii_{'+'.join(pii_types)}")
            
            # If in Paranoid mode, apply ML-based PII detection
            if context.privacy_level == PrivacyLevel.PARANOID:
                ml_pii_boxes = await self._ml_pii_detection(context, text_detection.bounding_boxes)
                pii_boxes.extend(ml_pii_boxes)
                pii_confidences.extend([0.8] * len(ml_pii_boxes))
                pii_labels.extend(["pii_ml"] * len(ml_pii_boxes))
            
            processing_time = time.time() - start_time
            
            self.logger.info(f"Identified {len(pii_boxes)} PII regions in {processing_time:.3f}s")
            
            return DetectionResult(
                node_type="pii_analysis",
                bounding_boxes=pii_boxes,
                confidences=pii_confidences,
                labels=pii_labels,
                processing_time=processing_time,
                metadata={
                    "text_regions_analyzed": len(text_detection.bounding_boxes),
                    "pii_regions_found": len(pii_boxes),
                    "patterns_used": list(self.pii_patterns.keys())
                }
            )
            
        except Exception as e:
            self.logger.error(f"PII analysis failed: {e}")
            return None
    
    def _extract_text_from_region(self, image: np.ndarray, box: Tuple[int, int, int, int]) -> str:
        """
        Extract text from image region using simple OCR
        
        Args:
            image: Original image
            box: Bounding box (x1, y1, x2, y2)
            
        Returns:
            Extracted text content
        """
        try:
            x1, y1, x2, y2 = box
            
            # Crop region
            region = image[y1:y2, x1:x2]
            
            if region.size == 0:
                return ""
            
            # Simple preprocessing for OCR
            gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
            
            # Use basic OCR (in practice, use better OCR like Tesseract or PaddleOCR)
            # For now, return placeholder that would trigger PII detection
            # This would be replaced with actual OCR in production
            
            return ""  # Placeholder - implement actual OCR
            
        except Exception as e:
            self.logger.warning(f"Text extraction failed for region {box}: {e}")
            return ""
    
    def _detect_pii_patterns(self, text: str) -> List[str]:
        """
        Detect PII using regex patterns
        
        Args:
            text: Text content to analyze
            
        Returns:
            List of detected PII types
        """
        detected_pii = []
        
        for pii_type, pattern in self.pii_patterns.items():
            if pattern.search(text):
                detected_pii.append(pii_type)
        
        return detected_pii
    
    async def _ml_pii_detection(self, context: ProcessingContext, text_boxes: List[Tuple]) -> List[Tuple]:
        """
        Use ML model for PII detection (Paranoid mode only)
        
        Args:
            context: Processing context
            text_boxes: Text bounding boxes to analyze
            
        Returns:
            List of boxes containing ML-detected PII
        """
        # Placeholder for ML-based PII detection
        # In practice, this would use a spaCy NER model or similar
        
        try:
            # Get PII analysis model if available
            model_session = await self.model_manager.get_model("pii_analysis", context.privacy_level)
            if not model_session:
                return []
            
            # Would implement actual ML-based PII detection here
            # For now, return empty list
            return []
            
        except Exception as e:
            self.logger.warning(f"ML PII detection failed: {e}")
            return []