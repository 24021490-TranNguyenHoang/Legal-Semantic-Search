# Chạy lại chẩn đoán BM25 năm query — phiên 11

Run giao: **staging/subset-v5-five-query-evaluation-001/**.
Scope: `five_query_development_diagnostic`, snapshot pháp luật2025-01-01.
Đây là phép đo năm query đã chọn với nhãn người dùng rà có AI hỗ trợ,
không độc lập/blind, không phải metrics chính thức50query/toàn corpus.

Mở `results.md` trong run: macro/per-query, toàn50Top10 có score/type/citation,
53 quyết định đã accepted và vị trí căn cứ positive,3positive ngoài Top10,
reason nguyên văn và giới hạn trả lời. `report.json` là tổng hợp máy đọc;
`metrics.per_query.jsonl` có counts/numerators/denominators,
`macro.contributions.jsonl` có đóng góp từng câu vào trung bình5câu.

## Chạy từ repository

Dùng môi trường `.venv-stage1` hiện có, từ repo root. Không cài dependency mới,
không load engine/model hoặc chạy lại ranking. Các dependency của validator
review/consumer phải giữ đúng cấu trúc/hash đã ghim; đây chưa là gói portable
độc lập, chưa kiểm OS/máy khác. Không sửa lỗi portability lịch sử trong lượt này.

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_evaluation validate --manifest staging/subset-v5-five-query-evaluation-001/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_evaluation build --config config/subset_five_query_evaluation.v1.json --run-dir staging/subset-v5-five-query-evaluation-NEW
```

NEW phải là thư mục chưa tồn tại dưới staging; không build vào001/replay cũ.
Build ở đây là **tính và đóng gói báo cáo từ frozen run**, không build BM25.
Input sai/thiếu/proposal thay accepted trả exit1 trước khi tạo output; không
fallback labels/index. Nếu hash/code binding sai, lấy đúng artifact/commit,
không sửa checksum để vượt validator. Manifest mới bind code/contract/helper;
giữ phiên bản đã chốt để replay nguyên byte.

Đầu vào duy nhất trong config:

- Batch `staging/bm25-subset-v5-batch-002/manifest.json`.
- Pool `staging/subset-v5-query-review-002/manifest.json`.
- Aggregate `staging/subset-v5-label-aggregate-001/manifest.json`.

Dataset `vtls-subset-experimental.v5-candidate.1`, index
`vtls-bm25s-subset.v1`; năm query giữ nguyên toàn object/hash/batch_group.
Không sử dụng trực tiếp scorer v1 chunk-only và không nhập annotation mới.
Hai pending V3-D02 vẫn ngoài tập; query đèn đỏ Direct0 vẫn ở macro, không loại.

## Kiểm thử và replay

```powershell
$env:VTLS_FIVE_QUERY_EVAL_MANIFEST='staging/subset-v5-five-query-evaluation-001/manifest.json'
$env:VTLS_FIVE_QUERY_EVAL_CHECKS='staging/source-session11-checks-NEW/artifacts'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest -v tests.test_subset_evaluation tests.test_evaluation tests.test_query_review.QueryReviewTests tests.test_subset_labels.TypedLabelsTests tests.test_query_labels.FeedbackTests tests.test_subset_calibration tests.test_subset_review tests.test_composition_review
```

Trong phiên đã chạy90test/0skip, không bật opt-in integration khác. Test artifact
mới dùng input đã validate thật một lần rồi kiểm bản sao riêng có reseal;
CLI validate vẫn đọc/validate lại input đầy đủ. Không chỉnh dữ liệu thật.
Replay đã chạy vào `staging/source-session11-checks-001/evaluation-replay/`,
13file gồm manifest/sidecar giống byte. Logs, phép kiểm Fraction độc lập và
preservation ở `staging/source-session11-checks-001/`.

Direct=2; Useful>=1 gồm supporting/dependency. P@k mẫu sốk, MRR@10/macro trên
đúng5query. nDCG@10_pool graded chỉ là diagnostic pool, IDCG0=null. Recall/AP/MAP
corpus và metrics chính thức50query vẫn null. Không dùng Hit đơn lẻ suy đủ
câu80/81 hoặc bỏ điều kiện đường/tầm nhìn của bảng khoảng cách.

Xem [contract](../design/Subset_Five_Query_Evaluation_v1.0.md) và
[báo cáo thực thi](../reviews/Source_Session11_Five_Query_Evaluation_Verification.md).
Bước tiếp theo chỉ đề xuất trong báo cáo; chưa tuning, review thêm hoặc đổi bản.
