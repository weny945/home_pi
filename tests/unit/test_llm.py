"""
LLM 模块单元测试
Unit Tests for LLM Module

Phase 1.3: 对话生成模块测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.llm import QwenLLMEngine, LLMEngine


class TestLLMEngine:
    """LLM 抽象接口测试"""

    def test_llm_engine_is_abstract(self):
        """测试 LLMEngine 是抽象类，不能直接实例化"""
        with pytest.raises(TypeError):
            LLMEngine()


class TestQwenLLMEngine:
    """千问 LLM 引擎测试"""

    @pytest.fixture
    def mock_dashscope(self):
        """Mock dashscope 模块"""
        with patch('src.llm.qwen_engine.dashscope') as mock:
            mock.Generation.call.return_value = Mock(
                status_code=200,
                output=Mock(
                    choices=[
                        Mock(
                            message=Mock(content="这是测试回复"),
                            finish_reason="stop"
                        )
                    ]
                ),
                usage=Mock(
                    input_tokens=10,
                    output_tokens=20
                )
            )
            mock.api_key = None
            yield mock

    def test_init_without_api_key(self):
        """测试没有 API Key 时初始化失败"""
        with patch.dict('os.environ', {}, clear=False):
            # 移除环境变量
            import os
            old_key = os.environ.pop('DASHSCOPE_API_KEY', None)

            with pytest.raises(ValueError, match="DashScope API Key 未提供"):
                QwenLLMEngine()

            # 恢复环境变量
            if old_key:
                os.environ['DASHSCOPE_API_KEY'] = old_key

    def test_init_with_api_key(self, mock_dashscope):
        """测试使用 API Key 初始化"""
        engine = QwenLLMEngine(api_key="test_key")
        assert engine.is_ready()
        assert engine._api_key == "test_key"

    def test_init_with_env_variable(self, mock_dashscope):
        """测试使用环境变量初始化"""
        import os
        os.environ['DASHSCOPE_API_KEY'] = 'env_key'

        engine = QwenLLMEngine()
        assert engine.is_ready()
        assert engine._api_key == "env_key"

        # 清理
        del os.environ['DASHSCOPE_API_KEY']

    def test_generate(self, mock_dashscope):
        """测试生成回复"""
        engine = QwenLLMEngine(api_key="test_key")
        reply = engine.generate("你好")

        assert reply == "这是测试回复"
        mock_dashscope.Generation.call.assert_called_once()

    def test_chat(self, mock_dashscope):
        """测试对话接口"""
        engine = QwenLLMEngine(api_key="test_key")
        result = engine.chat("你好")

        assert result["reply"] == "这是测试回复"
        assert result["usage"]["input_tokens"] == 10
        assert result["usage"]["output_tokens"] == 20
        assert result["model"] == "qwen-turbo"

    def test_conversation_history(self, mock_dashscope):
        """测试对话历史功能"""
        engine = QwenLLMEngine(
            api_key="test_key",
            enable_history=True,
            max_history=5
        )

        # 第一次对话
        engine.chat("你好")

        # 第二次对话
        engine.chat("今天天气怎么样")

        history = engine.get_conversation_history()
        assert len(history) == 4  # 2 轮对话，每轮 2 条消息

    def test_reset_conversation(self, mock_dashscope):
        """测试重置对话"""
        engine = QwenLLMEngine(api_key="test_key", enable_history=True)
        engine.chat("你好")

        engine.reset_conversation()
        history = engine.get_conversation_history()
        assert len(history) == 0

    def test_max_history_limit(self, mock_dashscope):
        """测试历史记录限制"""
        engine = QwenLLMEngine(
            api_key="test_key",
            enable_history=True,
            max_history=2
        )

        # 进行 3 轮对话
        for i in range(3):
            engine.chat(f"消息 {i}")

        history = engine.get_conversation_history()
        # max_history=2，最多保存 2 轮对话（4 条消息）
        assert len(history) <= 4

    def test_get_model_info(self, mock_dashscope):
        """测试获取模型信息"""
        engine = QwenLLMEngine(api_key="test_key")
        info = engine.get_model_info()

        assert info["name"] == "qwen-turbo"
        assert info["provider"] == "阿里云 DashScope"
        assert info["temperature"] == 0.7
        assert info["max_tokens"] == 1500

    def test_different_models(self, mock_dashscope):
        """测试不同模型选择"""
        for model in ["qwen-turbo", "qwen-plus", "qwen-max"]:
            engine = QwenLLMEngine(api_key="test_key", model=model)
            assert engine._model_name == model

    def test_invalid_model_fallback(self, mock_dashscope):
        """测试无效模型回退到默认"""
        with pytest.mock.patch('src.llm.qwen_engine.logger') as mock_logger:
            engine = QwenLLMEngine(api_key="test_key", model="invalid_model")
            assert engine._model_name == "qwen-turbo"
            mock_logger.warning.assert_called()

    def test_api_error_handling(self, mock_dashscope):
        """测试 API 错误处理"""
        # 模拟 API 错误
        mock_dashscope.Generation.call.return_value = Mock(
            status_code=400,
            code="InvalidParameter",
            message="参数错误"
        )

        engine = QwenLLMEngine(api_key="test_key")
        result = engine.chat("测试")

        assert "API 调用失败" in result["reply"]
        assert result["finish_reason"] == "api_error"

    def test_empty_input(self, mock_dashscope):
        """测试空输入处理"""
        engine = QwenLLMEngine(api_key="test_key")
        result = engine.chat("")

        assert result["reply"] == ""
        assert result["finish_reason"] == "empty_input"

    def test_temperature_bounds(self, mock_dashscope):
        """测试温度参数边界"""
        # 温度超出范围应被限制在 0-1 之间
        engine1 = QwenLLMEngine(api_key="test_key", temperature=-0.5)
        assert engine1._temperature == 0.0

        engine2 = QwenLLMEngine(api_key="test_key", temperature=1.5)
        assert engine2._temperature == 1.0

    def test_max_tokens_positive(self, mock_dashscope):
        """测试 max_tokens 必须为正数"""
        engine = QwenLLMEngine(api_key="test_key", max_tokens=0)
        assert engine._max_tokens == 1  # 最小值为 1
