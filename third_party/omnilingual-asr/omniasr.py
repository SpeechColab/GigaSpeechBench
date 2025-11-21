from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline
from omnilingual_asr.models.wav2vec2_llama.lang_ids import supported_langs

from pathlib import Path
from tqdm import tqdm
from collections import defaultdict
from utils import save_transcription

import torchaudio
import os, sys
import argparse
import warnings
warnings.filterwarnings("ignore", category=UserWarning)


def get_parser():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--audio", 
        type=str, 
        default=None,
        help="absolute path to audio file"
    )
    parser.add_argument(
        "--start", 
        type=float, 
        default=None,
        help="if audio is specified, this will be the starting timestamp (seconds) of the audio"
    )
    parser.add_argument(
        "--end", 
        type=float, 
        default=None,
        help="if audio is specified, this will be the ending timestamp (seconds) of the audio"
    )
    parser.add_argument(
        "--input", 
        type=str, 
        default=None,
        help="a meta-info file, listing all the audios and starting, ending points. \
            its format be like: path\tstart\tend\n"
    )
    parser.add_argument(
        "--output", 
        type=str, 
        default=None,
        help="The transcribed results will be saved at this path."
    )
    parser.add_argument(
        "--model", 
        type=str, 
        default='omniASR_CTC_3B',
        help="used for choosing the ASR model"
    )
    parser.add_argument(
        "--language", 
        type=str, 
        default='DZA',
        help="language code"
    )

    return parser


def get_omniasr_lang(language: str):
    """
    transform language code to omniasr lang id
    仅在使用 LLM 系列解码时，需要提供 lang id，CTC系列不支持
    """
    language = language.upper()

    if language == 'DZA':
        return 'arq_Arab'       # Algerian Arabic

    elif language == 'MAR':     
        return 'ary_Arab'       # Moroccan Arabic

    elif language == 'ARE':  
        return 'afb_Arab'       # Gulf Arabic (Qatar / UAE)
        
    elif language == 'EGY':     
        return 'arz_Arab'       # Egyptian Arabic
        # return 'aec_Arab'       # Saidi Arabic, spoken along the nile river

    elif language == 'IRQ':
        """
        omnilingual-asr中相关伊拉克的lang有三种，可以都试一下效果：
            美索不达米亚方言（帕尔米拉绿洲和幼发拉底河沿岸的居民点）、
            北美索不达米亚方言、（北部使用）
            内志阿拉伯语（南部使用）
        """
        return 'acm_Arab'       # Mesopotamian Arabic
        # return 'ayp_Arab'       # North Mesopotamian Arabic
        # return 'ars_Arab'       # Najdi Arabic 

    elif language == 'SAU':
        """
        omnilingual-asr中没有专门针对沙特的lang id
        相关的有三种：Najdi、Hijazi（红海沿岸）、Gulf Arabic（东部海湾沿岸）
        """
        return 'ars_Arab'       # Najdi Arabic 
        # return 'acw_Arab'       # Hijazi Arabic
        # return 'afb_Arab'       # Gulf Arabic (Qatar / UAE)

    elif language == 'KOR':
        return 'kor_Hang'       # Korean
    
    elif language == 'JPN':
        return 'jpn_Jpan'       # Japanese

    elif language == 'VNM':
        return 'vie_Latn'       # vietnamese

    elif language == 'PHL':
        return 'tgl_Latn'       # Tagalog

    elif language == 'THA':
        """
        omniasr 中以 thai 结尾的 lang id 有很多，
        这里取 Thai 单独命名的
        """
        return 'tha_Thai'       # Thai

    elif language == 'IND':
        """
        印尼语相当复杂，几个相关的 lang id:
        """
        return 'ind_Latn'       # Indonesian
        # return 'bhz_Latn'       # Bada (Indonesia)
        # return 'twe_Latn'       # Tewa (Indonesia)
        # return 'xmm_Latn'       # Manado Malay 万鸦老马来语
        # return 'abs_Latn'       # Ambonese Malay 安汶语
        # return 'jax_Latn'       # Jambi Malay 占碑马来语
        # return 'max_Latn'       # North Moluccan Malay 
        # return 'mkn_Latn'       # Kupang Malay
        # return 'pmy_Latn'       # Papuan Malay
        # return 'pse_Latn'       # Central Malay, AKA South Barisan Malay  南巴里桑马来
        # return 'xdy_Latn'       # Malayic Dayak 马来语系达雅克语

    elif language == 'MYS':
        """
        马来语也有好几个对应的 lang id，我不太了解，仅列举在下面
        """
        return 'zsm_Latn'       # standard malay
        # return 'msi_Latn'       # Sabah Malay 沙巴

    else:
        raise


