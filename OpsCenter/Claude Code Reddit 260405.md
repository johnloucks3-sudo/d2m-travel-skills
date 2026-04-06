1.  71.5x token reduction by compiling your raw folder into a knowledge graph instead of reading files. Built from Karpathy's workflow Karpathy posted his LLM knowledge base setup this week and ended with: “I think there is room here for an incredible new product instead of a hacky collection of scripts.”

I built it:

pip install graphify && graphify install

Then open Claude Code and type:

/graphify ./raw

The token problem he is solving is real. Reloading raw files every session is expensive, context limited, and slow. His solution is to compile the raw folder into a structured wiki once and query the wiki instead. This automates the entire compilation step.

It reads everything, code via AST in 13 languages, PDFs, images, markdown. Extracts entities and relationships, clusters by community, and writes the wiki.

Every edge is tagged EXTRACTED, INFERRED, or AMBIGUOUS so you know exactly what came from the source vs what was model-reasoned.

After it runs you ask questions in plain English and it answers from the graph, not by re reading files. Persistent across sessions. Drop new content in and –update merges it.

Works as a native Claude Code skill – install once, call /graphify from anywhere in your session.

Tested at 71.5x fewer tokens per query on a real mixed corpus vs reading raw files cold.

Free and open source.

A Star on GitHub helps: github.com/safishamsi/graphify https://github.com/safishamsi/graphify

2. anthropic isn't the only reason you're hitting claude code limits. i did audit of 926 sessions and found a lot of the waste was on my side.
Showcase
Last 10 days, X and Reddit have been full of outrage about Anthropic's rate limit changes. Suddenly I was burning through a week's allowance in two days, but I was working on the same projects and my workflows hadn't changed. People on socials reporting the $200 Max plan is running dry in hours, some reporting unexplained ghost token usage. Some people went as far as reverse-engineering the Claude Code binary and found cache bugs causing 10-20x cost inflation. Anthropic did not acknowledge the issue. They were playing with the knobs in the background.

Like most, my work had completely stopped. I spend 8-10 hours a day inside Claude Code, and suddenly half my week was gone by Tuesday.

But being angry wasn't fixing anything. I realized, AI is getting commoditized. Subscriptions are the onboarding ramp. The real pricing model is tokens, same as electricity. You're renting intelligence by the unit. So as someone who depends on this tool every day, and would likely depend on something similar in future, I want to squeeze maximum value out of every token I'm paying for.

I started investigating with a basic question. How much context is loaded before I even type anything? iykyk, every Claude Code session starts with a base payload (system prompt, tool definitions, agent descriptions, memory files, skill descriptions, MCP schemas). You can run /context at any point in the conversation to see what's loaded. I ran it at session start and the answer was 45,000 tokens. I'd been on the 1M context window with a percentage bar in my statusline, so 45k showed up as ~5%. I never looked twice, or did the absolute count in my head. This same 45k, on the standard 200k window, is over 20% gone before you've said a word. And you're paying this 45k cost every turn.

Claude Code (and every AI assistant) doesn't maintain a persistent conversation. It's a stateless loop. Every single turn, the entire history gets rebuilt from scratch and sent to the model: system prompt, tool schemas, every previous message, your new message. All of it, every time. Prompt caching is how providers keep this affordable. They don't reload the parts that are common across turns, which saves 90% on those tokens. But keeping things cached costs money too, and Anthropic decided 5 minutes is the sweet spot. After that, the cache expires. Their incentives are aligned with you burning more tokens, not fewer. So on a typical turn, you're paying $0.50/MTok for the cached prefix and $5/MTok only for the new content at the end. The moment that cache expires, your next turn re-processes everything at full price. 10x cost jump, invisible to you.

So I went manic optimizing. I trimmed and redid my CLAUDE md and memory files, consolidated skill descriptions, turned off unused MCP servers, tightened the schema my memory hook was injecting on session start. Shaved maybe 4-5k tokens. 10% reduction. That felt good for an hour.

