# Priority 2: Home Assistant Integration - REFINED

## Context

You are implementing Priority 2 of the Phase 3C.2 performance optimization refinement for AICleaner. This builds on the simplified SystemMonitor architecture from Priority 1 and focuses on creating user-friendly Home Assistant integration with intelligent health monitoring.

**Final Plan Integration:** This implementation incorporates specific decisions from our collaborative final plan, including representative prompt strategy, restart required messaging, error handling approach, and test environment requirements.

## Objective

Create intuitive Home Assistant integration that provides users with simple health monitoring, performance insights, and profile management without overwhelming them with technical complexity.

## Implementation Requirements

### Task 2.1: Implement Health Check Service & Score

**Action:** Create a `aicleaner.run_health_check` service in Home Assistant.

**Implementation Details:**
- **Service Name:** `aicleaner.run_health_check`
- **Duration:** 30-second comprehensive health check
- **Representative Prompt Strategy (Final Plan Decision):** Use the specific prompt "Analyze this room for cleaning tasks" for realistic performance testing (not a simple "Hello" test)

**Health Score Calculation (Exact Weighted Formula):**
```python
def calculate_health_score(latency_ms: float, error_rate: float, resource_pressure: float) -> int:
    """
    Calculate health score using exact weighted formula from final plan.
    
    Weights:
    - Average Inference Latency: 60% weight
    - Error Rate: 30% weight  
    - Resource Pressure: 10% weight
    """
    latency_score = max(0, 100 - (latency_ms / 10))  # 60% weight
    reliability_score = max(0, 100 - (error_rate * 100))  # 30% weight  
    resource_score = max(0, 100 - resource_pressure)  # 10% weight
    
    return int((latency_score * 0.6) + (reliability_score * 0.3) + (resource_score * 0.1))
```

**Health Check Implementation:**
```python
class HealthCheckService:
    HEALTH_CHECK_PROMPT = "Analyze this room for cleaning tasks"  # Final Plan Decision
    
    async def run_health_check(self) -> HealthResult:
        """Run comprehensive health check with representative testing."""
        
        # Test actual inference performance with representative prompt
        latency_samples = []
        error_count = 0
        total_requests = 5  # Run 5 test inferences
        
        for i in range(total_requests):
            try:
                start_time = time.time()
                # Use representative prompt for realistic testing
                await self._test_inference_with_prompt(self.HEALTH_CHECK_PROMPT)
                latency_samples.append((time.time() - start_time) * 1000)  # Convert to ms
            except Exception as e:
                error_count += 1
                self.logger.debug(f"Health check inference {i+1} failed: {e}")
        
        # Calculate metrics
        avg_latency_ms = statistics.mean(latency_samples) if latency_samples else 10000
        error_rate = error_count / total_requests
        resource_pressure = await self._get_resource_pressure()
        
        # Calculate health score using weighted formula
        health_score = self.calculate_health_score(avg_latency_ms, error_rate, resource_pressure)
        
        return HealthResult(
            score=health_score,
            status="good" if health_score > 80 else "fair" if health_score > 60 else "poor",
            avg_response_time_ms=int(avg_latency_ms),
            error_rate_percent=int(error_rate * 100),
            recommendations=self._generate_recommendations(health_score, avg_latency_ms, error_rate)
        )
```

**Error Handling Strategy (Final Plan Decision - Option A):**
- If health check fails completely (e.g., Ollama is down): Return score of 0 and trigger critical alert
- If partial failures occur: Include in error rate calculation
- Critical alert should be sent via Home Assistant persistent notification

### Task 2.2: Implement Home Assistant Sensors

**Action:** Create the necessary HA entities for health and performance monitoring.

**Required Sensors:**
```python
SENSORS = [
    {
        "name": "AICleaner Health Score",
        "unique_id": "aicleaner_health_score",
        "state_class": "measurement",
        "unit_of_measurement": "score",
        "icon": "mdi:heart-pulse",
        "device_class": None
    },
    {
        "name": "AICleaner Response Time", 
        "unique_id": "aicleaner_response_time",
        "state_class": "measurement",
        "unit_of_measurement": "ms",
        "icon": "mdi:timer",
        "device_class": None
    },
    {
        "name": "AICleaner Health Alert",
        "unique_id": "aicleaner_health_alert", 
        "device_class": "problem",
        "icon": "mdi:alert-circle"
    }
]
```

**Sensor Update Logic:**
- Health Score: Updated after each health check (0-100)
- Response Time: Updated with latest average response time in milliseconds
- Health Alert: Binary sensor (on = problem detected, off = system healthy)

### Task 2.3: Implement Performance Profile Service

