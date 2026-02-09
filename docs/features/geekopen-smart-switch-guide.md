# GeekOpen 智能开关集成指南（云 MQTT 协议）

## 一、功能概述

本语音助手现已支持 **GeekOpen 智能开关**（零火线版）的语音控制，通过 GeekOpen 云 MQTT 服务实现：

- 语音控制家电开关（开灯、关灯、切换）
- 支持多设备管理（客厅灯、卧室灯等）
- 支持多按键控制（Zero-2 有 2 个按键，Zero-4 有 4 个按键）
- 支持状态查询

---

## 二、硬件准备

### 1. GeekOpen 智能开关

- 型号：GeekOpen 零火线智能开关
  - **Zero-2**: 2 路控制（2 个按键）
  - **Zero-4**: 4 路控制（4 个按键）
- 通信协议：MQTT（云服务）
- 供电：220V 零火线供电
- 控制方式：继电器输出

### 2. GeekOpen 云 MQTT 服务

GeekOpen 提供云 MQTT 服务，无需自建 Broker。

**获取 MQTT 凭据：**
1. 下载并安装 GeekOpen App
2. 添加设备到 App
3. 在设备详情中查看 MQTT 信息

---

## 三、获取 GeekOpen MQTT 凭据

### 1. 在 App 中查看设备信息

在 GeekOpen App 中找到您的设备，记录以下信息：

| 信息 | 示例值 | 说明 |
|------|--------|------|
| MAC 地址 | `YOUR_DEVICE_MAC` | 设备唯一标识 |
| 主题前缀 (prefix) | `YOUR_PREFIX` | MQTT 主题前缀 |
| 用户 ID (uid) | `YOUR_UID` | 用户 ID |
| Client ID | `YOUR_CLIENT_ID` | MQTT 客户端 ID |
| 用户名 | `YOUR_MQTT_USERNAME` | MQTT 用户名 |
| 密码 | `YOUR_MQTT_PASSWORD` | MQTT 密码 |

### 2. MQTT 主题格式

**订阅主题（接收设备状态）：**
```
/YOUR_PREFIX/YOUR_UID/your_device_mac/publish
```
格式：`/{prefix}/{uid}/{mac小写}/publish`

**发布主题（发送控制命令）：**
```
/YOUR_PREFIX/YOUR_UID/your_device_mac/subscribe
```
格式：`/{prefix}/{uid}/{mac小写}/subscribe`

### 3. 设备状态消息格式

设备发布状态到订阅主题：

```json
{
  "messageId": "",
  "mac": "YOUR_DEVICE_MAC",
  "type": "Zero-2",
  "version": "2.1.2",
  "wifiLock": 0,
  "keyLock": 0,
  "ip": "192.168.1.150",
  "ssid": "@PHICOMM_EC",
  "key1": 0,  // 按键1状态 (0=关, 1=开)
  "key2": 0,  // 按键2状态 (Zero-2 有2个按键)
  "key3": 0,  // Zero-4 有4个按键
  "key4": 0
}
```

---

## 四、软件配置

### 1. 安装依赖

```bash
# 激活虚拟环境
source .venv/bin/activate

# 安装 MQTT 客户端库
pip install paho-mqtt

# 或重新安装所有依赖
pip install -r requirements.txt
```

### 2. 配置 GeekOpen 开关

编辑 `config.yaml` 文件：