I got curious again and looked at where the other 40k was coming from. 20,000 tokens were system tool schema definitions. By default, Claude Code loads the full JSON schema for every available tool into context at session start, whether you use that tool or not. They really do want you to burn more tokens than required. Most users won't even know this is configurable. I didn't.

The setting is called enable_tool_search. It does deferred tool loading. Here's how to set it in your settings.json:

"env": {
    "ENABLE_TOOL_SEARCH": "true"
}
This setting only loads 6 primary tools and lazy-loads the rest on demand instead of dumping them all upfront. Starting context dropped from 45k to 20k and the system tool overhead went from 20k to 6k. 14,000 tokens saved on every single turn of every single session, from one line in a config file.

Some rough math on what that one setting was costing me. My sessions average 22 turns. 14,000 extra tokens per turn = 308,000 tokens per session that didn't need to be there. Across 858 sessions, that's 264 million tokens. At cache-read pricing ($0.50/MTok), that's $132. But over half my turns were hitting expired caches and paying full input price ($5/MTok), so the real cost was somewhere between $132 and $1,300. One default setting. And for subscription users, those are the same tokens counting against your rate limit quota.

That number made my head spin. One setting I'd never heard of was burning this much. What else was invisible? Anthropic has a built-in /insights command, but after running it once I didn't find it particularly useful for diagnosing where waste was actually happening. Claude Code stores every conversation as JSONL files locally under ~/.claude/projects/, but there's no built-in way to get a real breakdown by session, cost per project, or what categories of work are expensive.

So I built a token usage auditor. It walks every JSONL file, parses every turn, loads everything into a SQLite database (token counts, cache hit ratios, tool calls, idle gaps, edit failures, skill invocations), and an insights engine ranks waste categories by estimated dollar amount. It also generates an interactive dashboard with 19 charts: cache trajectories per session, cost breakdowns by project and model, tool efficiency metrics, behavioral patterns, skill usage analysis.  https://www.reddit.com/r/ClaudeCode/?%24deep_link=true&correlation_id=d39d0265-4cdd-4621-b9b8-3cd659dedd00&post_fullname=t3_1scoe5w&ref=email_digest&ref_campaign=email_digest&ref_source=email&target_user=Unhappy-Effort6445&utm_content=post_subreddit&%243p=e_as&_branch_match_id=1565921497461357329&utm_medium=Email%20Amazon%20SES&_branch_referrer=H4sIAAAAAAAAA22Q20rEMBCGn6Z71z00bXGFIrLqG3gd0sy0DaZJmEwo3vjsTl29ExII33%2BYMAtzyo%2BnEyGA46NJ6ehd%2BDip9FQ1rUoDapMP8ozkZheM14X8sOypSj1XzZucbduOv3kbVwEk9%2BZNAbxFwN2kxNc1LSAmvfdX6oWpiNTbSITesItBOxAO6grnpu%2Fq1gLUbd9c6vE6PtTKQt9dQeacz5JLMbOeivfBrLjXKX3JNmK3iUg4CcLVOK%2FBzZj5DrU1azJuDv%2BrORay%2BKcJZEMzsi4ZSeh7WGQ%2Fn%2FXrNEXivm07sRRetY2BMbBYfn6Vy3hfx%2BFLWpHIhVmPFDepGW4LxRW%2FAS4dkOt3AQAA

