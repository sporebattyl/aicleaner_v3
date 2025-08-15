# AICleaner V3 Fresh Start - Development Guide

## 🎯 Core Development Principles

### KISS + Power User Focus
- **Simple but powerful**: Avoid enterprise complexity unless it directly helps the single power user
- **Direct solutions**: Prefer straightforward implementations over abstract patterns
- **User control**: Give the power user complete control over privacy, performance, and behavior
- **Real-world optimization**: Optimize for actual hardware (GMKTEC K8Plus: Ryzen 8845HS + 64GB RAM + iGPU)

### PDCA-Driven Development
All development follows **Plan → Do → Check → Act** methodology:

#### Plan Phase
- Define clear success criteria before coding
- Design component interfaces and data flows
- Identify testing requirements and dependencies
- Document expected behavior and edge cases

#### Do Phase  
- Implement following established patterns
- Write comprehensive error handling from start
- Create real test cases alongside implementation
- Use type hints and docstrings throughout

#### Check Phase
- Test with real dependencies (Gemini API, Ollama, HA)
- Validate against success criteria from Plan phase
- Performance testing on target hardware
- Integration testing with live services

#### Act Phase
- Refactor based on test results
- Document lessons learned
- Update patterns and templates for future use
- Commit only when Check phase passes completely

### Real Testing Only
- **NO MOCK TESTING** unless explicitly justified and pre-approved
- Code must adapt to tests, not tests to code
- Use real Gemini API, real Ollama instances, real HA integrations
- If tests are failing, fix the code - don't modify tests

## 🏗️ Architecture Patterns

### Provider Pattern Implementation
```python
# Always implement the full interface
class NewProvider(LLMProvider):
    async def analyze(self, image: bytes, prompt: str, **kwargs) -> AnalysisResult:
        # PLAN: Validate inputs and setup request
        # DO: Execute analysis with retry logic  
        # CHECK: Validate response format and quality
        # ACT: Return structured result or raise clear error
        pass
    
    async def health_check(self) -> ProviderHealth:
        # Always implement comprehensive health checking
        pass
    
    def get_capabilities(self) -> List[ProviderCapability]:
        # Accurately report what this provider can do
        pass
```

### Error Handling Patterns
```python
# Always use this error handling pattern
try:
    # PLAN: Log what we're attempting
    logger.info(f"Starting {operation_name} with {parameters}")
    
    # DO: Execute with proper timeout and retries
    result = await execute_operation()
    
    # CHECK: Validate result quality
    if not self._validate_result(result):
        raise ValueError(f"Invalid result from {operation_name}")
    
    # ACT: Log success and return
    logger.info(f"✓ {operation_name} completed successfully")
    return result
    
except SpecificException as e:
    # Handle specific exceptions with user-friendly messages
    logger.error(f"❌ {operation_name} failed: {e}")
    raise UserFriendlyException(f"Operation failed: {user_message}")
except Exception as e:
    # Catch-all with full context
    logger.error(f"❌ Unexpected error in {operation_name}: {e}")
    raise
```

### Configuration Validation
```python
# Always use Pydantic for configuration
class ComponentConfig(BaseModel):
    required_field: str = Field(..., description="Required field")
    optional_field: int = Field(default=42, ge=1, le=100)
    
    @validator('required_field')
    def validate_required(cls, v):
        if not v or not v.strip():
            raise ValueError('Required field cannot be empty')
        return v
    
    @root_validator  
    def validate_combination(cls, values):
        # Validate field combinations make sense
        return values
```

## 🎨 Visual Annotation Development Patterns

### Bounding Box Processing
```python
async def create_visual_annotations(self, tasks: List[Task], image: bytes) -> bytes:
    """
    PLAN: Parse tasks with annotations, validate image format
    DO: Draw bounding boxes and labels using PIL/OpenCV  
    CHECK: Verify annotations are visible and correctly positioned
    ACT: Return annotated image or raise clear error
    """
    
    # PLAN: Validate inputs
    if not tasks or not image:
        return image  # Return original if nothing to annotate
    
    annotated_tasks = [t for t in tasks if t.annotation is not None]
    if not annotated_tasks:
        return image
    
    # DO: Create annotations
    try:
        annotated = await self._draw_annotations(image, annotated_tasks)
    except Exception as e:
        logger.error(f"Annotation failed: {e}")
        return image  # Return original on failure
    
    # CHECK: Validate result
    if len(annotated) < len(image):
        logger.warning("Annotated image smaller than original")
    
    # ACT: Return result
    return annotated

def _clamp_bbox_to_image(self, bbox: BoundingBox, image_size: Tuple[int, int]) -> BoundingBox:
    """Always clamp bounding boxes to prevent drawing errors"""
    width, height = image_size
    return BoundingBox(
        x1=max(0, min(bbox.x1, width - 1)),
        y1=max(0, min(bbox.y1, height - 1)),
        x2=max(bbox.x1 + 10, min(bbox.x2, width)),   # Ensure minimum size
        y2=max(bbox.y1 + 10, min(bbox.y2, height))
    )
```

