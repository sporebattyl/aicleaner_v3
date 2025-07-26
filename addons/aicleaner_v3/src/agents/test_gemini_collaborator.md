# Test Case for Gemini Collaboration Agent

## Test Scenario: Simple Configuration Update

Let's test the agent with a realistic but simple task to validate the workflow.

### Test Task
```
Task(
    description="Update API rate limiting configuration",
    prompt="I need to update the API rate limiting configuration in our Express.js application. Current file is src/middleware/rateLimit.js with basic rate limiting (100 requests per 15 minutes). Requirements: increase to 200 requests per 10 minutes, add IP whitelist for admin users (192.168.1.0/24), add custom error messages, maintain backward compatibility with existing endpoints.",
    subagent_type="gemini-collaborator"
)
```

### Expected Workflow

#### Step 1: CONSULT
- Agent should present the rate limiting problem to Gemini
- Gemini should analyze current configuration and suggest improvements
- Should identify key areas: rate limits, IP whitelisting, error handling

#### Step 2: ANALYZE  
- Claude should evaluate Gemini's approach
- Should identify security considerations (IP validation, error message exposure)
- Should consider performance impact of new configurations

#### Step 3: REFINE
- Agent should iterate with Gemini on any concerns
- Should refine approach based on Claude's security and performance feedback
- Should confirm final implementation strategy

#### Step 4: GENERATE
- Gemini should provide specific code changes
- Should include exact line numbers and diffs
- Should specify configuration changes needed

#### Step 5: REVIEW
- Claude should validate all security aspects
- Should check IP whitelist format and validation
- Should verify error messages don't expose sensitive info

#### Step 6: IMPLEMENT
- Agent should apply changes using filesystem tools
- Should modify src/middleware/rateLimit.js appropriately
- Should handle any integration issues

#### Step 7: VALIDATE
- Should test that rate limiting works as expected
- Should verify IP whitelist functionality
- Should confirm backward compatibility

### Success Criteria

1. **Workflow Completion**: All 7 steps executed successfully
2. **Functional Changes**: Rate limiting updated to new specifications
3. **Security Validated**: IP whitelist properly implemented and validated
4. **Compatibility Maintained**: Existing endpoints continue to work
5. **Documentation**: Clear summary of changes and impact
6. **Error Handling**: Graceful handling of any issues during workflow

### Test Validation

The agent should:
- ✅ Follow the 7-step workflow systematically
- ✅ Use TodoWrite to track progress through each step
- ✅ Provide clear status updates at each phase
- ✅ Successfully collaborate with Gemini (or gracefully handle quota limits)
- ✅ Validate security and compatibility at each stage
- ✅ Deliver a working solution with proper documentation

This test case provides a good balance of complexity to validate the agent workflow without being overly complicated for initial testing.