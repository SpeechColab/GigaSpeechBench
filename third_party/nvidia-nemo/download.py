import nemo.collections.asr as nemo_asr

# 1. 加载模型（默认会缓存到 ~/.cache/torch/NeMo）
model = nemo_asr.models.ASRModel.from_pretrained("nvidia/stt_en_conformer_transducer_large")

# 2. 自定义保存路径
custom_dir = "/root/shared-nvme/haoranwang/nemo_asr"

# 3. 保存模型到指定目录（生成 .nemo 文件）
model.save_to(f"{custom_dir}/stt_en_conformer_transducer_large.nemo")