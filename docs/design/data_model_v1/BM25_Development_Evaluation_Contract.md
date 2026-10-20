# BM25 development evaluation v1

Contract `bm25-development-evaluation.v1`, snapshot tham chiếu 2025-01-01.
Tái sử dụng `src.bm25_baseline.load_index/search_loaded` và tokenizer hiện có.
Không có evaluation runner/qrels của nhóm trong repository được kiểm tra;
`config/bm25_smoke.v1.json` là smoke, không phải golden set. Giữ nguyên năm
câu smoke nghiệp vụ, không dùng câu OOV làm câu hỏi pháp luật.

DDD §14 và SRS DR-03, §10 quy định đánh giá corpus đã khóa. Lượt này là
development trên dataset experimental: binding bằng dataset/index version,
content hash và manifest hash, `corpus_version=null`. Không thay schema DDD,
không tuyên bố nghiệm thu test set hoặc xác minh pháp lý.

## Bốn loại bản ghi

- `queries.jsonl`: query_id, intent_group_id, query, query_type
  (direct/paraphrase/scenario), topic, split (dev/test). ID duy nhất, cùng
  intent chỉ có một split. Batch này chỉ dev; 30 câu/10 intent, mỗi intent
  ba cách diễn đạt. Không sửa câu sau khi xem ranking.
- `qrels.jsonl`: query_id, chunk_id thật, relevance nguyên 0/1/2. Chỉ nhãn
  được chấp nhận có annotation tương ứng; không dùng row index.
- `annotations.jsonl`: query_id, chunk_id, relevance, origin (agent/human),
  annotator_ref, status (pending/proposed/accepted), reason, evidence_refs,
  recorded_at thực tế có timezone. Pending có relevance=null; agent chỉ
  pending/proposed. Accepted cần human event thực, không tự điền người/ngày.
  Evidence `chunk:<chunk_id>` trỏ nguyên văn/context/source spans của
  dataset đã binding; `dataset_inventory` chỉ dùng cho lý do khảo sát
  toàn tập, không chứng minh tự động đã đọc. Không nhận evidence ID lạ.
- `run.jsonl`: query_id, chunk_id, rank từ 1 liên tục, score hữu hạn,
  giảm dần. Tối đa 10, không trùng chunk trong query.

`query_reviews.jsonl` ghi review độ đầy đủ nhãn/coverage: query_id, status,
origin, reviewer_ref, recorded_at, judgments_complete, coverage
(pending/answer_present/corpus_coverage_gap), reason, evidence_refs.
Đây là ghi nhận rà nhãn evaluation, không phải một cổng duyệt nguồn/corpus.
Không thể chứng minh không có đáp án chỉ vì BM25 không tìm thấy.

Mọi proposal/phiếu chưa điền nằm riêng, không được chép thành qrels.
Submission là snapshot mới ngoài bundle seal: binding, queries_sha256,
parent_manifest_sha256, qrels, annotations, query_reviews. Không sửa lịch sử;
score tạo run mới, giữ hash manifest cha và bản submission nguyên nội dung.
Một cặp query/chunk chỉ có một annotation hiện hành trong snapshot.

## Đủ điều kiện và metrics

Nhãn 2 trực tiếp, 1 hỗ trợ, 0 đã đánh giá không liên quan.
Recall/MRR lấy relevance >= 1. Recall@K là số positive trong Top-K chia
tổng positive đã gán nhãn; MRR@10 là nghịch đảo rank positive đầu hoặc 0.
nDCG@10: gain `2^rel-1`, discount `log2(rank+1)`, IDCG lấy nhãn lý tưởng
từ toàn qrels của câu. Macro trung bình theo query đủ điều kiện.

- Cần review độ đầy đủ qrels đã accepted và ít nhất một positive.
  Người rà cần tìm positive ngoài pool Top-10; recall chỉ phản ánh qrels
  được rà, không chứng minh đã tìm đủ mọi căn cứ trong corpus.
- Bất kỳ kết quả Top-10 chưa có accepted judgment: loại câu khỏi metric
  với `MISSING_TOP10_JUDGMENT`. Không chuyển unjudged thành 0.
- Không positive: không có mẫu số recall/IDCG; loại có lý do riêng.
  Corpus coverage gap được báo riêng khi có khảo sát và căn cứ;
  chưa khảo sát đủ giữ `coverage=pending`.
- Danh sách dưới 10 giữ nguyên độ dài; không đệm kết quả. Nếu qrels đủ
  điều kiện nhưng không có hit, cả bốn metrics bằng 0.
- Kết quả trùng/rank thiếu/ID lạ/NaN là lỗi validation, không tự deduplicate.
- Lỗi thực thi mỗi query được ghi outcome=error, không mất câu hỏi.
  Với query đủ nhãn, lỗi đóng góp 0 vào aggregate end-to-end theo SRS.
- Không có query đủ điều kiện: `PENDING_LABELS`, `metrics=null`.
  Không công bố số đo chính thức từ proposal hay fixture.

## Thực thi hữu hạn

Batch load index đúng một lần, không gọi build/index. Timing load tách khỏi
search từng câu; tuần tự, không warmup, không suy SLA/p95 từ 30 câu.
Output gồm queries/qrels/annotations/query_reviews/run/outcomes, phiếu
nguyên văn và nguồn, timing, report, manifest inventory SHA-256.
CLI validate kiểm binding/hash và bản ghi; không phải xác minh relevance.
Score không chạy lại hoặc điều chỉnh query/ranking.

Hướng dẫn: [Evaluation Quickstart](../../handoff/BM25_Evaluation_Quickstart.md).
