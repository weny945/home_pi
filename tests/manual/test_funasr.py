from funasr import AutoModel

# 加载离线识别模型 (中文)
# 这里使用 Paraformer-small 模型，适合树莓派
model = AutoModel(
    model="paraformer-zh",  # 模型名称
    device="cpu",           # 树莓派无 GPU，使用 CPU
)

# 识别音频文件 (替换为你自己的音频路径)
# 音频格式支持 wav, mp3, m4a, flac 等
res = model.generate(input="../../test_recording.wav")
print(res)