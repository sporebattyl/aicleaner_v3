# Claude Code Custom Agents

This directory contains custom agents designed to extend Claude Code's Task tool capabilities with specialized workflows.

## 🎯 Available Agents

### Gemini Collaboration Agent (`gemini-collaborator`)
- **Purpose**: Advanced problem-solving using the 7-step Claude-Gemini collaboration workflow
- **Best For**: Complex coding tasks, refactoring, architecture changes, performance optimization
- **Status**: ✅ Ready for use

## 🚀 Quick Start

### Using the Gemini Collaboration Agent

```bash
Task(
    description="Refactor authentication system", 
    prompt="I need to refactor the authentication system in my web app to use JWT tokens instead of sessions. Current files: src/auth/session.js, src/middleware/auth.js. Requirements: maintain backward compatibility, improve security.",
    subagent_type="gemini-collaborator"
)
```

## 📋 Agent Features

### Gemini Collaborator Workflow
1. **🤝 Consult**: Present problem to Gemini with full context
2. **🔍 Analyze**: Compare Gemini's approach with Claude assessment  
3. **🎯 Refine**: Iterate until consensus on solution
4. **⚙️ Generate**: Gemini creates precise implementation details
5. **🛡️ Review**: Claude validates security, style, integration
6. **🔨 Implement**: Apply changes using filesystem tools
7. **✅ Validate**: Run tests, verify functionality, document changes

### Key Benefits
- **Systematic Approach**: Structured 7-step workflow ensures thorough analysis
- **Best of Both Worlds**: Combines Gemini's analysis with Claude's validation
- **Security Focused**: Multiple validation checkpoints for security and compatibility  
- **Comprehensive Testing**: Includes testing and validation as core steps
- **Clear Documentation**: Provides detailed progress updates and final summaries

## 🛠️ Setup Instructions

**Note**: Currently, Claude Code's Task tool recognizes only the built-in `general-purpose` agent. To use custom agents, you would need:

1. **Official Integration**: Anthropic would need to add support for custom agent types
2. **Local Extension**: Modify Claude Code locally to recognize custom agents
3. **Workaround**: Use the general-purpose agent with the custom prompts

### Workaround Usage

Until official support is available, you can use the gemini-collaborator workflow by:

```bash
Task(
    description="Complex refactoring with gemini collaboration",
    prompt="Please follow the 7-step Claude-Gemini collaboration workflow defined in agents/gemini_collaborator_prompt.md for this task: [YOUR ACTUAL TASK DESCRIPTION HERE]",
    subagent_type="general-purpose"
)
```

## 📁 File Structure

```
agents/
├── README.md                           # This file
├── agent_registry.md                   # Registry of all available agents
├── gemini_collaboration_agent.md       # Agent specification
├── gemini_collaborator_prompt.md       # Implementation prompt
├── gemini_collaborator_example.md      # Usage examples
└── test_gemini_collaborator.md         # Test cases
```

## 🧪 Testing

See `test_gemini_collaborator.md` for comprehensive test cases that validate:
- Complete 7-step workflow execution
- Proper Gemini integration and collaboration
- Security and compatibility validation
- Progress tracking and documentation
- Error handling and recovery

## 🎨 Creating New Agents

### Agent Development Template

1. **Agent Specification** (`[name]_agent.md`):
   - Purpose and use cases
   - Tools and capabilities
   - When to use vs. other agents

2. **Implementation Prompt** (`[name]_prompt.md`):
   - Detailed instructions for the agent
   - Step-by-step workflow
   - Response format requirements

3. **Usage Examples** (`[name]_example.md`):
   - Real-world usage scenarios
   - Expected outputs and workflows
   - Best practices and tips

4. **Test Cases** (`test_[name].md`):
   - Validation scenarios
   - Success criteria
   - Edge case handling

### Best Practices for Agent Design

- **Clear Purpose**: Define specific problem domains the agent addresses
- **Structured Workflow**: Break complex tasks into manageable, trackable steps
- **Progress Transparency**: Use TodoWrite and clear status updates
- **Error Resilience**: Handle failures gracefully with fallback options
- **Security First**: Include security validation at appropriate stages
- **Comprehensive Testing**: Validate functionality, performance, and edge cases

## 🔮 Future Enhancements

Potential additional agents to consider:

- **`code-reviewer`**: Systematic code review with security and performance analysis
- **`architecture-planner`**: High-level system design and architecture planning
- **`performance-optimizer`**: Specialized performance analysis and optimization
- **`security-auditor`**: Comprehensive security assessment and vulnerability analysis
- **`migration-assistant`**: Framework/library migration with compatibility analysis
- **`test-generator`**: Intelligent test case generation and coverage analysis

## 🤝 Contributing

To contribute new agents or improvements:

1. Fork the repository
2. Create your agent following the template structure
3. Add comprehensive test cases
4. Update the agent registry
5. Submit a pull request with documentation

## 📚 Resources

- **Claude Code Documentation**: https://docs.anthropic.com/en/docs/claude-code
- **MCP Tools Reference**: For understanding available tool capabilities
- **Gemini CLI Integration**: For Gemini collaboration features
- **Sequential Thinking**: For complex problem analysis workflows

---

**Note**: This agent system is designed to work with Claude Code's Task tool. As the platform evolves, these agents may need updates to maintain compatibility.