# Bàn giao Hybrid v6 Hoàn chỉnh (`vtls-retrieval-v6-hybrid-handoff.v3`) — Chốt 6/6 Đầu việc

## 1. Môi trường tái lập trên máy thứ hai (`.venv-model` & Lockfile)

- **Máy đo & Runtime:** `nartgnaoh` | `Windows-10-10.0.26200-SP0` | `13th Gen Intel(R) Core(TM) i5-13500H` (16 luồng) | RAM `15.67 GB` | Device: `cpu`
- **Python & Unicode seal:** Python `3.11.9` (`unicodedata 14.0.0`), `torch 2.15.0+cpu`, `transformers 5.24.1`, `bm25s 0.3.13`, `numpy 2.4.6`
- **File khóa môi trường:** `requirements-model.lock.txt` (SHA-256: `2278902398a180211930ad10794a95f9ffe5dea61132531ab5a914ef0863ca5b`)
- **Revision Hugging Face đã ghim cứng (cả model + tokenizer):**
  - Dense Encoder: `BAAI/bge-m3` @ `5617a9f61b028005a4858fdac845db406aefb181`
  - Cross-Encoder Reranker *(offline / tùy chọn)*: `BAAI/bge-reranker-v2-m3` @ `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`

### Lệnh dựng `.venv-model`, tải/cache 2 model và chạy smoke trên máy thứ hai

```powershell
# 1. Tao moi truong ao tu Python 3.11.9 va cai dung ban khoa CPU
py -3.11 -m venv .venv-model
.\.venv-model\Scripts\python.exe -m pip install -r requirements-model.lock.txt

# 2. Tai & xac minh cache local cho dung revision cua 2 model + tokenizer
.\.venv-model\Scripts\python.exe -c "from src.hybrid_v6 import load_pinned_dense_encoder, load_pinned_reranker; load_pinned_dense_encoder(local_files_only=False); load_pinned_reranker(local_files_only=False); print('CACHE_OK')"

# 3. Kiem tra checksum goi ban giao
.\.venv-model\Scripts\python.exe artifacts\v6_hybrid_handoff_v3\verify_checksums.py
```

---

## 2. Sinh lại trực tiếp 139 vector từ `BAAI/bge-m3` & Bảo vệ đóng gói

1. **Sinh lại độc lập 139 embedding (`139 × 1024`):**
   - Mã hóa trực tiếp toàn bộ 139 bản ghi từ `unpacked-v6/bm25/search_inputs.jsonl` bằng `BAAI/bge-m3` (`5617a9f61b028005a4858fdac845db406aefb181`, `CLS` pooling, `max_length=512`, `float32` chuẩn hóa L2) trong `162750.87 ms`.
   - Đối chiếu với vector của `handoff-002` (`evidence/vector_regeneration_comparison.json`): `max_abs_diff = 4.38e-07`, `min_row_cosine_similarity = 0.99999982` (`139/139` hàng khớp cosine `> 0.99999`).
2. **Chống ghi đè & Cổng chặn đảo 2 hàng vector trước đóng gói:**
   - Bộ đóng gói từ chối ghi đè (`FileExistsError`) nếu thư mục/file đầu ra đã tồn tại; giữ nguyên vẹn SHA-256 của `handoff-001` và `handoff-002`.
   - Đã kiểm thử đảo 2 hàng vector (`[10, 11]`) trước khi xuất `SHA256SUMS.txt` và nén ZIP: cổng kiểm định từ chối ngay (`ValueError: Dense vector row order/content mismatch at row 10`).
3. **Khóa SHA-256 danh sách câu hỏi trong manifest:**
   - `queries_manifest_sha256`: `f8cc9257c410c8eb578d43a0bd1912e3aa5c572829be5e33d7ee0a2045e546f0`
   - `queries_files_sha256`: `15e76c4de50515c956f19d4601fed94d293c5ef43e88136710297af6474cbc34`
   - `queries_canonical_sha256`: `1f13ad5bf06c1d520d2c2432233a624e0aff3ac83324a306512e0f4f841de52f`

