# BM25 dev error analysis (provisional)

This review compares the supplied Top-10 run with passages found by scanning the complete 3,077-chunk snapshot. It is a development diagnosis, not final legal validation.

| Pattern | Examples | Diagnosis / follow-up |
|---|---|---|
| Lexical match on “ban đêm” | `dev-night_horn-1` ranks rules about oversized goods at night above the horn rule | False positives. The horn rule is present at rank 4; consider query weighting for còi/cấm còi rather than generic night terms |
| Wrong vehicle class | `motorcycle_stop-1` finds Decree 168 Art. 8(2)(d), whose heading is for specialized motor vehicles | Do not label it relevant to a motorcycle. The law's general signal rule is present outside some Top-10 lists. No motorcycle-specific penalty text was found in the chunk sweep; ask Huy to verify |
| Topic drift | All ten results for `dev-alcohol-2` are unrelated to alcohol | Search failure, not by itself a corpus gap; alcohol rules and motorcycle penalty thresholds are present elsewhere in the snapshot |
| Missed exact rule | `dev-red_light-2` and `dev-red_light-3` return goods/transport passages; the car red-light penalty passage appears for `dev-red_light-1` but not those variants | Query wording sensitivity / ranking failure. Keep vehicle-specific penalties separate from the general rule that red means stop |
| Passage buried in ranking | `dev-pedestrian-2` returns the exact crossing-place rule at rank 4; `dev-pedestrian-1` has it at rank 7 | Partial success; likely query reformulation/ranking opportunity |
| Missing target detail in available corpus | Expired-licence queries retrieve “expired licence is invalid” and penalties for driving with an expired licence, but not substantive renewal/exchange conditions | Suspected corpus gap. Huy should verify whether the governing procedure document is absent from the snapshot |
| Weak age-scenario retrieval | The 15-year-old / 110cc query returns child-safety and lighting passages, while the age rule and underage penalty are present outside Top-10 | Retrieval failure. Keep the exact vehicle class (moped vs 110cc motorcycle) explicit in the judgment |
| Points-query mismatch | The “no points, may I keep driving?” query returns transitional licence categories rather than Law 36 Art. 58(3) | Retrieval failure; the direct no-driving rule is in the corpus but outside the supplied Top-10 |

## Data items for Huy to verify

1. Whether the four-instrument corpus snapshot is missing an authoritative document on expired driver-licence exchange conditions and procedure.
2. Whether Decree 168 contains a motorcycle-class penalty for leaving/entering a stopping or parking position without signaling, or whether this action is not separately penalized in the captured source set. The visible Art. 8 hit is for specialized motor vehicles and cannot stand in for motorcycles.
3. Review the 33 source-gap records and 2,919 pending scope proposals before treating any full-corpus coverage decision as complete.
