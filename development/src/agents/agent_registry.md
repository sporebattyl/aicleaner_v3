# Agent Registry - Enhanced Claude Code Agents

This registry tracks all available custom agents for Claude Code's Task tool.

## 🚀 Available Agents

### Enhanced Gemini Collaborator (`gemini-collaborator-enhanced`)
- **File**: `gemini_collaborator_enhanced_prompt.md`
- **Purpose**: Advanced Claude-Gemini collaboration with intelligent quota management
- **Key Features**:
  - Intelligent API key cycling across 4 keys (40 req/min, 1000/day total)
  - Automatic model selection (gemini-2.5-pro vs 2.5-flash)
  - Request batching and optimization
  - Graceful fallback to Claude-only mode
  - Comprehensive error recovery
- **Best For**: Complex coding tasks requiring systematic analysis and implementation
- **Quota Management**: ✅ Full quota optimization
- **Error Recovery**: ✅ Multiple fallback strategies
- **Status**: ✅ Ready for production use

**Usage**:
```bash
Task(
    description="Refactor authentication system with quota optimization",
    prompt="Please follow the enhanced Claude-Gemini collaboration workflow defined in agents/gemini_collaborator_enhanced_prompt.md for this task: [YOUR ACTUAL TASK DESCRIPTION HERE]",
    subagent_type="general-purpose"
)
```

### Basic Gemini Collaborator (`gemini-collaborator`)
- **File**: `gemini_collaborator_prompt.md`
- **Purpose**: Standard 7-step Claude-Gemini collaboration workflow
- **Key Features**:
  - Structured 7-step workflow
  - Basic Gemini integration
  - Simple error handling
- **Best For**: Standard coding tasks with basic Gemini consultation
- **Quota Management**: ❌ Basic (no optimization)
- **Error Recovery**: ⚠️ Limited
- **Status**: ✅ Available (legacy)

**Usage**:
```bash
Task(
    description="Standard refactoring with basic gemini collaboration",
    prompt="Please follow the 7-step Claude-Gemini collaboration workflow defined in agents/gemini_collaborator_prompt.md for this task: [YOUR ACTUAL TASK DESCRIPTION HERE]",
    subagent_type="general-purpose"
)
```

## How to Use Agents

1. **Identify the Task Type**: Match your task to the appropriate agent based on complexity and requirements

2. **Prepare Context**: Gather all necessary information:
   - Problem description and requirements
   - Relevant file paths and code snippets
   - Constraints and compatibility requirements
   - Expected outcomes

3. **Invoke the Agent**: Use the Task tool with the appropriate subagent_type

4. **Monitor Progress**: Agents provide structured updates through their workflow steps

5. **Review Results**: Agents provide comprehensive summaries and validation reports

## Agent Development Guidelines

When creating new agents:

1. **Clear Purpose**: Define specific use cases and when to use the agent
2. **Structured Workflow**: Break complex tasks into manageable steps
3. **Progress Tracking**: Use TodoWrite to track workflow progress
4. **Comprehensive Validation**: Include security, performance, and integration checks
5. **Error Handling**: Gracefully handle failures and provide alternatives
6. **Documentation**: Provide clear examples and usage instructions

## Best Practices

- **Choose the Right Agent**: Use specialized agents for their intended purposes
- **Provide Complete Context**: The more context you provide, the better the results
- **Trust the Process**: Let agents manage their workflow - they're designed to be autonomous
- **Validate Results**: Always review agent outputs before deploying changes
- **Learn from Examples**: Study the provided examples to understand effective usage patterns

## Contributing

To add a new agent:

1. Create the agent documentation in `agents/[agent_name]_agent.md`
2. Create the implementation prompt in `agents/[agent_name]_prompt.md`  
3. Add usage examples in `agents/[agent_name]_example.md`
4. Update this registry with the new agent information
5. Test the agent thoroughly before submission