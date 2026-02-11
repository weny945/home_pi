# 配置文件说明

## 📁 配置文件清单

| 文件 | 说明 | 是否提交到 Git |
|------|------|----------------|
| `.env.sh` | 环境变量配置（Bash 脚本格式） | ❌ **排除** |
| `config.yaml` | 实际配置文件 | ❌ **排除** |
| `config.example.yaml` | 配置示例文件（含详细说明） | ✅ **包含** |
| `start-wrapper.sh` | systemd 服务启动包装脚本 | ✅ **包含** |
| `.gitignore` | Git 忽略规则 | ✅ **包含** |

---

## 🔑 环境变量配置 (.env.sh)

### 用途
存储敏感信息（API 密钥等），避免泄露到版本控制系统。

**统一配置**：手动运行和 systemd 服务启动都使用同一个 `.env.sh` 文件。

### 使用方法

```bash
# 1. 编辑环境变量文件
vi .env.sh

# 2. 修改 API Key
export DASHSCOPE_API_KEY="sk-你的实际密钥"

# 3. 加载环境变量（手动运行时）
source .env.sh

# 4. 验证已加载
echo $DASHSCOPE_API_KEY
```

### systemd 服务如何加载环境变量

systemd 服务通过 `start-wrapper.sh` 启动脚本自动加载 `.env.sh`：

```bash
# start-wrapper.sh 脚本会：
# 1. source .env.sh 加载环境变量
# 2. 启动 Python 应用
```

**无需手动操作**，运行 `./start-service.sh` 即可。

### 配置项说明

| 环境变量 | 说明 | 获取方式 |
|---------|------|----------|
| `DASHSCOPE_API_KEY` | 千问 TTS/LLM API 密钥 | [阿里云 DashScope 控制台](https://dashscope.console.aliyun.com/) |
| `OPENAI_API_KEY` | OpenAI API 密钥（可选） | [OpenAI API Keys](https://platform.openai.com/api-keys) |

---

## 📋 配置文件 (config.yaml)

### 创建配置文件

```bash
# 从示例文件创建实际配置
cp config.example.yaml config.yaml

# 根据实际情况编辑配置
vi config.yaml
```

### 关键配置项

#### 1. 千问 TTS 配置

```yaml
tts:
  engine: "hybrid-qwen"  # 推荐使用混合千问模式

  qwen:
    dashscope:
      api_key: "${DASHSCOPE_API_KEY}"  # 引用环境变量
      model: "qwen3-tts-flash"
      voice: "zhixiaobai"
```

**重要提示**：
- ✅ 优先使用 `${DASHSCOPE_API_KEY}` 环境变量
- ❌ 不要将实际 API Key 直接写在配置文件中
- 🔒 `config.yaml` 已添加到 `.gitignore`，不会被提交到 Git

#### 2. 角色名称配置

```yaml
llm:
  system_prompt: |
    你是一个名为"胡桃"的智能语音助手。
    # ... 其他配置
```

**当前角色**：胡桃（可自定义修改）

#### 3. 唤醒词配置

```yaml
wakeword:
  keywords:
    - "胡桃"  # 主要唤醒词
```

---

## 🚀 快速启动

### 方式 1：使用启动脚本（推荐）

```bash
# 一键启动（自动加载环境变量）
./start.sh

# 调试模式
./start.sh debug

# 运行测试
./start.sh test

# TTS 缓存测试
./start.sh cache
```

### 方式 2：手动启动

```bash
# 1. 加载环境变量
source .env.sh

# 2. 激活虚拟环境
source .venv/bin/activate

# 3. 设置 Python 路径
export PYTHONPATH="$PWD/src:$PYTHONPATH"

# 4. 启动应用
python main.py
```

---

## 🔒 安全最佳实践

### 1. 环境变量管理

✅ **推荐做法**：
```yaml
# config.yaml
api_key: "${DASHSCOPE_API_KEY}"  # 引用环境变量
```

❌ **不推荐做法**：
```yaml
# config.yaml
api_key: "sk-abc123..."  # 硬编码密钥（不安全）
```

### 2. Git 忽略规则

已排除的敏感文件：
- `.env.sh` - 环境变量配置
- `config.yaml` - 实际配置文件

包含在 Git 中：
- `config.example.yaml` - 配置示例
- `start-wrapper.sh` - 启动包装脚本
- `.gitignore` - 忽略规则

### 3. 首次部署检查清单

- [ ] 编辑 `.env.sh`，设置 `DASHSCOPE_API_KEY`
- [ ] 运行 `./deploy.sh`
- [ ] 从 `config.example.yaml` 创建 `config.yaml`
- [ ] 根据实际情况修改 `config.yaml`
- [ ] 验证配置：`source .env.sh`
- [ ] 运行测试：`./start.sh cache`

---

## 📝 配置验证

### 检查环境变量

```bash
source .env.sh

# 应显示类似输出：
# ✅ 环境变量已加载
# ========================================
#   DASHSCOPE_API_KEY: sk-abc123...
# ========================================
```

### 检查配置文件

```bash
# 验证 YAML 语法
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# 验证配置加载
python -c "from src.config import get_config; c = get_config(); print(c.raw_config['llm']['model'])"
```

---

## 🛠️ 常见问题

### Q1: 提示 API Key 未配置

**原因**：
- `.env.sh` 文件不存在
- 未设置 `DASHSCOPE_API_KEY`
- 手动运行时未执行 `source .env.sh`

**解决**：

```bash
# 检查文件是否存在
ls -la .env.sh

# 编辑文件
vi .env.sh

# 修改 API Key
export DASHSCOPE_API_KEY="sk-你的实际密钥"

# 加载环境变量（手动运行时）
source .env.sh

# 验证
echo $DASHSCOPE_API_KEY

# 重启服务（如果使用 systemd）
./start-service.sh
```

### Q2: 环境变量在 IDE 中不生效

**原因**：IDE 使用自己的环境变量设置

**解决**：
- PyCharm: Run → Edit Configurations → Environment Variables
- VS Code: launch.json 或 .env 文件
- 命令行：确保 `source .env.sh`

### Q3: 配置修改后不生效

**原因**：应用缓存了旧配置

**解决**：
```bash
# 重启应用
./start.sh

# 或清除 Python 缓存
find . -type d -name __pycache__ -exec rm -rf {} +
```

---

## 📚 相关文档

- [版本说明](./Delivery/VERSION_2.2.md)
- [TTS 缓存集成指南](./development/tts-cache-integration.md)
- [部署文档](./deploy/lan-deployment.md)

---

## 📞 获取帮助

- 千问 API: https://dashscope.console.aliyun.com/
- 项目 Issues: https://github.com/your-repo/home_pi/issues
