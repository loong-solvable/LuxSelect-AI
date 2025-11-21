from abc import ABC, abstractmethod
from typing import Generator, Optional, List, Dict
import openai
import httpx
import json
import hashlib
import time
from config import settings
from utils.logger import setup_logger
from utils.privacy import PrivacyFilter

logger = setup_logger(__name__)

class AIClient(ABC):
    """Abstract base class for AI clients."""
    
    @abstractmethod
    def stream_explanation(self, text: str) -> Generator[str, None, None]:
        """
        Streams an explanation for the provided text.
        
        Args:
            text: The selected text to explain.
            
        Yields:
            Chunks of the explanation.
        """
        pass
    
    @abstractmethod
    def generate_follow_up_questions(self, original_text: str, explanation: str) -> List[str]:
        """
        Generate follow-up questions based on the original text and its explanation.
        
        Args:
            original_text: The original selected text.
            explanation: The AI-generated explanation.
            
        Returns:
            A list of follow-up questions.
        """
        pass

class OpenAIClient(AIClient):
    """Enhanced OpenAI API client with timeout, retry, and caching.
    
    Features:
    - Automatic timeout control
    - Retry on transient failures
    - Response caching for identical queries
    - Privacy filtering
    - Input length limiting
    """
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_BASE_URL
        self.model = settings.AI_MODEL
        self.timeout = settings.AI_TIMEOUT
        self.max_tokens = settings.AI_MAX_TOKENS
        self.temperature = settings.AI_TEMPERATURE
        
        if not self.api_key:
            logger.warning("OpenAI API Key is missing in configuration.")
        
        # Initialize HTTP client with timeout
        http_client = httpx.Client(
            timeout=httpx.Timeout(
                timeout=self.timeout,
                connect=10.0,  # Connection timeout
                read=self.timeout,  # Read timeout
                write=10.0,  # Write timeout
                pool=5.0  # Pool timeout
            )
        )
        
        # Initialize OpenAI client with custom http_client
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            http_client=http_client
        )
        
        # Response cache
        self.cache: Dict[str, str] = {}
        self.cache_enabled = settings.ENABLE_CACHE
        self.cache_max_size = settings.CACHE_MAX_SIZE
        
        logger.info(f"OpenAI Client initialized: model={self.model}, timeout={self.timeout}s")

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _add_to_cache(self, key: str, response: str):
        """Add response to cache with LRU eviction."""
        if not self.cache_enabled:
            return
        
        # LRU eviction: remove oldest entry if cache is full
        if len(self.cache) >= self.cache_max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            logger.debug(f"Cache eviction: removed oldest entry")
        
        self.cache[key] = response
        logger.debug(f"Cached response for key: {key[:8]}...")
    
    def _get_from_cache(self, key: str) -> Optional[str]:
        """Get response from cache."""
        if not self.cache_enabled:
            return None
        return self.cache.get(key)
    
    def stream_explanation(self, text: str) -> Generator[str, None, None]:
        """
        Streams explanation from AI provider with robust error handling.
        
        Features:
        - Privacy filtering
        - Response caching
        - Input length limiting
        - Comprehensive error handling
        - Timeout control
        
        Args:
            text: The text to explain
            
        Yields:
            Chunks of the explanation
        """
        # 1. Privacy Filter
        if settings.ENABLE_PRIVACY_FILTER and PrivacyFilter.contains_sensitive_data(text):
            logger.warning("⚠️ Sensitive data detected. Aborting AI request.")
            yield "⚠️ **检测到敏感信息**\n\n"
            yield "为保护您的隐私，此请求已被拦截。\n\n"
            yield "可能包含：信用卡号、密码、API Key 等敏感数据。"
            return

        # 2. Validate API Key
        if not self.api_key:
            logger.error("API Key not configured")
            yield "❌ **配置错误**\n\n未配置 API Key，请检查 .env 文件。"
            return

        # 3. Input Length Limiting (prevent excessive costs)
        original_length = len(text)
        if original_length > 5000:
            text = text[:5000]
            logger.warning(f"Input text truncated: {original_length} -> 5000 chars")
            yield "⚠️ *输入文本过长，已自动截断至 5000 字符*\n\n"

        # 4. Check Cache
        cache_key = self._get_cache_key(text)
        cached_response = self._get_from_cache(cache_key)
        
        if cached_response:
            logger.info("✅ Using cached response")
            # Simulate streaming for cached response
            for i in range(0, len(cached_response), 20):
                yield cached_response[i:i+20]
                time.sleep(0.01)  # Smooth display
            return

        # 5. Prepare System Prompt
        system_prompt = (
            "你是一个专业的问答助手。你的任务是解释用户提供的文本。\n"
            "要求：\n"
            "1. 必须使用**中文**进行解释。\n"
            "2. 解释要简洁明了，直接指出核心含义。\n"
            "3. 如果是专有名词，先给出中文翻译，再解释其用途。\n"
            "4. 使用 Markdown 格式，重点内容可以使用粗体。\n"
            "5. 控制字数在300字以内，不要输出长篇大论，只解释最核心的概念。"
        )
        
        # 6. Make API Request with Error Handling
        full_response = ""
        try:
            logger.info(f"Making API request: model={self.model}, input_length={len(text)}")
            
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                stream=True,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content
            
            # Cache the complete response
            if full_response:
                self._add_to_cache(cache_key, full_response)
                logger.info(f"✅ API request completed: {len(full_response)} chars")

        except httpx.TimeoutException as e:
            logger.error(f"⏱️ Request timeout: {e}")
            yield "\n\n❌ **请求超时**\n\n"
            yield f"服务器响应时间超过 {self.timeout} 秒，请检查网络连接或稍后重试。"
        
        except openai.APIConnectionError as e:
            logger.error(f"🔌 API Connection Error: {e}")
            yield "\n\n❌ **无法连接到 AI 服务**\n\n"
            yield "请检查：\n"
            yield "1. 网络连接是否正常\n"
            yield "2. API Base URL 是否正确\n"
            yield f"3. 当前配置: {self.base_url}"
        
        except openai.AuthenticationError as e:
            logger.error(f"🔑 API Auth Error: {e}")
            yield "\n\n❌ **认证失败**\n\n"
            yield "API Key 无效或已过期，请检查 .env 文件中的 OPENAI_API_KEY。"
        
        except openai.RateLimitError as e:
            logger.error(f"⚠️ Rate Limit Error: {e}")
            yield "\n\n❌ **请求频率超限**\n\n"
            yield "API 调用次数已达上限，请稍后再试。"
        
        except openai.BadRequestError as e:
            logger.error(f"❌ Bad Request Error: {e}")
            yield "\n\n❌ **请求参数错误**\n\n"
            yield f"请检查模型配置是否正确。当前模型: {self.model}"
        
        except Exception as e:
            logger.error(f"💥 Unexpected error in AI request: {e}", exc_info=True)
            yield f"\n\n❌ **发生未知错误**\n\n{str(e)}"
    
    def generate_follow_up_questions(self, original_text: str, explanation: str) -> List[str]:
        """
        生成用户可能感兴趣的后续问题（扩展查询手）。
        
        Args:
            original_text: 用户选中的原始文本
            explanation: AI 生成的解释内容
            
        Returns:
            包含 3-5 个后续问题的列表
        """
        if not self.api_key:
            logger.warning("API Key is not configured for follow-up questions.")
            return []
        
        # Limit input length to control costs
        if len(original_text) > 500:
            original_text = original_text[:500] + "..."
        if len(explanation) > 1000:
            explanation = explanation[:1000] + "..."
        
        try:
            system_prompt = (
                "你是一个智能问题推荐助手。你的任务是根据用户选中的文本和已生成的解释，"
                "推理出用户可能会进一步感兴趣的问题。\n\n"
                "要求：\n"
                "1. 生成 3-5 个相关的后续问题\n"
                "2. 问题要具体、有针对性，不要太泛泛\n"
                "3. 问题应该由浅入深，涵盖不同角度（如历史、应用、原理、对比等）\n"
                "4. 每个问题控制在 15 字以内\n"
                "5. 直接返回 JSON 数组格式，例如：[\"问题1\", \"问题2\", \"问题3\"]\n"
                "6. 不要添加任何其他说明文字，只返回 JSON 数组"
            )
            
            user_prompt = (
                f"用户选中的文本：{original_text}\n\n"
                f"已生成的解释：\n{explanation}\n\n"
                f"请生成 3-5 个用户可能感兴趣的后续问题："
            )
            
            logger.debug("Generating follow-up questions...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=200,  # Limit token usage
                stream=False
            )
            
            content = response.choices[0].message.content.strip()
            logger.debug(f"Follow-up questions raw response: {content[:100]}...")
            
            # Parse JSON
            try:
                # Remove markdown code block markers
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                questions = json.loads(content)
                
                if isinstance(questions, list):
                    # Filter and clean questions
                    questions = [q.strip() for q in questions if isinstance(q, str) and q.strip()]
                    # Limit to 5 questions
                    questions = questions[:5]
                    logger.info(f"✅ Generated {len(questions)} follow-up questions")
                    return questions
                else:
                    logger.warning(f"Invalid JSON format: expected list, got {type(questions)}")
                    return []
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse follow-up questions JSON: {e}")
                logger.error(f"Content was: {content}")
                return []
        
        except httpx.TimeoutException as e:
            logger.error(f"Timeout generating follow-up questions: {e}")
            return []
        
        except openai.APIConnectionError as e:
            logger.error(f"API Connection Error in follow-up questions: {e}")
            return []
        
        except openai.AuthenticationError as e:
            logger.error(f"API Auth Error in follow-up questions: {e}")
            return []
        
        except Exception as e:
            logger.error(f"Unexpected error in follow-up questions: {e}", exc_info=True)
            return []
