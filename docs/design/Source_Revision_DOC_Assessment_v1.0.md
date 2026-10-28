# Source revision / DOC assessment v1.0 — 28/10/2026

Addendum hẹp cho Stage2–4 và Seven_Source_Completion_v1.0; snapshot **2025-01-01**.
Không sửa schema DDD/policy parser đã phát hành. Không sửa raw hoặc tạo dataset.

## NĐ168: bản hiệu chỉnh có nguồn gốc riêng

`src.source_revision` nhận config có SHA raw, SHA PDF và năm ảnh bằng chứng,
Điều/Khoản, toàn bộ before/after. Chỉ áp dụng khi khớp citation + nguyên văn duy
nhất; số paragraph chỉ dùng làm locator chẩn đoán. Sai binding/nội dung là blocker,
không Replace All, không sửa chỗ không khớp. Blocker làm CLI trả mã khác0.

Sửa đúng text node XML, hỗ trợ chuỗi nằm qua nhiều run. Giữ tags, properties,
thứ tự paragraph/table, các ZIP member khác và nội dung ngoài năm chỗ. Kiểm tra
XML ngoài nội dung w:t phải byte-identical; ZIP container có thể được nén lại.
Đây không thay thế kiểm tra render bố cục.

Đầu ra dưới run mới: `sources/`, `corrections.jsonl`, `structure_check.json`,
`revision_manifest.json`, source registration, extraction và graph Stage2–4.
`source_registry` cấp file_id theo law_id+SHA mới; evidence về lịch sử tải DOCX
legacy vẫn null. Không gán download_url PDF cho DOCX hiệu chỉnh. Sidecar revision
giữ liên kết raw→ảnh/PDF→text đã sửa, origin=agent_review, source_status=pending.
Thời điểm tạo bản hiệu chỉnh không phải retrieved_at của raw hoặc ngày hiệu lực.

Giữ công thức unit.v1/source-span.v1. Unit giữ ID khi identity payload không đổi;
source/extraction mới dẫn tới span ID mới. Crosswalk dùng ID hoặc locator nguồn
chính xác, không chỉ citation vì marker sai có thể đổi citation. Vùng trước đây
bị cách ly không có old_unit_id: lưu null và locator cũ, không bịa unit lịch sử.

Nhánh HTML là bản nguồn khác; đối chiếu theo canonical_path để xác định cùng vị
trí pháp lý, không coi các ID khác nhau là hai căn cứ độc lập. Chọn một nhánh cho
lần build sau; không tự nhập đồng thời HTML và DOCX.

## TT51: DOC là đầu vào chẩn đoán, chưa là extraction DDD

`src.qcvn_doc_assessment` đọc đúng năm DOC OLE đã capture, kiểm SHA/size/magic,
URL/part theo anchor trong HTML Công báo có receipt và kiểm PDF đối chiếu.
Part1–5 thuộc cùng serial Công báo1359–1368; DOC/PDF là alternate format, không
phải mười phần được nối vào một văn bản. Không áp pagination403 sang425.

Stage3 hiện nhận DOCX/PDF, chưa nhận DOC nhị phân. Không đổi MIME DOC thành DOCX
để vượt validator. Inventory DOC pending dùng UUID law_id+SHA hiện hành; chưa
nạp source_file/extraction chính thức. Antiword0.37 tạo diagnostic derivatives:

- `reader.raw.txt`: stdout nguyên byte; `reader.docbook.xml`: cấu trúc chẩn đoán.
- `normalized.txt`: UTF-8 strict, NFC và CRLF/CR→LF qua normalizer Stage3 hiện có.
  Không xóa NUL/noncharacter, blank hoặc `[pic]`.
- `lines.trace.jsonl`: offsets Unicode code point và quote hash trên chính
  normalized diagnostic text. Đây là vị trí dòng của output Antiword, **không**
  phải native DOC paragraph/cell/page, không dùng làm span PDF hoặc DDD giả.
- Tool executable/mapping/config/commands/raw hash và output hash nằm trong
  manifest/report. Không chuyển DOC→DOCX trong phiên này.

DocBook table/row/entry là quan sát reader, không chứng minh native cell binding.
`[pic]` không chứng minh hình mất khỏi DOC; hình còn trong binary có thể không
được reader xuất. Metadata nhúng năm2007/num_pages=1 không là edition/page count
thật. Không dùng metadata đó thay nội dung/thông báo Công báo2024.

Ảnh JPEG lấy từ OLE Data, khi khảo sát, giữ stream/byte range/SHA riêng; đây là
native stream locator, không phải tọa độ trang DOC. So ảnh theo thị giác phải ghi
phạm vi đã nhìn; nearest-image/thumbnail score chỉ gợi ý và có thể sai. Không suy
toàn bộ hình/bảng của DOC đã khớp từ một số mẫu.

Validator chẩn đoán kiểm manifest member paths/hash/size, nguồn/part/URL/time,
file ID, PDF binding, normalization và toàn bộ line slices. Thành công không
xác nhận layout, edition, scope/applicability, legal verification hoặc corpus gate.

## Tương thích và điểm dừng

Không sửa module/parser/schema hash-bound cũ. Các run lịch sử giữ nguyên; output
mới và replay vào thư mục mới. Snapshot, proposal và human decisions không đổi;
human reviewer events0, release_eligible=false. Chưa xử lý bảng TT35, build dataset,
index, embedding/inference hoặc ứng dụng. Các vùng chưa đọc chắc giữ blocker.
