# Stage 4 — Parser cây pháp lý có truy vết (legal-tree.v1.1)

Snapshot sản phẩm **2025-01-01**. SRS/SDD còn để mốc mở nhưng DDD/Source Inventory
và quyết định người dùng đã chốt mốc này. AGENTS ghi các mốc dừng Stage 2/3 theo
lịch sử; yêu cầu hiện tại cho phép tiếp tục Stage 4, dừng sau Stage 4. Không âm
thầm thay quyết định pháp lý bằng ngày chạy hoặc yêu cầu mới tự đặt ra.

Đã đọc DDD, schema/README trong ZIP mẫu, Stage3_Extraction_Contract.md,
Stage3_Verification.md, code và bundle nguồn/extraction. README mẫu nằm trong
ZIP, không có README.md rời trong thư mục này; không thiếu tài liệu bắt buộc cho
phạm vi parser. Schema DDD chính thức giữ nguyên byte. Tài liệu
Stage4_Legal_Tree_Contract.md mô tả policy v1 trước đây; tài liệu này là contract
hiện hành v1.1, ghi các quyết định triển khai bổ sung.

## Đầu vào, preflight và trạng thái

CLI `python -m src.legal_parser parse` nhận manifest bundle Stage 3 đạt cả
technical_valid và processing_success. Trước output: kiểm checksum, contract,
Stage 2 snapshot, raw size/hash, SQLite/export/FK và replay extraction Stage 3.
Đọc normalized.txt và trace.json đúng ref; không dùng cleaned TXT/chunk prototype.
Giữ file_id/law_id/extraction_id và hồ sơ evidence pending của nguồn.

Policy này hỗ trợ DOCX main-body block trace; chưa có chính sách parser PDF hoặc
ghép continuation/alternate/edition. PDF hoặc nhiều extraction cùng law_id bị
từ chối trước output. Không đoán bản nào đúng hoặc thứ tự từ tên file.

Nguồn/extraction pending được phân tích kỹ thuật trong staging. Units/spans vẫn
pending; CLI thành công không phải verified, applicability hay release approval.
Inference Windows WinError 4551 không ảnh hưởng parser; không tải/chạy model.

## 13 warning Stage 3 và rủi ro cấu trúc

B = `/w:document/w:body`; các part có tiền tố `word/`.
P = `word/endnotes.xml`, `word/footnotes.xml`, `word/header1.xml`.
Warning ancillary chỉ có danh sách part, không có XPath đơn để tự tạo ra.

| # | law_id | Code | Locator |
|---:|---|---|---|
| 1 | 168/2024/NĐ-CP | DOCX_VISUAL_OR_SYMBOL_REVIEW | document.xml, B/w:tbl[1]/w:tr[1]/w:tc[1]/w:p[1] |
| 2 | 168/2024/NĐ-CP | DOCX_VISUAL_OR_SYMBOL_REVIEW | document.xml, B/w:tbl[1]/w:tr[1]/w:tc[2]/w:p[1] |
| 3 | 168/2024/NĐ-CP | DOCX_GENERATED_CONTENT_REVIEW | header1.xml, /w:hdr/w:p[1] |
| 4 | 168/2024/NĐ-CP | DOCX_ANCILLARY_PARTS_APPENDED | P |
| 5 | 165/2024/NĐ-CP | DOCX_GENERATED_CONTENT_REVIEW | header1.xml, /w:hdr/w:p[2] |
| 6 | 165/2024/NĐ-CP | DOCX_ANCILLARY_PARTS_APPENDED | P |
| 7 | 36/2024/QH15 | DOCX_VISUAL_OR_SYMBOL_REVIEW | document.xml, B/w:tbl[1]/w:tr[1]/w:tc[1]/w:p[1] |
| 8 | 36/2024/QH15 | DOCX_VISUAL_OR_SYMBOL_REVIEW | document.xml, B/w:tbl[1]/w:tr[1]/w:tc[2]/w:p[1] |
| 9 | 36/2024/QH15 | DOCX_GENERATED_CONTENT_REVIEW | header1.xml, /w:hdr/w:p[1] |
| 10 | 36/2024/QH15 | DOCX_ANCILLARY_PARTS_APPENDED | P |
| 11 | 35/2024/QH15 | DOCX_VISUAL_OR_SYMBOL_REVIEW | document.xml, B/w:p[933], sự kiện thứ nhất |
| 12 | 35/2024/QH15 | DOCX_VISUAL_OR_SYMBOL_REVIEW | document.xml, B/w:p[933], sự kiện thứ hai |
| 13 | 35/2024/QH15 | DOCX_ANCILLARY_PARTS_APPENDED | P |