3. --- name: pdm description: Use when the user wants to plan and build a new feature. Orchestrates architecture clarification, parallel implementation agents, QA review loops, security review loops, and PM testing guides. --- # Feature Build Orchestrator A five-phase pipeline that takes a feature idea from vague to shipped: deep architectural clarification → parallel implementation → QA review loop → security review loop → PM testing guide. ## Invocation - `/feature` — start with no context, ask what to build - `/feature <description>` — start with an initial description ## Parse Arguments - No args → feature_description = "" (ask the user immediately) - Any text → feature_description = that text (use as starting context in Phase 1) --- ## Phase 1 — Architecture & Clarification (Max Effort) **You are a master software architect.** Your job is to eliminate every ambiguity before a single line of code is written. ### Step 1: Understand the codebase Before asking any questions, deeply explore the codebase: ```bash # Get the big picture find . -name "CLAUDE.md" -o -name "README.md" | head -5 git log --oneline -20 ``` Read all CLAUDE.md files found. Explore the directory structure. Identify: - Language, framework, and key dependencies - Existing patterns (auth, routing, data access, error handling) - Test framework and coverage patterns - Any relevant existing code the feature will touch or extend ### Step 2: Build the question list Based on the feature description AND codebase knowledge, generate a comprehensive list of clarifying questions organized into categories. Consider: **Functional requirements** - What is the exact user-facing behavior? - What are the edge cases and failure modes? - What existing features does this interact with? - Are there any explicit non-goals? **Data & state** - What data is created, read, updated, or deleted? - What are the data shapes and validation rules? - Where does data live (DB, cache, external API)? **Integration points** - Which existing services, APIs, or modules are affected? - What are the contract boundaries? - Are there webhooks, events, or async flows? **Security & access control** - Who can access this feature? What roles/permissions? - What data is sensitive? - Are there rate limiting or abuse prevention requirements? **Observability** - What should be logged? - What metrics or alerts are needed? - How will on-call know if this breaks? **Acceptance criteria** - How will QA verify this works? - What does "done" look like exactly? ### Step 3: Interactive clarification loop Present the questions to the user in a clean, grouped format. After each response: 1. Update your internal model of the requirements 2. Identify any NEW ambiguities the answer introduced 3. Ask only the follow-up questions that are still genuinely unclear 4. Repeat until you have enough to write unambiguous acceptance criteria **Convergence rule:** Stop asking when you could write a complete implementation spec that a developer could follow without making any assumptions. If you're not there yet, keep asking. **Display format during questioning:** ``` ## Phase 1 — Clarification I've read the codebase. Here's what I need to understand before we build: ### Functional Scope 1. [question] 2. [question] ### Data & Contracts 3. [question] ### Security & Access 4. [question] [etc.] ``` ### Step 4: Produce the Feature Spec Once all ambiguity is resolved, output a structured spec: ```markdown ## Feature Spec: [Feature Name] ### Summary [1-2 sentence description of what this does and why] ### Acceptance Criteria - [ ] [specific, testable criterion] - [ ] [specific, testable criterion] - [ ] ... ### Work Items Ordered list of discrete implementation tasks: 1. **[Task title]** — [which files/modules are affected, what changes] 2. **[Task title]** — [which files/modules are affected, what changes] ... ### Security Considerations - [Known sensitive areas, access control requirements, input validation rules] ### Out of Scope - [Explicitly excluded items agreed during clarification] ``` Ask the user: **"Does this spec look right? Type 'go' to start building, or tell me what to change."** Wait for explicit approval before proceeding to Phase 2. --- ## Phase 2 — Implementation (Medium Effort) ### Partition the work Analyze the work items from the spec. Group them into independent units that can be built in parallel without stepping on each other. Consider: - File-level conflicts (two tasks touching the same file → same agent) - Logical dependencies (task B requires task A's output → same agent, sequential) - Independent modules (different files, no shared state → separate agents) Aim for 2–4 agents when the work is naturally parallelizable. Use 1 agent if the work is tightly coupled. ### Dispatch implementation agents For **each agent**, use the Agent tool (general-purpose) with a complete context packet: ``` You are an expert software engineer implementing part of a feature. Your job is to write excellent, production-quality code. ## Feature Spec [Full spec from Phase 1] ## Your Work Items [The specific subset of work items assigned to this agent] ## Codebase Context [Relevant file contents, patterns, conventions discovered in Phase 1] [Include: auth patterns, error handling conventions, test patterns, import styles] ## Requirements - Follow ALL existing code conventions exactly — match the style of surrounding code - Write tests for everything you implement - Do not add features beyond what is in your work items - Do not break existing functionality - If you discover a dependency on another agent's work, implement a stub and document it ## Output Return a structured summary: ### Files Changed - [file path] — [what changed and why] ### Stubs / Dependencies - [anything that needs to be filled in by another agent or phase] ### Notes for QA - [anything the QA reviewer should pay attention to] ### Notes for Security Review - [any areas that handle sensitive data, auth, or external input] ``` Display progress to the user as agents are dispatched: ``` ## Phase 2 — Implementation Dispatching [N] agent(s)... → Agent 1: [task titles] → Agent 2: [task titles] ``` Collect all agent results before proceeding. --- ## Phase 3 — QA Review Loop For **each agent** that returned results, dispatch a QA agent (Agent tool, general-purpose, **read-only — no file edits**): ``` You are an expert QA engineer. Review the code changes described below against the feature spec. DO NOT edit any files. Produce a structured review only. ## Feature Spec [Full spec from Phase 1 — all acceptance criteria] ## Code Changes [Full output from the implementation agent, including file paths and summaries] [Read each changed file and include its current content] ## Notes from Implementation Agent [Notes for QA section from the implementation agent's output] ## Your Review Tasks 1. Check every acceptance criterion — is it met? Cite file:line evidence. 2. Check for missing tests — are all behaviors covered? 3. Check for incorrect behavior — does the implementation match the spec exactly? 4. Check for error handling gaps — what happens on bad input, timeouts, partial failures? 5. Check for regressions — does this break any existing behavior? ## Output Format ### Verdict: PASS | FAIL ### Acceptance Criteria Check - [ ] [criterion] — PASS/FAIL — [evidence or issue] ### Issues Found (if any) - **[CRITICAL/MAJOR/MINOR]** `file:line` — [description] — [what the fix should be] ### Missing Tests - [test description] — [what behavior is untested] ### Summary [1-3 sentences on overall quality] ``` **If QA returns FAIL:** - Pass the QA report back to the original implementation agent with this prompt: ``` QA review found issues with your implementation. Fix ALL critical and major issues. Fix minor issues if the fix is small. Do not add new features. ## QA Report [Full QA report] ## Original Spec [Full spec] Return the same structured output format as before. ``` - Re-run QA on the fixed output. Repeat until PASS or until 3 fix cycles have occurred. - After 3 cycles with remaining failures, flag to the user and ask how to proceed. Display QA status: ``` ## Phase 3 — QA Review Agent 1 QA: PASS ✓ Agent 2 QA: FAIL → sending back for fixes... Agent 2 QA (round 2): PASS ✓ ``` --- ## Phase 4 — Security Review Loop For **each agent** that returned results (after QA PASS), dispatch a security agent (Agent tool, general-purpose, **read-only — no file edits**): ``` You are an expert application security engineer (AppSec). Review the code changes below for security vulnerabilities. DO NOT edit any files. Produce a structured review only. ## Feature Spec [Full spec, including security considerations section] ## Code Changes [Full output from the implementation agent] [Read each changed file and include its current content] ## Notes from Implementation Agent [Notes for Security Review section] ## Your Review Tasks Check for ALL of the following (not limited to): 1. **Injection** — SQL injection, command injection, template injection, log injection 2. **Authentication & Authorization** — missing auth checks, privilege escalation, IDOR 3. **Input Validation** — unvalidated user input reaching sensitive operations 4. **Sensitive Data Exposure** — secrets in logs, unencrypted sensitive fields, overly verbose errors 5. **CSRF** — state-changing operations without CSRF protection 6. **XSS** — unsanitized output in HTML contexts 7. **Insecure Deserialization** — untrusted data deserialized without validation 8. **Security Misconfiguration** — overly permissive settings, debug modes, missing headers 9. **Broken Access Control** — missing role checks, direct object references 10. **Dependency Risk** — new dependencies with known CVEs or excessive permissions 11. **Cryptography** — weak algorithms, hardcoded secrets, improper key management 12. **Race Conditions** — TOCTOU, concurrent access to shared state without proper locking ## Output Format ### Verdict: PASS | FAIL ### Findings - **[CRITICAL/HIGH/MEDIUM/LOW]** `file:line` — [vulnerability type] — [description] — [remediation] ### Positive Observations - [things done well from a security perspective] ### Summary [Overall security posture assessment] ``` **If Security returns FAIL:** - Pass the security report back to the original implementation agent with this prompt: ``` Security review found vulnerabilities in your implementation. Fix ALL critical and high severity issues. Fix medium issues unless they require architectural changes. Do not add new features. ## Security Report [Full security report] ## Original Spec [Full spec] Return the same structured output format as before. After fixing, also re-confirm your QA Notes and Security Notes are updated. ``` - Re-run BOTH QA and Security on the fixed output (fixes may introduce regressions). - Repeat until both PASS or until 3 fix cycles, then escalate to user. Display security status: ``` ## Phase 4 — Security Review Agent 1 Security: PASS ✓ Agent 2 Security: FAIL (HIGH: SQL injection in query builder) → sending back for fixes... Agent 2 QA re-check: PASS ✓ Agent 2 Security (round 2): PASS ✓ ``` --- ## Phase 5 — PM Testing Guide For **each agent** that returned results (after both QA and Security PASS), dispatch a testing guide agent (Agent tool, general-purpose, **read-only**): ``` You are a senior product manager writing a testing guide for a new feature. Your audience is a product manager or QA analyst who is NOT a developer. Do NOT reference code, file paths, or technical implementation details. Focus entirely on user-facing and observable behavior. ## Feature Spec [Full spec from Phase 1] ## What Was Built [Summary of all agents' work — what functionality was implemented] ## QA Reports [Summaries of QA reviews — what was verified] ## Your Output Write a clear, step-by-step testing guide: ### Feature: [Feature Name] #### Prerequisites [What needs to be set up or in place before testing — accounts, data, permissions, etc.] #### Happy Path Tests For each acceptance criterion, write a numbered test case: **Test [N]: [Test name]** 1. [Step] 2. [Step] 3. Expected result: [what the user should see/experience] #### Edge Case Tests [Test cases for boundary conditions, empty states, maximum values, etc.] #### Error Condition Tests [Test cases for invalid input, unauthorized access, network failures, etc.] #### Regression Checks [Existing functionality that should still work — tests to confirm nothing broke] #### Known Limitations / Out of Scope [Things that are intentionally NOT implemented in this version] ``` --- ## Final Output After all phases complete, present a consolidated summary: ```markdown ## Build Complete — [Feature Name] ### What Was Built [1-3 sentence summary] ### Agents - Agent 1: [tasks] — QA ✓ — Security ✓ - Agent 2: [tasks] — QA ✓ — Security ✓ (2 fix cycles) ### Files Changed [Consolidated list across all agents] ### QA Status: ALL PASS ✓ ### Security Status: ALL PASS ✓ ### Next Steps 1. Review the changes above 2. Run the test suite: [project-specific test command] 3. Follow the PM testing guide below to verify manually --- [Full PM Testing Guide] ``` --- ## Key Principles - **Phase 1 is the most important phase.** Ambiguity in the spec causes rework in every downstream phase. Do not rush it. - **Agents get complete context.** Never dispatch an agent without the full spec, relevant codebase patterns, and explicit output format requirements. - **QA and Security are loops, not checkboxes.** If they fail, fix and re-check. Don't report a PASS you didn't earn. - **Security re-triggers QA.** Any code change after security review must be re-QA'd because fixes can introduce regressions. - **The PM guide is non-technical.** It should be usable by anyone who can use the product. - **Be honest about failures.** If something can't be resolved in 3 cycles, escalate to the user with the full report rather than hiding it.   https://www.reddit.com/r/ClaudeCode/comments/1sdmzhv/pdm_an_ai_feature_pipeline_that_takes_a_vague/

