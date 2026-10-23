# Addendum ingestion ba Thông tư v1.1

Ngày 2026-10-23; tiếp tục công việc 2026-10-22. Snapshot **2025-01-01**.
Kế thừa Source Inventory v0.1, DDD v1.0, contract Stage2–4/Stage6 và
`Source_Inventory_7_And_TT38_Addendum_v1.0.md`. Không sửa các bản đã phát hành,
schema DDD, raw hoặc artifact cũ. Changelog: sửa URL export; thêm preview
hàng bảng TT38, cây thưa TT35 và khảo sát reader TT51/QCVN.

## 1. URL metadata là scalar, không phải object

Lỗi lịch sử nằm trong capture PowerShell: chuỗi từ `Get-Content` mang các
thuộc tính PSPath/PSDrive/PSProvider… được ConvertTo-Json tuần tự hóa thành
object. `gazette_pdf_capture.json.url` và observed record giữ object đó;
exporter cũ chuyển tiếp nguyên object, rồi csv_text serialize thành JSON.
Đó là nguyên nhân trường CSV khoảng46,8 triệu ký tự, không phải URL dài hợp lệ.

Điểm tiếp nhận/export hiện hành `source_inventory.require_url` chỉ chấp nhận
null hoặc **str HTTP(S)** có host, không credentials, whitespace/control,
ngoặc/JSON hoặc chuỗi quá8192 ký tự. Capture mới phải gọi cổng này trước
serialize. Với PowerShell, tạo scalar mới bằng `[string](Get-Content -Raw …)`
rồi `.Trim()`; không chuyển nguyên object có note properties vào JSON.
Không sửa script/capture nằm trong run lịch sử đã seal.

Ngoại lệ migrate duy nhất: wrapper có đúng bộ7 keys của PowerShell, đúng
`PSChildName=gazette_cdn_url.txt`, law TT38; toàn wrapper bằng receipt đã lưu,
SHA/size/accessed_at trùng observed file, HTTP200/valid_pdf, và value xuất hiện
nguyên dạng trong HTML Công báo sau HTML-unescape. Thiếu một điều kiện thì
fail. Không chọn URL theo tên file hay lấy arbitrary `.value`.

`seven-source-export.v1.1` ghi URL scalar252 ký tự, evidence refs tới cả receipt
và HTML thật. Các giá trị unknown giữ null/ô CSV rỗng; không thay ngày tải
lịch sử. Validator đọc CSV bằng csv.DictReader với giới hạn mặc định, so với
JSONL cả dữ liệu scalar và JSON trong các cột evidence_ref được khai báo.
Các export lỗi giữ nguyên; replay bản cũ dùng commit gốc.

## 2. Policy bảng TT38: tt38-cell-row-preview.v1

Tái dùng cây/spans/cells của tt38-preview-003; không parse lại hoặc sửa unit.
Ba bảng đã đối chiếu ảnh PDF trang4/7 (trang in24/27). Mỗi hàng dữ liệu tạo
một ứng viên dẫn xuất gồm:

- unit_id của Khoản/Điểm thực; nguyên văn own text ngoài bảng và source_proof;
- context tổ tiên theo thứ tự Điều rồi Khoản, field/offset/proof;
- header/value cell IDs, row/column/bbox/page, source_slices/quote/hash;
- text_derived từ nhãn header và value nguyên văn, dấu `:`, `/`, LF có quy tắc;
- text_for_search và encoder_text riêng, hash/token đo được, origin=agent_review.

Giữ title Điều6 có ngoại lệ đường cao tốc; đoạn dẫn Khoản phân biệt trong/ngoài
khu dân cư; đầy đủ loại xe, ngưỡng3,5 tấn/28 chỗ, các ngoại lệ ở ô nguồn.
Điều11K2a giữ cả đoạn trước bảng về đường khô ráo/tầm nhìn và đoạn sau bảng về
tốc độ dưới60km/h. Không suy diễn thêm quy tắc cho tốc độ ngoài các hàng nguồn.
Bất đẳng thức `60 < V ≤ 80`, `80 < V ≤ 100`, `100 < V ≤ 120` giữ nguyên.

