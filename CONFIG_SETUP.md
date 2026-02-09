# 配置文件设置指南

## 首次使用前必读

本项目的 `config.yaml` 包含敏感信息（API密钥、MQTT密码等），因此**不会**上传到 GitHub。

### 设置步骤

1. **复制配置模板**
   ```bash
   cp config.yaml.example config.yaml
   ```

2. **编辑 config.yaml 并填写你的凭证**

### 必需配置项

#### 1. 千问 LLM API Key
在 `config.yaml` 第 109 行：
```yaml
llm:
  api_key: "YOUR_DASHSCOPE_API_KEY_HERE"  # 替换为你的实际 API Key
```

获取方式：
- 访问 https://dashscope.console.aliyun.com/
- 注册/登录后获取 API Key

#### 2. 智能开关 MQTT 配置（可选）
如果需要使用智能开关功能，在 `config.yaml` 第 463-477 行配置：
```yaml
smart_switch:
  mqtt:
    username: "YOUR_MQTT_USERNAME"      # GeekOpen MQTT 用户名
    password: "YOUR_MQTT_PASSWORD"      # GeekOpen MQTT 密码
    client_id: "YOUR_CLIENT_ID"         # 客户端 ID
  prefix: "YOUR_PREFIX"                 # 主题前缀
  uid: "YOUR_UID"                       # 用户 ID
  devices:
    - mac: "YOUR_DEVICE_MAC"            # 设备 MAC 地址
```

获取方式：
- 从 GeekOpen 云平台获取 MQTT 凭证
- 在 App 中查看设备 MAC 地址

### 安全提醒

⚠️ **重要**：
- ✅ `config.yaml` 已添加到 `.gitignore`，不会上传到 GitHub
- ✅ `config.yaml.example` 可安全上传（不含敏感信息）
- ❌ 切勿将 `config.yaml` 提交到版本控制
- ❌ 切勿将 API Key 分享给他人

### 其他私密文件

以下文件也会被自动排除：
- `data/*.db` - 数据库文件（闹钟等个人数据）
- `logs/` - 日志文件（可能包含敏感信息）
- `cache/` - 缓存文件
- `models/` - 模型文件（体积过大）
- `.claude/` - Claude Code 配置目录
- `CLAUDE.md` - Claude Code 项目指令（个人开发配置）

## 疑难解答

**Q: 提交时提示 config.yaml 包含敏感信息怎么办？**
A: 确保 `.gitignore` 中包含 `config.yaml`，然后运行：
```bash
git rm --cached config.yaml  # 从 Git 追踪中移除
git commit -m "Remove config.yaml from tracking"
```

**Q: 如何验证敏感文件是否被排除？**
A: 运行以下命令：
```bash
git status --ignored
```
应该看到 `config.yaml` 在 ignored files 列表中。
