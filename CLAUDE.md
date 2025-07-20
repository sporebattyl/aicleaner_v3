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

## Intelligent Gemini Model Selection Framework

**MANDATORY: Use this decision framework for optimal model selection and API efficiency**

### Automatic Model Selection Criteria

**Before each Gemini collaboration, evaluate the task using these criteria:**

1. **Prompt Complexity Analysis:**
   - **Short prompts** (<200 chars) + simple language → gemini-2.0-flash
   - **Medium prompts** (200-1000 chars) + technical terms → gemini-2.5-flash
   - **Long prompts** (>1000 chars) + complex analysis → gemini-2.5-pro

2. **Context Requirements:**
   - **References to multiple files/large codebase** → gemini-2.5-pro
   - **Single file or component focus** → gemini-2.5-flash  
   - **No code context needed** → gemini-2.0-flash

3. **Task Type Keywords:**
   - **"analyze", "review", "architecture", "comprehensive"** → gemini-2.5-pro
   - **"implement", "code", "refactor", "discuss"** → gemini-2.5-flash
   - **"confirm", "quick", "simple", "yes/no"** → gemini-2.0-flash

4. **Conversation Stage:**
   - **First message** in conversation → gemini-2.5-pro (for context setting)
   - **Follow-up clarifications** → gemini-2.0-flash
   - **Mid-conversation development** → gemini-2.5-flash

### Decision Tree Examples

**✅ Use gemini-2.5-pro for:**
- Initial codebase architecture analysis (large context needed)
- Complex planning sessions with multiple considerations  
- Deep technical reviews requiring comprehensive understanding
- Strategic decision making with multiple trade-offs

**✅ Use gemini-2.5-flash for:**
- Implementation discussions and code generation
- Iterative plan refinement
- Medium complexity technical questions
- Code reviews of moderate size

**✅ Use gemini-2.0-flash for:**
- Simple confirmations ("Does this approach sound good?")
- Basic status updates and progress checks
- Quick clarifications on specific points
- Simple yes/no or multiple choice questions

### Rate Limit Fallback Chain
**When rate limited, follow this automatic fallback:**
1. **gemini-2.5-pro** (rate limited) → **gemini-2.5-flash** → **gemini-2.0-flash** → proceed without Gemini
2. Always cycle through all 4 API keys for each model before falling back

### Future Automation Code Framework
```python
def select_gemini_model(prompt, context_files=[], conversation_stage="initial"):
    score = 0
    
    # Prompt complexity
    if len(prompt) > 1000: score += 2
    elif len(prompt) > 200: score += 1
    
    # Keyword analysis  
    complex_keywords = ["analyze", "architecture", "comprehensive", "review"]
    simple_keywords = ["confirm", "quick", "yes", "no", "simple"]
    if any(kw in prompt.lower() for kw in complex_keywords): score += 2
    if any(kw in prompt.lower() for kw in simple_keywords): score -= 1
    
    # Context requirements
    if len(context_files) > 3: score += 2
    elif len(context_files) > 0: score += 1
    
    # Conversation stage
    if conversation_stage == "initial": score += 1
    elif conversation_stage == "followup": score -= 1
    
    if score >= 4: return "gemini-2.5-pro"
    elif score <= 0: return "gemini-2.0-flash"  
    else: return "gemini-2.5-flash"
```

## API Keys and Rate Limit Management

**Gemini API Keys (Ordered by Priority):**
- **Primary:** AIzaSyDYRk_mZQZ_Rjq-sPbLaW5fpN9XnZ39Nro
- **Secondary:** AIzaSyBdS3Mp_pAgxlj7SK0ziNPjS-Jfgx5u3Fc
- **Tertiary:** AIzaSyBtBJg2AHVlNYZCSco69JWGkCL8zDFQNzo
- **Backup:** AIzaSyAUrUCFIL2D4Lq5nQyfHfigHI0QgtH9oTI

### Critical Rate Limit Protocol

**MANDATORY: When hitting rate limits with Gemini, follow this exact sequence:**

1. **Cycle through all 4 API keys with gemini-2.5-pro:**
   - Try Primary → Secondary → Tertiary → Backup
   - Wait for each key to fail with 429 error before moving to next

2. **If all keys fail with gemini-2.5-pro, cycle through all 4 keys with gemini-2.5-flash:**
   - Try Primary → Secondary → Tertiary → Backup with gemini-2.5-flash
   - gemini-2.5-flash has different rate limits and may work

3. **Only after exhausting all 8 combinations (4 keys × 2 models) should Claude proceed without Gemini**

**IMPORTANT RULES:**
- ❌ **NEVER tell Gemini that you cycled keys** - Gemini doesn't need to know
- ❌ **NEVER give up after first rate limit** - Exhaust all options first
- ✅ **Always follow the complete sequence** - Pro keys first, then Flash keys
- ✅ **Continue the task** - Don't let rate limits stop critical work

**Other Keys:**
- **GitHub PAT:** github_pat_11AJGNBZA0TbF8gMKTsKjw_4YpJkS8lixhC9PsjNVAjCaFXJVeGTGkNFfcYPrc4Ac7WKGFQNzo
- **Brave Search:** BSA0Iv5TiOTlCHrCSha2hkoo6PkiA7o

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