"""
千问 API LLM 引擎
Qwen API LLM Engine Implementation

Phase 1.3: 使用阿里云千问 API 实现对话生成
"""
import logging
import os
from typing import List, Dict, Any, Optional

try:
    import dashscope
    from dashscope import Generation
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False

from .engine import LLMEngine

logger = logging.getLogger(__name__)


class QwenLLMEngine(LLMEngine):
    """
    千问 API LLM 引擎

    使用阿里云 DashScope API 调用千问大模型
    """

    # 支持的模型列表
    MODELS = {
        "qwen-turbo": "qwen-turbo",          # 快速响应，适合实时对话
        "qwen-plus": "qwen-plus",            # 平衡性能和速度
        "qwen-max": "qwen-max",              # 最强性能
        "qwen-turbo-latest": "qwen-turbo-latest",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "qwen-turbo",
        temperature: float = 0.7,
        max_tokens: int = 3000,
        max_tokens_long: int = 8000,
        enable_history: bool = True,
        max_history: int = 10,
        system_prompt: Optional[str] = None,
        system_prompt_long: Optional[str] = None,
        long_text_keywords: Optional[list] = None
    ):
        """
        初始化千问 LLM 引擎

        Args:
            api_key: DashScope API Key，如果不提供则从环境变量读取
            model: 模型名称 (qwen-turbo/qwen-plus/qwen-max)
            temperature: 温度参数 (0.0-1.0)，越高越随机
            max_tokens: 最大生成 token 数（默认模式）
            max_tokens_long: 长文本模式最大 token 数（用于讲故事等）
            enable_history: 是否启用对话历史
            max_history: 最大对话历史轮数
            system_prompt: 系统提示词（简洁模式），用于设定助手角色和风格
            system_prompt_long: 系统提示词（长文本模式），用于详细回答
            long_text_keywords: 长文本检测关键词列表
        """
        if not DASHSCOPE_AVAILABLE:
            raise ImportError(
                "dashscope 库未安装，请运行: pip install dashscope"
            )

        # API Key
        self._api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self._api_key or self._api_key == "sk-your-api-key-here":
            raise ValueError(
                "DashScope API Key 未配置，请在 config.yaml 中设置 llm.api_key "
                "或设置 DASHSCOPE_API_KEY 环境变量"
            )

        # 设置 API Key
        dashscope.api_key = self._api_key

        # 模型配置（支持任意模型名称）
        self._model = model
        self._model_name = model

        # 如果是已知的千问模型，记录提示信息
        if model in self.MODELS:
            logger.info(f"使用千问模型: {model}")
        else:
            logger.info(f"使用自定义模型: {model}")

        # 生成参数
        self._temperature = max(0.0, min(1.0, temperature))
        self._max_tokens = max(1, max_tokens)
        self._max_tokens_long = max(1, max_tokens_long)
        self._long_text_keywords = long_text_keywords or [
            "讲个故事", "讲故事", "详细说说", "展开讲讲",
            "多说一点", "完整介绍", "详细描述"
        ]

        # 对话历史
        self._enable_history = enable_history
        self._max_history = max(1, max_history)
        self._conversation_history: List[Dict[str, str]] = []

        # 系统提示词
        self._system_prompt = system_prompt
        self._system_prompt_long = system_prompt_long
        if system_prompt:
            logger.info(f"已设置系统提示词，角色: {system_prompt.split('。')[0] if '。' in system_prompt else system_prompt[:50]}...")
        if system_prompt_long:
            logger.info(f"已设置长文本系统提示词")

        logger.info(f"千问 LLM 引擎初始化完成: {self._model}")

    def _detect_long_text_mode(self, message: str) -> bool:
        """
        检测用户消息是否需要长文本回复

        Args:
            message: 用户消息

        Returns:
            bool: 是否需要长文本模式
        """
        if not message:
            return False

        message_lower = message.lower()
        for keyword in self._long_text_keywords:
            if keyword.lower() in message_lower:
                logger.info(f"检测到长文本需求关键词: '{keyword}'")
                return True
        return False

    def generate(
        self,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> str:
        """
        生成回复

        Args:
            prompt: 用户输入的提示词
            conversation_history: 对话历史
            **kwargs: 其他参数

        Returns:
            str: 生成的回复文本
        """
        result = self.chat(prompt, conversation_history, **kwargs)
        return result["reply"]

    def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        对话接口（带完整返回信息）

        Args:
            message: 用户消息
            conversation_history: 对话历史
            **kwargs: 其他参数（temperature, max_tokens 等）

        Returns:
            dict: 包含回复和其他信息的字典
        """
        if not message:
            return {
                "reply": "",
                "usage": {},
                "model": self._model_name,
                "finish_reason": "empty_input",
            }

        # 构建消息列表
        messages = []

        # 检测是否需要长文本模式
        use_long_text_mode = self._detect_long_text_mode(message)
        max_tokens = self._max_tokens_long if use_long_text_mode else self._max_tokens

        # 添加系统提示词（根据模式动态选择）
        system_prompt = kwargs.get("system_prompt", self._system_prompt)
        if use_long_text_mode and self._system_prompt_long:
            # 长文本模式：使用长文本系统提示词
            system_prompt = kwargs.get("system_prompt_long", self._system_prompt_long)
            logger.info("📖 使用长文本系统提示词")
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # 添加对话历史
        history = conversation_history or self._conversation_history
        if history:
            # 限制历史长度
            if len(history) > self._max_history:
                history = history[-self._max_history:]
            messages.extend(history)

        # 添加当前消息
        messages.append({"role": "user", "content": message})

        if use_long_text_mode:
            logger.info(f"📖 长文本模式 (max_tokens={max_tokens})")
        else:
            logger.debug(f"标准模式 (max_tokens={max_tokens})")

        # 调用 API
        try:
            response = Generation.call(
                model=self._model,
                messages=messages,
                temperature=kwargs.get("temperature", self._temperature),
                max_tokens=kwargs.get("max_tokens", max_tokens),  # 使用动态计算的max_tokens
                result_format="message",
            )

            # 检查响应状态
            if response.status_code != 200:
                logger.error(f"API 调用失败: {response.code} - {response.message}")
                return {
                    "reply": f"抱歉，API 调用失败（{response.code}）",
                    "usage": {},
                    "model": self._model_name,
                    "finish_reason": "api_error",
                }

            # 提取回复
            reply = response.output.choices[0].message.content

            # 更新对话历史
            if self._enable_history:
                self._conversation_history.append({"role": "user", "content": message})
                self._conversation_history.append({"role": "assistant", "content": reply})

                # 限制历史长度
                if len(self._conversation_history) > self._max_history * 2:
                    self._conversation_history = self._conversation_history[-self._max_history * 2:]

            return {
                "reply": reply,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                },
                "model": self._model_name,
                "finish_reason": response.output.choices[0].finish_reason,
            }

        except Exception as e:
            logger.error(f"生成回复失败: {e}", exc_info=True)
            return {
                "reply": f"抱歉，生成回复时出错：{str(e)}",
                "usage": {},
                "model": self._model_name,
                "finish_reason": "error",
            }

    def is_ready(self) -> bool:
        """
        检查引擎是否就绪

        Returns:
            bool: 是否就绪
        """
        return DASHSCOPE_AVAILABLE and bool(self._api_key)

    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息

        Returns:
            dict: 模型信息
        """
        info = {
            "name": self._model_name,
            "provider": "阿里云 DashScope",
            "model": self._model,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "enable_history": self._enable_history,
            "max_history": self._max_history,
        }
        if self._system_prompt:
            # 只返回系统提示词的前100个字符
            info["system_prompt"] = self._system_prompt[:100] + "..." if len(self._system_prompt) > 100 else self._system_prompt
        return info

    def reset_conversation(self) -> None:
        """
        重置对话上下文

        清空对话历史，开始新的对话
        """
        self._conversation_history = []
        logger.info("对话历史已重置")

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """
        获取当前对话历史

        Returns:
            list: 对话历史
        """
        return self._conversation_history.copy()
