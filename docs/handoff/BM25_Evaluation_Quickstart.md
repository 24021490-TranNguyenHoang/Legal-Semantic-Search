# Development evaluation BM25

Dùng môi trường `requirements-bm25.txt` và index đã giải nén theo
[BM25 Quickstart](BM25_Quickstart.md). Không thêm package đánh giá hoặc
framework khác. Chạy từ root repo; thay executable bằng venv tương ứng.

```powershell
.\.venv-bm25\Scripts\python.exe -X utf8 -B -m unittest tests.test_evaluation
.\.venv-bm25\Scripts\python.exe -X utf8 -B -m src.evaluation batch --index-manifest staging/bm25-baseline-v1-001/index_manifest.json --queries config/evaluation_dev.v1.jsonl --run-dir staging/bm25-evaluation-dev-NEW
.\.venv-bm25\Scripts\python.exe -X utf8 -B -m src.evaluation validate --index-manifest staging/bm25-baseline-v1-001/index_manifest.json --bundle staging/bm25-evaluation-dev-NEW
```

Tên run phải chưa tồn tại. Batch lưu queries trước ranking, load một lần,
Top-10 giữ nguyên thuật toán cũ. `PENDING_LABELS`/exit 0 nghĩa là cấu trúc
đạt nhưng chưa đủ nhãn; không phải retrieval đã đạt chất lượng.
Sai ID/hash/split/relevance/rank/duplicate/evidence: exit khác 0.

Đọc `annotation_sheet.md` theo query: nguyên văn, context, citation,
chunk_id và source spans đều lấy từ dataset. Mọi đường nguồn trong phiếu
tính tương đối từ `staging/bm25-baseline-v1-001/dataset/`.
Pool BM25 có thiên lệch; người phụ trách cần tìm các positive ngoài Top-10.
Giữ nguyên query; phát hiện mơ hồ/gap thì ghi trong review, không sửa để
tăng điểm. GPLX đổi/cấp lại có thể cần nguồn bổ sung; Top-10 thiếu đáp án
không đủ kết luận dataset thiếu.

Submission mẫu hiện có:
`staging/bm25-evaluation-review-001/submission.json`.
Năm proposal agent có lý do trong `proposals.md`; các mục khác vẫn null.
Đây chưa phải phiếu đã duyệt. Tạo **bản mới** từ mẫu, không sửa bundle:

- Giữ binding, queries_sha256 và parent_manifest_sha256.
- Ghi relevance 0/1/2, reason, `chunk:<ID>` thực dùng, tên người rà và
  recorded_at đúng sự kiện. Chỉ đánh dấu accepted nếu thực sự đã rà.
- Mỗi accepted annotation cần một dòng qrels giống query/chunk/relevance.
  Proposal không có dòng qrels. Có thể thêm chunk ngoài pool bằng ID thật.
- Điền query_reviews khi đã rà độ đầy đủ: accepted/human, reviewer_ref,
  thời gian, reason/evidence, judgments_complete=true, answer_present
  hoặc corpus_coverage_gap. Phần chưa kết luận giữ pending.

```powershell
.\.venv-bm25\Scripts\python.exe -X utf8 -B -m src.evaluation score --index-manifest staging/bm25-baseline-v1-001/index_manifest.json --bundle staging/bm25-evaluation-dev-001 --submission staging/my-review/submission.json --run-dir staging/bm25-evaluation-scored-NEW
```

`report.json` chứa số tổng/đủ điều kiện/loại và từng lý do, coverage gaps,
coverage pending, lỗi, metrics từng câu và macro nếu đủ điều kiện.
Không có accepted labels thì metrics=null. Nhãn 0 là phán đoán đã rà,
không phải mặc định cho kết quả chưa đọc. Intent groups của bộ dev này
không được tái sử dụng trong test cuối.

Contract: [BM25 Development Evaluation](../design/data_model_v1/BM25_Development_Evaluation_Contract.md).
Thời gian fixture không đại diện latency thật. Các test nhãn synthetic
không xác nhận luật, hiệu lực hay chất lượng retrieval.
