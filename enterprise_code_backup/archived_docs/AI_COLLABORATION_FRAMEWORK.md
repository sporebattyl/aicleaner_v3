# AI-to-AI Collaboration Framework for AICleaner v3

## Executive Summary

This framework defines the operational protocols for enhanced collaboration between Claude and Gemini using the `gemini-cli` tool. It shifts from a "chat about code" model to a "tool-driven code interaction" model, leveraging Gemini's superior context window and Claude's implementation and orchestration capabilities.

## Core Principles

1. **Proactive Tooling**: Use gemini-cli as an active tool for codebase analysis and modification
2. **Structured Handoffs**: Standardized artifact formats for reliable AI-to-AI communication
3. **Context Scoping**: Intelligent context management for large codebases
4. **Quality Gates**: Automated verification and validation standards
5. **Security-First**: Cryptographic signing and audit trails for all interactions

## 1. Operational Protocols

### 1.1 Task Initiation Pattern

**Claude's Responsibility:** Initiate tasks with precise gemini-cli commands that scope context and define expected outputs.

**Command Structure:**
```bash
gemini --context "session_name" \
       --context-include 'relevant/path/**' \
       --context-exclude '**/__pycache__/**' \
       --thinking-budget high \
       "Task description with specific deliverables"
```

### 1.2 Handoff Artifact Standard

**Gemini's Responsibility:** Respond with structured artifacts following this JSON schema:

```json
{
  "session_id": "phase4a_ha_integration_001",
  "task_type": "architectural_implementation|security_audit|performance_review|refactoring",
  "timestamp": "2025-01-17T15:30:00Z",
  "summary": "Brief description of the changes",
  "risk_level": "low|medium|high|critical",
  "estimated_complexity": "trivial|low|medium|high|critical",
  "affected_modules": ["module1", "module2"],
  "dependencies": ["prerequisite_task_ids"],
  "changes": [
    {
      "file_path": "relative/path/to/file.py",
      "operation": "create|modify|delete",
      "content": "full_file_content_if_create",
      "diff": "unified_diff_content",
      "rationale": "explanation_of_changes"
    }
  ],
  "verification": {
    "unit_tests": ["pytest commands"],
    "integration_tests": ["integration test commands"],
    "security_checks": ["security validation commands"],
    "performance_tests": ["performance test commands"],
    "manual_verification": ["manual steps if needed"]
  },
  "rollback_strategy": "git revert {commit_hash} || specific rollback steps",
  "documentation_updates": ["files_to_update"],
  "security_considerations": ["security implications and mitigations"]
}
```

### 1.3 Response Validation Pattern

**Claude's Responsibility:** Validate artifacts before implementation:

1. **Schema Validation**: Ensure artifact follows required structure
2. **Security Review**: Check for security implications
3. **Dependency Validation**: Verify all dependencies are met
4. **Test Coverage**: Ensure adequate test coverage
5. **Documentation**: Verify documentation updates are included

## 2. Context Management Strategy

### 2.1 Context Zones for AICleaner v3

```yaml
context_zones:
  security:
    includes: 
      - "addons/aicleaner_v3/security/**"
      - "addons/aicleaner_v3/core/config_schema.py"
      - "addons/aicleaner_v3/core/config_schema_validator.py"
    excludes:
      - "**/__pycache__/**"
      - "**/*.pyc"
      - "**/test_*.py"
    
  ha_integration:
    includes:
      - "addons/aicleaner_v3/ha_integration/**"
      - "addons/aicleaner_v3/integrations/**"
      - "addons/aicleaner_v3/zones/ha_integration.py"
    excludes:
      - "**/test_*.py"
      - "**/__pycache__/**"
    
  ai_providers:
    includes:
      - "addons/aicleaner_v3/ai/**"
    excludes:
      - "addons/aicleaner_v3/ai/test_data/**"
      - "**/__pycache__/**"
    
  core_systems:
    includes:
      - "addons/aicleaner_v3/core/**"
    excludes:
      - "**/__pycache__/**"
      - "**/test_*.py"
    
  zone_management:
    includes:
      - "addons/aicleaner_v3/zones/**"
    excludes:
      - "**/__pycache__/**"
      - "**/test_*.py"
```

### 2.2 Session Management

**Session Lifecycle:**
- **Start New Session**: For new features or major refactoring
- **Continue Session**: For related changes or iterations
- **Session Cleanup**: Automatic cleanup after 24 hours of inactivity

