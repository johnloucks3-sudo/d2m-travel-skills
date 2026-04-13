#!/bin/bash
task_id="$1"
task_prompt="$2"
nohup env -u ANTHROPIC_API_KEY -u ANTHROPIC_BASE_URL claude -p "$task_prompt" --dangerously-skip-permissions > "/home/john/Thunderbird/logs/agent_${task_id}.log" 2>&1 &
echo $! > "/home/john/Thunderbird/logs/agent_${task_id}.pid"
echo "Spawned Agent ${task_id} PID: $!"
