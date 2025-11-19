# Omnilingual-ASR API

## Installation

请参考原repo:  
https://github.com/facebookresearch/omnilingual-asr
https://github.com/facebookresearch/fairseq2

omnilingual-asr 基于 fairseq2 构筑，fairseq 又需要 libsndfile:
```bash
sudo apt install libsndfile1

# Or download with conda:
conda install libsndfile # 需要配置一下 conda 源
```

然后选择与 pytorch 对应的 fairseq2 版本进行下载：
```bash
pip install fairseq2
pip install omnilingual-asr 
```

## Inference

### Models
https://github.com/facebookresearch/omnilingual-asr/blob/main/src/omnilingual_asr/models/inference/README.md

简要来说，omniasr 模型分为 CTC / LLM 两种类型。CTC 模型解码快，但不能接受 language id 控制，解码会出现非目标语种出现。LLM 模型外接了一层 Llama decoder，解码慢，但可用 lang id 作为限制条件进行解码。

目前可用的模型种类详见 `omniasr.py` 中的 `transcribe_audio` 函数：
```python
"omniASR_CTC_300M",         # wav2vec encoder + linear projection
"omniASR_CTC_1B",           # cannot apply language code
"omniASR_CTC_3B",           # however decoding very fast
"omniASR_CTC_7B",
"omniASR_LLM_300M",         # wav2vec encoder + llama decoder
"omniASR_LLM_1B",           # LLM ASR can apply language code
"omniASR_LLM_3B",           # but decoding speed is quite slow
"omniASR_LLM_7B",           # RTF ~ 0.5
"omniASR_LLM_7B_ZS",        # zero-shot ASR
```

### lang id

使用 LLM 模型解码时，可提供语种代号辅助解码，详细描述在其文章中的 appendix A 部分：https://ai.meta.com/research/publications/omnilingual-asr-open-source-multilingual-speech-recognition-for-1600-languages/

模型提供的可用 lang id 比较复杂，目前筛选了一部分仅供参考，请在`omniasr.py` 的 `get_omniasr_lang` 函数中了解详细内容，并做出对应的改变


## Usage

### Transcribe an audio & Download model
首先，请通过解码一个音频文件来下载模型：
```bash
# make sure you are at Multilingual-ASR-Benchmark home dir

python models/omnilingual-asr/omniasr.py [--audio /some/audio/path] [--start start_timestamp] [--end end_timestamp]  --model omniASR_CTC_3B --language DZA
```

- 输入：
    - `audio` (`str`) —— 音频文件绝对路径 
    - `start` (`float`) —— 音频文件开始时间戳
    - `end` (`float`) —— 音频文件结束时间戳
    - `model` (`str`) —— ASR 模型 card
    - `language` (`str`) —— 语种的缩写代号
 
- 输出：`text` (`str`) —— 打印出识别的转录文本

同时，模型会被保存在: `~/.cache/fairseq2/assets` 路径下，如果想自己指定路径：
```bash 
export FAIRSEQ2_CACHE_DIR=/your/path
```
或者你自己手动下载了模型（在git repo上）, checkout: https://github.com/facebookresearch/omnilingual-asr/issues/10#issuecomment-3527795460


### batch process audio files:
我们提供了一个 API 接口，用于批量处理大量音频标注，请使用 `--input` flag标识输入文件（与`--audio`互斥），函数期望的输入文件应包含如下信息：
```bash
data/DZA/DZA_UC57OCoLoU6zAtBdJOmwg2vA_gBvqK28oBgo_raw.wav 280 300
data/DZA/DZA_UC57OCoLoU6zAtBdJOmwg2vA_T7cGFKzKKaQ_raw.wav 150 180
test_audio/5OqVv6Tdwrs-0.wav
test_audio/-01EmTpJDj0-0.wav
```

即：要么一行为音频文件的绝对路径，要么包含音频文件的起止时间戳。另外由于模型是在小于 30s 的片段下训练的，因此请保证音频不超过 40s。

```bash
# make sure you are at Multilingual-ASR-Benchmark home dir

python models/omnilingual-asr/omniasr.py [--input /input/metainfo/path] --model omniASR_LLM_3B --language DZA
```

- 输入：
    - `input` (`str`) —— 输入文件的路径
    - `model` (`str`) —— ASR 模型 card (CTC解码快，LLM很慢，建议换着试试)
    - `language` (`str`) —— 语种的缩写代号（请不要把不同语种的音频放在一起解码）
 
- 输出：`text` (`str`) —— 使用 `utils.py` 中的 `save_transcription()` 函数，结果以 json 格式保存在 `results/` 下
