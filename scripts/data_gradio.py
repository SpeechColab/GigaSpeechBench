import os
import json
import random
import glob
import subprocess
import gradio as gr

# ==========================================
# 1. 基础配置
# ==========================================
BASE_DIR = "/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/data/ASRBench_gradio"
DEFAULT_DATASET = "CH-EN-Dialects"
REF_MODE_TEXT = "🔍 [Ref 模式] 仅查看数据集本身"

# 临时切片存放目录
TEMP_DIR = "/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/temp"
os.makedirs(TEMP_DIR, exist_ok=True)

# ==========================================
# 2. 辅助函数 (动态读取目录)
# ==========================================
def get_datasets():
    """获取所有数据集"""
    if not os.path.exists(BASE_DIR):
        return [DEFAULT_DATASET]
    return sorted([d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))])

def get_countries(dataset):
    """获取指定数据集下的所有国家"""
    ref_dir = os.path.join(BASE_DIR, dataset, "text", "ref")
    if not os.path.exists(ref_dir):
        return []
    return sorted([d for d in os.listdir(ref_dir) if os.path.isdir(os.path.join(ref_dir, d))])

def get_batches(dataset, country):
    """获取指定国家下的所有 Batch 文件夹"""
    if not dataset or not country:
        return []
    country_dir = os.path.join(BASE_DIR, dataset, "text", "ref", country)
    if not os.path.exists(country_dir):
        return []
    return sorted([d for d in os.listdir(country_dir) if os.path.isdir(os.path.join(country_dir, d))])

def get_models(dataset, country, batch):
    """获取指定国家和 Batch 下的所有模型"""
    if not dataset or not country or not batch:
        return [REF_MODE_TEXT]
        
    hyp_dir = os.path.join(BASE_DIR, dataset, "text", "hyp", country, batch)
    models = [REF_MODE_TEXT]
    if os.path.exists(hyp_dir):
        for f in sorted(os.listdir(hyp_dir)):
            if f.endswith(".json"):
                models.append(f[:-5]) # 去掉 .json 后缀
    return models

# ==========================================
# 3. 音频与信息处理核心
# ==========================================
def clear_temp_cache():
    """清除临时目录中的音频切片"""
    count = 0
    if os.path.exists(TEMP_DIR):
        for f in os.listdir(TEMP_DIR):
            file_path = os.path.join(TEMP_DIR, f)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    count += 1
                except Exception as e:
                    print(f"删除失败: {file_path} -> {e}")
    gr.Info(f"✅ 成功清除 {count} 个缓存音频文件！")

def find_audio_path(dataset, country, audio_name):
    """递归遍历搜索音频原文件"""
    audio_dir = os.path.join(BASE_DIR, dataset, "audio", country)
    if not os.path.exists(audio_dir):
        return None
        
    safe_name = glob.escape(audio_name)
    search_pattern = os.path.join(audio_dir, "**", f"{safe_name}.*")
    
    matches = glob.glob(search_pattern, recursive=True)
    for m in matches:
        if os.path.isfile(m):
            return m
    return None

def crop_audio(input_path, audio_name, start, end):
    """FFmpeg 快速切音"""
    ext = os.path.splitext(input_path)[1] or ".wav"
    safe_name = audio_name.replace("/", "_").replace("#", "_")
    output_filename = f"{safe_name}_{start}_{end}{ext}"
    output_path = os.path.join(TEMP_DIR, output_filename)
    
    if os.path.exists(output_path):
        return output_path
        
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-ss", str(start),
        "-to", str(end),
        "-c", "copy", 
        output_path
    ]
    
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg 切割失败: {input_path} -> {e}")
        return None