**Session Naming Convention:**
`{phase}_{component}_{sequence_number}`

Examples:
- `phase4a_ha_integration_001`
- `phase4a_entity_manager_002`
- `security_audit_authentication_001`

## 3. Command Templates and Cookbooks (2025 Update)

### 3.1 Model-Optimized Template System

**Use task-appropriate models for maximum efficiency and availability:**

#### 🎯 **Complex Analysis Templates** (Use gemini-2.5-pro)

**Architectural Review Template:**
```bash
gemini --model gemini-2.5-pro \
       --context "arch_review_$(date +%Y%m%d)" \
       --context-include 'CLAUDE.md' \
       --context-include 'addons/aicleaner_v3/{target_module}/**' \
       --thinking-budget high \
       "Perform comprehensive architectural review of {target_module}:
       1. Generate PlantUML component diagram showing relationships
       2. Identify architectural issues, technical debt, and anti-patterns
       3. Propose specific improvements with detailed rationale
       4. Provide implementation roadmap with risk assessment
       5. Output as structured artifact with unified diffs
       6. Include performance and scalability considerations"
```

**Security Audit Template:**
```bash
gemini --model gemini-2.5-pro \
       --context "security_audit_$(date +%Y%m%d)" \
       --context-include 'addons/aicleaner_v3/security/**' \
       --context-include '{target_files}' \
       --thinking-budget high \
       "Perform comprehensive security audit based on OWASP Top 10:
       1. Identify potential vulnerabilities with CVE mappings
       2. Assess risk levels using CVSS scoring
       3. Propose specific mitigations with implementation details
       4. Provide security test cases and validation procedures
       5. Generate compliance report with remediation timeline
       6. Include threat modeling and attack surface analysis"
```

#### ⚡ **Balanced Development Templates** (Use gemini-2.5-flash)

**Implementation Design Template:**
```bash
gemini --model gemini-2.5-flash \
       --context "impl_design_$(date +%Y%m%d)" \
       --context-include 'addons/aicleaner_v3/{target_module}/**' \
       --context-include 'tests/**/{related_tests}' \
       --thinking-budget medium \
       "Design implementation for {feature_name}:
       1. Analyze existing code patterns and conventions
       2. Design component interfaces and data structures
       3. Propose implementation strategy with error handling
       4. Create test cases and validation procedures
       5. Provide step-by-step implementation guide
       6. Include integration points and dependencies"
```

**Code Review Template:**
```bash
gemini --model gemini-2.5-flash \
       --context "code_review_$(date +%Y%m%d)" \
       --context-include '{target_files}' \
       --context-include 'tests/**/{related_tests}' \
       --thinking-budget medium \
       "Review code changes for quality and best practices:
       1. Check adherence to coding standards and patterns
       2. Identify potential bugs, edge cases, and error scenarios
       3. Verify test coverage and quality
       4. Suggest performance optimizations
       5. Provide refactoring recommendations
       6. Validate security implications"
```

#### 🚀 **Quick Iteration Templates** (Use gemini-2.5-flash-lite)

**Bug Fix Analysis Template:**
```bash
gemini --model gemini-2.5-flash-lite \
       --context "bugfix_$(date +%Y%m%d)" \
       --context-include '{problematic_files}' \
       "Analyze and fix the reported bug:
       1. Reproduce the issue and identify root cause
       2. Propose minimal fix with clear rationale
       3. Ensure fix doesn't introduce regressions
       4. Provide test case to prevent recurrence
       5. Document the solution"
```

**Quick Validation Template:**
```bash
gemini --model gemini-2.0-flash-lite \
       --context "validation_$(date +%Y%m%d)" \
       "Quick validation of proposed approach:
       1. Assess technical feasibility
       2. Identify potential issues or concerns
       3. Suggest immediate improvements
       4. Confirm alignment with project goals"
```

#### 🔄 **High-Volume Templates** (Use gemini-2.5-flash-lite for sustained work)

**Batch Analysis Template:**
```bash
gemini --model gemini-2.5-flash-lite \
       --context "batch_analysis_$(date +%Y%m%d)" \
       --context-include '{file_pattern}' \
       "Analyze multiple files for consistent patterns:
       1. Identify common patterns and inconsistencies
       2. Suggest standardization opportunities
       3. Highlight potential issues across files
       4. Provide bulk refactoring recommendations"
```

