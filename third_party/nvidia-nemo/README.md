## 📁 项目结构

```
nemo_asr/
├── ar_asr.py             # 阿拉伯语ASR处理脚本
├── kor_asr.py            # 韩语ASR处理脚本
├── jpn_asr.py            # 日语ASR处理脚本
├── download.py           # 模型下载脚本
├── upload_data.py        # 数据上传脚本
├── utils.py              # 工具函数模块
│
├── Nvidia_Nemo_results/  # 识别结果输出目录
├── labeled/              # 已标注数据目录
│
├── *.nemo                # ASR模型文件
└── pycache/          # Python编译缓
```

## 🚀 快速开始

### 1. 环境初始化
`说明，遇到网络问题，推荐对  apt、uv、pip、hf 等进行换源，推荐工具 chsrc 和 镜像网站hf-mirror，本代码中 hf 下载已经换源`



#### 安装uv（如果尚未安装）


#### 创建并激活虚拟环境
```bash
# 进入项目目录
cd /path/to/Multilingual-ASR-Benchmark/examples/whisper-large-v3

# 安装项目依赖
uv sync
```

### 2. 安装系统依赖

#### 系统工具
- `ffmpeg`（音频处理），使用`install_ffmpeg.sh`
- `aria2c`（模型下载，可选）,`install_model.sh`会自动下载 aria2c

### 3. 下载Whisper模型

#### 使用自动化脚本下载（推荐）
```bash
bash install_model.sh
```
