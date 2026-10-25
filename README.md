# BÁO CÁO CHI TIẾT TIẾN ĐỘ VÀ KIẾN TRÚC HỆ THỐNG: LEGAL SEMANTIC SEARCH

## 1. Xây dựng và Tổ chức Cấu trúc Dữ liệu & Ingestion Pipeline

Phần này chịu trách nhiệm tiền xử lý, băm nhỏ tài liệu pháp luật và đồng bộ hóa vào các kho lưu trữ phục vụ tìm kiếm đa mô hình.

* **Tự động hóa nạp tài liệu:**
* Xây dựng script `run_ingest.py` có khả năng tự động quét toàn bộ các file văn bản luật định dạng `.txt` nằm trong thư mục `data/processed/cleaned/` (bao gồm Luật Đường bộ 2024, các Nghị định xử phạt vi phạm hành chính, v.v.).

* **Xử lý Chunking & Indexing:**
* Tự động phân đoạn, cắt nhỏ văn bản pháp luật theo cấu trúc từng điều luật (Articles).


* Chuyển đổi các đoạn văn bản (chunks) thành vector số học thông qua mô hình Embedding `SentenceTransformer` (`all-MiniLM-L6-v2`) và thực hiện thao tác upsert toàn bộ vector lên **Qdrant Vector DB**.


* **Hỗ trợ BM25 Baseline:**
* Tự động tổng hợp và lưu trữ toàn bộ dữ liệu cấu trúc vào file `data/processed/chunks.json` nhằm cung cấp nguồn dữ liệu chuẩn cho thuật toán tìm kiếm từ khóa truyền thống BM25.



---

## 2. Phát triển Backend & Các chiến lược tìm kiếm (Search Strategies)

Hoàn thiện toàn bộ các module cốt lõi đặt trong thư mục `src/search/` tuân thủ chặt chẽ theo bản thiết kế (blueprint) của đồ án:

* **Dense Search (`dense.py`):**
* Thực hiện tìm kiếm dựa trên vector không gian ngữ nghĩa, giúp hệ thống hiểu được ý định sâu xa của người dùng ngay cả khi không dùng đúng từ khóa chính xác trong luật.


* **BM25 Search (`bm25.py`):**
* Thực hiện tìm kiếm dựa trên tần suất từ khóa truyền thống (keyword-based matching), tối ưu hóa tuyệt đối cho việc tra cứu mã điều khoản, số hiệu cụ thể.


* **Hybrid Search (`hybrid.py`):**
* Kết hợp hài hòa, đồng thời giữa tìm kiếm ngữ nghĩa (Dense) và tìm kiếm từ khóa (BM25) nhằm tối ưu hóa độ bao phủ tài liệu (`Recall`), hạn chế tối đa việc bỏ sót thông tin.


* **Reranker (`reranker.py`):**
* Tích hợp tầng chấm điểm lại (Cross-Encoder Reranker) ở giai đoạn cuối để tinh chỉnh, lọc sâu và đưa điều luật có độ chính xác cao nhất lên vị trí Top đầu.



---

## 3. Hoàn thiện Giao diện Streamlit Frontend (`app.py`)

Xây dựng một giao diện web trực quan, thân thiện với người dùng để trực tiếp demo sản phẩm:

* **Giao diện Chatbot trực quan:**
* Xây dựng khung chat tương tác thời gian thực, hiển thị câu trả lời tổng hợp dạng RAG kết hợp với các thẻ trích dẫn nguồn luật chi tiết (tên điều luật, điểm số confidence score, nội dung văn bản trích dẫn).


* **Thanh Sidebar tùy chỉnh chiến lược:**
* Thiết kế thanh điều khiển bên trái cho phép người dùng linh hoạt chuyển đổi qua lại giữa 4 chiến lược tìm kiếm (*Dense Search, BM25 Search, Hybrid Search, Hybrid + Reranker*) ngay lập tức.


* **Tích hợp khung giải thích chiến lược:**
* Bổ sung các hộp thông tin chú thích chi tiết ngay trên Sidebar giúp người xem (thầy cô/hội đồng) dễ dàng phân biệt sự khác biệt về bản chất, ưu điểm và loại kết quả của từng thuật toán.



* **Đo lường Latency Benchmark trực tiếp:**
* Tự động đo đạc thời gian thực thi và hiển thị trực quan thông số trễ (`⚡ Thời gian phản hồi: 0.XXXXs`) ngay dưới mỗi câu trả lời, phục vụ đắc lực cho việc đánh giá hiệu năng hệ thống.



---

## 4. Xây dựng Module Evaluation Benchmark (`evaluate.py`)

Hoàn thiện phần đánh giá định lượng mang tính học thuật cao cho đồ án:

* Viết script đánh giá tự động độc lập (`evaluate.py`) chạy trên một bộ câu hỏi kiểm thử chuẩn (test set) định sẵn.

* Đo lường các chỉ số học thuật quan trọng gồm **MRR (Mean Reciprocal Rank)** và **Recall@3** nhằm so sánh trực quan, minh bạch hiệu quả hoạt động giữa các chiến lược *Dense*, *BM25* và *Hybrid*, tạo cơ sở dữ liệu vững chắc cho slide báo cáo bảo vệ đồ án.

