# Assets 资源文件说明

## 闹钟铃声 (alarm_ringtone.wav)

本项目使用内置的双音调铃声，无需额外的音频文件。

如果需要自定义铃声：

1. 准备一个 WAV 格式的音频文件
2. 文件要求：
   - 格式：WAV
   - 采样率：16000 Hz
   - 声道：单声道 (mono)
   - 位深：16-bit PCM
3. 将文件命名为 `alarm_ringtone.wav` 并放在此目录下
4. 修改配置文件 `config.yaml` 中的 `alarm.ringtone.file` 路径

## 当前铃声

默认使用程序生成的双音调铃声（880Hz 和 1108.73Hz 交替），每 2 秒循环。

该铃声在 `src/feedback/audio_feedback.py` 的 `_generate_alarm_ringtone()` 方法中生成。
