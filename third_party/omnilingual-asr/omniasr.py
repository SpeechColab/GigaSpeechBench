from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline
from omnilingual_asr.models.wav2vec2_llama.lang_ids import supported_langs

from pathlib import Path
from tqdm import tqdm
from collections import defaultdict

import torchaudio
import os, sys
import json, shutil
import argparse
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from utils import save_transcription


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
        "--ref-dir", 
        type=str, 
        default=None,
        help="path to where ref json files are stored."
    )
    parser.add_argument(
        "--audio-dir", 
        type=str, 
        default=None,
        help="Where audio files are stored."
    )
    parser.add_argument(
        "--output-dir", 
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
        "--languages", 
        type=str, 
        nargs="+",
        default='DZA',
        help="language code"
    )
    parser.add_argument(
        "--batch-size", 
        type=int, 
        default=4,
        help="batch size for transcription"
    )
    parser.add_argument(
        '--batch-decode', 
        action='store_true', 
        help='If False, the decoding process will be for loop to avoid error'
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

    elif language == 'IDN':
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
    SAMPLE_RATE = 16000
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
                    continue
                if duration < 0.5:
                    print(f'WARNING: {wav_path} is too short: {duration} seconds')
                    continue

                # audio_files.append(wav_path)
                meta[wav_path].append((0.0, duration))
                metainfo.append([wav_path, 0.0, duration])
            elif len(line.strip().split()) == 3:
                wav_path, start, end = line.strip().split()
                assert os.path.isfile(wav_path), f"{wav_path} not a file"

                duration = float(end) - float(start)
                if duration > 40.0:
                    print(f'WARNING: {wav_path} segment is too long: {duration} seconds')
                    continue
                if duration < 0.5:
                    print(f'WARNING: {wav_path} segment is too short: {duration} seconds')
                    continue

                meta[wav_path].append((float(start), float(end)))
                metainfo.append([wav_path, start, end])
            else:
                print(line)
                raise

    for wav_path, segments in tqdm(meta.items()):
        try:
            waveform, sr = torchaudio.load(wav_path)

            # Convert to mono if needed
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)

            # Resample to 16k if needed
            if sr != SAMPLE_RATE:
                resampler = torchaudio.transforms.Resample(sr, SAMPLE_RATE)
                waveform = resampler(waveform)

            # Convert to numpy array
            audio = waveform.squeeze().numpy()

            for (start_time, end_time) in segments:
                # Convert time to sample indices
                start_sample = int(start_time * SAMPLE_RATE)
                end_sample = int(end_time * SAMPLE_RATE)

                # Boundary check
                start_sample = max(0, start_sample)
                end_sample = min(len(audio), end_sample)

                if start_sample >= end_sample:
                    raise ValueError(f"Invalid time range: {start_time} - {end_time}")

                # Extract segment
                segment = audio[start_sample:end_sample]
                audio_files.append({"waveform": segment, "sample_rate": SAMPLE_RATE})

        except Exception as e:
            raise RuntimeError(f"Failed to extract audio segment from {wav_path}: {e}")
            
    return metainfo, audio_files



def load_transcribed_segments(result_file):
    """
    loading previous transcribed result file.
    This could be used when resuming from a suspended transcribing session.
    """
    try:
        with open(result_file, 'r', encoding='utf-8') as f:
            segments = json.load(f)
    except Exception as e:
        print(f"CANNOT PROCESS {result_file}: \n{e}")
        return []

    assert isinstance(segments, list)
    print(f'loaded {len(segments)} segments from {result_file}')

    transcribed_segments = set()
    for seg in segments:
        audio_name = Path(seg['path']).stem
        start_time = seg['start_time']
        end_time = seg['end_time']
        transcribed_segments.add((
            audio_name,
            float(start_time),
            float(end_time),
        ))
    return transcribed_segments


def is_segment_transcribed(segment, transcribed) -> bool:
    """
    判断当前 segment 是否已经转译过
    Args:
        segment: an element from ref_json, a dict.
        transcribed: a set.
    Returns:
        true if segment is in transcribed
    """
    audio_name = segment['audio_name']
    start = float(segment['start'])
    end = float(segment['end'])
    return (audio_name, start, end) in transcribed