Bốn visual ở bảng quốc hiệu được giữ needs_review theo locator; không suy hình
thành tiêu đề/số. Hai visual Luật 35 cùng paragraph text rỗng trước câu thông qua
luật và chữ ký: giữ cả hai issue ID, không tạo source_span start=end không hợp lệ.
Ba generated warning nằm trong header (text có số 2/73/2), không giải mã field
hoặc dùng số đó làm Khoản. Bốn ancillary warning chỉ ra ranh giới part; bỏ qua
ranh giới có thể gán header/note vào Điều cuối. Part phụ được ghi supporting riêng.
Không kết luận hình/field/note đã hiểu đầy đủ hoặc warning đã resolved.

Field, automatic numbering, revision hoặc visual chưa giải mã ở paragraph thân
luật: cách ly paragraph và dừng gán cấu trúc đến heading tin cậy. Warning gốc và
locator luôn nằm trong source_warning_review.jsonl, đầy đủ hơn bảng rút gọn này.

## Nhận diện cấp và giữ nội dung riêng

- Chỉ paragraph trực tiếp thuộc main-body part mở cấp pháp lý. Dựa trên trace
  kind/parent/part, không coi ô bảng hay mỗi dòng đánh số nội bộ là Khoản.
- Chương có số La Mã hợp lệ hoặc số nguyên; tên cùng paragraph/dòng hoặc các
  paragraph viết hoa tiếp sau. Tên hai paragraph dạng chữ hoa/thường được nhận
  khi paragraph tên đầu chữ hoa, không kết thúc dấu câu văn xuôi, và paragraph
  kế tiếp là heading cấp rõ ràng; không đổi thành uppercase để pass. Mục tương tự với số nguyên. Hỗ trợ nhiều paragraph
  tên và LF trong paragraph. Không tạo Chương/Mục nếu nguồn không có marker.
- Điều khớp nguyên paragraph `Điều N. Tên`, tên đầu chữ hoa, không kết thúc bằng
  dấu câu văn xuôi `. ; : ! ?`; designation phải tăng. Số thiếu có issue, không
  sinh Điều thiếu. Số lùi/trùng bị cách ly. Hậu tố số chưa chắc chắn được review,
  không đổi số. Dẫn chiếu trong câu hoặc `Điều N của ...` không mở Điều.
- Khoản là paragraph `N. ...` liên tiếp từ 1 dưới Điều thực. Điểm `a) ...`, gồm
  `đ)`, theo thứ tự nguồn, dưới Khoản hoặc trực tiếp dưới Điều nếu không có Khoản.
  Không thêm Khoản trung gian. Không dùng ordinal làm designation pháp lý.
- Dòng bảng, số trong cùng paragraph nhiều dòng và danh sách minh họa/tham khảo
  được nhận diện rõ không trở thành Khoản. Các nhãn danh sách hỗ trợ hiện tại là
  `Ví dụ minh họa:`, `Danh sách minh họa:`, `Danh sách tham khảo:`; không tuyên bố
  phân biệt mọi danh sách với Khoản chỉ từ text. Trace chưa có style/indent Word.
- Heading có số/syntax không rõ, danh sách mơ hồ, numPr/field/revision chưa giải
  mã tạo issue/needs_review; không ép vào cấp trước. Chưa thấy cấp được hỗ trợ
  thì chỉ giữ gốc document, phát NO_RELIABLE_LEGAL_STRUCTURE, không sinh Điều giả.
- title là lát nguồn riêng, trim whitespace mép bằng cận span; không thay chữ
  bên trong hoặc tạo tên tóm tắt. text_original giữ nguyên paragraph riêng,
  gồm marker Khoản/Điểm, số, đơn vị, dấu và whitespace; nối các đoạn bằng LF.
  Parent giữ đủ đoạn dẫn trước con và phần riêng, không sao toàn bộ text con.

