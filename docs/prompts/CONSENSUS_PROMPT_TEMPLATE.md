# AICleaner v3 Implementation Prompt Template

## Design Principles
- **TDD First**: Always use Test-Driven Development principles
- **AAA Testing**: Structure all tests with Arrange-Act-Assert methodology  
- **Component-Based Design**: Create modular, loosely-coupled components with clear interfaces

## Template Structure

```markdown
# [Phase/Task Name]: [Brief Description]

## 1. Context & Objective
- **Primary Goal**: [1-2 sentences describing the main objective]
- **Phase Context**: [How this fits in the overall AICleaner v3 improvement plan]
- **Success Impact**: [What successful completion enables for future phases]

## 2. Implementation Requirements

### Core Tasks
1. **[Task 1 Name]**
   - **Action**: [Specific action required]
   - **Details**: [Key implementation points with TDD approach]
   - **Validation**: [How to verify completion with tests]

2. **[Task 2 Name]**
   - **Action**: [Specific action required]
   - **Details**: [Key implementation points with component design]
   - **Validation**: [How to verify completion]

### Technical Specifications
- **Required Tools**: [List essential tools and testing frameworks]
- **Key Configurations**: [Critical Home Assistant config changes]
- **Integration Points**: [HA API, MQTT, external service touchpoints]
- **Testing Strategy**: [Unit, integration, and component test requirements]

## 3. Quality Assurance

### Success Criteria (TDD-Based)
- [ ] [Specific measurable outcome 1 with passing tests]
- [ ] [Specific measurable outcome 2 with component validation]
- [ ] [All existing functionality preserved with regression tests]
- [ ] [New functionality covered by comprehensive test suite]

### Component Design Validation
- [ ] [Single responsibility principle maintained]
- [ ] [Clear interfaces defined between components]
- [ ] [Loose coupling achieved]
- [ ] [High cohesion within components]

### Risk Mitigation
- **High Risk**: [Primary risk and mitigation strategy]
- **Medium Risk**: [Secondary risk and mitigation approach]

## 4. Deliverables

### Primary Outputs
- **Code**: [Main implementation deliverable with test coverage]
- **Tests**: [Comprehensive test suite following AAA pattern]
- **Documentation**: [Required documentation updates]

### Review Requirements
- **Test Coverage**: [Minimum coverage requirements]
- **Code Review**: [Review criteria and checklist]
- **Integration Testing**: [HA addon integration validation]

## 5. Implementation Notes

### Development Approach
- **TDD Cycle**: Write failing tests first, implement to pass, refactor
- **AAA Pattern**: Structure all tests with clear Arrange-Act-Assert sections
- **Component Strategy**: Design for modularity and testability

### Technical Guidelines
- **Time Estimate**: [Realistic time range including test development]
- **Dependencies**: [What must be completed first]
- **HA Standards**: [Specific Home Assistant addon compliance requirements]

### MCP Server Usage Requirements
- **Mandatory MCP Servers**: [List required MCP servers for this phase]
- **Optional MCP Servers**: [List helpful but not required MCP servers]
- **Research Requirements**: [When to use brave-search, WebFetch, WebSearch]
- **Analysis Requirements**: [When to use zen for Gemini collaboration, context7 for sequential thinking]
- **Version Control Requirements**: [When to use GitHub MCP for commits, branches, and rollbacks]

### Rollback and Recovery Procedures
- **Pre-Phase Checkpoint**: Use GitHub MCP to create branch and commit baseline before starting
- **Incremental Commits**: Commit working changes at each major milestone within the phase
- **Rollback Triggers**: Specific conditions that require immediate rollback to previous state
- **Recovery Strategy**: Step-by-step rollback procedure using GitHub MCP commands

### Collaborative Review and Validation Process
- **Initial Implementation**: Complete all phase requirements according to specifications
- **Self-Assessment**: Verify all success criteria met and deliverables completed
- **Gemini Review Request**: Use zen MCP to request comprehensive Gemini review of implementation
- **Collaborative Analysis**: Work with Gemini to identify gaps, improvements, and optimizations
- **Iterative Refinement**: Implement agreed-upon changes and improvements
- **Re-Review Cycle**: Have Gemini review changes until both parties agree implementation is perfect
- **Final Consensus**: Achieve mutual agreement that phase is truly complete and meets all standards

### Key References
- [Home Assistant Developer Docs](https://developers.home-assistant.io/docs/add-ons/)
- [Project State Memory](../PROJECT_STATE_MEMORY.md)
- [Finalized Plan](../finalizedplan.md)
```

## Usage Guidelines

1. **Always Lead with Tests**: Each implementation task should begin with test creation
2. **Component Focus**: Design each module with single responsibility and clear interfaces
3. **HA Compliance**: Ensure all code follows current Home Assistant addon standards
4. **Documentation**: Include comprehensive docstrings and type hints
5. **Integration**: Verify seamless integration with existing HA ecosystem

## Quality Gates

Before marking any task complete:
- [ ] All tests pass (unit, integration, component)
- [ ] Code coverage meets minimum thresholds
- [ ] Component interfaces are well-defined
- [ ] Home Assistant standards compliance verified
- [ ] Regression testing completed

---
*This template ensures consistent, high-quality implementation across all AICleaner v3 improvement phases while maintaining focus on testability, modularity, and Home Assistant integration standards.*