def get_overall_metric(dataset, country, batch, model):
    """获取模型级别的全局 WER/CER 分数"""
    if model == REF_MODE_TEXT or not model:
        return "### 💡 **当前为参考文本 (Ref) 模式，仅浏览数据集本身，无评测指标。**"
        
    report_dir = os.path.join(BASE_DIR, dataset, "text", "reports", country, batch, model)
    if not os.path.exists(report_dir):
        return f"### ⚠️ **未找到模型 {model} 的评测报告目录 (请检查 reports 目录是否生成)**"
        
    summary_files = glob.glob(os.path.join(report_dir, "*summary*.txt"))
    if summary_files:
        try:
            with open(summary_files[0], "r", encoding="utf8") as f:
                lines = f.readlines()
                if len(lines) >= 2:
                    val = lines[1].strip().split("\t")[-1]
                    metric_name = "CER" if "cer" in summary_files[0].lower() else "WER"
                    return f"### 🏆 **全局评测结果:** 模型 `{model}` 在当前测试集的总 **{metric_name}** 为 <span style='color:red; font-size:1.2em;'>**{val}%**</span>"
        except Exception as e:
            return f"### ⚠️ **读取报告失败**: {e}"
            
    return f"### ⚠️ **找不到 summary 报告文件**: {report_dir}"

def format_info(item, is_hyp_mode):
    """格式化右侧单条样本的信息面板"""
    md = f"### 🎵 Audio Name: `{item.get('audio_name', 'Unknown')}`\n"
    md += f"**⏱️ Time:** {item.get('start', 0.0)}s - {item.get('end', 0.0)}s\n\n"
    
    if is_hyp_mode:
        metric_val = item.get('wer') if 'wer' in item is not None else item.get('cer')
        if metric_val is None: metric_val = "N/A"
        metric_name = "WER" if 'wer' in item else "CER"
        
        md += f"**🤖 Model:** `{item.get('model', 'Unknown')}` | <span style='background-color:#ffe4e1; padding:2px 6px; border-radius:4px;'>**📍 本句 {metric_name}:** `{metric_val}`</span>\n"
        md += f"**📉 本句错误详情:** Insertions: `{item.get('insertions')}` | Deletions: `{item.get('deletions')}` | Substitutions: `{item.get('substitutions')}`\n\n"
        
        md += f"**[REF] 原始参考文本:**\n> {item.get('ref_text', 'N/A')}\n\n"
        md += f"**[REF] 归一化参考文本:**\n> {item.get('ref_text_normalized', 'N/A')}\n\n"
        md += f"**[HYP] 模型识别原文:**\n> {item.get('text', 'N/A')}\n\n"
        md += f"**[HYP] 模型归一化文本:**\n> {item.get('text_normalized', 'N/A')}\n"
    else:
        md += f"**[REF] 原始文本:**\n> {item.get('text', 'N/A')}\n\n"
        md += f"**[REF] 归一化文本:**\n> {item.get('text_normalized', 'N/A')}\n\n"
        md += f"**👤 Meta信息:** \n"
        md += f"- Age Group: {item.get('age_group', 'N/A')}\n"
        md += f"- Gender: {item.get('gender', 'N/A')}\n"
        md += f"- Emotion: {item.get('emotion', 'N/A')}\n"
        md += f"- Speaker: {item.get('speaker', 'N/A')}\n"
        
    return md

# ==========================================
# 4. 抽取逻辑
# ==========================================
def fetch_samples(dataset, country, batch, model):
    if not country or not batch:
        return ["请确保国家和 Batch 已选择！"] + [None, ""] * 5
        
    is_hyp_mode = model != REF_MODE_TEXT
    global_metric_text = get_overall_metric(dataset, country, batch, model)
    
    if is_hyp_mode:
        data_path = os.path.join(BASE_DIR, dataset, "text", "hyp", country, batch, f"{model}.json")
    else:
        data_path = os.path.join(BASE_DIR, dataset, "text", "ref", country, batch, f"{country}.json")
        
    if not os.path.exists(data_path):
        return [global_metric_text + f"\n\n❌ 找不到数据文件: {data_path}"] + [None, ""] * 5
        
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return [global_metric_text + f"\n\n❌ 读取 JSON 失败: {str(e)}"] + [None, ""] * 5
        
    if not data:
        return [global_metric_text + "\n\n⚠️ JSON 文件为空"] + [None, ""] * 5

    sample_size = min(5, len(data))
    samples = random.sample(data, sample_size)
    
    outputs = [global_metric_text]
    for item in samples:
        audio_name = item.get("audio_name", "")
        start = float(item.get("start", 0.0))
        end = float(item.get("end", 0.0))
        
        orig_audio_path = find_audio_path(dataset, country, audio_name)
        info_md = format_info(item, is_hyp_mode)
        final_audio = None
        
        if orig_audio_path:
            final_audio = crop_audio(orig_audio_path, audio_name, start, end)
            if not final_audio:
                info_md = f"⚠️ **注意: FFmpeg 切割音频失败！**\n\n" + info_md
        else:
            info_md = f"⚠️ **注意: 遍历 audio 目录未找到原始音频文件！({audio_name})**\n\n" + info_md
            
        outputs.append(final_audio)
        outputs.append(info_md)
        
    while len(outputs) < 11:
        outputs.append(None)
        outputs.append("（无数据）")
        
    return tuple(outputs)

