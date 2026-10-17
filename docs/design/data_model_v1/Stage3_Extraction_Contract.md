# Stage 3 — Extraction có truy vết từ nguồn pending

Snapshot sản phẩm: **2025-01-01**. Người dùng cho phép extraction kỹ thuật trên
nguồn pending trong staging. Extraction không xác minh nguồn, bản ban hành,
thời điểm thu thập, hiệu lực hoặc phạm vi. Inference vẫn bị Windows chặn;
Stage 3 không cần model. Parser/chunker và cleaner prototype được giữ nguyên.

## Pending và schema chính thức

Đầu vào là manifest Stage 2 đạt kiểm tra kỹ thuật, dù release_eligible=false.
Stage 3 chụp nguyên các artifact của bundle nguồn vào `source_snapshot/`, giữ
file_id/law_id/raw hash và mọi evidence null. Không sửa run nguồn. Bản chụp có
content.sqlite chính thức trống; không tạo legal_document/source_file/corpus giả.

`extraction.pending.sqlite` là DB riêng theo `schemas/extraction_v1/pending_schema.sql`:

- pending_source giữ bản ghi nguồn pending đã đối chiếu với Stage 2.
- pending_extraction giữ metadata extraction và FK tới pending_source.
- pending_locator giữ cây locator, FK extraction/cha cùng extraction, offsets.
- pending_extraction_issue giữ cảnh báo/lỗi, FK nguồn và extraction khi có.

Kết nối ghi bật foreign_keys trước transaction; validator mở DB read-only,
kiểm tra FK/integrity, schema và so hàng với export. Không nới schema DDD.
Metadata con `extraction` tuân contract DDD hiện có, với review_status=pending;
envelope staging còn lưu source_status=pending, technical_status, config/raw/trace
hash. Đạt kiểm tra hình dạng/byte không làm review_status trở thành verified.

Stage 2 trước đây chỉ nhận DOCX. Để đăng ký fixture PDF đúng chuỗi file_id,
`detect_source_mime` bổ sung nhận diện header `%PDF-`; đây chưa phải kiểm tra PDF
đọc được. Reader Stage 3 chịu trách nhiệm báo/cách ly PDF hỏng. Nhận diện DOCX,
UUID, contract và các run Stage 2 cũ không đổi. Định dạng khác vẫn bị báo lỗi
ở cửa đăng ký hoặc bị reader từ chối; không âm thầm đổi thành DOCX/PDF.

## Reader tách khỏi normalization và cleaning

`src/ingestion/extractors.py` chỉ đọc cấu trúc nguồn và phát cảnh báo.
`src/ingestion/extraction_normalizer.py` chỉ áp dụng NFC và CRLF/CR → LF,
rồi ghép fragment theo quy tắc rõ ràng. Không strip, collapse khoảng trắng,
lowercase, xóa số trang/quốc hiệu/chữ ký hoặc thay văn bản pháp lý bằng lời diễn giải.
CLI mới không gọi clean_text hay parser prototype. Không dùng output này thay
corpus đang phục vụ trong Stage 3.

DOCX đọc gói XML bằng standard library, giữ paragraph và table xen kẽ trong
word/document.xml. Mỗi table → row → physical cell → paragraph/nested table được
duyệt theo thứ tự XML. Không dùng danh sách paragraph riêng rồi nối bảng ở cuối,
không nhân bản text của merged cell theo ô logic. gridSpan/vMerge được giữ trong
locator, chưa suy diễn hoặc điền text cho các ô merge.

Chính sách đọc paragraph: w:t/delText theo thứ tự XML; w:tab → TAB;
w:br/w:cr → LF; noBreakHyphen/softHyphen giữ ký tự Unicode tương ứng.
Không dựng marker đánh số tự động hay đánh giá field. Field, revision, visual,
symbol và note-reference có issue cần rà soát; text con hiện hữu được giữ.
Cấu trúc có nội dung chưa hỗ trợ (ví dụ altChunk) tạo error, file partial.
XML parser có quy tắc entity/line-ending của XML; pre-normalization raw_text
là text do reader giải mã, không phải lát byte XML. ZIP SHA và XPath giữ đường
đối chiếu về byte gốc.

Header/footer/footnote/endnote được đọc thành part riêng, nối sau main body theo
tên part đã sắp. Đây là thứ tự tuần tự hóa có nhãn, **không phải thứ tự trang
render của Word**. Issue ghi rõ việc nối. Không bịa số trang DOCX. Hình/OLE/symbol,
field và revision chưa được hiểu đầy đủ; không coi cảnh báo là xác nhận không mất nghĩa.

PDF dùng pdfplumber/pdfminer.six theo phiên bản và x/y tolerance đã ghi, layout=false.
Mỗi trang có locator page_start=page_end, 1-based và kích thước trang. Trang không
có text vẫn có node với start=end; issue PDF_PAGE_NO_TEXT yêu cầu rà soát trang
rỗng/scan và nhu cầu OCR. Không kết luận mọi trang rỗng là scan và không chạy OCR.
Lỗi đọc một trang tạo error/partial; lỗi mở file tạo quarantine cho cả file.

## Artifact chuẩn hóa và offsets

Mỗi extraction có normalized.txt UTF-8 không BOM, NFC, LF; trace.json có:

- nodes: document/part/paragraph/table/row/cell/page, locator, cha/thứ tự,
  [char_start,char_end), quote_sha256 và locator_id.
- fragments: raw_text trước NFC/LF, hash/độ dài trước và sau, quy tắc và cờ thay đổi.
- separators: vị trí/ký tự/rule nối cấu trúc, không giả làm chữ có trong nguồn.

