from huggingface_hub import HfApi

HF_TOKEN = "REDACTED_HF_TOKEN"

api = HfApi(token=HF_TOKEN)

# 注意这里最好是保持结构一致，即文件放在text/hyp/testbatch下，上传text文件夹

LOCAL_FOLDER = "/root/shared-nvme/yujietu/data/ASR-Bench/text" 

api.upload_folder(
    folder_path=LOCAL_FOLDER,
    repo_id="AlexTYJ/Multilingual-ASR-Benchmark",
    repo_type="dataset",
    path_in_repo="text",
)

print("Upload Done!")
