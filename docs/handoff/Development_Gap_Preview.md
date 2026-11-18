# Phiên 12 — mở và chạy lại preview khoảng trống development

Run giao **staging/development-gap-preview-002/**; snapshot2025-01-01.
Mở `preview.md` để đọc nguyên văn/context/search/encoder input, closure đầy đủ
và source locators. `red.reads.jsonl` là target đèn đỏ mới; `age.reads.jsonl`
giữ target tuổi cũ và mở rộng required-read. Chưa nhập vào dataset/index.

- `membership.proposals.jsonl`: disposition ba vấn đề, IDs/required IDs/blocker.
- `graph.projection.jsonl`, `source_spans.jsonl`:31nút/41span của projection.
- `distance.evidence_cases.jsonl`:11tập bằng chứng,2đạt/9không đạt yêu cầu khai báo.
- `distance.encoder_inputs.jsonl`: token evidence của các record TT38 hiện có;
  full279tokens giữ hai view237/44, không làm view thành target.
- `consumer.validation.json`, `report.json`, `manifest.json/.sha256`.
- Companion `staging/source-session12-checks-001/`: source review ảnh PDF,
  delta membership, replay, tests và preservation. Không xóa checks trước khi
  đóng gói dependency bằng chứng theo config; preview chưa là ZIP portable.

## CLI từ repo root trên môi trường hiện có

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.development_gap_preview validate --manifest staging/development-gap-preview-002/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.development_gap_preview build --config config/development_gap_preview.v1.json --run-dir staging/development-gap-preview-NEW
```

NEW phải chưa tồn tại dưới staging. Dùng đúng inputs đã ghim; source DOCX
NĐ168 session2-001, Luật36 stage4-docx-005, dataset006 và evaluation001.
Build chỉ dựng preview/tính token offline, không encoder inference hoặc index.
Validate tái dựng từ inputs và token cache, không đo lại metrics/đổi nhãn.
Replay build đã đo lại tokenizer thật và giữ17file byte-identical.

Không chọn latest, chạy correction lần nữa hoặc thay nhánh HTML. Nguồn thiếu/
hash sai phải khôi phục đúng artifact, không sửa seal. Lỗi trả exit1. Nguồn/
edition/applicability pending không được biến thành verified vì preview đạt.

Run001 giữ lịch sử lỗi gọi builder với absolute text_ref; source prototype
được giữ trong checks. Bản giao002 truyền đường dẫn tương đối đúng contract,
không sửa reader/builder/parser cũ hoặc workaround portability toàn dự án.

## Kiểm thử

Test Stage6 cũ import helper bằng tên ngắn nên cần thêm thư mục tests vào
PYTHONPATH trong process PowerShell này; không sửa test/helper đã chốt.
Chọn các lớp fixture cũ; real tests của preview mới được bật riêng.

```powershell
$env:PYTHONPATH=(Join-Path (Get-Location).Path 'tests')
$env:VTLS_GAP_PREVIEW_MANIFEST='staging/development-gap-preview-002/manifest.json'
$env:VTLS_GAP_PREVIEW_CHECKS='staging/source-session12-checks-NEW/artifacts'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest -v tests.test_development_gap_preview tests.test_session4 tests.test_stage6_points.PointBuilderTests tests.test_stage6.BuilderTests tests.test_stage6.EncoderTests tests.test_subset_candidate tests.test_subset_evaluation.DiagnosticMathTests tests.test_subset_evaluation.TypedInputTests
```

Trong phiên:70tests/0skip,11mutation preview đã reseal bị từ chối; fixture còn
kiểm source/header/cell/proof/owner/điều kiện/ranh giới. Không dùng số test để
tuyên bố xác minh pháp luật hoặc retrieval. Không cần download model/dependency.

Các việc trước candidate sau chỉ là đề xuất: nạp1target mới/closure vào adapter
candidate có version, bổ sung các graph nodes/proof mounts còn thiếu và kiểm
trùng vị trí; giữ nguyên trạng thái pending. Không tự chuyển59labels/qrels
sang dataset/hash mới. Record ID tuổi không đổi nhưng read closure thay đổi
vẫn cần binding phiên bản mới. Không tự build candidate hoặc index ở lượt này.

[Contract](../design/Development_Gap_Preview_v1.0.md),
[báo cáo và giới hạn](../reviews/Source_Session12_Gap_Preview_Verification.md).
