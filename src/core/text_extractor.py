import time
import sys
import platform
import pyperclip
import pyautogui
from typing import Optional
from utils.logger import setup_logger
from config import settings

logger = setup_logger(__name__)

class TextExtractor:
    """
    Service to extract selected text from any application using the 'Clipboard Hack'.
    
    Mechanism:
    1. Backup current clipboard.
    2. Simulate Copy shortcut.
    3. Read new clipboard.
    4. Restore original clipboard.
    """
    
    def __init__(self):
        self.is_mac = platform.system() == 'Darwin'
        self.copy_hotkey = ['command', 'c'] if self.is_mac else ['ctrl', 'c']
        # Increase safety delay for slower systems
        self.safety_delay = settings.SELECTION_DELAY

    def get_selected_text(self) -> Optional[str]:
        """
        Attempts to copy and retrieve the currently selected text.
        
        This method uses the "clipboard hack" technique:
        1. Backs up the current clipboard content
        2. Simulates Ctrl+C (or Cmd+C on macOS) to copy selected text
        3. Reads the new clipboard content
        4. ALWAYS restores the original clipboard (critical for user experience)
        
        Returns:
            Optional[str]: The selected text if successful, None otherwise.
        """
        old_clipboard = None
        new_clipboard = None
        
        try:
            # 1. Backup Clipboard - ALWAYS backup, even if empty
            try:
                old_clipboard = pyperclip.paste()
                logger.debug(f"Clipboard backed up: {len(old_clipboard) if old_clipboard else 0} chars")
            except Exception as e:
                logger.warning(f"Failed to backup clipboard: {e}")
                old_clipboard = ""  # Use empty string as fallback
            
            # 2. Simulate Copy (platform-aware)
            try:
                if self.is_mac:
                    pyautogui.hotkey('command', 'c')
                else:
                    pyautogui.hotkey('ctrl', 'c')
                logger.debug("Copy hotkey simulated")
            except Exception as e:
                logger.error(f"Failed to simulate hotkey: {e}")
                return None

            # 3. Wait for OS to process clipboard
            # Use configurable delay to support slower systems (VMs, Remote Desktop)
            time.sleep(self.safety_delay)

            # 4. Read New Clipboard
            try:
                new_clipboard = pyperclip.paste()
                logger.debug(f"New clipboard content: {len(new_clipboard) if new_clipboard else 0} chars")
            except Exception as e:
                logger.error(f"Failed to read new clipboard content: {e}")
                return None

            # 5. Validation
            if new_clipboard == old_clipboard:
                # No text selected, or copy failed, or same text selected twice
                logger.debug("Clipboard unchanged, no new selection detected")
                return None
            
            if not new_clipboard or not new_clipboard.strip():
                logger.debug("New clipboard is empty or whitespace only")
                return None
            
            # 6. Length sanity check (prevent accidental large clipboard operations)
            if len(new_clipboard) > 10000:
                logger.warning(f"Selected text is very large ({len(new_clipboard)} chars), truncating to 10000")
                new_clipboard = new_clipboard[:10000] + "\n...(truncated)"

            logger.info(f"✅ Text extracted successfully: {len(new_clipboard)} chars")
            return new_clipboard

        except Exception as e:
            logger.error(f"Unexpected error in text extraction: {e}", exc_info=True)
            return None
            
        finally:
            # 7. CRITICAL: ALWAYS Restore Clipboard
            # This is the most important step for user experience
            # We must restore even if old_clipboard is empty string
            try:
                # Restore original clipboard content
                if old_clipboard is not None:
                    pyperclip.copy(old_clipboard)
                    logger.debug("✅ Clipboard restored successfully")
                else:
                    # If we couldn't backup, try to restore empty
                    pyperclip.copy("")
                    logger.warning("Clipboard restored to empty (backup failed)")
            except Exception as e:
                logger.error(f"❌ CRITICAL: Failed to restore clipboard: {e}")
                # This is a critical error as it affects user experience
                # But we can't do much more than log it


