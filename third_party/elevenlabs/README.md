# ElevenLabs ASR Transcription Script

This module uses **ElevenLabs** 语音识别 API，对音频文件进行批量转录。

---
## 1. Environment Setup

### 1.1 Install dependencies

```bash
pip install elevenlabs pydub
```

### 1.2 获取 API Key

1. 访问 [ElevenLabs](https://elevenlabs.io/) 官网
2. 注册账号并登录
3. 在控制台中获取 API Key

### 1.3 设置 API Key

可以通过以下两种方式设置 API Key：

**方式 1: 环境变量**

```bash
export ELEVENLABS_API_KEY="your_api_key_here"
```

**方式 2: 命令行参数**

在运行脚本时通过 `--api_key` 参数传入（见下方调用方式）

---

## 2. 转录

### 2.1 数据准备

首先调用`data_process/generate_ref_json.py`脚本对参考文本文件进行合并处理

#### Text文件目录结构

文本文件应按照以下目录结构组织：

```
{text_dir}/
├── ARE.json
├── DZA.json
├── EGY.json
└── ...
```

**说明**:
- 每个language对应一个 JSON 文件
- 文件命名格式: `{language_code}.json`
- 默认路径: `data/text/testbatch/ref`

**JSON 文件格式**:

```json
[
  {
    "audio_name": "JPN_UCuTAXTexrhetbOe3zgskJBQ_eIIeZquJWFQ_raw",
    "start": 0.41,
    "end": 8.422,
    "text": "午後nine時過ぎです衝突した車両が移動しました"
  },
  {
    "audio_name": "JPN_UCuTAXTexrhetbOe3zgskJBQ_eIIeZquJWFQ_raw",
    "start": 12.04,
    "end": 17.27,
    "text": "事故からほぼ丸one日が経っても続いた影響"
  }
]
```

**字段说明**:
- `audio_name`: 音频文件名（不含扩展名）
- `start`: 起始时间（秒）
- `end`: 结束时间（秒）
- `text`: 参考文本（ground truth）

#### Audio文件目录结构

音频文件应按照以下目录结构组织：

```
{audio_dir}/
├── JPN/
│   ├── JPN_UCuTAXTexrhetbOe3zgskJBQ_eIIeZquJWFQ_raw.wav
│   └── ...
├── ARE/
│   ├── ARE_UCpTncbkcIjS0v51sJz2jhsg__N1S84dzeYU_raw.wav
│   └── ...
└── ...
```

**说明**:
- 每个language对应一个子目录
- 目录命名格式: `{language_code}`
- 音频文件命名: `{audio_name}.wav`
- 默认路径: `data/audio/testbatch`
- 脚本会自动尝试不同的扩展名来查找音频文件

---

### 2.2 调用方式

#### 完整参数调用示例

```bash
cd /path/to/Multilingual-ASR-Benchmark

export PYTHONPATH=./scripts:$PYTHONPATH

python third_party/elevenlabs/elevenlabs_asr.py \
  --languages JPN ARE IDN \
  --text_dir data/text/testbatch/ref \
  --audio_dir data/audio/testbatch \
  --output_dir results \
  --model_id scribe_v2 \
  --api_key your_api_key_here
```

#### 使用环境变量中的 API Key

```bash
export ELEVENLABS_API_KEY="your_api_key_here"

python third_party/elevenlabs/elevenlabs_asr.py \
  --languages JPN ARE IDN \
  --model_id scribe_v2
```

---

### 2.3 Parameter description

- **`--languages`**: 指定要处理的language代码，支持多个language同时处理
  - 示例: `--languages ARE IDN JPN`
  - 支持的language代码见 2.4 支持language 部分
  - language代码会自动转换为大写

- **`--text_dir`**: 文本文件目录，应包含标准格式的 JSON 文件
  - 默认路径: `data/text/testbatch/ref`
  - 文件命名格式: `{language_code}.json`
  - 例如: `data/text/testbatch/ref/ARE.json`
  - 每个language对应一个 JSON 文件，包含该language的所有片段信息

- **`--audio_dir`**: 音频文件根目录
  - 默认路径: `data/audio/testbatch`
  - 目录结构: `{audio_dir}/{language_code}/{audio_name}.wav`
  - 例如: `data/audio/testbatch/ARE/audio_file.wav`
  - 脚本会根据 JSON 文件中的 `audio_name` 自动查找对应的音频文件

- **`--output_dir`**: 转录结果输出目录
  - 默认路径: `results`
  - 输出文件格式: `{language_code}_elevenlabs_{model_id}.json`
  - 例如: `results/ARE_elevenlabs_scribe_v2.json`
  - 如果目录不存在，会自动创建

- **`--model_id`**: 选择使用的 ElevenLabs 模型
  - 可选值: `scribe_v1`, `scribe_v1_experimental`, `scribe_v2`
  - 默认值: `scribe_v1`

- **`--api_key`**: ElevenLabs API Key
  - 如果不提供，将从环境变量 `ELEVENLABS_API_KEY` 读取
  - 如果两者都未提供，脚本会报错

---

### 2.4 支持language

本测试集中，脚本支持以下language及其映射关系：

| language代码 | 语言 | ElevenLabs 语言代码 | 说明 |
|---------|------|-------------------|------|
| `AR`  | 阿拉伯语 (ar) | ara | 阿拉伯语 |
| `ARE` | 阿拉伯语 (ar) | ara | 阿拉伯语-阿联酋 |
| `IRQ` | 阿拉伯语 (ar) | ara | 阿拉伯语-Iraq |
| `DZA` | 阿拉伯语 (ar) | ara | 阿拉伯语-阿尔及利亚 |
| `EGY` | 阿拉伯语 (ar) | ara | 阿拉伯语-埃及 |
| `SAU` | 阿拉伯语 (ar) | ara | 阿拉伯语-Saudi |
| `MAR` | 阿拉伯语 (ar) | ara | 阿拉伯语-Morocco |
| `IDN` | Indonesia语 (id) | ind | Indonesia语 |
| `JPN` | 日语 (ja) | jpn | 日语 |
| `KOR` | 韩语 (ko) | kor | 韩语 |
| `THA` | 泰语 (th) | tha | 泰语 |
| `VNM` | Vietnam语 (vi) | vie | Vietnam语 |
| `PHL` | Philippines语 (fil) | fil | Philippines语 |
| `MYS` | 马来语 (ms) | msa | 马来语 |
| `USA` | 英语 (en) | eng | 英语 |
| `CHN` | 中文 (zh) | zho | 中文 (普通话) |
| `CHN-EN` | 英语 (en) | eng | 英语-中国 |
| `IDN-EN` | 英语 (en) | eng | 英语-印度 |
| `JPN-EN` | 英语 (en) | eng | 英语-Japan |
| `PHL-EN` | 英语 (en) | eng | 英语-Philippines |
| `SCT-EN` | 英语 (en) | eng | 英语-苏格兰 |
| `SGP-EN` | 英语 (en) | eng | 英语-新加坡 |
| `XIANG` | 中文 (zh) | eng | 中文-湘方言 |
| `JIN` | 中文 (zh) | eng | 中文-晋方言 |



其他language映射关系请参考[Elevenlabs官方文档](https://elevenlabs.io/docs/capabilities/speech-to-text)的Supported lanauges

### language映射说明

- **language代码**: 本测试集使用的国家/地区代码
- **ElevenLabs 语言代码**: ElevenLabs API 使用的语言标识符
---

### 2.5 API 接口

脚本提供了 `transcribe_audio` 函数接口，支持转录单一音频片段。该函数可以独立使用，无需通过命令行批量处理。

#### 函数签名

```python
def transcribe_audio(
    audio_path: str,
    start_time: float,
    end_time: float,
    language: str,
    model_id: str = "scribe_v1"
) -> str:
```

#### Parameters说明

- **`audio_path`** (str): 音频文件的绝对路径
- **`start_time`** (float): 起始时间（秒）
- **`end_time`** (float): 结束时间（秒）
- **`language`** (str): 国家代码（如 "ARE", "IRQ", "JPN"），将自动映射到 ElevenLabs API 支持的语言代码
- **`model_id`** (str): ElevenLabs 模型 ID，默认为 "scribe_v1"

#### Return值

- **`str`**: 转录文本

#### 使用示例

```python
from elevenlabs_asr import transcribe_audio
import os

# 设置 API Key（如果未设置环境变量）
os.environ["ELEVENLABS_API_KEY"] = "your_api_key_here"

# 转录单个音频片段
transcription = transcribe_audio(
    audio_path="/path/to/audio_file.wav",
    start_time=0.41,
    end_time=8.422,
    language="JPN",
    model_id="scribe_v2"
)

print(transcription)
```
