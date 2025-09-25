#!/bin/bash
# Neon Local Sync Commands
# Convenient wrapper for syncing data between local and remote databases

set -e

CONTAINER_NAME="neon_local_2-neon_local-1"

# Check if container is running
if ! docker compose ps --services --filter "status=running" | grep -q neon_local; then
    echo "❌ Error: Neon Local container is not running"
    echo "   Start it with: OFFLINE_MODE=true docker compose up -d"
    exit 1
fi

# Check if offline mode is enabled
if ! docker compose exec neon_local env | grep -q "OFFLINE_MODE=true"; then
    echo "❌ Error: Offline mode is not enabled"
    echo "   Restart with: OFFLINE_MODE=true docker compose up -d"
    exit 1
fi

case "${1:-help}" in
    "pull")
        echo "🔄 Pulling data from remote Neon database to local..."
        docker compose exec neon_local python3 /scripts/app/sync_cli.py pull
        ;;
    "push")
        echo "❌ Push operations are not supported"
        docker compose exec neon_local python3 /scripts/app/sync_cli.py push
        ;;
    "status")
        echo "📊 Sync status:"
        docker compose exec neon_local python3 /scripts/app/sync_cli.py status
        ;;
    "pause")
        echo "⏸️  Pausing continuous sync to allow remote database auto-suspend..."
        docker compose exec neon_local python3 /scripts/app/sync_cli.py pause
        ;;
    "resume")
        echo "▶️  Resuming continuous sync..."
        docker compose exec neon_local python3 /scripts/app/sync_cli.py resume
        ;;
    "help"|*)
        echo "Neon Local Sync Commands"
        echo ""
        echo "Usage: ./sync.sh <command>"
        echo ""
        echo "Commands:"
        echo "  pull    - Pull data from remote Neon database to local"
        echo "  push    - ❌ NOT SUPPORTED (Neon permission limitations)"
        echo "  status  - Show current sync status and continuous sync state"
        echo "  pause   - Pause continuous sync to allow remote database auto-suspend"
        echo "  resume  - Resume continuous sync (prevents remote auto-suspend)"
        echo "  help    - Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./sync.sh pull     # Sync remote changes to local"
        echo "  ./sync.sh push     # Shows why push is not supported"
        echo "  ./sync.sh status   # Check sync status"
        echo "  ./sync.sh pause    # Allow remote database to auto-suspend"
        echo "  ./sync.sh resume   # Resume continuous sync monitoring"
        echo ""
        echo "💡 Auto-suspend Management:"
        echo "   By default, continuous sync prevents remote database auto-suspend."
        echo "   Use 'pause' to allow auto-suspend and save costs when not actively developing."
        echo "   Use 'resume' to restart continuous sync for real-time changes."
        echo ""
        echo "Note: Requires OFFLINE_MODE=true and container to be running"
        ;;
esac
