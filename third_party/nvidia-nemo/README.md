📁 项目结构
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
└── __pycache__/
🔧 环境配置
确保已安装Python 3.8+
配置必要的Python包：
<BASH>
pip install nemo_toolkit['asr']==1.23.0
pip install librosa pydub soundfile tqdm

1. 下载预训练模型
<BASH>
python download.py
注：模型将自动下载到~/.cache/huggingface/hub/
2. 运行ASR处理
<BASH>
# 处理日语音频
python jpn_asr.py
# 处理韩语音频
python kor_asr.py 
# 处理阿拉伯语音频
python ar_asr.py

⚙️ 配置文件说明
目录结构配置（硬编码）：
<PYTHON>
CONFIG = {
    "audio_dir": "/root/shared-nvme/haoranwang/nemo_asr/testbatch_processed", # 输入音频
    "label_dir": "/root/shared-nvme/haoranwang/nemo_asr/labeled",             # 标注文件
    "result_dir": "./Nvidia_Nemo_results"                                     # 输出目录
}