# ==========================================
# 5. Gradio 界面与联动构建
# ==========================================
with gr.Blocks(title="ASR-Bench 评测数据查看器", theme=gr.themes.Soft()) as app:
    gr.Markdown("# 🎧 ASR-Bench 评测结果可视化查看器")
    
    with gr.Row():
        with gr.Column(scale=1):
            dataset_dd = gr.Dropdown(label="1. 选择 Dataset", choices=get_datasets(), value=DEFAULT_DATASET, interactive=True)
            country_dd = gr.Dropdown(label="2. 选择 Country", choices=[], interactive=True)
        with gr.Column(scale=1):
            batch_dd = gr.Dropdown(label="3. 选择 Batch", choices=[], interactive=True)
            model_dd = gr.Dropdown(label="4. 选择 Model", choices=[REF_MODE_TEXT], value=REF_MODE_TEXT, interactive=True)
        with gr.Column(scale=1, min_width=200):
            refresh_btn = gr.Button("🎲 随机抽取 5 条", variant="primary")
            clear_cache_btn = gr.Button("🧹 清除音频缓存", variant="secondary")

    gr.Markdown("---")
    
    global_info = gr.Markdown(value="请选择配置并点击抽取...")
    gr.Markdown("---")
    
    display_components = []
    for i in range(5):
        with gr.Row():
            with gr.Column(scale=1):
                audio_comp = gr.Audio(label=f"Sample {i+1} Audio", type="filepath", interactive=False)
            with gr.Column(scale=2):
                info_comp = gr.Markdown(value="等待抽取数据...")
        display_components.extend([audio_comp, info_comp])
        if i < 4:
            gr.Markdown("<hr>")
            
    # ====== 级联更新逻辑 ======
    def update_countries(ds):
        c = get_countries(ds)
        val = c[0] if c else None
        return gr.update(choices=c, value=val)

    def update_batches(ds, c):
        b = get_batches(ds, c)
        val = b[0] if b else None
        return gr.update(choices=b, value=val)

    def update_models(ds, c, b):
        m = get_models(ds, c, b)
        return gr.update(choices=m, value=REF_MODE_TEXT)

    # 绑定级联 (链式反应)
    dataset_dd.change(fn=update_countries, inputs=[dataset_dd], outputs=[country_dd])
    country_dd.change(fn=update_batches, inputs=[dataset_dd, country_dd], outputs=[batch_dd])
    batch_dd.change(fn=update_models, inputs=[dataset_dd, country_dd, batch_dd], outputs=[model_dd])

    # 绑定核心功能
    refresh_btn.click(
        fn=fetch_samples,
        inputs=[dataset_dd, country_dd, batch_dd, model_dd],
        outputs=[global_info] + display_components
    )
    clear_cache_btn.click(fn=clear_temp_cache, inputs=[], outputs=[])
    
    # 启动时初始化触发一次
    app.load(fn=update_countries, inputs=[dataset_dd], outputs=[country_dd])

# ==========================================
# 6. 启动配置
# ==========================================
if __name__ == "__main__":
    app.launch(
        server_name="0.0.0.0", 
        server_port=7860, 
        share=True,
        allowed_paths=[TEMP_DIR, BASE_DIR] 
    )