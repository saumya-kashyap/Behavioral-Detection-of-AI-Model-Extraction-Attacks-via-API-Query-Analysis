#!/usr/bin/env python3
"""
Replay a query CSV (normal_queries.csv OR attacker_queries.csv) through the victim API and fill the
victim fields from REAL responses. Use the same script for both datasets so both go through the same path.

Sends ONLY: text + neutral metadata (query_id, user_id, session_id, request_timestamp).
Never sends: label, attack_strategy, user_profile, query_intent, intended_topic, sequence_index, generation_seed.

ASSUMED API contract (edit REQUEST_BODY / parse_response below to match Harshita's API):
  POST <url>  {"text": "...", "query_id": "...", "user_id": "...", "session_id": "...", "request_timestamp": "..."}
  200 ->      {"label": "Sports", "scores": {"World": 0.01, "Sports": 0.97, ...}}   (scores may also be a list)
"""
import argparse, csv, json, sys, time, urllib.request, urllib.error
from datetime import datetime

def REQUEST_BODY(row, text_field):
    return {text_field: row["input_text"], "query_id": row["query_id"], "user_id": row["user_id"],
            "session_id": row["session_id"], "request_timestamp": row["request_timestamp"]}

def parse_response(js):
    label = js.get("label") or js.get("predicted_label") or js.get("prediction")
    scores = js.get("scores") or js.get("confidence_scores") or js.get("probabilities")
    return label, scores

def call(url, body, timeout, retries):
    data = json.dumps(body).encode()
    for k in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            t0 = time.perf_counter()
            with urllib.request.urlopen(req, timeout=timeout) as r:
                js = json.loads(r.read())
            return js, (time.perf_counter() - t0) * 1000
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            err = e; time.sleep(0.5 * (k + 1))
    raise RuntimeError(err)

def ts(s): return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True); ap.add_argument("--output", required=True)
    ap.add_argument("--url", required=True); ap.add_argument("--text-field", default="text")
    ap.add_argument("--time-scale", type=float, default=0,
                    help="0 = send as fast as possible; N>0 = sleep (simulated gap / N) between consecutive requests, e.g. 3600 compresses 1 hour to 1 second")
    ap.add_argument("--limit", type=int, default=None); ap.add_argument("--timeout", type=float, default=30); ap.add_argument("--retries", type=int, default=3)
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.input, encoding="utf-8")))
    rows.sort(key=lambda r: (r["request_timestamp"], r["query_id"]))      # replay chronologically
    if a.limit: rows = rows[:a.limit]
    cols = list(rows[0].keys()) + (["response_latency_ms"] if "response_latency_ms" not in rows[0] else [])
    prev, ok, bad = None, 0, 0
    for i, r in enumerate(rows, 1):
        if a.time_scale > 0 and prev is not None:
            time.sleep(max(0, (ts(r["request_timestamp"]) - prev).total_seconds()) / a.time_scale)
        prev = ts(r["request_timestamp"])
        try:
            js, ms = call(a.url, REQUEST_BODY(r, a.text_field), a.timeout, a.retries)
            label, scores = parse_response(js)
            r["victim_prediction"] = label if label is not None else ""
            r["victim_confidence_scores"] = json.dumps(scores) if scores is not None else ""
            r["response_latency_ms"] = round(ms, 2); ok += 1
        except Exception as e:
            r["response_latency_ms"] = ""; bad += 1; print(f"[{i}] {r['query_id']} FAILED: {e}", file=sys.stderr)
        if i % 250 == 0: print(f"{i}/{len(rows)} done ({bad} failed)")
    with open(a.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    print(f"finished: {ok} ok, {bad} failed -> {a.output}")

if __name__ == "__main__":
    main()
