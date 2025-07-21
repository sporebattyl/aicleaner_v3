# 🚀 Comprehensive Gemini API Usage Guide (Updated 2025-01-17)

### Current Model Recommendations (Based on Google AI Documentation)

**🏆 Production Models (Gemini 2.5 Series):**
- **`gemini-2.5-pro`** - Most powerful thinking model with maximum response accuracy
  - **Best for:** Complex coding, reasoning, multimodal understanding, architectural decisions
  - **Supports:** Audio, images, video, text, PDF inputs, function calling, code execution
  - **Token Limit:** 1,048,576 input tokens
  - **Thinking Budget:** 128-32,768 tokens

- **`gemini-2.5-flash`** - Best price-performance ratio with well-rounded capabilities
  - **Best for:** Large scale processing, low-latency, high volume tasks, general use
  - **Supports:** Text, images, video, audio inputs, adaptive thinking, function calling
  - **Token Limit:** 1,048,576 input tokens  
  - **Thinking Budget:** 0-24,576 tokens

- **`gemini-2.5-flash-lite`** - Optimized for cost efficiency and low latency
  - **Best for:** Real-time, high throughput use cases, simple queries
  - **Token Limit:** 1,000,000 input tokens
  - **Thinking Budget:** 512-24,576 tokens

### API Setup and Authentication

**Environment Setup:**
```bash
# Install Google Generative AI Python SDK (requires Python 3.9+)
pip install -q -U google-genai

# Set primary API key as environment variable
export GEMINI_API_KEY=AIzaSyDYRk_mZQZ_Rjq-sPbLaW5fpN9XnZ39Nro

# Additional keys for rotation
export GEMINI_API_KEY_PRIMARY=AIzaSyDYRk_mZQZ_Rjq-sPbLaW5fpN9XnZ39Nro
export GEMINI_API_KEY_SECONDARY=AIzaSyBdS3Mp_pAgxlj7SK0ziNPjS-Jfgx5u3Fc
export GEMINI_API_KEY_TERTIARY=AIzaSyBtBJg2AHVlNYZCSco69JWGkCL8zDFQNzo
export GEMINI_API_KEY_BACKUP=AIzaSyAUrUCFIL2D4Lq5nQyfHfigHI0QgtH9oTI
```

**Python SDK Usage:**
```python
from google import genai

# Initialize client (automatically uses GEMINI_API_KEY environment variable)
client = genai.Client()

# Basic text generation
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Explain how AI works in a few words"
)
print(response.text)

# Advanced configuration with thinking budget
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents="Complex architectural analysis task",
    config=genai.GenerateContentConfig(
        thinking_config=genai.ThinkingConfig(budget=8192)  # Optimize thinking budget
    )
)
```

### Thinking Feature Optimization

**Understanding Thinking Budgets:**
- **Purpose:** Improves reasoning and multi-step planning for complex tasks
- **Cost:** Pricing = Output tokens + Thinking tokens
- **Recommendation:** Adjust budget based on task complexity

**Budget Guidelines:**
```python
# Easy tasks (fact retrieval, simple questions)
thinking_config = genai.ThinkingConfig(budget=0)  # Disable thinking

# Medium complexity (code review, analysis)
thinking_config = genai.ThinkingConfig(budget=2048)  # Moderate thinking

# Complex tasks (architectural decisions, multi-step reasoning)
thinking_config = genai.ThinkingConfig(budget=8192)  # High thinking budget

# Maximum complexity (detailed analysis, comprehensive planning)
thinking_config = genai.ThinkingConfig(budget=16384)  # Very high thinking
```

### Rate Limit Management and Key Rotation

**Current Rate Limits (Free Tier Examples):**
- **Gemini 2.5 Pro:** 5 RPM, 250,000 TPM, 100 RPD
- **Gemini 2.5 Flash:** 10 RPM, 250,000 TPM, 250 RPD
- **Gemini 2.5 Flash-Lite:** Higher limits for production use

**Enhanced Key Cycling Strategy:**
```python
import time
import os
from typing import List

class GeminiKeyManager:
    def __init__(self):
        self.keys = [
            os.getenv("GEMINI_API_KEY_PRIMARY"),
            os.getenv("GEMINI_API_KEY_SECONDARY"), 
            os.getenv("GEMINI_API_KEY_TERTIARY"),
            os.getenv("GEMINI_API_KEY_BACKUP")
        ]
        self.current_key_index = 0
        self.request_count = 0
        self.last_rotation = time.time()
    
    def get_current_key(self) -> str:
        return self.keys[self.current_key_index]
    
    def should_rotate(self, max_requests: int = 45) -> bool:
        # Rotate before hitting rate limits
        return self.request_count >= max_requests
    
    def rotate_key(self):
        self.current_key_index = (self.current_key_index + 1) % len(self.keys)
        self.request_count = 0
        self.last_rotation = time.time()
        print(f"Rotated to key index: {self.current_key_index}")

# Usage in production code
key_manager = GeminiKeyManager()
client = genai.Client(api_key=key_manager.get_current_key())
```

### Function Calling and Advanced Features

