"""
简单的 LLM 测试脚本
Simple LLM Test Script
"""
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import get_config
from src.llm import QwenLLMEngine


def test_llm():
    """测试 LLM 引擎"""
    print("="*60)
    print("🤖 LLM 引擎测试")
    print("="*60)

    # 1. 加载配置
    print("\n📋 加载配置...")
    config = get_config()
    llm_config = config.get_section('llm') or {}

    api_key = llm_config.get('api_key')
    if not api_key or api_key == "sk-your-api-key-here":
        print("❌ API Key 未配置")
        return False

    print(f"✅ 配置加载成功")
    print(f"   模型: {llm_config.get('model', 'qwen-turbo')}")
    print(f"   API Key: {api_key[:10]}...")
    print(f"   温度: {llm_config.get('temperature', 0.7)}")

    # 2. 初始化引擎
    print("\n🔧 初始化 LLM 引擎...")
    try:
        llm = QwenLLMEngine(
            api_key=api_key,
            model=llm_config.get('model', 'qwen-turbo'),
            temperature=llm_config.get('temperature', 0.7),
            max_tokens=llm_config.get('max_tokens', 1500),
            enable_history=llm_config.get('enable_history', True),
            max_history=llm_config.get('max_history', 10),
            system_prompt=llm_config.get('system_prompt')
        )
        print("✅ 引擎初始化成功")
        model_info = llm.get_model_info()
        print(f"   模型: {model_info['name']}")
        print(f"   提供商: {model_info['provider']}")
        if 'system_prompt' in model_info:
            print(f"   角色设定: {model_info['system_prompt']}")
    except Exception as e:
        print(f"❌ 引擎初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 3. 测试对话
    print("\n💬 测试对话生成...")
    test_questions = [
        "你好",
        "今天天气怎么样"
    ]

    for i, question in enumerate(test_questions, 1):
        print(f"\n--- 测试 {i} ---")
        print(f"👤 用户: {question}")
        try:
            result = llm.chat(question)
            print(f"🤖 派蒙: {result['reply']}")
            print(f"   Token: {result['usage'].get('total_tokens', 0)}")
            print(f"   原因: {result['finish_reason']}")
        except Exception as e:
            print(f"❌ 生成失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    # 4. 测试对话历史
    print("\n📚 测试对话历史...")
    print("👤 用户: 你知道我是谁吗？")
    try:
        result = llm.chat("你知道我是谁吗？")
        print(f"🤖 派蒙: {result['reply']}")
        history = llm.get_conversation_history()
        print(f"   对话历史: {len(history)} 条消息")
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False

    print("\n" + "="*60)
    print("✅ 所有测试通过")
    print("="*60)
    return True


if __name__ == '__main__':
    try:
        success = test_llm()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试被中断")
        sys.exit(1)
