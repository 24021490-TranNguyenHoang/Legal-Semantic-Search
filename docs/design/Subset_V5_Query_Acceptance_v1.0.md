# Nhập phản hồi năm query subset v5 — contract v1.0

Phiên 10, 2026-11-05; snapshot pháp luật 2025-01-01.
Adapter `src.query_labels`, contract `subset-v5-query-acceptance.v1`.
Kế thừa rubric v1.2, contract năm query phiên 9 và typed labels phiên 8.
Không sửa producer/validator đã hash-bound hoặc scorer chunk-only v1.

## Phạm vi và đầu vào

Đúng 39 cặp chưa accepted từ năm template của
`staging/subset-v5-query-review-002/`. Prior bắt buộc là manifest
`staging/subset-v5-accepted-labels-002/`; không lấy 14 dòng inherited làm batch.
Trước khi ghi, validator replay bundle review, kiểm dữ liệu consumer/proof,
dataset/index/query/batch binding và toàn bộ prior accepted/pending.

Capture giữ nguyên bytes chỉ dẫn người dùng, SHA-256 và tham chiếu bản gốc.
Feedback được kiểm lại theo từng dòng explicit query/pair/relevance/reason trong
capture. Không dùng proposal làm quyết định hoặc tự điền cặp vắng thành 0.
Adapter hẹp này chỉ tiếp nhận xác nhận 39 cặp của phiên 10, không là bộ nhập
phản hồi tổng quát cho 500 cặp. Relation/completeness theo chỉ dẫn explicit;
relevance >=1 không đồng nghĩa direct/full.

## Submission và provenance

Năm bản điền ngoài bundle seal giữ nguyên template ID/type/hash/binding.
`submission.json` hợp nhất 39 dòng; `evidence.used.jsonl` giữ quote JSON pointer,
offset code point tương đối field, native source spans và cells. Không đổi
extraction offsets. Evidence được agent gắn từ nội dung bundle đã đọc;
không suy người dùng mở từng locator. Dependency-only phải trỏ required-read
hoặc dependency nhúng hợp lệ trong consumer closure; cells/header giữ nguyên.

`reviewer_ref` giữ nguyên `## CAL-039998018b`, là opaque reference người dùng
cung cấp, không suy danh tính. `reviewed_at=2026-11-05T09:07:00+07:00`, UTC
`2026-11-05T02:07:00Z`; import có thời gian kỹ thuật riêng và không được sớm
hơn thời điểm review. Không thay thời điểm review bằng đồng hồ agent.

Origin `user_reviewed_ai_assisted`, ai_assisted=true, independent=false,
blind=false. `proposal_consulted=true` trong template nghĩa là đã xem đề xuất
ChatGPT theo xác nhận; sidecar phân biệt `chatgpt_proposals_consulted=true`,
`bundle_b_consulted=null`, `user_opened_detail_files=null`.
Không suy lịch sử xem bảng B hoặc file. Coverage/all-label approval vẫn null.
Agreement so với proposal chỉ là đối chiếu, không ép nhãn/reason khớp proposal.

## Accepted và aggregate

Batch mới chỉ ghi 39 typed annotations với record_id thật, type giữ nguyên
chunk.v1/table-retrieval.v1/source-retrieval.v1; không ép thành chunk_id.
Giữ relation/completeness, reviewer metadata, evidence/provenance. Qrels mới
riêng batch; qrels lịch sử không thay. Mọi overlap query+record với prior,
kể cả pending, đều bị từ chối, không implicit supersedes.

Import ID từ contract+submission canonical; annotation ID từ quyết định đã
bind, không phụ thuộc vị trí vật lý bản accepted replay. Cùng run/source/prior
đã nhập trả ALREADY_IMPORTED/newly_imported=0, không ghi lại. Replay ở run mới
giữ import ID và payload quyết định; thời gian receipt import mới được ghi thật.

Aggregate chỉ tham chiếu đúng prior và batch mới, có row hash/annotation ID,
không tạo sự kiện chấp nhận mới cho 20 dòng cũ. Từ chối batch replay/trùng
import ID, cặp trùng và binding khác. Pending tham chiếu bản cũ nguyên vẹn.
Validator tái dựng nội dung rồi so canonical JSON, không chỉ kiểm outer seal;
bool/float không được coi là integer relevance.

## Giới hạn

59 accepted duy nhất không xác nhận toàn dataset/500 cặp. Pool năm query đủ
53 quyết định không chứng minh đã tìm mọi positive. Hai null V3-D02 vẫn
pending, không thành 0. Metrics chính thức 50 query vẫn null; nguồn/edition/
applicability pending và release gate không thay. Không scoring, tuning,
retrieval, model hoặc build dữ liệu trong adapter này.
