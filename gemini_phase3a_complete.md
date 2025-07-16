**AICleaner v3: Phase 3A Prompt Review (Gemini Analysis)**

Claude, thank you for providing the detailed prompt for Phase 3A, "Device Detection Enhancement" for AICleaner v3. The zen MCP connection is stable, and I've fully parsed the request. Here's my analysis:

**1. Implementation Readiness**

*   **Strengths:** The prompt's structure is a significant strength. Dividing the task into six sections with four sub-sections provides a clear roadmap for implementation. The request is specific.
*   **Areas for Improvement:** The prompt focuses on *requesting* an implementation plan, but the plan itself is not detailed.
*   **Recommendations:**  Add requirements for concrete artifacts within the prompt, e.g., defined error codes and logging schemas. This clarifies the expected outputs and drives more predictable, testable results.

**2. Quality Integration (TDD/AAA)**

*   **Strengths:** Mentioning TDD/AAA in the overall context is a positive sign.
*   **Areas for Improvement:** The prompt doesn't explicitly mandate a TDD approach or include tests for each section. How do we test documentation?
*   **Recommendations:** Explicitly incorporate a testing strategy or sub-section. Require unit, integration, and E2E tests for new features.

**3. MCP Server Usage**

*   **Strengths:** The prompt acknowledges MCP integration, which is essential for this project.
*   **Areas for Improvement:**  It's too generic. More specification is necessary for the utilization of MCP services.
*   **Recommendations:** Specify how each MCP service (WebFetch, Task, etc.) is to be used. For example, "Use `MCP.Task` for network scans."

**4. Collaborative Process**

*   **Strengths:** The prompt itself demonstrates a well-formed collaborative process, as in Claude providing the prompt to me.
*   **Areas for Improvement:** The process is not formalized.
*   **Recommendations:** Implement a "Review-Refine-Commit" loop with GitHub via `MCP`. Explicitly define the review and feedback cadence.

**5. Risk Management**

*   **Strengths:** The context references GitHub rollback procedures.
*   **Areas for Improvement:** The prompt lacks risk analysis related to device detection.
*   **Recommendations:** Add a "Risk Analysis & Mitigation" section under "Enhanced Security" to address potential feature failures.

**6. HA Compliance**

*   **Strengths:** The prompt correctly identifies the need for HA compliance.
*   **Areas for Improvement:** No specific HA standards are identified.
*   **Recommendations:** Explicitly list relevant HA standards, such as `async_setup_entry` and updates to the `manifest.json`.

**7. Completeness**

*   **Strengths:**  The six sections are comprehensive. The device detection elements are comprehensive.
*   **Areas for Improvement:**  Lacks configuration options for the user.
*   **Recommendations:** Add a "User Configuration & Control" sub-section for user-driven discovery controls.

**8. Production Readiness**

*   **Strengths:**  Following this prompt will lead to high-quality code.
*   **Areas for Improvement:** "Certifiable" is a high bar, implying official HA core review.
*   **Recommendations:** Emphasize aligning with the Home Assistant developer guidelines and incorporate a "Pre-Certification Checklist."

**Consensus on Readiness Level:** 88/100

**Final Verdict:** The prompt's structure is strong. Refinements are needed for specificity around artifacts, testing, and HA compliance. Acting on an improved prompt will lead to a high-quality, production-ready feature. Addon certification is a separate process.

I am ready to proceed with generating the full 6-section implementation once we've aligned on these refinements.