Paragraph/block/row/page nối LF; cell trong một row nối TAB. LF/TAB nguồn có sẵn
vẫn thuộc fragment; separator tổng hợp có bản ghi riêng. Hàng/ô rỗng giữ vị trí.
Offsets là **Unicode code point của chính normalized.txt**, không phải byte,
token hoặc vị trí ký tự trong raw XML/PDF. Container span bao gồm các separator
con; paragraph/page lá và separator phủ artifact. Locator rỗng được start=end;
chưa chuyển chúng thành source_span DDD vốn cần start<end và legal_unit.

DOCX XPath dùng namespace w, chỉ số XPath 1-based; table_index toàn gói, row_index,
cell_index và paragraph_index vật lý 0-based. XPath đầy đủ là khóa định vị khi có
wrapper/nested table; không dùng index đơn lẻ như định danh pháp lý.
Đầu text U+FEFF chưa có quy tắc hợp lệ sẽ bị từ chối/cách ly, không xóa âm thầm.

## Định danh, tool và thời gian

file_id lấy nguyên từ Stage 2. DDD chỉ yêu cầu extraction_id định danh artifact
bất biến, chưa chốt công thức; Stage 3 cụ thể hóa `e_` + SHA-256 canonical JSON:

```text
identity_schema="extraction.v1", file_id, source_raw_sha256, method,
tool_version, config_sha256, text_sha256, trace_content_sha256
```

trace_content_sha256 tính từ trace trước khi gắn ID, tránh hash tự tham chiếu.
locator_id là hash của extraction_id + node_index + locator. Hash JSON dùng quy
tắc canonical DDD. Không có timestamp/run path trong identity. Cùng byte nguồn,
config, code và tool version cho cùng nội dung/hash/ID; đổi code/config/tool tạo
phiên bản extraction mới. Đây không phải công thức ID unit/chunk hay UUID Qdrant.

tool_version là chuỗi JSON chứa reader, Python, Unicode version, PDF libraries
khi dùng, và SHA code reader/normalizer/pipeline. Config được chụp trong run và
tham gia hash. created_at/built_at là UTC của lần chạy thực tế, không retrieved_at.
Timestamp khác giữa hai run là đúng; không cam kết byte SQLite/manifest giống
nhau vì các tệp đó chứa timestamp. Text/trace/ID ổn định được kiểm tra riêng.

## Lỗi, manifest và validator

Mỗi nguồn có file_status dù thành công, partial hay quarantined. File hỏng/không
hỗ trợ được báo với file_id, ref, loại lỗi; nguồn thô được giữ tại vị trí cũ, không
di chuyển. Batch vẫn lưu phần đọc được và manifest/report, nhưng trả 1 nếu có
partial/quarantine. run_report.status=failed cho batch đó. Bundle lỗi nhập vào,
run dir đã có hoặc đường ghi ngoài staging bị từ chối trước khi tạo output.

technical_valid nói bundle nhất quán; processing_success nói reader hoàn tất
không có error. Một bundle quarantine có thể hợp lệ kỹ thuật nhưng xử lý thất bại.
release_eligible luôn false; lệnh require-release-ready trả 1. Đây là manifest
pending extraction, chưa phải corpus/release manifest. run_report ghi cuối được
loại khỏi checksum; các artifact khác và source snapshot đều được hash, sidecar
manifest.sha256 tránh tự tham chiếu.

Validator đối chiếu Stage 2, checksums, contract/FK/DB export, rồi đọc lại raw với
cùng code/tool/config để tái tạo text, trace, offsets, locator và issue. Nó không
chỉ kiểm tra start/end nằm trong chiều dài. Sau thay code/tool, dùng phiên bản
được khóa để replay run cũ; không sửa artifact cũ để khớp code mới. Quarantine là
hồ sơ lỗi lịch sử, không giả định lỗi tạm thời phải lặp lại khi kiểm tra sau này;
validator giữ cổng thất bại/pending, không tự chuyển file thành thành công.

## Chuyển sang schema chính thức sau khi đủ bằng chứng

Chưa triển khai lệnh promote trong Stage 3:

1. Hoàn tất hồ sơ nguồn theo Stage2_Source_Contract: đúng bản ban hành/đủ phần,
   URL và log thu thập thật; giữ raw và quyết định có bằng chứng.
2. Trong run mới, nạp legal_document và source_file hợp lệ với cùng file_id nếu
   đúng đối tượng byte/law; không tạo bản giả để lách FK của extraction.
3. Đối chiếu text, table/merge, hình, field/revision, PDF/OCR issues với nguồn.
   Khi chỉ thay quyết định review, giữ artifact và extraction_id; audit review
   riêng. Nếu hiệu đính text, đổi extraction/artifact/ID, không sửa offsets cũ.
4. Nạp metadata extraction đúng schema; verified chỉ sau rà soát có bằng chứng.
   legal_unit/source_span được tạo ở stage parser sau, không tạo nút giả ở đây.
5. Hiệu lực/scope tại snapshot và các cổng corpus/index/release vẫn phải hoàn tất.
   Nguồn đủ bằng chứng hoặc extraction verified chưa tự cho phép phát hành.

Không có mâu thuẫn schema cần nới. Lớp pending giải quyết FK cho nguồn chưa đủ
bằng chứng; các chính sách tuần tự hóa/ID ở trên là cụ thể hóa kỹ thuật được ghi
rõ, không thay yêu cầu pháp lý hoặc tự chọn giá trị TBD của chunking/model.
