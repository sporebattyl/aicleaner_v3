"""
Gemini client for AI Cleaner addon.
Handles communication with Google Gemini API.
"""
import os
import logging
import asyncio
import time
import json
from typing import Dict, Any, List, Optional
from PIL import Image

try:
    import google.generativeai as genai
    from google.generativeai import GenerativeModel
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

class GeminiClient:
    """
    Gemini client.
    
    Features:
    - Image analysis
    - Retry logic
    - Error handling
    """
    
    def __init__(self, config):
        """
        Initialize the Gemini client.
        
        Args:
            config: Configuration
        """
        self.config = config
        self.logger = logging.getLogger("gemini_client")
        
        # API key
        self.api_key = config.get("gemini_api_key")
        
        # Model name
        self.model_name = config.get("gemini_model", "gemini-1.5-flash")
        
        # Retry settings
        self.max_retries = config.get("gemini_max_retries", 3)
        self.retry_delay = config.get("gemini_retry_delay", 2)
        
        # Model
        self.model = None
        
    async def initialize(self):
        """Initialize the Gemini client."""
        self.logger.info("Initializing Gemini client")
        
        if not GEMINI_AVAILABLE:
            self.logger.error("Google Generative AI package not available")
            return
            
        if not self.api_key:
            self.logger.error("Gemini API key not configured")
            return
            
        try:
            # Configure API
            genai.configure(api_key=self.api_key)
            
            # Create model
            self.model = GenerativeModel(self.model_name)
            
            self.logger.info(f"Initialized Gemini client with model {self.model_name}")
            
        except Exception as e:
            self.logger.error(f"Error initializing Gemini client: {e}")
            
    async def analyze_image(self, prompt: str, image: Image.Image) -> Dict[str, Any]:
        """
        Analyze image.
        
        Args:
            prompt: Prompt
            image: Image
            
        Returns:
            Analysis result
        """
        if not GEMINI_AVAILABLE or not self.model:
            self.logger.error("Gemini client not initialized")
            return None
            
        # Retry logic
        for attempt in range(self.max_retries + 1):
            try:
                # Create the content parts
                content_parts = [prompt, image]
                
                # Generate content
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    content_parts
                )
                
                # Process the response
                if response.candidates and response.candidates[0].content:
                    text = response.candidates[0].content.parts[0].text
                    return {
                        "text": text,
                        "model": self.model_name,
                        "prompt": prompt,
                        "timestamp": time.time()
                    }
                else:
                    raise Exception("Empty response from Gemini API")
                    
            except Exception as e:
                # Log error
                self.logger.error(f"Error calling Gemini API (attempt {attempt + 1}/{self.max_retries + 1}): {e}")
                
                # Check if this was the last attempt
                if attempt < self.max_retries:
                    # Wait before retry
                    retry_delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    self.logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    # Last attempt failed
                    self.logger.error(f"Failed to call Gemini API after {self.max_retries + 1} attempts")
                    return None
        




