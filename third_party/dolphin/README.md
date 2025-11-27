# Dolphin ASR 转录脚本

该模块使用 **Dolphin** 多语种语音识别模型，对音频文件进行批量转录。

---
## 1. 环境配置

可参考原repo
https://github.com/DataoceanAI/Dolphin


下载最新版本dolphin
```
pip install -U dataoceanai-dolphin
```
或直接从github下载
```
pip install git+https://github.com/SpeechOceanTech/Dolphin.git 
```


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
- `id`: 片段编号
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


---

### 2.2 调用方式

#### 完整参数调用示例

```bash
cd /path/to/Multilingual-ASR-Benchmark

export PYTHONPATH=./scripts:$PYTHONPATH

python third_party/dolphin/dolphin_asr.py \
  --languages JPN ARE IDN \
  --text_dir data/text/testbatch/ref \
  --audio_dir data/audio/testbatch \
  --output_dir results \
  --model_name small \
  --model_dir /path/to/dolphin/models
```
---

### 2.3 参数说明

- **`--languages`**: 指定要处理的语种代码，支持多个语种同时处理
  - 示例: `--languages JPN ARE IDN`
  - 支持的语种代码见 2.4 支持语种部分
  - 语种代码会自动转换为大写

- **`--text_dir`**: 文本文件目录，应包含标准格式的 JSON 文件
  - 默认路径: `data/text/testbatch/ref`
  - 文件命名格式: `{language_code}.json`
  - 例如: `data/text/testbatch/ref/JPN.json`
  - 每个语种对应一个 JSON 文件，包含该语种的所有片段信息

- **`--audio_dir`**: 音频文件根目录
  - 默认路径: `data/audio/testbatch`
  - 目录结构: `{audio_dir}/{language_code}/{audio_name}.wav`
  - 例如: `data/audio/testbatch/JPN/audio_file.wav`
  - 脚本会根据 JSON 文件中的 `audio_name` 自动查找对应的音频文件

- **`--output_dir`**: 转录结果输出目录
  - 默认路径: `results`
  - 输出文件格式: `{language_code}_dolphin_{model_name}.json`
  - 如果目录不存在，会自动创建

- **`--model_name`**: 选择使用的模型
  - 可选： `base`, `small`

- **`--model_dir`**: 模型文件所在目录
  - 需指定模型文件所在目录，目录下包含对应的pt文件
  - 首次运行时会自动下载模型文件

---

### 2.4 支持语种

本测试集中，脚本支持以下语种及其映射关系：

| 语种代码 | 语言 | 地区代码 | 说明 |
|---------|------|---------|------|
| `ARE` | 阿拉伯语 (ar) | AE | 阿拉伯语-阿联酋 |
| `IRQ` | 阿拉伯语 (ar) | - | 阿拉伯语-伊拉克 |
| `DZA` | 阿拉伯语 (ar) | - | 阿拉伯语-阿尔及利亚 |
| `EGY` | 阿拉伯语 (ar) | EG | 阿拉伯语-埃及 |
| `SAU` | 阿拉伯语 (ar) | SA | 阿拉伯语-沙特 |
| `MAR` | 阿拉伯语 (ar) | MA | 阿拉伯语-摩洛哥 |
| `IDN` | 印尼语 (id) | ID | 印尼语 |
| `JPN` | 日语 (ja) | JP | 日语 |
| `KOR` | 韩语 (ko) | KR | 韩语 |
| `THA` | 泰语 (th) | TH | 泰语 |
| `VNM` | 越南语 (vi) | VN | 越南语 |
| `PHL` | 菲律宾语 (fil) | PH | 菲律宾语 |
| `MYS` | 马来语 (ms) | MY | 马来语 |
| `CHN` | 中文 (zh) | CN | 中文（普通话） |

其他语种代码参考[DataoceanAI/Dolphin](https://github.com/DataoceanAI/Dolphin/blob/main/languages.md)说明
### 语种映射说明

- **语言代码 (lang_sym)**: Dolphin 模型使用的语言标识符
- **地区代码 (region_sym)**: 可选的地区标识符，用于区分同一语言的不同变体
- 如果地区代码为空（`""`），则只指定语言，不指定地区
- 如果语种代码不在映射表中，脚本会使用自动语言检测


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
    model
) -> str:
```

#### 参数说明

- **`audio_path`** (str): 音频文件的绝对路径
- **`start_time`** (float): 起始时间（秒）
- **`end_time`** (float): 结束时间（秒）
- **`language`** (str): 国家代码（如 "ARE", "IRQ", "JPN"），将自动映射到 dolphin 支持的语言代码
- **`model`**: 已加载的 dolphin 模型对象

#### 返回值

- **`str`**: 转录文本（不含特殊符号）

#### 使用示例

```python
from dolphin.transcribe import load_model
from dolphin_asr import transcribe_audio

# 加载模型
model = load_model(
    model_name="small",
    model_dir="/path/to/dolphin/models"
)

# 转录单个音频片段
transcription = transcribe_audio(
    audio_path="/path/to/audio_file.wav",
    start_time=0.41,
    end_time=8.422,
    language="ARE",
    model=model
)

print(transcription)
```
