## Giai đoạn 1: Data Ingestion Pipeline (Luồng nạp và xử lý dữ liệu)
**Phụ trách:** Kỹ sư Dữ liệu (Data Engineering)

Luồng nạp dữ liệu (Ingestion Pipeline) là giai đoạn đầu tiên và then chốt của hệ thống Semantic Search. Giai đoạn này chịu trách nhiệm thu thập các văn bản quy phạm pháp luật dạng thô (.docx, .pdf) và chuyển đổi chúng thành các biểu diễn không gian vector cùng chỉ mục từ vựng, sẵn sàng cho việc truy vấn tốc độ cao. 

Kiến trúc Ingestion Pipeline được thiết kế chạy Offline (Batch Processing) theo một chiều tuần tự qua 4 bước:

### Bước 1: Data Cleaning (Làm sạch và Chuẩn hóa)
* **Thực thi:** `src/ingestion/cleaner.py`
* **Đầu vào:** Văn bản gốc tại `data/raw/` (Luật 35, Luật 36, NĐ 168, NĐ 165).
* **Đầu ra:** Các file `.txt` được lưu tại `data/processed/cleaned/`.
* **Logic cốt lõi:** Quét toàn bộ văn bản, áp dụng các bộ lọc RegEx để xóa bỏ header/footer, số trang, khoảng trắng/ký tự newline thừa. Đặc biệt, chuyển đổi bảng mã văn bản về chuẩn `Unicode NFC` nhằm đảm bảo tính nhất quán định dạng ký tự tiếng Việt.

### Bước 2: Context-Aware Chunking (Bóc tách nhận thức ngữ cảnh)
* **Thực thi:** `src/ingestion/chunker.py` (kết hợp logic parser).
* **Đầu vào:** File text sạch tại `data/processed/cleaned/`.
* **Đầu ra:** File `data/processed/corpus_chunks.jsonl` (Tạo ra 1.457 chunks).
* **Logic cốt lõi:** Không cắt chunk theo số token cố định để tránh gãy ngữ nghĩa. Dữ liệu được cắt theo cấu trúc luật (Chương $\rightarrow$ Điều $\rightarrow$ Khoản/Điểm). Hệ thống tạo ra 2 trường riêng biệt:
  * `original_text`: Giữ nguyên văn bản để hiển thị lên UI.
  * `enriched_text`: Nối tiền tố ngữ cảnh (Tên Luật > Chương > Điều) vào trước nội dung Khoản để chống "mất dấu ngữ nghĩa", phục vụ riêng cho bước nhúng Vector và BM25.

### Bước 3: Semantic Embedding (Nhúng Vector Ngữ Nghĩa)
* **Thực thi:** `src/ingestion/embedder.py`
* **Đầu vào:** File `corpus_chunks.jsonl`.
* **Đầu ra:** File `data/processed/corpus_embedded.jsonl`.
* **Logic cốt lõi:** Load mô hình tiếng Việt chuyên dụng `bkai-foundation-models/vietnamese-bi-encoder`. Mô hình quét qua trường `enriched_text` của mỗi chunk và sinh ra một chuỗi ma trận số (Vector) gồm 768 chiều. Biểu diễn này giúp hệ thống so khớp sự tương đồng về nghĩa (vd: "phạt tiền" và "xử phạt hành chính").

### Bước 4: Dual-Indexing (Lưu trữ và Lập chỉ mục kép)
Kết thúc Ingestion, dữ liệu được phân tán vào 2 cơ sở dữ liệu để phục vụ mô hình tìm kiếm lai (Hybrid Search):
1. **Dense Index (Lưu Vector):** Sử dụng `src/database/qdrant_setup.py` để nạp 1.457 vector cùng toàn bộ Metadata (Payload) vào **Qdrant DB**.
2. **Sparse Index (Lưu Từ Khóa):** Sử dụng `src/database/bm25_store.py` để tính toán ma trận TF-IDF trên tập `enriched_text`, xây dựng bộ Inverted Index (BM25Okapi) và lưu đóng gói xuống ổ cứng tại `qdrant_db/bm25_index.pkl` để load siêu tốc khi API Backend khởi động.

**$\rightarrow$ Kết quả:** Data Pipeline hoàn thành, giao tiếp với lớp Backend API (Giai đoạn 2) thông qua "Hợp đồng dữ liệu" định nghĩa tại `schemas/chunk_schema.json`.