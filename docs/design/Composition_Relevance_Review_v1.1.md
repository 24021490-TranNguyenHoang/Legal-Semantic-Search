# Rubric development composition v1.1

Chốt trước khi gán nhãn trong phiên 2026-10-24. Kế thừa
`BM25_Development_Evaluation_Contract.md`; không đổi ranking hoặc query.
Đây là đánh giá corpus experimental tại snapshot 2025-01-01, không xác minh
pháp lý. Mọi nhận xét của agent là `origin=agent_review`, `status=proposed`.

- Relevance **2**: target trực tiếp chứa căn cứ thực chất trả lời ít nhất một
  phần câu hỏi. **1**: căn cứ hỗ trợ, có điều kiện còn thiếu, hoặc đáp án chỉ
  nằm trong required-read dependency. **0**: đã đọc và không trả lời câu hỏi;
  cùng chủ đề/từ khóa không đủ. Chưa xác định được giữ null/pending.
- `relation`: direct_target, supporting_target, dependency_only, unrelated,
  uncertain. Dependency-only vẫn gắn ID retrieval record đang xét, không tạo
  rank/positive cho source unit không thuộc membership.
- `completeness`: full/partial/none/uncertain, độc lập với relevance. Full chỉ
  có nghĩa đủ cho câu hỏi cụ thể theo nguồn đã đóng gói; không phải lời tư vấn
  hoặc kết luận hiệu lực toàn văn. Câu hỏi nhiều hàng/đơn vị cần chỉ rõ phần
  đáp ứng, phần thiếu và evidence cần kết hợp. Một hàng đúng có thể 2/partial.
- Điều kiện trái câu hỏi (loại xe, thời tiết, số sàn/tự động, ranh giới số)
  không được bỏ qua. Hàng khô ráo không trả lời mức khoảng cách khi mưa.
  Chế tài liên quan chỉ là supporting khi câu hỏi cần quy tắc và ngược lại.
- `uncertainty`: null hoặc mô tả giới hạn diễn giải/độ phủ; chưa đủ căn cứ
  nhãn giữ pending. Không dùng score/rank để suy relevance.

Evidence gồm detail hash-bound của chính record, source spans/cells, context
và dependency cần đọc. Mỗi proposal có reason, answered_part, missing_part,
query/record hash, input binding và thời điểm ghi nhận thật. Phiếu đọc ẩn
rank/score, sắp ID; có thể đọc một record một lần cho nhiều query nhưng mỗi
cặp được xét riêng. Nhãn v1-only nằm riêng với binding v1, không chuyển qrels.

Tìm ngoài pool bằng citation/graph/thuật ngữ thay thế và ranking sâu, lưu riêng
run/phạm vi đọc. Không coi Top100 hoặc khảo sát hữu hạn là độ phủ đầy đủ.
Unjudged không thành 0. Nguồn withheld/dependency không thành retrieval member.

Metrics chính thức null khi chưa có accepted labels và review độ đầy đủ thực.
Không tính provisional metrics trong lượt này. Recall/MRR dùng >=1, nDCG
gain 2^relevance-1 và log2(rank+1); giữ nguyên quy tắc missing/duplicate/no
positive/danh sách ngắn của v1. Agent không tạo accepted/human reviewer event.

Gói hiệu chuẩn là mẫu 8–10 query, không phê duyệt toàn bộ nhãn/coverage.
Người dùng ghi đồng ý/sửa/chưa chắc trong submission ngoài bundle seal;
reviewer_ref và thời gian chỉ ghi từ sự kiện thật. Bước tiếp theo mới kiểm
accepted annotations + coverage trước scorer; không chép proposal vào qrels.

## Bản ghi và kiểm chứng thực thi

`annotations.proposed.jsonl` giữ chính xác tập cặp Top10;
`outside_pool.proposed.jsonl` chỉ positive đã đọc ngoài pool, kể cả record
pointer có đáp án trong dependency. Mỗi dòng có record_id/type, query_sha256,
record_sha256 (canonical toàn payload), binding dataset/index manifest/content
hash/version, detail_sha256, citation_path, source_spans, cell_ids,
combine_with (retrieval members thật), recorded_at UTC thực tế. Không dùng
thứ tự dòng làm ID. Query object hash bao gồm batch_group của frozen run.

`coverage.jsonl` tách khảo sát hữu hạn và coverage_approved=false;
`deep_run.jsonl` là kết quả tìm sâu chưa được gán nhãn toàn bộ.
Source-only graph/backlog và selection withheld không được nhập qrels.
`v1.proposed.jsonl` gắn dataset/index/query v1 riêng, có detail/context v1;
đọc lại payload giống nhau được tái sử dụng, không tái sử dụng human decision.

Validator `src.composition_review` tái dùng consumer/index load và validator
evaluation v1, không gọi build/reindex. Kiểm inventory, rubric, frozen queries,
membership/type/payload/hash, source detail/spans/cells/dependencies, template
trống, cặp thiếu/trùng, null không thành0, origin và trạng thái proposed/pending.
Kiểm kỹ thuật không chứng minh rationale/coverage đúng về pháp lý. CLI và gói
hiệu chuẩn được mô tả trong run review và tài liệu bàn giao. Scorer accepted
composition có cả table record chưa triển khai; metrics giữ null trong lượt này.
