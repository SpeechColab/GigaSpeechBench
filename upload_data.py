from huggingface_hub import HfApi

HF_TOKEN = "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"

api = HfApi(token=HF_TOKEN)

# 注意这里最好是保持结构一致，即文件放在text/hyp/testbatch下，上传test文件夹

LOCAL_FOLDER = "E:/Desktop/master/master_3/benchmark/result_revision" 

api.upload_folder(
    folder_path=LOCAL_FOLDER,
    repo_id="AlexTYJ/Multilingual-ASR-Benchmark",
    repo_type="dataset",
    path_in_repo="text/hyp/testbatch",
)

print("Upload Done!")