Điểm b có dependency **đúng Điểm a cùng Khoản và cả bảng3**; toàn văn của a
và b được giữ, không mở rộng dẫn chiếu toàn corpus. Không bỏ context hoặc
chia tùy tiện để ép qua256 token. Ứng viên b279 token nằm quarantine.

DDD yêu cầu chunk.text_original là lát legal_unit.text_original; bảng hiện
đang ở cells, không nằm trong own field. Vì vậy hàng dẫn xuất **chưa phải
chunk DDD**, không tạo legal_unit giả hoặc tự sửa công thức chunk.v1.
ID riêng `tp_ + SHA256(canonical(payload))` chỉ dùng sidecar preview; payload
bao gồm policy, nguyên văn, context/proofs, rows/cells, search/hash và trạng thái.
Thời gian build không tham gia ID. Chín bản đạt budget nằm tables.preview.jsonl;
không trộn vào chunks.preview.jsonl cũ hoặc dataset. Muốn nhập bảng vào dataset
cần quyết định biểu diễn nối DDD/cells có kiểm định; đây vẫn là blocker rõ ràng.
38 chunk/56 context v1 giữ nguyên, CLI build/validate v1 còn replay được.

## 3. TT35: source layout và cây thưa

Stage3 trích toàn69tr bản chính và179tr phụ lục với reader/NFC/LF/trace cũ.
Phải phân biệt trích toàn trang với đọc rà nội dung/ảnh. Adapter sử dụng
grammar paragraph hiện có, ánh xạ toàn bộ spans về PDF gốc. Text nguyên văn,
ID unit.v1/span/chunk.v1 và builder/encoder cũ không thay công thức.

PDF có nền trắng dạng rectangle; loại riêng các rectangle fill trắng không
stroke khỏi **phép đo bảng**, không loại ký tự hoặc sửa extraction. Các đường
viền đen/ô vật lý vẫn giữ; bảng không sinh Khoản/Điểm. Main có11 bảng, annex
có137 bảng/cụm ô được detector đo, cần rà ngữ nghĩa; không tuyên bố148 bảng
đã được rà pháp lý. Merged None slots không nhân bản. Cells giữ source slices.

Thực tế có7 Phần và các Chương đánh số lại theo Phần. DDD chưa có unit_type
Part. Không đổi schema hoặc giả Phần thành Chương. Legal units là **projection
thưa** document→Điều→Khoản→Điểm; header Phần/Chương/title được giữ ở
structure.pending.jsonl. unit_structure_dependencies.jsonl nối từng unit
với ancestor nguồn thực, theo vị trí/chương nằm trong đúng Phần.
SPARSE_PART_CHAPTER_PROJECTION_PENDING là blocker trước nhập DDD chính thức.
Đây chưa phải cây tổ tiên DDD hoàn chỉnh cho TT35. Không suy tất cả phần cha
đều included hoặc tự thêm nội dung cha vào search ngoài policy đã chốt.

Các phụ lục179tr giữ extraction, heading observations, tables/cells/figures,
unprocessed_regions và scope proposal từng vùng. Không chạy grammar thân luật
trên biểu mẫu có “Điều1…”/số thứ tự hoặc đánh đồng annex với excluded.
Phụ lục XI/XII/XXIII (PDF34/35/127) đã đọc text và ảnh, proposed supporting
vì được Điều15/28 dẫn chiếu. Chưa có policy form chunk; các vùng khác pending.

Scope riêng theo unit/hash và BRD: 133 đơn vị đã đọc cho đề xuất;25 included,
27 supporting,81 excluded. 634 đơn vị chưa kết luận. Config lưu nội dung đã đọc,
hash, lý do/đối tượng, origin, thời điểm agent thực sự ghi nhận; không phải
human reviewer event. Các proposal không truyền nhãn xuống con tự động.

## 4. TT51/QCVN: reader partial và phạm vi khảo sát

