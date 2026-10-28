# Phiên2 — quyết định biểu diễn hẹp, v1.0

28/10/2026; snapshot2025-01-01. Không thay DDD SQL, artifact hoặc policy cũ.
Đọc cùng Circular_Priority_Representation_v1.2, Seven_Source_Completion_v1.0
và Source_Revision_DOC_Assessment_v1.0. Đây là quyết định kỹ thuật của agent,
không human review hoặc xác minh pháp lý.

## NĐ168

Đối sánh theo canonical_path duy nhất, loại unit/designation và field; kiểm
identity và spans của cả hai graph. Một field có nhiều edit vẫn chỉ một hàng
trong86field. Phân biệt primary category với các khác biệt phụ trong cùng field.
So sánh quote typography/dấu thanh chỉ dùng để phân loại, không normalize lại
payload nguồn hoặc coi mọi dấu câu khác nhau là vô hại. Các khác từ/số/dẫn chiếu/
dấu kết thúc được đọc ảnh PDF và lưu kết luận riêng; HTML không là chuẩn mặc định.

Sửa DOCX bằng src.source_revision, chạy trên bản dẫn xuất phiên1 và ghi run mới.
Before là paragraph thật, chọn theo Điều/Khoản + nguyên văn; bằng chứng ảnh/SHA
và text đã đối chiếu lưu trong config. Không sửa kiểu dấu ngoặc/cách đặt dấu thanh
chỉ để giống HTML. Parent identity thay đổi thì ID con được tính lại/crosswalk.
Lỗi HTML có related-links lẫn vào Điều55 được xử lý bằng projection graph riêng
trên extraction bất biến; vùng ngoài luật được disposition, không sửa HTML capture
hoặc sao offsets sang extraction giả. Lịch sử graph/đối sánh cũ giữ nguyên.

## TT35 — table-owner-retrieval.v1

Contract table-retrieval.v1 cũ đã giữ cells và owner nhưng chưa biểu diễn đầy đủ
header nhiều tầng/rowspan, continuation nhiều trang và whole-owned-table read
cho tám owner này. Chọn sidecar `table-owner-retrieval.v1`, không sửa hồi tố v1.
Record chứa owner thật/ancestor fields và spans, toàn physical tables/cells,
header bindings, row/header/group relationships, required dependencies và proof.
Không tạo legal unit/chunk.v1 từ ô hoặc gán derived text thành nguyên văn.

Mapping riêng bind canonical owner, page/table IDs, số hàng header và vùng đã
đọc ảnh. Header cho continuation trỏ header gốc; null slot trong physical grid
giữ nguyên. Expanded slot chỉ được tham chiếu tới physical cell có bbox phủ
slot đó; không điền text suy đoán. Row groups/notes/source prose giữ riêng.
Cells và source_slices gắn extraction thật; validator kiểm page, bbox, quote,
hash và membership. Missing/sai owner, header/cell, dependency hoặc proof phải fail.

Consumer preview mới đọc toàn owner/table/context/dependencies; không được đưa
một encoder view thành target pháp lý độc lập. `text_for_search` là bản dẫn xuất
có recipe và cell/header refs, không phải text_original. Dùng encoder cache,
preprocessing/model hiện có và whole-record-encoder-views.v1/budget256. Mọi view
phủ kín search input, không truncate/tăng budget; atom quá dài vào quarantine.
Scope proposal kế thừa chỉ khi đúng unit/hash/crosswalk; phần chưa có giữ pending.
Khép blocker table-owner chỉ có nghĩa representation/read/proof được kiểm;
edition/applicability/độ phủ toàn phụ lục tiếp tục pending.

## QCVN — batch source-region recovery

Tái dùng text/page/cell/image caches. Các bản403/425 dùng source hash và page thật
riêng. Text reader/OCR draft và agent correction ở artifact khác nhau. Phiên âm
chỉ ở vùng đã đọc chắc, offset trên normalized text mới; native PDF text offsets
chỉ dùng cho reader extraction có thật. Locator hình dùng bbox đo được từ PDF
hoặc full-page có nhãn, không bịa glyph coordinate.

Loại vùng: text, table, sign+caption, design image và annex boundary. Mỗi vùng
giữ owner/mã/nhãn/dependencies, phần đã đối chiếu và phần chưa đọc; ảnh/[pic]/OCR
confidence không là proof nội dung đầy đủ. Sửa phiên âm/mapping qua sidecar mới,
không sửa pilot cũ. Trace downstream theo ID/hash/text thật, không suy ảnh hưởng
tất cả artifact chỉ từ cùng law_id.

Batch đầu có gate riêng theo loại; chỉ mở rộng phương pháp đã có proof kiểm được.
Các vùng vẫn phụ thuộc hình hoặc chưa đọc đủ không thành text target đủ nghĩa.
Không tạo dataset/index hoặc scope/applicability/human decision trong phiên2.
