# ElevenLabs ASR 转录脚本

该模块使用 **ElevenLabs** 语音识别 API，对音频文件进行批量转录。

---
## 1. 环境配置

### 1.1 安装依赖

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

#### 文本文件目录结构

文本文件应按照以下目录结构组织：

```
{text_dir}/
├── ARE.json
├── DZA.json
├── EGY.json
└── ...
```

**说明**:
- 每个语种对应一个 JSON 文件
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

#### 音频文件目录结构

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
- 每个语种对应一个子目录
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

### 2.3 参数说明

- **`--languages`**: 指定要处理的语种代码，支持多个语种同时处理
  - 示例: `--languages ARE IDN JPN`
  - 支持的语种代码见 2.4 支持语种 部分
  - 语种代码会自动转换为大写

- **`--text_dir`**: 文本文件目录，应包含标准格式的 JSON 文件
  - 默认路径: `data/text/testbatch/ref`
  - 文件命名格式: `{language_code}.json`
  - 例如: `data/text/testbatch/ref/ARE.json`
  - 每个语种对应一个 JSON 文件，包含该语种的所有片段信息

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

### 2.4 支持语种

本测试集中，脚本支持以下语种及其映射关系：

| 语种代码 | 语言 | ElevenLabs 语言代码 | 说明 |
|---------|------|-------------------|------|
| `ARE` | 阿拉伯语 (ar) | ara | 阿拉伯语-阿联酋 |
| `IRQ` | 阿拉伯语 (ar) | ara | 阿拉伯语-伊拉克 |
| `DZA` | 阿拉伯语 (ar) | ara | 阿拉伯语-阿尔及利亚 |
| `EGY` | 阿拉伯语 (ar) | ara | 阿拉伯语-埃及 |
| `SAU` | 阿拉伯语 (ar) | ara | 阿拉伯语-沙特 |
| `MAR` | 阿拉伯语 (ar) | ara | 阿拉伯语-摩洛哥 |
| `IDN` | 印尼语 (id) | ind | 印尼语 |
| `JPN` | 日语 (ja) | jpn | 日语 |
| `KOR` | 韩语 (ko) | kor | 韩语 |
| `THA` | 泰语 (th) | tha | 泰语 |
| `VNM` | 越南语 (vi) | vie | 越南语 |
| `PHL` | 菲律宾语 (fil) | fil | 菲律宾语 |
| `MYS` | 马来语 (ms) | msa | 马来语 |
| `ENG` | 英语 (en) | eng | 英语 |
| `CMN` | 中文 (zh) | zho | 中文（普通话） |

其他语种映射关系请参考[Elevenlabs官方文档](https://elevenlabs.io/docs/capabilities/speech-to-text)的Supported lanauges

### 语种映射说明

- **语种代码**: 本测试集使用的国家/地区代码
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

#### 参数说明

- **`audio_path`** (str): 音频文件的绝对路径
- **`start_time`** (float): 起始时间（秒）
- **`end_time`** (float): 结束时间（秒）
- **`language`** (str): 国家代码（如 "ARE", "IRQ", "JPN"），将自动映射到 ElevenLabs API 支持的语言代码
- **`model_id`** (str): ElevenLabs 模型 ID，默认为 "scribe_v1"

#### 返回值

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

#### 功能特性

- **自动语言映射**: 根据提供的国家代码自动映射到对应的 ElevenLabs 语言代码
- **自动音频处理**: 自动加载音频、截取指定时间段、转换为 WAV 格式
- **灵活的语言支持**: 如果语言代码不在映射表中，会自动使用语言检测功能
- **多格式支持**: 支持 WAV、MP3、FLAC、M4A 等音频格式


**解决方法**:
- 设置环境变量: `export ELEVENLABS_API_KEY="your_api_key"`
- 或使用命令行参数: `--api_key your_api_key`

### API 调用失败

**错误信息**: `转录失败: ...`

**可能原因**:
- API Key 无效或已过期
- API 配额已用完
- 网络连接问题
- 音频文件格式不支持

**解决方法**:
- 检查 API Key 是否有效
- 检查 ElevenLabs 账户配额
- 检查网络连接
- 确认音频文件格式是否支持

### 音频文件找不到

**错误信息**: `警告：音频文件不存在，跳过。尝试路径: ...`

**解决方法**:
- 确认音频文件路径格式：`{audio_dir}/{language_code}/{audio_name}.{ext}`
- 检查音频文件名是否与 JSON 中的 `audio_name` 完全匹配
- 确认音频文件扩展名是否在支持列表中（`.wav`, `.mp3`, `.flac`, `.m4a`）

### 不支持的 model_id

**错误信息**: `不支持的 model_id: ...`

**解决方法**:
- 检查 `--model_id` 参数是否正确
- 支持的 model_id: `scribe_v1`, `scribe_v1_experimental`, `scribe_v2`

---

## 5. 相关资源

- [ElevenLabs 官方文档](https://elevenlabs.io/docs)
- [ElevenLabs API 参考](https://elevenlabs.io/docs/api-reference)
- [pydub 文档](https://github.com/jiaaro/pydub)

---

## 6. 注意事项

1. **API 配额**: ElevenLabs API 有使用配额限制，请根据您的账户类型合理使用
2. **音频格式**: 虽然脚本支持多种音频格式，但推荐使用 WAV 格式以获得最佳兼容性
3. **网络连接**: 脚本需要稳定的网络连接来调用 ElevenLabs API
4. **成本控制**: 大量转录会产生 API 调用费用，请注意控制成本

---

## 7. 许可证

请参考项目主 LICENSE 文件。