```yaml
# ========================================
# 智能开关配置 - GeekOpen 云 MQTT 协议
# ========================================
smart_switch:
  enabled: true                          # 启用智能开关功能

  # MQTT 配置（GeekOpen 云服务）
  mqtt:
    broker: "mqtt.geek-smart.cn"         # GeekOpen MQTT Broker 地址
    port: 1883                           # MQTT 端口
    username: "YOUR_MQTT_USERNAME"             # MQTT 用户名（从 GeekOpen 获取）
    password: "YOUR_MQTT_PASSWORD"       # MQTT 密码（从 GeekOpen 获取）
    client_id: "YOUR_CLIENT_ID"            # 客户端 ID（从 GeekOpen 获取）
    qos: 1                               # 服务质量等级 (0/1/2)

  # GeekOpen 协议配置
  protocol: "geekopen"                   # 协议类型: geekopen（云协议）
  prefix: "YOUR_PREFIX"                       # 主题前缀（从 GeekOpen 获取）
  uid: "YOUR_UID"                    # 用户 ID（从 GeekOpen 获取）

  # 设备配置
  devices:
    - mac: "YOUR_DEVICE_MAC"                # 设备 MAC 地址
      name: "客厅灯"                      # 设备名称（中文，用于语音识别）
      location: "客厅"                    # 位置（可选）
      key_count: 2                       # 按键数量 (2 或 4)
      key_mapping:                       # 按键映射（可选）
        key1: "主灯"                      # 按键1对应的功能
        key2: "副灯"                      # 按键2对应的功能

    # 可以添加更多设备
    # - mac: "AABBCCDDEEFF"
    #   name: "卧室灯"
    #   location: "卧室"
    #   key_count: 2
```

### 3. 重要配置说明

**mac（设备 MAC 地址）：**
- 在 GeekOpen App 设备详情中查看
- 格式：`YOUR_DEVICE_MAC`（大小写均可，系统会自动转换）

**key_count（按键数量）：**
- Zero-2 设备：设置为 `2`（有 key1、key2）
- Zero-4 设备：设置为 `4`（有 key1、key2、key3、key4）

**prefix 和 uid：**
- 这些信息定义了 MQTT 主题的结构
- 从您的 GeekOpen 账户信息中获取

---

## 五、语音指令示例

### 单设备控制

| 指令 | 功能 | 示例 |
|------|------|------|
| "打开客厅灯" | 打开指定设备的 KEY1 | 客厅灯打开 |
| "关闭客厅灯" | 关闭指定设备的 KEY1 | 客厅灯关闭 |
| "切换客厅灯" | 切换设备状态 | 客厅灯开关切换 |
| "客厅灯怎么样" | 查询设备状态 | 返回当前状态 |

### 批量控制

| 指令 | 功能 |
|------|------|
| "打开所有灯" | 打开所有设备的 KEY1 |
| "关闭所有设备" | 关闭所有设备的 KEY1 |

### 按键映射（预留功能）

如果配置了 `key_mapping`，可以控制不同的按键：
- "打开客厅的主灯" → 控制 key1
- "打开客厅的副灯" → 控制 key2

---

## 六、测试与验证

### 1. MQTT 连接测试

使用 `mosquitto` 客户端工具测试：

```bash
# 订阅设备状态主题
mosquitto_sub -h mqtt.geek-smart.cn \
  -p 1883 \
  -u "YOUR_MQTT_USERNAME" \
  -P "YOUR_MQTT_PASSWORD" \
  -i "test_client" \
  -t "/YOUR_PREFIX/YOUR_UID/your_device_mac/publish" -v

# 发送控制命令
mosquitto_pub -h mqtt.geek-smart.cn \
  -p 1883 \
  -u "YOUR_MQTT_USERNAME" \
  -P "YOUR_MQTT_PASSWORD" \
  -i "test_client" \
  -t "/YOUR_PREFIX/YOUR_UID/your_device_mac/subscribe" \
  -m '{"key1":1}'
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
grep "MQTT\|GeekOpen" logs/phase1.log
```

---

## 七、故障排查

### 问题 1: MQTT 连接失败

**症状**: 日志显示 "MQTT 连接失败"

**解决方案**:
1. 检查网络连接：`ping mqtt.geek-smart.cn`
2. 验证凭据是否正确（用户名、密码、Client ID）
3. 确认端口 1883 未被防火墙阻止
4. 检查 `config.yaml` 中的 MQTT 配置

### 问题 2: 设备无响应

