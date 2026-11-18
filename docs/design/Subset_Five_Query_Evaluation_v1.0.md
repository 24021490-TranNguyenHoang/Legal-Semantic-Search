# Đánh giá chẩn đoán BM25 năm query — v1.0

Phiên 11, ngày 2026-11-16; snapshot pháp luật 2025-01-01.
Policy `subset-five-query-diagnostic.v1`,
`evaluation_scope=five_query_development_diagnostic`.

Config `config/subset_five_query_evaluation.v1.json` được ghim trước tính toán.
Đúng năm query theo thứ tự: dev-night_horn-3, dev-driving_age-2,
dev-red_light-2, V3-D05, V3-D07. Dùng batch002/review002/aggregate001 đã chỉ định,
không ranking mới, không sửa câu hỏi, nhãn hoặc hash. Các manifest dẫn tới
dataset006/index003 và query001, xác nhận bằng hash thực tế.

## Quan hệ với evaluator cũ

`src.evaluation` v1 chỉ nhận chunk, Useful>=1 và loại câu không có positive
hoặc thiếu review coverage. Không nới evaluator/contract/artifact đó.
Adapter hẹp `src.subset_evaluation` tái dùng validate_queries/require/metrics
(chỉ lấy nDCG từ metrics cũ), typed acceptance/evidence validators hiện có.
Không gọi scorer chunk-only hoặc đòi quyết định coverage mới để tính P/Hit/RR
trong phạm vi năm câu được người dùng cho phép. Recall/AP/MAP corpus không tính.

## Đủ điều kiện

Validate aggregate cùng cả hai accepted batches, bốn file refs/progress/summary,
review/templates và native evidence theo validator phiên 9–10. Resolve từng
reference bằng batch+annotation_id+row SHA, không theo dòng. Xác nhận59 accepted
duy nhất (7/10/42),53 cặp pool và50 vị trí Top10 đủ accepted,2 pending V3-D02
nằm ngoài phạm vi. Bảo toàn type chunk/table-row/whole-source, relation,
completeness, evidence, query object hash và record/detail hash.

Kiểm integrity tất cả file frozen batch; đối chiếu run với raw_results và
ranking_and_response_signature. Rank liên tục1..10, score hữu hạn giảm dần,
record/query/type/version đúng binding; giữ nguyên thứ tự. Thiếu/trùng nhãn,
proposal chưa accepted, binding sai hoặc payload khác: lỗi exit1 trước khi
tạo output, không tạo metric có vẻ hợp lệ và không tự unjudged→0.

## Phép đo đã chốt

Direct positive iff relevance=2. Useful positive iff relevance>=1, bao gồm
supporting_target và dependency_only. Không đổi completeness;2/partial không
có nghĩa đủ câu trả lời. Với mỗi cách đọc và cutoff k=1,3,5,10:

- Precision@k = số positive trong k vị trí / k, cả khi ít hơn k kết quả.
- Hit@k =1 nếu có ít nhất một positive trong k vị trí, còn lại0.
- RR@10 =1/rank positive đầu tiên trong Top10; không có hit thì0.
- Macro trung bình đúng5 câu, gồm cả0 và câu không có positive trong pool.
  MRR@10 là macro RR@10. Xuất count/numerator/denominator/contribution riêng.

nDCG@10_pool diagnostic chung graded: gain=2^relevance-1,
discount=log2(rank+1), IDCG từ accepted pool riêng query, tối đa10. Dùng
`evaluation.metrics` cho nDCG khi IDCG>0; nếu IDCG=0 trả null. Macro chỉ các
query IDCG>0 và báo rõ mẫu số, không mặc định null=0. Xuất DCG/IDCG để kiểm tay.
Đây là pool hữu hạn, không ideal ranking toàn corpus. Query không có positive
trong pool không chứng minh corpus không có đáp án.

Recall corpus, AP/MAP corpus và metrics chính thức50query đều null.
Không tính recall giả bằng mẫu số positive pool rồi gọi recall toàn corpus.

## Output, giải thích và replay

Run staging mới: config snapshot, nguyên50 dòng run đã chọn,53 nhãn accepted
tham chiếu nguyên nguồn, bảng Top10 có citation/rank/score/label/relation/
completeness/evidence, outside positives với rank deep đã lưu nếu có (không
tìm lại), metrics/counts/contributions, phân tích và manifest SHA inventory.
Outside deep rows là vị trí quan sát cũ, không nhãn mới hoặc completeness proof.

Bảng chứng cứ giữ nguyên user reason và quote JSON pointer/offset; phân biệt
own target/context với required-read, không đẩy supporting hoặc view thành target.
Error analysis tách retrieval miss trong pool, useful qua dependency, sai đối
tượng/hành vi/khu vực/ranh giới, và giới hạn membership/coverage chưa chứng minh.

Origin nhãn user_reviewed_ai_assisted, không độc lập/blind. Agent chỉ tính và
phân tích theo nhãn đã được chấp nhận; không tạo reviewer event, sửa scope/
applicability hoặc legal verified. Hoàn thành pool không là duyệt500 cặp.

Validate tái dựng từ input đã ghim và so byte tất cả output, gồm Markdown.
Manifest bind code mới và helper metric/contract; không sửa hash-bound code cũ.
Replay cùng input/config/code giữ payload và manifest giống byte, thời gian
thực thi ghi bên ngoài artifact trong checks. Không model/index/UI/API/tuning.
