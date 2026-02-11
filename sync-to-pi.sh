#!/bin/bash
# ========================================
# 同步项目到树莓派
# 从开发机同步到生产环境
# 版本: 2.2 - 支持千问 TTS + 流式 + 缓存
# ========================================

set -e

# 配置
PROJECT_DIR="/home/biwenyuan/PycharmProjects/home_pi"  # 开发机项目路径
PI_USER="admin"                     # 树莓派用户名
PI_HOST="192.168.2.163"          # 树莓派 IP 地址
PI_DIR="~/home_pi"               # 树莓派项目路径

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

echo_note() {
    echo -e "${CYAN}[NOTE]${NC} $1"
}

# 检查项目目录
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ 项目目录不存在: $PROJECT_DIR"
    echo "请修改脚本中的 PROJECT_DIR 变量"
    exit 1
fi

echo_info "项目目录: $PROJECT_DIR"
echo_info "目标主机: $PI_USER@$PI_HOST:$PI_DIR"
echo ""

# 检查网络连接
echo_info "检查网络连接..."
if ! ping -c 1 -W 2 "$PI_HOST" > /dev/null 2>&1; then
    echo "❌ 无法连接到 $PI_HOST"
    echo "请检查:"
    echo "  1. 树莓派是否开机"
    echo "  2. 网络 IP 是否正确: $PI_HOST"
    echo "  3. 是否在同一局域网"
    exit 1
fi
echo_info "✅ 网络连接正常"
echo ""

# 显示版本信息
echo "========================================"
echo "📦 项目版本信息"
echo "========================================"
echo_step "当前版本: v2.2.0"
echo_step "阶段: 第二阶段 2.2 (千问 TTS + 流式 + 缓存)"
echo ""

# 检查 Piper TTS 模型文件
echo "========================================"
echo "🎯 检查模型文件"
echo "========================================"

PIPER_MODEL_DIR="$PROJECT_DIR/models/piper"
PIPER_MODEL="$PIPER_MODEL_DIR/zh_CN-huayan-medium.onnx"
PIPER_CONFIG="$PIPER_MODEL_DIR/zh_CN-huayan-medium.onnx.json"

if [ -f "$PIPER_MODEL" ] && [ -f "$PIPER_CONFIG" ]; then
    MODEL_SIZE=$(du -h "$PIPER_MODEL" | cut -f1)
    echo_info "✅ Piper TTS 模型文件存在"
    echo_note "   模型: $PIPER_MODEL"
    echo_note "   大小: $MODEL_SIZE"
    echo_note "   将同步到树莓派"
else
    echo_warn "⚠️  Piper TTS 模型文件不存在"
    echo_warn "   需要的文件:"
    echo_warn "   - $PIPER_MODEL"
    echo_warn "   - $PIPER_CONFIG"
    echo ""
    echo_warn "请在树莓派上手动下载模型，或先下载再同步:"
    echo_warn "   cd $PIPER_MODEL_DIR"
    echo_warn "   wget https://huggingface.co/rhasspy/piper-voices/v1.0.0/zh_CN/zh_CN-huayan-medium/onnx/zh_CN-huayan-medium.onnx"
    echo_warn "   wget https://huggingface.co/rhasspy/piper-voices/v1.0.0/zh_CN/zh_CN-huayan-medium/onnx/zh_CN-huayan-medium.onnx.json"
    echo ""
    read -p "是否继续同步（不含模型）? (y/N): " sync_without_model
    if [[ ! "$sync_without_model" =~ ^[Yy]$ ]]; then
        echo "已取消"
        exit 0
    fi
fi

# FunASR 模型说明 (v1.2 新增)
echo ""
echo_note "📌 FunASR 模型说明 (v1.2 新增):"
echo_note "   - SenseVoiceSmall (~200MB)"
echo_note "   - fsmn-vad (~10MB)"
echo_note "   - 首次运行时自动下载到 ~/.cache/modelscope/"
echo_note "   - 无需手动同步"

echo ""

# 询问是否继续
echo_warn "即将同步项目到树莓派"
read -p "是否继续? (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 0
fi

echo ""
echo_info "开始同步..."
echo "========================================"

# 使用 rsync 同步
rsync -avz --progress \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='logs/*' \
    --exclude='*.log' \
    --exclude='.pytest_cache' \
    --exclude='htmlcov' \
    --exclude='.coverage' \
    --exclude='test_*.wav' \
    --exclude='test_recording.wav' \
    --exclude='*.tar.gz' \
    --exclude='.DS_Store' \
    --exclude='*.pid' \
    --exclude='.idea/' \
    --exclude='assets/music/*.mp3' \
    --exclude='assets/music/*.flac' \
    --exclude='assets/music/*.wav' \
    --exclude='assets/music/*.ogg' \
    --exclude='assets/music/*.m4a' \
    --exclude='assets/music/*.aac' \
    --exclude='data/tts_cache/*.npy' \
    --exclude='data/tts_cache/metadata.json' \
    "$PROJECT_DIR/" \
    "$PI_USER@$PI_HOST:$PI_DIR/"