Root document là cấp DDD có thật, designation dùng law_id; title đọc từ paragraph
tên văn bản trong extraction, không thay bằng tên inventory chưa xác minh.
Nội dung mở đầu ở root vẫn có spans; coverage v1.1 đếm nó là supporting_non_body.
Đây là nhãn kỹ thuật, không phải unit_assessment.scope_status hay quyết định scope.

## Sửa đổi văn bản khác và vùng chưa hỗ trợ

Dấu “…”/nháy kép tạo vùng trích dẫn, có thể kéo dài nhiều paragraph. Các heading
Điều/Khoản bên trong vùng đã có ranh giới được giữ làm nội dung riêng của đơn vị
chứa trích dẫn, không tạo cấp gốc mới trong văn bản đang sửa đổi.

Sau chỉ dẫn sửa đổi/bổ sung/thay thế nhắm Điều/Khoản/Điểm/phụ lục và kết thúc
`như sau:`/`sau đây:`, nhận quote, bảng chưa phân tích hoặc chỉ dẫn sửa đổi con.
Nếu không có dấu phân cách và không xác định được cấu trúc thay thế: phát
UNDELIMITED_AMENDMENT, giữ phần tiếp theo trong needs_review tới hết phần thân
còn lại. Không tự chọn heading tăng số làm ranh giới vì đó có thể là Điều được
thay thế. Đây là cách ly bảo thủ, có thể giữ lại cả phần hợp lệ sau đó để review.

Quote chưa đóng: phát UNCLOSED_QUOTATION ở vị trí mở; rút các paragraph bị ảnh
hưởng khỏi field đã gán thử, giữ nguyên trong coverage needs_review. Không đoán
Điều tiếp theo là trong hay ngoài quote. Quote chuẩn/đã đóng vẫn giữ đủ nguyên văn.

Bảng có inventory, span container, context_unit_id và lý do. Bảng thân luật chưa
phân tích ngữ nghĩa; không tạo Khoản từ ô. Marker chữ ký trong bảng chỉ tạo boundary
khi ở cuối phần thân hoặc ngay trước phụ lục; chỉ có từ giống chữ ký trong bảng
giữa thân luật chưa đủ để kết luận non-body. Câu thông qua luật, chữ ký và header/
footer không gán vào Điều cuối. Không mở DB Qdrant hoặc đọc model để phân loại.

Marker `PHỤ LỤC` độc lập: báo ANNEX_STRUCTURE_NOT_SUPPORTED, ghi marker và phần
thân tiếp theo là unprocessed; bảng trong vùng đó cũng có inventory. Chưa tạo
cây annex/figure, không ép heading phụ lục vào cây chính. Những cách trình bày
khác hoặc boundary không rõ vẫn cần rà soát; chưa chứng minh parser tổng quát.

Vị trí pháp lý trùng: duplicate Chương/Mục, Điều số lùi/trùng, Khoản không liên
tiếp và Điểm không đúng thứ tự tạo issue. Với Điểm trùng, cách ly cả hai vị trí
xung đột; không sửa thành chữ khác. Có thể tiếp tục ở Khoản liên tiếp rõ ràng.
Khoảng nhảy chữ có POINT_SEQUENCE_GAP, không thêm chữ bị thiếu.

## unit_id, source_span và coverage

Áp dụng nguyên công thức DDD §12.1:

```text
unit_id = "u_" + SHA256(UTF8(canonical_json({
  identity_schema: "unit.v1", law_id, parent_unit_id, unit_type, designation,
  canonical_path, citation_path, ordinal, title, text_original
})))
```

canonical JSON: sort_keys=true, ensure_ascii=false, separators=(",",":"). Xong
chữ riêng cha rồi cấp ID cha trước con. Không thêm config/tool/timestamp vào unit.v1.
text_sha256 là SHA-256 UTF-8 của text_original.

Quy ước path bổ sung: `document:<law_id>/chapter:I/section:1/article:6/clause:1`;
citation `<law_id> > Chương I > Mục 1 > Điều 6 > Khoản 1`. Chỉ gồm cấp hiện hữu.
Ordinal 0-based theo các con trực tiếp trong thứ tự nguồn, không sắp chuỗi số.

