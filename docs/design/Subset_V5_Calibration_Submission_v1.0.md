# Phiên 8 — tiếp nhận phản hồi calibration subset v5

Contract bổ sung `subset-v5-calibration-response.v1`, ngày 04/11/2026.
Kế thừa [rubric v1.2](Subset_V5_Relevance_Review_v1.2.md),
[rubric composition](Composition_Relevance_Review_v1.1.md) và template đã seal
trong `staging/subset-v5-relevance-002/`. Không sửa contract/payload lịch sử.
Snapshot sản phẩm giữ **2025-01-01**.

## Nguồn quyết định và phạm vi

Người dùng xác nhận đã đọc lại 22 quyết định, ChatGPT hỗ trợ đề xuất nhãn và
diễn đạt lý do. Chỉ dẫn thực tế này thay yêu cầu chấm độc lập của handoff cũ
đối với **submission mới này**: ghi `origin=user_reviewed_ai_assisted`,
`ai_assisted=true`, `blind=false`, `independent=false` trong sidecar provenance.
Gói blind lịch sử và proposal vẫn giữ nguyên. Không tuyên bố phép đo độc lập,
inter-annotator agreement hoặc human-only ground truth.

Xác nhận chỉ gồm 22 cặp, không phải 500 cặp, coverage của 50 query, chất lượng
dataset hoặc hiệu lực pháp lý. Hai null là quyết định giữ pending có chủ đích.
Chưa có danh tính tham chiếu hoặc thời điểm reviewer rà thực tế trong phản hồi.

## Bản ghi mới, không thay template

- `submission.json` giữ đúng shape template; copy nguyên binding và sáu field
  identity của từng item. `coverage_decision`/`all_labels_approved` giữ null.
- `feedback.received.json` giữ relevance/reason đúng nguyên văn người dùng,
  xác nhận có AI hỗ trợ và hai metadata còn null; không dùng tên Git/Windows.
- `provenance.json` bind SHA submission/template/review manifest/feedback/evidence;
  `agent_recorded_at` là lúc agent ghi hồ sơ, **không phải reviewed_at**.
- `evidence.used.jsonl` ghi detail hash và các quote/pointer thực sự đối chiếu
  để hỗ trợ reason: own text, context, cells/header và required-read khi cần.
  Việc chọn/bind evidence và điền relation/completeness là phần agent hỗ trợ;
  không tuyên bố người dùng đã mở từng đường dẫn file cụ thể.
- `evidence_refs_used` là đường dẫn POSIX tương đối **repository root**, chỉ
  tới detail của đúng record trong review đã seal. Không tự tải thêm nguồn.
  Quote offsets tương đối field JSON; native extraction spans/cells giữ nguyên.
- `comparison.jsonl/.md` ghi proposal và phản hồi riêng; bất đồng được bảo toàn.
  Metadata còn thiếu không làm nội dung phản hồi biến thành proposal của agent.

Relevance/relation/completeness theo rubric cũ: 2/direct_target full hoặc partial;
1/supporting_target hoặc dependency_only, partial; 0/unrelated/none;
null/uncertain/uncertain. `reviewer_outcome` dùng agree/edit/uncertain theo handoff
composition; null dùng uncertain dù đây là quyết định pending đã được xác nhận.
Không tự đặt full vì relevance=2. Chỉ khác nhãn máy không phải lỗi validation.

## Validator và admission

`src.subset_review.validate_template` chỉ kiểm **template chưa điền**; không nới
hoặc gọi nó trực tiếp với submission đã điền. Reader hẹp mới
`src.subset_calibration` dùng helper cũ kiểm template gốc, manifest/inventory,
IDs/hashes, frozen query, payload/detail/source spans/cells, enum, quote/dependency,
phản hồi nguyên văn và provenance. Không load/build/search lại BM25.

CLI trả:

- **1**: lỗi kỹ thuật/binding/evidence/enum, sửa sai phản hồi hoặc metadata không
  có trong captured feedback.
- **2**: nội dung/binding đạt nhưng `reviewer_ref` hoặc `reviewed_at` còn null;
  trạng thái `AWAITING_REVIEWER_METADATA`, báo chính xác field thiếu.
- **0**: metadata được cung cấp và hợp lệ; `METADATA_COMPLETE_NOT_ADMITTED`.
  Reader này chỉ validate, chưa phải lệnh nhập nhãn.

Không ghi accepted/qrels hoặc metrics trong reader. Contract accepted hiện hành
cần sự kiện reviewer thực và metadata có căn cứ; chưa đủ thì giữ submission
ngoài bundle. Khi có metadata thực tế, tạo snapshot mới ngoài seal và đánh giá
đường nhập typed accepted labels riêng; không đưa table/whole-source vào scorer
chunk-only v1 bằng cách đổi tên ID/type. Hai null tiếp tục pending, kể cả sau đó.
Không cần duyệt nguồn/hiệu lực để tiếp nhận relevance, và calibration không duyệt
nguồn/hiệu lực. Không bổ sung phân quyền, chữ ký số hoặc một vòng legal approval.

## Chạy lại

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_calibration --submission staging/subset-v5-calibration-submission-001/submission.json
# Exit 2 hiện là kết quả đúng: thiếu reviewer_ref và reviewed_at.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_subset_calibration tests.test_subset_review tests.test_composition_review tests.test_evaluation -v
```

Không chạy scorer, không sửa evaluation/query/qrels hoặc bundle lịch sử.
