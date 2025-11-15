from huggingface_hub import HfApi
HF_TOKEN = "Yhf_HzUNaPJnDUkupPTuxrtFSxvqiaGCpLHruS"
api = HfApi(token=HF_TOKEN)
api.upload_folder(
    folder_path="/path/to/local/dataset",
    repo_id="AlexTYJ/Multilingual-ASR-Benchmark",
    repo_type="dataset",
)
print("Done！")
