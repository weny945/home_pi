# 音乐目录说明

本目录用于存放音乐文件，供语音助手播放使用。

## 支持的格式

- MP3 (`.mp3`)
- WAV (`.wav`)
- OGG Vorbis (`.ogg`)
- FLAC (`.flac`)
- M4A (`.m4a`)
- AAC (`.aac`)

## 目录结构建议

### 方式1：平铺结构

```
assets/music/
├── song1.mp3
├── song2.wav
└── song3.flac
```

### 方式2：按艺术家分类（推荐）

```
assets/music/
├── 周杰伦/
│   ├── 叶惠美/
│   │   ├── 爷在西元前.flac
│   │   └── 晴天.flac
│   └── 七里香/
│       ├── 以父之名.mp3
│       └── 晴天.mp3
├── 邓紫棋/
│   └── 新的心跳/
│       └── 泡沫.mp3
└── 陈奕迅/
    └── 十年.mp3
```

### 方式3：按类型分类

```
assets/music/
├── 流行/
│   ├── song1.mp3
│   └── song2.mp3
├── 古典/
│   ├── track1.flac
│   └── track2.flac
└── 氛围/
    ├── ambient1.ogg
    └── ambient2.ogg
```

## 添加音乐的方法

### 方法1：直接复制

```bash
cp /path/to/your/music/*.mp3 assets/music/
```

### 方法2：创建软链接（推荐）

```bash
ln -s /path/to/your/music/Artist assets/music/Artist
```

### 方法3：通过U盘拷贝

1. 将U盘插入树莓派
2. 挂载U盘
3. 复制音乐文件到 `assets/music/`

## 注意事项

1. **文件名编码**：建议使用英文或拼音文件名，避免中文乱码
2. **音频质量**：推荐使用 FLAC 或高质量 MP3 (320kbps)
3. **文件权限**：确保音乐文件可读

## 示例音乐文件

为了快速测试，您可以：

1. 从网上下载无版权音乐
2. 使用自己收藏的音乐
3. 转换 CD 为 MP3/FLAC 格式

## 相关配置

音乐目录可在 `config.yaml` 中修改：

```yaml
music:
  library:
    path: "./assets/music"   # 修改为其他路径
    recursive: true          # 是否扫描子目录
```
