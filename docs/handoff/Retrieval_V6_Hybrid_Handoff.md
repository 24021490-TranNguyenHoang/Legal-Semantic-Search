# Bàn giao Retrieval Hybrid & Reranking v6 (`vtls-retrieval-v6-handoff.v1`)

- **Người thực hiện:** Trần Nguyễn Hoàng (Retrieval Lead)
- **Thời điểm tạo:** `2026-11-24T16:44:17.300685+00:00`
- **Môi trường:** Python `3.12.7` · PyTorch `2.15.0+cpu` · `bm25s==0.3.13`
- **Ràng buộc dữ liệu nguồn (giữ nguyên seal từ Huy):**
  - `dataset_version`: `vtls-subset-experimental.v6-candidate.1`
  - `index_version`: `vtls-bm25s-subset.v2`
  - `dataset_manifest_sha256`: `47b23b4f8742a308f32b4c1efd0d7749a81a8aae792459b95e7035490802bdfc`
  - `index_manifest_sha256`: `58c05ef0f6c2bb39d4a6af8d62d5520843c028e538a0b5d8abeb2ce5d3589c5f`
  - `queries_manifest_sha256`: `f8cc9257c410c8eb578d43a0bd1912e3aa5c572829be5e33d7ee0a2045e546f0`

---

## 1. Kiến trúc & Thông số Pipeline

1. **Lexical Retriever (Huy's Frozen Index):** Đọc trực tiếp chỉ mục Lucene BM25 (`k1=1.2, b=0.75, delta=0.5`) từ `vtls-bm25s-subset-v2-001` trên toàn bộ `139` target (`126 chunk.v1`, `9 table-retrieval.v1`, `4 source-retrieval.v1`).
2. **Dense Retriever (`BAAI/bge-m3`):**
   - Tensor lưu tại `dense_bge_m3/embeddings.npy` kích thước `(139, 1024)` (`float32`, `CLS` pooling, chuẩn hóa L2, SHA-256: `7887c71c334cf4b289c79bd3ad52c8b342b517af753b81d479bd3f6dcb2f9685`).
   - **Tokenizer Budget Audit:** Min `46`, Median `127`, P95 `236`, Max `373` token. **`0 / 139` bản ghi vượt ngưỡng 512/1024/2048** (không cắt cụt nội dung điều luật hay bảng biểu).
3. **Hybrid Fusion:** Reciprocal Rank Fusion thuần túy với $k = 60$ (`score = 1/(60 + rank_bm25) + 1/(60 + rank_dense)`), **không dùng trọng số nhân cố định**.
4. **Cross-Encoder Reranker (`BAAI/bge-reranker-v2-m3`):** Rescore Top-`30` ứng viên từ RRF (`max_length=1024`), xuất Top-`10` cuối cùng.

---

## 2. Hướng dẫn tiếp nhận theo vai trò

- **Gửi Huy (Data Pipeline):**
  - Toàn bộ artifact đầu vào từ `vtls-bm25s-subset-v2-001` được giữ nguyên vẹn chỉ đọc; `dense_bge_m3/records.jsonl` đối chiếu 1-1 `internal_doc_id`, `record_id`, `unit_id`, `content_sha256` với `document_mapping.jsonl`.
- **Gửi Long (Evaluation & Labeling):**
  - Sử dụng 4 file run log chuẩn hóa trong `runs/` (`bm25_only.top10.jsonl`, `dense_only.top10.jsonl`, `hybrid_rrf.top10.jsonl`, `hybrid_rrf_rerank.top10.jsonl`) cho đủ 50 queries (`30 old-dev` + `15 new-dev` + `5 limits`).
  - Mỗi dòng đã gắn sẵn `rank`, `score`, `score_type`, `bm25_rank`, `dense_rank`, `rrf_score` và `citation_path` để chấm đối chiếu và gán nhãn mở rộng.
- **Gửi Hùng (Serving / API Integration):**
  - Tải `BAAI/bge-reranker-v2-m3` theo cơ chế **lazy-load** và giải phóng encoder khi không dùng đồng thời trên máy RAM hạn chế (tránh lỗi Windows paging file `os error 1455`).
  - Tầng hydration nối `record_id` từ Top-10 sang `dataset/target_frames.jsonl` (`113` `record_id` duy nhất trong Top-10 đã được kiểm tra hydration thành công tại `hydration_check.jsonl`).
  - Có thể dùng `score < 0.0` (logit của `bge-reranker-v2-m3`) làm tín hiệu cảnh báo truy vấn ngoài phạm vi (`V3-L01..V3-L04` đều cho logit âm từ `-0.499` đến `-4.465`).

---

## 3. Danh mục tệp bàn giao (`artifacts/v6_hybrid_handoff/`)

| Tệp | Kích thước (Bytes) | SHA-256 (16 ký tự đầu) |
| :--- | ---: | :--- |
| `dense_bge_m3/dense_manifest.json` | 1,839 | `a38a359e1d7b79b4...` |
| `dense_bge_m3/embeddings.npy` | 569,472 | `7887c71c334cf4b2...` |
| `dense_bge_m3/records.jsonl` | 63,975 | `e63e48639d7fd2f5...` |
| `dense_bge_m3/tokenizer_audit.jsonl` | 46,988 | `eaf66d443e34fc77...` |
| `handoff_manifest.json` | 3,352 | `1ea4655fdb9b62ec...` |
| `hydration_check.jsonl` | 33,592 | `c0f7430e0f28256b...` |
| `query_diagnostics.50q.jsonl` | 32,165 | `8aba4b7a2f94bc28...` |
| `runs/bm25_only.top10.jsonl` | 359,752 | `d94a8fd19345bd68...` |
| `runs/dense_only.top10.jsonl` | 361,818 | `674f860ce4cc6be8...` |
| `runs/hybrid_rrf.top10.jsonl` | 358,672 | `efdee932d6f6f402...` |
| `runs/hybrid_rrf_rerank.top10.jsonl` | 371,675 | `8a884ae3acbfa3b2...` |
