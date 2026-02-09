"""
Phase 1.3 集成测试工具
Integration Test Tool for Phase 1.3

测试对话生成功能（千问 API + TTS 播放）
"""
import os
import sys
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import get_config
from src.llm import QwenLLMEngine
from src.tts import PiperTTSEngine
from src.stt import FunASRSTTEngine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Phase13TestSuite:
    """Phase 1.3 集成测试套件"""

    def __init__(self):
        """初始化测试套件"""
        self.config = None
        self.llm_engine = None
        self.tts_engine = None
        self.stt_engine = None

    def load_config(self):
        """加载配置"""
        print("\n" + "="*60)
        print("📋 加载配置文件")
        print("="*60)

        try:
            self.config = get_config()
            self.config.validate()
            print("✅ 配置加载成功")
            return True
        except Exception as e:
            print(f"❌ 配置加载失败: {e}")
            return False

    def test_llm_engine(self):
        """测试 LLM 引擎"""
        print("\n" + "="*60)
        print("🤖 测试 LLM 引擎 (千问 API)")
        print("="*60)

        # 检查 API Key
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            llm_config = self.config.get_section('llm', {})
            api_key = llm_config.get('api_key')

        if not api_key:
            print("❌ 未找到 DASHSCOPE_API_KEY")
            print("   请设置环境变量或在 config.yaml 中配置")
            return False

        try:
            llm_config = self.config.get_section('llm', {})
            self.llm_engine = QwenLLMEngine(
                api_key=api_key,
                model=llm_config.get('model', 'qwen-turbo'),
                temperature=llm_config.get('temperature', 0.7),
                max_tokens=llm_config.get('max_tokens', 1500),
                enable_history=llm_config.get('enable_history', True),
                max_history=llm_config.get('max_history', 10)
            )

            print(f"✅ LLM 引擎初始化成功")
            print(f"   模型: {self.llm_engine.get_model_info()['model']}")
            print(f"   提供商: {self.llm_engine.get_model_info()['provider']}")
            return True

        except Exception as e:
            print(f"❌ LLM 引擎初始化失败: {e}")
            return False

    def test_llm_generate(self):
        """测试 LLM 生成"""
        print("\n" + "="*60)
        print("💬 测试 LLM 对话生成")
        print("="*60)

        if not self.llm_engine:
            print("❌ LLM 引擎未初始化")
            return False

        test_questions = [
            "你好",
            "今天天气怎么样",
            "讲一个简短的笑话"
        ]

        for question in test_questions:
            print(f"\n👤 用户: {question}")
            try:
                result = self.llm_engine.chat(question)
                print(f"🤖 助手: {result['reply']}")
                print(f"   Token: {result['usage'].get('total_tokens', 0)}")
                print(f"   原因: {result['finish_reason']}")
            except Exception as e:
                print(f"❌ 生成失败: {e}")
                return False

        print("\n✅ 对话生成测试通过")
        return True

    def test_llm_conversation_history(self):
        """测试对话历史"""
        print("\n" + "="*60)
        print("📚 测试对话历史")
        print("="*60)

        if not self.llm_engine:
            print("❌ LLM 引擎未初始化")
            return False

        # 重置历史
        self.llm_engine.reset_conversation()

        # 多轮对话
        conversations = [
            "我叫张三",
            "我叫什么名字？",
            "今天天气怎么样？"
        ]

        for msg in conversations:
            print(f"\n👤 用户: {msg}")
            try:
                result = self.llm_engine.chat(msg)
                print(f"🤖 助手: {result['reply']}")
            except Exception as e:
                print(f"❌ 生成失败: {e}")
                return False

        history = self.llm_engine.get_conversation_history()
        print(f"\n📝 对话历史记录: {len(history)} 条消息")

        print("\n✅ 对话历史测试通过")
        return True

    def test_tts_engine(self):
        """测试 TTS 引擎"""
        print("\n" + "="*60)
        print("🔊 测试 TTS 引擎 (Piper)")
        print("="*60)

        try:
            tts_config = self.config.get_section('tts', {})
            audio_config = self.config.get_audio_config()

            self.tts_engine = PiperTTSEngine(
                model_path=tts_config.get('model_path', './models/piper/zh_CN-huayan-medium.onnx'),
                length_scale=tts_config.get('length_scale', 1.0),
                output_device=audio_config.get('output_device', 'plughw:0,0')
            )

            print("✅ TTS 引擎初始化成功")

            # 测试合成
            test_text = "这是一个测试文本。"
            print(f"\n合成测试文本: {test_text}")

            audio = self.tts_engine.synthesize(test_text)
            print(f"✅ 合成成功，音频长度: {len(audio)} 采样点")

            return True

        except Exception as e:
            print(f"❌ TTS 引擎测试失败: {e}")
            return False

    def test_full_pipeline(self):
        """测试完整流程：LLM 生成 + TTS 播放"""
        print("\n" + "="*60)
        print("🔄 测试完整流程 (LLM + TTS)")
        print("="*60)

        if not self.llm_engine or not self.tts_engine:
            print("❌ 引擎未初始化")
            return False

        test_input = "请用一句话介绍一下你自己"
        print(f"\n👤 用户: {test_input}")

        try:
            # LLM 生成
            result = self.llm_engine.chat(test_input)
            reply = result['reply']
            print(f"🤖 助手: {reply}")

            # TTS 合成
            print("\n🔊 合成语音...")
            audio = self.tts_engine.synthesize(reply)
            print(f"✅ 合成成功，音频长度: {len(audio)} 采样点")

            # 播放语音
            print("\n🔊 播放语音...")
            import numpy as np
            import pyaudio

            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.tts_engine.get_sample_rate(),
                output_device=self.tts_engine._output_device_index,
                output=True
            )

            stream.write(audio.tobytes())
            stream.stop_stream()
            stream.close()
            p.terminate()

            print("✅ 播放完成")

        except Exception as e:
            print(f"❌ 流程测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False

        print("\n✅ 完整流程测试通过")
        return True

    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*60)
        print("🧪 Phase 1.3 集成测试")
        print("="*60)
        print("\n测试内容:")
        print("  [1] LLM 引擎测试")
        print("  [2] LLM 对话生成测试")
        print("  [3] 对话历史测试")
        print("  [4] TTS 引擎测试")
        print("  [5] 完整流程测试")
        print("  [a] 运行所有测试")
        print("  [q] 退出")

        choice = input("\n请选择测试项目: ").strip().lower()

        if choice == '1':
            return self.test_llm_engine()
        elif choice == '2':
            if not self.llm_engine:
                if not self.load_config():
                    return False
                if not self.test_llm_engine():
                    return False
            return self.test_llm_generate()
        elif choice == '3':
            if not self.llm_engine:
                if not self.load_config():
                    return False
                if not self.test_llm_engine():
                    return False
            return self.test_llm_conversation_history()
        elif choice == '4':
            if not self.load_config():
                return False
            return self.test_tts_engine()
        elif choice == '5':
            if not self.load_config():
                return False
            if not self.test_llm_engine():
                return False
            if not self.test_tts_engine():
                return False
            return self.test_full_pipeline()
        elif choice == 'a':
            results = []
            if not self.load_config():
                return False
            results.append(self.test_llm_engine())
            results.append(self.test_llm_generate())
            results.append(self.test_llm_conversation_history())
            results.append(self.test_tts_engine())
            results.append(self.test_full_pipeline())

            print("\n" + "="*60)
            print("📊 测试结果汇总")
            print("="*60)
            passed = sum(results)
            total = len(results)
            print(f"通过: {passed}/{total}")
            if passed == total:
                print("✅ 所有测试通过")
                return True
            else:
                print(f"❌ {total - passed} 个测试失败")
                return False
        elif choice == 'q':
            print("退出测试")
            return True
        else:
            print("无效选择")
            return False


def main():
    """主函数"""
    test_suite = Phase13TestSuite()

    try:
        result = test_suite.run_all_tests()
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n测试被中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
