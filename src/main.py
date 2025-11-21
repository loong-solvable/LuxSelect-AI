import sys
import os
import signal
import platform
import tempfile
from pathlib import Path
from typing import Optional
from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import QApplication, QMessageBox
from core.event_monitor import EventMonitor
from core.text_extractor import TextExtractor
from ui.overlay_window import OverlayWindow
from utils.logger import setup_logger

logger = setup_logger(__name__)


class SingletonGuard:
    """
    Cross-platform singleton guard using file locking.
    
    Ensures only one instance of the application runs at a time.
    More robust than socket-based approach as it handles crashes better.
    """
    
    def __init__(self, app_name: str):
        self.app_name = app_name
        
        # Use temp directory for lock file
        lock_dir = Path(tempfile.gettempdir())
        self.lock_file_path = lock_dir / f"{app_name}.lock"
        self.lock_file: Optional[object] = None
        self._locked = False
        
        logger.debug(f"Lock file path: {self.lock_file_path}")
    
    def acquire(self) -> bool:
        """
        Try to acquire the singleton lock.
        
        Returns:
            True if lock acquired successfully, False if another instance is running
        """
        try:
            # Open lock file
            self.lock_file = open(self.lock_file_path, 'w')
            
            # Platform-specific locking
            if platform.system() == 'Windows':
                # Windows: use msvcrt
                import msvcrt
                try:
                    msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                    self._locked = True
                except IOError:
                    logger.warning("Lock file is already locked (another instance running)")
                    return False
            else:
                # Unix/Linux/macOS: use fcntl
                import fcntl
                try:
                    fcntl.lockf(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self._locked = True
                except IOError:
                    logger.warning("Lock file is already locked (another instance running)")
                    return False
            
            # Write PID to lock file for debugging
            self.lock_file.write(str(os.getpid()))
            self.lock_file.flush()
            
            logger.info(f"✅ Singleton lock acquired (PID: {os.getpid()})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to acquire singleton lock: {e}")
            return False
    
    def release(self):
        """Release the singleton lock and clean up."""
        if self._locked and self.lock_file:
            try:
                # Close file (automatically releases lock)
                self.lock_file.close()
                
                # Remove lock file
                self.lock_file_path.unlink(missing_ok=True)
                
                self._locked = False
                logger.info("✅ Singleton lock released")
            except Exception as e:
                logger.error(f"Error releasing singleton lock: {e}")


class LuxSelectApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)  # Keep running even if window is hidden
        
        # Singleton check using file lock
        self.singleton_guard = SingletonGuard("LuxSelect")
        if not self.singleton_guard.acquire():
            logger.warning("⚠️ Another instance of LuxSelect is already running")
            QMessageBox.warning(
                None, 
                "LuxSelect", 
                "LuxSelect is already running!\n\n"
                "Please check your system tray or task manager."
            )
            sys.exit(0)
        
        logger.info(f"🚀 LuxSelect starting... (PID: {os.getpid()})")
        
        # Initialize components
        self.monitor = EventMonitor()
        self.extractor = TextExtractor()
        self.overlay = OverlayWindow()
        
        # Connect signals
        self.monitor.selection_detected.connect(self.handle_selection)
        self.monitor.click_detected.connect(self.handle_click)
        
        # Handle Ctrl+C gracefully
        signal.signal(signal.SIGINT, self.quit)
        
        logger.info("✅ LuxSelect initialized successfully")

    def start(self):
        """Starts the application."""
        logger.info("LuxSelect is starting...")
        self.monitor.start()
        sys.exit(self.app.exec())

    def quit(self, signum=None, frame=None):
        """
        Gracefully shutdown the application.
        
        Args:
            signum: Signal number (for signal handler)
            frame: Current stack frame (for signal handler)
        """
        logger.info("🛑 Shutting down LuxSelect...")
        
        try:
            # Stop event monitor
            if self.monitor:
                self.monitor.stop()
            
            # Hide overlay and stop workers
            if self.overlay:
                self.overlay.hide()
                if self.overlay.worker:
                    self.overlay.worker.stop()
                    self.overlay.worker.wait(1000)
                if self.overlay.followup_worker:
                    self.overlay.followup_worker.stop()
                    self.overlay.followup_worker.wait(1000)
            
            # Release singleton lock
            self.singleton_guard.release()
            
            # Quit application
            self.app.quit()
            
            logger.info("✅ LuxSelect shutdown complete")
        
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)

    def handle_selection(self, x: int, y: int):
        """
        Orchestrates the flow:
        1. Triggered by mouse drag release.
        2. Extracts text.
        3. Shows overlay if text is valid.
        """
        logger.debug(f"Selection detected at {x}, {y}")
        
        # Extract text
        text = self.extractor.get_selected_text()
        
        if text:
            logger.info(f"Showing overlay for text: {text[:30]}...")
            self.overlay.show_at(x, y, text)
        else:
            logger.debug("No valid text extracted.")

    def handle_click(self, x: int, y: int):
        """
        Handles global clicks to close the overlay if clicked outside.
        """
        if self.overlay.isVisible():
            # Get overlay geometry
            # Note: geometry() might not include window frame, but ours is frameless.
            # We need screen coordinates.
            geo = self.overlay.geometry()
            rect = QRect(geo.x(), geo.y(), geo.width(), geo.height())
            
            # Check if click is inside
            if not rect.contains(x, y):
                logger.debug(f"Click outside overlay at {x}, {y}. Closing.")
                self.overlay.hide()
                # Stop AI processing if running
                if self.overlay.worker:
                    self.overlay.worker.stop()

def main():
    try:
        app = LuxSelectApp()
        app.start()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