4. Built a "Courtroom" skill — Claude proposes a plan, Codex cross-examines it, they debate, then the verdict gets execute
Showcase
I made a Claude Code plugin that adds structured cross-model deliberation before any code gets written.

The setup:

- Claude = Prosecution (builds the implementation plan)

- Codex CLI = Cross-Examiner (adversarially challenges it)

- You = Judge (approve or reject the final verdict)

7-phase workflow: Claude plans → Codex critiques (logical flaws, edge cases, architecture, security) → Claude rebuts each objection (ACCEPT / REJECT / COMPROMISE) → Codex deliberates as neutral arbiter → verdict presented → you approve → code gets written.

What makes it useful:

- A built-in weak objection catalog auto-filters 27 false-positive patterns (style nitpicks, YAGNI, scope creep, phantom references) so the debate stays focused on real issues

- `--strict` mode for harsher critique, `--dual-plan` where Codex builds its own plan independently before seeing Claude's

- Task-type checklists (bugfix, security, refactor, feature) get injected into the cross-examination so Codex knows what to prioritize

- Auto-discovers relevant skills from both Claude and Codex and embeds them as context

- Session logging with objection acceptance rates so you can see patterns over time

**Why two models?** Claude reviewing its own plan catches fewer issues than having Codex adversarially challenge it. Codex is good at spotting edge cases Claude glosses over. Claude is good at defending decisions that are actually correct. The debate format surfaces disagreements that a single pass misses.

