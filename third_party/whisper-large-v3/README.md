# Whisper Large V3 Multilingual ASR Complete User Guide

- DocumentationAI-generated from code, manually reviewed
- `--direct` parameter not yet verified
## Project Overview

这是一个基于Whisper Large V3模型的MultilingualAutomatic Speech Recognition(ASR)项目，支持从环境初始化到Model Download再到Batch Inference的Complete pipeline。项目使用`uv`进行Environment management，使用`hfd`tool download模型，并遵循项目unified`utils.save_transcription`format to save results。

## 📁 Project Structure

```
whisper-large-v3/
├── results/               # Fixed, aligned withutils里的save_transcriptionkeep aligned
├── auto_infer.py          # Full audio fileBatch Inference脚本
├── auto_infer_with_segments.py  # Timestamp-based segmentedInference script（new feature）
├── whisper_asr.py         # Whisper ASRwrapper class
├── language_mapping.py    # 国家代码到Language mapping
├── timestamp/             # Time戳标注数据目录（used for分段process）
├── pyproject.toml         # uv项目配置
├── uv.lock               # 依赖锁定文件
├── hfd.sh                # Hugging Face下载工具
├── install_model.sh      # Model安装脚本
├── install_ffmpeg.sh     # FFmpeg安装脚本
├── test.mp3              # Test音频文件
├── test_whisper.py       # Test脚本
└── README.md             # 本文档
```

## 🚀 Quick Start

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
- `ffmpeg`（Audio processing），使用`install_ffmpeg.sh`
- `aria2c`（Model Download，可选）,`install_model.sh`会自动下载 aria2c

### 3. 下载Whisper模型

#### 使用自动化脚本下载（推荐）
```bash
bash install_model.sh
```



### 4. 配置数据目录

确保数据目录存在并包含按国家代码组织的音频文件：

并更换auto_infer_with_segments.py中相应为真实路经()

#### Audio文件目录结构
```
data/testbatch_processed/testbatch_processed/
├── IRQ/                  # Iraq音频文件
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

#### Time戳标注目录结构（used for分段process）
```
timestamp/
├── KOR/                  # Korea时间戳标注
│   ├── KOR_audio1.json
│   ├── KOR_audio2.json
│   └── ...
├── JPN/                  # Japan时间戳标注
│   ├── JPN_audio1.json
│   └── ...
└── ...                   # 其他国家标注
```

**时间戳JSON格式示例：**
```json
{
  "audio_name": "KOR_UCkinYTS9IHqOEwR1Sze2JTw_4IhvQA7h6uI_raw",
  "segments": [
    {
      "index": 1,
      "start": 0.0,
      "end": 8.48,
      "status": "valid"
    },
    {
      "index": 2,
      "start": 8.48,
      "end": 17.92,
      "status": "valid"
    },
    {
      "index": 3,
      "start": 62.14,
      "end": 63.35,
      "status": "invalid"
    }
  ]
}
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

### Batch Inference

#### 1. Full audio file推理（auto_infer.py）

**基本用法**
```bash
# Process新的国家（跳过已process的）
python auto_infer.py

# 强制重新process所有国家
python auto_infer.py --force

# 使用自动语言检测模式
python auto_infer.py --direct

# 强制重新process并使用自动检测
python auto_infer.py --force --direct
```

**命令行参数详解**
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--force` | 强制重新处理所有国家，清除现有结果 | False |
| `--no-force` | 跳过已有结果的国家（默认行为） | False |
| `--direct` | 使用Whisper自动语言检测，跳过Language mapping | False |

#### 2. Timestamp-based segmented推理（auto_infer_with_segments.py）⭐ new feature

**适用场景：**
- 有精确的时间戳标注数据
- 需要对音频进行分段转录
- 支持无效分段的处理（保存空转录）
- 与elevenlabs实现格式对齐

**基本用法**
```bash
# Process指定国家的分段数据
python auto_infer_with_segments.py --countries KOR

# Process多个国家
python auto_infer_with_segments.py --countries KOR JPN THA

