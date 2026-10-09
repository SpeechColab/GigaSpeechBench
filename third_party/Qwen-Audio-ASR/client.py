from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import threading
import time

import requests

from common import API_BASE, read, redact, atomic_json as save, extract
from storage import Storage

MODELS = {'flash': 'qwen-audio-3.1-asr-flash', 'filetrans': 'qwen-audio-3.1-asr-flash-filetrans'}
EMPTY_CODES = {'ASR_RESPONSE_HAVE_NO_WORDS', 'SUCCESS_WITH_NO_VALID_FRAGMENT'}


class Limiter:
    def __init__(self, rps: float):
        self.interval = 1 / rps
        self.lock = threading.Lock()
        self.next_time = 0.0

    def acquire(self) -> None:
        with self.lock:
            delay = max(0, self.next_time-time.monotonic())
            self.next_time = max(self.next_time, time.monotonic()) + self.interval
        time.sleep(delay)

    def cooldown(self, seconds: float) -> None:
        with self.lock:
            self.next_time = max(self.next_time, time.monotonic()+seconds)


def parameters(route: str, language: str) -> dict:
    common = {'language_hints': [language], 'keep_dialect': False}
    if route == 'filetrans':
        return {**common, 'channel_id': [0], 'diarization_enabled': False}
    return {**common, 'format': 'wav', 'sample_rate': '16000', 'speaker_diarization_enabled': False}


def empty_response(value: dict) -> bool:
    return value.get('code') in EMPTY_CODES or value.get('message') in EMPTY_CODES


