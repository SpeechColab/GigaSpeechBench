# 🎙️ Google Speech V2 (Chirp) ASR Client

This module wraps **Google Cloud Speech-to-Text V2 API**（主要使用 **Chirp 3** 模型），for high-accuracy transcription of multilingual audio。

This script is designed for **short audio (< 60s)** synchronous inference scenarios，supports reading local files directly。

## ⚠️ Important: Audio Duration and Inference Mode

在使用前，请务必了解 Google Speech V2 API 对音频时长的处理机制：

1. **short audio (< 60s)**
   - **模式**：同步识别 (Synchronous Recognize)。
   - **输入**：支持直接发送本地音频文件的二进制数据。
   - **本脚本功能**：本客户端核心通过此接口实现，会自动截取Concurrency送音频数据。
   - [📚 官方文档：同步识别](https://docs.cloud.google.com/speech-to-text/docs/sync-recognize)
2. **长音频 (> 60s)**
   - **模式**：批量识别 (Batch Recognize)。
   - **输入**：**不支持本地文件**。必须先将音频上传到 **Google Cloud Storage (GCS)** 存储桶 (gs://...)。
   - **限制**：如果您需要处理长音频文件，请自行实现上传 GCS 及 Batch API 的调用逻辑，或将其切分为短片段使用本脚本。
   - [📚 官方文档：批量识别](https://docs.cloud.google.com/speech-to-text/docs/batch-recognize)

## 🛠️ Environment Setup

### 1. 系统要求

- Python 3.8+
- **FFmpeg**: `pydub` 依赖 FFmpeg 处理音频。
  - Ubuntu: `sudo apt-get install ffmpeg`
  - CentOS: `sudo yum install ffmpeg`
  - Mac: `brew install ffmpeg`

### 2. Python 依赖安装

```
pip install google-cloud-speech pydub tqdm google-api-core
```

### 3. Google Cloud 认证配置 (关键)

在运行脚本前，必须配置 Google Cloud 访问凭证 (ADC)。您可以选择以下任一方式：

**方式一：使用 gcloud 命令行直接登录 (推荐本地开发)**

如果您安装了 Google Cloud SDK，可以直接在终端运行以下命令进行授权，无需管理密钥文件：

```
gcloud auth application-default login
```

**方式二：使用 Service Account 密钥文件**

1. 在 GCP 控制台创建 Service Account 并下载 JSON 密钥文件。
2. 设置环境变量指向该密钥文件：

```
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
```

👉 **官方详细认证指南**：[如何为本地开发环境设置 ADC](https://cloud.google.com/docs/authentication/provide-credentials-adc)

## 💻 命令行使用 (CLI Usage)

该脚本内置了命令行接口，可以直接对指定目录下的音频文件进行批量转录。

### 基本用法

```
python third_party/google_speech_v2.py --input_dir <音频目录> --lang <语言代码>
```

### Parameters说明

| 参数           | 必填 | 说明                                                         | 示例                 |
| -------------- | ---- | ------------------------------------------------------------ | -------------------- |
| `--input_dir`  | ✅    | 音频文件所在目录（支持 wav, mp3, flac 等，支持递归查找）     | `data/raw_audio/JPN` |
| `--lang`       | ✅    | 目标语言的 3 字母代码 (ISO 639-3)                            | `JPN`, `CHN`, `USA`  |
| `--project_id` | ❌    | 指定 GCP 项目 ID。**请前往** [**GCP 控制台**](https://console.cloud.google.com/welcome) **查看您的项目 ID**。 | `my-gcp-project-id`  |
| `--location`   | ❌    | 指定 API 区域端点。**支持的区域列表请查阅** [**官方文档 - Service Endpoints**](https://www.google.com/search?q=https://cloud.google.com/speech-to-text/docs/endpoints)。 | `us`, `eu`           |

### Run example

**示例 1：使用默认项目配置跑日语数据**

```
python third_party/google_speech_v2.py \
  --input_dir data/raw_audio/JPN \
  --lang JPN
```

**示例 2：指定项目 ID 和区域**

```
python third_party/google_speech_v2.py \
  --input_dir data/wenetspeech/test \
  --lang CHN \
  --project_id my-custom-project \
  --location us
```

## ⚙️ 脚本配置 (作为模块使用时)

如果您不使用命令行参数，而是直接修改代码文件 `third_party/google_speech_v2.py`，请关注以下全局变量：

```
# --- 全局默认配置 ---
PROJECT_ID = "steady-fin-478206-g9"  # [必须修改] 您的 GCP 项目 ID
DEFAULT_LOCATION = "eu"              # [可选] 区域
MODEL_NAME = "chirp_3"               # [可选] 模型版本
```

## ⚡ Python 接口调用

除了命令行运行，您也可以在其他 Python 脚本中导入核心函数 `transcribe_audio_segment` 来处理单个文件。

### 核心接口：`transcribe_audio_segment`

```
from third_party.google_speech_v2 import transcribe_audio_segment

def transcribe_audio_segment(
    audio_path: str, 
    start: float = None, 
    end: float = None, 
    language: str = None
) -> TranscriptionSegment:
    ...
```

#### Input参数

| 参数名       | 类型    | 必填 | 说明                                             |
| ------------ | ------- | ---- | ------------------------------------------------ |
| `audio_path` | `str`   | ✅    | 本地音频文件的绝对或相对路径。                   |
| `start`      | `float` | ❌    | 截取的开始时间（秒）。默认为 `None` (从头开始)。 |
| `end`        | `float` | ❌    | 截取的结束时间（秒）。默认为 `None` (直到结束)。 |
| `language`   | `str`   | ✅    | 3位语言代码 (ISO 639-3)，如 `"CHN"`, `"USA"`。   |

#### Output结构

函数返回一个 `TranscriptionSegment` (namedtuple) 对象：

- `text` (str): 识别出的文本。**如果API调用失败或时长超限，此字段可能为 `None`**。
- `audio_path` (str): 原始音频路径。
- `start_time` (float): 实际处理的开始时间。
- `end_time` (float): 实际处理的结束时间。

### 代码示例

```
from pathlib import Path
from third_party.google_speech_v2 import transcribe_audio_segment

# 1. 定义您的数据目录
my_audio_dir = Path("./my_data")

# 2. 遍历文件并调用接口
for audio_file in my_audio_dir.glob("*.wav"):
    try:
        # 调用接口process单个文件
        result = transcribe_audio_segment(
            audio_path=str(audio_file),
            language="CHN"
        )
        
        # 3. process结果
        if result.text:
            print(f"文件: {result.audio_path}")
            print(f"文本: {result.text}")
            
    except Exception as e:
        print(f"处理失败 {audio_file}: {e}")
```

## 🌍 支持Language mapping

接口的 `language` 参数接受 3 字母代码 (ISO 639-3)，脚本内部会自动映射到 Google API 所需的 BCP-47 代码。

👉 **完整支持语言列表**：[Google Cloud Speech-to-Text Supported Languages](https://cloud.google.com/speech-to-text/docs/speech-to-text-supported-languages)

当前脚本中已配置的**完整**映射关系如下：

| 简码 (ISO 639-3) | 对应语言              | Google API 代码 (BCP-47) |
| ---------------- | --------------------- | ------------------------ |
| **CHN**          | 中文 (简体)           | `cmn-Hans-CN`            |
| **USA**          | 英语 (美国)           | `en-US`                  |
| **JPN**          | 日语                  | `ja-JP`                  |
| **KOR**          | 韩语                  | `ko-KR`                  |
| **VNM**          | Vietnam语                | `vi-VN`                  |
| **THA**          | 泰语                  | `th-TH`                  |
| **IDN**          | 印度尼西亚语          | `id-ID`                  |
| **MYS**          | 马来语                | `ms-MY`                  |
| **PHL**          | Philippines语 (Tagalog)    | `fil-PH`                 |
| **EGY**          | 阿拉伯语 (埃及)       | `ar-EG`                  |
| **ARE**          | 阿拉伯语 (阿联酋)     | `ar-AE`                  |
| **DZA**          | 阿拉伯语 (阿尔及利亚) | `ar-DZ`                  |
| **IRQ**          | 阿拉伯语 (Iraq)     | `ar-IQ`                  |
| **MAR**          | 阿拉伯语 (Morocco)     | `ar-MA`                  |
| **SAU**          | 阿拉伯语 (Saudi阿拉伯) | `ar-SA`                  |

## 🧹 [可选功能] ASR 文本正则化 (Text Normalization)

本项目额外提供了一个文本正则化脚本，供有需要的用户使用。**这不是强制步骤**，但如果您需要对齐模型输出与 Ground Truth 的格式以便进行更精准的 WER 计算，可以使用此工具。

该正则化脚本主要实现了以下标准化流程（以Vietnam语为例）：

1. **Unicode NFC 归一化**:
   - **目的**: 解决字符编码不一致问题（如分解形式 NFD 与组合形式 NFC 的混用）。
   - **操作**: 统一强制转换为 **NFC** 格式。
2. **移除不可见字符**:
   - **目的**: 清除文本中潜藏的零宽空格（Zero-width space, `\u200B`）等干扰符号。
3. **移除 ASR 噪音标记**:
   - **目的**: 过滤非语言内容的标注标签。
   - **操作**: 移除如 `[laugh]`, `<unk>`, `++garbage++`, `(noise)` 等格式的标签。
4. **语言学标准化 (Vietnamese specific)**:
   - **目的**: 处理拼写变体与声调歧义。
   - **工具**: 使用 `underthesea` 库进行文本normalization（例如统一 `hòa` 与 `hoà` 的声调位置）。
5. **数字转文本 (Number to Words)**:
   - **目的**: 将阿拉伯数字转换为对应的语言读音，因为 ASR 模型通常输出纯文本。
   - **操作**: 使用 `num2words` 库将 `100` 转换为 `một trăm`（Vietnam语）或 `one hundred`（英语）。
6. **标点移除与格式化**:
   - **操作**: 移除所有标点符号，**但保留特定符号（如 `+`）**以保护编程术语（C++）或特定名称（K+）。
   - **操作**: 将所有文本转换为**小写**。
   - **操作**: 移除多余空格，确保单词间仅有一个空格。

## ⚠️ Notes

1. **API 配额与计费**: 该脚本调用 Google Cloud 付费 API，请关注 GCP 控制台的配额使用情况。
2. **网络要求**: 运行环境需要能够访问 `*.googleapis.com`。
3. **异常处理**: 接口内部已包含自动Retry mechanism（针对网络波动），但如果遇到 4xx 错误（如语言代码不支持）或文件损坏，会抛出异常，请在调用层做好 try-except 处理。