#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
从多个 batch 读取 ref/hyp，
但最终合并为一套 ref_pool/hyp_pool，
按 country-model 输出统一的 WER/CER 结果
"""

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

WER_LANGS = ["IRQ","DZA","ARE","EGY","MAR","SAU",
             "IDN","MYS","PHL","VNM","USA"]
CER_LANGS = ["JPN","KOR","THA","CHN"]


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


def main():

    BATCHES=[
        "testbatch",
        "20251212",
        "20251205"
    ]

    ROOT_BASE = "/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/text_normalized"
    OUT_ROOT  = "/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/results_total"

    os.makedirs(OUT_ROOT,exist_ok=True)

    # ------- 累积池 --------
    ref_pool = defaultdict(list)
    hyp_pool = defaultdict(list)  # key=(country,model)

    logging.info("====== Stage1: 读取并合并 ======")

    for batch in BATCHES:

        REF_ROOT=f"{ROOT_BASE}/{batch}/ref"
        HYP_ROOT=f"{ROOT_BASE}/{batch}/hyp"

        if not os.path.exists(REF_ROOT):
            logging.warning(f"{batch} no ref")
            continue

        countries=[
            f[:-5] for f in os.listdir(REF_ROOT)
            if f.endswith(".json")
        ]

        for country in countries:

            # load ref
            ref_path=os.path.join(REF_ROOT,f"{country}.json")
            ref_items=json.load(open(ref_path,"r",encoding="utf8"))
            ref_pool[country].extend(ref_items)

            # load hyp dir
            hyp_dir=os.path.join(HYP_ROOT,country)
            if not os.path.exists(hyp_dir):
                continue

            models=[
                f[:-5] for f in os.listdir(hyp_dir)
                if f.endswith(".json")
            ]

            for model in models:
                hyp_path=os.path.join(hyp_dir,f"{model}.json")
                hyp_items=json.load(open(hyp_path,"r",encoding="utf8"))

                hyp_pool[(country,model)].extend(hyp_items)


    logging.info("====== Stage2: 统一 evaluate ======")

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


if __name__=="__main__":
    main()
