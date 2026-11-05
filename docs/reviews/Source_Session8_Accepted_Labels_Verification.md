# Tiếp tục phiên 8 — nhập nhãn calibration subset v5

Ngày **05/11/2026**, snapshot sản phẩm **2025-01-01**.
**SCOPED_LABELS_ACCEPTED / 20 ACCEPTED + 2 PENDING / METRICS_NULL**.
Phạm vi chỉ22phản hồi, có ChatGPT hỗ trợ; không độc lập/blind hoặc legal verified.

## Metadata và phạm vi thực tế

Giữ nguyên reviewer_ref người dùng chỉ định: **`## CAL-039998018b`**. Contract
chỉ cần tham chiếu do người dùng cung cấp, không yêu cầu tên pháp lý hoặc hệ
thống xác thực. Đây là mã mờ, không suy ra danh tính từ Git/Windows và không
diễn giải thành chỉ xác nhận một cặp. Người dùng đã xác nhận phạm vi22phản hồi.

Reviewed_at đầu vào **8:00 AM 5/11/2026 GMT +7**, chuẩn hóa
**2026-11-05T01:00:00Z**. Capture giữ nguyên chuỗi đầu vào/cách đổi múi giờ;
imported_at/agent_recorded_at là thời điểm kỹ thuật riêng, không thay giờ rà.
Snapshot pháp luật không đổi thành ngày rà.

HEAD đầu phiên **c77447bc1ae8b2d5a3369d37d1bf06ed504379c4**, Git sạch. Đã đọc
AGENTS/STATUS, báo cáo/contract phiên8, code/template/provenance và evaluation
contract thực tế. Không dùng SHA hoặc trạng thái Git trong chat làm bằng chứng.
Baseline **6.870 file** được ghi trước khi sửa; file list trong checks.

## Output mới và lineage

| Output | Run/file cuối |
|---|---|
| Snapshot metadata mới | staging/subset-v5-calibration-submission-002/submission.json |
| Phản hồi/capture/provenance/lineage | cùng run: feedback.received.json, metadata.received.json, provenance.json, lineage.json |
| Accepted annotations và qrels typed | staging/subset-v5-accepted-labels-002/accepted.annotations.jsonl, qrels.accepted.jsonl |
| Pending | cùng run: pending.annotations.jsonl |
| Receipt nhập | cùng run: receipt.json, manifest.json |
| Bảng dễ đọc | staging/source-session8-acceptance-checks-001/accepted_review.md |
| CLI/test logs, preservation | staging/source-session8-acceptance-checks-001/ |
| Replay/negative cuối | checks/artifacts-001/replay, negative_checks.jsonl, validation_report.json |

Đã so sánh snapshot001→002: **items của22cặp giống hoàn toàn**, top-level chỉ
reviewer_ref/reviewed_at đổi. Giữ binding, IDs, hashes, relevance/reason,
relation/completeness và evidence. Evidence ledger copy nguyên byte, các parent
manifest/submission/provenance có SHA riêng. Template/proposal/review run cũ
không đổi. Snapshot002 validate exit0, metadata không còn thiếu; reader cũ đúng
nghĩa vẫn báo METADATA_COMPLETE_NOT_ADMITTED trước lệnh nhập riêng.

## Nhập accepted đúng type và nguồn quyết định

Trước phiên này chỉ có reader submission, chưa có đường nhập typed accepted v5.
Adapter hẹp mới **src/subset_labels.py** dùng validator/quote/manifest helpers
cũ, thêm snapshot/admit/validate; không sửa scorer/validator v1 hoặc load model.
Contract bổ sung [accepted v1](../design/Subset_V5_Accepted_Annotations_v1.0.md).

| Phân loại | Số thực tế |
|---|---:|
| Accepted relevance2 /1 /0 | **7 /6 /7** |
| Accepted chunk /table-row /whole-source | **11 /6 /3** |
| Direct /supporting /dependency-only /unrelated | **7 /2 /4 /7** |
| Nhãn2 full /partial | **1 /6** |
| Null giữpending | **2** |
| Metrics chính thức50query | **null** |
| Coverage approved /legal verified | **false /false** |

Import_id **import_bb4ff7420b6b79b970e1dcdaed07b188ec3d87dcd92d44213a023c2217f65a3f**.
Accepted giữ origin=user_reviewed_ai_assisted, AI hỗ trợ, blind=false,
independent=false, reviewer/time thực tế do người dùng cung cấp; không đổi
nhãn1 thành direct hoặc nhận proposal thay phản hồi. Đây là acceptance relevance
cho mẫu22cặp, không là approval nguồn, edition, applicability hoặc500proposal.

