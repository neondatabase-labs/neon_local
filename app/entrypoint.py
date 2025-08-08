
import signal
import sys
import threading
import os

from app.unified_manager import UnifiedManager

def main():
    # Use unified manager that runs both HAProxy and PgBouncer
    manager = UnifiedManager()

    def handle_signal(signum, frame):
        print(f"Received signal {signum}, shutting down...")
        manager.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    manager.reloader_thread = threading.Thread(target=manager.start_reloader_loop)
    manager.watcher_thread = threading.Thread(target=manager.watch_file_changes, args=("/tmp/.git/HEAD",))

    manager.reloader_thread.start()
    manager.watcher_thread.start()

    manager.reloader_thread.join()

if __name__ == "__main__":
    main()
