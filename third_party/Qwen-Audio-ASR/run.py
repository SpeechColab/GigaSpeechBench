"""Prepare GigaSpeechBench, call one hosted ASR model, and export complete results."""
from __future__ import annotations

import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import time

import soundfile as sf

from client import Runner
from common import API_BASE, atomic_json, read, redact, sha
from prepare import prepare_group
from storage import Storage

MODELS = ('qwen-audio-3.1-asr-flash', 'qwen-audio-3.1-asr-flash-filetrans', 'qwen-audio-3.0-asr-flash')
SUBSETS = {'low-resource': ['Low-Resource-Languages'], 'zh-en': ['Vertical-Domain', 'CH-EN-Dialects'],
           'vertical-domain': ['Vertical-Domain'], 'dialects': ['CH-EN-Dialects'],
           'older-children': ['Older-Children'],
           'all': ['Low-Resource-Languages', 'Vertical-Domain', 'CH-EN-Dialects']}
LANGUAGES = {'CH': 'zh', 'CHN': 'zh', 'EN': 'en', 'ENG': 'en', 'USA': 'en',
             'JPN': 'ja', 'KOR': 'ko', 'VNM': 'vi', 'THA': 'th', 'IDN': 'id', 'IND': 'id',
             'MYS': 'ms', 'FIL': 'tl', 'PHL': 'tl', 'GAN': 'zh', 'JIN': 'zh', 'MIN': 'zh',
             'WU': 'zh', 'XIANG': 'zh', 'YUE': 'zh', 'ARE': 'ar', 'DZA': 'ar', 'EGY': 'ar',
             'IRQ': 'ar', 'MAR': 'ar', 'SAU': 'ar', 'SYR': 'ar'}
SUPPORTED = set('zh en ja ko vi th id ms tl hi ar fr de es pt ru it nl sv da fi no el pl cs hu ro bg hr sk'.split())


def language_code(group: str) -> str:
    code = LANGUAGES.get(group.upper().rsplit('-', 1)[-1], group.lower())
    if code not in SUPPORTED:
        raise ValueError(f'No supported language mapping for {group}; use --language explicitly')
    return code


def parameters(model: str, language: str) -> dict:
    result = {'language_hints': [language]}
    if model.endswith('-filetrans'):
        return {**result, 'keep_dialect': False, 'channel_id': [0], 'diarization_enabled': False,
                'special_word_filter': json.dumps({'system_reserved_filter': False,
                    'filter_with_signed': {'word_list': []}, 'filter_with_empty': {'word_list': []}})}
    result.update(format='wav', sample_rate='16000')
    if model == MODELS[0]:
        result.update(keep_dialect=False, speaker_diarization_enabled=False)
    return result


def merged(rows: list[dict], group: str) -> list[dict]:
    audios = {}
    for row in rows:
        aid = row['audio_name']
        if not aid.startswith(group+'#'):
            aid = group+'#'+aid
        begin, end = str(row['start']), str(row['end'])
        audios.setdefault(aid, {'aid': aid, 'language': group, 'segments': []})['segments'].append({
            'sid': f'{aid}#{begin}#{end}', 'begin_time': begin, 'end_time': end, 'text': row['text']})
    return list(audios.values())


