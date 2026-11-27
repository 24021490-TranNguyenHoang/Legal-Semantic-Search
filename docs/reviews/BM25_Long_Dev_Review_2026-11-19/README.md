# BM25 review for Long — development only

This folder is a review pack for the 30-query development evaluation. It is not an accepted qrels submission and must not replace any sealed evaluation bundle.

## Inputs and binding

- Baseline archive: `bm25-baseline-v1-001.zip`; SHA-256 `8678cd66620cbacfae7443e9e0774ac36f8294aeb6edceebf1e06cfaa789d03e` (matches its supplied sidecar).
- Evaluation archive: `bm25-evaluation-dev-001.zip`; SHA-256 `baa94e3bce0385fe54108378733ce175464b9ce9b3a1a480ddfcaa6ee6dc7dc1`; its manifest binds index `vtls-bm25s-lucene.v1` and dataset `vtls-coverage-experimental.v1`.
- The 30 query IDs and texts match the repository's `config/evaluation_dev.v1.jsonl`.
- Baseline data is experimental, legal verification is false, release eligibility is false, and corpus version is null.

## Label state

- 77 assistant-proposed positive judgments, all requiring human review.
- 247 of the 300 Top-10 candidate rows remain without a relevance judgment.
- Coverage remains pending for all 30 queries.
- Do not copy `proposed_positive_judgments.jsonl` into official `qrels.jsonl`; the labels are proposals, not accepted human judgments.

## Metrics status

`metrics.provisional.json` is calculated only from currently known proposed positives. Its Recall@5/10, MRR@10, and nDCG@10 values are workflow previews, not official retrieval results. The source evaluation report remains `PENDING_LABELS` with `metrics: null` until human judgments and coverage reviews are accepted.

## Files

- `queries.jsonl`, `run.jsonl`, `evaluation_manifest.json` — source evaluation run and its binding metadata.
- `candidate_judgment_queue.csv` — 300 Top-10 candidates plus 24 proposed positive leads outside Top-10, including passage, context, source URL, and source locator.
- `proposed_judgments_review.csv` — compact table for the 77 proposed positives.
- `proposed_positive_judgments.jsonl` — machine-readable assistant proposals; not qrels.
- `query_crosswalk.md`, `corpus_and_label_status.md`, `error_analysis.md` — comparison, coverage limits, and issue triage.
- `metrics.provisional.json`, `compute_provisional_metrics.py` — provisional calculation and its reproducible calculator.
- `HANDOVER.md` — steps remaining for Long and Huy.

## Separate v6 candidate run

A separate 50-query BM25 v6 development/limit run is recorded in [`v6-candidate-run-001/`](v6-candidate-run-001/README.md). It contains 500 Top-10 candidates, frozen query inputs, per-query timing, a review queue and a manifest. All labels remain pending, so official metrics remain unavailable. This run does not replace or merge with the original 30-query pack.