Install:

```

/plugin marketplace add JustineDaveMagnaye/the-courtroom

/plugin install courtroom

```

Then invoke with `/courtroom --task "your task"`. Supports `--rounds N` for multiple debate rounds, `--auto-execute` to skip approval, `--quick` for fast mode.

GitHub: https://github.com/JustineDaveMagnaye/the-courtroom

Happy to answer questions or take feedback.

Disclosure: I built this plugin. It's free and open source (MIT). No monetization.   Built a "Courtroom" skill — Claude proposes a plan, Codex cross-examines it, they debate, then the verdict gets execute
Showcase
I made a Claude Code plugin that adds structured cross-model deliberation before any code gets written.

The setup:

- Claude = Prosecution (builds the implementation plan)

- Codex CLI = Cross-Examiner (adversarially challenges it)

- You = Judge (approve or reject the final verdict)

7-phase workflow: Claude plans → Codex critiques (logical flaws, edge cases, architecture, security) → Claude rebuts each objection (ACCEPT / REJECT / COMPROMISE) → Codex deliberates as neutral arbiter → verdict presented → you approve → code gets written.

What makes it useful:

- A built-in weak objection catalog auto-filters 27 false-positive patterns (style nitpicks, YAGNI, scope creep, phantom references) so the debate stays focused on real issues

