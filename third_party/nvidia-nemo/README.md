<MARKDOWN>
# 📁 Nemo多语言ASR处理系统

## 目录结构
nemo_asr/
├── ar_asr.py             # 阿拉伯语ASR处理脚本
├── kor_asr.py            # 韩语ASR处理脚本
├── jpn_asr.py            # 日语ASR处理脚本
├── download.py           # 模型下载脚本
├── upload_data.py        # 数据上传脚本
├── utils.py              # 通用工具函数
│
├── Nvidia_Nemo_results/  # ASR结果输出目录
├── labeled/              # 标注数据存放目录
│
├── *.nemo                # 各语言ASR模型文件
└── pycache/


## 🛠️ 环境配置

### 系统要求
- Python 3.8+
- Linux系统 (推荐Ubuntu 18.04+)

### 安装依赖
```bash
pip install nemo_toolkit['asr']==1.23.0
pip install librosa pydub soundfile tqdm
🚀 快速开始
1. 下载预训练模型
<BASH>
python download.py
📍 模型会自动下载到 ~/.cache/huggingface/hub/ 目录下

2. 运行ASR处理脚本
语言	运行命令
日语	python jpn_asr.py
韩语	python kor_asr.py
阿拉伯语	python ar_asr.py
⚙️ 系统配置
配置文件通过代码硬编码设置：

<PYTHON>
CONFIG = {
    # 输入音频目录（按语言分文件夹存放）
    "audio_dir": "/root/shared-nvme/haoranwang/nemo_asr/testbatch_processed",
    
    # 标注文件目录（结构需与音频目录一致）
    "label_dir": "/root/shared-nvme/haoranwang/nemo_asr/labeled",
    
    # ASR结果输出目录
    "result_dir": "./Nvidia_Nemo_results"
}
