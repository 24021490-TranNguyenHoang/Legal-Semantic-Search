# Stage 4 — Cây pháp lý pending có truy vết

Snapshot sản phẩm **2025-01-01**. Đã đọc AGENTS, DDD, README trong ZIP mẫu,
Stage2_Source_Contract, Stage3_Extraction_Contract và báo cáo Stage 3. README mẫu
vẫn nằm trong ZIP, không có file README.md rời ở thư mục data_model_v1.
Không thiếu tài liệu bắt buộc cho phạm vi này. Quy định dừng Stage 3 trong AGENTS
là lịch sử, đã được người dùng thay bằng cho phép Stage 4 và dừng sau Stage 4.
SRS/SDD còn snapshot mở; dùng quyết định 2025-01-01 đã chốt trong DDD/inventory
và hội thoại, không lấy ngày chạy thay snapshot.

## Đầu vào và trạng thái

`python -m src.legal_parser parse` chỉ nhận bundle Stage 3 technical_valid=true
và processing_success=true, có checksum, normalized.txt, trace và source snapshot
replay được. Nguồn/extraction pending được phân tích kỹ thuật, vẫn pending.
Không suy ra verified, scope hay hiệu lực từ việc nhận diện được cấu trúc.
Không tải model; inference Windows WinError 4551 không ảnh hưởng Stage 4.

legal-tree.v1 hỗ trợ DOCX main-body block trace. PDF đã được extraction ở Stage 3
nhưng chưa có chính sách parser hình học/heading PDF; Stage 4 từ chối PDF trước
khi ghi output. Nhiều extraction cho cùng law_id (phần tiếp nối/bản thay thế)
cần chính sách chọn/ghép tường minh; v1 từ chối, không tự nối theo tên file.
Bốn nguồn thật hiện có mỗi law_id một file, một extraction.

## Rà soát 13 warning trước triển khai

Tiền tố B = `/w:document/w:body`. Bộ P gồm `word/endnotes.xml`,
`word/footnotes.xml`, `word/header1.xml`. Mỗi hàng là một warning Stage 3;
hai hàng cùng XPath Luật 35 là hai sự kiện riêng, không gộp thành một warning.

| # | law_id | Code rút gọn | Part và XPath | Quan sát và xử lý |
|---:|---|---|---|---|
| 1 | 168/2024/NĐ-CP | VISUAL_OR_SYMBOL | document.xml, B/w:tbl[1]/w:tr[1]/w:tc[1]/w:p[1] | Bảng quốc hiệu; cách ly locator có visual. |
| 2 | 168/2024/NĐ-CP | VISUAL_OR_SYMBOL | document.xml, B/w:tbl[1]/w:tr[1]/w:tc[2]/w:p[1] | Bảng quốc hiệu; cách ly locator có visual. |
| 3 | 168/2024/NĐ-CP | GENERATED_CONTENT | header1.xml, /w:hdr/w:p[1] | Header, text có số 2; không giải mã field, không nhập vào Điều cuối. |
| 4 | 168/2024/NĐ-CP | ANCILLARY_PARTS_APPENDED | P, không có XPath đơn | Tách các part phụ theo trace. |
| 5 | 165/2024/NĐ-CP | GENERATED_CONTENT | header1.xml, /w:hdr/w:p[2] | Header, text có số 73; không coi là số Khoản. |
| 6 | 165/2024/NĐ-CP | ANCILLARY_PARTS_APPENDED | P, không có XPath đơn | Tách các part phụ theo trace. |
| 7 | 36/2024/QH15 | VISUAL_OR_SYMBOL | document.xml, B/w:tbl[1]/w:tr[1]/w:tc[1]/w:p[1] | Bảng quốc hiệu; cách ly locator có visual. |
| 8 | 36/2024/QH15 | VISUAL_OR_SYMBOL | document.xml, B/w:tbl[1]/w:tr[1]/w:tc[2]/w:p[1] | Bảng quốc hiệu; cách ly locator có visual. |
| 9 | 36/2024/QH15 | GENERATED_CONTENT | header1.xml, /w:hdr/w:p[1] | Header, text có số 2; không nhập vào Điều cuối. |
| 10 | 36/2024/QH15 | ANCILLARY_PARTS_APPENDED | P, không có XPath đơn | Tách các part phụ theo trace. |
| 11 | 35/2024/QH15 | VISUAL_OR_SYMBOL | document.xml, B/w:p[933] | Paragraph text rỗng trước câu thông qua luật/chữ ký; giữ locator rỗng để review. |
| 12 | 35/2024/QH15 | VISUAL_OR_SYMBOL | document.xml, B/w:p[933] | Sự kiện thứ hai tại cùng paragraph, giữ nguyên issue ID riêng. |
| 13 | 35/2024/QH15 | ANCILLARY_PARTS_APPENDED | P, không có XPath đơn | Tách các part phụ theo trace. |

