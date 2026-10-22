# Addendum v1.0 — bảy nguồn và adapter PDF TT38

Ngày 2026-10-22; snapshot sản phẩm **2025-01-01**. Đây là bổ sung triển khai,
không thay lịch sử/hiệu lực của văn bản hoặc xác nhận nghiệm thu.

## Changelog và đối chiếu tài liệu đã phát hành

| Tài liệu | Kết quả rà | Cách xử lý |
|---|---|---|
| Source Inventory v0.1 | Đã có đúng7 nguồn, SRC-001…007 | Giữ nguyên; config tổng hợp mới thực hiện đúng mapping |
| BRD v1.0 §3/§5.1 | Bốn văn bản **khởi đầu**, cho phép mở rộng; loại quy hoạch/thiết kế hạ tầng và nhận diện ảnh | Không phải giới hạn4 nguồn; không sửa bản đã phát hành |
| SRS v1.0 | Corpus cần chọn/xác minh theo snapshot, không giới hạn mọi input DOCX | Giữ bản gốc; snapshot còn mở được chốt2025-01-01 theo Inventory/DDD/người dùng |
| SDD kiến trúc v1.0 §6 | Pipeline nguồn→extraction→cấu trúc→chunk; yêu cầu thiết kế không chứng minh đã triển khai mọi reader | Bổ sung tình trạng thực qua addendum này, không viết lại lịch sử |
| DDD v1.0 | Một law có nhiều file/edition; extraction/spans tách nguồn; không cố định4 nguồn hoặc DOCX | Không sửa SQL/schema; workflow progress/observed/pending ở sidecar |
| docs/architecture.md, docs/scope.md | Prototype cũ, corpus4 DOCX/1.457 chunks và pipeline cũ | Giữ làm tài liệu lịch sử, README/ingestion guide trỏ rõ trạng thái hiện tại |

BRD/SRS/SDD/DDD/Inventory gốc không bị sửa byte; một số artifact scope đã
bind hash các tài liệu này. Addendum không âm thầm thay policy source,
scope, applicability, identity hay release gates của các run đã seal.

## Danh mục và các chiều trạng thái

| source_id | law_id |
|---|---|
| SRC-001 | 36/2024/QH15 |
| SRC-002 | 168/2024/NĐ-CP |
| SRC-003 | 35/2024/QH15 |
| SRC-004 | 165/2024/NĐ-CP |
| SRC-005 | 38/2024/TT-BGTVT |
| SRC-006 | 51/2024/TT-BGTVT |
| SRC-007 | 35/2024/TT-BGTVT |

`config/source_registration.seven.v1.json` chứa7 văn bản/10 file:4 DOCX,
5 PDF người dùng thêm và một PDF Công báo38. Sourcefile UUIDv5 theo law_id/
hash/namespace cũ: di chuyển/sao chép không làm đổi file_id. Nạp lại run
đăng ký là snapshot hồ sơ, không tạo thêm source_file chính thức trùng.
Không đổi config4 nguồn hoặc config3 Thông tư cũ để replay lịch sử.

Dataset/index v1 chỉ có4 văn bản đầu; draft3.082 cũng chưa có3 Thông tư.
TT38 ở run preview riêng. Đã thu thập/đăng ký, extraction, parse, chunk,
dataset/index membership và scope/applicability là các chiều riêng, không
gói chúng thành một nhãn ready hoặc thêm cột workflow vào DDD chính thức.

Mapping artifact thực: DOCX dataset có source_id đúng Inventory. Riêng
nhánh HTML NĐ168 khôi phục dùng internal SRC-004; export ghi crosswalk
theo **law_id + artifact hash** về SRC-002. Không alias SRC-004 toàn cục
(mã này vẫn là NĐ165), không đổi ID/hash/object chunk trong draft cũ.

## Metadata và nguồn bền vững

PDF Công báo được lưu append-only tại
`data/raw/official/38-2024-TT-BGTVT/congbao-1355-1356.pdf`, byte/hash/file_id
trùng bản đã capture trong staging. Tệp7tr `38-bgtvt.pdf` giữ riêng để so;
hai bản không phải continuation và không ghép extraction.

`data/source_evidence/circulars-2024/` giữ bản sao nguyên byte HTML,
observed records, actual capture receipt và diagnostics. Các đường dẫn trong
bản sao records cũ là lịch sử; receipt/archive manifest công khai phạm vi
bản sao, không giả đó là bundle inspection cũ portable. Export mới ghi
evidence_ref/locator/hash tới các file bền vững thật; CSV cũ giữ nguyên.

Export10 file có source_id/law_id/file_id/source_set/file_role/part_order,
local_ref, official_page_url, download_url, SHA/size/pages/retrieved_at,
status và evidence refs. JSON null và ô CSV trống là chưa biết. Không dùng
mtime, thời điểm kiểm tra/copy hoặc snapshot thay ngày tải. Các DOCX không
có số trang render đáng tin nên pages=null. Chỉ Công báo38 có ngày thu thập
mới đã ghi thật; local PDFs vẫn thiếu log tải lịch sử. Observed không verified.

Profile Stage2 chưa nhận evidence review: schema pending giữ null và92
placeholder issues cho7 docs/10 files. Các facts có bằng chứng được giữ
riêng trong export/receipt;92 không phải số dữ kiện thực sự chưa tìm thấy.
Không tạo corpus giả hoặc nới schema để promote chúng.

