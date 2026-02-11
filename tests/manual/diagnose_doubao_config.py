"""
豆包 TTS 配置诊断工具
Doubao TTS Configuration Diagnostic Tool

用于检查火山引擎 TTS 配置是否正确
"""
import os
import sys
import json

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

def diagnose():
    """诊断豆包 TTS 配置"""

    print("=" * 60)
    print("豆包 TTS 配置诊断")
    print("=" * 60)

    # 1. 检查环境变量
    print("\n[1] 检查环境变量...")
    access_key = os.getenv("DOUBAO_ACCESS_KEY")
    app_id = os.getenv("DOUBAO_APP_ID")

    if not access_key:
        print("  ❌ DOUBAO_ACCESS_KEY 未设置")
        print("     请运行: export DOUBAO_ACCESS_KEY='your_access_key'")
    else:
        print(f"  ✅ DOUBAO_ACCESS_KEY: {access_key[:10]}...{access_key[-4:]}")

    if not app_id:
        print("  ❌ DOUBAO_APP_ID 未设置")
        print("     请运行: export DOUBAO_APP_ID='your_app_id'")
    else:
        print(f"  ✅ DOUBAO_APP_ID: {app_id}")

    # 2. 验证格式
    print("\n[2] 验证格式...")

    if access_key:
        if len(access_key) < 20:
            print(f"  ⚠️  Access Key 长度较短 ({len(access_key)} 字符)，请确认是否正确")
        else:
            print(f"  ✅ Access Key 长度正常 ({len(access_key)} 字符)")

    if app_id:
        if not app_id.isdigit():
            print(f"  ⚠️  APP ID 通常应该是纯数字，当前值: {app_id}")
        else:
            print(f"  ✅ APP ID 格式正常")

    # 3. 测试 API 连接
    print("\n[3] 测试 API 连接...")

    if not access_key or not app_id:
        print("  ⚠️  跳过 API 测试（缺少凭证）")
        return False

    import requests

    # 测试不同的 Resource ID
    resource_ids = [
        ("seed-tts-2.0", "豆包语音合成模型 2.0"),
        ("seed-tts-1.0", "豆包语音合成模型 1.0"),
    ]

    api_url = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"

    for resource_id, desc in resource_ids:
        print(f"\n  测试资源: {resource_id} ({desc})...")

        headers = {
            "X-Api-App-Id": app_id,
            "X-Api-Access-Key": access_key,
            "X-Api-Resource-Id": resource_id,
            "X-Api-Request-Id": f"test-diagnostic-{resource_id}",
            "Content-Type": "application/json",
        }

        payload = {
            "user": {"uid": "diagnostic_test"},
            "req_params": {
                "text": "测试",
                "speaker": "zh_female_shuangkuaisisi_moon_bigtts",
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

            print(f"    响应状态码: {response.status_code}")

            if response.status_code == 200:
                print(f"    ✅ {resource_id} 连接成功！")
                print(f"\n  ✅✅✅ 找到可用的 Resource ID: {resource_id} ✅✅✅")
                print(f"\n  请在 config.yaml 中设置:")
                print(f"    tts:")
                print(f"      engine: doubao")
                print(f"      doubao:")
                print(f"        resource_id: \"{resource_id}\"")
                return True

            elif response.status_code == 403:
                try:
                    error_data = response.json()
                    error_code = error_data.get("header", {}).get("code")
                    error_msg = error_data.get("header", {}).get("message", "")

                    if "not granted" in error_msg:
                        print(f"    ❌ 该资源未授权")
                    else:
                        print(f"    ❌ 认证失败: {error_msg}")
                except:
                    print(f"    ❌ 403 错误")

            elif response.status_code == 400:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("header", {}).get("message", "未知错误")
                    print(f"    ❌ 请求错误: {error_msg}")
                except:
                    print(f"    ❌ 400 错误")

            else:
                print(f"    ❌ 未知错误: {response.status_code}")

        except requests.exceptions.Timeout:
            print(f"    ❌ 请求超时")
        except requests.exceptions.ConnectionError:
            print(f"    ❌ 连接失败")
        except Exception as e:
            print(f"    ❌ 测试失败: {e}")

    print("\n  ⚠️  所有 Resource ID 测试失败")
    print("  请确认:")
    print("    1. 已在火山引擎控制台开通语音合成服务")
    print("    2. 访问: https://console.volcengine.com/speech/service")
    print("    3. 确认开通的资源包类型（1.0 或 2.0）")
    print("    4. 检查是否有可用余额或免费额度")

    return False


if __name__ == "__main__":
    print("\n提示：请先运行 source .env.sh 加载环境变量\n")
    success = diagnose()

    print("\n" + "=" * 60)
    if success:
        print("✅ 配置验证通过！")
    else:
        print("❌ 配置验证失败，请根据上述提示修复")
    print("=" * 60)

    sys.exit(0 if success else 1)
