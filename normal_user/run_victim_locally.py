#!/usr/bin/env python3
"""
FALLBACK ONLY: fill victim_prediction / victim_confidence_scores by running the BERT model directly
(no API, no real latency/logging path). Prefer replay_queries_to_api.py so normal and attacker traffic
share one logging path. NOT run in development (model.safetensors was not available) - sanity-check on 5 rows first.

Needs: pip install torch transformers ; model dir containing config.json, tokenizer.json,
tokenizer_config.json, model.safetensors.
Usage: python run_victim_locally.py --model-dir ./victim_model --input normal_queries.csv --output normal_queries_scored.csv
"""
import argparse, csv, json, time, torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

ap = argparse.ArgumentParser()
ap.add_argument("--model-dir", required=True); ap.add_argument("--input", required=True); ap.add_argument("--output", required=True)
a = ap.parse_args()
tok = AutoTokenizer.from_pretrained(a.model_dir); model = AutoModelForSequenceClassification.from_pretrained(a.model_dir).eval()
id2label = model.config.id2label
rows = list(csv.DictReader(open(a.input, encoding="utf-8")))
cols = list(rows[0].keys()) + (["response_latency_ms"] if "response_latency_ms" not in rows[0] else [])
with torch.no_grad():
    for r in rows:
        t0 = time.perf_counter()
        enc = tok(r["input_text"], return_tensors="pt", truncation=True, max_length=512)
        p = torch.softmax(model(**enc).logits, dim=-1)[0].tolist()
        r["response_latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        r["victim_prediction"] = id2label[max(range(len(p)), key=p.__getitem__)]
        r["victim_confidence_scores"] = json.dumps({id2label[i]: round(v, 6) for i, v in enumerate(p)})
with open(a.output, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
