## 📁 项目结构

```
nemo_asr/
├── ar_asr.py             # 阿拉伯语ASR处理脚本
├── kor_asr.py            # 韩语ASR处理脚本
├── jpn_asr.py            # 日语ASR处理脚本
├── download.py           # 模型下载脚本
├── upload_data.py        
├── utils.py              
│
├── Nvidia_Nemo_results/  # 识别结果输出目录
├── labeled/              # 已标注数据目录
│
├── *.nemo                # ASR模型文件
└── pycache/              # Python编译缓
```

## 🚀 快速开始

## 🛠️ 环境配置

### 系统要求
- Python 3.8或更高版本
- Linux系统 (推荐Ubuntu 18.04+)

### 依赖安装
```bash
pip install nemo_toolkit['asr']==1.23.0
pip install librosa pydub soundfile tqdm
```
### 下载预训练模型
```bash
python download.py
```
注：模型将自动下载至 ~/.cache/huggingface/hub/ 目录和指定目录

## ⚡运行语音识别脚本	

### 日语
```bash
python jpn_asr.py
```
### 韩语
```bash
python kor_asr.py
```
### 阿拉伯语
```bash
python ar_asr.py
```

### 配置文件

<PYTHON>
CONFIG = {
    # 音频输入目录（按语言分类存储）
    "audio_dir": "/root/shared-nvme/haoranwang/nemo_asr/testbatch_processed",
    
    # 标签文件目录（需与音频目录保持相同结构）
    "label_dir": "/root/shared-nvme/haoranwang/nemo_asr/labeled",
    
    # 识别结果输出路径
    "result_dir": "./Nvidia_Nemo_results"
}



