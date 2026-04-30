# 🌍 多语种语音识别基准

<p align="center">
  <b>面向低资源语言的大规模多语种语音识别基准</b>
</p>

<p align="center">
  <a href="README.md">🇬🇧 English</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/语言-14+-blue" alt="Languages">
  <img src="https://img.shields.io/badge/时长-308h-green" alt="Duration">
  <img src="https://img.shields.io/badge/片段-260K+-orange" alt="Segments">
  <img src="https://img.shields.io/badge/模型-14+-red" alt="Models">
  <img src="https://img.shields.io/badge/许可-非商业-lightgrey" alt="License">
</p>

<p align="center">
  <a href="#-排行榜">🏆 排行榜</a> •
  <a href="#-数据集">📦 数据集</a> •
  <a href="#-快速开始">🚀 快速开始</a> •
  <a href="#-评测">📊 评测</a> •
  <a href="#-贡献">🤝 贡献</a>
</p>

---

## 👥 参与机构

<!-- TODO: 请补充参与机构 -->

---

## 🏆 排行榜

> **低资源语言 ASR — 词/字错误率 (%) ↓**
>
> 📊 14 种语言/方言 • ⏱ ~308 小时 • 🎙 26 万+ 片段

<!-- 排行榜表格/图片占位 -->
<!-- TODO: 插入排行榜图片或交互式表格 -->

<p align="center">
  <i>📋 完整结果请查看 <code>data/all_results_besteff.xlsx</code></i>
</p>

### 🗺 语言代码

| 代码 | 语言 | 地区 |
|:-----|:-----|:-----|
| IRQ | 伊拉克阿拉伯语 | 中东 |
| DZA | 阿尔及利亚阿拉伯语 | 北非 |
| ARE | 阿联酋阿拉伯语 | 中东 |
| EGY | 埃及阿拉伯语 | 北非 |
| MAR | 摩洛哥阿拉伯语 | 北非 |
| SAU | 沙特阿拉伯语 | 中东 |
| SYR | 叙利亚阿拉伯语 | 中东 |
| IDN | 印度尼西亚语 | 东南亚 |
| MYS | 马来语 | 东南亚 |
| PHL | 菲律宾语 | 东南亚 |
| VNM | 越南语 | 东南亚 |
| THA | 泰语 | 东南亚 |
| JPN | 日语 | 东亚 |
| KOR | 韩语 | 东亚 |

---

## 📦 数据集

### 📈 概览

| 统计项 | 数值 |
|:-------|:-----|
| 语言数 | 14（+ 2 个难集） |
| 总时长 | ~308 小时 |
| 总片段数 | 26 万+ |
| 音频格式 | WAV（16kHz 单声道） |
| 标注方式 | 人工转写，含说话人元信息 |
| 数据来源 | YouTube，按语种精选 |

### 📝 数据格式

每个音频文件对应一个 JSON 标注：

```json
{
  "audio_name": "ARE#UCIJXOvggjKtCagMfxvcCzAA#RVSrDuhYDZA#raw",
  "segments": [
    {
      "start": 165.613,
      "end": 169.92,
      "text": "ياسيدي هذي مشكلة يعني طويلة، الواقع هو شوف احنا.",
      "status": "valid",
      "age_group": "Adults",
      "gender": "Male",
      "emotion": "Neutral",
      "speaker": "Speaker1",
      "index": 1,
      "text_en": "Sir, this is indeed a complex problem...",
      "text_zh": "先生，这个问题确实很复杂..."
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|:-----|:-----|:-----|
| `audio_name` | string | 音频标识符（同时也是 wav 文件名） |
| `segments[].start` | float | 片段起始时间（秒） |
| `segments[].end` | float | 片段结束时间（秒） |
| `segments[].text` | string | 源语言转写文本 |
| `segments[].status` | string | `valid`（有效）或 `invalid`（无效） |
| `segments[].text_en` | string | 英文翻译（可选） |
| `segments[].text_zh` | string | 中文翻译（可选） |

---

## 🚀 快速开始

### ⚙️ 环境依赖

```bash
pip install kaldialign
```

### 🔄 完整评测流程

```bash
# 步骤1：从原始标注生成标准 ref JSON
python data_process/generate_ref_json.py

# 步骤2：从模型输出生成标准 hyp JSON
python data_process/generate_hyp_json.py

# 步骤3：文本归一化（标点、大小写等）
python data_process/normalization_single_ref.py
python data_process/normalization_single_hyp.py

# 步骤4：计算 WER/CER
python scripts/compute_wer.py

# 步骤5：生成 Excel 报告
python scripts/excel_single.py
python scripts/merge_excel.py
```

或一键运行完整流程：

```bash
bash example.sh Low-Resource-Languages
```

### ➕ 接入新模型

将模型输出整理为标准 JSON 格式：

```json
[
  {
    "audio_name": "ARE#UCIJXOvggjKtCagMfxvcCzAA#RVSrDuhYDZA#raw",
    "text": "你的转写结果",
    "model": "你的模型名",
    "start": 165.613,
    "end": 169.92
  }
]
```

保存为 `{语言代码}_{模型名}.json` 到 hyp 目录，然后重新运行流程。

---

## 📊 评测

- **WER**（词错误率）：用于字母文字语言（阿拉伯语、印尼语、越南语等）
- **CER**（字错误率）：用于 CJK 语言（日语、韩语、中文）
- 评测前会对每种语言进行相应的文本归一化

---

## 📁 项目结构

```
Multilingual-ASR-Benchmark/
├── data_process/          # 数据预处理脚本
├── text_norm/             # 各语言文本归一化
├── scripts/               # 评测与报告生成
├── third_party/           # 模型接入脚本
│   ├── Azure/
│   ├── Chirp3/
│   ├── gemeni/            # Gemini ASR
│   ├── Qwen3ASR/
│   ├── whisper-large-v3/
│   └── ...
├── build_gradio/          # Gradio 可视化界面
├── example.sh             # 一键运行脚本
└── README.md
```

---

## 🤝 贡献

欢迎贡献新模型的评测结果，请：

1. 在测试集上运行你的 ASR 模型
2. 按标准 JSON 格式输出结果
3. 提交包含 hyp JSON 文件的 Pull Request

---

## 📄 许可

本项目仅供**非商业研究用途**。音频数据来源于公开内容，受原始内容创作者许可协议约束。

---

## 📖 引用

如果您在研究中使用了本基准，请引用：

```bibtex
@misc{multilingual-asr-benchmark,
  title={Multilingual ASR Benchmark: A Large-Scale Evaluation for Low-Resource Languages},
  year={2026},
  url={https://github.com/AlexTYJ/Multilingual-ASR-Benchmark}
}
```