# 强制重新process所有国家
python auto_infer_with_segments.py --force

# 使用自动语言检测模式
python auto_infer_with_segments.py --direct

# Process无效分段（默认跳过无效分段）
python auto_infer_with_segments.py --countries KOR --no-skip-invalid

# 自定义目录路径
python auto_infer_with_segments.py \
  --timestamp-dir ./custom_timestamp \
  --audio-dir ./custom_audio
```

**命令行参数详解**
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--countries` | 指定要处理的国家代码列表（空格分隔） | 处理所有可用国家 |
| `--force` | 强制重新处理所有国家，清除现有结果 | False |
| `--direct` | 使用Whisper自动语言检测，跳过Language mapping | False |
| `--no-skip-invalid` | 处理包括无效分段在内的所有分段 | False（默认跳过无效分段） |
| `--timestamp-dir` | 时间戳JSON文件目录路径 | `./timestamp` |
| `--audio-dir` | 音频文件目录路径 | 配置中的默认路径 |

**输出特点：**
- 每个音频分段独立调用 `save_transcription()`
- 无效分段保存空字符串 `""`
- Output format与elevenlabs实现完全对齐
- 支持WER计算系统

#### Output格式

**统一Output format**
两种脚本都使用相同的Output format，Save results在 `./results/` 目录中，文件命名格式：
- `{country_code}_whisper-large-v3.json`

**标准JSON格式**
```json
[
    {
        "path": "KOR/KOR_UCkinYTS9IHqOEwR1Sze2JTw_4IhvQA7h6uI_raw.wav",
        "text": "지금까지 오클릭이었습니다. 끝으로 캄보디아에서 한국인 납치 감금 사건이 잇따르자...",
        "language": "KOR",
        "model": "whisper-large-v3",
        "start_time": 0.0,
        "end_time": 8.484
    },
    {
        "path": "KOR/KOR_UCkinYTS9IHqOEwR1Sze2JTw_4IhvQA7h6uI_raw.wav",
        "text": "",
        "language": "KOR",
        "model": "whisper-large-v3",
        "start_time": 62.141,
        "end_time": 63.347
    }
]
```

**字段说明**
| 字段 | 说明 | 示例 |
|------|------|------|
| `path` | 音频文件路径，格式为 `{country_code}/{filename}` | `KOR/audio.wav` |
| `text` | 转录文本，无效分段为空字符串 | `"转录内容"` 或 `""` |
| `language` | 3字母国家代码 | `"KOR"` |
| `model` | 模型名称，固定为 `"whisper-large-v3"` | `"whisper-large-v3"` |
| `start_time` | 分段开始时间（秒） | `0.0` |
| `end_time` | 分段结束时间（秒） | `8.484` |

## 🌍 语言支持

项目的Language mapping在`language_mapping.py`，未对所有映射关系进行严格验证，建议使用前 check。

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
- 使用 `language_mapping.py` 中的Language mapping
- 根据国家代码指定转录语言
- 更准确的转录结果
- 需要确保所有国家代码都有映射

### 2. 自动检测模式（--direct）
- 让Whisper自动检测音频语言
- 适used for语言未知或混合语言场景
- 跳过Language mapping检查
- 可能准确性略低于指定语言模式

## 🔍 监控和调试

### 查看process进度

**Full audio file推理**
```bash
# 运行时会显示详细进度
python auto_infer.py

# Output示例：
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

**分段推理**
```bash
# 分段推理的进度显示
python auto_infer_with_segments.py --countries KOR

# Output示例：
# === Whisper ASR Segment-based Batch Inference ===
# Found 1 countries: KOR
# ✓ All countries have language mapping
#
# --- Processing KOR segments ---
#   Loaded 1 timestamp files
#   Processing KOR_UCkinYTS9IHqOEwR1Sze2JTw_4IhvQA7h6uI_raw: 12 segments
#     [1/12] Segment 1: 0.00s - 8.48s
#       ✓ Transcribed: 지금까지 오클릭이었습니다...
#     [2/12] Segment 2: 8.48s - 17.92s
#       ✓ Transcribed: 결혼 이민자로 지금 18년째...
#     [3/12] Segment 3: 17.92s - 25.25s
#       ✓ Transcribed: 그러나 너희 나라로 돌아가라는...
#   Summary: 10/12 segments processed successfully, 0 failed
```

### Check结果文件
```bash
# 查看结果目录
ls -la results/

