Gemini-ASR 音频转录工具

# 一、Introduction
This tool is based on Google Gemini，for batch transcription of multilingual long audio。Auto-segments audio based on reference timestamps，Uses multi-threaded parallel processing，Outputs structured results matching reference format，Suitable for ASR model testing, audio subtitling, multilingual speech data processing。

# 二、核心功能
批量处理：递归遍历指定目录下所有 WAV 音频，自动匹配对应参考分段文件
精准切割：依据参考文件时间戳切割长音频为短片段，优化转录准确率
并行高效：多ThreadConcurrency调用 Gemini API，充分利用算力提升处理速度
格式兼容：输出结果与参考文件结构完全一致，便于后续对比分析
异常耐受：自动跳过无效分段、清理临时文件，转录失败保留详细日志
灵活配置：支持自定义目录、Concurrency数、模型版本等核心参数

# 三、环境准备
1. 依赖安装
执行以下命令安装 Python 依赖包：
pip install google-genai tqdm pydub ffmpeg-python


# 四、Parameter config
修改代码中 Parameter config 模块的字段，适配实际使用场景：
参数名	说明	默认值
API_KEY	Google Gemini API Key（必填，需自行申请）	REDACTED_GEMINI_KEY（占位符）
ROOT_DIR	待转录音频根目录（WAV 格式，支持子目录递归查找）	E:\workspace\SH-ASR\testbatch_processed
TESTMARK_DIR	参考分段文件根目录（JSON 格式，目录结构需与音频目录一致）	E:\workspace\SH-ASR\testmark
OUTPUT_DIR	转录结果输出根目录（自动按语言分类创建子目录）	E:\workspace\SH-ASR\results
MODEL_NAME	Gemini 模型名称（推荐使用稳定版）	gemini-2.0-flash（快速版，平衡速度与准确率）
TEMP_DIR	临时音频片段存储目录（自动创建，任务完成后清理）	E:\workspace\SH-ASR\temp_segments
MAX_WORKERS	最大ConcurrencyThread数（需适配 Gemini API Concurrency限制，建议 5-10）	16

# 五、使用步骤
完成环境准备（Install dependencies、配置 API Key）
按要求组织音频文件和参考文件的目录结构
修改代码中的Parameter config（重点确认目录路径和 API Key）
运行脚本
查看结果：转录完成后，在 OUTPUT_DIR 中按语言分类获取结果文件

# 六、输出结果说明
输出 JSON 文件与参考文件格式完全一致，仅更新 segments 中的 text 字段为 Gemini 转录结果：
json
{
  "audio_name": "EGY_UC123",  // 音频文件名（无后缀）
  "segments": [
    {
      "start": 0.5,
      "end": 3.2,
      "status": "valid",
      "text": "السلام عليكم ورحمة الله وبركاته"  // 转录结果
    },
    {
      "start": 3.5,
      "end": 6.8,
      "status": "valid",
      "text": "كيف حالكم اليوم؟"
    }
  ]
}
