# Claude & Gemini Collaboration Guide

## 🚨 CRITICAL SESSION INITIALIZATION REQUIREMENTS

**MANDATORY FOR EVERY CLAUDE SESSION:**

1. **Always read CLAUDE.md immediately after:**
   - Starting a new session
   - After using /compact command
   - After any context reset or restart
   - Before engaging with Gemini or starting work

2. **Always read AI_COLLABORATION_FRAMEWORK.md for technical protocols**

3. **These files contain critical instructions that MUST be followed:**
   - API key cycling protocols
   - Rate limit management procedures
   - Collaboration workflows
   - Project status and requirements

**⚠️ FAILURE TO READ THESE FILES WILL RESULT IN:**
- Improper API key usage
- Premature abandonment of Gemini collaboration
- Protocol violations
- Inefficient task execution

---

## Project Philosophy

This document outlines the collaboration workflow for developing AICleaner v3, a Home Assistant addon for personal, hobbyist use. The goal is to leverage the strengths of both Gemini and Claude in a flexible, iterative process. This is not an enterprise project; the process should be practical and efficient for a single developer.

## Project Status Summary (2025-01-19)

### AICleaner v3 Implementation Progress
**Status:** 95% Complete - FINAL RELEASE PREPARATION**  
**Current Task:** Task 5C-6: Release Preparation (FINAL TASK)  
**Architecture:** Home Assistant addon with AI-powered automation ready for v1.0.0 release

### Completed Phases
✅ **Phase 1A-1C:** Core Foundation - Configuration, AI providers, testing  
✅ **Phase 2A-2C:** AI Optimization - Model selection, quality, monitoring  
✅ **Phase 3A-3C:** Device Management - Detection, zones, security  
✅ **Phase 4A:** Enhanced HA Integration - Entities, services, event bridge  
✅ **Phase 4B:** MQTT Discovery - Device communication and discovery  
✅ **Phase 4C:** User Interface - Web dashboard implementation
✅ **Phase 5A:** Performance Optimization - Complete system optimization  
✅ **Phase 5B:** Resource Management - Advanced resource monitoring  

### Phase 5C: Production Deployment Status
✅ **Task 5C-1:** Versioning and Changelog Management (bump2version, unified versioning)
✅ **Task 5C-2:** Documentation Finalization (README, INSTALL, CONTRIBUTING, LICENSE)
✅ **Task 5C-3:** Docker Image Optimization (multi-stage, multi-arch, validation)
✅ **Task 5C-4:** CI/CD Pipeline Implementation (GitHub Actions, security scanning)
✅ **Task 5C-5:** Production Validation Agent (comprehensive system validation)
🔄 **Task 5C-6:** Release Preparation (FINAL TASK - creating final release components)  

### Current Implementation
- **Configuration System:** Encrypted, validated, unified configuration
- **AI Providers:** Multi-provider with intelligent failover (OpenAI, Gemini, Anthropic, Ollama)
- **Home Assistant Integration:** Native entities, services, and event synchronization
- **MQTT Discovery:** Automatic device discovery and entity registration
- **Backend Ready:** Solid backend foundation ready for UI implementation

## Gemini-Claude Collaboration Workflow

This workflow emphasizes a partnership where Gemini and Claude complement each other's strengths for practical, single-developer projects.

> **📋 Technical Specification:** For detailed protocols and advanced features, see `AI_COLLABORATION_FRAMEWORK.md`

### Core Roles

**Gemini (The Architect & Workhorse):**
- **Strengths:** Large context window, deep codebase understanding, generating new code, broad architectural reviews
- **Primary Tasks:** Initial code generation, applying large-scale changes, comprehensive code reviews, heavy lifting for complex implementations

**Claude (The Precision Tool & Implementer):**
- **Strengths:** Technical precision, tool use, implementing specific tasks
- **Primary Tasks:** Implementing changes using tools, reviewing and refining code, asking clarifying questions, final implementation and validation

### The Definitive Coding Collaboration Process
**Schema:** CCW-v1.0

This structured, two-stage process ensures clarity, quality, and efficient iteration.

