# LLM 打气词闹钟 - 实现计划

## 功能概述
- 设置闹钟时询问主题："请问这个闹钟是什么主题？"
- 使用 LLM 生成 30 秒打气词
- 闹钟响铃时播放 TTS 打气词
- 支持修改主题："派蒙，把明天的闹钟改成运动主题"

## 实现步骤

### 1. 数据库迁移 (alarm_storage.py)
```sql
ALTER TABLE alarms ADD COLUMN theme TEXT DEFAULT '起床';
ALTER TABLE alarms ADD COLUMN cheerword TEXT;
```

### 2. 修改 Alarm 数据类 ✅ 已完成
```python
@dataclass
class Alarm:
    id: int
    time: datetime
    message: str
    is_active: bool = True
    theme: str = "起床"  # 打气词主题
    cheerword: Optional[str] = None  # 预生成的打气词
```

### 3. 创建打气词生成器 ✅ 已完成
- `src/alarm/cheerword_generator.py`
- 支持主题：起床、工作、运动、学习、睡觉
- 使用 LLM 或预设模板生成 30 秒打气词

### 4. 修改意图检测器
- 添加 `set_theme` action
- 识别修改主题的意图
- 提取主题和目标闹钟

### 5. 状态机添加询问主题流程
- 设置闹钟后询问主题
- 记录待设置主题的闹钟 ID
- 处理主题输入

### 6. 修改响铃逻辑
- 使用 TTS 播放打气词代替铃声
- 支持用户打断（停止/稍后提醒）

## 简化实现方案

由于完整实现较复杂，建议采用简化方案：

### 方案 A：直接使用默认主题
- 不询问主题
- 默认使用"起床"主题
- 响铃时播放 TTS 打气词

### 方案 B：后续补充主题设置
- 先实现响铃播放打气词
- 支持后续修改主题
- 设置时不询问

## 推荐实现顺序
1. ✅ 创建 cheerword_generator.py
2. ✅ 修改 Alarm 数据类
3. ⏳ 数据库添加列
4. ⏳ 修改响铃逻辑播放打气词
5. ⏳ 支持修改主题
6. ⏳ 添加设置时询问主题

## 当前状态
- [x] cheerword_generator.py 已创建
- [x] Alarm 数据类已添加 theme 字段
- [ ] 数据库迁移待实现
- [ ] 响铃逻辑待修改
- [ ] 主题修改待实现
- [ ] 设置询问待实现
