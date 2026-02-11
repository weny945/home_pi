"""
豆包 TTS 发音人诊断工具
用于测试哪些发音人可用
"""
import os
import sys
import json
import requests

# 可能的发音人 ID
TEST_VOICES = [
    # 模型 1.0 发音人
    "zh_female_shuangkuaisisi_moon_bigtts",
    "zh_female_qingxinmeili",
    "zh_female_wenrou",
    "zh_female_tianmei",
    "zh_male_qingchen",
    "zh_male_chunhou",
    "zh_male_wenhe",
]

def test_with_resource_id(resource_id, desc):
    """测试指定 Resource ID 下的发音人"""

    access_key = os.getenv("DOUBAO_ACCESS_KEY")
    app_id = os.getenv("DOUBAO_APP_ID")

    if not access_key or not app_id:
        print("❌ 请先设置环境变量: DOUBAO_ACCESS_KEY, DOUBAO_APP_ID")
        return False, []

    print(f"\n{'=' * 60}")
    print(f"测试 Resource ID: {resource_id} ({desc})")
    print(f"{'=' * 60}")

    api_url = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"

    working_voices = []

    for voice in TEST_VOICES:
        print(f"\n测试发音人: {voice}...")

        headers = {
            "X-Api-App-Id": app_id,
            "X-Api-Access-Key": access_key,
            "X-Api-Resource-Id": resource_id,
            "X-Api-Request-Id": f"test-voice-{voice}",
            "Content-Type": "application/json",
        }

        payload = {
            "user": {"uid": "diagnostic_test"},
            "req_params": {
                "text": "测试",
                "speaker": voice,
                "audio_params": {
                    "format": "mp3",
                    "sample_rate": 24000,
                },
            },
        }

        try:
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=10
            )

            if response.status_code == 200:
                # 读取响应
                for line in response.iter_lines():
                    if line:
                        try:
                            result = json.loads(line)
                            code = result.get("code")

                            if code == 0:
                                print(f"  ✅ 可用！收到音频数据")
                                working_voices.append(voice)
                                break
                            elif code == 20000000:
                                print(f"  ✅ 可用！合成完成")
                                working_voices.append(voice)
                                break
                            elif code == 55000000:
                                print(f"  ❌ 不兼容此发音人")
                                break
                            else:
                                msg = result.get("header", {}).get("message", "未知错误")
                                print(f"  ❌ 错误 (code={code}): {msg}")
                                break
                        except json.JSONDecodeError:
                            pass

            elif response.status_code == 403:
                print(f"  ❌ 认证失败")

            else:
                print(f"  ❌ HTTP {response.status_code}")

        except Exception as e:
            print(f"  ❌ 错误: {e}")

    return len(working_voices) > 0, working_voices


def main():
    """主函数"""

    print("豆包 TTS 发音人诊断工具")

    # 测试不同的 Resource ID
    resource_ids = [
        ("seed-tts-1.0", "豆包语音合成模型 1.0"),
        ("seed-tts-2.0", "豆包语音合成模型 2.0"),
    ]

    final_result = {}
    for resource_id, desc in resource_ids:
        success, voices = test_with_resource_id(resource_id, desc)
        final_result[resource_id] = (success, voices)

    # 输出总结
    print(f"\n{'=' * 60}")
    print("总结")
    print(f"{'=' * 60}")

    for resource_id, desc in resource_ids:
        success, voices = final_result[resource_id]
        if success:
            print(f"\n✅ {resource_id} ({desc}):")
            for v in voices:
                print(f"   - {v}")
        else:
            print(f"\n❌ {resource_id} ({desc}): 无可用发音人")

    print(f"\n{'=' * 60}")

    # 推荐配置
    for resource_id, desc in resource_ids:
        success, voices = final_result[resource_id]
        if success:
            print(f"\n推荐配置 ({desc}):")
            print(f"  resource_id: \"{resource_id}\"")
            print(f"  voice: \"{voices[0]}\"  # 可选: {', '.join(voices)}")
            break
    else:
        print("\n❌ 未找到可用配置")
        print("建议:")
        print("  1. 检查火山引擎控制台确认订阅状态")
        print("  2. 确认是否有可用余额")

    print(f"{'=' * 60}")


if __name__ == "__main__":
    print("提示：请先运行 source .env.sh\n")
    main()
