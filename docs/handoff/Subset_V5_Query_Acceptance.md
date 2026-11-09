# Phiên 10 — phản hồi và accepted labels năm query

Môi trường đã thử: Windows, Python từ `.venv-stage1`, chạy tại thư mục repo.
Không cần tải mô hình, chạy BM25 lại hoặc dùng scorer chunk-only.

- Submission: `staging/subset-v5-query-submission-002/manifest.json`.
- Batch mới: `staging/subset-v5-query-accepted-001/manifest.json`.
- Aggregate: `staging/subset-v5-label-aggregate-001/manifest.json`.
- Capture/checks: `staging/source-session10-checks-001/`.
- Bản 001 submission là lần ghi thử chưa hoàn tất (thiếu thư mục responses),
  giữ lịch sử; không dùng để import. Bản bàn giao là 002 có seal hợp lệ.

## Validate

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.query_labels validate-submission --manifest staging/subset-v5-query-submission-002/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.query_labels validate --manifest staging/subset-v5-query-accepted-001/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.query_labels validate-aggregate --manifest staging/subset-v5-label-aggregate-001/manifest.json
```

## Tái tạo ở run mới

Thay hậu tố REPLAY bằng thư mục chưa tồn tại; giữ nguyên input đã ghim.
Adapter kiểm integrity consumer và các manifest; đây là kiểm dữ liệu read-only,
không load encoder hoặc chạy ranking. Các dependency nguồn của consumer phải
còn truy được trong repo theo manifest; chưa là gói portable độc lập.

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.query_labels submit --review-manifest staging/subset-v5-query-review-002/manifest.json --prior-manifest staging/subset-v5-accepted-labels-002/manifest.json --feedback staging/source-session10-checks-001/feedback.received.json --run-dir staging/subset-v5-query-submission-REPLAY
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.query_labels admit --submission-manifest staging/subset-v5-query-submission-REPLAY/manifest.json --prior-manifest staging/subset-v5-accepted-labels-002/manifest.json --run-dir staging/subset-v5-query-accepted-REPLAY
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.query_labels aggregate --review-manifest staging/subset-v5-query-review-002/manifest.json --batches staging/subset-v5-accepted-labels-002/manifest.json staging/subset-v5-query-accepted-REPLAY/manifest.json --run-dir staging/subset-v5-label-aggregate-REPLAY
```

Batch replay là cùng import, không được cộng thêm vào aggregate đang có.
Cùng lệnh admit trỏ lại run accepted đã nhập trả newly_imported=0.
Không sửa input để vượt seal/code hash/binding. Khi thiếu dependency, khôi phục
đúng artifact/hash; không trỏ tùy tiện run khác. Mọi lỗi validation trả exit 1.

## Kiểm thử

```powershell
$env:VTLS_QUERY_LABELS_REAL='1'
$env:VTLS_QUERY_SUBMISSION='staging/subset-v5-query-submission-002/manifest.json'
$env:VTLS_QUERY_ACCEPTED='staging/subset-v5-query-accepted-001/manifest.json'
$env:VTLS_QUERY_CHECKS='staging/source-session10-checks-NEW/artifacts'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest -v tests.test_query_labels tests.test_query_review.QueryReviewTests tests.test_subset_labels.TypedLabelsTests tests.test_subset_calibration tests.test_subset_review
```

Kiểm artifact thật tạo các bản sai có seal mới bên trong checks, không sửa
bundle cũ. Không bật các opt-in integration khác khi chạy lệnh này.
Kết quả và giới hạn ở báo cáo `Source_Session10_Query_Acceptance_Verification.md`.
Hai pending CAL-a46415f601/CAL-b69c61257d của V3-D02 cần phản hồi riêng khi đủ
thông tin; phiên này không yêu cầu chấm lại 20 quyết định cũ hoặc toàn bộ pool.
