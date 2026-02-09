#!/usr/bin/env python3
"""
快速测试远程 TTS API 连接
Quick Test for Remote TTS API Connection
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_connection(server_ip, port=9880):
    """测试连接"""
    status_url = f"http://{server_ip}:{port}/status"
    tts_url = f"http://{server_ip}:{port}/tts"

    print("="*60)
    print(f"测试远程 TTS 服务器: {server_ip}:{port}")
    print("="*60)

    # 测试 1: 状态检查
    print("\n1️⃣  检查服务器状态...")
    try:
        response = requests.get(status_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ 服务器在线")
            print(f"   GPT 模型: {data['models']['gpt']}")
            print(f"   SoVITS 模型: {data['models']['sovits']}")
            print(f"   参考音频: {data['reference']['audio'][:50]}...")
        else:
            print(f"❌ 服务器响应异常: HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器")
        print("   请检查:")
        print("   1. 服务器是否已启动")
        print("   2. IP 地址是否正确")
        print("   3. 防火墙是否放行")
        return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

    # 测试 2: TTS 合成
    print("\n2️⃣  测试语音合成...")
    try:
        params = {
            "text": "你好，这是一个测试。",
            "text_lang": "zh",
            "speed": 1.0
        }
        response = requests.get(tts_url, params=params, timeout=60)

        if response.status_code == 200:
            audio_size = len(response.content)
            print(f"✅ 合成成功")
            print(f"   音频大小: {audio_size} 字节")
            print(f"   预估时长: {audio_size / 32000:.2f} 秒 (16kHz 16bit)")

            # 可选：保存到文件
            output_file = "test_remote_tts_output.wav"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            print(f"   已保存到: {output_file}")

            return True
        else:
            print(f"❌ 合成失败: HTTP {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        print("❌ 请求超时（服务器响应时间过长）")
        return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="测试远程 TTS API 连接")
    parser.add_argument("-s", "--server", type=str, default="192.168.2.141",
                        help="服务器 IP 地址")
    parser.add_argument("-p", "--port", type=int, default=9880,
                        help="端口号")

    args = parser.parse_args()

    print("\n" + "="*60)
    print("  远程 TTS API 连接测试")
    print("="*60)
    print(f"服务器: {args.server}:{args.port}")
    print("="*60)

    success = test_connection(args.server, args.port)

    print("\n" + "="*60)
    if success:
        print("✅ 所有测试通过！")
        print("\n你可以安全地在 config.yaml 中配置:")
        print(f"  tts:")
        print(f"    engine: hybrid")
        print(f"    remote:")
        print(f"      enabled: true")
        print(f"      server_ip: \"{args.server}\"")
    else:
        print("❌ 测试失败")
        print("\n请检查:")
        print("  1. GPT-SoVITS API 服务是否已启动")
        print("  2. 服务器 IP 地址是否正确")
        print("  3. 防火墙是否放行 9880 端口")
        print("  4. 树莓派和电脑是否在同一局域网")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
