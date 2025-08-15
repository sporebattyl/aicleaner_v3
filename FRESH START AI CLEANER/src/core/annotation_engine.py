"""
Annotation Engine for AICleaner V3
Handles bounding box processing and image overlay for visual annotations
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
import io
import time

from ..providers.base_provider import BoundingBox, Task

@dataclass
class AnnotationStyle:
    """Configuration for visual annotation styling"""
    box_color: Tuple[int, int, int] = (255, 0, 0)  # Red
    box_thickness: int = 2
    text_color: Tuple[int, int, int] = (255, 255, 255)  # White
    text_background: Tuple[int, int, int] = (255, 0, 0)  # Red background
    font_size: int = 14
    alpha: float = 0.8  # Transparency

@dataclass
class AnnotationConfig:
    """Configuration for annotation processing"""
    max_text_length: int = 50
    min_box_size: int = 20
    padding: int = 5
    number_tasks: bool = True
    show_confidence: bool = True

class AnnotationEngine:
    """Engine for creating visual annotations on images"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.style = AnnotationStyle()
        self.annotation_config = AnnotationConfig()
        
        # Try to load a font, fallback to default if not available
        self._font = self._load_font()
    
    def _load_font(self) -> Optional[ImageFont.FreeTypeFont]:
        """Load a font for text rendering"""
        try:
            # Try to load a system font
            return ImageFont.truetype("arial.ttf", self.style.font_size)
        except:
            try:
                # Try alternative font names
                return ImageFont.truetype("DejaVuSans.ttf", self.style.font_size)
            except:
                # Use default PIL font
                return ImageFont.load_default()
    
    async def annotate_image(self, image_bytes: bytes, tasks: List[Task]) -> bytes:
        """
        Add visual annotations to an image based on tasks
        
        Args:
            image_bytes: Original image as bytes
            tasks: List of tasks with bounding box annotations
            
        Returns:
            Annotated image as bytes
        """
        start_time = time.time()
        
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_bytes))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Create a copy for annotation
        annotated = image.copy()
        draw = ImageDraw.Draw(annotated)
        
        # Filter tasks that have annotations
        annotated_tasks = [task for task in tasks if task.annotation is not None]
        
        # Draw annotations for each task
        for i, task in enumerate(annotated_tasks, 1):
            await self._draw_task_annotation(draw, task, i, image.size)
        
        # Convert back to bytes
        output = io.BytesIO()
        annotated.save(output, format='JPEG', quality=90)
        
        processing_time = time.time() - start_time
        print(f"Image annotation completed in {processing_time:.3f} seconds")
        
        return output.getvalue()
    
    async def _draw_task_annotation(self, draw: ImageDraw.Draw, task: Task, task_number: int, image_size: Tuple[int, int]) -> None:
        """Draw annotation for a single task"""
        if task.annotation is None:
            return
        
        bbox = task.annotation
        
        # Ensure bounding box is within image bounds
        bbox = self._clamp_bbox(bbox, image_size)
        
        # Draw bounding box
        draw.rectangle(
            [(bbox.x1, bbox.y1), (bbox.x2, bbox.y2)],
            outline=self.style.box_color,
            width=self.style.box_thickness
        )
        
        # Prepare text
        text_lines = self._prepare_text(task, task_number)
        
        # Draw text background and text
        if text_lines:
            await self._draw_text_with_background(draw, text_lines, bbox, image_size)
    
    def _clamp_bbox(self, bbox: BoundingBox, image_size: Tuple[int, int]) -> BoundingBox:
        """Ensure bounding box coordinates are within image bounds"""
        width, height = image_size
        
        return BoundingBox(
            x1=max(0, min(bbox.x1, width - 1)),
            y1=max(0, min(bbox.y1, height - 1)),
            x2=max(bbox.x1 + self.annotation_config.min_box_size, min(bbox.x2, width)),
            y2=max(bbox.y1 + self.annotation_config.min_box_size, min(bbox.y2, height))
        )
    
    def _prepare_text(self, task: Task, task_number: int) -> List[str]:
        """Prepare text lines for annotation"""
        lines = []
        
        # Task number if enabled
        if self.annotation_config.number_tasks:
            lines.append(f"#{task_number}")
        
        # Task description (truncated if too long)
        description = task.description
        if len(description) > self.annotation_config.max_text_length:
            description = description[:self.annotation_config.max_text_length - 3] + "..."
        lines.append(description)
        
        # Confidence score if available and enabled
        if self.annotation_config.show_confidence and task.confidence is not None:
            lines.append(f"Confidence: {task.confidence:.1%}")
        
        # Priority indicator
        priority_labels = {1: "HIGH", 2: "MED", 3: "LOW"}
        if task.priority in priority_labels:
            lines.append(f"Priority: {priority_labels[task.priority]}")
        
        return lines
    
    async def _draw_text_with_background(self, draw: ImageDraw.Draw, text_lines: List[str], bbox: BoundingBox, image_size: Tuple[int, int]) -> None:
        """Draw text with a background for readability"""
        
        # Calculate text dimensions
        text_bbox = self._calculate_text_bbox(text_lines)
        text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
        
        # Position text (prefer above the bounding box, fallback to inside)
        text_x = bbox.x1
        text_y = bbox.y1 - text_height - self.annotation_config.padding
        
        # If text would go outside image bounds, position it inside the bbox
        if text_y < 0:
            text_y = bbox.y1 + self.annotation_config.padding
        
        # Clamp text position to image bounds
        text_x = max(0, min(text_x, image_size[0] - text_width))
        text_y = max(0, min(text_y, image_size[1] - text_height))
        
        # Draw background rectangle
        bg_x1 = text_x - self.annotation_config.padding
        bg_y1 = text_y - self.annotation_config.padding
        bg_x2 = text_x + text_width + self.annotation_config.padding
        bg_y2 = text_y + text_height + self.annotation_config.padding
        
        draw.rectangle(
            [(bg_x1, bg_y1), (bg_x2, bg_y2)],
            fill=self.style.text_background,
            outline=self.style.box_color
        )
        
        # Draw text lines
        current_y = text_y
        line_height = self._get_line_height()
        
        for line in text_lines:
            draw.text(
                (text_x, current_y),
                line,
                fill=self.style.text_color,
                font=self._font
            )
            current_y += line_height
    
    def _calculate_text_bbox(self, text_lines: List[str]) -> Tuple[int, int, int, int]:
        """Calculate bounding box for multiple text lines"""
        if not text_lines:
            return (0, 0, 0, 0)
        
        max_width = 0
        total_height = 0
        line_height = self._get_line_height()
        
        for line in text_lines:
            if hasattr(self._font, 'getbbox'):
                bbox = self._font.getbbox(line)
                width = bbox[2] - bbox[0]
            else:
                # Fallback for older PIL versions
                width, _ = self._font.getsize(line)
            
            max_width = max(max_width, width)
            total_height += line_height
        
        return (0, 0, max_width, total_height)
    
    def _get_line_height(self) -> int:
        """Get line height for text rendering"""
        if hasattr(self._font, 'getbbox'):
            bbox = self._font.getbbox('Ay')
            return bbox[3] - bbox[1] + 2  # Add small padding
        else:
            # Fallback for older PIL versions
            return self._font.getsize('Ay')[1] + 2
    
    def create_summary_image(self, tasks: List[Task], image_size: Tuple[int, int] = (400, 300)) -> bytes:
        """
        Create a summary image showing all tasks without the original image
        
        Args:
            tasks: List of tasks to summarize
            image_size: Size of the summary image
            
        Returns:
            Summary image as bytes
        """
        # Create blank image
        image = Image.new('RGB', image_size, color=(240, 240, 240))
        draw = ImageDraw.Draw(image)
        
        # Title
        title = f"Found {len(tasks)} Cleaning Tasks"
        title_bbox = self._font.getbbox(title) if hasattr(self._font, 'getbbox') else (0, 0, *self._font.getsize(title))
        title_x = (image_size[0] - (title_bbox[2] - title_bbox[0])) // 2
        
        draw.text((title_x, 20), title, fill=(0, 0, 0), font=self._font)
        
        # Draw task list
        y_offset = 60
        line_height = self._get_line_height()
        
        for i, task in enumerate(tasks[:10], 1):  # Limit to 10 tasks
            # Priority indicator
            priority_color = {1: (255, 0, 0), 2: (255, 165, 0), 3: (0, 128, 0)}.get(task.priority, (128, 128, 128))
            draw.rectangle([(20, y_offset - 2), (30, y_offset + line_height - 2)], fill=priority_color)
            
            # Task text
            text = f"{i}. {task.description[:50]}{'...' if len(task.description) > 50 else ''}"
            draw.text((40, y_offset), text, fill=(0, 0, 0), font=self._font)
            
            y_offset += line_height + 5
            
            if y_offset > image_size[1] - 40:
                break
        
        # Convert to bytes
        output = io.BytesIO()
        image.save(output, format='PNG')
        return output.getvalue()
    
    def update_style(self, **kwargs) -> None:
        """Update annotation style parameters"""
        for key, value in kwargs.items():
            if hasattr(self.style, key):
                setattr(self.style, key, value)
    
    def update_config(self, **kwargs) -> None:
        """Update annotation configuration parameters"""
        for key, value in kwargs.items():
            if hasattr(self.annotation_config, key):
                setattr(self.annotation_config, key, value)