#### Stage 1: The Plan Artifact
Before any code is written, create a concise agreement on the "what" and "how":

1. **Define Goal & Scope:** Clearly state the objective
2. **Task Decomposition:** Break complex features into logical chunks
3. **Propose Implementation Plan:** Outline technical approach, files to modify, architectural changes
4. **User Approval:** Plan must be approved before implementation begins

#### Stage 2: The Implementation Artifact
Once the plan is approved, implement the actual code:

1. **Time-Boxing:** Each task limited to **3 implementation-review iterations**. If not completed, escalate to user for plan re-evaluation.

2. **Implementation Cycle:**
   - Gemini creates initial implementation as unified diff
   - Claude reviews and provides specific feedback
   - Discussion and refinement until both AIs agree
   - Final implementation by Claude using tools

3. **Diff Format:** All changes must be clean, unified diff format:
   ```diff
   --- a/file.py
   +++ b/file.py
   @@ -25,7 +25,8 @@
    # Expected response
    expected_response = {
   -    "status": "success"
   +    "status": "success",
   +    "provider": "gemini-primary"
    }
   ```

4. **Quality Gates:** Before completion, all changes must pass:
   - Linting (ruff, pylint)
   - Type checking (mypy)
   - Unit and integration tests
   - Documentation updates

5. **Rollback Protocol:** If issues arise post-implementation:
   - Immediate revert to stable state
   - Root cause analysis
   - Return to Stage 1 with improved plan

## MCP Server Configuration

Working MCP server configuration for `~/.claude-settings.json`:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/drewcifer/aicleaner_v3"]
    },
    "git": {
      "command": "npx", 
      "args": ["-y", "@cyanheads/git-mcp-server"]
    },
    "brave-search": {
      "command": "npx",
      "args": ["-y", "brave-search-mcp"],
      "env": {
        "BRAVE_API_KEY": "BSA0Iv5TiOTlCHrCSha2hkoo6PkiA7o"
      }
    },
    "gemini-cli": {
      "command": "npx",
      "args": ["-y", "mcp-gemini-cli"],
      "env": {
        "GEMINI_API_KEY": "AIzaSyAUrUCFIL2D4Lq5nQyfHfigHI0QgtH9oTI"
      }
    },
    "context7": {
      "command": "context7-mcp",
      "args": []
    },
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
    }
  }
}
```

**Status:** ✅ **ALL SERVERS WORKING** - Configuration stable and tested

## Gemini API Usage Quick-Reference

For detailed guide, see `GEMINI_API_GUIDE.md`.

**Key Environment Variables:**
```bash
export GEMINI_API_KEY="AIzaSyAUrUCFIL2D4Lq5nQyfHfigHI0QgtH9oTI"
```

**Quick-Start Python Example:**
```python
import google.generativeai as genai

genai.configure(api_key="YOUR_API_KEY")

