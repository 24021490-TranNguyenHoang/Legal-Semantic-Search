# Bàn giao Hybrid v6, Benchmark Độ trễ & Khắc phục 4 Lỗi Review (`vtls-retrieval-v6-hybrid-handoff.v2`)

- **Người thực hiện:** Trần Nguyễn Hoàng (`24021490`) — Retrieval Lead
- **Thời điểm xuất gói:** `2026-11-26T17:16:44.218912+00:00`
- **Gói bàn giao mới:** `artifacts/vtls-retrieval-v6-hybrid-handoff-002.zip` *(giữ nguyên gói cũ `artifacts/vtls-retrieval-v6-hybrid-handoff-001.zip`)*

---

## 1. Cấu hình máy & Phiên bản đã ghim (24h Checkpoint)

- **Phần cứng & HĐH:** `13th Gen Intel(R) Core(TM) i5-13500H` (16 luồng), RAM `15.67 GB`, GPU tích hợp `AnyViewerIddDriver Device; Intel(R) Iris(R) Xe Graphics` (chạy inference trên `CPU`, `cuda=False`), OS `Windows-10-10.0.26200-SP0`.
- **Môi trường Python:** Python `3.11.9` · `torch==2.15.0+cpu` · `transformers==5.24.1` · `bm25s==0.3.13` · `numpy==2.4.6` · `scipy==1.17.1`.
- **Ghim Revision Model & Tokenizer (cả 2 thành phần đều khóa cứng commit SHA):**
  - Dense Encoder: `BAAI/bge-m3` — `model_revision = 5617a9f61b028005a4858fdac845db406aefb181`, `tokenizer_revision = 5617a9f61b028005a4858fdac845db406aefb181`.
  - Cross-Encoder Reranker: `BAAI/bge-reranker-v2-m3` — `model_revision = 953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`, `tokenizer_revision = 953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`.

---

## 2. Kết quả đo độ trễ chuẩn (48h Benchmark — Warmup + 3 lượt × 50 câu)

- **Thời gian nạp model & kiểm chứng index (tách riêng ngoài truy vấn):**
  - Nạp & validate BM25 v2 + `Consumer` v6 chính thức: `91327.20 ms`
  - Nạp & validate Dense bundle (`139 × 1024`, kiểm SHA-256 từng hàng): `16.43 ms`
  - Nạp `BAAI/bge-reranker-v2-m3` (model + tokenizer rev `953dc6f6f85a...`): `19082.33 ms`

| Chế độ truy xuất | Phạm vi đo | Số lượt đo | Số lỗi | p50 (ms) | p95 (ms) | Mean (ms) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| **`bm25_only` (BM25 v2)** | Nhận câu hỏi → tokenize → BM25s → Top-10 | `150` (`3×50`) | `0` | **`0.852`** | **`1.690`** | `0.961` |
| **`hybrid_rrf` (RRF k=60)** | Nhận câu hỏi → encode `bge-m3` + Dense + BM25s + RRF → Top-10 | `150` (`3×50`) | `0` | **`155.610`** | **`427.540`** | `204.378` |
| **`hybrid_rrf_rerank` *(dòng riêng — full 50q)*** | `hybrid_rrf` + Rerank Top-30 `bge-reranker-v2-m3` → Top-10 | `50` (`1×50`) | `0` | **`40389.680`** | **`47483.611`** | `38194.030` |
| **`hybrid_rrf_rerank` *(dòng riêng — 2 câu smoke × 3)*** | `hybrid_rrf` + Rerank Top-30 trên 2 câu smoke (sau warmup) | `6` (`3×2`) | `0` | **`37546.561`** | **`38773.057`** | `37468.189` |

*(Log thô từng câu của mọi lượt đo được lưu tại `benchmark/latency_raw_per_query.jsonl`.)*

---

## 3. Báo cáo khắc phục 4 lỗi Review & Hướng dẫn tích hợp cho Hùng & Long