def export(sources: list[tuple], work: Path, model: str) -> None:
    staged = {}
    maps = []
    for module, group, manifest, source_rows in sources:
        refs, hyps = [], []
        for row in source_rows:
            key = module+'/'+group+'/'+row['segment_key']
            result = read(work/'responses'/(hashlib.sha256(key.encode()).hexdigest()+'.json'))
            if result['status'] not in {'success', 'empty_exhausted'}:
                raise ValueError('Incomplete results cannot be exported')
            meta = row['meta']
            entry = {'audio_name': meta['ref_audio_name'], 'start': meta['start_time'], 'end': meta['end_time']}
            refs.append({**entry, 'text': row['ref_text']})
            hyps.append({**entry, 'text': result['text']})
        text = work/'pipeline/data/text'/module
        atomic_json(text/'ref'/f'{group}.json', refs)
        atomic_json(text/'hyp'/group/f'{group}_{model.upper()}.json', [{**h, 'model': model.upper()} for h in hyps])
        atomic_json(work/'legacy'/model.upper()/module/'ref'/f'{group}.json', refs)
        atomic_json(work/'legacy'/model.upper()/module/'hyp'/f'{group}.json', hyps)
        atomic_json(work/'staging'/module/'data'/group/'metadata.json', {'audios': merged(refs, group)})
        staged.setdefault(module, []).extend(merged(hyps, group))
        for aid in dict.fromkeys(r['audio_name'] for r in refs):
            maps.append({'module': module, 'group': group, 'original_aid': aid,
                         'aid': aid if aid.startswith(group+'#') else group+'#'+aid})
    for module, audios in staged.items():
        if len({a['aid'] for a in audios}) != len(audios):
            raise ValueError('Staging audio identity collision')
        atomic_json(work/'staging'/module/'results'/f'{model.upper()}.json', {'audios': audios})
    atomic_json(work/'identity_map.json', maps)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=MODELS, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--data-root', type=Path, help='HF snapshot with CATEGORY/data/GROUP/metadata.json')
    source.add_argument('--prepared-root', type=Path, help='Directory with GROUP/input_prepare.json manifests')
    parser.add_argument('--subset', choices=SUBSETS, default='older-children')
    parser.add_argument('--module', default='Older-Children', choices=sorted({m for ms in SUBSETS.values() for m in ms}),
                        help='Export category when using --prepared-root')
    parser.add_argument('--groups', nargs='+')
    parser.add_argument('--language', choices=sorted(SUPPORTED), help='Override subgroup language mapping')
    parser.add_argument('--work-dir', required=True, type=Path)
    parser.add_argument('--oss-prefix', required=True, help='Your writable object prefix; clips are content-addressed')
    parser.add_argument('--workers', type=int)
    parser.add_argument('--rps', type=float, default=6)
    parser.add_argument('--empty-retries', type=int, default=10)
    parser.add_argument('--limit-per-group', type=int)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--dataset-repo', default='speechcolab/GigaSpeechBench')
    parser.add_argument('--dataset-revision', default='680d3057641b7507a1ef14974407c7b0a7964e64')
    args = parser.parse_args()
    route = 'filetrans' if args.model.endswith('-filetrans') else 'flash'
    workers = args.workers if args.workers is not None else (64 if route == 'filetrans' else 32)
    if not 1 <= workers <= 128 or not math.isfinite(args.rps) or not 0 < args.rps <= 10:
        parser.error('Use 1..128 workers and a finite RPS in (0, 10]')
    if args.empty_retries < 0 or (args.limit_per_group is not None and args.limit_per_group < 1):
        parser.error('Invalid empty retry count or limit')
    prefix = args.oss_prefix.strip('/')
    if not prefix or any(p in {'.', '..'} for p in prefix.split('/')):
        parser.error('A nonempty OSS prefix without dot path components is required')
    work = args.work_dir.resolve()
    source_root = (args.data_root or args.prepared_root).resolve()
    if work == source_root or work.is_relative_to(source_root) or source_root.is_relative_to(work):
        parser.error('work-dir must be separate from the input tree')
    work.mkdir(parents=True, exist_ok=True)
    with (work/'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (work/'protocol.json').exists() and not args.resume:
            parser.error('Existing run: use --resume or a new work directory')
        if args.download:
            if not args.data_root:
                parser.error('--download requires --data-root')
            from huggingface_hub import snapshot_download
            patterns = [f'{m}/data/{g}/{n}' for m in SUBSETS[args.subset]
                        for g in (args.groups or ['*']) for n in ('metadata.json', 'audio.tar.gz')]
            snapshot_download(args.dataset_repo, repo_type='dataset', revision=args.dataset_revision,
                              local_dir=source_root, allow_patterns=patterns)
        selected = []
        if args.prepared_root:
            selected = [(args.module, p.parent.name, p) for p in sorted(source_root.glob('*/input_prepare.json'))]
        else:
            for module in SUBSETS[args.subset]:
                paths = sorted((source_root/module/'data').glob('*/metadata.json'))
                if not paths and not args.groups:
                    raise ValueError(f'Missing dataset category: {module}')
                selected.extend((module, p.parent.name, p) for p in paths)
        selected = [item for item in selected if not args.groups or item[1] in args.groups]
        if not selected or (args.groups and set(args.groups)-{g for _, g, _ in selected}):
            raise ValueError('No input groups or requested groups missing')
        sources, jobs, fingerprints = [], [], {}
        for module, group, path in selected:
            language = args.language or language_code(group)
            fingerprints[f'{module}/{group}'] = sha(path)
            if args.data_root:
                path = prepare_group(path.parent, work/'prepared'/module/group, language, args.limit_per_group)
            content = path.read_text()
            rows = json.loads(content) if content.lstrip().startswith('[') else [json.loads(s) for s in content.splitlines() if s.strip()]
            if args.limit_per_group:
                rows = rows[:args.limit_per_group]
            seen = set()
            for row in rows:
                meta = row['meta']
                identity = (meta['ref_audio_name'], float(meta['start_time']), float(meta['end_time']))
                if (identity in seen or not all(math.isfinite(t) for t in identity[1:])
                        or not 0 <= identity[1] < identity[2] or not isinstance(row['ref_text'], str)):
                    raise ValueError('Invalid or duplicate source segment')
                seen.add(identity)
                audio = (path.parent/row['audio_path']).resolve()
                info = sf.info(audio)
                if info.format != 'WAV' or info.samplerate != 16000 or info.channels != 1:
                    raise ValueError('Prepared input must be mono 16 kHz WAV')
                digest = sha(audio)
                jobs.append({'segment_key': module+'/'+group+'/'+row['segment_key'], 'audio_path': str(audio),
                             'sha256': digest, 'language': language, 'oss_key': prefix+'/'+digest+'.wav'})
            sources.append((module, group, path, rows))
        if not jobs or len({r['segment_key'] for r in jobs}) != len(jobs):
            raise ValueError('Empty input or duplicate segment keys')
        protocol = {'model': args.model, 'endpoint': API_BASE, 'inputs': fingerprints,
                    'parameters': {r['language']: parameters(args.model, r['language']) for r in jobs},
                    'audio_sha256': {r['segment_key']: r['sha256'] for r in jobs},
                    'oss_bucket': os.getenv('OSS_BUCKET_NAME'), 'oss_region': os.getenv('OSS_REGION'),
                    'oss_prefix': prefix, 'empty_retries': args.empty_retries, 'limit_per_group': args.limit_per_group,
                    'source_sha256': {p.name: sha(p) for p in Path(__file__).parent.glob('*.py')}}
        if (work/'protocol.json').exists() and read(work/'protocol.json') != protocol:
            raise ValueError('Input, model, parameters, or code changed; use a new work directory')
        atomic_json(work/'protocol.json', protocol)
        atomic_json(work/'inference_manifest.json', jobs)
        if args.prepare_only:
            print(json.dumps({'prepared': len(jobs)}))
            return
        for name in ('DASHSCOPE_API_KEY', 'OSS_ACCESS_KEY_ID', 'OSS_ACCESS_KEY_SECRET', 'OSS_REGION', 'OSS_BUCKET_NAME'):
            if not os.getenv(name):
                raise ValueError(f'Missing environment variable: {name}')
        runner = Runner(route, args.rps, out=work, model=args.model,
                        parameter_factory=lambda lang: parameters(args.model, lang), empty_retries=args.empty_retries)

        def recognize(row: dict) -> None:
            dest = work/'responses'/(hashlib.sha256(row['segment_key'].encode()).hexdigest()+'.json')
            for attempt in range(3):
                try:
                    if not dest.exists():
                        Storage().upload(row)
                    runner.work(row)
                    return
                except Exception as exc:
                    if attempt == 2 or 'unknown outcome' in str(exc) or 'outcome unknown' in str(exc):
                        raise
                    time.sleep(2**(attempt+1))

        completed = 0
        failures = []
        pending = iter(jobs)
        started = time.time()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {}
            def enqueue() -> None:
                row = next(pending, None)
                if row is not None:
                    futures[pool.submit(recognize, row)] = row
            for _ in range(workers):
                enqueue()
            last = 0.0
            while futures:
                done, _ = wait(futures, timeout=10, return_when=FIRST_COMPLETED)
                for future in done:
                    row = futures.pop(future)
                    try:
                        future.result()
                        completed += 1
                    except Exception as exc:
                        failures.append({'segment_key': row['segment_key'], 'error': redact(str(exc))})
                    if not failures:
                        enqueue()
                if time.time()-last >= 15 or not futures:
                    state = {'done': completed, 'total': len(jobs), 'failures': len(failures), 'seconds': time.time()-started}
                    atomic_json(work/'status.json', state)
                    print(json.dumps(state), flush=True)
                    last = time.time()
        atomic_json(work/'failures.json', failures)
        if failures:
            raise RuntimeError('Incomplete run; inspect failures.json and resume. No completed export was written.')
        export(sources, work, args.model)
        atomic_json(work/'status.json', {'phase': 'complete', 'done': completed, 'total': len(jobs)})


if __name__ == '__main__':
    main()
