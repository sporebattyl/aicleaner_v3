# Gemini CLI MCP Tool - Collaboration Guide

## Overview
This guide documents best practices for using the Gemini CLI MCP tool in collaborative AI sessions with Claude Code. Based on the comprehensive README from the `jamubc/gemini-mcp-tool` project.

## 🎯 Core Capabilities

### AI Collaboration Features
- **Read with Gemini, Edit with Claude**: Use Gemini's massive token window for analysis, Claude for implementation
- **Large File Analysis**: Leverage Gemini's extended context for analyzing entire codebases
- **Safe Code Testing**: Sandbox mode for secure code execution and testing
- **Natural Language Integration**: Seamless conversation flow between AI systems

## 🛠 Available Tools

### Tool Categories

#### 1. Analysis Tools
- **`ask-gemini`**: Primary analysis tool for complex questions and large file examination
  - **Parameters**: `prompt` (required), `model` (optional), `sandbox` (optional)
  - **Usage**: General questions or file analysis using `@` syntax

#### 2. Sandbox Tools  
- **`sandbox-test`**: Safe code execution environment
  - **Parameters**: `prompt` (required), `model` (optional)
  - **Usage**: Test scripts, run experiments, validate code safely

#### 3. Utility Tools
- **`Ping`**: Connection testing
- **`Help`**: Display Gemini CLI help information

### Slash Commands (Claude Code Interface)
- **/analyze**: File/directory analysis or general questions
- **/sandbox**: Safe code testing in isolated environment
- **/help**: Show Gemini CLI help
- **/ping**: Test server connection

## 💡 Usage Patterns

### File Analysis with @ Syntax
```
# Single file analysis
"ask gemini to analyze @src/main.js and explain what it does"
"use gemini to examine @config.yaml and identify issues"

# Directory analysis
"analyze @src/ and summarize the architecture"
"use gemini to understand @. the current directory structure"

# Multiple files
"compare @old_config.yaml and @new_config.yaml for differences"
```

### Natural Language Commands
```
# General analysis
"ask gemini to search for the latest tech news"
"use gemini to explain React best practices"

# Project understanding
"understand the massive project using gemini"
"ask gemini about deployment strategies for this codebase"

# Problem solving
"use gemini to help debug @error_logs.txt"
```

### Sandbox Mode Usage
```
# Safe script testing
"use gemini sandbox to create and run a Python data processing script"
"ask gemini to safely test @script.py and explain results"

# Environment testing
"use gemini sandbox to install numpy and create a visualization"
"test this code safely: Create an HTTP client that calls external APIs"
```

## 🚀 Best Practices for Collaboration

### 1. Workflow Optimization
- **Analysis Phase**: Use Gemini for understanding large codebases and complex problems
- **Implementation Phase**: Use Claude for code changes, file edits, and system modifications
- **Testing Phase**: Use Gemini sandbox for safe validation of changes

### 2. Token Management
- **Large Files**: Always use Gemini for files >10k lines
- **Context Preservation**: Let Gemini handle the heavy analysis, Claude implements based on summary
- **Efficient Handoffs**: Clear communication between AI systems about findings and next steps

### 3. File Reference Strategy
```
# Effective patterns
@file.js explain the main function
@directory/ summarize the module structure  
@config.yaml validate this configuration

# Directory analysis
@src/ analyze the architecture patterns used
@tests/ review test coverage and identify gaps
@docs/ check documentation completeness
```

### 4. Safety Protocols
- **Always use sandbox** for untested code execution
- **Validate before applying** changes to production files
- **Test incrementally** rather than making bulk changes

## 🔧 Configuration Reference

### MCP Server Setup
```json
{
  "mcpServers": {
    "gemini-cli": {
      "command": "npx",
      "args": ["-y", "gemini-mcp-tool"]
    }
  }
}
```

### One-line Installation
```bash
claude mcp add gemini-cli -- npx -y gemini-mcp-tool
```

### Verification Commands
```bash
# Check MCP availability
claude mcp

# Verify Gemini CLI
gemini --version
npx -y gemini-mcp-tool
```

## 🎯 Use Cases for AICleaner v3

### Code Review and Analysis
```
"use gemini to analyze @addons/aicleaner_v3/ and identify architectural improvements"
"ask gemini to review @core/config_loader.py for optimization opportunities"
```

### Configuration Management
```
"analyze @config.default.yaml and @addons/aicleaner_v3/config.yaml for consistency"
"use gemini to validate @docker-compose.yml against best practices"
```

### Testing and Validation
```
"use gemini sandbox to test @test_scripts/integration_test.py safely"
"ask gemini to analyze @test-results/ and identify failure patterns"
```

### Documentation Generation
```
"analyze @src/ and generate comprehensive API documentation"
"use gemini to review @README.md and suggest improvements"
```

## 📋 Command Quick Reference

| Pattern | Description | Example |
|---------|-------------|---------|
| `ask gemini to analyze @file` | Single file analysis | `ask gemini to analyze @main.py` |
| `use gemini to examine @dir/` | Directory analysis | `use gemini to examine @src/` |
| `gemini sandbox @script` | Safe code testing | `gemini sandbox @test.py` |
| `analyze @file1 @file2` | Multiple file comparison | `analyze @old.conf @new.conf` |
| `ask gemini about X` | General questions | `ask gemini about Docker best practices` |

## 🔄 Integration Notes

- **Persistent Setup**: Configuration survives Claude Code restarts
- **Token Efficiency**: Gemini handles large context, Claude executes changes
- **Safe Testing**: Always use sandbox for uncertain operations
- **Natural Flow**: Commands work in conversational context

## 🎪 Advanced Patterns

### Multi-stage Analysis
1. **Discovery**: `"use gemini to analyze @project/ and identify main components"`
2. **Deep Dive**: `"ask gemini to examine @core/ and explain the architecture"`  
3. **Implementation**: Claude makes changes based on Gemini's analysis
4. **Validation**: `"use gemini sandbox to test the changes safely"`

### Collaborative Debugging
1. **Problem Identification**: `"analyze @error_logs/ and identify root causes"`
2. **Solution Research**: `"ask gemini for solutions to [specific issue]"`
3. **Code Changes**: Claude implements fixes
4. **Testing**: `"use gemini sandbox to validate the fix"`

This guide enables efficient AI collaboration by leveraging each system's strengths while maintaining safety and code quality.