def process_ref_json(input_file, audio_dir, language, result_file):
    """
    修改了文件处理逻辑，该函数将直接读取 ref json，并转换为 omniASR 能处理的格式
    Args:
        input_file: pre-processed ref json file,
            generated by data_process/generate_ref_json.py

        audio_dir: audio stored path

        language: language id

        result_file: str, where results saved, 
            we load data from this json file and see how many data have already been processed
    Return:
        metainfo: [(audio, start, end, index), ...]
        audio_files: omniASR model input: [(audio, start, end), ...]
    """
    transcribed_segments = load_transcribed_segments(result_file)

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            segments = json.load(f)
    except Exception as e:
        print(f"CANNOT PROCESS {input_file}: {e}")

    assert isinstance(segments, list)
    segments_by_audio = defaultdict(list)
    for segment in segments:
        audio_name = segment.get("audio_name", "")
        if audio_name:
            segments_by_audio[audio_name].append(segment)
    print(f'{input_file} has {len(segments_by_audio)} audios, with {len(segments)} segments in total.')

    SAMPLE_RATE = 16000
    metainfo = []
    audio_files = []

    for audio_idx, (audio_name, segments) in enumerate(segments_by_audio.items(), 1):
        print(f"[{audio_idx}/{len(segments_by_audio)}] Processing: {audio_name}")

        audio_extensions = ['.wav', '.mp3', '.flac', '.m4a']
        audio_path = None
        
        lang_audio_dir = os.path.join(audio_dir, language)
        for ext in audio_extensions:
            potential_path = os.path.join(lang_audio_dir, f"{audio_name}{ext}")
            if os.path.exists(potential_path):
                audio_path = potential_path
                break
        
        if audio_path is None:
            print(f"    WARNING: AUDIO FILE DOESN'T EXISTS: {lang_audio_dir}/{audio_name}[.wav|.mp3|.flac|.m4a]")
            continue

        print(f"Found audio file: {audio_path} with {len(segments)} segments")

        waveform, sr = torchaudio.load(audio_path)
        if waveform.shape[0] > 1:   # Convert to mono if needed
            waveform = torch.mean(waveform, dim=0, keepdim=True)
        if sr != SAMPLE_RATE:       # Resample to 16k if needed
            resampler = torchaudio.transforms.Resample(sr, SAMPLE_RATE)
            waveform = resampler(waveform)
        audio = waveform.squeeze().numpy()

        for seg_idx, segment in enumerate(segments, 1):
            if is_segment_transcribed(segment, transcribed_segments):
                print(f'{audio_name}_{seg_idx} is already transcribed. Skip.')
                continue

            start_time = float(segment['start'])
            end_time = float(segment['end'])
            if start_time >= end_time:
                raise ValueError(f"Invalid time range: {start_time} - {end_time}")
            
            dur = end_time - start_time
            if dur < 0.5 or dur > 40.0:
                print(f'Skipping {audio_name}_{seg_idx} with duration: {dur}')
                continue

            start_sample = int(start_time * SAMPLE_RATE)
            end_sample = int(end_time * SAMPLE_RATE)
            start_sample = max(0, start_sample)
            end_sample = min(len(audio), end_sample)

            # Extract segment
            segment = audio[start_sample:end_sample]
            audio_files.append({"waveform": segment, "sample_rate": SAMPLE_RATE})
            metainfo.append([audio_path, start_time, end_time, seg_idx])
    
    assert len(audio_files) == len(metainfo)
    print(f'processed {len(metainfo)} segments to transcribing.')
    return metainfo, audio_files


def batch_transcribe_audios(
    input_file: str = None,
    audio_dir: str = None,
    output_dir: str = None,
    model: str = 'omniASR_LLM_3B',
    language: str = 'IRQ',
    batch_size: int = 2,
    batch_decode: bool = True,
):
    """
    批量转录大量音频，请指定一个包含音频信息的文件
    Args:
        input_file: str (line format belike: {wav_path}\t{start}\t{end})
            if no start / end is provided, whole audio will be processed
            Currently only audio files shorter than 40 seconds are accepted for inference.
        
        output_dir: str, where results saved, 
            or maybe save_transcription has hardcoded the output path...

        audio_dir: str, where audio files are stored.

        model: omnilingual-ASR model choice (str)
        language: language code (str)
        batch_decode: set to False only if you met ValueError while transcribing
        batch_size: decide how big every batch is when batch_decode is True
    """
    assert input_file is not None

    print('Loading input audio files...')
    # metainfo, audio_files = process_audio_files(input_file)
    result_file = os.path.join(output_dir, f'{language}_{model}.json')
    metainfo, audio_files = process_ref_json(input_file, audio_dir, language, result_file)

    print('Loading omniasr model:')
    pipeline = ASRInferencePipeline(model_card=model)

    if batch_decode:
        print(f'Transcribing with batch size {batch_size} ...')
        lang = [get_omniasr_lang(language)] * len(audio_files)
        transcriptions = pipeline.transcribe(audio_files, lang=lang, batch_size=batch_size)
    
    else:
        print(f'Transcribing in for loop ...')
        transcriptions = []
        for i, audio_file in tqdm(enumerate(audio_files), total=len(audio_files)):
            try:
                transcription = pipeline.transcribe([audio_file], lang=[get_omniasr_lang(language)], batch_size=1)
                transcriptions.append(transcription[0])
            except Exception as e:
                print(f"Error transcribing file {metainfo[i]}: {e}")
                transcriptions.append(None)

    for (audio_path, start, end, index), text in zip(metainfo, transcriptions):
        if text is not None:
            save_transcription(audio_path, text, language, model, start, end, index)

    print('DONE')


def main():
    parser = get_parser()
    args = parser.parse_args()

    # test code & download models:
    if args.audio:
        transcribe_audio(args.audio, args.start, args.end, args.model, args.language)

    # After downloading the models, you can batch processing audios:
    elif args.ref_dir:
        languages = [lang.upper() for lang in args.languages]

        ref_dir = os.path.abspath(args.ref_dir)
        audio_dir = os.path.abspath(args.audio_dir)
        output_dir = os.path.abspath(args.output_dir)

        assert os.path.exists(ref_dir)
        assert os.path.exists(audio_dir)
        os.makedirs(output_dir, exist_ok=True)

        for lang in languages:
            ref_file = os.path.join(ref_dir, f"{lang}.json")
        
            if not os.path.exists(ref_file):
                print(f"ref file: {ref_file} doesn't exists.")
                continue
    
            batch_transcribe_audios(
                input_file=ref_file,
                audio_dir=audio_dir,
                output_dir=output_dir,
                model=args.model, 
                language=lang,
                batch_decode=args.batch_decode,
                batch_size=args.batch_size,
            )

            # move saved file to output_dir:
            results_dir = os.path.join(os.getcwd(), "results")
            filename = f"{lang}_{args.model}.json"
            source_file = os.path.join(results_dir, filename)
            assert os.path.exists(source_file), f'{source_file} does not exists'

            target_file = os.path.join(output_dir, filename)
            if os.path.exists(target_file):
                print(f"WARNING: {target_file} exists! And will be replaced.")
                shutil.move(source_file, target_file)


if __name__ == "__main__":
    main()
