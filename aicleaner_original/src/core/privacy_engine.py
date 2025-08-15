"""
Privacy Engine for AICleaner V3
Handles image sanitization for the 4-level privacy spectrum
"""

import cv2
import numpy as np
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import json
import time

class PrivacyLevel(Enum):
    LEVEL_1_RAW = 1      # Raw images to cloud (fastest, no privacy)
    LEVEL_2_SANITIZED = 2 # Sanitized images to cloud (recommended balance)
    LEVEL_3_METADATA = 3  # Metadata only to cloud (limited effectiveness)
    LEVEL_4_LOCAL = 4     # Full local processing (maximum privacy)

@dataclass
class DetectedObject:
    """Represents an object detected during privacy scanning"""
    type: str  # face, license_plate, document, screen, etc.
    confidence: float
    bbox: tuple  # (x1, y1, x2, y2)
    
@dataclass
class SanitizationResult:
    """Result of image sanitization process"""
    sanitized_image: Optional[bytes]
    metadata: Dict[str, Any]
    objects_detected: List[DetectedObject]
    processing_time: float
    privacy_level: PrivacyLevel

class PrivacyEngine:
    """Core privacy processing engine"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._face_cascade = None
        self._initialize_detectors()
    
    def _initialize_detectors(self):
        """Initialize OpenCV classifiers for privacy detection"""
        try:
            # Load OpenCV's pre-trained face cascade
            self._face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
        except Exception as e:
            print(f"Warning: Could not initialize face detection: {e}")
            self._face_cascade = None
    
    async def process_image(self, image_bytes: bytes, privacy_level: PrivacyLevel) -> SanitizationResult:
        """
        Process image according to specified privacy level
        
        Args:
            image_bytes: Raw image data
            privacy_level: Desired privacy level
            
        Returns:
            SanitizationResult with processed image and metadata
        """
        start_time = time.time()
        
        # Convert bytes to OpenCV image
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise ValueError("Invalid image data")
        
        # Process based on privacy level
        if privacy_level == PrivacyLevel.LEVEL_1_RAW:
            return SanitizationResult(
                sanitized_image=image_bytes,  # No processing
                metadata={},
                objects_detected=[],
                processing_time=time.time() - start_time,
                privacy_level=privacy_level
            )
        
        elif privacy_level == PrivacyLevel.LEVEL_2_SANITIZED:
            return await self._sanitize_image(image, image_bytes, start_time, privacy_level)
        
        elif privacy_level == PrivacyLevel.LEVEL_3_METADATA:
            return await self._extract_metadata_only(image, start_time, privacy_level)
        
        elif privacy_level == PrivacyLevel.LEVEL_4_LOCAL:
            # For local processing, we still need to pass the image
            # but mark it for local-only processing
            return SanitizationResult(
                sanitized_image=image_bytes,
                metadata={"local_processing": True},
                objects_detected=[],
                processing_time=time.time() - start_time,
                privacy_level=privacy_level
            )
    
    async def _sanitize_image(self, image, original_bytes: bytes, start_time: float, privacy_level: PrivacyLevel) -> SanitizationResult:
        """Sanitize image by blurring sensitive areas"""
        detected_objects = []
        sanitized_image = image.copy()
        
        # Detect and blur faces
        if self._face_cascade is not None:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = self._face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            for (x, y, w, h) in faces:
                # Apply strong gaussian blur to face region
                face_region = sanitized_image[y:y+h, x:x+w]
                blurred_face = cv2.GaussianBlur(face_region, (99, 99), 30)
                sanitized_image[y:y+h, x:x+w] = blurred_face
                
                detected_objects.append(DetectedObject(
                    type="face",
                    confidence=0.8,  # OpenCV doesn't provide confidence scores
                    bbox=(x, y, x+w, y+h)
                ))
        
        # Detect and blur text/documents (simple approach using contours)
        detected_objects.extend(await self._detect_and_blur_text(sanitized_image))
        
        # Convert back to bytes
        _, buffer = cv2.imencode('.jpg', sanitized_image)
        sanitized_bytes = buffer.tobytes()
        
        return SanitizationResult(
            sanitized_image=sanitized_bytes,
            metadata=self._generate_metadata(image, detected_objects),
            objects_detected=detected_objects,
            processing_time=time.time() - start_time,
            privacy_level=privacy_level
        )
    
    async def _extract_metadata_only(self, image, start_time: float, privacy_level: PrivacyLevel) -> SanitizationResult:
        """Extract only metadata from image for Level 3 processing"""
        
        # Basic scene analysis without sending the actual image
        height, width = image.shape[:2]
        
        # Simple brightness and color analysis
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        
        # Basic object detection using simple methods
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Count potential objects based on contours
        significant_objects = len([c for c in contours if cv2.contourArea(c) > 500])
        
        metadata = {
            "image_dimensions": {"width": width, "height": height},
            "brightness_level": float(brightness),
            "estimated_objects": significant_objects,
            "scene_complexity": "low" if significant_objects < 5 else "medium" if significant_objects < 15 else "high",
            "dominant_color": self._get_dominant_color(image).tolist(),
            "analysis_type": "metadata_only"
        }
        
        return SanitizationResult(
            sanitized_image=None,  # No image sent to cloud
            metadata=metadata,
            objects_detected=[],
            processing_time=time.time() - start_time,
            privacy_level=privacy_level
        )
    
    async def _detect_and_blur_text(self, image) -> List[DetectedObject]:
        """Simple text/document detection and blurring"""
        detected = []
        
        # Convert to grayscale for text detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Use adaptive threshold to find text-like regions
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        
        # Find contours that might be text
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if 100 < area < 10000:  # Text-like size range
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h
                
                # Text usually has certain aspect ratios
                if 0.1 < aspect_ratio < 10:
                    # Apply blur to potential text region
                    text_region = image[y:y+h, x:x+w]
                    blurred_text = cv2.GaussianBlur(text_region, (15, 15), 0)
                    image[y:y+h, x:x+w] = blurred_text
                    
                    detected.append(DetectedObject(
                        type="text",
                        confidence=0.6,
                        bbox=(x, y, x+w, y+h)
                    ))
        
        return detected
    
    def _generate_metadata(self, image, detected_objects: List[DetectedObject]) -> Dict[str, Any]:
        """Generate metadata about the image for analysis"""
        height, width = image.shape[:2]
        
        return {
            "image_dimensions": {"width": width, "height": height},
            "objects_sanitized": len(detected_objects),
            "sanitization_types": list(set(obj.type for obj in detected_objects)),
            "privacy_level": "sanitized",
            "processing_method": "opencv_blur"
        }
    
    def _get_dominant_color(self, image) -> np.ndarray:
        """Get dominant color in image"""
        pixels = image.reshape(-1, 3)
        pixels = np.float32(pixels)
        
        # Use k-means to find dominant color
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        _, labels, centers = cv2.kmeans(pixels, 1, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        
        return centers[0].astype(np.uint8)
    
    def get_privacy_level_description(self, level: PrivacyLevel) -> str:
        """Get human-readable description of privacy level"""
        descriptions = {
            PrivacyLevel.LEVEL_1_RAW: "Raw images sent to cloud provider (fastest, no privacy protection)",
            PrivacyLevel.LEVEL_2_SANITIZED: "Faces and sensitive data blurred before cloud processing (recommended balance)",
            PrivacyLevel.LEVEL_3_METADATA: "Only scene metadata sent to cloud (faster processing, limited accuracy)",
            PrivacyLevel.LEVEL_4_LOCAL: "Everything processed locally (slowest, maximum privacy protection)"
        }
        return descriptions.get(level, "Unknown privacy level")