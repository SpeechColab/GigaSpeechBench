# Multilingual-ASR-Benchmark

ASR 最终最外层函数接口说明：输入一条音频路径，返回转录文本。即：

- 输入：`audio_path` (`str`) —— 音频文件绝对路径  
- 输出：`text` (`str`) —— 识别出的转录文本  

**结果保存：**  
可使用 `utils.py` 中的 `save_transcription()` 函数测试保存结果，需传入六个参数：
1. 音频绝对路径  
2. 开始时间
3. 结束时间
4. 转录文本  
5. 模型名称（如 `"elevenlabs"`）  
6. 语种（三字母国家代码，如 `"IRQ"`）

会自动在results文件夹中写入json文件