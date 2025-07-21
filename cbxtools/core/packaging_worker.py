#!/usr/bin/env python3
"""
Unified packaging worker for CBZ creation.
Consolidates packaging logic for different execution contexts.
"""

import queue
import threading
import shutil
from pathlib import Path

from .archive_handler import ArchiveHandler
from .filesystem_utils import FileSystemUtils


class PackagingWorkerBase:
    """Base class for CBZ packaging workers."""
    
    def __init__(self, logger, keep_originals=False):
        self.logger = logger
        self.keep_originals = keep_originals
        self.running = False
    
    def package_single(self, file_output_dir, cbz_output, input_file, zip_compresslevel=9):
        """Package a single directory into CBZ format."""
        try:
            ArchiveHandler.create_cbz(file_output_dir, cbz_output, self.logger, zip_compresslevel)
            _, new_size_bytes = FileSystemUtils.get_file_size_formatted(cbz_output)
            
            if not self.keep_originals:
                shutil.rmtree(file_output_dir)
                self.logger.debug(f"Removed extracted files from {file_output_dir}")
            
            self.logger.info(f"Packaged {input_file.name} successfully")
            return True, new_size_bytes
            
        except Exception as e:
            self.logger.error(f"Error packaging {input_file.name}: {e}")
            return False, 0


class SynchronousPackagingWorker(PackagingWorkerBase):
    """Synchronous packaging worker for single-threaded operations."""
    
    def process(self, file_output_dir, cbz_output, input_file, zip_compresslevel=9):
        """Process packaging synchronously."""
        return self.package_single(file_output_dir, cbz_output, input_file, zip_compresslevel)


class AsynchronousPackagingWorker(PackagingWorkerBase):
    """Asynchronous packaging worker for pipeline operations."""
    
    def __init__(self, logger, keep_originals=False, result_queue=None):
        super().__init__(logger, keep_originals)
        self.packaging_queue = queue.Queue()
        self.result_queue = result_queue
        self.worker_thread = None
    
    def start(self):
        """Start the packaging worker thread."""
        if self.running:
            return
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
    
    def stop(self):
        """Stop the packaging worker thread."""
        if not self.running:
            return
        
        self.packaging_queue.put(None)  # Sentinel
        self.packaging_queue.join()
        self.running = False
        
        if self.worker_thread:
            self.worker_thread.join(timeout=10)
    
    def queue_package(self, file_output_dir, cbz_output, input_file, result_dict, zip_compresslevel=9):
        """Queue a packaging operation."""
        if not self.running:
            self.start()
        
        self.packaging_queue.put((file_output_dir, cbz_output, input_file, result_dict, zip_compresslevel))
    
    def _worker_loop(self):
        """Main worker loop for processing packaging queue."""
        while True:
            item = self.packaging_queue.get()
            if item is None:  # Sentinel
                self.packaging_queue.task_done()
                break
            
            # Handle both old and new queue item formats
            if len(item) >= 5:
                file_output_dir, cbz_output, input_file, result_dict, zip_compresslevel = item
            else:
                file_output_dir, cbz_output, input_file, result_dict = item
                zip_compresslevel = 9  # Default
            
            success, new_size = self.package_single(
                file_output_dir, cbz_output, input_file, zip_compresslevel
            )
            
            result_dict["success"] = success
            result_dict["new_size"] = new_size
            
            # Put result in queue if available (for stats tracking)
            if self.result_queue:
                self.result_queue.put({
                    "file": input_file,
                    "success": success,
                    "new_size": new_size
                })
            
            self.packaging_queue.task_done()


class WatchModePackagingWorker(AsynchronousPackagingWorker):
    """Enhanced packaging worker for watch mode with better result tracking."""
    
    def _worker_loop(self):
        """Enhanced worker loop with better result handling."""
        while True:
            item = self.packaging_queue.get()
            if item is None:  # Sentinel
                self.packaging_queue.task_done()
                break
            
            # Handle both old and new queue item formats
            if len(item) >= 5:
                file_output_dir, cbz_output, input_file, result_dict, zip_compresslevel = item
            else:
                file_output_dir, cbz_output, input_file, result_dict = item
                zip_compresslevel = 9
            
            success, new_size = self.package_single(
                file_output_dir, cbz_output, input_file, zip_compresslevel
            )
            
            result_dict["success"] = success
            result_dict["new_size"] = new_size
            
            # Always put result in queue for watch mode stats tracking
            if self.result_queue:
                self.result_queue.put({
                    "file": input_file,
                    "success": success,
                    "new_size": new_size
                })
            
            self.packaging_queue.task_done()
