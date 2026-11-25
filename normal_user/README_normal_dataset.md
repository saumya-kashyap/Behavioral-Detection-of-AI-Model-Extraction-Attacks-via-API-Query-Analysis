# Normal User Query Dataset v1.0

Legitimate-usage traffic for the BERT news-topic classifier (World, Sports, Business, Sci/Tech). Column-compatible with `attacker_queries.csv` v2.0 so the two files can be concatenated.

**3,000 records · 115 users · 407 sessions · 2026-10-01 to 2026-10-12 · seed 20261125 · 2,784 unique texts**

## Files
| File | Purpose |
|---|---|
| `normal_queries.csv` | The dataset (victim fields empty, see below) |
| `normal_dataset_manifest.json`, `normal_dataset_stats.json` | Counts and generation stats |
| `generate_normal_dataset.py` | Reproduces the dataset: `python generate_normal_dataset.py --attacker attacker_queries.csv` |
| `replay_queries_to_api.py` | Sends queries to the victim API, fills prediction/scores/latency from real responses. Works for the attacker CSV too |
| `run_victim_locally.py` | Fallback only: runs the BERT weights directly (untested, no weights available) |

## Schema
Same first 11 columns as the attacker file: `query_id, user_id, session_id, request_timestamp, input_text, attack_strategy, label, sequence_index, generation_seed, victim_prediction, victim_confidence_scores`.
Normal rows have `attack_strategy = none`, `label = normal`. IDs use `q_100001+`, `client_101+`, so they never collide with the attacker's `q_000001-003000`, `client_001-030`.
Extra analysis-only columns: `user_profile`, `query_intent`, `intended_topic` (generator intent, not victim ground truth).
`sequence_index` is the chronological position in this file.

## How normal behaviour is simulated
Six user profiles with different session sizes, pacing, writing style and typo rates. Every profile can rephrase, follow up, repeat, and read the same trending stories as other users.

| Profile | Users | Rows | Behaviour |
|---|---|---|---|
| casual_reader | 40 | 240 | 1-7 queries/session, slow, evenings, short/casual/question style, many typos |
| news_app_user | 30 | 865 | 3-14 queries, headline-heavy, commute/lunch hours |
| student_researcher | 20 | 709 | 3-20 queries, topic-focused, frequent rephrasing |
| journalist_editor | 12 | 699 | 5-28 queries, long multi-sentence pastes, weekday work hours, jumps across topics |
| analyst_batch_user | 5 | 467 | 10-31 queries, fast (median ~6 s gap): deliberate hard negatives that look attacker-like in volume/pace |
| curious_tester | 8 | 20 | 1-5 queries, includes off-topic strings ("hello", "recipe for banana bread") |

Intents: fresh 1,862 · follow_up 412 · trending 399 · rephrase 246 · repeat 61 · off_topic 20.
Overall: median 6 queries/session (max 31), median gap 21 s, median 17 words/query (1-63).

## Filling the victim fields (must come from the real API)
```
python replay_queries_to_api.py --input normal_queries.csv --output normal_logged.csv --url http://<victim-api>/predict
python replay_queries_to_api.py --input attacker_queries.csv --output attacker_logged.csv --url http://<victim-api>/predict
```
The request/response shape is an assumption (top of the script: `REQUEST_BODY`, `parse_response`); adjust to the real API. Only `text` + `query_id/user_id/session_id/request_timestamp` are sent. Tested against a mock server, not the real API.
`--time-scale N` sleeps (simulated gap / N) between requests so inter-query timing survives replay. If the logger stamps its own arrival time, timing features need either that or a logger that accepts the forwarded `request_timestamp`. Decide this with the logging teammate.

## Leakage rules (same as the attacker dataset)
Never send `label`, `attack_strategy`, `user_profile`, `query_intent`, `intended_topic` to the API. Keep them and all IDs out of detector features. Split train/test by user/session, never by row.

## Limitations
- Synthetic, template-based text about fictional organisations/teams; not real user logs.
- Exact duplicates exist on purpose (retries, trending stories shared across users).
- `intended_topic` is not ground truth; compare it with victim predictions once logs exist.
- Gaps and session sizes are drawn from simple lognormal models, not fitted to real traffic.

## Issues found in the attacker dataset (worth raising with Jiya)
1. **Artifact suffixes:** 2,650 of 3,000 attacker texts end with filler like "Additional context item 0187 was included in this simulated request." or "The update was recorded in bulletin 190." No normal row has this, so any text-based detector will separate the classes trivially, which the project brief says to avoid.
2. **Timing:** each attacker strategy runs on its own single day starting at 09:00 UTC, and every attacker session has exactly 20 queries. Do not use absolute date/hour or session length as features without noting this.
3. **Text shape:** attacker texts are 18-52 words in a fixed two-to-four sentence format; normal texts are more varied. Partially overlapping, but a confound.
