"""
Metrics JSON Writer

Handles writing query execution metrics to JSON file.
"""

import json
import logging
import queue
import threading
import time
from typing import Optional

from metrics import QueryExecutionMetrics

logger = logging.getLogger(__name__)


class MetricsJSONWriter:
    """Writes query execution metrics to JSON file"""
    
    def __init__(self, output_file: str):
        self.output_file = output_file
        self.queue = queue.Queue()
        self.writer_thread: Optional[threading.Thread] = None
        self.running = False
        self.written_count = 0
        self.count_lock = threading.Lock()
    
    def start(self) -> None:
        """Start the writer thread"""
        if self.running:
            return
        
        self.running = True
        self.writer_thread = threading.Thread(target=self._writer_loop)
        self.writer_thread.start()
        logger.info(f"📊 Metrics writer started, output file: {self.output_file}")
    
    def stop(self) -> None:
        """Stop the writer thread"""
        if not self.running:
            return
        
        self.running = False
        # Add sentinel to queue to wake up writer
        self.queue.put(None)
    
    def wait(self) -> None:
        """Wait for writer thread to finish"""
        if self.writer_thread:
            self.writer_thread.join()
            logger.info("✅ Metrics writer stopped")
    
    def write_result(self, result: QueryExecutionMetrics) -> None:
        """Write a query result to the output file"""
        if self.running:
            self.queue.put(result)
    
    def get_written_count(self) -> int:
        """Get the number of results written"""
        with self.count_lock:
            return self.written_count
    
    def _writer_loop(self) -> None:
        """Main writer loop running in separate thread"""
        try:
            with open(self.output_file, 'w') as f:
                while self.running:
                    try:
                        # Use timeout to periodically check if we should stop
                        result = self.queue.get(timeout=0.1)
                        
                        if result is None:  # Sentinel value to stop
                            break
                        
                        # Write JSON line
                        json_line = json.dumps(result.to_dict(), separators=(',', ':'))
                        f.write(json_line + '\n')
                        f.flush()
                        
                        with self.count_lock:
                            self.written_count += 1
                        
                        self.queue.task_done()
                        
                    except queue.Empty:
                        continue
                
                # Process any remaining items in queue
                while not self.queue.empty():
                    try:
                        result = self.queue.get_nowait()
                        if result is not None:
                            json_line = json.dumps(result.to_dict(), separators=(',', ':'))
                            f.write(json_line + '\n')
                            
                            with self.count_lock:
                                self.written_count += 1
                        
                        self.queue.task_done()
                    except queue.Empty:
                        break
                
                f.flush()
        
        except Exception as e:
            logger.error(f"Error in metrics writer: {e}")
        
        logger.info(f"Metrics writer finished. Total results written: {self.get_written_count()}") 