### Prompt Engineering for Visual Grounding
```python
def create_visual_grounding_prompt(self, base_prompt: str) -> str:
    """Create prompts that encourage bounding box responses"""
    return f"""{base_prompt}

CRITICAL: Respond with valid JSON in this exact format:
{{
  "tasks": [
    {{
      "description": "Specific, actionable cleaning task",
      "priority": 1,
      "confidence": 0.95,
      "estimated_duration": "5 minutes",
      "bounding_box": {{
        "x1": 100, "y1": 150, "x2": 300, "y2": 400
      }}
    }}
  ]
}}

REQUIREMENTS:
- Priority: 1=High, 2=Medium, 3=Low  
- Bounding box: (x1,y1)=top-left, (x2,y2)=bottom-right
- Be specific: "wipe coffee spill on counter" not "clean counter"
- Provide coordinates for ALL tasks when possible
- Only identify actual cleaning tasks
"""
```

## 🔒 Privacy Processing Patterns

### Level 2 Sanitization Implementation
```python
async def sanitize_image(self, image: bytes, level: PrivacyLevel) -> SanitizationResult:
    """
    PLAN: Determine processing requirements, validate inputs
    DO: Apply appropriate privacy processing
    CHECK: Verify privacy protection is adequate
    ACT: Return sanitized image with processing metadata
    """
    
    if level == PrivacyLevel.LEVEL_1_RAW:
        # No processing needed
        return SanitizationResult(
            sanitized_image=image,
            metadata={'processing': 'none'},
            processing_time=0.0
        )
    
    elif level == PrivacyLevel.LEVEL_2_SANITIZED:
        # PLAN: Setup OpenCV processing
        nparr = np.frombuffer(image, np.uint8)
        cv_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # DO: Apply face and text blurring
        sanitized = await self._apply_sanitization(cv_image)
        
        # CHECK: Verify blurring was applied
        if not self._verify_sanitization_quality(cv_image, sanitized):
            logger.warning("Sanitization quality check failed")
        
        # ACT: Return processed result
        _, buffer = cv2.imencode('.jpg', sanitized)
        return SanitizationResult(
            sanitized_image=buffer.tobytes(),
            metadata={'faces_blurred': len(detected_faces)},
            processing_time=processing_time
        )
```

### Privacy Level Selection Logic
```python
def determine_optimal_privacy_level(
    self, 
    user_preference: PrivacyLevel,
    camera_location: str,
    provider_health: Dict[str, ProviderHealth]
) -> PrivacyLevel:
    """
    PLAN: Analyze user preference, context, and provider availability
    DO: Apply decision logic with clear reasoning
    CHECK: Validate selected level is feasible
    ACT: Return level with reasoning logged
    """
    
    # Honor explicit user choice
    if user_preference != self.config.privacy.default_level:
        logger.info(f"Using user-specified privacy level: {user_preference.value}")
        return user_preference
    
    # Apply contextual logic
    if camera_location in ['bedroom', 'bathroom', 'nursery']:
        level = max(user_preference, PrivacyLevel.LEVEL_2_SANITIZED)
        logger.info(f"Upgrading privacy for sensitive location: {camera_location}")
        return level
    
    # Check provider availability for Level 4
    if user_preference == PrivacyLevel.LEVEL_4_LOCAL:
        ollama_providers = [p for p in provider_health.keys() if 'ollama' in p.lower()]
        if not any(provider_health[p].status == ProviderStatus.HEALTHY for p in ollama_providers):
            logger.warning("Level 4 requested but no healthy Ollama providers, falling back to Level 2")
            return PrivacyLevel.LEVEL_2_SANITIZED
    
    return user_preference
```

## 🔄 PDCA Orchestration Patterns