model = genai.GenerativeModel('gemini-2.5-pro')
response = model.generate_content('Analyze this code structure...')
print(response.text)
```

## Intelligent Gemini Model Selection Framework (2025 Update)

**MANDATORY: Use this optimized 5-model framework for maximum availability and efficiency**

### Model Capabilities Overview

| Model | RPM (Free) | RPD (Free) | Context Window | Best For |
|-------|------------|------------|----------------|----------|
| **gemini-2.5-pro** | 5 | 100 | 1M tokens | Complex reasoning, architecture, large codebases |
| **gemini-2.5-flash** | 10 | 250 | 1M tokens | Balanced development, code generation |
| **gemini-2.5-flash-lite** | 15 | **1,000** | 1M tokens | **High throughput, sustained work** |
| **gemini-2.0-flash** | 15 | 200 | 1M tokens | Tool use, speed, next-gen features |
| **gemini-2.0-flash-lite** | **30** | 200 | 1M tokens | **Quick iteration, cost efficiency** |

### Task-Based Model Selection Matrix

**Choose the PRIMARY model based on task requirements:**

#### 🎯 **Complex Analysis & Architecture**
**Primary Path:** gemini-2.5-pro → gemini-2.5-flash → gemini-2.5-flash-lite
- Initial codebase architecture analysis
- Deep technical reviews requiring comprehensive understanding
- Complex planning sessions with multiple considerations
- Strategic decision making with multiple trade-offs

#### ⚡ **Balanced Development & Implementation**
**Primary Path:** gemini-2.5-flash → gemini-2.5-flash-lite → gemini-2.0-flash
- Implementation discussions and code generation
- Iterative plan refinement
- Medium complexity technical questions
- Code reviews of moderate size

#### 🚀 **Quick Iteration & Clarification**
**Primary Path:** gemini-2.0-flash-lite → gemini-2.5-flash-lite → gemini-2.0-flash
- Simple confirmations ("Does this approach sound good?")
- Basic status updates and progress checks
- Quick clarifications on specific points
- Simple yes/no or multiple choice questions

#### 🔄 **High-Volume & Sustained Work**
**Primary Path:** gemini-2.5-flash-lite → gemini-2.0-flash-lite → gemini-2.5-flash
- Large scale processing tasks
- Extended collaboration sessions
- When you need consistent availability throughout the day
- Batch processing and analysis

### Smart Selection Criteria

**Automatic model selection based on prompt characteristics:**

1. **Prompt Length Analysis:**
   - **<100 characters** + simple language → **gemini-2.0-flash-lite**
   - **100-500 characters** + standard complexity → **gemini-2.5-flash-lite**
   - **500-1000 characters** + technical terms → **gemini-2.5-flash**
   - **>1000 characters** + complex analysis → **gemini-2.5-pro**

2. **Context Requirements:**
   - **No code context needed** → **gemini-2.0-flash-lite**
   - **Single file or component focus** → **gemini-2.5-flash-lite**
   - **Multiple files (2-5)** → **gemini-2.5-flash**
   - **Large codebase/complex architecture** → **gemini-2.5-pro**

3. **Task Type Keywords:**
   - **"confirm", "quick", "simple", "yes/no", "check"** → **gemini-2.0-flash-lite**
   - **"implement", "code", "debug", "fix", "create"** → **gemini-2.5-flash-lite**
   - **"refactor", "discuss", "explain", "design"** → **gemini-2.5-flash**
   - **"analyze", "review", "architecture", "comprehensive", "evaluate"** → **gemini-2.5-pro**

4. **Urgency & Availability Needs:**
   - **Need immediate response** → **gemini-2.0-flash-lite** (30 RPM)
   - **Extended work session** → **gemini-2.5-flash-lite** (1,000 RPD)
   - **Standard collaboration** → **gemini-2.5-flash**
   - **Deep analysis session** → **gemini-2.5-pro**

### Optimized Rate Limit Fallback Chain

**NEW AVAILABILITY-FIRST PROTOCOL: Designed for maximum Gemini collaboration uptime**

When your PRIMARY model choice hits rate limits:

1. **Try gemini-2.5-flash-lite first** (1,000 RPD - highest daily limit)
2. **Then try gemini-2.0-flash-lite** (30 RPM - highest per-minute rate)
3. **Fall back to remaining models in availability order**
4. **Cycle through all 4 API keys for EACH model before moving to next**
5. **NEVER give up until all 20 combinations exhausted (4 keys × 5 models)**

**Detailed Fallback Sequence:**
```
Primary Model (rate limited)
├─ gemini-2.5-flash-lite (Key 1,2,3,4)
├─ gemini-2.0-flash-lite (Key 1,2,3,4)  
├─ gemini-2.0-flash (Key 1,2,3,4)
├─ gemini-2.5-flash (Key 1,2,3,4)
└─ gemini-2.5-pro (Key 1,2,3,4)
```

### Enhanced Selection Algorithm

```python
def select_optimal_gemini_model(prompt, context_files=[], conversation_stage="initial", urgency="standard"):
    # Base scoring system
    score = 0
    
    # Prompt complexity analysis
    prompt_length = len(prompt)
    if prompt_length > 1000: score += 3
    elif prompt_length > 500: score += 2
    elif prompt_length > 100: score += 1
    
    # Keyword analysis (weighted)
    complex_keywords = ["analyze", "architecture", "comprehensive", "review", "evaluate", "assess"]
    medium_keywords = ["implement", "code", "refactor", "design", "create", "develop"]
    simple_keywords = ["confirm", "quick", "simple", "yes", "no", "check", "verify"]
    
    if any(kw in prompt.lower() for kw in complex_keywords): score += 3
    elif any(kw in prompt.lower() for kw in medium_keywords): score += 1
    elif any(kw in prompt.lower() for kw in simple_keywords): score -= 2
    
    # Context requirements
    context_count = len(context_files)
    if context_count > 5: score += 3
    elif context_count > 2: score += 2
    elif context_count > 0: score += 1
    
    # Conversation stage
    if conversation_stage == "initial": score += 1
    elif conversation_stage == "followup": score -= 1
    
    # Urgency and availability weighting
    if urgency == "immediate":
        # Prefer high RPM models
        if score <= 1: return "gemini-2.0-flash-lite"  # 30 RPM
        elif score <= 3: return "gemini-2.5-flash-lite"  # 15 RPM  
        else: return "gemini-2.5-flash"  # 10 RPM
    elif urgency == "sustained":
        # Prefer high RPD models
        if score <= 2: return "gemini-2.5-flash-lite"  # 1,000 RPD
        elif score <= 4: return "gemini-2.0-flash-lite"  # 200 RPD
        else: return "gemini-2.5-flash"  # 250 RPD
    else:
        # Standard selection
        if score >= 6: return "gemini-2.5-pro"
        elif score >= 3: return "gemini-2.5-flash"
        elif score >= 1: return "gemini-2.5-flash-lite"
        else: return "gemini-2.0-flash-lite"

