# Rubric relevance — BM25 v6 candidate run

**Rubric version:** `candidate-review-rubric.v1.0`
**Run:** `v6-bm25-candidate-run-001`
**Index / dataset:** `vtls-bm25s-subset.v2` / `vtls-subset-experimental.v6-candidate.1`

## Mức relevance

- **2 — Direct target:** nội dung target chứa căn cứ thực chất trả lời một phần hoặc toàn bộ câu hỏi. Ghi `full` hoặc `partial`, phần đã trả lời và điều kiện còn thiếu trong `label_reason_or_evidence`.
- **1 — Supporting:** target/context cung cấp thông tin hỗ trợ hoặc điều kiện cần nhưng chưa trực tiếp giải quyết câu hỏi. Ghi loại quan hệ hỗ trợ.
- **1 — Dependency-only:** nội dung trả lời chỉ xuất hiện trong phần required-read của target được xếp hạng. Ghi rõ dependency; không coi nội dung đó là direct target.
- **0 — Unrelated:** sau khi đọc target, context và phần đọc kèm, record không giúp trả lời. Trùng từ khóa/chủ đề là chưa đủ; phân biệt đúng phương tiện, loại đường, tình huống, thời điểm và điều kiện.
- **Để trống — Pending/uncertain:** chưa đủ căn cứ hoặc còn mơ hồ. Không dùng 0 thay cho chưa đọc/chưa kết luận.

Thang 0/1/2 theo quy ước qrels của SRS dự án; tiêu chí phân biệt target trực tiếp, supporting và dependency-only theo rubric composition hiện có. Direct metric dùng relevance 2; Useful dùng relevance từ 1 trở lên; nDCG dùng gain `2^relevance - 1`.

## Cách ghi nhận

1. Rà từng cặp `query_id`–`record_id`; giữ nguyên ID, query, index version và dataset version trong hàng.
2. Đọc đầy đủ target, context và required-read của record. Ghi phần trả lời, điều kiện, loại đối tượng và căn cứ nguồn trong `label_reason_or_evidence`.
3. Điền `relevance`, `reviewer_id` và trạng thái theo quy trình duyệt. Nếu có bất đồng hoặc chưa rõ applicability, để pending và ghi vấn đề cụ thể.
4. Chỉ chuyển thành qrels accepted sau khi hoàn tất quy trình review/coverage của dự án và tạo manifest mới. Không dùng điểm BM25, đề xuất AI cũ hoặc việc nằm trong Top-10 làm nhãn.

## Phạm vi và giới hạn

Bộ 50 query gồm `old-dev` 30, `new-dev` 15 và `limits` 5; manifest đánh dấu toàn bộ là development, không phải test độc lập. Run hiện chỉ là pool BM25 Top-10. Rubric này không xác nhận nguồn luật, phiên bản áp dụng, hiệu lực tại snapshot, độ bao phủ toàn corpus hoặc tính độc lập của người rà. Chỉ số hiện tại vì thế chưa phải metrics chính thức.
