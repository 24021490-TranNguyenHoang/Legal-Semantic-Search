# Accepted annotations cho calibration subset v5

Contract **subset-v5-accepted-labels.v1**, 05/11/2026. Snapshot pháp luật vẫn
**2025-01-01**. Kế thừa rubric v1.2 và
[contract submission phiên8](Subset_V5_Calibration_Submission_v1.0.md).
Không sửa schema/validator chunk-only v1 hoặc các payload đã phát hành.

## Quyền quyết định và metadata

Người dùng đã xác nhận22phản hồi có ChatGPT hỗ trợ, cung cấp reviewer_ref và
thời điểm rà, đồng thời yêu cầu nhập đúng20nhãn số. Đây là quyết định thực tế
về relevance trong phạm vi mẫu, không phải legal review hoặc duyệt500nhãn.
Origin là **user_reviewed_ai_assisted**, ai_assisted=true, blind=false,
independent=false; không đổi thành nhãn agent tự accepted hoặc chấm độc lập.

`reviewer_ref` là mã tham chiếu mờ do người dùng cung cấp. Giá trị hiện tại
`## CAL-039998018b` được giữ nguyên, dù giống tiêu đề/mã calibration. Không suy
ra tên người, không coi đây là yêu cầu chỉ nhập một cặp. Phạm vi vẫn22cặp như
người dùng xác nhận. Không thêm yêu cầu xác thực danh tính/chữ ký/phân quyền.

Thời gian đầu vào **8:00 AM 5/11/2026 GMT +7** được hiểu ngày/tháng/năm,
chuẩn hóa **2026-11-05T01:00:00Z** (08:00+07:00). Metadata capture giữ cả chuỗi
gốc và cách chuẩn hóa. reviewed_at khác giờ agent tạo snapshot/imported_at.

## Snapshot và lineage

`src.subset_labels snapshot` kiểm seal và validator phiên8 trước khi ghi output
mới dưới staging. Chỉ thay reviewer_ref/reviewed_at trong submission; items,
relevance/reason, IDs, hashes, bindings, relation/completeness/evidence giữ nguyên.
Feedback/provenance mới được bind SHA, giữ parent manifest/submission/provenance
và metadata capture; không sửa snapshot001 hoặc template/proposal đã seal.
Reader phiên8 vẫn chỉ validate; trạng thái METADATA_COMPLETE_NOT_ADMITTED không
đồng nghĩa đã nhập nhãn.

## Biểu diễn accepted và pending

Adapter `src.subset_labels` hỗ trợ đúng các type:
`chunk.v1`, `table-retrieval.v1`, `source-retrieval.v1`. Giữ record_id thật;
không đổi table/whole thành chunk_id hoặc source-only thành ranked target.

- `accepted.annotations.jsonl`: chỉ các item relevance nguyên0/1/2,
  status=accepted; giữ relation/completeness/reason/evidence, record_type,
  query/record/proposal hash, binding dataset/index/query/batch và metadata reviewer.
- `pending.annotations.jsonl`: hai null, status=pending,
  relation=completeness=uncertain. Có xác nhận giữpending, không là missing feedback.
- `qrels.accepted.jsonl`: qrel **mới, typed**, gồm query_id/record_id/record_type/
  relevance/annotation_id/binding; một-một với accepted annotations. Không chứa
  null; không thay qrels lịch sử và không đưa trực tiếp vào scorer v1 chunk-only.
- Evidence locators và native spans/cell IDs giữ nguyên; detail/provenance/source
  snapshot tiếp tục được tham chiếu bằng SHA. Nhãn1 giữ supporting_target hoặc
  dependency_only, không tự đổi thành direct_target hoặc nâng relevance2.
- `receipt.json`: nguồn snapshot/provenance/manifest, import_id, counts,
  metadata reviewer và imported_at thực tế, phạm vi22cặp/metrics=null/coverage=false/
  legal_verified=false. Source/edition/applicability không được promote.

Identity dùng phiên bản contract này: import_id hash canonical toàn submission;
annotation_id hash typed decision + import_id + SHA submission, loại đường dẫn
vật lý source khỏi identity. Không đổi công thức DDD unit/chunk ID.

## Chống nhập lặp và kiểm chứng

Một snapshot không được thiếu/trùng Calibration ID hoặc cặpquery/record.
Validator replay projection từ submission có metadata và evidence hợp lệ,
so khớp **toàn bộ** accepted/pending/qrels/receipt; checksum wrapper không đủ để
làm nhãn sai pass. Kiểm cả manifest và payload thật của dataset/index/query/batch,
không build/search/reindex. Không dùng scorer làm đường nhập.

Gọi admit lại vào **cùng run** với cùng source/import_id trả ALREADY_IMPORTED,
newly_imported=0, không ghi file. Run có input khác bị từ chối, không ghi đè.
`--prior-manifest` kiểm artifact đã nhận và từ chối cặp trùng/xung đột trước
tạo output mới; chưa hỗ trợ tự supersede hoặc merge quyết định trái nhau.
Không có registry toàn máy hay tự tìm run mới nhất: khi ghép bộ nhãn sau này,
phải đưa artifact trước làm prior. Replay vào run riêng là bản sao kiểm chứng
cùng import_id, không phải20nhãn mới để cộng dồn.

Metadata hợp lệ chỉ mở đường nhập relevance theo xác nhận thực tế. Chấp nhận
20nhãn này không chấp nhận500cặp, qrels completeness, coverage50query hoặc corpus.
Metrics50query vẫn null; chưa gọi metric scorer. Không thay query/ranking hoặc
chạy model/index/UI/API.

## CLI

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_labels snapshot --parent-manifest staging/subset-v5-calibration-submission-001/manifest.json --metadata staging/source-session8-acceptance-checks-001/metadata.received.json --run-dir staging/subset-v5-calibration-submission-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_calibration --submission staging/subset-v5-calibration-submission-002/submission.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_labels admit --submission staging/subset-v5-calibration-submission-002/submission.json --run-dir staging/subset-v5-accepted-labels-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_labels validate --manifest staging/subset-v5-accepted-labels-002/manifest.json
```

Snapshot cần run chưa tồn tại; admit cùngrun chỉ no-op khi kiểm input/artifact
đúng. Lỗi có exit1; thành công/no-op exit0. Fixtures synthetic tách dữ liệu thật.
