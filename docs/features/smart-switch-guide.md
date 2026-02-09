# GeekOpen 智能开关集成指南

## 一、功能概述

本语音助手现已支持 **GeekOpen 智能开关**（零火线版）的语音控制，通过 MQTT 协议实现：

- 语音控制家电开关（开灯、关灯、切换）
- 支持多设备管理（客厅灯、卧室灯等）
- 支持批量控制（"打开所有灯"）
- 支持状态查询（"客厅灯怎么样"）

---

## 二、硬件准备

### 1. GeekOpen 智能开关

- 型号：GeekOpen 智能开关（零火线版）
- 通信协议：MQTT
- 供电：220V 零火线供电
- 控制方式：继电器输出

### 2. MQTT Broker（必需）

智能开关需要 MQTT Broker 进行通信。推荐使用 **Mosquitto**：

#### 在树莓派上安装 Mosquitto

```bash
# 更新软件包列表
sudo apt update

# 安装 MQTT Broker
sudo apt install mosquitto mosquitto-clients -y

# 启动服务
sudo systemctl start mosquitto
sudo systemctl enable mosquitto

# 验证服务状态
sudo systemctl status mosquitto
```

#### 配置 MQTT（可选，如需认证）

```bash
# 编辑配置文件
sudo nano /etc/mosquitto/mosquitto.conf

# 添加以下内容（启用用户名密码认证）
allow_anonymous false
listener 1883
password_file /etc/mosquitto/passwd

# 创建密码文件
sudo mosquitto_passwd -c /etc/mosquitto/passwd admin

# 重启服务
sudo systemctl restart mosquitto
```

---

## 三、软件配置

### 1. 安装依赖

```bash
# 激活虚拟环境
source .venv/bin/activate

# 安装 MQTT 客户端库
pip install paho-mqtt

# 或重新安装所有依赖
pip install -r requirements.txt
```

### 2. 配置智能开关

编辑 `config.yaml` 文件，添加智能开关配置：

```yaml
# ========================================
# 智能开关配置 - GeekOpen 开关控制
# ========================================
smart_switch:
  enabled: true                          # 启用智能开关功能

  # MQTT 配置
  mqtt:
    broker: "localhost"                  # MQTT Broker 地址（树莓派本地）
    port: 1883                           # MQTT 端口
    username: null                       # MQTT 用户名（可选）
    password: null                       # MQTT 密码（可选）
    client_id: "voice_assistant"         # 客户端 ID
    qos: 1                               # 服务质量等级 (0/1/2)

  # 设备配置
  devices:
    - device_id: "switch_livingroom"     # 设备 ID（MQTT 主题前缀）
      name: "客厅灯"                      # 设备名称（中文，用于语音识别）
      location: "客厅"                    # 位置（可选）
      type: "light"                      # 设备类型

    - device_id: "switch_bedroom"
      name: "卧室灯"
      location: "卧室"
      type: "light"

    - device_id: "switch_fan"
      name: "风扇"
      location: "客厅"
      type: "fan"
```

### 3. 配置 GeekOpen 开关

在 GeekOpen 开关的配置界面中设置 MQTT 参数：

- **MQTT 服务器**: 树莓派的 IP 地址（如 `192.168.1.100`）
- **端口**: `1883`
- **用户名/密码**: 如果启用了认证，填写对应的凭据
- **主题前缀**: 设备 ID（如 `switch_livingroom`）

GeekOpen 开关会订阅以下主题：
- `cmnd/{device_id}/POWER` - 控制命令
- 并发布状态到：
  - `stat/{device_id}/POWER` - 状态响应
  - `tele/{device_id}/STATE` - 遥测状态

---

## 四、语音指令示例

### 单设备控制

| 指令 | 功能 | 示例 |
|------|------|------|
| "打开客厅灯" | 打开指定设备 | 客厅灯打开 |
| "关闭卧室灯" | 关闭指定设备 | 卧室灯关闭 |
| "切换风扇" | 切换设备状态 | 风扇开关切换 |
| "客厅灯怎么样" | 查询设备状态 | 返回当前状态 |

### 批量控制