Part `document.xml` ở bảng trên là `word/document.xml`. Code đầy đủ có tiền tố
DOCX_ và hậu tố _REVIEW cho visual/generated. Artifact source_warning_review.jsonl
giữ nguyên code, issue_id, locator đầy đủ và vị trí code point khi có.

Nguy cơ cấu trúc: ba generated warning có thể sinh số giả nếu nối vào thân luật;
bốn ancillary warning báo ranh giới part, nếu bỏ qua có thể gán header/note vào
Điều cuối. Bốn visual ở quốc hiệu và hai visual ở paragraph rỗng không cho phép
kết luận nội dung hình đã hiểu; không dùng chúng suy số hay tên cấp pháp lý.
Chưa quan sát warning field/numbering/revision tại heading pháp lý trong bốn DOCX;
đếm XML main body cho thấy numPr=0 và các revision được kiểm tra=0. Điều đó
không chứng minh toàn bộ cơ chế Word hoặc ý nghĩa hình đã được hỗ trợ.

Mọi warning vẫn pending. Với warning tại paragraph thân luật: cách ly paragraph,
dừng gán cấu trúc tiếp theo tới heading Chương/Mục/Điều tin cậy. Không tự tạo số
từ field/numPr hoặc lấy text revision làm nội dung đã chấp nhận.

## Grammar và bảo toàn nội dung

Parser mới ở `src/ingestion/legal_tree.py`, CLI ở `src/legal_parser.py`.
Không sửa code extraction Stage 3 hoặc parser/chunker prototype. Config policy
v1 khóa ở `config/legal_parser.v1.json`; thay hành vi phải đổi chính sách có tài liệu.

- Chỉ paragraph trực tiếp trong main-body part được mở cấp pháp lý. Không tách
  từng dòng đánh số bên trong một paragraph để tạo Khoản. Table/cell và part phụ
  không được dùng làm heading. Mọi bảng có inventory và locator.
- Chương/Mục có marker và tên cùng paragraph, hoặc marker rồi các paragraph tên
  viết hoa liên tiếp; hỗ trợ tên chứa LF và nhiều paragraph. Trim whitespace mép
  title bằng cận span, không sửa nội dung bên trong. Dấu phân cách sau marker
  thuộc coverage HEADING_MARKER, không chép vào title.
- Điều phải là paragraph khớp `Điều N. Tên`, tên bắt đầu chữ hoa, không kết thúc
  bằng dấu câu văn xuôi `. ; : ! ?`, số tăng. Thứ tự thiếu tạo issue, không tạo
  Điều thiếu. Dẫn chiếu dạng `Điều N của ...`, hoặc chuỗi Điều trong câu, không
  mở cấp mới. Paragraph giống heading nhưng không đủ bằng chứng có issue.
- Khoản là paragraph `N. ...`, dưới Điều thật và liên tiếp từ 1. Điểm `a) ...`
  dưới Khoản hoặc trực tiếp Điều khi thực sự không có Khoản. Giữ `đ`, thứ tự
  nguồn; không thêm Khoản trung gian. Số/điểm mơ hồ được cách ly, không đoán.
- Đoạn trích trong dấu “…” hoặc dấu nháy kép được giữ trong text riêng của chủ
  sở hữu hiện tại, gồm cả trích dẫn sửa đổi nhiều paragraph. Không phân tích số
  trong trích thành các đơn vị của văn bản đang chứa nó. Quote chưa đóng có issue.
- `text_original` giữ nguyên toàn bộ paragraph trực tiếp, kể cả marker Khoản/Điểm,
  số, dấu, whitespace, đơn vị và phủ định. Các paragraph được nối LF qua spans.
  Parent chỉ giữ phần chữ riêng: mọi đoạn dẫn trước con và phần tiếp nối trực tiếp;
  không sao chép toàn bộ nội dung con vào parent.
- Quốc hiệu/bảng mở đầu, câu thông qua luật, chữ ký/nơi nhận và part phụ có nhãn
  kỹ thuật supporting_non_body. Đây không phải unit_assessment.scope_status.
  Quy tắc boundary dựa trên marker rõ và part; không tự xóa uppercase bất kỳ.
  Bảng ở giữa thân luật được giữ với context_unit_id, chưa suy ngữ nghĩa bảng.

Grammar có tính bảo thủ, không khẳng định nhận diện mọi cách trình bày DOCX.
Không có style/render từ Word để chứng minh một paragraph độc lập giống heading
chắc chắn không phải dẫn chiếu. Trường hợp dấu trích dẫn không chuẩn, numbering
tự động, số Điều có hậu tố/không tăng, phụ lục hoặc định dạng khác cần policy/review
riêng; coverage/issue là cổng chặn, không sửa nguồn cho pass.

## Bất thường bổ sung của Nghị định 168

