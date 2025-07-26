# Gemini Collaboration Agent - Example Usage

## Example Task: Refactor Database Connection Pool

### Initial Request
```
Task(
    description="Optimize database connection pooling",
    prompt="I need to refactor our database connection pooling system to improve performance and reduce connection leaks. Current implementation uses basic mysql2 pool in src/database/connection.js. We're seeing connection timeouts under load. Requirements: maintain existing API compatibility, add connection monitoring, implement proper cleanup, support connection retry logic.",
    subagent_type="gemini-collaborator"
)
```

### Step-by-Step Execution

#### Step 1: CONSULT 🤝
**Agent Action**: Consult with Gemini about the database pooling problem

```markdown
## Step 1: CONSULT

### Gemini Consultation:
Presented the database connection pooling optimization problem to Gemini. Gemini analyzed the requirements and suggested:

1. **Connection Pool Configuration**: Implement advanced pool settings with proper min/max connections
2. **Health Monitoring**: Add connection health checks and metrics
3. **Retry Logic**: Implement exponential backoff for failed connections
4. **Graceful Cleanup**: Proper connection lifecycle management
5. **Load Balancing**: Consider read/write splitting for better performance

Gemini recommended using mysql2's advanced pooling features with custom monitoring wrapper.

### Progress Update:
✅ Problem presented to Gemini - moving to analysis phase
```

#### Step 2: ANALYZE 🔍
**Agent Action**: Compare Gemini's approach with Claude's assessment

```markdown
## Step 2: ANALYZE

### Claude Validation:
Analyzing Gemini's proposed approach:

**Strengths**:
- Comprehensive connection lifecycle management
- Good separation of concerns with monitoring wrapper
- Proper error handling and retry logic

**Concerns**:
- Need to ensure backward compatibility with existing API
- Security: connection string handling and credential management
- Performance: monitoring overhead should be minimal
- Testing: need comprehensive test coverage for edge cases

**Recommendation**: Proceed with Gemini's approach but add security validations and performance monitoring.

### Progress Update:
✅ Analysis complete - proceeding to refinement
```

#### Step 3: REFINE 🎯
**Agent Action**: Iterate with Gemini to refine the solution

```markdown
## Step 3: REFINE

### Gemini Consultation:
Discussed concerns with Gemini and refined the approach:

1. **Security**: Added credential encryption and secure storage
2. **Compatibility**: Wrapper pattern to maintain existing API
3. **Performance**: Lazy loading of monitoring features
4. **Testing**: Added comprehensive test scenarios including edge cases

**Final Architecture**:
- `DatabasePool` class with connection management
- `PoolMonitor` class for health tracking  
- `ConnectionRetry` utility for failure handling
- Backward-compatible API wrapper

### Progress Update:
✅ Solution refined and agreed upon - generating implementation details
```

#### Step 4: GENERATE ⚙️
**Agent Action**: Get precise implementation details from Gemini

```markdown
## Step 4: GENERATE

### Implementation Plan from Gemini:

**Files to Modify**:
1. `src/database/connection.js` - Main connection pool implementation
2. `src/database/monitor.js` - New monitoring system
3. `src/database/retry.js` - New retry logic utility
4. `tests/database/connection.test.js` - Updated tests

**Key Code Changes**:
- Replace simple pool with advanced configuration
- Add connection health checks every 30 seconds
- Implement exponential backoff (100ms → 1.6s → 25.6s)
- Add connection leak detection and auto-cleanup

### Progress Update:
✅ Detailed implementation plan received - proceeding to review
```

#### Step 5: REVIEW 🛡️
**Agent Action**: Claude validates the implementation plan

```markdown
## Step 5: REVIEW

### Claude Validation:
Reviewing all proposed changes:

**Security Check**: ✅
- Credentials properly encrypted
- No SQL injection vectors
- Secure connection string handling

**Integration Check**: ✅  
- Maintains backward compatibility
- Proper error propagation
- No breaking API changes

**Performance Check**: ✅
- Monitoring has minimal overhead
- Connection reuse optimized
- Memory leak prevention

**Code Quality**: ✅
- Following existing patterns
- Proper error handling
- Comprehensive logging

### Approval: Ready for implementation

### Progress Update:
✅ Review complete and approved - beginning implementation
```

#### Step 6: IMPLEMENT 🔨
**Agent Action**: Apply changes using filesystem tools

```markdown
## Step 6: IMPLEMENT

### Implementation Progress:

1. **Created monitoring system**: ✅
   - Added `src/database/monitor.js` with health checks
   - Integrated performance metrics collection

2. **Created retry utility**: ✅  
   - Added `src/database/retry.js` with exponential backoff
   - Added circuit breaker pattern for failed connections

3. **Updated main connection**: ✅
   - Modified `src/database/connection.js` with new pool configuration
   - Added proper cleanup and lifecycle management
   - Maintained backward compatibility

4. **Updated tests**: ✅
   - Added comprehensive test coverage
   - Added edge case testing for connection failures

### Progress Update:
✅ All changes implemented successfully - proceeding to validation
```

#### Step 7: VALIDATE ✅
**Agent Action**: Comprehensive verification

```markdown
## Step 7: VALIDATE

### Validation Results:

**Tests**: ✅ All tests passing (23/23)
**Linting**: ✅ No style issues
**Functionality**: ✅ Connection pooling working correctly
**Performance**: ✅ 40% improvement in connection reuse
**Monitoring**: ✅ Health checks reporting properly

### Implementation Summary:

**Files Modified**:
- `src/database/connection.js` - Enhanced with advanced pooling
- `src/database/monitor.js` - New monitoring system  
- `src/database/retry.js` - New retry logic
- `tests/database/connection.test.js` - Updated test coverage

**Key Improvements**:
- 40% better connection reuse efficiency
- Automatic connection leak detection and cleanup
- Comprehensive health monitoring and alerting
- Robust retry logic with exponential backoff
- Full backward compatibility maintained

**Usage**: No changes required for existing code - all improvements are transparent to consumers.

### 🎉 Gemini Collaboration Workflow Complete!
```

## Key Features Demonstrated

1. **Structured Progress**: Clear step-by-step progression with status updates
2. **Gemini Integration**: Real consultations with Gemini for analysis and implementation
3. **Claude Validation**: Security, performance, and integration validation at each step
4. **Practical Implementation**: Actual file changes using MCP tools
5. **Comprehensive Testing**: Validation of functionality and performance
6. **Documentation**: Clear summary of changes and improvements

## Usage Tips

- **Be Specific**: Provide detailed problem descriptions and requirements
- **Include Context**: Share relevant file paths and existing code structure  
- **Set Constraints**: Clearly define backward compatibility and performance needs
- **Trust the Process**: Let the agent manage the collaboration workflow
- **Review Outputs**: The agent provides detailed summaries for verification