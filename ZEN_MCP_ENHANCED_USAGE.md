# Enhanced Zen MCP Client - Multi-API Key Usage Guide

## Overview
The enhanced zen MCP client now supports multiple API keys with intelligent quota cycling, maximizing your total capacity across 3 API keys while maintaining model priority and thinking mode optimization.

## Multi-API Key Architecture

### Total Capacity (3 API Keys)
- **Gemini 2.5 Pro**: 300 requests/day total (100 × 3 keys)
- **Gemini 2.5 Flash**: 750 requests/day total (250 × 3 keys)  
- **Gemini 2.5 Flash-Lite**: 3,000 requests/day total (1,000 × 3 keys)
- **Grand Total**: 4,050 requests/day across all models

### Intelligent Fallback Strategy
1. **Try 2.5 Pro on Key 1** → **Key 2** → **Key 3**
2. **Try 2.5 Flash on Key 1** → **Key 2** → **Key 3**
3. **Try 2.5 Flash-Lite on Key 1** → **Key 2** → **Key 3**

### Per-Key Limits
- **Daily**: 100/250/1000 requests per key per model
- **Rate**: 5/10/15 RPM per key per model
- **Tokens**: 250,000 TPM per key per model

## Enhanced Features

### Thinking Mode Integration
- **Gemini 2.5 Pro**: Dynamic thinking mode (-1 budget) for complex analysis
- **Gemini 2.5 Flash**: Medium thinking (12,288 tokens) for collaborative review
- **Gemini 2.5 Flash-Lite**: Minimal thinking (2,048 tokens) for efficiency
- **Thinking Insights**: Access to reasoning process when available

### Automatic Fallback
- Client tries models in priority order
- Automatically switches when rate limits hit
- Graceful degradation with status reporting

### Quota Tracking
- Tracks daily usage per model
- Respects rate limits (RPM)
- Resets counters every 24 hours
- Shows quota status in responses

### Error Handling
- Rate limit detection (429 responses)
- Connection error recovery
- Clear status reporting

## Usage Examples

### Multi-Key Initialization
```python
from zen_gemini_client import ZenGeminiClient

# Method 1: Use default 3 API keys (built-in)
client = ZenGeminiClient()

# Method 2: Provide custom API keys
api_keys = ["key1", "key2", "key3"]
client = ZenGeminiClient(api_keys=api_keys)

# Method 3: Single key (backward compatibility)
client = ZenGeminiClient(primary_api_key="single-key")

# Check quota status across all keys
status = client.get_quota_status()
print(f"Recommended: {status['recommended_model']} on {status['recommended_api_key']}")
print(f"Total capacity: {status['total_api_keys']} API keys")

# Collaborate with intelligent key cycling
result = await client.collaborate_with_gemini("Your prompt here")
print(f"Used: {result['model_used']} on {result['api_key_used']}")
```

### Testing the System
```bash
cd "X:\aicleaner_v3"
python test_multikey_system.py  # Test multi-key functionality
python test_zen_enhanced.py     # Test thinking mode integration
```

### Current Status Check
```python
# Get detailed quota information
status = client.get_quota_status()
for model_name, info in status['quota_status'].items():
    print(f"{model_name}: {info['daily_used']}/{info['daily_limit']} requests used")
```

## Integration with AICleaner v3 Workflow

### Phase Enhancement Process
1. **Quota Check**: Verify available quota before starting
2. **Collaborative Review**: Use zen MCP for Gemini collaboration  
3. **Fallback Protection**: System automatically handles rate limits
4. **Progress Tracking**: Monitor quota usage across multiple prompts

### Example: Phase 2A Enhancement
```python
# Start with quota check
client = ZenGeminiClient(api_key)
status = client.get_quota_status()
print(f"Starting with {status['recommended_model']}")

# Enhance Phase 2A
enhanced_prompt = apply_90plus_template("PHASE_2A_AI_MODEL_OPTIMIZATION.md")
gemini_review = await client.collaborate_with_gemini(enhanced_prompt)

# Check quota after collaboration
print(f"Model used: {gemini_review['model_used']}")
print(f"Quota status: {gemini_review['quota_status']}")
```

## Best Practices

### Daily Quota Management
- Start with high-priority prompts when using 2.5 Pro
- Save complex reviews for when you have sufficient quota
- Monitor usage with `get_quota_status()` regularly

### Rate Limit Optimization
- Space out requests to respect RPM limits
- Use fallback models for testing and iteration
- Reserve 2.5 Pro for final validations

### Quality Workflow
1. **Draft with Flash-Lite**: Initial prompt development
2. **Refine with Flash**: Iterative improvements  
3. **Validate with Pro**: Final quality assurance

## Response Format

### Success Response
```json
{
  "success": true,
  "response": "Gemini's response text",
  "collaboration_established": true,
  "model_used": "gemini-2.5-pro",
  "thinking": {
    "thinking_available": true,
    "thinking_summary": "Summary of reasoning process...",
    "thinking_budget_used": -1
  },
  "quota_status": {
    "daily_used": 1,
    "daily_limit": 100
  }
}
```

### Quota Exhausted Response
```json
{
  "success": false,
  "error": "All models exhausted or rate limited. Please wait before retrying.",
  "collaboration_established": false,
  "quota_status": {
    "gemini-2.5-pro": {
      "daily_used": 100,
      "daily_limit": 100,
      "can_use": false
    }
  }
}
```

## Troubleshooting

### Rate Limits Hit
- Wait for rate limit window to reset (1 minute / RPM limit)
- Client automatically tries next available model
- Check `quota_status` for availability

### All Models Exhausted
- Wait for daily quota reset (24 hours)
- Use `get_quota_status()` to check reset times
- Plan workflow around quota limits

### API Errors
- Verify API key is valid
- Check internet connectivity
- Review Google AI Studio quotas

## Next Steps

With the enhanced zen MCP client ready, you can now:

1. **Continue Phase Enhancement**: Apply 90+ template to remaining 14 prompts
2. **Prioritize High-Impact**: Start with Phase 2A, 3C, 4A as planned
3. **Quota-Aware Workflow**: Use model fallback for efficient quota usage
4. **Quality Assurance**: Leverage 2.5 Pro for final validations

The system is optimized for your free tier quotas while maintaining access to the highest quality models when needed.