**Documentation Generation Template:**
```bash
gemini --model gemini-2.5-flash-lite \
       --context "docs_gen_$(date +%Y%m%d)" \
       --context-include '{target_files}' \
       "Generate comprehensive documentation:
       1. Extract API interfaces and usage patterns
       2. Create clear examples and use cases
       3. Document configuration options
       4. Include troubleshooting guide"
```

### 3.2 Intelligent API Cycling Integration

**🚀 AUTOMATED INTELLIGENCE: Rate limits now handled completely automatically**

**No Manual Templates Needed:**
The intelligent API cycling system handles all rate limit management transparently. Claude simply uses Gemini without thinking about API keys or rate limits.

**Integration with Gemini-CLI:**
```bash
# Claude now automatically gets optimal API key + model
# The system handles all 20 combinations (4 keys × 5 models) transparently

gemini --context "{session_name}" \
       --context-include '{context_files}' \
       --intelligent-cycling true \
       "{task_description}"
```

**Python Integration Example:**
```python
from utils.gemini_model_selector import get_collaboration_strategy

# Get complete strategy with intelligent API cycling
strategy = get_collaboration_strategy(
    prompt="Implement authentication system",
    context_files=["auth/*.py", "config/*.yaml"],
    urgency="standard"
)

# Strategy includes optimal API key and model automatically
api_key = strategy["api_key"]        # Best available key
model = strategy["selected_model"]   # Optimal model for task
fallbacks = strategy["fallback_sequence"]  # Automatic fallback plan
```

**Transparent Operation:**
- ✅ **No rate limit management needed**: System handles everything
- ✅ **Optimal model selection**: Always gets best model for the task  
- ✅ **Intelligent fallback**: Tries all combinations automatically
- ✅ **Learning system**: Improves over time based on usage patterns
- ✅ **Health monitoring**: Real-time API key health tracking

### 3.3 Intelligent API Integration Functions

**Python API Functions (Recommended):**
```python
from utils.gemini_model_selector import (
    get_optimal_api_key_model,
    get_collaboration_strategy,
    record_gemini_success,
    record_gemini_failure,
    get_gemini_health_status
)

# Get optimal API key + model combination
api_key, model = get_optimal_api_key_model(
    prompt="Implement user authentication system",
    context_files=["auth/*.py", "config/*.yaml"],
    urgency="standard"  # immediate, standard, sustained, batch
)

# Get complete collaboration strategy
strategy = get_collaboration_strategy(
    prompt="Analyze security vulnerabilities in payment system",
    context_files=["payments/*.py", "security/*.yaml"],
    urgency="immediate",
    conversation_stage="initial",
    expected_duration="30min"
)

# After successful API call (for learning)
record_gemini_success(api_key, model)

# After failed API call (for learning) 
record_gemini_failure(api_key, model, error_type="rate_limit")

# Check API health status
health = get_gemini_health_status()
print(f"Available: {health['healthy_keys']}/{health['total_keys']} keys")
```

**Bash Integration (Optional):**
```bash
# For environments where Python integration isn't available
# The system automatically selects optimal combinations

gemini --context "session_$(date +%Y%m%d)" \
       --context-include 'relevant/files/**' \
       "Task description here"

# No need to specify model or API key - handled automatically
```

**Migration from Manual System:**
- ❌ **Old**: Manual key cycling with bash functions
- ✅ **New**: Automatic intelligent selection with learning
- ❌ **Old**: Static model selection based on rules  
- ✅ **New**: Dynamic selection based on real-time availability
- ❌ **Old**: No memory between sessions
- ✅ **New**: Persistent learning across all Claude sessions
```

### 3.4 Context Optimization for Different Models

**Model-Specific Context Management:**

```bash
# For gemini-2.5-pro (complex analysis)
gemini --model gemini-2.5-pro \
       --context-include 'CLAUDE.md' \
       --context-include 'AI_COLLABORATION_FRAMEWORK.md' \
       --context-include 'addons/aicleaner_v3/**/*.py' \
       --context-exclude '**/__pycache__/**' \
       --context-exclude '**/test_*.py' \
       --thinking-budget high

# For gemini-2.5-flash (balanced work)  
gemini --model gemini-2.5-flash \
       --context-include 'addons/aicleaner_v3/{specific_module}/**' \
       --context-include 'tests/{specific_module}/**' \
       --thinking-budget medium

# For lite models (quick/sustained work)
gemini --model gemini-2.5-flash-lite \
       --context-include '{specific_files}' \
       --thinking-budget low