### Lỗi 1: Loader từ chối sai dữ liệu (`src/hybrid_v6.py` & `evidence/loader_rejection_tests.json`)
- Sử dụng trực tiếp `subset_bm25_v6.load_index()` chính thức để kiểm tra seal của BM25 v2 + `Consumer` v6, sau đó `load_dense_bundle()` đối chiếu toàn bộ hash manifest, version/revision và SHA-256 của **từng vector hàng `0..138`** với `record_id`.
- Đã kiểm thử tự động 3 ca lỗi (`evidence/loader_rejection_tests.json`):
  1. **Sai hash** (`embeddings.npy` bị sửa 1 byte) → `ValueError: Dense directory inventory/content hash mismatch`.
  2. **Sai version** (`dense_version` lệch `vtls-dense-bge-m3.v1`) → `ValueError: Dense version mismatch`.
  3. **Lệch thứ tự 139 vector so với `record_id`** (hoán đổi dòng `0` và `1` trong `embeddings.npy`) → `ValueError: Dense vector row order/content mismatch at row 0`.

### Lỗi 2: Đủ bằng chứng Top-30 RRF trước khi rerank (`runs/rrf_top30_rerank_audit.50q.jsonl`)
- Xuất đủ `50 × 30 = 1,500` bản ghi Top-30 RRF trước rerank, ghi rõ `rrf_rank`, `record_id`, `bm25_rank`, `bm25_score`, `dense_rank`, `dense_score`, `rrf_score`, `reranker_logit`, `final_rerank_rank` và cờ `in_final_top10`.
- Kiểm chứng tự động đạt **`500 / 500` hit Top-10 nằm trọn trong Top-30 RRF (`0` hit thiếu bằng chứng)**.

### Lỗi 3: Mở căn cứ qua `Consumer` v6 thật (`evidence/consumer_v6_hydration_audit.json`)
- Loại bỏ hoàn toàn cách đọc thẳng `target_frames.jsonl`. Mọi `record_id` được mở qua `subset_bm25_v6.read_loaded(bm25_state, record_id)` gọi trực tiếp `Consumer.read(record_id)`:
  - **Câu đèn đỏ** (`c_fcaa52f3e09aa9b0719e84d05d9d13a9bd68343ff44f596fd379553ded82f4c6`): **`7` mục đọc kèm** (`unit_reads`), `0` `supporting_records`.
  - **Câu tuổi lái mô tô** (`c_30a64fc1bea93d7860d4f3821af382006956ca7dcbdc7770e636782e97fb1d9e`): **`16` mục đọc kèm** (`unit_reads`), `0` `supporting_records`.
  - **Hàng bảng (`table-retrieval.v1`):** Đã kiểm khớp `9` hàng bảng trong Top-10 qua `Consumer.read()` (ví dụ `tr_03f3ae425e4a1930d6081703c72e22aba780a4cdfd1402625e9ce8081e6308e6`).
- **Hướng dẫn tích hợp cho Hùng:**
  1. Gọi `mod, state, _ = load_bm25_v2_index("unpacked-v6/bm25")` và `dense = load_dense_bundle(state, "artifacts/v6_hybrid_handoff_v2/dense_bge_m3")`.
  2. Sau khi lấy `record_id` từ kết quả `search_hybrid_rrf(...)` hoặc `rerank_rrf_candidates(...)`, gọi `detail = mod.read_loaded(state, record_id)["dataset_response"]` rồi đọc căn cứ từ `detail["required_read"]["unit_reads"]` và `detail["required_read"]["supporting_records"]`.
  3. Bắt `ValueError` (sai hash, sai version, lệch thứ tự vector, `record_id` không hợp lệ) và `RuntimeError` (thiếu model hoặc sai commit SHA revision trong cache HuggingFace) để trả HTTP `503` / log lỗi rõ ràng thay vì âm thầm fallback.

### Lỗi 4: Gói mới tái lập được & Danh sách cặp thay đổi Top-10 cho Long
- Giữ nguyên gói `artifacts/vtls-retrieval-v6-hybrid-handoff-001.zip`.
- Gói mới `artifacts/vtls-retrieval-v6-hybrid-handoff-002.zip` dùng chuẩn xuống dòng `LF` (`\n`) và script `verify_checksums.py` khớp SHA-256 trên cả Git lẫn checkout Windows.
- Xuất sẵn 2 danh sách cặp thay đổi (để `relevance: null`, **không gán mặc định 0**) cho Long chấm và tính Recall@10:
  - `runs/top10_diff_vs_handoff001.jsonl`: `22` cặp khác biệt Top-10 giữa gói `001` và `002`.
  - `runs/top10_diff_bm25_vs_hybrid.jsonl`: `1198` cặp khác biệt Top-10 giữa `bm25_only` và `hybrid_rrf` / `hybrid_rrf_rerank`.
