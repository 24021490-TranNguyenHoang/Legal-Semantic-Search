# Phiên 11 — đánh giá BM25 trên năm query đã có accepted labels

Ngày thực thi **2026-11-16**, Windows, Python `.venv-stage1`; snapshot sản phẩm
**2025-01-01**. HEAD đầu phiên **c9c33b1371622d6fd90338d5fb98d2e951fb10b8**,
Git sạch. Không chọn latest; không sửa/tuning/chạy lại ranking hoặc nhập nhãn.

`evaluation_scope = five_query_development_diagnostic`.
Nhãn người dùng rà và xác nhận **có ChatGPT hỗ trợ**, không independent/blind.
Đây không phải metrics chính thức50query, toàn corpus hoặc so sánh công bằng
phiên bản khác; không dùng làm kết luận thống kê tổng quát hay xác minh pháp lý.

## Đầu vào và trạng thái

| Input ghim | Manifest SHA-256 |
|---|---|
| bm25-subset-v5-batch-002 | baa811c55622580eb081b21e2df1868a3dba3d12f6f2a63acd532e6ca6b2fa09 |
| subset-v5-query-review-002 | 04ad32955c1443aedcc7b6f6f82e4e63e1bcd9a8adfe903159ff93463444b2f2 |
| subset-v5-label-aggregate-001 | 7c4dbee482e5bc7d38e96b12e4a75684b3756a47b48d4385c713e2fd846cd56e |

Các run tính từ `staging/`, input dùng `manifest.json`. Đã validate aggregate
cùng hai accepted batches, refs accepted/pending, progress và summary bằng
validator phiên10. **59accepted duy nhất**,7/10/42; **53cặp pool**,50Top10 đều
có accepted theo query+record và binding. Hai pending V3-D02 giữ nguyên, ngoài
đánh giá; không nhập lại14inherited hoặc gán proposal thành accepted.

Binding giữ nguyên dataset `vtls-subset-experimental.v5-candidate.1` (candidate006),
index `vtls-bm25s-subset.v1` (index003), queries001 và batch002. Tất cả file
frozen batch được kiểm size/hash/content inventory; run đối chiếu raw_results
và ranking signature, không đổi rank/score/ID/type/query. Không đổi bảng hoặc
whole-source thành chunk. Native evidence/dependency quotes được kiểm lại.

Config/policy được ghi trước tính toán; bằng chứng thời điểm và SHA trong
`staging/source-session11-checks-001/metric_policy.pinned.json`. Contract mới
bổ sung cách đọc Direct và query không positive, không sửa evaluator v1 vốn chỉ
chunk/Useful và đòi coverage review cho metrics rộng hơn. Tái dùng helper metric
graded nDCG, validate_queries và validators/consumer typed phiên9–10 hiện có.

## Kết quả đã tính

Macro trên đúng **5query**, không bỏ query đóng góp0. Precision mẫu sốk.
Direct iff relevance=2; Useful iff relevance>=1, gồm supporting/dependency.
Completeness giữ nguyên;2/partial không có nghĩa đủ câu trả lời.

| Cách đọc | P@1 | P@3 | P@5 | P@10 | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Direct | 0.20 | 0.333333 | 0.20 | 0.10 | 0.20 | 0.60 | 0.60 | 0.60 | **0.40** |
| Useful | 0.80 | 0.60 | 0.36 | 0.22 | 0.80 | 1.00 | 1.00 | 1.00 | **0.90** |

| Query | Direct ranks Top10 | Useful ranks Top10 | RR Direct | RR Useful | nDCG@10_pool |
|---|---|---|---:|---:|---:|
| dev-night_horn-3 | 1,2 | 1,2 | 1 | 1 | 1.000000 |
| dev-driving_age-2 | không có | 1 | 0 | 1 | 0.242076 |
| dev-red_light-2 | không có | 2 | 0 | 0.5 | 0.386853 |
| V3-D05 | 2 | 1,2,10 | 0.5 | 1 | 0.770251 |
| V3-D07 | 2,3 | 1,2,3,7 | 0.5 | 1 | 0.811565 |

