#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from pathlib import Path
from collections import defaultdict
import logging
import kaldialign

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# 原有设置保留
WER_LANGS = ["IRQ","DZA","ARE","EGY","MAR","SAU",
             "IDN","MYS","PHL","VNM","USA"]
CER_LANGS = ["JPN","KOR","THA","CHN"]

# offline batch（读取 REF）
OFFLINE_BATCHES = ["testbatch","20251212","20251205"]

# gradio hyp batch
GRADIO_BATCH = "gradio_batch"


def store_transcripts(filename: Path, texts):
    with open(filename,"w",encoding="utf8") as f:
        for cut_id,ref,hyp in texts:
            print(f"{cut_id}:\tref={' '.join(ref)}", file=f)
            print(f"{cut_id}:\thyp={' '.join(hyp)}", file=f)


def write_error_stats(f,test_set_name,results,compute_CER=False):
    ERR="*"
    subs=defaultdict(int)
    ins=defaultdict(int)
    dels=defaultdict(int)
    num_corr=0

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

    return wer


def evaluate_model(country,model,ref_items,hyp_items,compute_CER,OUT_ROOT):

    out_dir=Path(OUT_ROOT)/country/model
    out_dir.mkdir(parents=True,exist_ok=True)

    hyp_index={
        (item["audio_name"],float(item["start"])):item["text"]
        for item in hyp_items
    }

    results=[]
    for ref in ref_items:
        key=(ref["audio_name"], float(ref["start"]))
        if key not in hyp_index:
            continue
        
        ref_text=ref["text"].strip()
        hyp_text=hyp_index[key].strip()

        cut_id=f"{ref['audio_name']}_{ref['start']}"

        ref_words=ref_text.split()
        hyp_words=hyp_text.split()

        results.append((cut_id,ref_words,hyp_words))

    metric_name="cer" if compute_CER else "wer"

    recogs_path  = out_dir / f"recogs-{country}-{model}.txt"
    errs_path    = out_dir / f"errs-{country}-{model}.txt"
    summary_path = out_dir / f"{metric_name}-summary-{country}-{model}.txt"

    store_transcripts(recogs_path,results)

    with open(errs_path,"w",encoding="utf8") as f:
        wer = write_error_stats(f,f"{country}-{model}",results,compute_CER)

    with open(summary_path,"w",encoding="utf8") as f:
        print("model\tWER/CER",file=f)
        print(f"{model}\t{wer:.2f}",file=f)


def run_compute_wer(temp_root: str):

    logging.info(f"[Gradio] computing WER in {temp_root}")

    ROOT_BASE = str(Path(temp_root)/"text_normalized")
    OUT_ROOT  = str(Path(temp_root)/"results")

    os.makedirs(OUT_ROOT,exist_ok=True)

    ref_pool = defaultdict(list)
    hyp_pool = defaultdict(list)

    logging.info("====== Stage1: read refs ======")

    # scan offline ref batches
    for batch in OFFLINE_BATCHES:

        REF_ROOT=f"data/text_normalized/{batch}/ref"   # *** REF仍然来源固定位置 ***

        if not os.path.exists(REF_ROOT):
            logging.warning(f"{batch} no ref")
            continue

        countries=[
            f[:-5] for f in os.listdir(REF_ROOT)
            if f.endswith(".json")
        ]

        for country in countries:
            ref_path=os.path.join(REF_ROOT,f"{country}.json")
            ref_items=json.load(open(ref_path,"r",encoding="utf8"))
            ref_pool[country].extend(ref_items)

    logging.info("====== Stage2: read hyp(gradio batch only) ======")

    HYP_ROOT = os.path.join(ROOT_BASE,GRADIO_BATCH,"hyp")

    # countries folders
    for country in os.listdir(HYP_ROOT):
        country_dir = os.path.join(HYP_ROOT,country)
        if not os.path.isdir(country_dir):
            continue

        for fname in os.listdir(country_dir):
            if fname.endswith(".json"):
                hyp_path=os.path.join(country_dir,fname)
                hyp_items=json.load(open(hyp_path,"r",encoding="utf8"))
                model=fname.split(".json")[0]   # 文件名=model.json
                hyp_pool[(country,model)].extend(hyp_items)

    logging.info("====== Stage3: evaluate ======")

    for (country,model),hyp_items in hyp_pool.items():

        compute_CER = country in CER_LANGS
        evaluate_model(
            country,
            model,
            ref_pool[country],
            hyp_items,
            compute_CER=compute_CER,
            OUT_ROOT=OUT_ROOT
        )

    logging.info("[Gradio] finished compute_wer.")
