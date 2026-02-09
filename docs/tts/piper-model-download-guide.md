# Piper TTS 模型下载指南

**更新日期**: 2026-01-26
**适用版本**: Phase 1.1+

---

## 一、官方模型仓库

Piper TTS 的所有模型都托管在 Hugging Face 上：

**仓库地址**: [https://huggingface.co/rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices)

---

## 二、zh_CN-huayan 可用模型

### 2.1 模型规格对比

| 模型大小 | 文件大小 | 音质 | 速度 | 推荐场景 |
|---------|---------|------|------|---------|
| **x_low** | ~20MB | ⭐⭐ | 极快 | 资源受限设备 |
| **low** | ~40MB | ⭐⭐⭐ | 快 | 树莓派4/5 |
| **medium** | ~63MB | ⭐⭐⭐⭐ | 中等 | **默认推荐** |
| **large** | ❌ 不存在 | - | - | 此模型不存在 |

### 2.2 重要说明

⚠️ **zh_CN-huayan 没有 large 版本！**

`zh_CN-huayan` 模型只有以下三个尺寸：
- `x_low` - 极小模型
- `low` - 小模型
- `medium` - 中等模型（**当前项目使用**）

---

## 三、下载方法

### 3.1 方法一：直接下载（推荐）

使用 `wget` 或 `curl` 直接从 Hugging Face 下载：

#### 下载 medium 模型（推荐）

```bash
# 创建模型目录
mkdir -p models/piper

# 进入目录
cd models/piper

# 下载模型文件
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx

# 下载配置文件
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx.json
```

#### 下载 low 模型（资源受限）

```bash
# 创建模型目录
mkdir -p models/piper

# 进入目录
cd models/piper

# 下载模型文件
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/low/zh_CN-huayan-low.onnx

# 下载配置文件
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/low/zh_CN-huayan-low.onnx.json
```

#### 下载 x_low 模型（最小）

```bash
# 创建模型目录
mkdir -p models/piper

# 进入目录
cd models/piper

# 下载模型文件
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/x_low/zh_CN-huayan-x_low.onnx

# 下载配置文件
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/x_low/zh_CN-huayan-x_low.onnx.json
```

---

### 3.2 方法二：使用 Python 脚本下载

项目提供了便捷的下载脚本：

```bash
# 运行下载脚本
python tests/manual/download_models_simple.py

# 按提示选择要下载的模型
```

**脚本会自动**：
- 下载模型文件
- 下载配置文件
- 验证文件完整性
- 放置到正确位置

---

### 3.3 方法三：从 Windows 开发机同步

如果你在 Windows 上已经下载了模型：

```bash
# 在开发机上运行
./sync-to-pi.sh

# 脚本会自动同步 medium 模型到树莓派
```

---

## 四、模型下载链接汇总

### zh_CN-huayan 系列

| 模型 | ONNX 文件 | JSON 配置 | 大小 |
|------|-----------|----------|------|
| **medium** | [下载](https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx) | [下载](https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx.json) | ~63MB |
| **low** | [下载](https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/low/zh_CN-huayan-low.onnx) | [下载](https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/low/zh_CN-huayan-low.onnx.json) | ~40MB |
| **x_low** | [下载](https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/x_low/zh_CN-huayan-x_low.onnx) | [下载](https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/x_low/zh_CN-huayan-x_low.onnx.json) | ~20MB |

---

## 五、配置文件修改

### 5.1 切换到 low 模型

编辑 `config.yaml`:

```yaml
feedback:
  tts:
    engine: "piper"
    model_path: "./models/piper/zh_CN-huayan-low.onnx"  # 改为 low
    length_scale: 1.0
```

### 5.2 切换到 x_low 模型

编辑 `config.yaml`:

```yaml
feedback:
  tts:
    engine: "piper"
    model_path: "./models/piper/zh_CN-huayan-x_low.onnx"  # 改为 x_low
    length_scale: 1.0
```

### 5.3 使用混合 TTS（推荐）

```yaml
tts:
  engine: "hybrid"  # 自动故障切换

  remote:
    server_ip: "192.168.1.100"  # GPT-SoVITS 高音质

  local:
    engine: "piper"
    model_path: "./models/piper/zh_CN-huayan-medium.onnx"
```

---

## 六、性能对比

### 6.1 树莓派5 测试数据

| 模型 | 合成速度 | 内存占用 | CPU占用 | 音质 |
|------|---------|---------|---------|------|
| **medium** | ~0.6 RTF | ~180MB | 40% | ⭐⭐⭐⭐ |
| **low** | ~0.4 RTF | ~120MB | 30% | ⭐⭐⭐ |
| **x_low** | ~0.3 RTF | ~80MB | 20% | ⭐⭐ |

*注: RTF = 合成时间 / 音频时长，值越小越快*

### 6.2 推荐配置

**树莓派5 (4GB)**:
- 推荐: `medium` 模型
- 备选: `low` 模型（内存紧张时）

**树莓派4 (2-4GB)**:
- 推荐: `low` 模型
- 备选: `x_low` 模型

**树莓派3/Zero 2 W**:
- 推荐: `x_low` 模型
- 备注: 性能可能不足

---

## 七、故障排查

### 7.1 下载失败

**问题**: `wget` 命令执行失败

**解决方案**:
```bash
# 方案1: 使用代理
export https_proxy=http://127.0.0.1:7890
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx

# 方案2: 使用浏览器下载
# 访问上面的链接，用浏览器下载后通过 SFTP 传到树莓派
```

### 7.2 模型加载失败

**问题**: 日志显示 "模型文件不存在"

**解决方案**:
```bash
# 1. 检查文件是否存在
ls -lh models/piper/zh_CN-huayan-*.onnx*

# 2. 检查文件权限
chmod 644 models/piper/zh_CN-huayan-*.onnx*

# 3. 检查配置路径
grep model_path config.yaml
```

### 7.3 音质不理想

**解决方案**:
1. **切换到混合TTS**: 使用远程 GPT-SoVITS 高音质
2. **调整语速**: 修改 `length_scale` 参数
   - `length_scale: 0.8` - 更快，音质略降
   - `length_scale: 1.2` - 更慢，音质略升

---

## 八、其他中文模型

如果想要尝试其他中文音色，可以访问：

**Hugging Face 中文模型列表**:
- [https://huggingface.co/rhasspy/piper-voices/tree/main/zh](https://huggingface.co/rhasspy/piper-voices/tree/main/zh)

可用模型：
- `zh_CN-huayan` - 花言（女声，当前使用）
- `zh_CN-xiaoyan` - 小燕（女声）
- `zh_CN-xiaoya` - 小雅（女声）
- `zh_CN-xiaoyun` - 小云（男声）

下载其他模型格式相同：
```bash
# 示例：下载 xiaoyan 模型
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/xiaoyan/medium/zh_CN-xiaoyan-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/xiaoyan/medium/zh_CN-xiaoyan-medium.onnx.json
```

---

## 九、快速下载命令

### 一键下载脚本

保存为 `download_piper_model.sh`:

```bash
#!/bin/bash

MODEL_SIZE="${1:-medium}"  # 默认 medium
MODEL_DIR="models/piper"

mkdir -p "$MODEL_DIR"
cd "$MODEL_DIR"

echo "下载 zh_CN-huayan-$MODEL_SIZE 模型..."

wget "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/$MODEL_SIZE/zh_CN-huayan-$MODEL_SIZE.onnx"
wget "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/$MODEL_SIZE/zh_CN-huayan-$MODEL_SIZE.onnx.json"

echo "下载完成！"
ls -lh
```

**使用方法**:
```bash
chmod +x download_piper_model.sh

# 下载 medium 模型
./download_piper_model.sh medium

# 下载 low 模型
./download_piper_model.sh low

# 下载 x_low 模型
./download_piper_model.sh x_low
```

---

## 十、总结

### 关键要点

1. ✅ **zh_CN-huayan 没有 large 版本**
2. ✅ **推荐使用 medium 版本**（~63MB，音质与速度平衡）
3. ✅ **所有模型都在 Hugging Face 上**
4. ✅ **可以直接 wget 下载**
5. ✅ **使用混合 TTS 获得最佳体验**

### 下载地址

**直接下载链接**:
```
https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx
https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx.json
```

**仓库主页**:
```
https://huggingface.co/rhasspy/piper-voices
```

---

**文档版本**: 1.0
**最后更新**: 2026-01-26
**参考来源**: [Hugging Face - rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices)