## TT38 — mở rộng layout hẹp, tái sử dụng pipeline

1. Stage2 đăng ký duy nhất bản Công báo được chọn. Stage3 CLI hiện có trích
   toàn8 trang pdf_text, NFC/LF, immutable normalized.txt/trace, page locators,
   offsets Unicode code point, SHA và tool/version. Không cleaning/OCR.
2. Adapter `src/ingestion/pdf_layout.py` đối chiếu từng dòng/bbox từ PDF với
   đúng slice Stage3, fail nếu lệch. Header Công báo từng trang và chữ ký
   được partition riêng; continuation qua trang giữ các source slices, không
   thêm header vào Khoản. Bold/marker thật dùng phân biệt heading nhiều dòng.
3. Tái dùng `legal_tree.parse_extraction` và `validate_tree` cũ. API grammar
   hiện hardcode tags DOCX; adapter dùng **view tương thích trong bộ nhớ**
   (paragraph/table blocks và offsets projection). Các tags method/part đó
   chỉ để gọi grammar, không phải hồ sơ nguồn. Không ghi extraction DOCX giả.
   Toàn bộ spans được ánh xạ lại về original PDF trace, tính lại span_id;
   output không có locator word/document.xml. Root title THÔNG TƯ được lấy
   từ slices thật vì grammar cũ chỉ biết title LUẬT/NGHỊ ĐỊNH. Unit IDs vẫn
   unit.v1; text/title là LF-join slices, không viết lại câu luật.
4. Không sửa byte module grammar/builder/encoder cũ đã bind trong dataset.
   Đây là adapter layout cho đúng bản TT38, không parser PDF tổng quát hoặc
   bản sao thuật toán parser. Mọi code point trong extraction được partition
   parsed, supporting/non-body, unprocessed, source layout hoặc page separator.
5. Chọn3 bảng thật theo caption/bbox/rows/columns đã đối chiếu ảnh. Detector
   pdfplumber còn báo false-positive vùng Điều12 ở trang7–8; không coi đó là
   bảng, không bỏ nội dung thi hành. Bảng thật giữ physical cells/merged None
   slots, bbox và các source slices/hash trong normalized.txt. Bbox là
   `[x0, top, x1, bottom]` theo PDF points/pdfplumber, không phải pixel ảnh
   render. Không điền ô
   merge bằng nội dung tự suy.
6. Chín hàng dẫn xuất lưu riêng labels ghép từ header cells, data cells,
   owner lead và ancestor context (gồm ngoại lệ đường cao tốc/điều kiện khô
   ráo). Chúng không thay text_original, không unit/chunk giả. Row→cell→PDF
   bbox/page + extraction slices cho phép đối chiếu số/đơn vị/loại xe/đường.
   Chưa có table chunk policy đủ kiểm định nên giữ các hàng ở quarantine.
7. Tái dùng builder Khoản/Điểm và Điều lá. Context theo policy cũ, không
   ghép anh em. A6K1/K2 và A11K2a bị chặn do bảng; A11K2b bị chặn riêng vì
   dẫn chiếu giá trị bảng ởa, không giả đã mở rộng cross-reference. Quarantine
   giữ own fields/spans và table objects/cells, không truncate để tạo chunk.
8. Tokenizer/preprocessing query/document hiện có, budget256, không đổi model
   hoặc chạy encoder. Preview thành công chưa phải scope included/verified.
   Scope chỉ proposal theo BRD đã đọc từng vùng; thiết kế/thẩm quyền quản lý
   A5/A10 được đề xuất excluded. Hiệu lực chung quan sát từ A12K1 lưu cùng
   spans, không suy toàn bộ units active tại2025-01-01.

CLI `src.tt38_preview` build/validate tái dùng Stage3 validator, DDD shape,
tree invariant, source proof, chunk identity, builder và encoder input cũ.
Validate replay layout/cells/units/context/content bằng cached token evidence
bound input/token IDs/hash/count. Chỉ build tokenize CPU; không embedding.
`--extraction-manifest` cho phép bind một run Stage3 mới cùng profile/source,
không đổi luật/layout/model/budget, giúp tái tạo sau khi dọn staging. Input
snapshot được copy vào preview; raw/evidence gốc đã bền vững trong data/.

## TT35/TT51 và giới hạn giữ nguyên

TT35 chính69tr/phụ lục179tr mới đăng ký/inspection, chưa Stage3/parse/chunk.
TT51 chính1tr/QCVN403tr cũng chưa pipeline extraction. Giữ100 trang PDFium
text rỗng, mẫu NUL pdfplumber, cảnh báo bảng/hình và thiếu số TT ở lời nói
đầu QCVN trong durable diagnostics. Không bỏ100 trang hoặc đồng nhất text
rỗng với trang trắng. Chưa OCR toàn QCVN, không nhận diện ảnh biển báo.

Không nhập3 Thông tư vào dataset/index, không đổi dataset3077/index/evaluation/
ZIP hoặc draft3082, không yêu cầu nhóm chuyển phiên bản. Tài liệu mới nhất:
[ingestion guide](../ingestion.md), [STATUS](../progress/STATUS.md) và
[verification](../reviews/Seven_Sources_TT38_Verification.md).