**Action:** Create `aicleaner.apply_performance_profile` service with restart handling.

**Service Implementation:**
```python
# Service definition
SERVICE_APPLY_PROFILE = {
    "name": "apply_performance_profile",
    "description": "Apply a specific performance profile",
    "fields": {
        "profile": {
            "description": "Profile to apply",
            "selector": {
                "select": {
                    "options": [
                        "auto",
                        "resource_efficient", 
                        "balanced",
                        "maximum_performance"
                    ]
                }
            }
        }
    }
}
```

**Restart Required Messaging (Final Plan Decision - Option A):**
```python
async def apply_performance_profile(self, profile: str) -> Dict[str, Any]:
    """Apply performance profile with restart required messaging."""
    
    # Update configuration
    await self.optimization_profiles.apply_profile(profile)
    
    # Show restart required message (Final Plan Decision)
    restart_message = (
        f"Performance profile '{profile}' has been applied. "
        f"Restart AICleaner addon to activate the new settings."
    )
    
    # Send Home Assistant persistent notification
    await self._send_ha_notification(
        title="AICleaner Profile Updated",
        message=restart_message,
        notification_id="aicleaner_restart_required"
    )
    
    return {
        "success": True,
        "profile": profile,
        "restart_required": True,
        "message": restart_message
    }
```

### Task 2.4: Implement Alerting Strategy

**Action:** Create intelligent alerting that doesn't overwhelm users.

**Alert Thresholds:**
- **Health Score < 60:** Warning alert (yellow)
- **Health Score < 40:** Critical alert (red)
- **Complete system failure:** Emergency alert (red, persistent)

**Alert Frequency Management:**
- Maximum 1 alert per hour for the same issue
- Escalation only if problem persists for 24 hours
- Auto-resolve alerts when health score improves

**Alert Implementation:**
```python
class AlertManager:
    async def process_health_score(self, score: int):
        """Process health score and generate appropriate alerts."""
        
        if score == 0:
            # Critical system failure (Final Plan Decision)
            await self._send_critical_alert(
                "AICleaner system failure detected. Check addon logs and Ollama status."
            )
        elif score < 40:
            await self._send_alert("critical", f"Poor system performance (Score: {score})")
        elif score < 60:
            await self._send_alert("warning", f"Performance degradation detected (Score: {score})")
        else:
            # System healthy - clear any existing alerts
            await self._clear_alerts()
```

## Test Environment Requirements (Final Plan Decision)

**Mandatory:** Set up a test Home Assistant instance to validate integration:

1. **Test HA Instance Setup:**
   - Install Home Assistant in test environment
   - Install AICleaner addon in test instance
   - Configure with test Ollama instance

2. **Integration Testing:**
   - Verify all sensors appear correctly in HA
   - Test health check service execution
   - Test profile switching service
   - Validate alert notifications
   - Test sensor state updates

3. **Documentation Requirements:**
   - Include screenshots of working sensors in review document
   - Document service call examples
   - Provide automation examples for users

## Acceptance Criteria

### Functional Requirements
- [ ] Health check service completes in <30 seconds
- [ ] Health score calculation uses exact weighted formula (60/30/10)
- [ ] Representative prompt testing provides realistic performance data
- [ ] All sensors update correctly after health checks
- [ ] Profile switching service works with restart messaging
- [ ] Alerts are generated appropriately without spam

### User Experience Requirements
- [ ] Health check can be triggered manually from HA UI
- [ ] Sensor data is meaningful and actionable
- [ ] Profile switching is intuitive with clear restart guidance
- [ ] Alerts provide helpful information without overwhelming users
- [ ] All features work without requiring technical knowledge

### Technical Requirements
- [ ] Services are properly registered in Home Assistant
- [ ] Sensors follow HA best practices and conventions
- [ ] Error handling is comprehensive and user-friendly
- [ ] Performance overhead is minimal
- [ ] Integration works across HA versions

### Test Environment Requirements
- [ ] All features tested in actual Home Assistant instance
- [ ] Screenshots document working integration
- [ ] Service calls tested and documented
- [ ] Automation examples provided
- [ ] Integration validated across different HA configurations

## Success Metrics

1. **Usability:** Users can understand system health without technical knowledge
2. **Reliability:** Health checks provide accurate performance assessment
3. **Integration:** Seamless operation within Home Assistant ecosystem
4. **Performance:** No noticeable impact on HA or AICleaner performance
5. **User Satisfaction:** Beta feedback indicates improved monitoring experience

This implementation creates a bridge between AICleaner's technical capabilities and Home Assistant's user-friendly interface, making performance monitoring accessible to all users.
