# Vietnamese Legal Semantic Search ⚖️

Hệ thống tìm kiếm ngữ nghĩa và kết hợp (Hybrid Search) dành cho văn bản pháp luật Việt Nam, giúp giải quyết các hạn chế của phương pháp tìm kiếm từ khóa truyền thống (Keyword Search).

---

## 🚀 Tổng quan dự án (Project Overview)
Phương pháp tìm kiếm từ khóa (*BM25/Keyword*) thường bỏ sót các văn bản pháp luật có cùng ý nghĩa nhưng khác biệt về từ ngữ. Dự án này xây dựng một pipeline thông minh kết hợp giữa **Dense Retrieval** (tìm kiếm vector ngữ nghĩa) và **BM25**, được tối ưu hóa bằng mô hình **Reranker** để nâng cao độ chính xác (*Recall@K, MRR, NDCG*) khi tra cứu văn bản pháp luật.

---

## 📂 Cấu trúc thư mục (Project Directory Structure)

```text
legal_search_project/
│
├── .env                  # Lưu biến môi trường (API keys, Qdrant URL, DB config...)
├── .gitignore            # Các file/thư mục Git không muốn push lên (venv, __pycache__, data, .env)
├── README.md             # Giới thiệu dự án, hướng dẫn setup và chạy
├── requirements.txt      # Danh sách thư viện Python (FastAPI, qdrant-client, sentence-transformers, v.v.)
├── Dockerfile            # Cấu hình đóng gói Docker cho backend
├── docker-compose.yml    # Chạy service (FastAPI + Qdrant DB) nhanh chóng bằng Docker
│
├── data/                 # Chứa dữ liệu 
│   ├── raw/              # Dữ liệu văn bản pháp luật gốc (PDF, JSON, CSV...)
│   └── processed/        # Dữ liệu đã làm sạch, tách đoạn (chunking)
│
├── src/                  # Mã nguồn chính của dự án
│   ├── config.py         # Quản lý cấu hình, đọc biến từ file .env
│   ├── ingestion/        # Xử lý dữ liệu đầu vào (Parser, Chunker, Embedder)
│   ├── database/         # Tương tác với Qdrant Vector Database
│   ├── search/           # Core thuật toán tìm kiếm (BM25, Dense, Hybrid, Reranker)
│   ├── api/              # Xây dựng Backend API (FastAPI routes)
│   └── frontend/         # Giao diện người dùng (Streamlit app)
│
├── notebooks/            # Jupyter Notebooks phục vụ thử nghiệm và đánh giá (Recall, NDCG, Latency)
└── tests/                # Unit test và Integration test cho hệ thống