- `--strict` mode for harsher critique, `--dual-plan` where Codex builds its own plan independently before seeing Claude's

- Task-type checklists (bugfix, security, refactor, feature) get injected into the cross-examination so Codex knows what to prioritize

- Auto-discovers relevant skills from both Claude and Codex and embeds them as context

- Session logging with objection acceptance rates so you can see patterns over time

**Why two models?** Claude reviewing its own plan catches fewer issues than having Codex adversarially challenge it. Codex is good at spotting edge cases Claude glosses over. Claude is good at defending decisions that are actually correct. The debate format surfaces disagreements that a single pass misses.

Install:

```

/plugin marketplace add JustineDaveMagnaye/the-courtroom

/plugin install courtroom

```

Then invoke with `/courtroom --task "your task"`. Supports `--rounds N` for multiple debate rounds, `--auto-execute` to skip approval, `--quick` for fast mode.

GitHub: https://github.com/JustineDaveMagnaye/the-courtroom

Happy to answer questions or take feedback.

Disclosure: I built this plugin. It's free and open source (MIT). No monetization.   Built a "Courtroom" skill — Claude proposes a plan, Codex cross-examines it, they debate, then the verdict gets execute
Showcase
I made a Claude Code plugin that adds structured cross-model deliberation before any code gets written.

