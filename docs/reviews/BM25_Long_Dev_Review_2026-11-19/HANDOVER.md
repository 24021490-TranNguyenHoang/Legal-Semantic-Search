# BM25 dev handover for Long

## Work completed

- Verified the baseline ZIP against its SHA-256 sidecar and unpacked both ZIPs into separate working copies under `deliverables/`.
- Compared the 30 dev questions with the 100-question CSV. There are no normalized exact-text duplicates; likely semantic overlaps and keep/rewrite suggestions are recorded in `query_crosswalk.md`.
- Reviewed Top-10 results and scanned all 3,077 chunk texts for likely positive passages. Draft qrels contain 77 proposed positive judgments across all 30 query IDs. The proposed labels are not accepted and coverage remains pending.
- Calculated a provisional metrics preview from those proposed known positives.
- Recorded retrieval errors and likely source gaps for Huy to verify.

## BM25 metrics preview

| Metric | Value |
|---|---:|
| Recall@5 (known proposed positives only) | 0.504167 |
| Recall@10 (known proposed positives only) | 0.658333 |
| MRR@10 | 0.498466 |
| nDCG@10 | 0.485420 |

These are not final metrics. They use incomplete, unaccepted qrels; the numbers are for review of the workflow only. The evaluation ZIP's official report remains `PENDING_LABELS` with `metrics: null`.

## Review files

- `query_crosswalk.md` — overlap assessment against the existing 100 questions.
- `proposed_judgments_review.csv` — 77 proposed positive judgments with query text, BM25 rank or `outside_top10`, passage, context, and source locator.
- `candidate_judgment_queue.csv` — all 300 Top-10 candidates plus 24 proposed positives found outside Top-10. It marks 77 proposed positive rows for review and leaves 247 Top-10 candidates pending a human relevance judgment.
- `qrels.proposed.jsonl` — machine-readable proposed positives, explicitly marked `assistant_proposal` and `coverage: pending`.
- `metrics.provisional.json` — per-query metrics preview and limitations.
- `error_analysis.md` — retrieval issues and suspected corpus gaps to verify with Huy.
- `corpus_and_label_status.md` — input integrity, corpus state, coverage leads, and review gates.

## Still required for a careful completion

1. Long reviews/changes the 77 proposed judgments, judges the remaining candidate passages in the original 300-row pool, and accepts the labels.
2. A reviewer completes full-dataset coverage for each query. Do not mark a query complete just because no further relevant passage appeared in a keyword sweep.
3. Huy verifies the suspected gaps: motorcycle-class penalty for signaling when entering/leaving a stop/parking position, expired-licence exchange conditions, and the baseline's pending source/scope records.
4. After accepted qrels and complete coverage exist, rerun Recall@5/10, MRR@10, and nDCG@10 as official BM25 metrics. Dense/Hybrid/Reranker is deferred as requested.

The baseline snapshot is explicitly experimental and legally unverified. Final reporting should preserve that limitation even after labels are accepted.
