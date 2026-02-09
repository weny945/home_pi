import openwakeword
from openwakeword.model import Model
import pyaudio
import numpy as np
import time

# 初始化模型（加载所有已下载的唤醒词，包括 alexa）
oww_model = Model()

print("正在监听唤醒词... 说 'Alexa' 试试")
print("已加载的唤醒词:", list(oww_model.models.keys()))

# 音频参数（必须与模型训练时一致）
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # 采样率：16kHz
CHUNK = 1280  # 每次读取的帧数（1280 = 80ms）

# 初始化 PyAudio
audio = pyaudio.PyAudio()
stream = audio.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    frames_per_buffer=CHUNK
)

try:
    print("开始监听...")
    while True:
        # 从麦克风读取一帧音频（bytes）
        data = stream.read(CHUNK, exception_on_overflow=False)

        # 转为 int16 numpy 数组（模型要求格式）
        audio_frame = np.frombuffer(data, dtype=np.int16)

        # 将音频帧传给模型进行预测
        prediction = oww_model.predict(audio_frame)

        # 检查每个唤醒词的置信度
        for wake_word, score in prediction.items():
            if score > 0.5:  # 可调整阈值
                print(f"✅ 唤醒成功！检测到: {wake_word} (置信度: {score:.2f})")
                time.sleep(2)  # 防止重复触发
                oww_model.reset()  # 重置内部状态（可选）

except KeyboardInterrupt:
    print("\n停止监听...")
finally:
    stream.stop_stream()
    stream.close()
    audio.terminate()