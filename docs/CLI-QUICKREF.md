# 语音助手 CLI 快捷命令参考

## 📋 命令列表

### 1. 查看系统状态
```bash
python3 voice_assistant_cli.py status
```

### 2. 性能监控
```bash
# 单次查看
python3 voice_assistant_cli.py perf

# 实时监控（Ctrl+C 退出）
python3 voice_assistant_cli.py perf --watch

# 自定义采样间隔
python3 voice_assistant_cli.py perf --watch --interval 0.5
```

### 3. 配置管理
```bash
# 查看配置段
python3 voice_assistant_cli.py config --show audio
python3 voice_assistant_cli.py config --show llm

# 获取配置项
python3 voice_assistant_cli.py config --get audio.sample_rate

# 设置配置项
python3 voice_assistant_cli.py config --set audio.sample_rate=16000
python3 voice_assistant_cli.py config --save

# 重新加载配置
python3 voice_assistant_cli.py config --reload

# 验证配置
python3 voice_assistant_cli.py config --validate
```

### 4. 资源管理
```bash
# 查看资源统计
python3 voice_assistant_cli.py resource --stats

# 清理所有未使用资源
python3 voice_assistant_cli.py resource --cleanup all

# 清理特定资源
python3 voice_assistant_cli.py resource --cleanup stt_model
```

### 5. 日志查看
```bash
# 查看最后20行
python3 voice_assistant_cli.py logs

# 查看最后N行
python3 voice_assistant_cli.py logs --tail 50

# 实时跟踪（Ctrl+C 退出）
python3 voice_assistant_cli.py logs --follow

# 过滤日志
python3 voice_assistant_cli.py logs --filter "ERROR"
python3 voice_assistant_cli.py logs --filter "检测到唤醒词"

# 指定日志文件
python3 voice_assistant_cli.py logs --file ./logs/phase1.log
```

### 6. 系统诊断
```bash
python3 voice_assistant_cli.py diag
```

### 7. 性能基准测试
```bash
python3 voice_assistant_cli.py benchmark
```

## 🎯 常用场景

### 场景1：系统出现问题时诊断
```bash
# 1. 查看系统状态
python3 voice_assistant_cli.py status

# 2. 运行诊断
python3 voice_assistant_cli.py diag

# 3. 查看最近日志
python3 voice_assistant_cli.py logs --tail 50
```

### 场景2：性能调优
```bash
# 1. 实时监控性能
python3 voice_assistant_cli.py perf --watch

# 2. 查看资源使用
python3 voice_assistant_cli.py resource --stats

# 3. 运行基准测试对比
python3 voice_assistant_cli.py benchmark
```

### 场景3：配置调试
```bash
# 1. 验证配置
python3 voice_assistant_cli.py config --validate

# 2. 查看当前配置
python3 voice_assistant_cli.py config --show audio_quality

# 3. 修改配置并验证
python3 voice_assistant_cli.py config --set audio_quality.max_retries=0
python3 voice_assistant_cli.py config --validate
python3 voice_assistant_cli.py config --save
python3 voice_assistant_cli.py config --reload
```

### 场景4：日志分析
```bash
# 1. 查看错误日志
python3 voice_assistant_cli.py logs --filter "ERROR" --tail 100

# 2. 查看唤醒词检测
python3 voice_assistant_cli.py logs --filter "检测到唤醒词"

# 3. 实时跟踪日志
python3 voice_assistant_cli.py logs --follow
```

## 💡 提示和技巧

### 快捷方式
```bash
# 创建别名（可选）
alias va-status='python3 voice_assistant_cli.py status'
alias va-perf='python3 voice_assistant_cli.py perf'
alias va-logs='python3 voice_assistant_cli.py logs --follow'
alias va-diag='python3 voice_assistant_cli.py diag'

# 使用别名
va-status
va-perf --watch
va-logs
va-diag
```

### 定时监控
```bash
# 每10秒显示一次系统状态
watch -n 10 'python3 voice_assistant_cli.py status'

# 每5秒显示一次性能
watch -n 5 'python3 voice_assistant_cli.py perf'
```

### 后台运行
```bash
# 后台持续监控并保存到文件
python3 voice_assistant_cli.py perf --watch > perf.log 2>&1 &
```

## 🔧 故障排查

### CLI 工具报错
```bash
# 确保在项目根目录运行
cd ~/home_pi
python3 voice_assistant_cli.py status
```

### psutil 相关错误
```bash
# psutil 是可选依赖，安装以获取详细信息
pip install psutil
```

### 导入错误
```bash
# 确保虚拟环境已激活
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 📚 更多信息

详细优化报告请参考: [docs/optimization-report.md](./optimization-report.md)
