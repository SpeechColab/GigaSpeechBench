# Multilingual-ASR-Benchmark

---

## 🗂 数据格式（Standard Data Format）

项目采用统一的 JSON 结构描述每个语音片段，确保不同语种、不同模型输出都能对齐处理。

### 字段说明

| 字段名          | 类型     | 说明                                  |
| ------------ | ------ | ----------------------------------- |
| `audio_name` | string | 音频文件名（不含扩展名），作为片段主键                 |
| `id`         | int    | 当前音频中的片段编号，与 `audio_name` 组合构成唯一 ID |
| `start`      | float  | 片段起始时间（秒）                           |
| `end`        | float  | 片段结束时间（秒）                           |
| `text`       | string | 文本转写（ASR ground truth 或模型输出）        |

---

## 🚀 使用流程

以下给出数据处理的完整步骤。

### **Step 1：准备 ground truth 数据**

请先将标注数据整理为上述 JSON 标准格式。若源于海天标注，可运行：

```bash
python data_process/generate_ref_json.py
```

最终生成的 ground truth 文件位于：

data/text/ref/<country_name>.json

格式示例：

```json
[
  {
    "audio_name": "JPN_UCuTAXTexrhetbOe3zgskJBQ_eIIeZquJWFQ_raw",
    "id": 1,
    "start": 0.41,
    "end": 8.422,
    "text": "午後nine時過ぎです衝突した車両が移動しましたただ職員らによる作業は続いています"
  },
  {
    "audio_name": "JPN_UCuTAXTexrhetbOe3zgskJBQ_eIIeZquJWFQ_raw",
    "id": 2,
    "start": 12.04,
    "end": 17.27,
    "text": "事故からほぼ丸one日が経っても続いた影響"
  }
]
```

---

### **Step 2：准备 hyp 数据（模型输出）**

在 `third_party/` 目录执行相应模型推理后，运行：

```bash
python data_process/generate_hyp_json.py
```

可自动将各模型输出整理为标准格式。

最终 hyp 文件位于：

data/text/hyp/<country_name>_<model_name>.json

格式示例：

```json
[
  {
    "audio_name": "JPN_UCuTAXTexrhetbOe3zgskJBQ_4F-qUKtHj9M_raw",
    "id": 1,
    "start": 1.407,
    "end": 9.675,
    "text": "ノーベル生理学医学賞に選ばれたのは大阪大学の坂口志紋特任教授らthree人です",
    "model": "Azure"
  },
  {
    "audio_name": "JPN_UCuTAXTexrhetbOe3zgskJBQ_4F-qUKtHj9M_raw",
    "id": 2,
    "start": 11.18,
    "end": 14.91,
    "text": "まあ嬉しい驚きと言いましょうかあの",
    "model": "Azure"
  }
]
```

---

### **Step 3：文本归一化（text normalization）**

统一处理大小写、标点、空格等：

```bash
python data_process/text_norm.py
```

---

### **Step 4：计算 ASR WER**

使用官方脚本进行对齐与评估：

```bash
python scripts/compute_wer.py
```

---

## third_party 编写指南

使用 `utils.py` 中的 `save_transcription()` 可将模型输出写入标准 JSON。需传入以下参数：

1. 音频绝对路径
2. 起始时间
3. 结束时间
4. 转录文本
5. 模型名称（如 "elevenlabs"）
6. 三字母语种代码（如 "IRQ"）
7. 片段编号 ID

第三方模型只需按此格式输出，便可无缝接入基准体系。