### Request Processing Flow
```python
async def process_analysis_request(self, request: AnalysisRequest) -> OrchestratorResult:
    """Complete PDCA cycle for analysis request"""
    
    # PLAN: Analyze request and select strategy
    plan = await self._pdca_plan(request)
    logger.info(f"PLAN: Using {plan['selected_provider']} with privacy level {request.privacy_level.value}")
    
    # DO: Execute the plan  
    do_result = await self._pdca_do(request, plan)
    logger.info(f"DO: Generated {len(do_result['analysis_result'].tasks)} tasks")
    
    # CHECK: Validate results quality
    check_result = await self._pdca_check(do_result, request)
    if not check_result['validation']['overall_valid']:
        logger.warning("CHECK: Validation failed, attempting fallback")
        # Fallback logic here
    
    # ACT: Finalize and return results
    final_result = await self._pdca_act(check_result, start_time)
    logger.info(f"ACT: Completed in {final_result.total_processing_time:.2f}s")
    
    return final_result
```

### Health Monitoring Integration
```python
async def monitor_provider_health(self) -> None:
    """Continuous health monitoring with PDCA"""
    
    while self.running:
        # PLAN: Determine which providers to check
        providers_to_check = self._get_active_providers()
        
        # DO: Execute health checks in parallel
        health_tasks = [
            provider.health_check() 
            for provider in providers_to_check
        ]
        health_results = await asyncio.gather(*health_tasks, return_exceptions=True)
        
        # CHECK: Analyze health status changes
        status_changes = self._detect_status_changes(health_results)
        
        # ACT: Update routing and notify if needed
        if status_changes:
            await self._update_provider_routing(status_changes)
            await self._notify_health_changes(status_changes)
        
        await asyncio.sleep(self.health_check_interval)
```

## 🧪 Real Testing Patterns

### Provider Integration Tests
```python
async def test_gemini_provider_real_api():
    """Test Gemini provider with real API - NO MOCKS"""
    
    # PLAN: Setup real test environment
    config = GeminiConfig(
        api_key=os.getenv('GEMINI_TEST_API_KEY'),  # Real API key required
        model="gemini-pro-vision"
    )
    provider = GeminiProvider("test_gemini", config.dict())
    
    # Use real test image
    with open('tests/test_images/kitchen_mess.jpg', 'rb') as f:
        test_image = f.read()
    
    # DO: Execute real analysis
    result = await provider.analyze(
        image=test_image,
        prompt="Identify cleaning tasks in this kitchen"
    )
    
    # CHECK: Validate real response
    assert len(result.tasks) > 0, "Should find at least one task"
    assert all(task.description.strip() for task in result.tasks), "All tasks should have descriptions"
    assert result.model_used == "gemini-pro-vision", "Should report correct model"
    
    # ACT: Cleanup
    await provider.close()
```

### Privacy Engine Tests
```python  
async def test_face_blurring_real_images():
    """Test face blurring with real face images"""
    
    engine = PrivacyEngine({'face_blur_strength': 99})
    
    # Load real image with faces (test dataset)
    with open('tests/test_images/family_kitchen.jpg', 'rb') as f:
        original_image = f.read()
    
    # DO: Apply sanitization
    result = await engine.process_image(
        original_image, 
        PrivacyLevel.LEVEL_2_SANITIZED
    )
    
    # CHECK: Verify faces were detected and blurred
    assert len(result.objects_detected) > 0, "Should detect faces"
    assert any(obj.type == 'face' for obj in result.objects_detected), "Should detect face type"
    
    # Visual verification: Save images for manual inspection
    with open('tests/outputs/original.jpg', 'wb') as f:
        f.write(original_image)
    with open('tests/outputs/sanitized.jpg', 'wb') as f:
        f.write(result.sanitized_image)
    
    print(f"Detected {len(result.objects_detected)} objects for sanitization")
```

### Integration Test with Real HA
```python
async def test_full_workflow_with_real_ha():
    """End-to-end test with real Home Assistant instance"""
    
    # PLAN: Setup requires running HA instance
    app = AICleanerApplication('tests/real_config.yaml')
    await app.initialize()
    
    # Use real camera entity from HA
    camera_entity = 'camera.kitchen'  # Must exist in test HA instance
    
    # DO: Execute full analysis workflow
    with open('tests/test_images/messy_kitchen.jpg', 'rb') as f:
        test_image = f.read()
    
    result = await app.analyze_image(
        image_bytes=test_image,
        privacy_level=PrivacyLevel.LEVEL_2_SANITIZED
    )
    
    # CHECK: Validate complete result
    assert result['success'], f"Analysis failed: {result.get('error')}"
    assert len(result['tasks']) > 0, "Should generate tasks"
    assert result['annotated_image_base64'] is not None, "Should have annotations"
    
    # ACT: Cleanup
    await app.shutdown()
```

