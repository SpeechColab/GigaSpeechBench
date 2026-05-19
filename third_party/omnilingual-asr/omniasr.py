from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline
from omnilingual_asr.models.wav2vec2_llama.lang_ids import supported_langs

from pathlib import Path
from tqdm import tqdm
from collections import defaultdict

import torchaudio
import os, sys
import argparse
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from scripts.utils import save_transcription


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
    parser.add_argument(
        "--batch-size", 
        type=int, 
        default=2,
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
    Only LLM-series decoding requires lang id; CTC series does not support this
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
        omnilingual-asr has three relevant lang ids for Iraq; you can try each to see which works best:
            Mesopotamian Arabic (Palmyra oasis and settlements along the Euphrates),
            North Mesopotamian Arabic (used in the north),
            Najdi Arabic (used in the south)
        """
        return 'acm_Arab'       # Mesopotamian Arabic
        # return 'ayp_Arab'       # North Mesopotamian Arabic
        # return 'ars_Arab'       # Najdi Arabic 

    elif language == 'SAU':
        """
        omnilingual-asr does not have a lang id specifically for Saudi Arabia.
        Three relevant options exist: Najdi, Hijazi (Red Sea coast), Gulf Arabic (Eastern Gulf coast)
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
        omnilingual-asr has many lang ids ending with "thai",
        here we use the standalone Thai lang id
        """
        return 'tha_Thai'       # Thai

    elif language == 'IDN':
        """
        Indonesian is quite complex; several relevant lang ids are listed below:
        """
        return 'ind_Latn'       # Indonesian
        # return 'bhz_Latn'       # Bada (Indonesia)
        # return 'twe_Latn'       # Tewa (Indonesia)
        # return 'xmm_Latn'       # Manado Malay
        # return 'abs_Latn'       # Ambonese Malay
        # return 'jax_Latn'       # Jambi Malay
        # return 'max_Latn'       # North Moluccan Malay 
        # return 'mkn_Latn'       # Kupang Malay
        # return 'pmy_Latn'       # Papuan Malay
        # return 'pse_Latn'       # Central Malay, AKA South Barisan Malay
        # return 'xdy_Latn'       # Malayic Dayak

    elif language == 'MYS':
        """
        Malay also has several corresponding lang ids; listed below for reference
        """
        return 'zsm_Latn'       # standard malay
        # return 'msi_Latn'       # Sabah Malay

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
    Transcribe a single audio file. Recommended for initial testing and model downloading.

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
    Process the metainfo file input_file and aggregate into audio_files: a list containing input audio information
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


def batch_transcribe_audios(
    input_file: str = None,
    output_file: str = None,
    model: str = 'omniASR_CTC_300M',
    language: str = 'IRQ',
    batch_size: int = 2,
    batch_decode: bool = True,
):
    """
    Batch transcribe a large number of audios. Please specify a file containing audio information.
    Args:
        input_file: str (line format belike: {wav_path}\t{start}\t{end})
            if no start / end is provided, whole audio will be processed
            Currently only audio files shorter than 40 seconds are accepted for inference.
        
        output_file: str, where results saved, 
            or maybe save_transcription has hardcoded the output path...

        model: omnilingual-ASR model choice (str)
        language: language code (str)
        batch_decode: set to False only if you met ValueError while transcribing
        batch_size: decide how big every batch is when batch_decode is True
    """
    assert input_file is not None

    print('Loading input audio files...')
    metainfo, audio_files = process_audio_files(input_file)

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

    for (audio_path, start, end), text in zip(metainfo, transcriptions):
        if text is not None:
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
            batch_decode=args.batch_decode,
            batch_size=args.batch_size,
        )


if __name__ == "__main__":
    main()