| 指令 | 功能 |
|------|------|
| "打开所有灯" | 打开所有灯类设备 |
| "关闭所有设备" | 关闭所有已注册设备 |

### 简化指令

当只说动作+设备类型时，会自动控制对应设备：

| 指令 | 解释 |
|------|------|
| "开灯" | 打开默认灯设备 |
| "关灯" | 关闭默认灯设备 |

---

## 五、测试与验证

### 1. MQTT 连接测试

```bash
# 在另一个终端订阅状态主题
mosquitto_sub -h localhost -t "stat/#" -v

# 手动发送控制命令
mosquitto_pub -h localhost -t "cmnd/switch_livingroom/POWER" -m "ON"
```

### 2. 语音助手测试

```bash
# 启动语音助手
python main.py

# 说出语音指令
"派蒙，打开客厅灯"  # 唤醒 + 控制指令
```

### 3. 查看日志

```bash
# 查看详细日志
tail -f logs/phase1.log

# 查找 MQTT 相关日志
grep "MQTT" logs/phase1.log
```

---

## 六、故障排查

### 问题 1: MQTT 连接失败

**症状**: 日志显示 "MQTT 连接失败"

**解决方案**:
1. 检查 Mosquitto 服务是否运行：`sudo systemctl status mosquitto`
2. 检查 Broker 地址是否正确：`ping localhost` 或 `ping <IP>`
3. 检查端口是否开放：`netstat -an | grep 1883`

### 问题 2: 设备无响应

**症状**: 语音指令发出后设备没有反应

**解决方案**:
1. 检查设备 ID 是否与 GeekOpen 配置一致
2. 使用 `mosquitto_sub` 监听 `stat/#` 主题，确认设备是否在线
3. 手动发送 MQTT 命令测试：`mosquitto_pub -t "cmnd/{device_id}/POWER" -m "ON"`

### 问题 3: 语音识别错误

**症状**: 识别不出设备名称或指令

**解决方案**:
1. 检查配置中的 `name` 字段是否使用中文
2. 确保设备名称在指令中完整说出（如"客厅灯"而不是"灯"）
3. 查看日志中的识别结果：`grep "识别到开关意图" logs/phase1.log`

---

## 七、扩展设备

### 添加新设备

1. 在 `config.yaml` 中添加设备配置：

```yaml
devices:
  - device_id: "switch_kitchen"
    name: "厨房灯"
    location: "厨房"
    type: "light"
```

2. 在 GeekOpen 开关中设置相同的 `device_id`

3. 重启语音助手

### 支持的设备类型

| 类型 | 代码 | 语音关键词 |
|------|------|------------|
| 灯光 | `light` | 灯、照明、电灯、灯具 |
| 风扇 | `fan` | 风扇、吊扇、排气扇 |
| 插座 | `socket` | 插座、插排、电源 |
| 空调 | `ac` | 空调、冷气 |
| 暖气 | `heater` | 暖气、加热器 |
| 窗帘 | `curtain` | 窗帘、卷帘 |

---

## 八、技术架构

```
语音输入
    ↓
唤醒词检测（派蒙）
    ↓
STT 语音识别 → "打开客厅灯"
    ↓
意图检测 → SwitchIntent(action=on, device=客厅灯)
    ↓
MQTT 发布 → cmnd/switch_livingroom/POWER = "ON"
    ↓
GeekOpen 开关响应 → stat/switch_livingroom/POWER = "ON"
    ↓
TTS 语音回复 → "好的，已打开客厅灯"
```

---

## 九、安全注意事项

1. **电气安全**: 安装零火线开关前务必断电
2. **负载限制**: GeekOpen 开关有最大负载限制，请参考产品规格
3. **MQTT 安全**: 建议启用用户名密码认证，避免未授权访问
4. **网络隔离**: 建议将智能家居设备放在独立的网络中

---

## 十、参考资料

- [GeekOpen 智能开关文档](https://wiki.geekopen.com/)
- [Mosquitto MQTT Broker 文档](https://mosquitto.org/)
- [Tasmota 固件文档](https://tasmota.github.io/docs/)（GeekOpen 通常使用 Tasmota 固件）
