from huggingface_hub import HfApi

HF_TOKEN = "REDACTED_HF_TOKEN"

api = HfApi(token=HF_TOKEN)

LOCAL_FOLDER = "/root/shared-nvme/yujietu/data/ASR-Bench/testbatch"

api.upload_folder(
    folder_path=LOCAL_FOLDER,
    repo_id="AlexTYJ/Multilingual-ASR-Benchmark",
    repo_type="dataset",
    path_in_repo="testbatch",
)

print("Upload Done!")
