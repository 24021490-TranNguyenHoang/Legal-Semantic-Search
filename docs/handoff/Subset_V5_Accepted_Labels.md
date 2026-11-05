# Bàn giao 20 accepted labels calibration subset v5

Ngày05/11/2026; snapshot pháp luật **2025-01-01**. Chỉ22phản hồi đã được người
dùng xác nhận có ChatGPT hỗ trợ; không phải chấm độc lập/blind, legal review,
duyệt500cặp hoặc qrels completeness của50query. Metrics chính thức vẫnnull.

## File cần mở

| Nội dung | Đường dẫn từ repository root |
|---|---|
| Snapshot mới có metadata | staging/subset-v5-calibration-submission-002/submission.json |
| Capture thời gian gốc và mã reviewer | staging/subset-v5-calibration-submission-002/metadata.received.json |
| Lineage/provenance | cùng run: lineage.json, provenance.json |
| 20 accepted annotations typed | staging/subset-v5-accepted-labels-002/accepted.annotations.jsonl |
| 2 pending annotations | cùng run: pending.annotations.jsonl |
| Qrels typed riêng,20nhãn số | cùng run: qrels.accepted.jsonl |
| Receipt nhập | cùng run: receipt.json, manifest.json |
| Bảng dễ đọc22cặp và kiểm chứng | staging/source-session8-acceptance-checks-001/accepted_review.md |
| Báo cáo checks/replay/negative | staging/source-session8-acceptance-checks-001/artifacts-001/validation_report.json |

Reviewer_ref giữ đúng **`## CAL-039998018b`**, mã tham chiếu mờ do người dùng
cung cấp, không suy ra tên người hoặc thu hẹp phạm vi chỉ một cặp.
Reviewed_at **2026-11-05T01:00:00Z** =08:00GMT+7 ngày05/11/2026; khác giờ import.
20nhãn gồm7nhãn2/6nhãn1/7nhãn0. Type counts11chunk/6table-row/3whole-source.
Nhãn1 giữ2supporting_target/4dependency_only; completeness/evidence giữ nguyên.

Hai cặp **CAL-a46415f601**, **CAL-b69c61257d** vẫnnull/pending. Cặp thứ hai
giữ bất đồng với proposal cũ2; không sửa proposal hoặc đổi null thành0.

## Validate và chạy lại

Từ root repo với môi trường hiện hành; không dùng scorer chunk-only v1:

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_calibration --submission staging/subset-v5-calibration-submission-002/submission.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_labels validate --manifest staging/subset-v5-accepted-labels-002/manifest.json
# Cùng run/cùng input: no-op, newly_imported=0; không ghi file hoặc thêm nhãn.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_labels admit --submission staging/subset-v5-calibration-submission-002/submission.json --run-dir staging/subset-v5-accepted-labels-002
# Replay độc lập: dùng tên NEW chưa tồn tại, cùng import_id; không cộng thành40nhãn.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_labels admit --submission staging/subset-v5-calibration-submission-002/submission.json --run-dir staging/subset-v5-accepted-labels-NEW
```

Snapshot đã seal: không điền lại file002 hoặc001. Nếu cần metadata/decision khác,
phải có phản hồi thực tế mới và snapshot/lineage tương ứng. Adapter hiện không
tự supersede/merge quyết định xung đột. Khi nhập vào lịch sử nhãn đã có, truyền
`--prior-manifest` để phát hiện trùng/xung đột trước khi ghi; không có registry
toàn máy và không tự chọn run mới nhất.

Kiểm thử fixture và hồi quy:

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_subset_labels tests.test_subset_calibration tests.test_subset_review tests.test_composition_review tests.test_evaluation -v
```

Mặc định58test thực thi,1artifact test opt-in được skip. Để chạy cả59test với
artifact thật và giữ output kiểm riêng, đặt biến chỉ trong process test:

```powershell
$env:VTLS_SUBSET_ACCEPTED_MANIFEST = 'staging/subset-v5-accepted-labels-002/manifest.json'
$env:VTLS_SUBSET_LABEL_CHECKS_DIR = 'staging/subset-labels-check-NEW'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_subset_labels tests.test_subset_calibration tests.test_subset_review tests.test_composition_review tests.test_evaluation -v
Remove-Item Env:VTLS_SUBSET_ACCEPTED_MANIFEST
Remove-Item Env:VTLS_SUBSET_LABEL_CHECKS_DIR
```

Trong phiên đã chạy59test/0skip,20private mutation bị từ chối, replay payload
giống byte; nhập cùng run không ghi file, nhập lại với prior bị từ chối trước
tạo output. Đây là kiểm kỹ thuật, không phải metric retrieval hoặc legal review.

Prototype **subset-v5-accepted-labels-001** giữ lịch sử trước khi siết so sánh
JSON bool/int/float; bản giao là **002**. Ba file accepted/pending/qrels của hai
run giống byte, cùngimport_id, không là hai đợt nhận nhãn. Source validator
prototype được lưu tại checks/subset_labels.prototype.py. Replay kiểm cuối ở
checks/artifacts-001/replay; không dùng private mutation làm nhãn thật.

Các dependency source/review/template và dataset/index/query phải đúng manifest
đã ghim. Qrels mới dùng record_id/record_type, không sửa qrels cũ hoặc đổi record
type để nạp vào scorer cũ. Bước sau về metrics cần đánh giá độ đầy đủ nhãn và
coverage thực tế theo contract; chưa được suy từ mẫu calibration này.
