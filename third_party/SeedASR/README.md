# 🎙️ SeedASR (豆包语音识别) 转录脚本

该模块封装了**字节跳动火山引擎**的录音文件识别大模型 API，支持对音频片段进行批量转录，并提供断点续传、失败记录等能力。

- **豆包录音文件识别模型 2.0** (`volc.seedasr.auc`)
- **豆包录音文件识别模型 1.0** (`volc.bigasr.auc`)

> 🔗 [火山引擎控制台 - 录音文件识别大模型1.0](https://console.volcengine.com/speech/service/10012)
> 🔗 [火山引擎控制台 - 豆包录音文件识别模型2.0](https://console.volcengine.com/speech/service/10039)

---

## 1. 环境配置

### 1.1 安装依赖

```bash
pip install requests
```

### 1.2 获取 API 凭证

1. 访问 [火山引擎控制台](https://console.volcengine.com/) 并注册/登录
2. 开通语音识别服务，获取以下凭证：
   - **App ID** (`appid`)
   - **API Access Key** (`token`)

---

## 2. 转录

### 2.1 数据准备

#### 音频文件目录结构

音频文件应按语种目录组织，每个音频片段的文件名需遵循 `<audio_name>_<start>_<end>.wav` 格式：

```
{audio_dir}/
├── JPN/
│   ├── JPN_UCuTAXTexrhetbOe3zgskJBQ_eIIeZquJWFQ_raw_0.41_8.422.wav
│   ├── JPN_UCuTAXTexrhetbOe3zgskJBQ_eIIeZquJWFQ_raw_12.04_17.27.wav
│   └── ...
├── ARE/
│   ├── ARE_UCpTncbkcIjS0v51sJz2jhsg__N1S84dzeYU_raw_1.2_5.6.wav
│   └── ...
└── ...
```

**说明**:
- 每个语种对应一个子目录，目录名即为语种代码
- 文件名格式: `{audio_name}_{start_time}_{end_time}.{ext}`
- 脚本通过解析文件名自动提取 `audio_name`、`start_time`、`end_time`

---

### 2.2 调用方式

#### 直接运行脚本

修改 `seed_asr_infer_list.py` 底部的 `__main__` 部分，填入您的凭证：

```python
asr = SeedASR(
    appid="YOUR_APP_ID",
    token="YOUR_API_ACCESS_KEY",
    model_id="volc.seedasr.auc",  # 2.0 模型
)

file_paths = list(sorted(Path("/path/to/audio_dir").rglob("*.wav")))
summary = asr.recognize_lists(file_paths, output_root=Path("/path/to/output"))
print(summary)
```

```bash
python third_party/SeedASR/seed_asr_infer_list.py
```

---

### 2.3 参数说明

#### `SeedASR` 构造参数

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `appid` | `str` | ✅ | 火山引擎 App ID | `"YOUR_APP_ID"` |
| `token` | `str` | ✅ | API Access Key | `"YOUR_ACCESS_KEY"` |
| `model_id` | `str` | ❌ | 模型标识符 | `"volc.seedasr.auc"`是2.0模型，`"volc.bigasr.auc"`是1.0模型 |
| `requests_info` | `dict` | ❌ | 自定义请求参数（覆盖默认值） | 见下方 |

#### 模型选择

| model_id | 说明 |
|----------|------|
| `volc.seedasr.auc` | 豆包语音识别模型 **2.0**（默认，推荐） |
| `volc.bigasr.auc` | 豆包语音识别模型 **1.0** |

#### 默认请求参数 (`request_info`)
请求参数可以参考：[大模型录音文件识别标准版API](https://www.volcengine.com/docs/6561/1354868?lang=zh)
```json
{
  "model_name": "bigmodel",
  "enable_channel_split": false,
  "enable_ddc": false,
  "enable_speaker_info": false,
  "enable_punc": true,
  "enable_itn": true,
  "model_version": "400",
  "show_speech_rate": true,
  "show_volume": true
}
```

| 参数名 | 说明 | 默认值 |
|--------|------|--------|
| `enable_channel_split` | 双声道识别 | `false` |
| `enable_ddc` | 语义顺滑 | `false` |
| `enable_speaker_info` | 说话人信息输出 | `false` |
| `enable_punc` | 标点符号 | `true` |
| `enable_itn` | 文本规范化 (Inverse Text Normalization) | `true` |
| `model_version` | 模型版本 | `"400"` |
| `show_speech_rate` | 语速信息输出 | `true` |
| `show_volume` | 音量信息输出 | `true` |

---

### 2.4 批量转录接口

#### `recognize_lists`

```python
def recognize_lists(
    self,
    file_paths,
    output_root=DEFAULT_BATCH_OUTPUT_ROOT,
    resume=True,
) -> dict:
```

**参数说明**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `file_paths` | `list[Path]` | ✅ | 待转录的音频文件路径列表 |
| `output_root` | `Path` | ❌ | 输出根目录 |
| `resume` | `bool` | ❌ | 是否跳过已完成的片段（断点续传），默认 `True` |

**返回值**:

```json
{
  "total": 100,
  "completed": 95,
  "skipped": 0,
  "failed": 5
}
```

---

### 2.5 单文件识别接口

#### `recognize_audio`

```python
def recognize_audio(
    self,
    audio_path,
    language=None,
    uid="fake_uid",
) -> dict:
```

**参数说明**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `audio_path` | `str` / `Path` | ✅ | 音频文件路径 |
| `language` | `str` | ❌ | 指定识别语言（默认 `None`，由服务端自动检测） |
| `uid` | `str` | ❌ | 用户标识，默认 `"fake_uid"` |

**返回值**: API 返回的 `result` 字典，其中 `result["text"]` 为识别文本。

**使用示例**:

```python
from seed_asr_infer_list import SeedASR

asr = SeedASR(
    appid="YOUR_APP_ID",
    token="YOUR_ACCESS_KEY",
    model_id="volc.seedasr.auc",
)

result = asr.recognize_audio("/path/to/audio.wav")
print(result.get("text", ""))
```

---

## 3. 输出结构

批量转录结果按语种目录组织，每个语种目录下包含三个文件：

```
{output_root}/
├── JPN/
│   ├── results.jsonl        # 转录结果（逐行 JSON）
│   ├── completed.json       # 已完成片段列表（用于断点续传）
│   └── failed.jsonl         # 失败记录
├── ARE/
│   ├── results.jsonl
│   ├── completed.json
│   └── failed.jsonl
└── ...
```

#### `results.jsonl` 格式（每行一条记录）

```json
{
  "audio_name": "JPN_UCuTAXTexrhetbOe3zgskJBQ_eIIeZquJWFQ_raw",
  "segment_name": "JPN_UCuTAXTexrhetbOe3zgskJBQ_eIIeZquJWFQ_raw_0.41_8.422",
  "text": "午後9時過ぎです衝突した車両が移動しました",
  "language": null,
  "model": "volc.seedasr.auc",
  "start_time": 0.41,
  "end_time": 8.422
}
```

#### `failed.jsonl` 格式（每行一条记录）

```json
{
  "audio_name": "JPN_example_audio",
  "segment_name": "JPN_example_audio_1.2_5.6",
  "language": null,
  "model": "volc.seedasr.auc",
  "start_time": 1.2,
  "end_time": 5.6,
  "audio_path": "/path/to/audio.wav",
  "error": "Submit task failed.",
  "attempts": 1,
  "failed_at": "2026-03-10T12:00:00+00:00"
}
```

---

## 4. 断点续传机制

脚本内置断点续传能力，适合大规模批量转录场景：

1. 每完成一个片段，立即追加写入 `results.jsonl` 并更新 `completed.json`
2. 重新运行时，自动跳过 `completed.json` 中已记录的片段
3. 失败的片段记录在 `failed.jsonl`，成功后自动清除对应失败记录
4. 通过 `resume=False` 可关闭断点续传，强制重新处理所有片段

---

## ⚠️ 注意事项

1. **API 计费**: 该脚本调用火山引擎付费 API，请关注控制台的用量和计费情况
2. **网络要求**: 运行环境需要能够访问 `openspeech-direct.zijieapi.com`
3. **异步轮询**: 提交任务后，脚本会每秒轮询一次查询结果，直到任务完成或失败
4. **音频格式**: 支持常见音频格式（wav, mp3 等），格式通过文件扩展名自动识别
5. **文件名规范**: 音频文件名必须符合 `{audio_name}_{start}_{end}.{ext}` 格式，否则会解析失败
