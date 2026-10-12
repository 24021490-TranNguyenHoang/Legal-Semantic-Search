## 1. Phạm vi Dữ liệu (Data Scope)

### 1.1. Dữ liệu trong phạm vi (In-scope)
Hệ thống tập trung xử lý và truy xuất thông tin trong miền tri thức **Pháp luật Giao thông Đường bộ Việt Nam mới nhất (hiệu lực từ 2025)**. Tập ngữ liệu đầu vào (`data/raw/`) được quản lý nghiêm ngặt qua tệp `MANIFEST.csv`, bao gồm 04 văn bản quy phạm pháp luật cốt lõi:
1. **Luật 35/2024/QH15:** Luật Đường bộ (Hiệu lực: 01/01/2025).
2. **Luật 36/2024/QH15:** Luật Trật tự, an toàn giao thông đường bộ (Hiệu lực: 01/01/2025).
3. **Nghị định 168/2024/NĐ-CP:** Quy định chi tiết một số điều và biện pháp thi hành Luật Trật tự, an toàn giao thông đường bộ.
4. **Nghị định 165/2024/NĐ-CP:** Tổ chức và hoạt động của lực lượng bảo vệ an ninh, trật tự ở cơ sở (hoặc các nghị định hướng dẫn liên quan trực tiếp đã khai báo).

### 1.2. Ranh giới ngoài phạm vi (Out-of-scope)
Để đảm bảo độ chính xác và tập trung cho mô hình truy hồi, hệ thống KHÔNG xử lý:
* Các văn bản luật giao thông thuộc lĩnh vực khác (Đường thủy nội địa, Hàng hải, Hàng không, Đường sắt).
* Các văn bản pháp luật cũ, đã hết hiệu lực (ví dụ: Luật Giao thông đường bộ 2008).
* Các văn bản dự thảo, công văn hướng dẫn nội bộ, hoặc tin tức báo chí không mang tính quy phạm pháp luật.

---

## 2. Tiêu chuẩn Đầu ra & Hợp đồng Dữ liệu (Data Contract)
Phạm vi của Data Pipeline kết thúc tại bước sinh dữ liệu chuẩn để nạp vào Database. Đầu ra bắt buộc phải tuân thủ **Hợp đồng dữ liệu** được định nghĩa tại `schemas/chunk_schema.json`.

**Cấu trúc Context-Aware Chunking (Cắt chunk nhận thức ngữ cảnh):**
Thay vì cắt theo độ dài token cố định (Fixed-size), dữ liệu được cắt theo cấu trúc phân cấp (Structural) đến đơn vị nhỏ nhất là Khoản/Điểm. Mỗi đơn vị dữ liệu xuất ra tệp `corpus_chunks.jsonl` cam kết cung cấp 2 trường thông tin tách biệt:
* **`original_text`**: Nội dung nguyên bản của Điều/Khoản để trả về cho Frontend (UI) hiển thị gọn gàng.
* **`enriched_text`**: Nội dung được tự động nối thêm siêu dữ liệu (Tên Luật > Chương > Tên Điều) nhằm bảo toàn ngữ nghĩa pháp lý vĩ mô, phục vụ riêng cho tác vụ mã hóa Vector và Inverted Index.

---

## 3. Ranh giới Kỹ thuật (Technical Scope)
Phạm vi thực thi của Data Engineering Pipeline (`src/ingestion/`) bao gồm 3 hạng mục:
1. **Data Cleaning:** Chuẩn hóa toàn bộ văn bản về bảng mã `Unicode NFC`, loại bỏ ký tự rác, khoảng trắng thừa, header/footer của file DOCX/PDF.
2. **Embedding:** Mã hóa `enriched_text` thành Vector 768 chiều bằng mô hình `bkai-foundation-models/vietnamese-bi-encoder`.
3. **Dual-Indexing:** Khởi tạo luồng lưu trữ kép:
   * Lưu Vector & Payload Metadata vào **Qdrant DB** (phục vụ Dense Retrieval).
   * Khởi tạo và lưu Inverted Index dạng pickle vào **BM25_Store** (phục vụ Sparse Retrieval).

---

## 4. Metrics Mục tiêu (Định lượng Data Pipeline)
* **Khối lượng xử lý:** Hoàn thành trích xuất và Indexing thành công **1.457 chunks** từ 4 văn bản luật.
* **Tỷ lệ bao phủ (Coverage):** 100% các Điều/Khoản trong file thô phải được parser bóc tách thành chunk, không được phép rớt dữ liệu (Data loss = 0%).
* **Tính hợp lệ (Schema Validity):** 100% chunks đầu ra pass qua bộ test kiểm duyệt cấu trúc của `chunk_schema.json` trước khi Backend API được phép truy xuất.