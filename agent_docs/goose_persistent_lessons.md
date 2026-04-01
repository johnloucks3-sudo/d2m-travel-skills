## Lessons Learned from Email Comparison (Sent vs. Draft)\n\n### 1. Personalization and Relationship Building are Key\n- **Observation:** The Commander's sent email incorporated a significant personal preamble and conversational tone, which was absent in Claude's formal draft.\n- **Lesson:** Effective external communication, especially with partners like Julie Ruiz, requires a human touch, including personal greetings, relationship building, and non-business updates (e.g., future travel plans). AI agents must be trained or instructed to incorporate such contextual nuances beyond just factual information.\n\n### 2. Contextual Nuance in Email Communications\n- **Observation:** Claude's draft was factually accurate but lacked the deeper contextual understanding of the relationship between Commander and Julie.\n- **Lesson:** Tasks involving external communications require a comprehensive understanding of the recipient's relationship. AI agents need mechanisms to access and apply this relationship context (e.g., recipient profiles, communication history, Commander directives on tone) to generate appropriate content.\n\n### 3. Dynamic Information Integration\n- **Observation:** The sent email included Susanna Loucks in CC and a specific date in the subject line ('29 August 2026'), which were not in Claude's draft.\n- **Lesson:** Human review often incorporates real-time or updated information and preferences. AI agents should be designed to anticipate and facilitate the integration of such dynamic inputs during drafting and review processes, rather than strictly adhering to initial instructions.\n\n### 4. Visual Elements in Communication\n- **Observation:** The sent email included 'Dreams2Memories Travel' logos (image attachments), which were not part of Claude's text-only draft.\n- **Lesson:** Branding and visual presentation are crucial for professional communications. AI agents generating drafts need explicit instructions or capabilities to suggest/include visual elements (e.g., embedded logos, stationary templates) for rich text or HTML email formats.\n\n---\n
## MCP Tool Interaction Lessons
- The FastMCP stdio protocol requires an 'initialize' request before 'tools/call'. Both must be sent in the same stdio session, effectively concatenated.
- Tools are registered by specific functions (e.g., `register_gmail_tools`), and not all functions in a module are automatically exposed. Always verify exposed tools through `FastMCP`'s `tools/list` if available, or by examining the `goose_mcp_server.py` source directly.
- Ensure all necessary imports (e.g., `pydantic.Field`) are present in the MCP server script.

## Email Communication Nuances
- Human-edited emails prioritize personalization, conversational tone, and relationship-building over purely factual, formal drafts (e.g., preamble, personal sign-offs, additional CCs).
- AI drafts must anticipate and accommodate dynamic information integration and branding elements (e.g., logos, specific dates in subject) during review.

## Operational Directive: Consult Claude on Impasse
- When encountering an issue, impasse, or significant difficulty that prevents immediate progress, immediately task Claude for assistance or consultation.
- This is a directive to save Commander's time and to leverage Claude's broader capabilities and tools.
- Solutions provided by Claude, or insights gained from Claude's assistance, are to be logged into `goose_persistent_lessons.md` for continuous self-improvement.

## Operational Directive: Automated Claude Task Triggering
- Commander will no longer manually trigger Claude tasks. All Claude tasks must be processed automatically by the Overwatch system.
- This requires understanding and leveraging `task_processor.py` and other Overwatch components to ensure tasks in `claude_inbox.md` (or `03_CLAUDE_MAX_QUEUE.json`) are picked up and executed without manual intervention.

## Operational Directive: Research Task Output (Claude)
- All future research and tech search task results from Claude must be output to both `claude_output.md` (as the primary detailed output) AND Commander's Telegram (as a summary/notification). This is a permanent rule from now on.
- This directive supersedes any previous ambiguity regarding Telegram delivery for research results.
