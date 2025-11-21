import pytest
from unittest.mock import MagicMock, patch
from src.core.ai_client import OpenAIClient

@pytest.fixture
def client():
    with patch('src.config.settings.OPENAI_API_KEY', 'fake-key'):
        return OpenAIClient()

def test_stream_explanation_success(client):
    """Test successful streaming from OpenAI."""
    mock_stream = MagicMock()
    
    # Mock chunks
    chunk1 = MagicMock()
    chunk1.choices[0].delta.content = "Hello"
    chunk2 = MagicMock()
    chunk2.choices[0].delta.content = " World"
    
    mock_stream.__iter__.return_value = [chunk1, chunk2]
    
    with patch.object(client.client.chat.completions, 'create', return_value=mock_stream):
        generator = client.stream_explanation("test code")
        results = list(generator)
        
        assert results == ["Hello", " World"]

def test_stream_explanation_no_key():
    """Test behavior when API key is missing."""
    with patch('src.config.settings.OPENAI_API_KEY', ''):
        client = OpenAIClient()
        generator = client.stream_explanation("test")
        results = list(generator)
        # Check for error in response (can be Chinese or English)
        assert ("认证失败" in results[0] or "Error" in results[0])

def test_stream_explanation_api_error(client):
    """Test handling of API errors."""
    with patch.object(client.client.chat.completions, 'create', side_effect=Exception("API Down")):
        generator = client.stream_explanation("test")
        results = list(generator)
        # Check for error in response (can be Chinese or English)
        assert ("发生未知错误" in results[0] or "API Down" in results[0])

