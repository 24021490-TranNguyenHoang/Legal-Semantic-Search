# BM25 dev query crosswalk

Source set: 30 queries from `bm25-evaluation-dev-001/queries.jsonl`. Comparison set: 100 questions in `deliverables/dataset/golden_set_draft.csv`.

Normalized exact-text duplicates: **0**. The pairs below are semantic overlaps to adjudicate before treating the two sets as independent evaluation splits. Topic overlap alone does not prove duplication.

| Dev query group | Closest existing questions | Assessment | Suggested action |
|---|---|---|---|
| roundabout (3) | Q004 (right-of-way at an intersection); Q030 (yielding while turning) | Related setting, but neither asks the roundabout left-side rule | Keep; confirm that this is an intentional distinct intent |
| motorcycle_stop (3) | Q022 (signal before changing lanes); Q038 (stopping to load goods) | Adjacent signaling/stopping terms; different action and legal rule | Keep; do not merge based on terms alone |
| night_horn (3) | None close | New query intent | Keep |
| driving_age (3) | Q052 (motorcycle licence eligibility); Q058 (learner-driver conditions); Q068 (giving a vehicle to an unqualified driver) | Same broad licence/age area; Q052 is the closest, but the 15-year-old/110cc scenario is more specific | Keep the scenario; review whether the direct query should be narrowed to age by vehicle class |
| licence_points (3) | None close | New query intent | Keep |
| alcohol (3) | Q061 (penalties after drinking); Q065 (refusing an alcohol test) | Q061 is a broad near-duplicate; dev questions add motorcycle scope and a measured 0.3 mg/L scenario. Q065 is a different violation | Keep only if the added vehicle/threshold intent is wanted; otherwise merge/rewrite against Q061 |
| red_light (3) | Q002 (motorcycle red-light penalty); Q071 (car and motorcycle red-light penalties) | Strong topic and intent overlap; dev set narrows to cars | Do not retain both forms without a reason. Prefer one car-specific query in each evaluation split |
| helmet (3) | Q041 (passenger helmet requirement); Q043 (passenger safety conditions) | Dev-2 is a strong paraphrase of Q041; dev-3 is a scenario variant. Q043 is broader | Choose whether the paraphrase belongs in the same group or a separate split; avoid counting near-identical queries as independent evidence |
| pedestrian (3) | None close | New query intent | Keep |
| licence_exchange (3) | Q053 (expired licence while renewal is pending); Q055 (where/how to exchange a licence) | Strong overlap with both validity and exchange procedure; dev set is focused on expiry | Keep only if expiration-specific exchange is a distinct target intent; otherwise merge/rewrite |

Recommended policy: keep the 30-query set as a separate dev split for now, record the overlap links above, and do not combine its scores with the 100-question draft as if the 130 questions were independent. The 100-question CSV also has blank qrels, so it is not a judged comparison set.