def get_fallback_sequence(primary_model):
    """Get optimized fallback sequence based on availability"""
    models = ["gemini-2.5-flash-lite", "gemini-2.0-flash-lite", "gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"]
    
    # Remove primary model from list and put lite models first
    if primary_model in models:
        models.remove(primary_model)
    
    # Always prioritize lite models for sustained availability
    return models
```

## API Keys and Rate Limit Management

**Gemini API Keys (Ordered by Priority):**
- **Primary:** AIzaSyDYRk_mZQZ_Rjq-sPbLaW5fpN9XnZ39Nro
- **Secondary:** AIzaSyBdS3Mp_pAgxlj7SK0ziNPjS-Jfgx5u3Fc
- **Tertiary:** AIzaSyBtBJg2AHVlNYZCSco69JWGkCL8zDFQNzo
- **Backup:** AIzaSyAUrUCFIL2D4Lq5nQyfHfigHI0QgtH9oTI

### Intelligent API Cycling System (2025)

**🎯 AUTOMATED INTELLIGENCE: Claude now uses a fully automated intelligent API cycling system**

**No Manual Management Required:**
- ✅ **Persistent Usage Tracking**: System remembers usage across Claude sessions
- ✅ **Smart Key Selection**: Automatically chooses optimal API key + model combination
- ✅ **Exponential Backoff**: Learns from failures and avoids recently failed combinations
- ✅ **Load Balancing**: Distributes usage across all 4 API keys for maximum availability
- ✅ **Seamless Fallback**: Automatically tries all 20 combinations (4 keys × 5 models)

**How It Works:**
1. **Task Analysis**: System analyzes your prompt to determine optimal model
2. **Intelligent Selection**: Picks best available API key + model based on recent usage
3. **Automatic Retry**: If rate limited, instantly tries next best combination
4. **Learning**: Records successes/failures to improve future selections
5. **Health Monitoring**: Tracks API key health and availability in real-time

**Storage Location:** 
- Usage data persisted in `~/.aicleaner/gemini_api_usage.json`
- Automatic reset tracking (daily quotas reset at midnight UTC)
- Per-minute rate limit management

**Usage Example:**
```python
from utils.gemini_model_selector import get_optimal_api_key_model, record_gemini_success

# Get best combination for your task
api_key, model = get_optimal_api_key_model(
    prompt="Implement user authentication system",
    urgency="standard"
)