def transcribe_audio(
    audio: str = None,
    start: float = None,
    end: float = None,
    model: str = 'omniASR_CTC_300M',
    language: str = 'IRQ',
):
    """
    转录一个音频文件的函数，建议先从该函数开始进行测试，同时下载模型

    Args:
        audio: Audio input path (str)
        start: starting timestamp, in seconds (float)
        end: ending timestamp, in seconds (float)
        model: omnilingual-ASR model choice (str)
        language: language code (str)
    """
    assert audio is not None, "Audio Path must be applied"
    assert model in [
        "omniASR_CTC_300M",         # wav2vec encoder + linear projection
        "omniASR_CTC_1B",           # cannot apply language code
        "omniASR_CTC_3B",           # however decoding very fast
        "omniASR_CTC_7B",
        "omniASR_LLM_300M",         # wav2vec encoder + llama decoder
        "omniASR_LLM_1B",           # LLM ASR can apply language code
        "omniASR_LLM_3B",           # but decoding speed is quite slow
        "omniASR_LLM_7B",           # RTF ~ 0.5
        "omniASR_LLM_7B_ZS",        # zero-shot ASR
    ]
    assert language in [
        "ARE", "DZA", "EGY", "IDN", "IRQ", "JPN", "KOR", "MAR", "MYS", "PHL", "SAU", "THA", "VNM"
    ]

    lang = get_omniasr_lang(language)
    assert lang in supported_langs, f"{language} not supported"
    
    pipeline = ASRInferencePipeline(model_card=model)   # download model and tokenizer
    """
    By default, downloaded models will be saved in ~/.cache/fairseq2/assets
    you can choose another path by setting:

    export FAIRSEQ2_CACHE_DIR=/your/path

    OR you can manually download models from https://github.com/facebookresearch/omnilingual-asr/
    and then checkout this issue to load your local model:
    https://github.com/facebookresearch/omnilingual-asr/issues/10#issuecomment-3527795460
    """

    if start is None or end is None:
        transcriptions = pipeline.transcribe([audio], lang=[lang], batch_size=2)
    else:
        wav, sr = torchaudio.load(audio, channels_first=False)
        # wav = wav.cpu().numpy().astype('uint8')
        arr = wav[int(start*sr):int(end*sr), :]
        
        transcriptions = pipeline.transcribe(
            [{"waveform": arr, "sample_rate": sr}], 
            lang=[lang], 
            batch_size=2
        )
    """
    transcribe: Audio input in different forms.
        - `List[ Path | str ]`: Audio file paths
        - `List[ bytes ]`: Raw audio data
        - `List[ np.ndarray ]`: Audio data as uint8 numpy array
        - `List[ dict[str, Any] ]`: Pre-decoded audio with 'waveform' and 'sample_rate' keys
    """
    print(transcriptions)


def process_audio_files(input_file: str = None):
    """
    处理 metainfo 文件 input_file，汇总成 audio_files：一个包含输入音频信息的 list
    Args:
        input_file: str (line format belike: {wav_path}\t{start}\t{end})
            if no start / end is provided, whole audio will be processed
            Currently only audio files shorter than 40 seconds are accepted for inference.
        
    Return:
        metainfo: a list of segments of audios. [[wav_path, start, end], ...]

        audio_files: a list of Audio input in different forms.
        - `List[ Path | str ]`: Audio file paths
        - `List[ bytes ]`: Raw audio data
        - `List[ np.ndarray ]`: Audio data as uint8 numpy array
        - `List[ dict[str, Any] ]`: Pre-decoded audio with 'waveform' and 'sample_rate' keys
    """

    metainfo = []
    audio_files = []
    meta = defaultdict(list)

    with open(input_file, 'r') as f:
        for line in f:
            if len(line.strip().split()) == 1:
                wav_path = line.strip().split()[0]
                assert os.path.isfile(wav_path), f"{wav_path} not a file"

                info = torchaudio.info(wav_path)
                duration = info.num_frames / info.sample_rate
                if duration > 40.0:
                    print(f'WARNING: {wav_path} is too long: {duration} seconds')

                # audio_files.append(wav_path)
                meta[wav_path].append((0.0, duration))
                metainfo.append([wav_path, 0.0, duration])
            elif len(line.strip().split()) == 3:
                wav_path, start, end = line.strip().split()
                assert os.path.isfile(wav_path), f"{wav_path} not a file"
                meta[wav_path].append((float(start), float(end)))
                metainfo.append([wav_path, start, end])
            else:
                print(line)
                raise

    for wav_path, segments in tqdm(meta.items()):
        wav, sr = torchaudio.load(wav_path, channels_first=False)

        for idx, (start, end) in enumerate(segments):
            if end - start > 40.0:
                print(f'WARNING: {wav_path}_{idx} is too long: {end - start} seconds')

            arr = wav[int(start*sr):int(end*sr), :]
            audio_files.append({"waveform": arr, "sample_rate": sr})

    return metainfo, audio_files


def batch_transcribe_audios(
    input_file: str = None,
    output_file: str = None,
    model: str = 'omniASR_CTC_300M',
    language: str = 'IRQ',
):
    """
    批量转录大量音频，请指定一个包含音频信息的文件
    Args:
        input_file: str (line format belike: {wav_path}\t{start}\t{end})
            if no start / end is provided, whole audio will be processed
            Currently only audio files shorter than 40 seconds are accepted for inference.
        
        output_file: str, where results saved, 
            or maybe save_transcription has hardcoded the output path...

        model: omnilingual-ASR model choice (str)
        language: language code (str)
    """
    assert input_file is not None
    # assert output_file is not None and output_file.endswith('.json'), "please specify json name"

    print('Loading input audio files...')
    metainfo, audio_files = process_audio_files(input_file)
    lang = [get_omniasr_lang(language)] * len(audio_files)

    print('Loading omniasr model:')
    pipeline = ASRInferencePipeline(model_card=model)
    
    print('Transcribing ...')
    transcriptions = pipeline.transcribe(audio_files, lang=lang, batch_size=2)

    for (audio_path, start, end), text in zip(metainfo, transcriptions):
        save_transcription(audio_path, text, language, model, start, end)

    print('DONE')


def main():
    parser = get_parser()
    args = parser.parse_args()

    # test code & download models:
    if args.audio:
        transcribe_audio(args.audio, args.start, args.end, args.model, args.language)

    # After downloading the models, you can batch processing audios:
    if args.input:
        batch_transcribe_audios(
            input_file=args.input, 
            model=args.model, 
            language=args.language,
        )


if __name__ == "__main__":
    main()