## 🛠️ Component Development Guidelines

### Adding New Providers
1. **PLAN**: Define capabilities and configuration schema
2. **DO**: Implement full LLMProvider interface
3. **CHECK**: Test with real provider service/API
4. **ACT**: Add to factory and registry patterns

### Extending Privacy Levels
1. **PLAN**: Define new level requirements and tradeoffs
2. **DO**: Implement in PrivacyEngine with comprehensive validation
3. **CHECK**: Test privacy protection effectiveness
4. **ACT**: Update documentation and configuration schema

### Adding New Annotation Features
1. **PLAN**: Define visual requirements and user experience
2. **DO**: Implement in AnnotationEngine with proper bounds checking
3. **CHECK**: Test with various image sizes and annotation densities
4. **ACT**: Add configuration options and documentation

## 🚨 Anti-Patterns to Avoid

### ❌ Don't Do This
```python
# Don't use mocks unless explicitly justified
@patch('providers.gemini_provider.aiohttp')
def test_gemini_provider_mock():
    # This breaks our "real testing only" principle
    pass

# Don't modify tests to make them pass
def test_analysis_accuracy():
    result = analyze_image(test_image)
    assert len(result.tasks) >= 1  # ❌ Lowered from >= 3 because tests failing

# Don't ignore error conditions
def process_image(image):
    try:
        return ai_provider.analyze(image)
    except Exception:
        return []  # ❌ Silent failure, user won't know what happened
```

### ✅ Do This Instead
```python
# Use real dependencies
async def test_gemini_provider_real():
    provider = GeminiProvider(real_config)
    result = await provider.analyze(real_image, prompt)
    # Fix provider if this fails, don't lower standards

# Fix code when tests fail
def test_analysis_accuracy():
    result = analyze_image(test_image) 
    assert len(result.tasks) >= 3, "Should find at least 3 cleaning tasks"
    # If this fails, improve the analysis logic

# Handle errors properly
def process_image(image):
    try:
        return ai_provider.analyze(image)
    except NetworkError as e:
        logger.error(f"Network failed: {e}")
        raise UserFriendlyError("Unable to reach AI service, please check connection")
    except ValidationError as e:
        logger.error(f"Invalid response: {e}")
        raise UserFriendlyError("Received invalid response from AI service")
```

## 📚 Development Workflow

### Starting New Feature
1. **Plan**: Create detailed design document with success criteria
2. **Setup**: Create feature branch with descriptive name
3. **Implement**: Follow PDCA patterns with real testing
4. **Validate**: Test with target hardware and real dependencies
5. **Document**: Update relevant documentation files
6. **Review**: Self-review using patterns and anti-patterns guide
7. **Integrate**: Only merge when all tests pass on real dependencies

### Bug Fixes
1. **Reproduce**: Create failing test that reproduces the bug with real dependencies
2. **Analyze**: Use PDCA to understand root cause
3. **Fix**: Implement fix without modifying the failing test
4. **Validate**: Ensure test passes and no regressions introduced
5. **Document**: Update documentation if bug revealed knowledge gap

### Performance Optimization
1. **Measure**: Use real hardware (GMKTEC K8Plus) for benchmarks
2. **Optimize**: Focus on critical path identified by measurements
3. **Validate**: Ensure optimization doesn't break functionality
4. **Document**: Update performance expectations and configuration

## 🎯 Success Metrics

### Code Quality
- All tests pass with real dependencies
- Type hints on all public interfaces
- Comprehensive error handling with user-friendly messages
- Clear logging at appropriate levels

### Performance
- Level 1: < 3 seconds processing time
- Level 2: < 5 seconds processing time  
- Level 3: < 4 seconds processing time
- Level 4: < 30 seconds on target hardware

### Reliability
- Graceful fallback when providers are unavailable
- Clear error messages for configuration issues
- Automatic recovery from transient failures
- No silent failures or data loss

Following these patterns ensures AICleaner V3 maintains its architectural integrity while providing a reliable, performant, and privacy-respectful experience for power users.