# After successful API call
record_gemini_success(api_key, model)
```

**Success Metrics:**
- **99.9%+ Uptime**: Intelligent use of all 20 available combinations
- **Zero Manual Work**: Claude never thinks about rate limits
- **Optimal Performance**: Always uses best available model for each task
- **Persistent Memory**: Learns and improves across sessions

**Health Monitoring:**
```python
from utils.gemini_model_selector import get_gemini_health_status

status = get_gemini_health_status()
print(f"Healthy keys: {status['healthy_keys']}/{status['total_keys']}")
```

**Other Keys:**
- **GitHub PAT:** github_pat_11AJGNBZA0TbF8gMKTsKjw_4YpJkS8lixhC9PsjNVAjCaFXJVeGTGkNFfcYPrc4Ac7WKGFQNzo
- **Brave Search:** BSA0Iv5TiOTlCHrCSha2hkoo6PkiA7o

## Comprehensive Model Comparison and Usage Guidelines

### Model Performance Comparison Matrix

| Criteria | 2.5-pro | 2.5-flash | 2.5-flash-lite | 2.0-flash | 2.0-flash-lite |
|----------|---------|-----------|----------------|-----------|----------------|
| **Availability Score** | ⭐⭐ (2/5) | ⭐⭐⭐ (3/5) | ⭐⭐⭐⭐⭐ (5/5) | ⭐⭐⭐ (3/5) | ⭐⭐⭐⭐ (4/5) |
| **Cost Efficiency** | ⭐⭐ (2/5) | ⭐⭐⭐ (3/5) | ⭐⭐⭐⭐⭐ (5/5) | ⭐⭐⭐⭐ (4/5) | ⭐⭐⭐⭐⭐ (5/5) |
| **Response Speed** | ⭐⭐⭐ (3/5) | ⭐⭐⭐⭐ (4/5) | ⭐⭐⭐⭐⭐ (5/5) | ⭐⭐⭐⭐⭐ (5/5) | ⭐⭐⭐⭐⭐ (5/5) |
| **Analysis Depth** | ⭐⭐⭐⭐⭐ (5/5) | ⭐⭐⭐⭐ (4/5) | ⭐⭐⭐ (3/5) | ⭐⭐⭐ (3/5) | ⭐⭐ (2/5) |
| **Context Handling** | ⭐⭐⭐⭐⭐ (5/5) | ⭐⭐⭐⭐ (4/5) | ⭐⭐⭐ (3/5) | ⭐⭐⭐⭐ (4/5) | ⭐⭐⭐ (3/5) |
| **Sustained Work** | ⭐⭐ (2/5) | ⭐⭐⭐ (3/5) | ⭐⭐⭐⭐⭐ (5/5) | ⭐⭐⭐ (3/5) | ⭐⭐⭐ (3/5) |

### Detailed Model Characteristics

#### 🎯 **Gemini 2.5 Pro** - *The Deep Thinker*
**Best For:** Complex architectural analysis, security audits, strategic planning
- **Thinking Enabled:** ✅ Advanced reasoning capabilities
- **Rate Limits:** 5 RPM, 100 RPD (most restrictive)
- **Use Cases:** 
  - Initial codebase architecture analysis
  - Comprehensive security reviews
  - Complex problem-solving requiring deep analysis
  - Strategic decision making with multiple trade-offs
- **Avoid For:** Quick iterations, sustained work sessions, simple tasks

#### ⚡ **Gemini 2.5 Flash** - *The Balanced Workhorse*
**Best For:** Standard development tasks, code generation, moderate complexity work
- **Thinking Enabled:** ✅ Good reasoning with faster responses
- **Rate Limits:** 10 RPM, 250 RPD (balanced availability)
- **Use Cases:**
  - Implementation discussions and code generation
  - Code reviews of moderate complexity
  - Iterative plan refinement
  - Standard collaboration tasks
- **Avoid For:** Immediate response needs, all-day work sessions

#### 🚀 **Gemini 2.5 Flash-Lite** - *The Sustained Collaborator*
**Best For:** Extended work sessions, high-volume tasks, cost-sensitive projects
- **Thinking Enabled:** ❌ Optimized for speed and efficiency
- **Rate Limits:** 15 RPM, 1,000 RPD (★ **BEST FOR ALL-DAY WORK** ★)
- **Use Cases:**
  - Extended development sessions (2+ hours)
  - High-throughput batch processing
  - Sustained collaboration throughout the day
  - Cost-efficient development work
- **Perfect For:** Most power user scenarios requiring consistent availability

#### 🔧 **Gemini 2.0 Flash** - *The Feature Pioneer*
**Best For:** Next-generation features, tool integration, modern capabilities
- **Thinking Enabled:** ❌ Focus on speed and tool use
- **Rate Limits:** 15 RPM, 200 RPD (good availability)
- **Use Cases:**
  - Tool-assisted development
  - Next-gen feature exploration
  - Integration with external systems
  - Modern development workflows
- **Avoid For:** Deep analysis, complex reasoning tasks

#### ⚡ **Gemini 2.0 Flash-Lite** - *The Quick Responder*
**Best For:** Immediate responses, rapid iteration, simple confirmations
- **Thinking Enabled:** ❌ Optimized for minimal latency
- **Rate Limits:** 30 RPM, 200 RPD (★ **HIGHEST PER-MINUTE RATE** ★)
- **Use Cases:**
  - Quick confirmations and validations
  - Rapid iteration cycles
  - Simple yes/no questions
  - Immediate response requirements
- **Perfect For:** When you need answers RIGHT NOW

### Usage Guidelines by Development Phase

#### 🔍 **Project Analysis Phase**
**Primary:** gemini-2.5-pro → **Fallback:** gemini-2.5-flash → gemini-2.5-flash-lite
- Use 2.5-pro for initial architecture review
- Switch to 2.5-flash for detailed component analysis
- Use 2.5-flash-lite for ongoing analysis work

#### 🛠️ **Active Development Phase** 
**Primary:** gemini-2.5-flash-lite → **Fallback:** gemini-2.0-flash-lite → gemini-2.5-flash
- 2.5-flash-lite provides sustained availability for long coding sessions
- 2.0-flash-lite offers quick responses for immediate needs
- 2.5-flash handles more complex implementation discussions

#### 🐛 **Debugging & Bug Fixing**
**Primary:** gemini-2.0-flash-lite → **Fallback:** gemini-2.5-flash-lite → gemini-2.0-flash
- 2.0-flash-lite gives immediate responses for urgent bugs
- 2.5-flash-lite handles more complex debugging scenarios
- Quick turnaround times are essential for debugging workflow

#### 📚 **Documentation & Testing**
**Primary:** gemini-2.5-flash-lite → **Fallback:** gemini-2.0-flash-lite → gemini-2.5-flash
- 2.5-flash-lite excels at high-volume documentation generation
- 2.0-flash-lite handles quick documentation updates
- Sustained availability needed for comprehensive documentation work

### Model Selection Decision Tree

```
START: Need Gemini collaboration
│
├─ URGENT (need answer immediately)
│  └─ Use gemini-2.0-flash-lite (30 RPM)
│
├─ COMPLEX (architecture, security, deep analysis)
│  └─ Use gemini-2.5-pro (if available)
│      └─ Fallback: gemini-2.5-flash → gemini-2.5-flash-lite
│
├─ SUSTAINED (2+ hour work session)
│  └─ Use gemini-2.5-flash-lite (1,000 RPD)
│      └─ Fallback: gemini-2.0-flash-lite → gemini-2.0-flash
│
├─ STANDARD (normal collaboration)
│  └─ Use gemini-2.5-flash (balanced)
│      └─ Fallback: gemini-2.5-flash-lite → gemini-2.0-flash
│
└─ HIGH-VOLUME (batch processing, documentation)
   └─ Use gemini-2.5-flash-lite (best throughput)
       └─ Fallback: gemini-2.0-flash-lite → gemini-2.5-flash
