#!/bin/bash
# Cleanup zombie agent processes
# Run this periodically or when you notice high CPU usage

echo "🧹 Cleaning up zombie agent processes..."

# Kill multiprocessing spawn processes (zombie workers)
SPAWN_COUNT=$(ps aux | grep -E "[p]ython.*spawn_main" | grep -v grep | wc -l | tr -d ' ')
if [ "$SPAWN_COUNT" -gt 0 ]; then
    echo "Found $SPAWN_COUNT spawn processes, killing..."
    ps aux | grep -E "[p]ython.*spawn_main" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null
    echo "✅ Killed spawn processes"
else
    echo "✅ No spawn processes found"
fi

# Kill resource tracker processes
TRACKER_COUNT=$(ps aux | grep -E "[p]ython.*resource_tracker" | grep -v grep | wc -l | tr -d ' ')
if [ "$TRACKER_COUNT" -gt 0 ]; then
    echo "Found $TRACKER_COUNT tracker processes, killing..."
    ps aux | grep -E "[p]ython.*resource_tracker" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null
    echo "✅ Killed tracker processes"
else
    echo "✅ No tracker processes found"
fi

# Show summary
echo ""
echo "📊 Summary:"
echo "  Agent processes: $(ps aux | grep -E '[p]ython.*start_agent' | grep -v grep | wc -l | tr -d ' ')"
echo "  Backend processes: $(ps aux | grep -E '[p]ython.*uvicorn' | grep -v grep | wc -l | tr -d ' ')"
echo "  Total Python processes: $(ps aux | grep -E '[p]ython' | grep -v grep | wc -l | tr -d ' ')"

