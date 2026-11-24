import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HANDOFF_DIR = ROOT / "artifacts" / "v6_hybrid_handoff"
DOC_PATH = ROOT / "docs" / "handoff" / "Retrieval_V6_Hybrid_Handoff.md"
ZIP_PATH = ROOT / "artifacts" / "vtls-retrieval-v6-hybrid-handoff-001.zip"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((HANDOFF_DIR / "handoff_manifest.json").read_text(encoding="utf-8"))
    dense_m = manifest["dense_manifest"]
    audit = dense_m["tokenizer_audit_summary"]
    bindings = manifest["source_bindings"]

    # 1. Generate SHA256SUMS.txt for all files inside v6_hybrid_handoff
    files = sorted(
        [p for p in HANDOFF_DIR.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"],
        key=lambda p: p.relative_to(HANDOFF_DIR).as_posix(),
    )
    sha_lines = []
    inventory_md_rows = []
    for f in files:
        rel = f.relative_to(HANDOFF_DIR).as_posix()
        digest = sha256_file(f)
        size_b = f.stat().st_size
        sha_lines.append(f"{digest}  {rel}")
        inventory_md_rows.append(f"| `{rel}` | {size_b:,} | `{digest[:16]}...` |")

    (HANDOFF_DIR / "SHA256SUMS.txt").write_text("\n".join(sha_lines) + "\n", encoding="ascii")

    # 2. Write formal handoff markdown for Huy, Hung, Long
    doc_text = f"""# Bàn giao Retrieval Hybrid & Reranking v6 (`vtls-retrieval-v6-handoff.v1`)

- **Người thực hiện:** Trần Nguyễn Hoàng (Retrieval Lead)
- **Thời điểm tạo:** `{manifest["created_at"]}`
- **Môi trường:** Python `{manifest["environment"]["python_version"]}` · PyTorch `{manifest["environment"]["torch_version"]}` · `bm25s=={manifest["environment"]["bm25s_version"]}`
- **Ràng buộc dữ liệu nguồn (giữ nguyên seal từ Huy):**
  - `dataset_version`: `{bindings["dataset_version"]}`
  - `index_version`: `{bindings["index_version"]}`
  - `dataset_manifest_sha256`: `{bindings["dataset_manifest_sha256"]}`
  - `index_manifest_sha256`: `{bindings["index_manifest_sha256"]}`
  - `queries_manifest_sha256`: `{bindings["queries_manifest_sha256"]}`

---

## 1. Kiến trúc & Thông số Pipeline

1. **Lexical Retriever (Huy's Frozen Index):** Đọc trực tiếp chỉ mục Lucene BM25 (`k1=1.2, b=0.75, delta=0.5`) từ `vtls-bm25s-subset-v2-001` trên toàn bộ `139` target (`126 chunk.v1`, `9 table-retrieval.v1`, `4 source-retrieval.v1`).
2. **Dense Retriever (`BAAI/bge-m3`):**
   - Tensor lưu tại `dense_bge_m3/embeddings.npy` kích thước `(139, 1024)` (`float32`, `CLS` pooling, chuẩn hóa L2, SHA-256: `{dense_m["embeddings_npy_sha256"]}`).
   - **Tokenizer Budget Audit:** Min `{audit["min_tokens"]}`, Median `{audit["median_tokens"]}`, P95 `{audit["p95_tokens"]}`, Max `{audit["max_tokens"]}` token. **`0 / 139` bản ghi vượt ngưỡng 512/1024/2048** (không cắt cụt nội dung điều luật hay bảng biểu).
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
{chr(10).join(inventory_md_rows)}
"""
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(doc_text, encoding="utf-8")

    # 3. Package reproducible ZIP archive
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(HANDOFF_DIR.rglob("*"), key=lambda x: x.relative_to(HANDOFF_DIR).as_posix()):
            if p.is_file():
                zf.write(p, arcname=f"v6_hybrid_handoff/{p.relative_to(HANDOFF_DIR).as_posix()}")
        zf.write(DOC_PATH, arcname="Retrieval_V6_Hybrid_Handoff.md")

    zip_sha = sha256_file(ZIP_PATH)
    ZIP_PATH.with_suffix(".zip.sha256").write_text(f"{zip_sha}  {ZIP_PATH.name}\n", encoding="ascii")
    print(f"Created handoff doc: {DOC_PATH}")
    print(f"Created SHA256SUMS : {HANDOFF_DIR / 'SHA256SUMS.txt'}")
    print(f"Created ZIP bundle : {ZIP_PATH} ({ZIP_PATH.stat().st_size:,} bytes)")
    print(f"ZIP SHA-256        : {zip_sha}")


if __name__ == "__main__":
    main()