# OPENCODE PROGRESS TIMER PATTERN
This pattern provides clear, visual progress indication for headless processes.

## Pattern
```bash
# Define visual progress bar
function progress_bar() {
    local duration=$1
    local steps=20
    echo -n "["
    for i in $(seq 1 $steps); do
        sleep $(echo "$duration / $steps" | bc -l)
        echo -n "█"
    done
    echo "]"
}

# Example Usage in spawning script
echo -n "EXECUTION STARTING: "
progress_bar 5 &
PID=$!
# ... perform task ...
wait $PID
echo " COMPLETE."
```