Trong normalized.txt hiện có, p[518] và p[519] cùng `đ)` dưới Điều 16 Khoản 2;
p[1057] và p[1058] cùng `đ)` dưới Điều 40 Khoản 3. Đây là quan sát văn bản/trace,
không phải bằng chứng để sửa ký hiệu pháp lý hoặc xác nhận bản nguồn chính thức.
Parser cách ly cả hai vị trí trùng của mỗi nhóm và phần tiếp theo tới Khoản
liên tiếp rõ ràng hoặc heading tin cậy. Những Điểm trước đó không xung đột được
giữ. Thứ tự con còn lại đánh lại ordinal theo vị trí thật, không đổi designation.
Chỗ nhảy chữ có POINT_SEQUENCE_GAP, giữ ký hiệu nhìn thấy, không bổ sung chữ thiếu.

## Định danh, spans và coverage

unit_id áp dụng đúng DDD §12.1: `u_ + SHA256(canonical(unit.v1))`, gồm
identity_schema, law_id, parent_unit_id, unit_type, designation, canonical_path,
citation_path, ordinal, title, text_original. Hoàn tất chữ riêng của cha trước
khi cấp ID cha rồi con. Timestamp/tool/config không thêm vào công thức DDD.

Quy ước path cụ thể của v1: `document:<law_id>/chapter:I/section:1/article:6/...`;
citation `<law_id> > Chương I > Mục 1 > Điều 6 > Khoản 1 > Điểm đ`. Không dùng
metadata chưa xác minh làm title; title gốc lấy từ paragraph tên văn bản thực tế.
Ordinal 0-based trong các con trực tiếp, theo thứ tự nguồn, không sort chuỗi số.

source_span giữ đúng trường DDD. Quote là lát normalized.txt [start,end), code
point; field bằng LF nối quote theo span_order liên tục từ 0. Field rỗng không
có span; locator rỗng không bị biến thành source_span start=end không hợp lệ.
span_id được cụ thể hóa là `s_ + SHA256(canonical({identity_schema:"source-span.v1",
...mọi trường span trừ span_id}))`. Không gọi đây là công thức DDD đã chốt sẵn.
locator_json giữ locator Stage 3 nguyên bản dưới dạng canonical JSON string.

Coverage phân hoạch toàn bộ leaf+separator của extraction thành parsed,
supporting_non_body, unprocessed, needs_review, layout, serialization_separator.
Các vị trí rỗng vẫn có record. Coverage không cộng container nhiều lần;
table_inventory dùng locator container riêng. Có 100% ký tự được ghi nhận không
có nghĩa 100% đã phân tích hoặc được xác minh pháp lý.

## Lưu pending, validator và chuyển chính thức

Run mới dưới staging gồm legal_units.pending.jsonl, source_spans.pending.jsonl,
legal_tree.pending.sqlite, coverage.jsonl/report, tables.jsonl, quality_issues.jsonl,
source_warning_review.jsonl, examples.json, config/schema và manifest/sidecar.
extraction_snapshot sao nguyên artifact Stage 3 và snapshot nguồn; không sửa run
đầu vào. run_report ghi cuối, loại khỏi manifest checksum như các stage trước.
Manifest ghi timestamp chạy UTC thật, tool/Python/code hash và luôn release=false.

DB riêng có pending_source/extraction/LEGAL unit/span/issue, foreign_keys ON;
cha và spans cùng law qua composite FK. Bản content.sqlite chính thức được sao
trong snapshot vẫn trống; không tạo document/file/extraction/corpus giả.
UNIQUE canonical position chỉ áp dụng một cây pending đã chọn của run này,
không thay giới hạn lịch sử/version của schema chính thức DDD.

Validator kiểm checksum/set artifact, schema/JSON/FK/integrity/export, unit.v1,
tree không chu trình/cha sai/cấp giả/ID trùng, ordinal, spans/hash/locator/roundtrip,
coverage liền mạch, rồi replay parser và Stage 3/2 nguồn. Thiếu input, bundle sai,
run đã tồn tại hoặc output ngoài staging thất bại trước khi ghi. Validation đọc
read-only. `--require-release-ready` luôn trả 1. CLI 0 chỉ nói kỹ thuật nhất quán;
tables/needs_review và mọi cổng bằng chứng vẫn chặn phát hành.

Chưa triển khai promote. Sau khi bổ sung bằng chứng nguồn thật theo Stage 2,
rà soát extraction theo Stage 3 và cây/bảng/quote/numbering với nguồn, mới nạp
legal_document/source_file/extraction hợp lệ rồi unit cha trước con và spans vào
schema DDD nguyên vẹn. Nếu text thay đổi, tạo extraction/cây/ID/spans mới; không
sửa offsets artifact cũ. Giữ liên kết file_id/extraction_id khi đúng đối tượng
bất biến; đánh giá scope/hiệu lực và cổng corpus/release là công việc các stage sau.