---

## 3. Benchmark độ trễ trên bộ 139 vector vừa sinh lại (Warmup + 3 lượt × 50 câu)

| Chế độ | Phạm vi đo | Số lượt (`n`) | Lỗi | p50 (ms) | p95 (ms) | Mean (ms) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **`bm25_only`** | Nhận câu hỏi → tokenize → BM25s → Top-10 | `150` | `0` | **`1.047`** | **`1.481`** | `1.096` |
| **`hybrid_rrf` (RRF k=60)** | Nhận câu hỏi → encode `bge-m3` + NumPy cosine + BM25s + RRF → Top-10 | `150` | `0` | **`356.623`** | **`508.524`** | `358.899` |
| **`hybrid_rrf_rerank` *(offline/tùy chọn)*** | `hybrid_rrf` + Rerank Top-30 `bge-reranker-v2-m3` → Top-10 | `50` | `0` | **`21518.327`** | **`37662.580`** | `25423.763` |

---

## 4. Phối hợp Hùng (Tích hợp & Smoke live 3 ca) & Long (Chấm Recall@5/10, MRR, nDCG)

### Phần bàn giao cho Hùng (`evidence/hung_integration_smoke.json`)
- **Kiến trúc backend hiện tại:**
  - Dense retrieval chạy **NumPy / cosine cục bộ** trên ma trận `139 × 1024` `float32` nạp từ `dense_bge_m3/embeddings.npy` (chưa bật Qdrant).
  - Cross-Encoder Reranker (`BAAI/bge-reranker-v2-m3`) giữ ở chế độ **offline / tùy chọn**, không bật trong đường dẫn truy vấn trực tuyến mặc định.
- **Kết quả smoke live 3 ca + mở detail qua `Consumer` v6 thật:**
  1. **Câu đèn đỏ** (`dev-red_light-1`): hit `c_fcaa52f3e09aa9b0719e84d05d9d13a9bd68343ff44f596fd379553ded82f4c6` tại hạng `#1`, hydrate qua `Consumer` trả **`7`** mục đọc kèm (`unit_reads`).
  2. **Câu tuổi lái mô tô** (`dev-driving_age-2`): hit `c_30a64fc1bea93d7860d4f3821af382006956ca7dcbdc7770e636782e97fb1d9e` tại hạng `#6`, hydrate qua `Consumer` trả **`16`** mục đọc kèm (`unit_reads`).
  3. **Câu hàng bảng** (`dev-night_horn-2`): hit `tr_03f3ae425e4a1930d6081703c72e22aba780a4cdfd1402625e9ce8081e6308e6` (`table-retrieval.v1`) tại hạng `#9`, hydrate qua `Consumer` trả **`4`** mục đọc kèm.
- **Fail-fast khi thiếu model hoặc sai binding/hash/version:**
  - Thiếu model/revision trong cache (`local_files_only=True`) → ném `RuntimeError` ngay lúc khởi động.
  - Sai hash, sai version, lệch thứ tự vector hoặc lệch hash danh sách truy vấn → `load_dense_bundle()` ném `ValueError` ngay lập tức.

### Phần bàn giao cho Long (`runs/`)
- Các bảng xếp hạng Top-10 tái chạy trên bộ vector mới: `bm25_only.top10.jsonl`, `dense_only.top10.jsonl`, `hybrid_rrf.top10.jsonl`, `hybrid_rrf_rerank.top10.jsonl`, kèm `rrf_top30_rerank_audit.50q.jsonl` (`1,500` dòng).
- Danh sách cặp thay đổi Top-10 (để `relevance: null`, không gán mặc định `0`):
  - `runs/top10_diff_vs_handoff002.jsonl`: `0` cặp thay đổi so với `handoff-002`.
  - `runs/top10_diff_vs_handoff001.jsonl`: `22` cặp thay đổi so với `handoff-001`.
  - `runs/top10_diff_bm25_vs_hybrid.jsonl`: `1198` cặp khác biệt giữa BM25 và Hybrid.
