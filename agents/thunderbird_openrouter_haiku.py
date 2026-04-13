#!/usr/bin/env python3
"""
Thunderbird OpenRouter Haiku Agent
Processes tasks using Claude Haiku via OpenRouter API
"""

import os
import sys
import json
import re
from openai import OpenAI
from datetime import datetime

# Configuration
OPENROUTER_API_KEY = os.environ.get(
    "OPENROUTER_API_KEY",
    "***REMOVED-SECRET***",
)
CLAUDE_INBOX = "/home/john/Thunderbird/claude_inbox.md"
OPENCODE_INBOX = "/home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md"
CLAUDE_OUTBOX = "/home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md"

# Model selection: cheapest to most capable
MODELS = {
    "cheapest": "anthropic/claude-3-haiku",  # $0.25/$1.25 per 1M tokens
    "balcost": "anthropic/claude-3.5-haiku",  # $0.8/$4 per 1M tokens
    "latest": "anthropic/claude-haiku-4.5",  # $1/$5 per 1M tokens
}


class OpenRouterHaikuAgent:
    def __init__(self, model="cheapest"):
        self.client = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )
        self.model = MODELS.get(model, MODELS["cheapest"])

    def parse_task_from_inbox(self, task_content):
        """Parse task content from claude_inbox.md format"""
        task_match = re.search(
            r"task:\s*\|\s*\n(.*?)(?=\n\S+\s*:|$)", task_content, re.DOTALL
        )
        if task_match:
            return task_match.group(1).strip()
        return task_content

    def process_task(self, task_content):
        """Process a single task using OpenRouter Haiku"""
        task = self.parse_task_from_inbox(task_content)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are Claude Haiku, a helpful AI assistant processing tasks for Dreams2Memories Travel.",
                    },
                    {"role": "user", "content": task},
                ],
                max_tokens=4000,
            )

            result = response.choices[0].message.content
            usage = response.usage

            return {
                "success": True,
                "result": result,
                "model": self.model,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                    "cost": getattr(usage, "cost", 0.0),
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e), "model": self.model}

    def mark_task_complete(self, task_id, result, inbox_file=CLAUDE_INBOX):
        """Mark a task as complete in the inbox file"""
        if not os.path.exists(inbox_file):
            return False

        with open(inbox_file, "r") as f:
            content = f.read()

        # Find the task block and update status
        pattern = rf"## TASK:\s*{re.escape(task_id)}.*?(?=## TASK:|$)"
        match = re.search(pattern, content, re.DOTALL)

        if match:
            task_block = match.group(0)

            # Update status and add result
            if "status: UNREAD" in task_block:
                updated_block = task_block.replace("status: UNREAD", "status: COMPLETE")

                # Add result if not already present
                if "result:" not in updated_block:
                    result_section = f"\nresult: |\n  {result.replace(chr(10), '\n  ')}"
                    # Insert before the closing --- if exists, or at end
                    if "---" in updated_block:
                        updated_block = updated_block.replace(
                            "---", f"{result_section}\n---"
                        )
                    else:
                        updated_block = f"{updated_block}\n{result_section}"

                # Update the content
                updated_content = content.replace(task_block, updated_block)

                with open(inbox_file, "w") as f:
                    f.write(updated_content)
                return True

        return False


def process_queued_tasks():
    """Process all UNREAD tasks in claude_inbox.md"""
    agent = OpenRouterHaikuAgent(model="cheapest")

    if not os.path.exists(CLAUDE_INBOX):
        print(f"Error: {CLAUDE_INBOX} not found")
        return False

    with open(CLAUDE_INBOX, "r") as f:
        content = f.read()

    # Find all UNREAD tasks
    task_pattern = r"## TASK:\s*(.+?)\n(.*?)(?=## TASK:|$)"
    tasks = re.findall(task_pattern, content, re.DOTALL)

    processed = 0
    for task_id, task_content in tasks:
        if "status: UNREAD" in task_content:
            print(f"Processing task: {task_id}")
            print(f"Using model: {agent.model}")

            result = agent.process_task(task_content)

            if result["success"]:
                print(f"✓ Task completed successfully")
                print(f"  Tokens: {result['usage']['total_tokens']}")
                print(f"  Cost: ${result['usage'].get('cost', 0.0):.6f}")

                # Write result to outbox
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                outbox_entry = f"""
## RESULT: {task_id}
timestamp: {timestamp}
model: {result["model"]}
tokens: {result["usage"]["total_tokens"]}
cost: ${result["usage"].get("cost", 0.0):.6f}
result: |
  {result["result"]}

---
"""

                with open(CLAUDE_OUTBOX, "a") as f:
                    f.write(outbox_entry)

                # Mark task as complete
                agent.mark_task_complete(task_id, result["result"])
                processed += 1
            else:
                print(f"✗ Task failed: {result['error']}")

    print(f"\nProcessed {processed} tasks")
    return processed > 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Test the agent
        agent = OpenRouterHaikuAgent()
        test_result = agent.process_task("Test task: What's 2+2?")
        print(json.dumps(test_result, indent=2))
    else:
        # Process queued tasks
        success = process_queued_tasks()
        sys.exit(0 if success else 1)
