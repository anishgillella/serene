#!/bin/bash
# Kill all zombie LiveKit agent processes

echo "🔍 Searching for zombie agent processes..."

# Count processes before killing
AGENT_COUNT=$(pgrep -f "start_agent.py" 2>/dev/null | wc -l | tr -d ' ')
SPAWN_COUNT=$(pgrep -f "multiprocessing.spawn" 2>/dev/null | wc -l | tr -d ' ')
TRACKER_COUNT=$(pgrep -f "multiprocessing.resource_tracker" 2>/dev/null | wc -l | tr -d ' ')

TOTAL=$((AGENT_COUNT + SPAWN_COUNT + TRACKER_COUNT))

if [ "$TOTAL" -eq "0" ]; then
    echo "✨ No zombie processes found - all clean!"
    exit 0
fi

echo "  📊 Found: $AGENT_COUNT agent(s) + $SPAWN_COUNT worker(s) + $TRACKER_COUNT tracker(s) = $TOTAL total"

# Kill main agent processes
if [ "$AGENT_COUNT" -gt "0" ]; then
    echo "  → Killing $AGENT_COUNT start_agent.py process(es)..."
    pkill -9 -f "start_agent.py" 2>/dev/null
fi

# Kill multiprocessing spawn workers (LiveKit agent workers)
if [ "$SPAWN_COUNT" -gt "0" ]; then
    echo "  → Killing $SPAWN_COUNT multiprocessing.spawn worker(s)..."
    pkill -9 -f "multiprocessing.spawn" 2>/dev/null
fi

# Kill resource trackers
if [ "$TRACKER_COUNT" -gt "0" ]; then
    echo "  → Killing $TRACKER_COUNT resource_tracker process(es)..."
    pkill -9 -f "multiprocessing.resource_tracker" 2>/dev/null
fi

# Wait a moment for processes to die
sleep 1

# Check what's left
REMAINING=$(ps aux | grep -E "(start_agent|multiprocessing)" | grep -v grep | grep -v kill_zombies | wc -l | tr -d ' ')

if [ "$REMAINING" -eq "0" ]; then
    echo "✅ Successfully killed all $TOTAL zombie process(es)!"
else
    echo "⚠️  Warning: $REMAINING process(es) may still be running (tried to kill $TOTAL)"
    echo "Run 'ps aux | grep -E \"(start_agent|multiprocessing)\" | grep -v grep' to check"
fi