```

### Best Practices for Maximum Collaboration Uptime

#### ✅ **DO**
- **Always start with lite models for sustained work** - They have the best availability
- **Use 2.0-flash-lite for immediate responses** - Highest per-minute rate (30 RPM)
- **Reserve 2.5-pro for truly complex analysis** - Don't waste limited quota on simple tasks
- **Plan long sessions with 2.5-flash-lite** - 1,000 RPD enables all-day collaboration
- **Follow the complete 20-combination fallback** - Never give up after first rate limit

#### ❌ **DON'T**
- **Don't use 2.5-pro for simple tasks** - Wastes precious quota (only 100 RPD)
- **Don't give up after first rate limit** - Lite models should almost always be available
- **Don't ignore urgency requirements** - Match model to time sensitivity
- **Don't forget about sustained work needs** - Choose models that can handle long sessions
- **Don't skip the fallback sequence** - It's designed for 99%+ availability

### Integration with Python Code

```python
# Import the advanced model selector
from utils.gemini_model_selector import select_optimal_model, get_collaboration_strategy

# Simple model selection
model = select_optimal_model(
    prompt="Review this implementation for security issues",
    context_files=["security/validator.py", "auth/manager.py"],
    urgency="standard"
)
# Returns: "gemini-2.5-flash"

