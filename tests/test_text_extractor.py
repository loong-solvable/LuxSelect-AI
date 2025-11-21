import pytest
from unittest.mock import MagicMock, patch
from src.core.text_extractor import TextExtractor

@pytest.fixture
def extractor():
    return TextExtractor()

def test_get_selected_text_success(extractor):
    """Test successful text extraction."""
    with patch('pyperclip.paste') as mock_paste, \
         patch('pyperclip.copy') as mock_copy, \
         patch('pyautogui.hotkey') as mock_hotkey, \
         patch('time.sleep') as mock_sleep:
        
        # Setup mocks
        # First paste (backup): "old_content"
        # Second paste (new content): "selected_text"
        mock_paste.side_effect = ["old_content", "selected_text"]
        
        result = extractor.get_selected_text()
        
        assert result == "selected_text"
        
        # Verify interactions
        mock_hotkey.assert_called_once() # Should call ctrl+c
        mock_copy.assert_called_with("old_content") # Should restore

def test_get_selected_text_no_change(extractor):
    """Test when no text is selected (clipboard content doesn't change)."""
    with patch('pyperclip.paste') as mock_paste, \
         patch('pyperclip.copy') as mock_copy, \
         patch('pyautogui.hotkey') as mock_hotkey, \
         patch('time.sleep'):
        
        # Clipboard remains same
        mock_paste.side_effect = ["content", "content"]
        
        result = extractor.get_selected_text()
        
        assert result is None
        # Should still restore (or at least try, though logic says if same, we might skip restore? 
        # The code restores in finally block if old_clipboard exists)
        mock_copy.assert_called_with("content")

def test_get_selected_text_empty(extractor):
    """Test when clipboard becomes empty."""
    with patch('pyperclip.paste') as mock_paste, \
         patch('pyperclip.copy') as mock_copy, \
         patch('pyautogui.hotkey'), \
         patch('time.sleep'):
        
        mock_paste.side_effect = ["old", ""]
        
        result = extractor.get_selected_text()
        
        assert result is None
        mock_copy.assert_called_with("old")

def test_get_selected_text_exception(extractor):
    """Test handling of exceptions during copy."""
    with patch('pyperclip.paste') as mock_paste, \
         patch('pyautogui.hotkey') as mock_hotkey:
        
        mock_paste.return_value = "old"
        mock_hotkey.side_effect = Exception("Hotkey failed")
        
        result = extractor.get_selected_text()
        
        assert result is None