class Runner:
    def __init__(self, route: str, rps: float, out: Path | None = None,
                 model: str | None = None, parameter_factory=None, empty_retries: int = 10):
        self.route = route
        self.empty_retries = empty_retries
        self.model = model or MODELS[route]
        self.parameter_factory = parameter_factory or (lambda language: parameters(route, language))
        if out is None:
            raise ValueError('An output directory is required')
        self.out = out
        self.out.mkdir(parents=True, exist_ok=True)
        self.submit_rate = Limiter(rps)
        self.query_rate = Limiter(12)
        self.log_lock = threading.Lock()
        self.stop = threading.Event()

    def log(self, value: dict) -> None:
        with self.log_lock:
            with (self.out / 'http.jsonl').open('a') as stream:
                stream.write(json.dumps(redact(value), ensure_ascii=False)+'\n')

    def request(self, method: str, endpoint: str, row: dict, *, payload=None, authenticated=True, submit=False) -> tuple[int, dict]:
        limiter = self.submit_rate if submit else self.query_rate
        headers = {}
        if authenticated:
            headers['Authorization'] = 'Bearer '+os.environ['DASHSCOPE_API_KEY']
        if submit:
            headers['X-DashScope-Async' if self.route == 'filetrans' else 'X-DashScope-SSE'] = 'enable' if self.route == 'filetrans' else 'disable'
        for retry in range(7):
            limiter.acquire()
            started = time.time()
            try:
                response = requests.request(method, endpoint, headers=headers, json=payload, timeout=(15,120))
                value = response.json()
            except (requests.RequestException, ValueError) as exc:
                self.log({'segment_key': row['segment_key'], 'operation': 'submit' if submit else 'query_or_download',
                          'started': started, 'seconds': time.time()-started, 'error_type': type(exc).__name__})
                if submit and self.route == 'filetrans':
                    raise RuntimeError('Submission outcome unknown; inspect pending state before resubmission') from None
                if retry == 6:
                    raise RuntimeError('Transport retry budget exhausted') from None
                time.sleep(min(30,2**(retry+1)))
                continue
            self.log({'segment_key': row['segment_key'], 'operation': 'submit' if submit else 'query_or_download',
                      'started': started, 'seconds': time.time()-started, 'http_status': response.status_code,
                      'response': value})
            if response.status_code in {408,429,500,502,503,504}:
                if retry == 6:
                    raise RuntimeError(f'HTTP retry budget exhausted: {response.status_code}')
                delay = min(30,2**(retry+1))
                limiter.cooldown(delay)
                continue
            return response.status_code, value
        raise AssertionError('Unreachable')

    def work(self, row: dict) -> dict:
        identity = hashlib.sha256(row['segment_key'].encode()).hexdigest()
        dest = self.out / 'responses' / f'{identity}.json'
        state_path = self.out / 'states' / f'{identity}.json'
        params = self.parameter_factory(row['language'])
        if dest.exists():
            result = read(dest)
            assert result['parameters'] == params and result['sha256'] == row['sha256']
            assert result['model'] == self.model
            return result
        state = read(state_path) if state_path.exists() else {
            'segment_key': row['segment_key'], 'sha256': row['sha256'], 'model': self.model,
            'parameters': params, 'empty_count': 0, 'failed_tasks': 0, 'active_task': None,
            'task_ids': [], 'created': time.time(), 'ambiguous_submission': False}
        assert state['parameters'] == params and state['model'] == self.model
        if state['ambiguous_submission']:
            raise RuntimeError('An earlier async submission has unknown outcome; refusing duplicate submission')
        storage = Storage()
        while True:
            if self.route == 'flash':
                url = storage.sign(row)
                payload = {'model': self.model, 'parameters': params, 'input': {'messages': [
                    {'role': 'user', 'content': [{'type': 'input_audio','input_audio': {'data': url}}]}]}}
                code, result = self.request('POST', API_BASE+'/services/aigc/multimodal-generation/generation',
                                            row, payload=payload, submit=True)
                if code != 200 and not empty_response(result):
                    raise RuntimeError(f'Flash failed: HTTP {code} {redact(result)}')
                text = '' if empty_response(result) else extract(result)
                transcript = None
            else:
                if not state['active_task']:
                    if self.stop.is_set():
                        raise RuntimeError('Stopped before submission')
                    url = storage.sign(row)
                    payload = {'model': self.model, 'input': {'file_urls': [url]}, 'parameters': params}
                    state['ambiguous_submission'] = True
                    save(state_path,state)
                    code, result = self.request('POST', API_BASE+'/services/audio/asr/transcription',
                                                row,payload=payload,submit=True)
                    state['ambiguous_submission'] = False
                    if code != 200 or not (result.get('output') or {}).get('task_id'):
                        save(state_path,state)
                        raise RuntimeError(f'Async submission failed: HTTP {code} {redact(result)}')
                    state['active_task'] = result['output']['task_id']
                    state['task_ids'].append(state['active_task'])
                    save(state_path,state)
                    time.sleep(3)
                polls = 0
                while True:
                    code,result = self.request('GET',API_BASE+'/tasks/'+state['active_task'],row)
                    if code != 200:
                        raise RuntimeError(f'Polling failed: HTTP {code}; task retained for resume')
                    output = result.get('output',{})
                    status = output.get('task_status')
                    state['last_task_status'] = status
                    save(state_path,state)
                    if status in {'PENDING','RUNNING'}:
                        polls += 1
                        time.sleep(min(15,3+polls))
                        continue
                    if status not in {'SUCCEEDED','FAILED'}:
                        raise RuntimeError(f'Unexpected task status {status}; task retained for investigation')
                    break
                entries = output.get('results',[])
                terminal = entries[0] if len(entries)==1 else output
                if empty_response(terminal):
                    text = ''
                    transcript = None
                elif status == 'SUCCEEDED' and len(entries)==1 and terminal.get('subtask_status')=='SUCCEEDED':
                    link = terminal.get('transcription_url')
                    if not link:
                        raise RuntimeError('Successful subtask missing transcript URL')
                    code,transcript = self.request('GET',link,row,authenticated=False)
                    if code != 200:
                        raise RuntimeError('Transcript download failed; task retained for resume')
                    channels = transcript.get('transcripts')
                    if not isinstance(channels,list):
                        raise RuntimeError('Unexpected transcript format')
                    if not channels:
                        text = ''
                    else:
                        selected = [c for c in channels if c.get('channel_id')==0]
                        if len(selected)!=1 or not isinstance(selected[0].get('text'),str):
                            raise RuntimeError('Missing channel-0 full transcript')
                        text = selected[0]['text'].strip()
                else:
                    state['failed_tasks'] += 1
                    save(self.out/'failed_tasks'/f'{state["active_task"]}.json',redact(result))
                    state['active_task'] = None
                    save(state_path,state)
                    if state['failed_tasks'] >= 3:
                        raise RuntimeError(f'Task failed three times: {redact(terminal)}')
                    time.sleep(5)
                    continue
            if text or state['empty_count'] >= self.empty_retries:
                final = {'segment_key': row['segment_key'], 'sha256': row['sha256'],
                         'model': self.model, 'parameters': params, 'endpoint': API_BASE,
                         'text': text, 'status': 'success' if text else 'empty_exhausted',
                         'empty_retries': state['empty_count'], 'task_ids': state['task_ids'],
                         'failed_tasks': state['failed_tasks'], 'response': redact(result),
                         'transcript': redact(transcript), 'wall_seconds': time.time()-state['created']}
                save(dest,final)
                state['complete'] = True
                save(state_path,state)
                return final
            state['empty_count'] += 1
            state['active_task'] = None
            save(state_path,state)
