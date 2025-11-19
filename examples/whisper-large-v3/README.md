# Whisper Large V3 多语言ASR完整使用指南

- 说明文档由 AI 根据当前目录的代码生成并人为 check
- `--direct` 参数还没有验证
## 项目概述

这是一个基于Whisper Large V3模型的多语言自动语音识别(ASR)项目，支持从环境初始化到模型下载再到批量推理的完整流程。项目使用`uv`进行环境管理，使用`hfd`工具下载模型，并遵循项目统一的`utils.save_transcription`格式保存结果。

## 📁 项目结构

```
whisper-large-v3/
├── results/               # 固定，和utils里的save_transcription保持对齐
├── auto_infer.py          # 批量推理主脚本
├── whisper_asr.py         # Whisper ASR封装类
├── language_mapping.py    # 国家代码到语言映射
├── pyproject.toml         # uv项目配置
├── uv.lock               # 依赖锁定文件
├── hfd.sh                # Hugging Face下载工具
├── install_model.sh      # 模型安装脚本
├── install_ffmpeg.sh     # FFmpeg安装脚本
├── test.mp3              # 测试音频文件
├── test_whisper.py       # 测试脚本
└── README.md             # 本文档
```

## 🚀 快速开始

### 1. 环境初始化
`说明，遇到网络问题，推荐对  apt、uv、pip、hf 等进行换源，推荐工具 chsrc 和 镜像网站hf-mirror，本代码中 hf 下载已经换源`



#### 安装uv（如果尚未安装）


#### 创建并激活虚拟环境
```bash
# 进入项目目录
cd /path/to/Multilingual-ASR-Benchmark/examples/whisper-large-v3

# 安装项目依赖
uv sync
```

### 2. 安装系统依赖

#### 系统工具
- `ffmpeg`（音频处理），使用`install_ffmpeg.sh`
- `aria2c`（模型下载，可选）,`install_model.sh`会自动下载 aria2c

### 3. 下载Whisper模型

#### 使用自动化脚本下载（推荐）
```bash
bash install_model.sh
```



### 4. 配置数据目录

确保数据目录存在并包含按国家代码组织的音频文件：

```
data/testbatch_processed/testbatch_processed/
├── IRQ/                  # 伊拉克音频文件
│   ├── audio1.wav
│   ├── audio2.mp3
│   └── ...
├── USA/                  # 美国音频文件
│   ├── audio1.wav
│   └── ...
└── CHN/                  # 中国音频文件
    ├── audio1.wav
    └── ...
```

## 🔧 使用方法

### 单文件测试

```bash
# 激活环境
source .venv/bin/activate

# 运行测试脚本
python test_whisper.py

# 或直接使用WhisperASR类
python -c "
from whisper_asr import WhisperASR
asr = WhisperASR()
text = asr.transcribe_and_save('test.mp3', 'ENG')
print(f'转录结果: {text}')
"
```

### 批量推理（主要功能）

#### 基本用法
```bash
# 处理新的国家（跳过已处理的）
python auto_infer.py

# 强制重新处理所有国家
python auto_infer.py --force

# 使用自动语言检测模式
python auto_infer.py --direct

# 强制重新处理并使用自动检测
python auto_infer.py --force --direct
```

#### 命令行参数详解

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--force` | 强制重新处理所有国家，清除现有结果 | False |
| `--no-force` | 跳过已有结果的国家（默认行为） | False |
| `--direct` | 使用Whisper自动语言检测，跳过语言映射 | False |

#### 输出格式

结果保存在 `auto_infer_results/` 目录中，文件命名格式：
- `{country_code}_whisper-large-v3.json`

JSON格式遵循项目标准：
```json
[
    {
        "path": "/absolute/path/to/audio.wav",
        "text": "转录的文本内容",
        "language": "IRQ",
        "model": "whisper-large-v3"
    },
    ...
]
```

## 🌍 语言支持

项目的语言映射在`language_mapping.py`，未对所有映射关系进行严格验证，建议使用前 check。

### 主要支持的语言/地区

| 语言 | 国家代码示例 |
|------|-------------|
| 阿拉伯语 | IRQ, SAU, EGY, ARE, JOR, SYR, LBN, DZA |
| 英语 | USA, GBR, AUS, CAN, IND, NGA, KEN, ZAF |
| 中文 | CHN, TWN, HKG, SGP |
| 西班牙语 | ESP, MEX, ARG, COL, PER, VEN |
| 法语 | FRA, CAN, BEL, CHE, MAR, TUN |
| 德语 | DEU, AUT, CHE |
| 俄语 | RUS, BLR, KAZ |
| 葡萄牙语 | BRA, PRT, AGO, MOZ |
| 日语 | JPN |
| 韩语 | KOR |
| 印地语 | IND |
| 土耳其语 | TUR |
| ... | ... |

### 添加新语言支持

如果需要添加新的国家代码支持：

1. 编辑 `language_mapping.py`
2. 在 `COUNTRY_CODE_TO_LANGUAGE` 字典中添加映射：
```python
COUNTRY_CODE_TO_LANGUAGE = {
    # ... 现有映射 ...
    "NEW": "new_language",  # 新增
}
```

## 📊 工作模式

### 1. 标准模式（默认）
- 使用 `language_mapping.py` 中的语言映射
- 根据国家代码指定转录语言
- 更准确的转录结果
- 需要确保所有国家代码都有映射

### 2. 自动检测模式（--direct）
- 让Whisper自动检测音频语言
- 适用于语言未知或混合语言场景
- 跳过语言映射检查
- 可能准确性略低于指定语言模式

## 🔍 监控和调试

### 查看处理进度
```bash
# 运行时会显示详细进度
python auto_infer.py

# 输出示例：
# === Whisper ASR Batch Inference ===
# Found 15 countries: ARE, CHN, DEU, EGY, ESP, FRA, GBR, IND, IRQ, ITA, JPN, KOR, SAU, TUR, USA
# Checking language mapping...
# ✓ All countries have language mapping
# Countries to process: IRQ, USA, CHN
#
# --- Processing IRQ ---
# Found 5 audio files
# [1/5] Processing: audio1.wav
#     ✓ Transcribed: 这是第一段音频的转录内容...
```

### 检查结果文件
```bash
# 查看结果目录
ls -la auto_infer_results/

# 查看具体结果
cat auto_infer_results/IRQ_whisper-large-v3.json | jq '.'
```

## 🔄 持续集成

### 重新运行处理
```bash
# 检查哪些国家已处理
ls auto_infer_results/ | sed 's/_whisper-large-v3.json//'

# 重新处理特定国家（删除对应结果文件）
rm auto_infer_results/IRQ_whisper-large-v3.json
python auto_infer.py
```

### 增量处理
当有新的音频文件时，只需将文件放入对应国家目录，重新运行脚本即可自动处理新文件。

