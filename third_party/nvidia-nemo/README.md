## 📂 项目目录结构
nemo_asr/
├── ar_asr.py                 # 阿拉伯语 ASR 推理脚本
├── kor_asr.py                # 韩语 ASR 推理脚本
├── jpn_asr.py                # 日语 ASR 推理脚本
├── download.py               # 预训练模型下载脚本
├── upload_data.py            # 数据上传脚本
├── utils.py                  # 通用工具函数
│
├── Nvidia_Nemo_results/      # ASR 识别结果输出目录
├── labeled/                  # 人工标注文件（与音频目录结构保持一致）
│
└── *.nemo                    # 各语言本地模型权重（可选）


## 🛠️ 环境配置

### 系统要求
- Python 3.8或更高版本
- Linux系统 (推荐Ubuntu 18.04+)
### 依赖安装
```bash
pip install nemo_toolkit['asr']==1.23.0
pip install librosa pydub soundfile tqdm

⚡ 快速开始
1、下载预训练模型
<BASH>
python download.py
注：模型将自动下载至 ~/.cache/huggingface/hub/ 目录和项目指定目录

2、运行语音识别脚本
语言	执行命令
日语	python jpn_asr.py
韩语	python kor_asr.py
阿拉伯语	python ar_asr.py

⚙️ 配置文件
<PYTHON>
CONFIG = {
    # 音频输入目录（按语言分类存储）
    "audio_dir": "/root/shared-nvme/haoranwang/nemo_asr/testbatch_processed",
    # 标签文件目录（需与音频目录保持相同结构）
    "label_dir": "/root/shared-nvme/haoranwang/nemo_asr/labeled",
    # 识别结果输出路径
    "result_dir": "./Nvidia_Nemo_results"
}

