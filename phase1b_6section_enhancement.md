**My Current Thought Process as I Tackle This Task**

Okay, so I've got a pretty specific request. The user, who is clearly an expert, wants me, as Gemini, to demonstrate how to improve Claude's prompts for the AICleaner v3 project.  I'm not just writing code; I'm acting as a collaborative AI partner, a reviewer. I need to showcase this "Enhanced 6-Section Pattern" ? something I'm already quite familiar with ? for "Phase 1B: Configuration Migration & Validation."  This is all about how we should plan a feature.

**First, the `diff` file:**  I need to get into the mindset of a senior engineer working on this. I'm focusing on the practical application of the 6 sections: User-Facing Error Reporting, Structured Logging, Security, Metrics, DevEx, and Documentation.

*   **Error Reporting:** How do we guide users through potential migration issues? It?s important to give helpful, actionable information, and guidance for their benefit.
*   **Logging:** Detailed logs are crucial. I'll need to think about levels, formats (JSON is the obvious choice), and context (e.g., addon version, HA core version).
*   **Security:**  This requires careful consideration.  Config files are a high-value target. I need to make sure we're taking all appropriate security measures, from input validation to avoiding logging sensitive information.
*   **Metrics:** KPIs are a must.  How do we *measure* success? We need to get some performance baseline targets (speed, memory usage), and a benchmarking strategy.
*   **DevEx:**  Code should be readable, testable, and extensible. No magic ? clarity, and maintainability are key.  I'll stress the importance of TDD, as always.
*   **Documentation:** Clear instructions for users *and* developers. It's not just about making the code work; it?s about making the code *usable*.

**Next, the Detailed Analysis:**

Once I've crafted this diff, I?ll analyze the overall pattern against 8 points.  What are the strengths? Areas for improvement? What recommendations can I give?

*   **Strengths:** This pattern is very thorough ? a good professional software engineering approach.
*   **Improvements:** Making it executable could be a focus. MCP integration needs to be clarified.
*   **Recommendations:**  We need a "master prompt" to get the MCP server really integrated.

Finally, I'll give it a readiness score and a verdict. I believe in this, and will make sure the details are precise and useful.
