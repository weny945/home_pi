#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版树莓派 TTS 客户端
用于调用 GPT-SoVITS API 生成语音并播放
"""

import requests
import pygame
import tempfile
import os
import sys

class SimpleTTSClient:
    """简化版 TTS 客户端"""

    def __init__(self, server_ip, port=9880):
        """
        初始化客户端

        Args:
            server_ip: TTS 服务器的 IP 地址
            port: 端口号，默认 9880
        """
        self.server_url = f"http://{server_ip}:{port}/tts"
        self.status_url = f"http://{server_ip}:{port}/status"

        print(f"TTS 服务器: {self.server_url}")

        # 初始化音频播放器
        pygame.mixer.init()

    def check_server(self):
        """检查服务器是否在线"""
        try:
            response = requests.get(self.status_url, timeout=5)
            if response.status_code == 200:
                info = response.json()
                print("✅ 服务器在线")
                print(f"   GPT 模型: {info['models']['gpt']}")
                print(f"   SoVITS 模型: {info['models']['sovits']}")
                return True
            else:
                print(f"❌ 服务器响应异常: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print("❌ 无法连接到服务器")
            print("   请检查:")
            print("   1. 服务器是否已启动")
            print("   2. IP 地址是否正确")
            print("   3. 防火墙是否放行 9880 端口")
            return False
        except Exception as e:
            print(f"❌ 错误: {str(e)}")
            return False

    def speak(self, text, text_lang="zh", speed=1.0):
        """
        生成语音并播放

        Args:
            text: 要合成的文本
            text_lang: 语言，默认 zh（中文）
                      支持: zh, en, ja, zh_en, ja_en, auto
            speed: 语速，默认 1.0，范围 0.6-1.65

        Returns:
            bool: 成功返回 True，失败返回 False
        """
        if not text or text.strip() == "":
            print("❌ 文本不能为空")
            return False

        print(f"\n🎤 正在生成语音: {text[:50]}{'...' if len(text) > 50 else ''}")

        # 构建请求参数
        params = {
            "text": text,
            "text_lang": text_lang,
            "speed": speed,
        }

        try:
            # 发送请求
            response = requests.get(self.server_url, params=params, timeout=60)

            if response.status_code == 200:
                print("✅ 语音生成成功")

                # 保存到临时文件
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                temp_file.write(response.content)
                temp_file.close()

                # 播放音频
                print("🔊 正在播放...")
                pygame.mixer.music.load(temp_file.name)
                pygame.mixer.music.play()

                # 等待播放完成
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)

                # 删除临时文件
                os.unlink(temp_file.name)

                print("✅ 播放完成")
                return True

            else:
                print(f"❌ 生成失败: HTTP {response.status_code}")
                try:
                    error_info = response.json()
                    print(f"   错误信息: {error_info.get('error', 'Unknown error')}")
                except:
                    print(f"   响应内容: {response.text[:200]}")
                return False

        except requests.exceptions.Timeout:
            print("❌ 请求超时，服务器响应时间过长")
            return False
        except requests.exceptions.ConnectionError:
            print("❌ 无法连接到服务器")
            return False
        except Exception as e:
            print(f"❌ 错误: {str(e)}")
            return False

    def save_audio(self, text, save_path, text_lang="zh", speed=1.0):
        """
        生成语音并保存到文件

        Args:
            text: 要合成的文本
            save_path: 保存路径
            text_lang: 语言
            speed: 语速

        Returns:
            bool: 成功返回 True
        """
        if not text or text.strip() == "":
            print("❌ 文本不能为空")
            return False

        print(f"\n💾 正在生成并保存: {text[:50]}{'...' if len(text) > 50 else ''}")

        params = {
            "text": text,
            "text_lang": text_lang,
            "speed": speed,
        }

        try:
            response = requests.get(self.server_url, params=params, timeout=60)

            if response.status_code == 200:
                with open(save_path, "wb") as f:
                    f.write(response.content)
                print(f"✅ 已保存到: {save_path}")
                return True
            else:
                print(f"❌ 生成失败: HTTP {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ 错误: {str(e)}")
            return False


def main():
    """主函数 - 使用示例"""

    # ========== 配置：修改为你的电脑 IP ==========
    SERVER_IP = "192.168.1.100"  # ⚠️ 改成你的电脑IP！
    # ============================================

    print("\n" + "=" * 60)
    print("  简化版 GPT-SoVITS TTS 客户端")
    print("=" * 60)

    # 创建客户端
    client = SimpleTTSClient(SERVER_IP)

    # 检查服务器
    print("\n检查服务器状态...")
    if not client.check_server():
        print("\n服务器连接失败，程序退出")
        sys.exit(1)

    # 示例 1: 简单播放
    print("\n" + "=" * 60)
    print("示例 1: 生成并播放中文语音")
    print("=" * 60)
    client.speak("你好，这是一个语音合成测试。")

    # 示例 2: 调整语速
    print("\n" + "=" * 60)
    print("示例 2: 调整语速播放")
    print("=" * 60)
    client.speak("今天天气真不错！", speed=1.2)

    # 示例 3: 保存到文件
    print("\n" + "=" * 60)
    print("示例 3: 保存到文件")
    print("=" * 60)
    client.save_audio(
        "这是第三段测试文本，将保存到文件。",
        save_path="output.wav"
    )

    # 示例 4: 英文语音
    print("\n" + "=" * 60)
    print("示例 4: 生成英文语音")
    print("=" * 60)
    client.speak("Hello, this is a test.", text_lang="en")

    print("\n" + "=" * 60)
    print("所有测试完成！")
    print("=" * 60)


def interactive_mode():
    """交互模式 - 持续输入文本进行语音合成"""

    # 配置
    SERVER_IP = input("请输入服务器 IP 地址 (例如: 192.168.1.100): ").strip()
    if not SERVER_IP:
        print("❌ IP 地址不能为空")
        return

    # 创建客户端
    client = SimpleTTSClient(SERVER_IP)

    # 检查服务器
    print("\n检查服务器状态...")
    if not client.check_server():
        print("\n服务器连接失败，程序退出")
        return

    print("\n" + "=" * 60)
    print("  交互模式")
    print("=" * 60)
    print("输入文本后按回车生成语音")
    print("输入 'quit' 或 'exit' 退出")
    print("=" * 60 + "\n")

    while True:
        try:
            text = input("请输入要合成的文本: ").strip()

            if text.lower() in ["quit", "exit", "q"]:
                print("\n👋 再见！")
                break

            if not text:
                print("⚠️  文本不能为空，请重新输入")
                continue

            # 生成并播放
            client.speak(text)
            print()  # 空行分隔

        except KeyboardInterrupt:
            print("\n\n👋 程序已中断")
            break
        except Exception as e:
            print(f"❌ 错误: {str(e)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="简化版 GPT-SoVITS TTS 客户端")
    parser.add_argument("-i", "--interactive", action="store_true", help="启动交互模式")
    parser.add_argument("-s", "--server", type=str, help="服务器 IP 地址")
    parser.add_argument("-t", "--text", type=str, help="要合成的文本")
    parser.add_argument("-l", "--lang", type=str, default="zh", help="语言 (zh/en/ja)")
    parser.add_argument("-o", "--output", type=str, help="保存路径")

    args = parser.parse_args()

    # 交互模式
    if args.interactive:
        interactive_mode()
    # 命令行模式
    elif args.server and args.text:
        client = SimpleTTSClient(args.server)
        if args.output:
            client.save_audio(args.text, args.output, text_lang=args.lang)
        else:
            client.speak(args.text, text_lang=args.lang)
    # 默认运行示例
    else:
        main()
