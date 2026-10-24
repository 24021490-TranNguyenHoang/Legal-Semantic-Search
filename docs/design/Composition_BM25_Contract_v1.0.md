# Consumer/index composition experimental v1.0

2026-10-23, snapshot2025-01-01. Khóa dataset-v3-draft-005 bằng manifest SHA
và content hash; không đổi dataset/index/app v1 hoặc artifact lịch sử.

Consumer dùng validator/resolver stdlib đóng gói trong dataset. Validate một
lần khi load, sau đó cache records/graphs/context/dependency snapshot. Các path
được resolve bằng chính resolve() của portable reader, không fallback repo.
Detail dùng đúng unit_ids/subtrees đã đóng gói, không trích reference hoặc
mở rộng ngoài binding. Kiểm regression detail với portable.read gốc.

Projection `composition-text-for-search.v1`: mỗi retrieval membership một
document, giữ record_type và ID thật. Cả chunk.v1 và table-retrieval.v1 dùng
text_for_search đã có/hash; bảng không thành nguyên văn, không merge theo
owner. Supporting/dependency/withheld/quarantine không thành document độc lập.
Required-read không ghép vào BM25 input. Không lọc scope ngầm.

Engine BM25S0.3.13 Lucene k1=1.2,b=.75, float32/int32 và lexical preprocessing
vi-unicode-lexical.v1 giữ nguyên. Tái dùng engine/rank/tokenizer/runtime checks
của bm25_baseline. Adapter mapping dùng record_id như khóa xếp thứ tự nội bộ;
không gán table tr_ thành chunk_id trong dữ liệu. Tie: score giảm, record_id
Unicode tăng; các ID text c_ giữ thứ tự v1. Score0 không trả, không đệm Top10.
Index version `vtls-bm25s-composition.v1`, consumer `composition-consumer.v1`.

Index package gồm dataset bất biến, engine/mapping/config/runtime, và runtime
source tối thiểu. Manifest bind dataset version/SHA/content, policy/consumer/
projection/engine/query config và runtime code hashes. Validate rebuild sparse
arrays theo tolerance cũ; load kiểm checksum, config/runtime, mapping/vocab/
shape trước search. Consumer thiếu capability phải fail. Query BM25 không chịu
encoder budget; không encoder/Dense/embedding/Qdrant/reranker.

Batch dùng validate_queries/evaluation contract hiện có. Cố định30query cũ
và15dev mới +5case giới hạn trước ranking. Run dùng record_type/record_id,
không chuyển qrels v1; annotation mới pending/null, có trường reviewer đánh
dấu direct_target/dependency_only/unrelated sau khi đọc. Dependency source
unit không được tính là document rank. Metrics chính thức null/PENDING_LABELS.
Top10 cùng detail/source/cells/context/dependencies được lưu đủ, snippet không
phải câu trả lời đầy đủ. Timing load tách search/detail. Nhóm giới hạn dựa
selection/membership/source inventory để nhận diện coverage, không dựa Top10.
