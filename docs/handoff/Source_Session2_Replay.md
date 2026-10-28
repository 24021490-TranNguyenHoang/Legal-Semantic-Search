# Bàn giao phiên 2 — replay hữu hạn

28/10/2026. Snapshot2025-01-01; tất cả output pending/agent_review,
release=false. Đọc [báo cáo](../reviews/Source_Session2_Verification.md) trước;
đặc biệt đính chính 4.1 không phải khác biệt edition như báo cáo phiên 1.

## Mở hồ sơ trước

- 86 trường NĐ168: `staging/nd168-field-review-003/fields.review.csv` (CSV chuẩn,
  hai giá trị nguyên văn và JSON spans/evidence); JSONL cùng tên giữ typed fields.
- DOCX mới: `staging/nd168-docx-session2-001/sources/168.2024.NĐ-CP.docx`;
  corrections.jsonl, revision_manifest.json, unit_crosswalk.jsonl,
  span_crosswalk.jsonl, graph_delta.json. Raw/phiên1 không đổi.
- TT35: `staging/source-session2-checks-002/tt35.before_after.md`,
  `staging/tt35-owner-tables-002/tables_preview.md` và `tr_*.read.json`.
  File read trả toàn owner/table/cell/dependencies, không chỉ encoder view.
- QCVN: `staging/qcvn-region-recovery-004/review.md`, source_differences.json,
  regions.pending.jsonl, transcriptions/*/normalized.txt + metadata.json;
  continuation.before_after.jsonl (11), remaining_940.jsonl (929).
- Ảnh đối chiếu: `staging/source-session2-001/visual/`; ảnh cũ reuse nằm tại
  `staging/source-revision-session1-001/visual/`. OCR hai caption trong
  `staging/source-session2-001/label-ocr/` chỉ là draft, không human decision.

## Dependency thật

Chạy từ thư mục repo, Windows PowerShell, Python3.11.9/.venv-stage1 đã cài
requirements theo README. Không gọi encoder/inference, chỉ tokenizer/PyVi CPU
cục bộ theo config preview cũ; không tải model weights. OCR không cần để replay
vì dùng receipt/draft đã lưu. Không có Word/LibreOffice trên PATH đã thử.

Các input không nằm trong Git: giữ `data/raw/`, `source-session2-001` (ảnh/hash),
nd168-docx-corrected-002, nd168-html-full-002, source-revision-checks-002,
tt35-preview-005, circular-priority-006, tt35-source-regions-001 và dependency
tt35-full-layout-001, seven-source-handoff-001; qcvn-gazette-extraction-001,
qcvn-source-regions-001, qcvn-rule-graph-003, qcvn-doc-assessment-003,
source-revision-session1-001 và PDF/receipt ở seven-source-completion-001.
Đường dẫn chính xác/hash nằm trong bốn config mới và manifest của từng input;
đây là dependency tường minh, không cần tìm run “mới nhất”. PDF NĐ168 dùng
capture05 bên trong bm25-baseline-v1-001/dataset/evidence. Các nguồn/caches này
chỉ được đọc; không tải/extraction lại PDF để replay.

Staging chưa được Git quản lý: clone code riêng không có đủ input để chạy ngay.
Chưa tạo ZIP mới trong phiên này; các ZIP bàn giao trước giữ nguyên.

## Lệnh đã chạy

Run phải chưa tồn tại; khi tự chạy lại, đổi tên output sang `*-user-001` hoặc
tên mới khác. Không ghi đè run liệt kê dưới đây.

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.nd168_field_review --config config/nd168_field_review.v1.json --run-dir staging/nd168-field-review-003
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_revision --config config/nd168_docx_revision.session2.v1.json --run-dir staging/nd168-docx-session2-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.ingestion.tt35_owner_tables --config config/tt35_owner_tables.v1.json --run-dir staging/tt35-owner-tables-002
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.qcvn_region_recovery --config config/qcvn_region_recovery.v1.json --run-dir staging/qcvn-region-recovery-004
```

Kết quả: lần lượt86field (67/18/1),18correction/0blocker,
8owner/11table/590cell/84view/quarantine0,6region/24cell/11dòngB18/929pending.
Replay đã chạy cùng lệnh với output review004, nd168-session2-002,
tt35-owner-tables003, qcvn-region-recovery005;17payload giữ hash, không so timestamp.

Validate không ghi output, có thể chạy trực tiếp các run đã seal:

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.ingestion.tt35_owner_tables --config config/tt35_owner_tables.v1.json --run-dir staging/tt35-owner-tables-002 --validate
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.qcvn_region_recovery --config config/qcvn_region_recovery.v1.json --run-dir staging/qcvn-region-recovery-004 --validate
```

Checker tổng hợp đã chạy (đổi output khi tự chạy lại):

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m tests.check_session2_artifacts `
  --review staging/nd168-field-review-003 --review-config config/nd168_field_review.v1.json `
  --nd168 staging/nd168-docx-session2-001 `
  --tables staging/tt35-owner-tables-002 --tables-config config/tt35_owner_tables.v1.json `
  --qcvn staging/qcvn-region-recovery-004 --qcvn-config config/qcvn_region_recovery.v1.json `
  --baseline staging/source-session2-001/preservation.baseline.json `
  --replay-review staging/nd168-field-review-004 --replay-nd168 staging/nd168-docx-session2-002 `
  --replay-tables staging/tt35-owner-tables-003 --replay-qcvn staging/qcvn-region-recovery-005 `
  --run-dir staging/source-session2-checks-002
```

Kết quả exit0: graph/FK/spans/ZIP/XML/consumer/proof/replay/baseline đạt;
13mutation bị từ chối, gồm4bản private QCVN được tính lại seal. Các private
negative artifacts cố ý không hợp lệ; không dùng chúng làm input pipeline.
Checker mới chạy lại sau cập nhật tài liệu ở `source-session2-checks-003`.

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_session2_sources tests.test_source_revision tests.test_qcvn_doc_assessment tests.test_full_ingestion tests.test_circular_priority tests.test_stage3 tests.test_stage4 -v
git diff --check
```

71tests pass; kiểm thử không tuyên bố legal verified. Lỗi thực tế: thiếu input
manifest/raw/model tokenizer cache thì dừng với exception/nonzero, không chọn
run/source khác. Sai binding hoặc thiếu whole-read dependency là lỗi kỹ thuật;
scope/edition/applicability pending là trạng thái rà soát khác, không tự sửa
thành accepted. Chưa thử máy khác hoặc render DOCX; chưa nhập dataset/đổi ứng dụng.