Bản ban hành1tr đọc bằng Stage3 cũ. Với QCVN403tr, lần pdfplumber nguyên bản
tiêu thụ trên6GB và quá nhiều thời gian ở vùng đồ họa; attempt chưa seal giữ
nguyên. Reader adapter hẹp circular-pdfium-extraction.v1 đọc từng trang và đóng
page/textpage ngay; dùng lại node/normalizer, contract extraction.v1, pending
schema SQLite, Stage3 issue/status/database_rows và source snapshot.
Không thêm hệ thống registry/parser/chunker song song.

Tool/version/code/config thật tham gia extraction_id theo công thức Stage3.
Offsets trên normalized.txt **mới**, không sao offsets của pdfplumber hoặc DOCX.
NFC/LF chỉ đổi Unicode và line endings; NUL/U+FFFE/U+FFFF giữ nguyên, tạo error
PDF_READER_NONCHARACTER. Trang text rỗng vẫn có locator và warning, không được
gọi là trang trắng. Reader hoàn thành404 trang nhưng processing_success=false
vì QCVN partial; CLI extract-circular/validate-reader trả1 và lưu bundle đầy đủ.
Main complete được đi tiếp độc lập, không dùng QCVN lỗi làm target/context.

Font diagnostic ở PDF7: CMap thực ánh xạ CID tới U+0000; pdfplumber trả NUL,
PDFium trả U+FFFE ở nhiều vị trí. Chưa có quy tắc hiệu đính có bằng chứng cho
toàn file; không xóa hàng loạt hoặc mặc định đó là dấu cách. PDFium403tr có100
trang không text,302 trang U+FFFE; trang368 chỉ có số trang, không quy định usable.

Inventory hình chỉ đo **root objects/max_depth=1**: ảnh có bbox/page nhưng không
nhận diện/diễn giải; vector paths không phải các biển đã hiểu. Trên10000 root
objects thì giữ root count, đánh dấu incomplete và không duyệt tiếp. Nested
Form objects chưa mở rộng cũng được đánh dấu. Không đo layout bảng trên QCVN
bằng PDFium: tables=null cho403 trang, không báo thành0 bảng thực tế.
QCVN có cờ phụ thuộc hình/đồ họa hoặc lỗi text và nằm unprocessed theo từng trang.
Chưa OCR toàn403tr; backlog hẹp phải nêu trang/vùng/nhu cầu trước khi triển khai.

## 5. Validation, replay và giới hạn

Các subcommand bổ sung ở **CLI PDF preview hiện có src.tt38_preview**; tên file
là lịch sử. Không thêm executable/framework. src.source_inventory vẫn là exporter.
Giữ policy v1 và code parser/builder/encoder hash-bound cũ. CLI v1 validator cho
phép đúng SHA entrypoint trước khi thêm routes; mọi module tính toán cũ, source,
config, layout và nội dung vẫn được kiểm và replay. Không bỏ toàn validator.

Mỗi nguồn/run có manifest, nguyên văn, offsets, coverage và báo cáo riêng.
validate-circular replay cây/spans/chunks/context/ID/hash và check source slices,
page count, cells/quote/ID, token evidence, scope binding và pending gates.
validate-reader đọc lại raw, tái tạo toàn text/trace/ID, kiểm SQLite FK/integrity/
export bằng schema Stage3. --survey-manifest chỉ tái sử dụng phép đo cùng đúng
SHA manifest extraction, không dùng để promote pending hoặc bỏ source checks.

Nguồn/edition/applicability tại2025-01-01 vẫn pending. Ngày hiệu lực chung chỉ
là observation có spans trong applicability.observed.jsonl (TT38 A12K1;
TT35 A66K1; TT51 A2K1). Nội dung chuyển tiếp TT35 A67 và thay thế TT51 A2K2
được giữ trong legal units/spans, chưa phải quyết định applicability riêng.
Chưa rà đầy đủ sửa đổi/ngoại lệ cấp đơn vị. Ba Thông tư chưa thuộc dataset/index
v1 hoặc draft3.082; preview không phải serving. Chưa embedding/index/OCR/nhận
diện ảnh/đổi ứng dụng. Kiểm kỹ thuật không xác minh pháp lý hoặc chất lượng retrieval.
