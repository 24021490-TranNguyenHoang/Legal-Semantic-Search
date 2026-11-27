# BM25 v6 candidate run 001

This is a development-only BM25 run added alongside the existing 30-query review pack. It contains 50 frozen development/limit queries and 500 Top-10 results. It is not an independent test set and has no accepted qrels.

## Binding and source

- Index: `vtls-bm25s-subset.v2`; dataset: `vtls-subset-experimental.v6-candidate.1`; snapshot `2025-01-01`.
- Index archive SHA-256: `00e966c92a655f6405a64f4cb352eef89252508ecb75e1bd6bce6f66a63538cb`.
- Index manifest SHA-256: `58c05ef0f6c2bb39d4a6af8d62d5520843c028e538a0b5d8abeb2ce5d3589c5f`.
- Dataset manifest SHA-256: `47b23b4f8742a308f32b4c1efd0d7749a81a8aae792459b95e7035490802bdfc`.
- Query manifest SHA-256: `f8cc9257c410c8eb578d43a0bd1912e3aa5c572829be5e33d7ee0a2045e546f0`. The frozen files are under `queries/`; all groups have `split=dev`.
- Source folder: [Google Drive handoff](https://drive.google.com/drive/folders/16tSZALHShIrWXSmJGZ7qpwgZZH9A9bsv). The index archive is referenced by checksum and is not duplicated in Git.
- Integration hashes are recorded in `summary.json`. The repository base used for this handoff was `07c9e31329eeb2cd0a3019f77edbf38c7d68ed97`.

## Run and timing

Executed with CPython 3.11.9, `bm25s 0.3.13`, `numpy 2.4.6`, and `scipy 1.17.1` through the v6 `BoundSearch` service. One unmeasured warmup preceded one sequential measured pass; concurrency was 1. External `service.search` latency was p50 1.240 ms and p95 1.642 ms. Internal preprocess/rank/filter latency was p50 0.658 ms and p95 0.823 ms. Service load and validation took 137224.5 ms and are reported separately.

## Review status

Every result is unjudged. `review_queue.csv` and `review_queue.xlsx` have editable relevance/evidence fields. The rubric is in `rubric.md`: 0 unrelated, 1 supporting or dependency-only, 2 direct target; leave unresolved cases blank and pending. Direct metrics use relevance 2; Useful metrics use relevance at least 1. The run manifest binds the query inputs and all committed artifacts.

The candidate index is experimental, release-ineligible, and has pending source edition/applicability. Do not calculate official metrics from this pool until a reviewer accepts qrels and completes the required coverage review. Dense, hybrid, and reranker modes were not run.

## Files

- `run.jsonl`: ordered Top-10 rows, scores, IDs, versions, and unjudged status.
- `timings.jsonl`: per-query outer and internal latency.
- `summary.json`: aggregate run facts, runtime, latency, and bindings.
- `run_manifest.json`: SHA-256 and sizes for inputs and handoff files.
- `review_queue.jsonl`, `review_queue.csv`, `review_queue.xlsx`: human review queue.
- `rubric.md`: relevance scale and recording guidance.
- `queries/`: exact 30 old-dev, 15 new-dev, and 5 limits query inputs with manifest.