```

### 3.5 Collaboration Session Management

**Session Types with Optimal Models:**

```bash
# Deep Analysis Session (use 2.5-pro)
gemini --model gemini-2.5-pro \
       --session-type "analysis" \
       --expected-duration "30min"

# Development Session (use 2.5-flash-lite for sustainability)  
gemini --model gemini-2.5-flash-lite \
       --session-type "development" \
       --expected-duration "2hours"

# Quick Iteration Session (use 2.0-flash-lite for speed)
gemini --model gemini-2.0-flash-lite \
       --session-type "iteration" \
       --expected-duration "15min"
```

## 4. Quality Assurance Framework

### 4.1 Verification Standards

**All handoff artifacts must include:**
1. **Unit Tests**: Comprehensive test coverage for new/modified code
2. **Integration Tests**: End-to-end testing of integrated components
3. **Security Tests**: Security validation and vulnerability scanning
4. **Performance Tests**: Performance benchmarking and regression testing
5. **Manual Verification**: Step-by-step manual testing procedures

### 4.2 Code Quality Gates

**Before implementation, Claude must verify:**
1. **Code Standards**: Follows established patterns and conventions
2. **Type Safety**: Complete type annotations and validation
3. **Error Handling**: Comprehensive error handling and logging
4. **Security**: No security vulnerabilities or exposure risks
5. **Performance**: No performance regressions
6. **Documentation**: Complete documentation updates

### 4.3 Testing Integration

**Integration with existing testing framework:**
```bash
# Run verification commands from artifact
source testing_env/bin/activate
cd /home/drewcifer/aicleaner_v3/addons/aicleaner_v3

# Execute verification commands
pytest tests/ha_integration/test_entity_manager.py -v
python tests/integration/test_ha_entities.py
python scripts/security_audit.py --module ha_integration
python benchmarks/entity_performance.py
```

## 5. Error Handling and Fallback Procedures

### 5.1 Common Error Scenarios

**API Unavailability:**
- **Symptom**: `gemini exited with code 1: [API Error: got status: UNAVAILABLE]`
- **Fallback**: Retry with exponential backoff, then switch to alternative approach
- **Recovery**: Continue with manual analysis and documentation

**Context Overflow:**
- **Symptom**: Context window exceeded
- **Fallback**: Reduce context scope using more specific includes/excludes
- **Recovery**: Break task into smaller, focused subtasks

**Session Timeout:**
- **Symptom**: Session context lost
- **Fallback**: Restart session with previous artifact as context
- **Recovery**: Use git history to reconstruct session state

### 5.2 Fallback Workflow

```bash
# Primary command fails
gemini --context "session_name" --context-include 'path/**' "task"

# Fallback 1: Reduce context scope
gemini --context "session_name" --context-include 'path/specific_file.py' "task"

# Fallback 2: Use alternative model
gemini --model gemini-2.0-flash-exp --context "session_name" "task"

# Fallback 3: Manual process
# Document the failure and proceed with manual analysis
```

## 6. Security Framework

### 6.1 Artifact Security

**Cryptographic Signing:**
- All handoff artifacts must be cryptographically signed
- Use GPG signatures for artifact verification
- Maintain audit trail of all signed artifacts

**Validation Pipeline:**
```bash
# Verify artifact signature
gpg --verify artifact.json.sig artifact.json

# Validate artifact schema
python scripts/validate_artifact.py artifact.json

# Security scan proposed changes
python scripts/security_scan.py --artifact artifact.json
```

### 6.2 Change Validation

**Automated Security Checks:**
1. **Static Analysis**: Automated code analysis for security vulnerabilities
2. **Dependency Scanning**: Check for vulnerable dependencies
3. **Configuration Validation**: Ensure secure configuration patterns
4. **Permission Analysis**: Verify appropriate access controls
5. **Data Flow Analysis**: Validate data handling and encryption

## 7. Integration with Existing Tools

### 7.1 MCP Server Integration

**Gemini-CLI with MCP Servers:**
```bash
# Use with filesystem MCP
gemini --context "session_name" \
       --mcp-server filesystem \
       --context-include 'addons/aicleaner_v3/**' \
       "task with file system access"

# Use with git MCP
gemini --context "session_name" \
       --mcp-server git \
       "analyze git history for patterns"
```

### 7.2 Sandbox Testing Integration

**Integration with testing framework:**
```bash
# Run proposed changes in sandbox
python tests/sandbox_execution_wrapper.py --artifact artifact.json --validate

