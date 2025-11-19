apt install aria2 -y
export HF_ENDPOINT=https://hf-mirror.com
mkdir -p whisper_model
wget https://hf-mirror.com/hfd/hfd.sh
chmod a+x hfd.sh
./hfd.sh openai/whisper-large-v3 --local-dir whisper_model