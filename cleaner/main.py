import logging
import signal

from utils.cleaner import setup_redis_watcher_thread

# Set up logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    # load the redis watcher
    watcher_thread = setup_redis_watcher_thread()
    logger.info(f"{watcher_thread}")

    # Setup Graceful shutdown
    def exit_gracefully(signum, frame):
        watcher_thread.stop()
    signal.signal(signal.SIGINT, exit_gracefully)
    signal.signal(signal.SIGTERM, exit_gracefully)

    # Wait till the thread is no longer running
    watcher_thread.join()
    logger.info("Cleaner stopped gracefully")


if __name__ == "__main__":
    main()