echo "========================================"
echo_info "同步完成！"
echo ""

# 显示同步内容摘要
echo "========================================"
echo "📊 同步内容摘要"
echo "========================================"
echo_step "✅ 源代码文件"
echo_step "✅ 配置文件 (config.yaml)"
echo_step "✅ 单元测试"
echo_step "✅ 集成测试"
if [ -f "$PIPER_MODEL" ]; then
    echo_step "✅ Piper TTS 模型 (~63MB)"
else
    echo_warn "⚠️  Piper TTS 模型（需要手动下载）"
fi
echo_note "📌 FunASR 模型（首次运行自动下载 ~210MB）"
echo ""

# 显示后续步骤
echo "========================================"
echo "📋 在树莓派上执行以下命令:"
echo "========================================"
echo ""
echo "1. 进入项目目录:"
echo "   cd ~/home_pi"
echo ""
echo "2. 如果模型未同步，下载 Piper TTS 模型:"
echo "   mkdir -p models/piper"
echo "   cd models/piper"
echo "   wget https://huggingface.co/rhasspy/piper-voices/v1.0.0/zh_CN/zh_CN-huayan-medium/onnx/zh_CN-huayan-medium.onnx"
echo "   wget https://huggingface.co/rhasspy/piper-voices/v1.0.0/zh_CN/zh_CN-huayan-medium/onnx/zh_CN-huayan-medium.onnx.json"
echo "   cd ~/home_pi"
echo ""
echo "3. 激活虚拟环境并安装依赖:"
echo "   source .venv/bin/activate"
echo "   pip install -r requirements-arm64.txt"
echo ""
echo "4. 验证 TTS 引擎 (v1.1):"
echo "   python3 tests/manual/test_software.py"
echo "   # 选择 [1] 测试 TTS 引擎"
echo ""
echo "5. 验证 STT 引擎 (v1.2 新增):"
echo "   python3 tests/manual/test_phase12_stt.py"
echo "   # 选择 [1] 测试 STT 引擎"
echo ""
echo "6. 测试完整流程 (v1.2 新增):"
echo "   python3 tests/manual/test_phase12_stt.py"
echo "   # 选择 [3] 测试完整交互流程"
echo ""
echo "7. 测试音频质量检测 (v1.4 新增):"
echo "   python3 tests/manual/test_software.py"
echo "   # 选择 [7] 测试 Phase 1.4 音频质量检测"
echo ""
echo "8. 测试对话优化 (v1.5 新增):"
echo "   python3 tests/manual/test_software.py"
echo "   # 选择 [8] 测试 Phase 1.5 对话优化"
echo ""
echo "9. 测试闹钟功能 (v1.7 新增):"
echo "   python3 tests/manual/test_alarm_e2e.py"
echo "   # 测试设置、查询、删除闹钟"
echo ""
echo "10. 添加音乐文件 (v1.8 新增):"
echo "   # 音乐目录已同步，请手动添加音乐文件到 assets/music/"
echo "   # 支持格式: mp3, wav, ogg, flac, m4a, aac"
echo "   # 可以创建子目录分类（艺术家/专辑）"
echo ""
echo "11. 测试音乐播放 (v1.8 新增):"
echo "   python3 tests/manual/test_music_e2e.py"
echo "   # 测试本地音乐播放功能"
echo ""
echo "12. 测试 TTS 缓存 (v2.2 新增):"
echo "   python3 tests/manual/test_tts_cache.py"
echo "   # 测试缓存预热、命中率、持久化"
echo ""
echo "13. 重启服务:"
echo "   sudo systemctl restart voice-assistant.service"
echo ""
echo "14. 查看服务状态:"
echo "    sudo systemctl status voice-assistant.service"
echo ""
echo "15. 查看日志:"
echo "    sudo journalctl -u voice-assistant.service -f"
echo ""
echo "========================================"
echo "📖 版本 v2.2.0 更新内容"
echo "========================================"
echo ""
echo "✨ Phase 2.2 新增功能 (v2.2):"
echo "   - 千问 TTS 集成：高质量远程语音合成"
echo "   - 流式 TTS 支持：长文本首字延迟 ~97ms"
echo "   - TTS 缓存系统：常用短语 <1ms 响应"
echo "   - 自动预热：启动时生成常用短语"
echo "   - 持久化缓存：项目重启后依然有效"
echo ""
echo "⚠️  重要提示 (v2.2):"
echo "   - 千问 TTS 需要配置 DASHSCOPE_API_KEY"
echo "   - 流式模式会维持 WebSocket 连接，用完立即关闭"
echo "   - 长时间保持连接可能产生额外费用"
echo "   - 缓存目录: ./data/tts_cache/"
echo ""
echo "✨ Phase 1.8 新增功能 (v1.8):"
echo "   - 本地音乐播放：支持 mp3/wav/ogg/flac 等格式"
echo "   - 多级目录扫描：自动扫描 assets/music/ 下所有音乐"
echo "   - 语音控制：播放、暂停、停止、音量调节"
echo "   - 背景播放：音乐不阻塞其他功能"
echo ""
echo "✨ Phase 1.7 新增功能 (v1.7):"
echo "   - 语音定闹钟：自然语言时间解析"
echo "   - 闹钟持久化：SQLite 存储，系统重启不丢失"
echo "   - 自动响铃：后台线程检测，到时自动响铃"
echo "   - 语音交互：响铃时可语音控制停止/稍后提醒"
echo ""
echo "✨ Phase 1.5 新增功能 (v1.5):"
echo "   - 智能打断：TTS 播放时检测语音并立即停止"
echo "   - 上下文增强：延续性表达支持（如'明天呢'）"
echo "   - 自动收尾：多轮对话超时后播放道别消息"
echo "   - 技能系统框架：为未来扩展预留接口"
echo ""
echo "✨ Phase 1.4 新增功能 (v1.4):"
echo "   - 自适应VAD阈值：实时监测底噪，动态调整触发门槛"
echo "   - 音频质量检测：时长-能量双重校验"
echo "   - 文本质量检测：语义完整性检查"
echo "   - 分级重试策略：3级渐进式提示与兜底"
echo "   - 智能尾端点检测：延长超时时间，拼接断句"
echo ""
echo "✨ Phase 1.3 新增功能 (v1.3):"
echo "   - 阿里云千问 API 对话生成"
echo "   - 完整交互流程：唤醒→TTS回复→录音→识别→LLM生成→TTS播报"
echo ""
echo "✨ Phase 1.2 新增功能 (v1.2):"
echo "   - FunASR 语音识别 (STT) - SenseVoiceSmall"
echo "   - FunASR 语音活动检测 (VAD) - fsmn-vad"
echo ""
echo "📦 新增文件 (v2.2):"
echo "   - src/tts/qwen_engine.py          千问非流式 TTS"
echo "   - src/tts/qwen_realtime_engine.py 千问流式 TTS"
echo "   - src/tts/hybrid_qwen_engine.py   混合千问引擎"
echo "   - src/tts/cached_engine.py        TTS 缓存引擎"
echo "   - data/tts_cache/                 TTS 缓存目录（自动创建）"
echo ""
echo "📦 新增文件 (v1.8):"
echo "   - src/music/                    音乐播放模块"
echo "   - assets/music/                 音乐目录（需手动添加音乐文件）"
echo ""
echo "📦 新增文件 (v1.7):"
echo "   - src/alarm/                    闹钟管理模块"
echo "   - assets/alarm_ringtone.wav     闹钟铃声文件"
echo ""
echo "📦 新增文件 (v1.5):"
echo "   - src/skills/           技能系统框架"
echo ""
echo "📦 新增文件 (v1.4):"
echo "   - src/feedback/led_feedback.py     LED可视化反馈"
echo "   - tests/unit/test_vad.py          VAD单元测试"
echo ""
echo "⚙️  配置更新 (v1.8):"
echo "   music.enabled: true"
echo "   music.library.path: \"./assets/music\""
echo "   music.player.initial_volume: 0.7"
echo ""
echo "⚙️  配置更新 (v1.7):"
echo "   alarm.enabled: true"
echo "   alarm.storage.path: \"./data/alarms.db\""
echo "   alarm.ringtone.duration: 30"
echo ""
echo "⚙️  配置更新 (v1.5):"
echo "   audio_quality.interrupt.enabled: true"
echo "   conversation.enabled: true"
echo "   conversation.auto_farewell.enabled: true"
echo "   skills.enabled: false              # 框架预留"
echo ""
echo "⚙️  配置更新 (v1.4):"
echo "   audio_quality.adaptive_enabled: true"
echo "   audio_quality.vad.adaptive_enabled: true"
echo "   audio_quality.max_retries: 1"
echo ""
echo "📊 模型要求:"
echo "   - SenseVoiceSmall (~200MB) - 自动下载"
echo "   - fsmn-vad (~10MB) - 自动下载"
echo "   - Piper TTS (~63MB) - 手动下载"
echo "   - 缓存位置: ~/.cache/modelscope/"
echo ""
echo "📦 新增依赖 (v1.7):"
echo "   - dateparser>=1.2.0     - 自然语言时间解析"
echo ""
echo "📦 新增依赖 (v2.2):"
echo "   - websockets>=12.0      - 千问流式 TTS (WebSocket)"
echo "   - pydub>=0.25.0         - 千问 TTS 音频解码"
echo ""
echo "📦 新增依赖 (v1.8):"
echo "   - pygame>=2.5.0         - 音乐播放引擎"
echo ""
echo "📚 文档更新:"
echo "   - docs/Delivery/VERSION_2.2.md"
echo "   - docs/development/tts-cache-integration.md"
echo "   - docs/demand/1.5-dialogue-optimization.md"
echo "   - docs/features/music-player.md"
echo "   - docs/Delivery/VERSION_1.7.md"
echo "   - docs/Delivery/VERSION_1.8.md"
echo "   - assets/music/README.md"
echo ""
