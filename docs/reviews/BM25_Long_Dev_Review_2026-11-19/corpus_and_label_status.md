# BM25 dev review status

## Inputs checked

- Baseline ZIP SHA-256 matches the supplied sidecar.
- The evaluation ZIP binds to BM25 index `vtls-bm25s-lucene.v1` and dataset `vtls-coverage-experimental.v1`.
- Baseline contains 3,077 indexed chunks from four 2024 instruments: 35/2024/QH15, 36/2024/QH15, 165/2024/NĐ-CP, and 168/2024/NĐ-CP.
- The evaluation run has Top-10 results for all 30 queries, and all 30 searches completed successfully.
- Evaluation state is `PENDING_LABELS`: 300 candidate labels pending, 30 query reviews pending, `qrels.jsonl` empty, no accepted judgments, and no metrics.
- A separate working proposal now lists 77 possible positive judgments for Long to review; the 300 original annotation records and the supplied `qrels.jsonl` remain unchanged.

## Corpus limitations

The supplied snapshot is usable for a development experiment, as requested, but its own manifests say `experimental=true`, `legal_verification=false`, `release_eligible=false`, and `corpus_version=null`. It reports 2,919 scope proposals pending, 33 source-gap records, 46 deferred units, and source/applicability review pending. The date is 2025-01-01. Any reported dev metrics must carry these limitations.

## Coverage leads from a full-chunk text sweep

The sweep was a relevance lead search across all 3,077 chunk texts, not a legal sign-off or proof that every relevant passage was found. Each candidate still needs a human check against the complete context and the agreed rubric.

| Query group | Lead outside Top-10 / coverage note | Current interpretation |
|---|---|---|
| motorcycle_stop | Law 36, Art. 18(3)(a), chunk `c_96302c44f490a78e5ecf2efbb3cab276fe7cc6943b3c30ae93b8c654902dfde2` | The direct rule exists. The superficially matching Decree 168 Art. 8(2)(d) hit (`c_2161734d90a868725a276e7adda40b2d0762061fa9b864e206f31c98cbf1bfb2`) is under the heading for specialized motor vehicles, so it must not be judged relevant to a motorcycle query. No motorcycle-specific penalty passage was found in the full-chunk phrase sweep; Huy should verify whether this is a corpus gap |
| night_horn | Law 36, Art. 21(2), `c_1a62de0c691cf366786bf2b871f8e2d045512204f3ac91e4a17e8d6ebc009802`; Decree 168, Arts. 6/7 penalties, `c_a5785aafe2b19ea902bc6c7bd66746b717e203f44c6fb6b29c3c88aebea59959` and `c_a49a127d239f3bcb7777ec2b5719329fc450daa8de47bac00a83659841baf724` | Direct rule and penalties exist. The goods-at-night result is a false lexical match, not a horn rule |
| driving_age | Law 36, Art. 59(1)(b), `c_30a64fc1bea93d7860d4f3821af382006956ca7dcbdc7770e636782e97fb1d9e`; Decree 168, Art. 18(4)(a), `c_3323329546e5c7a385eb4b40b25aa57e5fa8cc6d4f0aebf6fe7b83c754b43be6`; Art. 18(1), `c_a77abb18483c50f0c13a62671b639eff8c34199c0de4f4b1228f60fb9008eb9d` | Source passages exist; `driving_age-3` has poor Top-10 results |
| licence_points | Law 36, Art. 58(1)-(3), chunks `c_66603c4c82714a4dc21725cff6a3aa0dde5d4f94d53d1bddeeebda5e1df55c35`, `c_64504dccc76cd16e68d3bfca11b122249472cbdfca1e798e0cd04287e97d2d30`, and `c_298b8c2865cabcaf0dc28f4e06b3f1fc1708fbbdf15f5b29d5852abe87ef2fad` | Relevant provisions exist; retrieval varies by query |
| alcohol | Law 36, Art. 9(2), `c_251e73033a44c7279c70d25ba9c7e93ff2573ff68e6cb889c289339348b6ef02`; Decree 168, Art. 7 motorbike thresholds, including `c_0b0f37137528b90b9d2b27843358bdeeaffce685ddbf4cfa8edf8cabfb8f0a12` | Rules exist; `alcohol-2` Top-10 is off-topic. Threshold judgments must respect vehicle class |
| red_light | Law 36, Art. 11(4)(c), `c_8bc5c29870ede49e9714da306fd41b84fe1799aa03357031fbe142b86b52bae7`; auto penalty, Decree 168 Art. 6(9)(b), `c_f15cec78fd1456f829a37a39c6edbd71cd9a70cf26a54660c3b321e6eba1208a` | Relevant provisions exist; red-light dev queries 2/3 have weak Top-10 retrieval |
| helmet | Law 36, Art. 33(2), `c_69e6fd68f3181cef8133549e7f36560223a21cc1e8160c4565b2497bcfbc5c9c`; motorcycle passenger penalty, Decree 168 Art. 7(2)(i), `c_3a6cfddd39c1eb56eb4b51ea44ee0898f72c2020598e54123084c4a1d443db90` | Rule and penalty exist; distinguish driver vs passenger and motorbike vs bicycle |
| pedestrian | Law 36, Art. 30(1)(b), `c_d3f741ac3d34e856d3b7fb26302f1650f965ac6179e5dcba2fdfa4f9b9354363`; crossing-place penalty, Decree 168 Art. 10(1)(a), `c_05ab6a309b40dd83caafb004bd527b5d29ebc44c7768904dd3fe7599d70d26fc` | Rule exists; some exact results are below Top-10 |
| licence_exchange | Law 36 Art. 57(7)(a), `c_b9189a14c7ebdbcc36f2e8fe7d07f79e23e96a460583200b24f591e77b0543ac`, only says an expired licence is invalid; Art. 62(6), `c_6d59a403ca7d17252e337b7b361569ad24ae35e8878f30f6c8f3413d93c940c1`, delegates procedures to a minister | Available snapshot did not reveal substantive exchange conditions/procedure for an expired licence. Treat as a suspected corpus gap for Huy to verify, not as a confirmed absence |

## Next review gates

1. Confirm the proposed relevance rubric and adjudicate candidate labels, including passages outside Top-10.
2. Mark coverage complete only after a reviewer has checked the full dataset for each query; otherwise keep coverage pending and do not present Recall as final.
3. Send the suspected motorcycle-penalty and expired-licence procedure gaps, plus relevant pending source-gap records, to Huy for verification.
4. Once the 30 query reviews and qrels are accepted, calculate Recall@5/10, MRR@10, and nDCG@10 from the supplied BM25 run. Dense/Hybrid/Reranker is deferred by the user's instruction to prioritize BM25.

## Provisional BM25 calculation

The separate `qrels.proposed.jsonl` contains assistant-proposed known positives for all 30 queries. Using those proposals and the supplied Top-10 run produced:

| Metric | Provisional value |
|---|---:|
| Recall@5 over currently known positives | 0.504167 |
| Recall@10 over currently known positives | 0.658333 |
| MRR@10 | 0.498466 |
| nDCG@10 | 0.485420 |

These are a workflow preview only. The qrels are not accepted, coverage is pending, and relevant chunks may still be missing; the official report in the supplied evaluation remains `metrics: null`. The detailed calculation and per-query values are in `metrics.provisional.json`.
