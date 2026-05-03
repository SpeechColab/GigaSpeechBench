import nemo.collections.asr as nemo_asr

# Load model (Arabic)
model = nemo_asr.models.ASRModel.from_pretrained("nvidia/stt_ar_fastconformer_hybrid_large_pcd_v1.0")
custom_dir = "/root/shared-nvme/haoranwang/nemo_asr" # Custom save path
model.save_to(f"{custom_dir}/stt_ar_fastconformer_hybrid_large_pcd_v1.0.nemo")

# Load model (Korean)
model = nemo_asr.models.ASRModel.from_pretrained("eesungkim/stt_kr_conformer_transducer_large")
custom_dir = "/root/shared-nvme/haoranwang/nemo_asr" # Custom save path
model.save_to(f"{custom_dir}/stt_kr_conformer_transducer_large")

# Load模型（日语）
model = nemo_asr.models.ASRModel.from_pretrained("nvidia/parakeet-tdt_ctc-0.6b-ja")
custom_dir = "/root/shared-nvme/haoranwang/nemo_asr" # Custom save path
model.save_to(f"{custom_dir}/parakeet-tdt_ctc-0.6b-ja")

# Load模型（中文）
model = nemo_asr.models.ASRModel.from_pretrained("nvidia/stt_zh_conformer_transducer_large")
custom_dir = "/root/shared-nvme/haoranwang/nemo_asr" # Custom save path
model.save_to(f"{custom_dir}/stt_zh_conformer_transducer_large")

# Load模型（英语）
model = nemo_asr.models.ASRModel.from_pretrained("nvidia/stt_en_conformer_transducer_large")
custom_dir = "/root/shared-nvme/haoranwang/nemo_asr" # Custom save path
model.save_to(f"{custom_dir}/stt_en_conformer_transducer_large")