Span dùng đúng field DDD: unit_id, extraction_id, field_name, span_order,
char_start/end, locator_json, quote_sha256 và span_id. Offset Unicode code point
trên normalized.txt bất biến, không phải byte/token/raw XML. Locator lấy trace,
không bịa trang DOCX. Field = LF nối lát cắt theo span_order liên tục từ 0;
field rỗng không có span. Không sửa nội dung hay thêm dấu để roundtrip pass.

DDD chưa chốt công thức span_id; cụ thể hóa: `s_` + SHA-256 canonical JSON chứa
identity_schema="source-span.v1" và mọi trường span trừ span_id. Không đưa thời
gian/run path vào identity; locator_json là canonical JSON string của locator.

Coverage phân hoạch leaf + separator thành parsed, supporting_non_body,
unprocessed, needs_review, layout, serialization_separator. Vị trí rỗng có record.
Không cộng trùng container; bảng có inventory riêng. Đủ 100% ký tự được ghi nhận
không có nghĩa đã phân tích hoặc xác minh 100%. Dùng số đo thực tế, không dùng
1.457 chunk prototype làm chỉ tiêu đơn vị pháp lý.

## Bundle pending, validator và cây dễ đọc

Run mới dưới staging có legal_units.pending.jsonl, source_spans.pending.jsonl,
legal_tree.pending.sqlite, coverage.jsonl/report, quality_issues.jsonl, tables.jsonl,
source_warning_review.jsonl, examples.json/txt, trees/index.json và cây từng văn bản.
trees/index.json ánh xạ law_id sang trees/01.txt…; file cây in riêng title/text,
unit/parent ID, spans và vùng chưa xử lý. Đây là view để đọc, không phải corpus
hoặc context tìm kiếm. examples A/B lấy đúng Điều 22 Luật 36 và Điều 6 Khoản 1
NĐ168; bundle fixture không có các luật đó thì ghi không có, không tạo fixture giả.

extraction_snapshot sao nguyên artifact Stage 3 và source snapshot; không sửa
nguồn hoặc tạo legal_document/source_file/extraction/corpus chính thức giả.
SQLite pending riêng có FK cha cùng law, spans cùng law/extraction, trạng thái
pending. Bật foreign_keys trước transaction; validator mở read-only/query_only.
Schema DDD chính thức vẫn nguyên byte; content.sqlite trong snapshot vẫn trống.

Validator kiểm schema/JSON/hash/unit.v1, cha/cấp/path/citation/ordinal, chu trình,
ID/vị trí trùng, FK/integrity/export, quote/locator/offset/field roundtrip, coverage
và replay Stage 2/3/parser. Cây dễ đọc và ví dụ cũng replay và hash trong manifest.
Built_at là thời gian chạy UTC thật; không phải retrieved_at. run_report ghi cuối,
loại khỏi checksum để tránh tự tham chiếu. Manifest có sidecar SHA-256.

Policy v1.1 có config riêng `config/legal_parser.v1.1.json`, ghi code hash parser,
pipeline và renderer. Các run Stage 4 v1 giữ nguyên; replay chúng cần code/tool
v1 ghi trong manifest. Validator hiện hành không tự chấp nhận code hash khác.
Cùng input/config/code cho cùng cây/spans/ID/views, không đòi manifest có built_at
khác phải giống byte. Thiếu input, bundle sai, run đã có hoặc output ngoài staging
trả mã khác 0 trước khi ghi. --require-release-ready luôn trả 1 vì còn pending.

## Chuyển sang schema chính thức khi có bằng chứng

Chưa có lệnh promote. Hoàn tất bằng chứng nguồn Stage 2, rà soát extraction Stage 3
và cây/quote/bảng/numbering với nguồn rồi mới nạp các hồ sơ chính thức hợp lệ;
nạp unit cha trước con và spans trong một run mới. Giữ file_id/extraction_id khi
đúng đối tượng bất biến. Text hiệu đính tạo extraction/cây/ID/spans mới, không sửa
offset cũ. Scope/hiệu lực snapshot, chunking, embedding, index và release gate
thuộc các stage sau; chưa thực hiện trong Stage 4.