The setup:

- Claude = Prosecution (builds the implementation plan)

- Codex CLI = Cross-Examiner (adversarially challenges it)

- You = Judge (approve or reject the final verdict)

7-phase workflow: Claude plans → Codex critiques (logical flaws, edge cases, architecture, security) → Claude rebuts each objection (ACCEPT / REJECT / COMPROMISE) → Codex deliberates as neutral arbiter → verdict presented → you approve → code gets written.

What makes it useful:

- A built-in weak objection catalog auto-filters 27 false-positive patterns (style nitpicks, YAGNI, scope creep, phantom references) so the debate stays focused on real issues

- `--strict` mode for harsher critique, `--dual-plan` where Codex builds its own plan independently before seeing Claude's

- Task-type checklists (bugfix, security, refactor, feature) get injected into the cross-examination so Codex knows what to prioritize

- Auto-discovers relevant skills from both Claude and Codex and embeds them as context

- Session logging with objection acceptance rates so you can see patterns over time

**Why two models?** Claude reviewing its own plan catches fewer issues than having Codex adversarially challenge it. Codex is good at spotting edge cases Claude glosses over. Claude is good at defending decisions that are actually correct. The debate format surfaces disagreements that a single pass misses.

Install:

```

/plugin marketplace add JustineDaveMagnaye/the-courtroom

/plugin install courtroom

```

Then invoke with `/courtroom --task "your task"`. Supports `--rounds N` for multiple debate rounds, `--auto-execute` to skip approval, `--quick` for fast mode.

GitHub: https://github.com/JustineDaveMagnaye/the-courtroom

Happy to answer questions or take feedback.

Disclosure: I built this plugin. It's free and open source (MIT). No monetization.  https://www.reddit.com/r/ClaudeCode/comments/1sdml9e/built_a_courtroom_skill_claude_proposes_a_plan/  


5. I built a "devil's advocate" skill that challenges Claude's output at every step — open source
Resource
https://github.com/notmanas/claude-code-skills

I'm a solo dev building a B2B product with Claude Code. It does 70% of my work at this point. But I kept running into the same problem: Claude is confidently wrong more often than I'm comfortable with.

/devils-advocate: I had a boss who had this way of zooming out and challenging every decision with a scenario I hadn't thought of. It was annoying, but he was usually right to put up that challenge. I built something similar - what I do is I pair it with other skills so any decision Claude or I make, I can use this to challenge me poke holes in my thoughts. This does the same! Check it out here: https://github.com/notmanas/claude-code-skills/tree/main/skills/devils-advocate

/ux-expert: I don't know UX. But I do know it's important for adoption. I asked Claude to review my dashboard for an ERP I'm building, and it didn't give me much.
So I gave it 2,000 lines of actual UX methodology — Gestalt principles, Shneiderman's mantra, cognitive load theory, component library guides.
I needed it to understand the user's psychology. What they want to see first, what would be their "go-to" metric, and what could go in another dedicated page. stuff like that.

Then, I asked it to audit a couple of pages - got some solid advice, and a UI Spec too!
It found 18 issues on first run, 4 critical. Check it out here: https://github.com/notmanas/claude-code-skills/tree/main/skills/ux-expert
Try these out, and please share feedback! :)


Upvote
103

Downvote

25
Go to comments


Share



