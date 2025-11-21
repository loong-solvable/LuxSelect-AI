import math
import time
from typing import Tuple, List, Optional
from pynput import mouse
from PyQt6.QtCore import QObject, pyqtSignal
from utils.logger import setup_logger
from config import settings

logger = setup_logger(__name__)

class EventMonitor(QObject):
    """
    Enhanced mouse event monitor with debouncing and exclusion filtering.
    
    Features:
    - Configurable drag threshold
    - Debouncing to prevent rapid triggers
    - Window title exclusion list
    - Maximum drag distance filtering (to exclude file drags)
    - Detailed logging in debug mode
    """
    
    # Signal emits (x, y) coordinates of the mouse release
    selection_detected = pyqtSignal(int, int)
    # Signal emits (x, y) for any click (used to close overlay)
    click_detected = pyqtSignal(int, int)
    
    def __init__(self):
        super().__init__()
        self.listener: Optional[mouse.Listener] = None
        self.start_pos: Tuple[int, int] = (0, 0)
        self.is_dragging: bool = False
        
        # Configuration from settings
        self.threshold: int = settings.DRAG_THRESHOLD
        self.debounce_interval: float = settings.DEBOUNCE_INTERVAL
        self.max_drag_distance: int = 1000  # Maximum pixels (to filter file drags)
        
        # Debouncing state
        self.last_trigger_time: float = 0.0
        
        # Exclusion list (window titles to ignore)
        self.excluded_windows: List[str] = settings.get_excluded_windows_list()
        if not self.excluded_windows:
            # Default exclusions
            self.excluded_windows = [
                'Password', 'KeePass', 'LastPass', '1Password',  # Password managers
                'GameBar', 'Steam', 'Battle.net', 'Epic Games',  # Gaming
                'League of Legends', 'Dota', 'Counter-Strike',   # Specific games
            ]
        
        logger.info(f"Event Monitor configured: threshold={self.threshold}px, "
                   f"debounce={self.debounce_interval}s, "
                   f"excluded_windows={len(self.excluded_windows)}")
        
    def start(self):
        """Starts the global mouse listener."""
        logger.info("🖱️ Starting Event Monitor...")
        try:
            self.listener = mouse.Listener(on_click=self._on_click)
            self.listener.start()
            logger.info("✅ Event Monitor started successfully")
        except Exception as e:
            logger.error(f"❌ Failed to start Event Monitor: {e}", exc_info=True)
            raise
        
    def stop(self):
        """Stops the global mouse listener."""
        if self.listener:
            logger.info("🛑 Stopping Event Monitor...")
            try:
                self.listener.stop()
                self.listener = None
                logger.info("✅ Event Monitor stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping Event Monitor: {e}")

    def _is_excluded_window(self) -> bool:
        """
        Check if the current active window should be excluded from monitoring.
        
        Returns:
            True if the window should be excluded, False otherwise
        """
        try:
            import pygetwindow as gw
            active_window = gw.getActiveWindow()
            
            if active_window and active_window.title:
                window_title = active_window.title
                
                # Check if any excluded keyword is in the window title
                for excluded in self.excluded_windows:
                    if excluded.lower() in window_title.lower():
                        logger.debug(f"🚫 Excluded window detected: {window_title}")
                        return True
            
        except Exception as e:
            # If we can't determine the window, don't exclude
            logger.debug(f"Failed to get active window: {e}")
        
        return False
    
    def _should_trigger(self, distance: float) -> bool:
        """
        Check if a drag event should trigger selection detection.
        
        Args:
            distance: The drag distance in pixels
            
        Returns:
            True if should trigger, False otherwise
        """
        current_time = time.time()
        
        # 1. Check debounce interval
        if current_time - self.last_trigger_time < self.debounce_interval:
            logger.debug(f"⏱️ Debounced: last trigger was {current_time - self.last_trigger_time:.2f}s ago")
            return False
        
        # 2. Check minimum threshold
        if distance < self.threshold:
            logger.debug(f"📏 Distance too small: {distance:.1f}px < {self.threshold}px")
            return False
        
        # 3. Check maximum distance (to filter file drags)
        if distance > self.max_drag_distance:
            logger.debug(f"📏 Distance too large: {distance:.1f}px > {self.max_drag_distance}px (likely file drag)")
            return False
        
        # 4. Check excluded windows
        if self._is_excluded_window():
            return False
        
        return True

    def _on_click(self, x: int, y: int, button: mouse.Button, pressed: bool):
        """
        Callback for mouse click events.
        
        Args:
            x: Mouse X coordinate
            y: Mouse Y coordinate
            button: Mouse button
            pressed: True if button was pressed, False if released
        """
        # We only care about the left button
        if button != mouse.Button.left:
            return

        try:
            if pressed:
                # Mouse button pressed - start tracking
                self.start_pos = (x, y)
                self.is_dragging = True
                
                # Emit click signal on press (to close overlay immediately)
                self.click_detected.emit(int(x), int(y))
                
                if settings.DEBUG:
                    logger.debug(f"🖱️ Mouse down at ({x}, {y})")
            
            else:
                # Mouse button released
                if self.is_dragging:
                    end_pos = (x, y)
                    distance = math.hypot(
                        end_pos[0] - self.start_pos[0], 
                        end_pos[1] - self.start_pos[1]
                    )
                    
                    if settings.DEBUG:
                        logger.debug(f"🖱️ Mouse up at ({x}, {y}), drag distance: {distance:.2f}px")
                    
                    # Check if should trigger
                    if self._should_trigger(distance):
                        logger.info(f"✅ Selection detected: distance={distance:.1f}px at ({x}, {y})")
                        # Emit signal to main thread
                        self.selection_detected.emit(int(x), int(y))
                        # Update last trigger time
                        self.last_trigger_time = time.time()
                    
                    self.is_dragging = False
                    
        except Exception as e:
            logger.error(f"❌ Error in mouse event handler: {e}", exc_info=True)


