import nemo.collections.asr as nemo_asr

# 加载模型（阿拉伯语）
model = nemo_asr.models.ASRModel.from_pretrained("nvidia/stt_ar_fastconformer_hybrid_large_pcd_v1.0")
custom_dir = "/root/shared-nvme/haoranwang/nemo_asr" # 自定义保存路径
model.save_to(f"{custom_dir}/stt_ar_fastconformer_hybrid_large_pcd_v1.0.nemo")

# 加载模型（韩语）
model = nemo_asr.models.ASRModel.from_pretrained("eesungkim/stt_kr_conformer_transducer_large")
custom_dir = "/root/shared-nvme/haoranwang/nemo_asr" # 自定义保存路径
model.save_to(f"{custom_dir}/stt_kr_conformer_transducer_large")

# 加载模型（日语）
model = nemo_asr.models.ASRModel.from_pretrained("nvidia/parakeet-tdt_ctc-0.6b-ja")
custom_dir = "/root/shared-nvme/haoranwang/nemo_asr" # 自定义保存路径
model.save_to(f"{custom_dir}/parakeet-tdt_ctc-0.6b-ja")
