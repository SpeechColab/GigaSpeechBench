from huggingface_hub import HfApi

HF_TOKEN = "REDACTED_HF_TOKEN"

api = HfApi(token=HF_TOKEN)

# 注意这里最好是保持结构一致，即文件放在text/hyp/testbatch下，上传test文件夹

LOCAL_FOLDER = "E:/Desktop/master/master_3/benchmark/result_revision" 

api.upload_folder(
    folder_path=LOCAL_FOLDER,
    repo_id="AlexTYJ/Multilingual-ASR-Benchmark",
    repo_type="dataset",
    path_in_repo="wenetspeech/audio/wenetspeech_tar", #这里自己改下push到repo的路径
)

print("Upload Done!")