Hai pending là **CAL-a46415f601** và **CAL-b69c61257d**. Cặp thứ hai vẫn khác
proposal2; giữ null/uncertain/uncertain. Hai cặp không xuất hiện trong qrels mới.
Qrels typed20cặp một-một với accepted, gồm nhãn0 đã đánh giá; không có null,
không fake chunk_id cho bảng/whole-source và không ghi vào qrels lịch sử.

## Chống nhập lặp, replay và kiểm chứng

- **59tests pass,0skip**:12fixture mới +1artifact test thực +46tests hồi quy.
  Default chưa truyền biến opt-in sẽ chạy58test/skip1; log cuối đã truyền đủ biến.
- **20private mutation bị từ chối**, kể cả reseal: thiếu/trùng accepted, sai
  binding/ID/type, mất relation/completeness/evidence, null→0 hoặc mấtpending,
  qrels trùng/null/bool, accepted bool/float, sai reviewer/giảindependent,
  mở rộngscope/tiêmmetrics. Một ca sửa cả feedback/checksum vẫn bị chặn vì
  snapshot chỉ được bổ sung metadata, không thay quyết định parent.
- `admit` lại đúng run002/cùng input trả **ALREADY_IMPORTED,newly_imported=0**;
  mọi file run giữ hash. Dùng run002 làm `--prior-manifest` bị từ chối duplicate
  trước tạo output mới. Không có registry ngầm hoặc tự supersede.
- Replay vào checks/artifacts-001/replay giữ accepted/pending/qrels giống byte,
  import_id/annotation IDs giống. Receipt có thời điểm nhập kỹ thuật riêng.
  Replay là bản sao cùng batch, không cộng thành40nhãn được nhận.
- Validator đọc lại manifest/payload dataset/index/query/batch đã ghim,
  query/record hash/type/evidence/spans/cells và rederive toàn bộ output từ
  submission; không chỉ tin checksum hoặc số lượng20.

Trong quá trình kiểm, đã siết so sánh canonical JSON để không coi True=1 hoặc
0.0=0 như equality của Python. Prototype accepted001 giữ nguyên, source tương
ứng lưu tại checks/subset_labels.prototype.py. Bản giao cuối là002. Ba payload
accepted/pending/qrels prototype→final giống byte và cùngimport_id; không nhập
thêm một tập quyết định khác. Không dùng validator hiện tại ép sửa manifest cũ.

## Lệnh thực thi và tự chạy lại

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_labels snapshot --parent-manifest staging/subset-v5-calibration-submission-001/manifest.json --metadata staging/source-session8-acceptance-checks-001/metadata.received.json --run-dir staging/subset-v5-calibration-submission-002
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_calibration --submission staging/subset-v5-calibration-submission-002/submission.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_labels admit --submission staging/subset-v5-calibration-submission-002/submission.json --run-dir staging/subset-v5-accepted-labels-002
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_labels validate --manifest staging/subset-v5-accepted-labels-002/manifest.json
```

Bốn lệnh trên đã chạy thành công; snapshot cần tên NEW khi tái tạo, không ghi
đè002. Logs/exits ở checks/executions.json và executions.final.json. Test CLI,
biến opt-in và receipt đầy đủ ở tests.final.receipt.json/tests.final.log.
[Handoff](../handoff/Subset_V5_Accepted_Labels.md) có lệnh test/replay/prior.

## Thay đổi và giới hạn

Thêm src/subset_labels.py, tests/test_subset_labels.py, contract/handoff/báo cáo
này; prepend STATUS và giữ lịch sử nguyên byte. Module phiên8
src/subset_calibration.py, các module producer/index/consumer/rubric hash-bound
giữ nguyên. Không thay schema DDD, dataset/index/query/ranking hoặc app.

Snapshot001/review002/proposal/template/raw/evidence/run cũ và qrels/ZIP lịch sử
được bảo toàn; preservation cuối và git diff --check ở checks/final_preservation.json.
Không stage/commit/push. Chưa tính metrics, chưa rà completeness/coverage50query,
không embedding/Dense/Hybrid/Reranker/UI/API hoặc suy nguồn đã verified.
Không còn metadata thiếu trong phạm vi22cặp; hai pending là quyết định giữ
chưa kết luận, không tự yêu cầu làm rõ query hoặc đổi chúng thành0.