# Comprehensive strategy
strategy = get_collaboration_strategy(
    prompt="Extended development session for Phase 3 features",
    context_files=["addons/aicleaner_v3/**/*.py"],
    urgency="sustained",
    expected_duration="3hours"
)
# Returns full strategy with fallback sequence, thinking budget, etc.
```

### Availability Monitoring

**Real-time Model Status:**
- 🟢 **gemini-2.5-flash-lite** - Usually available (1,000 RPD buffer)
- 🟢 **gemini-2.0-flash-lite** - Usually available (30 RPM capacity)
- 🟡 **gemini-2.5-flash** - Moderate availability (250 RPD)
- 🟡 **gemini-2.0-flash** - Moderate availability (200 RPD)
- 🔴 **gemini-2.5-pro** - Limited availability (100 RPD)

**Expected Success Rates:**
- **First choice model:** 70-80%
- **With lite model fallback:** 95%+
- **Full 20-combination sequence:** 99%+

## Development Patterns

**Established Patterns:**
- **Async/Await:** All components use modern async patterns
- **Structured Logging:** JSON-based logging throughout
- **Security-First:** Built-in security scanning and validation
- **Modular Design:** Clear separation of concerns
- **Type Safety:** Comprehensive type hints and validation

**Technical Stack:**
- **Language:** Python 3.11+ with type hints
- **Framework:** FastAPI for web interface, asyncio for concurrency
- **Integration:** Home Assistant API, WebSocket communication
- **Testing:** pytest with comprehensive coverage
- **Deployment:** Docker multi-architecture, Home Assistant addon

## Current File Structure

```
/home/drewcifer/aicleaner_v3/
├── addons/aicleaner_v3/           # Main addon code
│   ├── ai/                        # AI provider system
│   ├── core/                      # Core configuration and utilities
│   ├── ha_integration/            # Home Assistant integration
│   ├── security/                  # Security framework
│   ├── zones/                     # Zone management
│   ├── ui/                        # Web interface
│   └── tests/                     # Test suite
├── scripts/                       # Build and release scripts
├── .github/workflows/             # CI/CD pipeline
├── config.yaml                    # Addon configuration
├── Dockerfile                     # Multi-arch Docker build
├── README.md                      # User documentation
├── INSTALL.md                     # Installation guide
└── CHANGELOG.md                   # Version history
```

## Next Steps

**Remaining Work:**
- Complete Phase 5C: Production deployment optimization
- Finalize logging and diagnostics system
- Production testing and validation
- Docker image optimization

**Future Enhancements:**
- Phase 4B: MQTT Discovery integration
- Phase 5A: Advanced performance optimization
- Phase 5B: Enhanced resource management
- Mobile app integration
- Voice control features

---

**Project Philosophy:** Simple, effective Home Assistant addon for personal use with AI-powered automation. Focus on practical functionality over enterprise complexity.