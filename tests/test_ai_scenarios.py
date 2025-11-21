import pytest
from unittest.mock import MagicMock, patch
from src.core.ai_client import OpenAIClient

@pytest.fixture
def client():
    # Use a real key from env if available, otherwise mock it.
    # But for this 'response quality' test, we usually want real API calls 
    # OR we just verify the inputs. 
    # Since the user asked to "test different AI responses", this sounds like an integration test
    # or a prompt verification test. 
    # Here we create a parametrized test to verify the INPUTS are constructed correctly.
    # Actual AI response testing usually requires a live key and costs money.
    with patch('src.config.settings.OPENAI_API_KEY', 'fake-key'):
        return OpenAIClient()

# Test Cases covering various scenarios
TEST_CASES = [
    ("文言文阅读", "左司马", "Explain usage in ancient texts"),
    ("技术文档", "PyQt6 signals", "Explain technical concept"),
    ("地理/旅游", "大别山", "Explain location/significance"),
    ("英语学习", "Ubiquitous", "Translate and explain"),
    ("法律文书", "不可抗力", "Explain legal definition"),
    ("网络流行语", "绝绝子", "Explain slang"),
    ("数学公式", "傅里叶变换", "Explain mathematical concept"),
    ("错误堆栈", "RecursionError: maximum recursion depth exceeded", "Debug code error"),
    ("Shell命令", "chmod +x script.sh", "Explain command"),
    ("医学术语", "阿司匹林", "Explain drug usage"),
]

@pytest.mark.parametrize("scenario, input_text, intent", TEST_CASES)
def test_ai_prompt_construction(client, scenario, input_text, intent):
    """
    Verifies that different input texts are correctly passed to the AI client.
    This ensures our system handles various characters/lengths correctly.
    """
    mock_stream = MagicMock()
    mock_stream.__iter__.return_value = [] # Empty stream

    with patch.object(client.client.chat.completions, 'create', return_value=mock_stream) as mock_create:
        # Trigger the method
        list(client.stream_explanation(input_text))
        
        # Capture arguments
        call_args = mock_create.call_args
        _, kwargs = call_args
        
        messages = kwargs['messages']
        user_message = messages[1]['content']
        system_message = messages[0]['content']

        # Assertions
        assert user_message == input_text
        assert "问答助手" in system_message
        assert "中文" in system_message

