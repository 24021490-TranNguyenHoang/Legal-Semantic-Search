# NĐ168 Điều16 Khoản2 — khôi phục hẹp từ HTML, đối chiếu scan

Policy `nd168-a16k2-html.v1`, snapshot tham chiếu 2025-01-01. CLI
`src.nd168_a16k2 build/validate`; không đổi parser/extraction/chunker cũ.

## Chọn nguồn và giới hạn

Ưu tiên text chính thức khi đối chiếu được đúng vùng. Lượt này đã capture
bản toàn văn trên Xây dựng chính sách — Cổng Chính phủ, xác định đúng
NĐ168/2024/NĐ-CP ngày26/12/2024 và so title/lead/từng Điểm với ảnh PDF
đã capture trang40–41. Không cần phiên âm hoặc OCR để làm nguồn text.
HTML được tải hiện tại; ngày bài/metadata là 03/04/2025, sau snapshot.
Khớp vùng scan không chứng minh website đã có cùng nội dung ở snapshot,
không tự xác nhận lịch sử sửa đổi/hiệu lực hoặc toàn văn.

PDF scan cũ giữ URL/SHA/thời điểm thu thập thật, ảnh40–41 có hash. Quan
sát thêm trang1 chỉ xác định số/ngày/tên nghị định, không map thêm Điều.
Không xác minh chữ ký số hoặc đặt thêm cổng người dùng.

## Nguồn và extraction

DDD đã có method=html_text; Stage3 reader hiện chỉ thực thi DOCX/PDF.
Bổ sung **reader/mapping hẹp trong module này**, không nới enum/schema,
không biến HTML thành DOCX hoặc pdf_text. Source facts/prepared JSONL
đủ trường source_file và UUIDv5 source-file.v1 hiện có, giữ pending riêng.
Không giả bundle đăng ký Stage2 hoặc INSERT document/corpus để thỏa FK.

Byte HTML/capture JSON, PDF và hai ảnh được chụp vào run mới. URL/time
HTML lấy từ request thật; PDF lấy từ capture gốc. Chuẩn hóa UTC `Z` chỉ
đổi biểu diễn timezone. Không lấy thời điểm chạy thay ngày tải nguồn.
Capture metadata cũng khóa bằng SHA riêng.

Chỉ chọn document/chapterII/section2 title, Article16 title, lead Khoản2
và toàn bộ năm paragraph Điểm a,b,c,d,đ. DOM selector articleBody/heading
phải duy nhất; ordinal kiểm qua heading/marker thực trước vùng được chọn.
HTML không có đúng năm Điểm hoặc có nội dung ngoài khả năng trong block
đã chọn phải fail, không đoán. Ads/iframe ở ngoài vùng không được trích.

Reader nối text inline, giải mã HTML entities theo lxml, div/br trong
heading thành LF có quy tắc; không strip/fold/lowercase/sửa dấu hoặc
đánh lại ký hiệu. Dùng lại Stage3 extraction_normalizer NFC/LF và LF
giữa block. Giữ whitespace/NBSP/trailing space trong nội dung nguồn.

normalized.txt UTF-8 không BOM là artifact mới bất biến. Trace giữ XPath
HTML, selection_key, raw fragments, separator và absolute code-point
offsets. Extraction ID theo extraction.v1 với file_id, raw hash, method,
tool/code/normalizer/lxml/Python/Unicode, config và text/trace hashes.
Review timestamp không tham gia identity; created_at là thời điểm chạy.
Metadata extraction dùng schema DDD hiện có, review_status=pending.

**Ba namespace không trộn:** source_span offsets trên normalized.txt HTML
mới; diff offsets tương đối trong field cũ/mới; PDF confirmation chỉ
page/region mô tả và image hash. Không có PDF text offset hoặc tọa độ
tự đoán. Locator span là HTML XPath thật, không bịa DOCX/PDF locator.
Nguồn scan là bằng chứng đối chiếu, không gán scan làm nguồn của text HTML.

## Cây chọn lọc, IDs và context

Cây đúng 10 nút: document → ChươngII → Mục2 → Điều16 → Khoản2 → năm
Điểm. Ordinal nguồn lần lượt 0/1/1/3/1, Điểm0..4; không sinh Khoản1 hoặc
Điều13–15 giả để lấp khoảng trống. Document/Chương/Mục giữ title thật,
own text không được chọn và được ghi rõ là sparse projection; không khẳng
định preamble hoặc toàn body của các cha rỗng/đã rà.

Dùng nguyên unit.v1 và source-span.v1. Title/own text là lát của extraction
mới; parent hoàn tất trước con, LF nối spans. Cùng toàn identity payload
thì giữ ID; đổi source file/extraction đơn thuần không đổi unit ID.
Crosswalk ghi từng field identity thay đổi, quan hệ cha đổi dây chuyền,
và các Điểm mới không có legacy unit. Không tạo old ID cho vùng cách ly.

Builder Điểm/policy `leaf-clause-point-context.v1` dùng lại nguyên byte:
target = own text từng Điểm; context = title Điều, lead Điều nếu có
(ở đây rỗng hợp lệ), lead Khoản2. Context title giữ loại xe máy chuyên
dùng/kể cả rơ moóc; lead giữ mức phạt. Không đưa anh em hoặc Khoản1 vào.
Không thêm target từ câu dẫn mức phạt. Không mở rộng dẫn chiếu ngoài cây.

Encoder/preprocessing/budget256 gồm special giữ nguyên; đếm thực trên
encoder_text. Vượt budget thì giữ nguyên candidate/context ở quarantine,
không truncate. Ký tự còn chưa chắc trong hồ sơ review tạo issue và chặn
preview thay vì đoán; kết quả hiện tại không có ký tự chưa đọc rõ trong
vùng đã chọn, nhưng vẫn agent_review, chưa human/verified.

Scope là proposal riêng theo BRD3.1: năm Điểm included vì chế tài trực tiếp
người điều khiển tham gia giao thông; title/lead supporting đúng dependency;
cha cấu trúc không tự được gán scope. Binding gồm unit/hash, extraction,
HTML/PDF hash và snapshot; không mang proposal/decision DOCX sang nguồn mới.
Applicability và hiệu lực luôn pending/null trong preview này.

## Replay và output

Run giữ sources/evidence/legacy snapshot, extraction, units/spans, comparison
đầy đủ, crosswalk, scope proposals, preview/context/encoder/issues/quarantine,
bản cây và báo cáo dễ đọc, manifest/report. Validator kiểm source/capture/
image hashes, DDD shape/relations/IDs/roundtrip, legacy snapshot binding,
replay reader/mapping/builder/tokenizer, source facts và mọi output.
Reseal sau sửa text/trạng thái không thay kết quả replay hợp lệ.

Exit0 = preview kỹ thuật hoàn tất; 2 = có blocked/quarantine; 1 = lỗi
input/runtime/binding. Không corpus/assessment verified, embedding/index
hoặc sửa dữ liệu đang dùng. Cần giữ coverage/tokenizer assets referenced
để replay, không quảng bá run là gói portable độc lập.

Xem [Verification và lệnh](../../reviews/ND168_A16K2_Recovery_Verification.md).
