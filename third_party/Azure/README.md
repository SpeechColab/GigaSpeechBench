```shell
#!/bin/bash

# ==========================================
# Azure ASR Evaluation Script Configuration
# ==========================================

# 1. Set your Azure API Key
# Strongly recommend exporting via env var, not hardcoding in script
export SPEECH_KEY="your_azure_speech_key_here"

# 假设你的 Python 脚本命名为 evaluate_asr.py
SCRIPT_NAME="Azure.py"

echo "开始运行 ASR 评估脚本..."

# ==========================================
# 运行方式 A：使用代码中的默认路径
# 只需要传入 base_dir，其他子目录会自动拼接
# ==========================================
# python $SCRIPT_NAME \
#     --base_dir "/workdir/Multilingual-ASR-Benchmark/CH-EN-Dialects" \
#     --model_name "azure" \
#     --speech_region "eastasia"


# ==========================================
# 运行方式 B：完全自定义所有路径（推荐，更灵活）
# 如果你的音频和文本存放在不同地方，可以用这种方式
# ==========================================
python $SCRIPT_NAME \
    --base_dir "/workdir/Multilingual-ASR-Benchmark/CH-EN-Dialects" \
    --speech_roots "/workdir/Multilingual-ASR-Benchmark/CH-EN-Dialects/audio/testbatch" \
    --ref_roots "/workdir/Multilingual-ASR-Benchmark/CH-EN-Dialects/text/ref" \
    --submission_root "/workdir/Multilingual-ASR-Benchmark/CH-EN-Dialects/submission_azure" \
    --pre_root "/workdir/Multilingual-ASR-Benchmark/CH-EN-Dialects/submission_azure2" \
    --model_name "azure" \
    --speech_region "eastasia"

echo "运行结束！"
```

### Parameters详细说明（对照上述脚本）：

* **`--base_dir`**:
    * **作用**：设置整个数据集的**根目录**（基础路径）。
    * **说明**：如果你没有指定后面的其他路径参数，脚本会自动基于这个根目录去拼接寻找 `audio/testbatch`、`text/ref` 等文件夹。

* **`--speech_roots`**:
    * **作用**：存放待识别**音频文件**的目录路径。
    * **说明**：可以传入一个或多个路径。脚本会去这些目录下寻找按language（如 `PHL-EN`）分类的文件夹，并读取里面的 `.wav` 或 `.mp3` 音频文件。

* **`--ref_roots`**:
    * **作用**：存放**参考文本（Ground Truth）**和时间戳配置的 JSON 文件的目录路径。
    * **说明**：脚本会读取这里的 JSON 文件，获取需要截取的音频片段的 `start` 和 `end` 时间，以及used for对比的标准答案（ref text）。

* **`--submission_root`**:
    * **作用**：当前脚本**输出识别结果**的目标文件夹。
    * **说明**：脚本运行结束后，会将 Azure 返回的识别结果按language保存为 JSON 文件并放到这个目录下。如果该目录不存在，代码会自动创建它。

* **`--pre_root`**:
    * **作用**：存放**历史缓存结果**的文件夹（类似断点续传的机制）。
    * **说明**：为了节省 API 调用费和时间，脚本在请求 Azure 前会先来这里找找。如果某段音频在历史 JSON 文件中已经有识别结果了，就直接读取，跳过调用。如果不需要缓存机制，可以随便填一个不存在的空目录。

* **`--model_name`**:
    * **作用**：标记当前使用的**模型名称**。
    * **说明**：这个字符串仅仅是写在最终输出的 JSON 结果里面的一个字段（比如 `"model": "azure"`），方便你后续在做数据分析和对比时，知道这个结果是哪个模型跑出来的。

* **`--speech_region`**:
    * **作用**：你的 Azure Speech 资源所在的**数据中心区域**。
    * **说明**：比如 `"eastasia"`（东亚）、`"westus"`（美国西部）。这必须与你在 Azure 门户上创建该服务时选择的区域完全一致，否则 API 会报错连不上。