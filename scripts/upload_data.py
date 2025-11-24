from huggingface_hub import HfApi

HF_TOKEN = "REDACTED_HF_TOKEN"

api = HfApi(token=HF_TOKEN)

LOCAL_FOLDER = "/root/shared-nvme/yujietu/data/ASR-Bench/Multilingual-ASR-Benchmark/wenetspeech/audio/wenetspeech_tar" 

api.upload_folder(
    folder_path=LOCAL_FOLDER,
    repo_id="AlexTYJ/Multilingual-ASR-Benchmark",
    repo_type="dataset",
    path_in_repo="wenetspeech/audio/wenetspeech_tar", #这里自己改下push到repo的路径
)

print("Upload Done!")
