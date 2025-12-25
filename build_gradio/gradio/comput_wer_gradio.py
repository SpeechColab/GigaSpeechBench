#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
用于 Gradio 模式：

- ref 仍然来自 /data/text_normalized/<batch>/ref
- hyp 目录来自临时路径 temp_root/<country>/<model>.json
- 扫描全部 batch/ref
- hyp 只用传入目录，不扫描 batch
- 输出 recogs / errs / summary
- 返回 wer 值和 recogs 文件绝对路径
"""

import os
import json
from pathlib import Path
from collections import defaultdict
import logging
import kaldialign


# 这些语种使用 CER
CER_LANGS = ["JPN","KOR","THA","CHN"]


def store_transcripts(filename: Path, texts):
    """存 recogs 文件"""
    with open(filename,"w",encoding="utf8") as f:
        for cut_id,ref,hyp in texts:
            print(f"{cut_id}:\tref={' '.join(ref)}", file=f)
            print(f"{cut_id}:\thyp={' '.join(hyp)}", file=f)


def write_error_stats(f,test_set_name,results,compute_CER=False):
    """写 errs 文件"""
    ERR="*"
    subs=defaultdict(int)
    ins=defaultdict(int)
    dels=defaultdict(int)
    num_corr=0

    # char level for CER
    if compute_CER:
        tmp=[]
        for cut_id,ref_words,hyp_words in results:
            tmp.append(
                (cut_id,list("".join(ref_words)),list("".join(hyp_words)))
            )
        results=tmp

    for cut_id,ref,hyp in results:
        ali=kaldialign.align(ref,hyp,ERR)
        for ref_w,hyp_w in ali:
            if ref_w==ERR:
                ins[hyp_w]+=1
            elif hyp_w==ERR:
                dels[ref_w]+=1
            elif ref_w!=hyp_w:
                subs[(ref_w,hyp_w)]+=1
            else:
                num_corr+=1

    ref_len=sum(len(r) for _,r,_ in results)
    sub_errs=sum(subs.values())
    ins_errs=sum(ins.values())
    del_errs=sum(dels.values())
    total_err=sub_errs+ins_errs+del_errs

    wer=100.0*total_err/ref_len if ref_len>0 else 0.0

    print(f"%WER = {wer:.2f}", file=f)
    print(
        f"Errors: {ins_errs} insertions, {del_errs} deletions, "
        f"{sub_errs} substitutions, over {ref_len} units ({num_corr} correct)",
        file=f
    )

    logging.info(f"[{test_set_name}] %WER {wer:.2f}")

    return wer, ins_errs, del_errs, sub_errs, ref_len


def run_compute_wer(temp_hyp_root: str):
    """
    temp_hyp_root: 来自 gradio temp path，如：
        build_gradio/query/req_xxx/hyp

    返回：
        (
            wer,
            recogs_file_path,
            insertions,
            deletions,
            substitutions,
            total_ref_len
        )
    """

    logging.info("===== Stage0: collect REF pool =====")

    # batch 写死，不可删
    BATCHES=["testbatch","20251212","20251205"]

    BASE_REF = "data/text_normalized"   # 相对路径
    ref_pool = defaultdict(list)

    for batch in BATCHES:
        REF_ROOT=f"{BASE_REF}/{batch}/ref"
        if not os.path.exists(REF_ROOT):
            continue

        countries=[
            f[:-5] for f in os.listdir(REF_ROOT)
            if f.endswith(".json")
        ]

        for country in countries:
            ref_path=os.path.join(REF_ROOT,f"{country}.json")
            with open(ref_path,"r",encoding="utf8") as f:
                ref_items=json.load(f)

            ref_pool[country].extend(ref_items)

    logging.info("===== Stage1: read hyp from temp dir =====")

    hyp_pool = defaultdict(list)   # key=(country,model)

    for country in os.listdir(temp_hyp_root):
        c_dir=os.path.join(temp_hyp_root,country)
        if not os.path.isdir(c_dir):
            continue

        for hyp_file in os.listdir(c_dir):
            if not hyp_file.endswith(".json"):
                continue

            model=hyp_file[:-5]
            hyp_path=os.path.join(c_dir,hyp_file)

            hyp_items=json.load(open(hyp_path,"r",encoding="utf8"))
            hyp_pool[(country,model)].extend(hyp_items)

    logging.info("===== Stage2: evaluate =====")

    results_out=[]

    for (country,model),hyp_items in hyp_pool.items():

        compute_CER = country in CER_LANGS

        out_dir=Path(temp_hyp_root)/"results"/country/model
        out_dir.mkdir(parents=True,exist_ok=True)

        hyp_index={
            (item["audio_name"],float(item["start"])):item["text"]
            for item in hyp_items
        }

        results=[]
        for ref in ref_pool[country]:
            key=(ref["audio_name"], float(ref["start"]))
            if key not in hyp_index:
                continue

            ref_text=ref["text"].strip()
            hyp_text=hyp_index[key].strip()

            cut_id=f"{ref['audio_name']}_{ref['start']}"
            results.append((cut_id, ref_text.split(), hyp_text.split()))

        recogs = out_dir / f"recogs-{country}-{model}.txt"
        errs   = out_dir / f"errs-{country}-{model}.txt"
        summary= out_dir / f"{'cer' if compute_CER else 'wer'}-summary-{country}-{model}.txt"

        store_transcripts(recogs,results)

        with open(errs,"w",encoding="utf8") as f:
            wer,ins_errs,del_errs,sub_errs,ref_len= \
                write_error_stats(f,f"{country}-{model}",results,compute_CER)

        with open(summary,"w",encoding="utf8") as f:
            print("model\tWER/CER",file=f)
            print(f"{model}\t{wer:.2f}",file=f)

        # 只支持单 model 单 country，所以直接 return
        return wer, str(recogs), ins_errs, del_errs, sub_errs, ref_len

    raise RuntimeError("NO HYP FOUND in temp_root!")
