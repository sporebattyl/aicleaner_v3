# Master AICleaner v3 Implementation Prompt Template - 100/100 Readiness

## Design Principles
- **TDD First**: Always use Test-Driven Development with explicit AAA (Arrange-Act-Assert) pattern
- **AAA Testing**: Structure all tests with clear Arrange-Act-Assert sections for maintainability
- **Component-Based Design**: Create modular, loosely-coupled components with well-defined interface contracts
- **Validation Robustness**: Empower senior developers with strategic guidance and comprehensive validation

## Enhanced Template Structure

```markdown
# [Phase/Task Name]: [Brief Description]

## 1. Context & Objective
- **Primary Goal**: [1-2 sentences describing the main objective]
- **Phase Context**: [How this fits in the overall AICleaner v3 improvement plan]
- **Success Impact**: [What successful completion enables for future phases]

## 2. Implementation Requirements

### Core Tasks
1. **[Task 1 Name]**
   - **Action**: [Specific action required with validation focus]
   - **Details**: [Key implementation points with TDD approach and component contracts]
   - **Validation**: [How to verify completion with specific tests using AAA pattern]

2. **[Task 2 Name]**
   - **Action**: [Specific action required]
   - **Details**: [Key implementation points with interface stability requirements]
   - **Validation**: [How to verify completion with integration tests]

### Technical Specifications
- **Required Tools**: [List essential tools and testing frameworks]
- **Key Configurations**: [Critical Home Assistant config changes]
- **Integration Points**: [HA API, MQTT, external service touchpoints]
- **Component Contracts**: [API interfaces between components with stability requirements]
- **Testing Strategy**: [Unit, integration, and system test requirements with AAA examples]

### Security Considerations
- **Input Validation**: [Specific validation requirements for user inputs]
- **API Security**: [Secure communication practices for external services]
- **Data Protection**: [User data handling and storage security]
- **HA Security Compliance**: [Link to specific HA security documentation sections]

## 3. Implementation Validation Framework

### Self-Assessment Checklist (5-7 Items)
- [ ] [Specific, measurable validation criterion 1]
- [ ] [Specific, measurable validation criterion 2]
- [ ] [Integration test passes with other components]
- [ ] [Performance baseline established and documented]
- [ ] [Security considerations addressed and validated]
- [ ] [Component interface contracts clearly defined]
- [ ] [AAA test pattern correctly implemented]

### Integration Gates
- **Phase Entry Criteria**: [What must be complete before starting this phase]
- **Phase Exit Criteria**: [What must be validated before proceeding to next phase]
- **Rollback Test**: [Specific scenario to test rollback procedures]

### Performance Baseline
- **Measurement Strategy**: [How to establish performance baselines for this phase]
- **Acceptable Ranges**: [Guidelines for determining acceptable performance]
- **Monitoring Setup**: [What metrics to track during development]

## 4. Quality Assurance

### Success Criteria (Validation-Based)
- [ ] [Specific measurable outcome 1 with passing validation tests]
- [ ] [Specific measurable outcome 2 with component validation]
- [ ] [All existing functionality preserved with regression tests using AAA pattern]
- [ ] [New functionality covered by comprehensive test suite]
- [ ] [Component interface contracts validated and documented]

### Component Design Validation
- [ ] [Single responsibility principle maintained with clear evidence]
- [ ] [Clear interfaces defined between components with documented contracts]
- [ ] [Loose coupling achieved with measurable component independence]
- [ ] [High cohesion within components with focused functionality]

### Risk Mitigation Validation
- **High Risk Scenarios**: [Specific high-risk scenarios and validation tests]
- **Rollback Validation**: [Test scenarios for rollback procedures]
- **Failure Recovery**: [Validation of error handling and recovery mechanisms]

## 5. Production Readiness Validation

### Deployment Readiness
- **Smoke Tests**: [Basic functionality verification after deployment]
- **User Scenario Validation**: [Key user workflows that must function correctly]
- **Performance Under Load**: [Load testing requirements and acceptance criteria]

### Operational Readiness
- **Monitoring Setup**: [Required monitoring and alerting configuration]
- **Logging Validation**: [Adequate logging for troubleshooting verification]
- **Documentation Complete**: [Operational procedures and troubleshooting guides]
- **Rollback Procedures**: [Validated rollback procedures with test results]

## 6. Deliverables

### Primary Outputs
- **Code**: [Main implementation deliverable with comprehensive test coverage]
- **Tests**: [Complete test suite following AAA pattern with component validation]
- **Documentation**: [Required documentation updates including interface contracts]
- **Validation Report**: [Self-assessment checklist completion with evidence]

### Review Requirements
- **Test Coverage**: [Minimum coverage requirements with AAA pattern compliance]
- **Code Review**: [Review criteria including component contract validation]
- **Integration Testing**: [Cross-component integration validation requirements]

## 7. Implementation Notes

### Development Approach
- **TDD Cycle**: Write failing tests first using AAA pattern, implement to pass, refactor for contracts
- **AAA Pattern Example**: 
  ```python
  def test_configuration_validation():
      # Arrange
      config_data = {"ai_provider": "gemini", "temperature": 0.7}
      validator = ConfigValidator()
      
      # Act
      result = validator.validate(config_data)
      
      # Assert
      assert result.is_valid
      assert result.ai_provider == "gemini"
  ```
- **Component Strategy**: Design for modularity, testability, and clear interface contracts

### Technical Guidelines
- **Time Estimate**: [Realistic time range including comprehensive validation and testing]
- **Dependencies**: [What must be completed first with validation evidence]
- **HA Standards**: [Specific Home Assistant addon compliance requirements with links]

### MCP Server Usage Requirements
- **Mandatory MCP Servers**: [List required MCP servers for this phase]
- **Optional MCP Servers**: [List helpful but not required MCP servers]
- **Research Requirements**: [When to use WebFetch/WebSearch for HA standards validation]
- **Analysis Requirements**: [When to use zen for Gemini collaboration on complex decisions]
- **Version Control Requirements**: [GitHub MCP usage for commits, branches, and rollbacks]
- **Monitoring Integration**: [How MCP servers track progress and report status]

### Home Assistant Compliance Notes
- **Critical Compliance Issues**: [Commonly missed HA addon requirements]
- **Specific Documentation**: [Direct links to relevant HA documentation sections]
- **Validation Requirements**: [How to verify HA compliance for this phase]

### Rollback and Recovery Procedures
- **Pre-Phase Checkpoint**: Use GitHub MCP to create branch and commit baseline
- **Incremental Commits**: Commit working changes at validated milestones
- **Rollback Triggers**: Specific, measurable conditions requiring rollback
- **Recovery Strategy**: Step-by-step rollback validation with test procedures

### Collaborative Review and Validation Process
- **Implementation Validation**: Complete requirements and validate against checklist
- **Self-Assessment**: Verify all success criteria met with documented evidence
- **Gemini Review Request**: Use zen MCP for comprehensive expert review
- **Collaborative Analysis**: Work with Gemini to identify improvements and optimizations
- **Iterative Refinement**: Implement improvements and re-validate
- **Final Consensus**: Achieve mutual agreement on completion and quality

### Key References
- [Home Assistant Developer Docs - Addon Development](https://developers.home-assistant.io/docs/add-ons/)
- [Home Assistant Security Standards](https://developers.home-assistant.io/docs/add-ons/security/)
- [PROJECT_STATE_MEMORY.md](../PROJECT_STATE_MEMORY.md)
- [Finalized Plan](../finalizedplan.md)
```

## Template Validation Checklist

### Template Completeness (5 Items)
- [ ] All consensus improvements integrated (validation framework, AAA patterns, security considerations)
- [ ] Component interface contracts clearly specified
- [ ] MCP server monitoring and reporting integration included
- [ ] Production readiness validation with operational focus
- [ ] Specific HA compliance notes with targeted documentation links

### Quality Assurance (7 Items)
- [ ] TDD principles with explicit AAA pattern examples
- [ ] Component-based design with clear interface contracts
- [ ] Validation robustness over specification detail
- [ ] Self-assessment tools empower senior developers
- [ ] Integration gates prevent phase progression without validation
- [ ] Rollback procedures include test validation scenarios
- [ ] Production readiness covers both deployment and operational concerns

---
*This enhanced template incorporates Claude-Gemini consensus improvements to achieve 90+ implementation readiness while maintaining developer empowerment and strategic guidance focus.*