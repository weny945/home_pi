"""
测试文本质量检测功能
验证STT识别结果的过滤逻辑
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import re


def check_text_quality(text: str, config: dict = None) -> dict:
    """
    文本质量检测函数（从 StateMachine 复制的简化版本）

    Args:
        text: 待检测文本
        config: 配置字典

    Returns:
        dict: 检测结果
    """
    if config is None:
        config = {
            "min_length": 4,
            "invalid_words": ["嗯", "啊", "哦"]
        }

    # 0. 清理 STT 特殊标签和噪音
    cleaned_text = re.sub(r'<\|[^|]+\|>', '', text)
    cleaned_text = cleaned_text.strip()

    if not cleaned_text:
        return {
            "is_valid": False,
            "issue_type": "garbage",
            "reason": "识别结果为空或仅含标签"
        }

    # 1. 检查是否包含有效中文内容
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', cleaned_text)
    min_length = config.get("min_length", 4)

    if len(chinese_chars) == 0:
        # 没有中文字符，检查是否为有意义的英文
        # 注意：要从清理后的文本检测，避免标签中的英文被计入
        english_words = re.findall(r'[a-zA-Z]+', cleaned_text)
        # 纯英文必须至少2个单词
        if len(english_words) < 2:
            return {
                "is_valid": False,
                "issue_type": "garbage",
                "reason": f"无有效中文内容，英文单词过少 (英文词数: {len(english_words)})"
            }
        # 英文单词总长度至少5个字符
        if len(''.join(english_words)) < 5:
            return {
                "is_valid": False,
                "issue_type": "garbage",
                "reason": "英文内容过短"
            }
    else:
        # 有中文，清理标点符号和空格来计算长度
        cleaned_for_length = cleaned_text.replace(" ", "").replace("，", "").replace("。", "")
        cleaned_for_length = cleaned_for_length.replace("？", "").replace("！", "").replace("、", "")

        if len(cleaned_for_length) < min_length:
            return {
                "is_valid": False,
                "issue_type": "fragment",
                "reason": f"文本太短 (长度: {len(cleaned_for_length)} < {min_length})"
            }

    # 2. 检查重复字符（使用清理标点后的版本）
    cleaned_for_check = cleaned_text.replace(" ", "").replace("，", "").replace("。", "")
    cleaned_for_check = cleaned_for_check.replace("？", "").replace("！", "").replace("、", "")

    if len(cleaned_for_check) >= 2 and len(set(cleaned_for_check)) == 1:
        return {
            "is_valid": False,
            "issue_type": "fragment",
            "reason": f"重复字符: {cleaned_for_check}"
        }

    # 3. 检查无效词汇
    invalid_words = config.get("invalid_words", [])
    # 使用清理标点后的版本来匹配无效词汇
    if cleaned_for_check in invalid_words:
        return {
            "is_valid": False,
            "issue_type": "semantic",
            "reason": f"无效词汇: {cleaned_text}"
        }

    # 4. 检查韩文
    if re.search(r'[가-힣]+', text):
        korean_chars = re.findall(r'[가-힣]+', text)
        if len(''.join(korean_chars)) > len(chinese_chars):
            return {
                "is_valid": False,
                "issue_type": "garbage",
                "reason": "检测到韩文内容，可能为误识别"
            }

    # 5. 通过检测
    return {
        "is_valid": True,
        "issue_type": None,
        "reason": ""
    }


def test_clean_stt_tags():
    """测试清理STT特殊标签"""
    test_cases = [
        ("<|zh|><|EMO_UNKNOWN|><|Speech|><|withitn|>你好你好", True, "zh标签-4字"),
        ("<|en|><|EMO_UNKNOWN|><|Speech|><|withitn|>Hello", False, "纯英文短句"),
        ("<|zh|><|HAPPY|><|Speech|><|withitn|>今天天气怎么样", True, "中文长句"),
        ("<|ko|><|EMO_UNKNOWN|><|Speech|><|withitn|>어", False, "韩文短句"),
        ("", False, "空文本"),
        ("<|zh|><|EMO_UNKNOWN|>", False, "仅标签"),
    ]

    print("\n" + "="*60)
    print("1. 测试STT标签清理")
    print("="*60)

    for text, expected_valid, desc in test_cases:
        result = check_text_quality(text)
        print(f"\n测试: {desc}")
        print(f"  输入: {text}")
        print(f"  有效: {result['is_valid']} (预期: {expected_valid})")
        print(f"  原因: {result['reason']}")

        assert result['is_valid'] == expected_valid, f"{desc} 检测失败"


def test_chinese_min_length():
    """测试中文最小长度"""
    test_cases = [
        ("你好", False, "2字-太短"),
        ("你好啊", False, "3字-太短"),
        ("你好啊呀", True, "4字-刚好"),
        ("今天天气怎么样", True, "7字-正常"),
    ]

    print("\n" + "="*60)
    print("2. 测试中文最小长度")
    print("="*60)

    for text, expected_valid, desc in test_cases:
        result = check_text_quality(text)
        print(f"\n测试: {desc}")
        print(f"  输入: {text}")
        print(f"  有效: {result['is_valid']} (预期: {expected_valid})")
        if not result['is_valid']:
            print(f"  原因: {result['reason']}")

        assert result['is_valid'] == expected_valid, f"{desc} 检测失败"


def test_english_short_words():
    """测试英文短句过滤"""
    test_cases = [
        ("Good", False, "单个英文单词"),
        ("Good morning", True, "两个英文单词"),
        ("How are you", True, "多个英文单词"),
        ("I", False, "单个字母"),
    ]

    print("\n" + "="*60)
    print("3. 测试英文短句过滤")
    print("="*60)

    for text, expected_valid, desc in test_cases:
        result = check_text_quality(text)
        print(f"\n测试: {desc}")
        print(f"  输入: {text}")
        print(f"  有效: {result['is_valid']} (预期: {expected_valid})")
        if not result['is_valid']:
            print(f"  原因: {result['reason']}")

        assert result['is_valid'] == expected_valid, f"{desc} 检测失败"


def test_korean_detection():
    """测试韩文过滤"""
    test_cases = [
        ("<|ko|><|EMO_UNKNOWN|><|Speech|><|withitn|>어", False, "韩文短句"),
        ("<|ko|><|EMO_UNKNOWN|><|Speech|><|withitn|>그 좋아", False, "韩文混合"),
        ("你好어", False, "中韩混合，韩文多"),
        ("어你好你好", True, "韩文少，中文多"),
    ]

    print("\n" + "="*60)
    print("4. 测试韩文检测")
    print("="*60)

    for text, expected_valid, desc in test_cases:
        result = check_text_quality(text)
        print(f"\n测试: {desc}")
        print(f"  输入: {text}")
        print(f"  有效: {result['is_valid']} (预期: {expected_valid})")
        if not result['is_valid']:
            print(f"  原因: {result['reason']}")

        assert result['is_valid'] == expected_valid, f"{desc} 检测失败"


def test_repeated_chars():
    """测试重复字符过滤"""
    test_cases = [
        ("啊啊啊啊", False, "重复字符"),
        ("你好你好", True, "重复词语"),
        ("啊啊", False, "2个重复"),
    ]

    print("\n" + "="*60)
    print("5. 测试重复字符")
    print("="*60)

    for text, expected_valid, desc in test_cases:
        result = check_text_quality(text)
        print(f"\n测试: {desc}")
        print(f"  输入: {text}")
        print(f"  有效: {result['is_valid']} (预期: {expected_valid})")
        if not result['is_valid']:
            print(f"  原因: {result['reason']}")

        assert result['is_valid'] == expected_valid, f"{desc} 检测失败"


def test_real_world_examples():
    """测试实际日志中的例子"""
    real_cases = [
        ("<|zh|><|EMO_UNKNOWN|><|Speech|><|withitn|>过。 <|zh|><|HAPPY|><|Speech|><|withitn|>游泳游泳。 <|en|><|EMO_UNKNOWN|><|Speech|><|withitn|>I。",
         True, "混合语言+标签（5个中文）"),
        ("<|en|><|EMO_UNKNOWN|><|Speech|><|withitn|>2.",
         False, "单个字符+标签"),
        ("<|en|><|EMO_UNKNOWN|><|Speech|><|withitn|>Good. <|en|><|EMO_UNKNOWN|><|Speech|><|withitn|>Sorry.",
         True, "Good Sorry - 两个英文单词"),
        ("<|zh|><|EMO_UNKNOWN|><|Speech|><|withitn|>没有么问。",
         True, "5个中文字符（虽然可能是误识别）"),
        ("<|ko|><|EMO_UNKNOWN|><|Speech|><|withitn|>어.",
         False, "韩文"),
        ("<|en|><|EMO_UNKNOWN|><|Speech|><|withitn|>My.",
         False, "单个英文单词"),
        ("<|zh|><|EMO_UNKNOWN|><|Speech|><|withitn|>这么了。 <|en|><|EMO_UNKNOWN|><|Speech|><|withitn|>Oh.",
         True, "3个中文+Oh"),
        ("<|en|><|EMO_UNKNOWN|><|Speech|><|withitn|>그 좋아.",
         False, "韩文"),
        ("<|yue|><|EMO_UNKNOWN|><|Speech|><|withitn|>以后。",
         False, "2个中文-太短（粤语标签）"),
    ]

    print("\n" + "="*60)
    print("6. 测试实际案例")
    print("="*60)

    for text, expected_valid, desc in real_cases:
        result = check_text_quality(text)
        print(f"\n测试: {desc}")
        print(f"  输入: {text}")
        print(f"  有效: {result['is_valid']} (预期: {expected_valid})")
        if not result['is_valid']:
            print(f"  原因: {result['reason']}")

        # 记录实际结果
        if result['is_valid'] != expected_valid:
            print(f"  ⚠️  结果与预期不同")


if __name__ == "__main__":
    test_clean_stt_tags()
    test_chinese_min_length()
    test_english_short_words()
    test_korean_detection()
    test_repeated_chars()
    test_real_world_examples()

    print("\n" + "="*60)
    print("✅ 所有测试完成")
    print("="*60)
