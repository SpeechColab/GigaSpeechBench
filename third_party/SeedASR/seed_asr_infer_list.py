### 字节ASR
import base64
import json
import os
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests

"""
使用的是录音文件识别大模型：豆包录音文件识别模型2.0
链接：https://console.volcengine.com/speech/service/10012
"""


DEFAULT_BATCH_OUTPUT_ROOT = Path(
    "/Users/niuzhikang/Desktop/tmp/Multilingual-ASR-Benchmark/Vertical-Domain_segments/seedasr1_400/ref"
)
DEFAULT_BATCH_INPUT_ROOT = Path(
    "/Users/niuzhikang/Desktop/tmp/Multilingual-ASR-Benchmark/output_segments/audio/testbatch"
)

class ASRError(Exception):
    pass


class SeedASR():
    def __init__(self, appid, token, model_id="volc.seedasr.auc", requests_info=None):
        self.appid = appid
        self.token = token
        self.model_id = model_id  # 豆包语音识别模型2.0的model_id是volc.seedasr.auc，豆包语音识别模型1.0的model_id是volc.bigasr.auc
        self.submit_url = "https://openspeech-direct.zijieapi.com/api/v3/auc/bigmodel/submit"
        self.query_url = "https://openspeech-direct.zijieapi.com/api/v3/auc/bigmodel/query"
        self.request_info = requests_info if requests_info else {
            "model_name": "bigmodel",
            "enable_channel_split": False,  # 关闭双声道的识别
            "enable_ddc": False,  # 关闭语义顺滑
            "enable_speaker_info": False,  # 关闭说话人信息输出
            "enable_punc": True,  # 开启标点符号
            "enable_itn": True,  # 开启文本规范化
            # "model_version": "400",  # 传 model_version = "400" 使用400模型效果
            "show_speech_rate": True,  # 开启语速信息输出
            "show_volume": True,  # 开启音量信息输出
            # "show_utterances": True,
        }
        if self.model_id == "volc.bigasr.auc":
            self.request_info["model_version"] = "400"  # bigasr默认使用400模型效果，seedasr默认使用310模型效果，使用400会报错

    def log_response_error(self, prefix, response):
        api_status = response.headers.get("X-Api-Status-Code", "<missing>")
        api_message = response.headers.get("X-Api-Message", "<missing>")
        body = response.text.strip()
        if len(body) > 1000:
            body = body[:1000] + "...(truncated)"
        print(
            f"{prefix}\n"
            f"HTTP status: {response.status_code}\n"
            f"X-Api-Status-Code: {api_status}\n"
            f"X-Api-Message: {api_message}\n"
            f"Response headers: {dict(response.headers)}\n"
            f"Response body: {body or '<empty>'}"
        )

    def infer_language(self, language_dir):
        # For current datasets, omit audio.language and rely on server-side defaults.
        return None

    def get_language_dir(self, audio_path):
        audio_path = Path(audio_path)
        return audio_path.parent.name

    def parse_segment_info(self, audio_path):
        audio_path = Path(audio_path)
        segment_name = audio_path.stem
        try:
            audio_name, start_str, end_str = segment_name.rsplit("_", 2)
        except ValueError as exc:
            raise ASRError(
                f"Invalid segment filename, expected <audio_name>_<start>_<end>: {audio_path.name}"
            ) from exc

        try:
            start_time = float(start_str)
            end_time = float(end_str)
        except ValueError as exc:
            raise ASRError(
                f"Invalid start/end time in segment filename: {audio_path.name}"
            ) from exc

        return {
            "audio_name": audio_name,
            "segment_name": segment_name,
            "start_time": start_time,
            "end_time": end_time,
            "language_dir": self.get_language_dir(audio_path),
        }

    def get_language_state(self, output_root, language_dir, state_cache):
        if language_dir in state_cache:
            return state_cache[language_dir]

        language_output_dir = Path(output_root) / language_dir
        language_output_dir.mkdir(parents=True, exist_ok=True)
        results_path = language_output_dir / "results.jsonl"
        completed_path = language_output_dir / "completed.json"
        failed_path = language_output_dir / "failed.jsonl"
        completed, rebuilt = self.load_completed_segments(completed_path, results_path)
        if rebuilt:
            self.write_completed_segments(completed_path, completed)
        failed, failed_rebuilt = self.load_failed_records(failed_path)
        stale_failed = set(failed) & completed
        if stale_failed:
            for segment_name in stale_failed:
                failed.pop(segment_name, None)
            failed_rebuilt = True
        if failed_rebuilt:
            self.write_failed_records(failed_path, failed)
        state = {
            "results_path": results_path,
            "completed_path": completed_path,
            "failed_path": failed_path,
            "completed": completed,
            "failed": failed,
        }
        state_cache[language_dir] = state
        return state

    def load_completed_segments(self, completed_path, results_path):
        rebuilt = False
        if completed_path.exists():
            try:
                with open(completed_path, "r", encoding="utf-8") as file:
                    data = json.load(file)
                if isinstance(data, list):
                    return {str(item) for item in data}, False
                print(
                    f"Invalid completed list format in {completed_path}, rebuilding from results.jsonl"
                )
                rebuilt = True
            except (OSError, json.JSONDecodeError) as exc:
                print(
                    f"Failed to read {completed_path}: {exc}. Rebuilding from results.jsonl"
                )
                rebuilt = True
        else:
            rebuilt = True

        completed = set()
        if not results_path.exists():
            return completed, rebuilt

        try:
            with open(results_path, "r", encoding="utf-8") as file:
                for line_number, line in enumerate(file, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as exc:
                        print(
                            f"Skip invalid JSONL line {line_number} in {results_path}: {exc}"
                        )
                        continue
                    segment_name = record.get("segment_name")
                    if segment_name:
                        completed.add(str(segment_name))
        except OSError as exc:
            print(f"Failed to read {results_path}: {exc}")

        return completed, rebuilt

    def write_completed_segments(self, completed_path, completed_segments):
        completed_path = Path(completed_path)
        completed_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=completed_path.parent,
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                json.dump(
                    sorted(completed_segments),
                    temp_file,
                    ensure_ascii=False,
                    indent=2,
                )
                temp_file.flush()
                os.fsync(temp_file.fileno())
            os.replace(temp_path, completed_path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

    def append_result_record(self, results_path, record):
        results_path = Path(results_path)
        results_path.parent.mkdir(parents=True, exist_ok=True)
        with open(results_path, "a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    def load_failed_records(self, failed_path):
        failed_path = Path(failed_path)
        rebuilt = False
        failed_records = {}
        if not failed_path.exists():
            return failed_records, True

        try:
            with open(failed_path, "r", encoding="utf-8") as file:
                for line_number, line in enumerate(file, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as exc:
                        print(
                            f"Skip invalid JSONL line {line_number} in {failed_path}: {exc}"
                        )
                        rebuilt = True
                        continue
                    segment_name = record.get("segment_name")
                    if not segment_name:
                        print(
                            f"Skip failed record without segment_name on line {line_number} in {failed_path}"
                        )
                        rebuilt = True
                        continue
                    failed_records[str(segment_name)] = record
        except OSError as exc:
            print(f"Failed to read {failed_path}: {exc}")
            rebuilt = True

        return failed_records, rebuilt

    def write_failed_records(self, failed_path, failed_records):
        failed_path = Path(failed_path)
        failed_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=failed_path.parent,
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                for segment_name in sorted(failed_records):
                    temp_file.write(
                        json.dumps(failed_records[segment_name], ensure_ascii=False) + "\n"
                    )
                temp_file.flush()
                os.fsync(temp_file.fileno())
            os.replace(temp_path, failed_path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

    def build_failure_record(
        self,
        audio_path,
        error,
        attempts,
        segment_info=None,
        language=None,
    ):
        audio_path = Path(audio_path)
        if segment_info is None:
            segment_name = audio_path.stem or audio_path.name
            audio_name = None
            start_time = None
            end_time = None
        else:
            segment_name = segment_info["segment_name"]
            audio_name = segment_info["audio_name"]
            start_time = segment_info["start_time"]
            end_time = segment_info["end_time"]

        return {
            "audio_name": audio_name,
            "segment_name": segment_name,
            "language": language,
            "model": self.model_id,
            "start_time": start_time,
            "end_time": end_time,
            "audio_path": str(audio_path),
            "error": str(error),
            "attempts": attempts,
            "failed_at": datetime.now(timezone.utc).isoformat(),
        }

    def record_failure(self, state, failure_record):
        state["failed"][failure_record["segment_name"]] = failure_record
        self.write_failed_records(state["failed_path"], state["failed"])

    def clear_failure(self, state, segment_name):
        if segment_name not in state["failed"]:
            return
        state["failed"].pop(segment_name, None)
        self.write_failed_records(state["failed_path"], state["failed"])

    def submit_task(self, audio_info, uid="fake_uid"):
        task_id = str(uuid.uuid4())

        headers = {
            "X-Api-App-Key": self.appid,
            "X-Api-Access-Key": self.token,
            "X-Api-Resource-Id": self.model_id,
            "X-Api-Request-Id": task_id,
            "X-Api-Sequence": "-1",
        }

        request = {
            "user": {
                "uid": uid
            },
            "audio": audio_info,
            "request": self.request_info,
        }
        print(f"Submit task id: {task_id}")
        try:
            response = requests.post(
                self.submit_url,
                json=request,
                headers=headers,
                timeout=60,
            )
        except requests.RequestException as exc:
            print(f"Submit task request failed: {exc}")
            raise ASRError(f"Submit task request failed: {exc}") from exc

        if response.headers.get("X-Api-Status-Code") == "20000000":
            x_tt_logid = response.headers.get("X-Tt-Logid", "")
            return task_id, x_tt_logid

        self.log_response_error("Submit task failed.", response)
        raise ASRError("Submit task failed.")

    def query_task(self, task_id, x_tt_logid):
        headers = {
            "X-Api-App-Key": self.appid,
            "X-Api-Access-Key": self.token,
            "X-Api-Resource-Id": self.model_id,
            "X-Api-Request-Id": task_id,
            "X-Tt-Logid": x_tt_logid,
        }
        try:
            return requests.post(self.query_url, json={}, headers=headers, timeout=60)
        except requests.RequestException as exc:
            print(f"Query task request failed: {exc}")
            raise ASRError(f"Query task request failed: {exc}") from exc

    def load_audio(self, audio_path):
        audio_path = Path(audio_path)
        try:
            with open(audio_path, "rb") as file:
                audio_content = file.read()
                base64_audio = base64.b64encode(audio_content).decode("utf-8")
                print(f"Loaded audio file: {audio_path}")
            return {
                "data": base64_audio,
                "format": audio_path.suffix.lstrip("."),
            }
        except FileNotFoundError:
            print(f"Error, Not Found {audio_path}")

    def recognize_audio(self, audio_path, language=None, uid="fake_uid"):
        audio_info = self.load_audio(audio_path)
        if not audio_info:
            raise ASRError(f"Audio file not found: {audio_path}")
        if language:
            audio_info["language"] = language  # 指定可识别的语言

        task_id, x_tt_logid = self.submit_task(audio_info, uid=uid)
        while True:
            query_response = self.query_task(task_id, x_tt_logid)
            code = query_response.headers.get("X-Api-Status-Code", "")
            if code == "20000000":  # task finished
                print("SUCCESS!")
                break
            if code not in {"20000001", "20000002"}:  # task failed
                self.log_response_error("Query task failed.", query_response)
                raise ASRError("Query task failed.")
            time.sleep(1)

        try:
            response_json = query_response.json()
        except json.JSONDecodeError as exc:
            raise ASRError(f"Failed to decode query response JSON: {exc}") from exc

        result = response_json.get("result")
        if result is None:
            raise ASRError(f"Query response missing 'result': {response_json}")
        return result


    def recognize_lists(
        self,
        file_paths,
        output_root=DEFAULT_BATCH_OUTPUT_ROOT,
        resume=True,
    ):
        output_root = Path(output_root)
        state_cache = {}
        summary = {
            "total": 0,
            "completed": 0,
            "skipped": 0,
            "failed": 0,
        }

        for file_path in file_paths:
            summary["total"] += 1
            audio_path = Path(file_path)
            try:
                segment_info = self.parse_segment_info(audio_path)
                language_dir = segment_info["language_dir"]
                language = self.infer_language(language_dir)
                state = self.get_language_state(output_root, language_dir, state_cache)

                if resume and segment_info["segment_name"] in state["completed"]:
                    print(f"Skip completed segment: {segment_info['segment_name']}")
                    summary["skipped"] += 1
                    continue

                result = self.recognize_audio(audio_path, language=language)
                record = {
                    "audio_name": segment_info["audio_name"],
                    "segment_name": segment_info["segment_name"],
                    "text": result.get("text", ""),
                    "language": language,
                    "model": self.model_id,
                    "start_time": segment_info["start_time"],
                    "end_time": segment_info["end_time"],
                }
                self.append_result_record(state["results_path"], record)
                state["completed"].add(segment_info["segment_name"])
                self.write_completed_segments(
                    state["completed_path"], state["completed"]
                )
                self.clear_failure(state, segment_info["segment_name"])
                summary["completed"] += 1
                print(
                    f"Saved result for {segment_info['segment_name']} -> {state['results_path']}"
                )
            except ASRError as exc:
                summary["failed"] += 1
                language_dir = self.get_language_dir(audio_path)
                language = self.infer_language(language_dir)
                state = self.get_language_state(output_root, language_dir, state_cache)
                segment_info = None
                try:
                    segment_info = self.parse_segment_info(audio_path)
                except ASRError:
                    pass
                failure_record = self.build_failure_record(
                    audio_path=audio_path,
                    error=exc,
                    attempts=1,
                    segment_info=segment_info,
                    language=language,
                )
                self.record_failure(state, failure_record)
                print(f"Failed to recognize {audio_path}: {exc}")

        print(
            "Batch recognition finished | "
            f"total: {summary['total']} | "
            f"completed: {summary['completed']} | "
            f"skipped: {summary['skipped']} | "
            f"failed: {summary['failed']}"
        )
        return summary


if __name__ == "__main__":
    # resource_id = "volc.bigasr.auc"  # 豆包语音识别模型1.0的model_id是volc.bigasr.auc，豆包语音识别模型2.0的model_id是volc.seedasr.auc
    resource_ids = ["volc.bigasr.auc", "volc.seedasr.auc"]
    for resource_id in resource_ids:
        asr = SeedASR(
            appid="APP_ID",
            token="API_ACCESS_KEY",
            model_id=resource_id,
        )
        file_paths = list(sorted(DEFAULT_BATCH_INPUT_ROOT.rglob("*.wav")))
        summary = asr.recognize_lists(file_paths)
        print(summary)
    
