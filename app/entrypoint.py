
import signal
import sys
import threading
import os

from app.pgbouncer_manager import PgBouncerManager
from app.haproxy_manager import HAProxyManager 

def main():
    driver = os.getenv("DRIVER", "postgres").lower()

    if driver == "postgres":
        manager = PgBouncerManager()
    elif driver == "serverless":
        manager = HAProxyManager()
    else:
        print("Invalid driver - only 'postgres' and 'serverless' drivers are supported.")
        sys.exit(1)

    def handle_signal(signum, frame):
        print(f"Received signal {signum}, shutting down...")
        manager.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    manager.reloader_thread = threading.Thread(target=manager.start_reloader_loop)
    manager.watcher_thread = threading.Thread(target=manager.watch_file_changes, args=("/scripts/.git/HEAD",))

    manager.reloader_thread.start()
    manager.watcher_thread.start()

    manager.reloader_thread.join()

if __name__ == "__main__":
    main()