nDCG@10_pool macro **0.642149**,5valid/0null. Gain2^rel−1, discountlog2(rank+1),
IDCG chỉ accepted pool riêng query. Trường hợp IDCG0 được test null, không
gộp0; dữ liệu thật cả5 có Useful-positive. **Recall/AP/MAP corpus=null**,
**metrics chính thức50query=null**. Không suy pool đã đủ mọi positive.

Run **staging/subset-v5-five-query-evaluation-001/**, manifest SHA:
`71b249f6626120cf2137ab86675874f6e6131438758df8ca64e9faa0dbbff4d1`.

- `results.md`:5bảng Top10 đầy đủ score/type/citation/label/relation/completeness,
  user reason, vị trí evidence target/context/required-read và nguyên văn positive.
- `metrics.per_query.jsonl`: P/Hit/RR, counts, denominator, DCG/IDCG từng query.
- `macro.contributions.jsonl`:10dòng đóng góp5query×2cách đọc để kiểm phép cộng.
- `frozen.run.jsonl`:50dòng nguyên object từ frozen batch, không ranking lại.
- `accepted.selected.jsonl`:53quyết định nguyên object, không tạo event mới.
- `outside_positives.jsonl`:3positive đã accepted ngoài10, rank deep cũ.
- `config.snapshot.json`, `queries.jsonl`, `input_validation.json`, `report.json`
  và manifest/sidecar giữ binding và giới hạn.

## Phân tích căn cứ và lỗi, không chấm lại

**Còi ban đêm:** hai direct ở rank1/2. Luật36 A21K2 có quy tắc và ngoại lệ xe
ưu tiên; NĐ168 A6K1đ có target và context đúng ô tô. Rank3 cùng hành vi nhưng
dành mô tô nên0. Các bảng tốc độ và hành vi đèn/giảm tốc không trả lời query.

**Tuổi lái mô tô:** Useful rank1 chỉ là chế tài chưa đủ tuổi. Direct đã biết
Luật36 A59K1b ở **rank15**, label2/partial; TT35 A28K1 dependency-only ở
**rank49**, label1/partial. Đây là miss Top10 của positive trong pool đã rà,
không là thiếu nguồn. Cần ghép phân loại hạng GPLX để khớp loại xe; mốc16tuổi
xe gắn máy và tuổi tối đa ô tô không thay thế được. Không tự ghép và gán full.

**Đèn đỏ:** pool không có label2, vì vậy Direct0; Useful có QCVN rule6.4 ở
rank2, chỉ hỗ trợ hiểu đèn mũi tên. NĐ168 A6K1a ở **rank20** là label1 qua
required-read, own target nói về biển/vạch. Quote trong detail trỏ A6K9b,
lead A6K9 và A6K16b; không dùng khung phạt context A6K1 làm mức phạt đèn đỏ.
Ba positive ngoài10 nói trên là rank đã lưu phiên7, không tìm sâu mới.

Khảo sát bổ sung có mục tiêu trên **138target frames**: không có own
`record.unit_id` trùng ba dependency A6K9b/A6K9/A6K16b đã chỉ rõ, trong khi
nội dung có trong required-read. Bằng chứng/hash/method ở
`checks/membership.observations.json`. Đây là phân biệt membership ở cấp unit
đó với nguồn phụ thuộc, không kết luận cả corpus thiếu đáp án hoặc gán nhãn
cho target khác chưa chấm. Chưa chứng minh coverage đầy đủ ngoài pool.

**60km/h:** hàng V=60/35m rank2 direct partial; dependency thời tiết bất lợi
rank1 và quy tắc chung rank10 chỉ Useful. Hàng60<V≤80 không bao gồm60; bảng
tốc độ không phải bảng khoảng cách. Giữ điều kiện khô ráo/đường/tầm nhìn của
lead, không dùng35m vô điều kiện hoặc chuyển label1 thành direct.

**80/81km/h:** hai hàng55m (60<V≤80) và70m (80<V≤100) ở rank2/3, mỗi hàng
label2/partial; phải kết hợp cả hai và điều kiện áp dụng. Hit@1 Useful=1 từ
dependency không là chứng minh trả đủ phép so sánh. Các hàngV=60 hoặc100<V≤120,
quy định tốc độ thay khoảng cách đều không trả lời được query này.

Reason lỗi loại xe/hành vi/ranh giới/khu vực giữ nguyên từng cặp trong bảng,
không sửa nhãn theo từ khóa. Không có blocker input/missing judgment ở5query;
coverage toàn corpus, nguồn/edition/applicability vẫn pending riêng.

## Kiểm chứng thực thi và replay

Đã chạy (exit0):

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_evaluation build --config config/subset_five_query_evaluation.v1.json --run-dir staging/subset-v5-five-query-evaluation-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_evaluation validate --manifest staging/subset-v5-five-query-evaluation-001/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_evaluation build --config config/subset_five_query_evaluation.v1.json --run-dir staging/source-session11-checks-001/evaluation-replay
```

Đặt biến môi trường opt-in như [handoff](../handoff/Subset_Five_Query_Evaluation.md),
rồi chạy:

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest -v tests.test_subset_evaluation tests.test_evaluation tests.test_query_review.QueryReviewTests tests.test_subset_labels.TypedLabelsTests tests.test_query_labels.FeedbackTests tests.test_subset_calibration tests.test_subset_review tests.test_composition_review
```

**90tests pass/0skip**,33.557s. Trước đó31unit/math/regression pass. Fixture
synthetic có phép tính tay độc lập: nhiều/graded positive, cutoff10/11, hai
ngưỡng, không hit, không positive, IDCG0, kết quả ngắn/empty, macro giữ0.
Từ chối thiếu/trùng/proposal nhãn, sai binding query/dataset/type/hash.
**12mutation output đã reseal bị từ chối**, gồm rank/score/query/type/label
binding/proposal/missing evidence, metric và phạm vi giả. Bad config bị từ
chối trước khi tạo output. Test artifact dùng input thật đã validate một lần
cho các bản sao private; CLI validate chạy đầy đủ độc lập, không bypass.

Replay **13file gồm manifest/sidecar byte-identical**; kiểm Fraction độc lập
10trường hợp (5query×2cách đọc) khớp số đếm/P/Hit/RR. Không dùng test count làm chất lượng
pháp lý/retrieval. Logs và bằng chứng:
`staging/source-session11-checks-001/` (viết tắt `checks/` trong báo cáo):
`tests.final.log`, `aggregate.input_validation.json`, `build.log`, `validate.log`,
`replay.log`, `replay.summary.json`, `arithmetic.independent.jsonl`,
`artifacts-001/negative_checks.jsonl`, `preservation.final.json`, `diff-check.log`.

## File thay đổi và phần tiếp theo

Thêm adapter `src/subset_evaluation.py`, tests tương ứng, config ghim,
contract mới và handoff/báo cáo này. STATUS thêm trạng thái hiện tại, giữ toàn
lịch sử. Không sửa evaluator/validator hash-bound cũ, không đổi dữ liệu/nhãn.
Preservation đối chiếu baseline và giữ nguyên lịch sử STATUS; git diff --check
và whitespace các file mới phải đạt trước bàn giao (receipt trong checks).

Chưa kiểm máy/OS khác, chưa chạy toàn suite ingestion hoặc inference: không
thay phần đó và không cần để kiểm phép đo này. Không cài dependency mới.
Chưa chạy Dense/Hybrid/Reranker, index/model/UI/API hoặc chỉnh portability.
Chưa có coverage toàn corpus hay đánh giá độc lập; không nâng hiệu lực pháp lý.

Đề xuất sau phiên (chưa thực hiện): rà membership trực tiếp chế tài đèn đỏ và
dependency phân hạng GPLX theo phạm vi riêng; chọn lô nhãn tiếp độc lập với
tuning; định nghĩa kiểm đủ câu trả lời nhiều record cho80/81. Nếu muốn so các
phiên bản, cần cùng dataset/query/qrels/binding và protocol đã chốt; năm query
chọn sẵn, AI-assisted này chưa đủ cho tuyên bố so sánh tổng quát.