**症状**: 语音指令发出后设备没有反应

**解决方案**:
1. 使用 `mosquitto_sub` 监听设备状态，确认设备在线
2. 检查 MAC 地址是否正确（大小写不敏感）
3. 验证 prefix 和 uid 是否与 App 中一致
4. 手动发送 MQTT 命令测试（参考第六步）

### 问题 3: 状态不同步

**症状**: 设备已操作但语音助手显示的状态不对

**解决方案**:
1. 检查是否正确订阅了 `/publish` 主题
2. 查看日志中是否收到设备状态消息
3. 重启语音助手，重新连接

### 问题 4: 语音识别错误

**症状**: 识别不出设备名称或指令

**解决方案**:
1. 检查配置中的 `name` 字段是否使用中文
2. 确保设备名称在指令中完整说出（如"客厅灯"而不是"灯"）
3. 查看日志中的识别结果：`grep "识别到开关意图" logs/phase1.log`

---

## 八、扩展设备

### 添加新设备

1. 在 GeekOpen App 中添加新设备
2. 记录设备的 MAC 地址
3. 在 `config.yaml` 中添加设备配置：

```yaml
devices:
  - mac: "YOUR_DEVICE_MAC"
    name: "客厅灯"
    location: "客厅"
    key_count: 2

  # 新设备
  - mac: "AABBCCDDEEFF"
    name: "卧室灯"
    location: "卧室"
    key_count: 2
```

4. 重启语音助手

### 支持的设备类型

| 型号 | 按键数量 | 说明 |
|------|----------|------|
| Zero-2 | 2 个按键 | key1, key2 |
| Zero-4 | 4 个按键 | key1, key2, key3, key4 |

---

## 九、高级配置

### 按键映射

如果设备有多个按键，可以配置按键映射：

```yaml
devices:
  - mac: "YOUR_DEVICE_MAC"
    name: "客厅灯"
    key_count: 2
    key_mapping:
      key1: "主灯"
      key2: "副灯"
```

然后可以使用语音指令：
- "打开客厅的主灯" → 控制 key1
- "打开客厅的副灯" → 控制 key2

### 多位置管理

```yaml
devices:
  - mac: "YOUR_DEVICE_MAC"
    name: "客厅灯"
    location: "客厅"
    key_count: 2

  - mac: "AABBCCDDEEFF"
    name: "卧室灯"
    location: "卧室"
    key_count: 2

  - mac: "112233445566"
    name: "厨房灯"
    location: "厨房"
    key_count: 2
```

语音指令：
- "打开客厅的灯" → 只控制客厅灯
- "打开所有灯" → 控制所有位置的灯

---

## 十、技术架构

```
语音输入
    ↓
唤醒词检测（派蒙）
    ↓
STT 语音识别 → "打开客厅灯"
    ↓
意图检测 → SwitchIntent(action=on, device=客厅灯)
    ↓
GeekOpenController.turn_on("客厅灯", key=KEY1)
    ↓
MQTT 发布 → /YOUR_PREFIX/uid/your_device_mac/subscribe
    ↓
JSON: {"key1": 1}
    ↓
GeekOpen 开关响应 → /publish 主题
    ↓
JSON: {"key1": 1, "key2": 0, ...}
    ↓
TTS 语音回复 → "好的，已打开客厅灯"
```

---

## 十一、安全注意事项

1. **电气安全**: 安装零火线开关前务必断电
2. **负载限制**: GeekOpen 开关有最大负载限制，请参考产品规格
3. **凭据安全**: 不要泄露 MQTT 用户名和密码
4. **网络稳定**: 云 MQTT 需要稳定的网络连接

---

## 十二、参考资料

- [GeekOpen 官网](https://www.geekopen.com/)
- [paho-mqtt Python 文档](https://www.eclipse.org/paho/index.php?page=clients/python/index.php)
- [MQTT 协议规范](http://mqtt.org/)