# 查看具体结果（推荐使用jq格式化）
cat results/KOR_whisper-large-v3.json | jq '.'

# 统计分段数量
cat results/KOR_whisper-large-v3.json | jq 'length'

# 查看无效分段（空文本）
cat results/KOR_whisper-large-v3.json | jq '.[] | select(.text == "")'
```

### 性能对比

| 功能 | auto_infer.py | auto_infer_with_segments.py |
|------|---------------|-----------------------------|
| 处理单位 | Full audio file | 音频分段 |
| 适用场景 | 快速批量处理 | 精确分段转录 |
| 输出精度 | 文件级别 | 分段级别（精确到秒） |
| 内存使用 | 较高 | 较低（分段处理） |
| 错误恢复 | 文件级别 | 分段级别 |
| WER兼容性 | ✅ | ✅ |
| elevenlabs兼容 | ✅ | ✅ |

## 🔄 持续集成

### 重新运行process

**Full audio file推理**
```bash
# Check哪些国家已process
ls results/ | sed 's/_whisper-large-v3.json//'

# 重新process特定国家（删除对应结果文件）
rm results/IRQ_whisper-large-v3.json
python auto_infer.py
```

**分段推理**
```bash
# Check哪些国家已process
ls results/ | sed 's/_whisper-large-v3.json//'

# 重新process特定国家
python auto_infer_with_segments.py --countries IRQ --force

# Process新增的时间戳文件
# 只需将新的JSON文件放入 timestamp/对应国家/ 目录即可
```

### 增量process

**音频文件增量**
- 当有新的音频文件时，只需将文件放入对应国家目录
- 重新运行脚本即可自动处理新文件

**时间戳标注增量**
- 将新的时间戳JSON文件放入 `timestamp/{country_code}/` 目录
- 重新运行分段Inference script即可处理新分段

### 故障排除

**常见问题**
1. **时间戳文件找不到音频**
   ```
   ⚠ Audio file not found: KOR_audio_name
   ```
   - 检查音频文件名是否匹配（忽略扩展名）
   - 确认音频文件存在于对应国家目录

2. **无效分段过多**
   - 检查时间戳JSON中的 `status` 字段
   - 使用 `--no-skip-invalid` 强制处理所有分段

3. **内存不足**
   - 分段推理通常比整个文件推理内存使用更低
   - 可以考虑减少Concurrency处理的文件数量

**调试模式**
```bash
# Process单个国家进行调试
python auto_infer_with_segments.py --countries KOR

# 使用自动语言检测排查Language mapping问题
python auto_infer_with_segments.py --countries KOR --direct
```

## 📋 使用建议

### 选择合适的推理方式

| 场景 | 推荐脚本 | 理由 |
|------|----------|------|
| 快速批量转录 | `auto_infer.py` | 处理速度快，适合大量文件 |
| 精确分段转录 | `auto_infer_with_segments.py` | 分段级别精度，支持时间戳 |
| WER计算需求 | 两者皆可 | 都输出标准格式，支持WER计算 |
| elevenlabs兼容 | `auto_infer_with_segments.py` | 完全对齐elevenlabs格式 |
| 混合语言音频 | `auto_infer_with_segments.py --direct` | 自动检测每段语言 |

### 最佳实践

1. **预处理阶段**
   - 确保时间戳标注质量
   - 验证音频文件与标注的对应关系
   - 检查国家代码的Language mapping

2. **处理阶段**
   - 先用小批量测试参数
   - 监控内存使用情况
   - 定期检查输出质量

3. **后处理阶段**
   - 验证Output format正确性
   - 检查无效分段的处理情况
   - 进行WER计算评估质量

