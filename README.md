# Legal Semantic Search

Hệ thống tìm kiếm ngữ nghĩa và kết hợp từ khóa cho văn bản quy phạm pháp luật giao thông đường bộ Việt Nam (như Luật Trật tự, an toàn giao thông đường bộ `35.2024.QH15` và Nghị định `168.2024.NĐ-CP`), tích hợp FastAPI backend và giao diện Streamlit.

## Kiến trúc tìm kiếm (`src/search/`)

Pipeline tìm kiếm được thiết kế theo hướng mô-đun hóa:

1. **BM25 Searcher (`src/search/bm25.py`)**: Tìm kiếm khớp từ khóa dựa trên `rank_bm25`, lọc các kết quả có điểm `<= 0.0` trước khi hợp nhất xếp hạng để tránh nhiễu.
2. **Dense Searcher (`src/search/dense.py`)**: Sinh vector 768 chiều bằng mô hình `bkai-foundation-models/vietnamese-bi-encoder` (bật `normalize_embeddings=True`) và truy vấn trên Qdrant theo độ đo Cosine.
3. **Hybrid Searcher (`src/search/hybrid.py`)**: Hợp nhất kết quả từ BM25 và Dense bằng thuật toán **RRF (Reciprocal Rank Fusion)**, phân định khóa tài liệu rõ ràng theo `chunk_id` / `law_id` + `article_title` / `citation_path` để tránh gộp nhầm nhiều điều khoản của cùng một văn bản.
4. **Reranker (`src/search/reranker.py`)**: Xếp hạng lại các ứng viên hàng đầu nhằm cải thiện độ chính xác ở vị trí Top 1 cho các truy vấn pháp lý.

## Công nghệ sử dụng

- **Ngôn ngữ & Runtime**: Python 3.11 (khuyến nghị chạy với `-X utf8` trên Windows)
- **Vector Database**: Qdrant
- **Embedding & Rerank**: `sentence-transformers` (`bkai-foundation-models/vietnamese-bi-encoder`, 768-d), `rank_bm25`
- **API & Giao diện**: FastAPI (`uvicorn`), Streamlit

## Chạy hệ thống cục bộ

### 1. Khởi động Qdrant
Đảm bảo dịch vụ Qdrant đang chạy (qua Docker hoặc bản cài đặt cục bộ) và đã nạp dữ liệu vào collection chính.

### 2. Chạy Backend API (FastAPI)
```cmd
python -X utf8 -m uvicorn src.api.main:app --reload