**Function Calling Setup:**
```python
import json
from google import genai

# Define functions for AICleaner integration
def analyze_home_state(room: str, image_data: str) -> dict:
    """Analyze room state for cleaning recommendations"""
    return {"room": room, "cleanliness": "moderate", "recommendations": [...]}

def generate_cleaning_tasks(room: str, priority: str) -> list:
    """Generate specific cleaning tasks for room"""
    return [{"task": "vacuum", "priority": priority, "estimated_time": 15}]

# Configure function calling
tools = [
    genai.Tool(function_declarations=[
        genai.FunctionDeclaration(
            name="analyze_home_state",
            description="Analyze room state for cleaning recommendations",
            parameters=genai.Schema(
                type=genai.Type.OBJECT,
                properties={
                    "room": genai.Schema(type=genai.Type.STRING),
                    "image_data": genai.Schema(type=genai.Type.STRING)
                },
                required=["room", "image_data"]
            )
        )
    ])
]

# Use with function calling
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents="Analyze the kitchen and generate cleaning tasks",
    tools=tools,
    config=genai.GenerateContentConfig(
        function_calling_config=genai.FunctionCallingConfig(
            mode=genai.FunctionCallingConfig.Mode.AUTO
        )
    )
)
```

### Production Usage Patterns

**Task-Specific Model Selection:**
```python
class GeminiTaskRouter:
    @staticmethod
    def get_optimal_model(task_type: str, complexity: str) -> tuple[str, dict]:
        """Get optimal model and config for specific tasks"""
        
        configs = {
            "architectural_review": {
                "model": "gemini-2.5-pro",
                "thinking_budget": 16384,
                "temperature": 0.1
            },
            "code_generation": {
                "model": "gemini-2.5-pro", 
                "thinking_budget": 8192,
                "temperature": 0.2
            },
            "quick_analysis": {
                "model": "gemini-2.5-flash",
                "thinking_budget": 2048,
                "temperature": 0.3
            },
            "bulk_processing": {
                "model": "gemini-2.5-flash-lite",
                "thinking_budget": 512,
                "temperature": 0.1
            }
        }
        
        config = configs.get(task_type, configs["quick_analysis"])
        return config["model"], {
            "thinking_config": genai.ThinkingConfig(budget=config["thinking_budget"]),
            "generation_config": genai.GenerationConfig(temperature=config["temperature"])
        }

# Usage example
model, config = GeminiTaskRouter.get_optimal_model("architectural_review", "high")
response = client.models.generate_content(
    model=model,
    contents="Review this system architecture...",
    config=genai.GenerateContentConfig(**config)
)
```

### Cost Optimization Strategies

**1. Thinking Budget Optimization:**
- **Disable thinking** for simple tasks (budget=0)
- **Use moderate budgets** for standard tasks (2048-4096 tokens)
- **Reserve high budgets** for complex reasoning only (8192+ tokens)

**2. Model Selection Optimization:**
- **Use Flash-Lite** for high-volume, simple tasks
- **Use Flash** for general-purpose processing
- **Reserve Pro** for complex reasoning and critical decisions

**3. Batch Processing:**
- **Leverage batch mode** for 50% token discount on large datasets
- **Group similar tasks** to minimize context switching overhead

### Error Handling and Resilience

```python
import asyncio
from typing import Optional

class ResilientGeminiClient:
    def __init__(self, key_manager: GeminiKeyManager):
        self.key_manager = key_manager
        self.client = None
        self._update_client()
    
    def _update_client(self):
        self.client = genai.Client(api_key=self.key_manager.get_current_key())
    
    async def generate_with_retry(self, model: str, prompt: str, max_retries: int = 3) -> Optional[str]:
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt
                )
                
                self.key_manager.request_count += 1
                return response.text
                
            except Exception as e:
                if "rate limit" in str(e).lower() or "quota" in str(e).lower():
                    if self.key_manager.should_rotate():
                        self.key_manager.rotate_key()
                        self._update_client()
                        continue
                
                if attempt == max_retries - 1:
                    raise e
                    
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return None
```

### Monitoring and Analytics

**Track Usage Metrics:**
```python
class GeminiUsageTracker:
    def __init__(self):
        self.daily_requests = 0
        self.thinking_tokens_used = 0
        self.output_tokens_used = 0
        self.cost_estimate = 0.0
    
    def log_request(self, model: str, response):
        self.daily_requests += 1
        
        # Track thinking tokens if available
        if hasattr(response, 'usage_metadata'):
            thinking_tokens = getattr(response.usage_metadata, 'thoughts_token_count', 0)
            output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)
            
            self.thinking_tokens_used += thinking_tokens
            self.output_tokens_used += output_tokens
            
            # Estimate cost (example rates)
            self.cost_estimate += (thinking_tokens + output_tokens) * 0.000001
    
    def get_daily_summary(self) -> dict:
        return {
            "requests": self.daily_requests,
            "thinking_tokens": self.thinking_tokens_used,
            "output_tokens": self.output_tokens_used,
            "estimated_cost": self.cost_estimate
        }
```

### Documentation References
- **Quickstart Guide:** https://ai.google.dev/gemini-api/docs/quickstart?lang=python
- **Model Documentation:** https://ai.google.dev/gemini-api/docs/models
- **Thinking Guide:** https://ai.google.dev/gemini-api/docs/thinking
- **Rate Limits:** https://ai.google.dev/gemini-api/docs/rate-limits
- **Function Calling:** https://ai.google.dev/gemini-api/docs/function-calling