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


