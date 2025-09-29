import logging
import threading
from prometheus_client import Counter, Gauge, Histogram, start_http_server
from typing import Optional

logger = logging.getLogger(__name__)

# Prometheus metrics for cleaner service
sessions_cleaned_total = Counter(
    'cleaner_sessions_cleaned_total',
    'Total number of sessions cleaned up'
)

documents_cleaned_total = Counter(
    'cleaner_documents_cleaned_total', 
    'Total number of documents cleaned up'
)

files_deleted_total = Counter(
    'cleaner_files_deleted_total',
    'Total number of files deleted from storage'
)

chromadb_collections_cleaned_total = Counter(
    'cleaner_chromadb_collections_cleaned_total',
    'Total number of ChromaDB collection cleanups',
    ['collection_name']
)

redis_events_processed_total = Counter(
    'cleaner_redis_events_processed_total',
    'Total number of Redis keyspace events processed',
    ['event_type']
)

redis_watcher_active = Gauge(
    'cleaner_redis_watcher_active',
    'Whether the Redis watcher thread is active (1=active, 0=inactive)'
)

cleanup_duration_seconds = Histogram(
    'cleaner_cleanup_duration_seconds',
    'Time spent cleaning up resources',
    ['cleanup_type']
)

cleanup_errors_total = Counter(
    'cleaner_cleanup_errors_total',
    'Total number of cleanup errors',
    ['error_type']
)

# Set Redis watcher as active when service starts
redis_watcher_active.set(1)

class MetricsServer:
    """HTTP server for Prometheus metrics"""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.server_thread: Optional[threading.Thread] = None
        
    def start(self):
        """Start the metrics HTTP server in a separate thread"""
        def run_server():
            try:
                logger.info(f"Starting Prometheus metrics server on port {self.port}")
                start_http_server(self.port)
                logger.info(f"Prometheus metrics server started on port {self.port}")
            except Exception as e:
                logger.error(f"Failed to start metrics server: {e}")
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
    def stop(self):
        """Mark the Redis watcher as inactive"""
        redis_watcher_active.set(0)
        logger.info("Metrics server marked as stopped")