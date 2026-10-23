# Quyết định biểu diễn ưu tiên ba Thông tư v1.2

Ngày2026-10-23, snapshot2025-01-01. Đây là revision preview/pending, không
thay schema DDD v1 hoặc artifact đã phát hành. Quyết định kỹ thuật của agent,
không phải chấp thuận scope/hiệu lực của reviewer.

1. DDD v1 có table/table_row nhưng chunk yêu cầu slice own text của legal_unit;
   các ô TT38 nằm ngoài own text. Không thể gán hàng dẫn xuất thành nguyên văn.
   Chọn retrieval projection riêng `table-retrieval.v1`: owner_unit_id thật,
   source_original/cells/rows/context tách search_text dẫn xuất. ID tr_ hash
   toàn payload có policy và source proof, không giả chunk.v1 hoặc unit mới.
   Validator replay từ bảng nguồn và tokenizer. Downstream muốn dùng phải
   chấp nhận record_type mới; adapter dataset hiện hành chưa hỗ trợ, giữ blocker.
2. TT35 có Phần ngoài enum DDD v1, Chương lặp số theo Phần. Revision graph
   pending cho phép part, dùng lại unit.v1 với canonical_path/citation/parent
   thật. Part/Chapter lấy marker/title có span; không đổi own text Điều/con.
   Thứ tự theo nguồn. Canonical path chứa part trước chapter; ID con đổi do
   parent/path/citation/ordinal, có crosswalk. Không ép giữ ID sparse cũ.
   Chỉ schema graph sidecar mới, không nới schema chính thức. Title bao gồm
   marker nguồn để tái dựng không cần tự thêm ký hiệu. Preview target dùng
   builder/encoder cũ trên graph mới, không copy ID chunk cũ qua binding mới.
3. Giữ budget256 và preprocessing. Điểm b TT38 vẫn toàn dependency a/bảng3;
   chưa có chứng minh tách an toàn thì quarantine. Không xóa cờ bằng tay.
4. Scope proposal cũ nối qua crosswalk + hash nội dung, không thành accepted.
   Technical pass không xác nhận provenance/edition/applicability. Các dẫn
   chiếu ngoài cây cha được liệt kê riêng; chưa giải nghĩa tự động.
5. Pilot QCVN chỉ PDF7/214/300/368, render và text reader thực. Transcription
   hẹp do agent đọc ảnh lưu riêng, page-level region (không bịa bbox ký tự),
   offset trên UTF8/NFC/LF mới. Không đổi normalized cũ, không tạo unit/chunk.
   Trang phụ thuộc hình giữ dependency, không suy nghĩa biển từ hình.

CLI bổ sung trong src.tt38_preview, tính toán revision nằm trong module nhỏ
src.ingestion.circular_priority để giữ nguyên module hash-bound lịch sử.
Manifest bind input SHA, code/schema/config; validate replay nội dung, IDs,
spans, source checks và token không truncate. Giữ serving/release=false.

Leaf-article adapter hẹp dùng policy `leaf-article-part-ancestry.v1` cho ba
Điều lá đã có preview; tái dùng own text/title/context formula và source_proof,
kiểm graph trước khi rebind, đếm lại token và chunk.v1. Không sửa RANK toàn
cục của builder cũ. Khoản/Điểm dùng builder cũ nguyên byte. Source proof của
TT35 tương đối run mới (tt35/); TT38 text copy nguyên ID/proof từ input tables/base,
consumer phải resolve proof tại binding.tables.parent/base. Table records ghi
source_proof_base_ref rõ theo repo. Tất cả là preview, downstream dataset v1
chưa nhận graph Part hoặc table record; cần adapter revision trước đóng gói.