# Test in HA environment
python tests/real_ha_environment_tests.py --changes artifact.json
```

### 7.3 CI/CD Integration

**GitHub Actions Integration:**
```yaml
name: AI Collaboration Validation
on:
  push:
    paths:
      - 'ai_artifacts/**'
      
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Validate AI Artifacts
        run: |
          python scripts/validate_ai_artifacts.py
          python scripts/security_scan_artifacts.py
```

## 8. Implementation Roadmap

### 8.1 Phase 1: Foundation (This Session)

**Priority 1: Core Framework**
- [ ] Finalize handoff artifact schema
- [ ] Implement context zone configuration
- [ ] Create command templates for common tasks
- [ ] Add framework to CLAUDE.md

**Priority 2: Basic Integration**
- [ ] Test framework with Phase 4A HA integration task
- [ ] Validate artifact generation and processing
- [ ] Refine based on initial results

### 8.2 Phase 2: Enhanced Features (Next Session)

**Priority 1: Security and Quality**
- [ ] Implement cryptographic signing
- [ ] Add automated security validation
- [ ] Create comprehensive testing integration
- [ ] Add performance monitoring

**Priority 2: Advanced Integration**
- [ ] Integrate with existing MCP servers
- [ ] Add CI/CD pipeline integration
- [ ] Create automated documentation generation
- [ ] Add monitoring and alerting

### 8.3 Phase 3: Production Optimization (Future)

**Priority 1: Optimization**
- [ ] Optimize context management strategies
- [ ] Add advanced error handling
- [ ] Implement session persistence
- [ ] Add collaborative workflow analytics

**Priority 2: Expansion**
- [ ] Support for additional AI models
- [ ] Multi-agent collaboration patterns
- [ ] Advanced security features
- [ ] Performance optimization tools

## 9. Monitoring and Analytics

### 9.1 Collaboration Metrics

**Key Performance Indicators:**
- Artifact generation success rate
- Implementation accuracy rate
- Security vulnerability detection rate
- Performance improvement metrics
- Time to implementation

**Monitoring Dashboard:**
```python
class CollaborationMetrics:
    def track_artifact_generation(self, session_id: str, success: bool):
        # Track artifact generation metrics
        pass
    
    def track_implementation_success(self, artifact_id: str, success: bool):
        # Track implementation success rates
        pass
    
    def track_security_findings(self, artifact_id: str, findings: List[SecurityFinding]):
        # Track security analysis results
        pass
```

### 9.2 Quality Metrics

**Code Quality Tracking:**
- Code complexity reduction
- Test coverage improvement
- Documentation completeness
- Security compliance scores
- Performance benchmarks

## 10. Getting Started

### 10.1 Quick Start Checklist

**Prerequisites:**
- [ ] gemini-cli installed and configured
- [ ] API keys properly configured with rotation
- [ ] MCP servers configured and running
- [ ] Testing environment set up

**First Collaboration:**
1. Choose a context zone appropriate for your task
2. Use a command template from the cookbook
3. Validate the generated artifact
4. Implement and test the changes
5. Document the results and lessons learned

### 10.2 Example First Task

**Phase 4A HA Integration - Entity Manager:**
```bash
# Initialize session
gemini --context "phase4a_ha_integration_001" \
       --context-include 'CLAUDE.md' \
       --context-include 'addons/aicleaner_v3/ha_integration/**' \
       --context-include 'addons/aicleaner_v3/integrations/**' \
       --thinking-budget high \
       "Design and implement centralized entity manager for HA integration:
       1. Analyze existing entity management patterns
       2. Design unified entity manager architecture
       3. Implement centralized entity registration system
       4. Add entity discovery capabilities
       5. Provide comprehensive test suite and documentation"
```

## Conclusion

This AI-to-AI collaboration framework provides a structured, secure, and efficient approach to complex software development tasks. By leveraging the strengths of both Claude and Gemini through the gemini-cli tool, we can achieve higher quality outcomes with better maintainability and security.

The framework is designed to be iterative and adaptive, allowing for continuous improvement based on real-world usage and feedback. Regular reviews and updates will ensure the framework remains effective and aligned with project goals.

---

**Next Steps:**
1. Integrate this framework into CLAUDE.md
2. Test with the Phase 4A HA integration implementation
3. Refine based on initial results
4. Expand to additional project phases
5. Establish monitoring and continuous improvement processes