# Mapping PDF hẹp Điều 22 Luật 36 — article22-pdf.v1

Snapshot **2025-01-01**. DDD/schema chính thức và assessment v1.1 được giữ.
Yêu cầu mới của người dùng chọn đường 2 trong chính sách DOCX legacy: dùng
PDF Công báo đã capture làm nguồn riêng cho phạm vi này. Lựa chọn thiết kế
không xác nhận nội dung, bản ban hành, hiệu lực hay phê duyệt của reviewer.
Không khôi phục log tải DOCX bằng log PDF; raw và mọi run cũ bất biến.

## Nguồn và phạm vi

- Phần đầu Công báo 977–978 ngày 24-8-2024: URL
  `https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/9/36-2024-qh15.pdf`,
  SHA-256 `e83b092fd1e93a63d3082424bd63e7ad99afcf39ba3729f6d82ce19fe8b33690`.
- Phần tiếp Công báo 979–980: URL cùng thư mục, `36-2024-qh15_tiep.pdf`,
  SHA-256 `55ba152f3abe925d9a75418c3e61bc0122824db41a0d2352053dbff2c6264f8c`.
- Capture hiện có: `staging/stage5a-article22-evidence-001/`, lần tải kết thúc
  lần lượt **2026-10-17T12:15:08.153174Z** và
  **2026-10-17T12:15:09.952942Z**. Ngày tải không phải ngày hiệu lực.
- `source_set_id=SRC-001-gazette-20240824-977-980`; part_order 1/main và
  2/continuation là quyết định điều phối có căn cứ liên kết metadata và dòng
  “Tiếp theo Công báo số 977 + 978” ở phần tiếp. Đủ phần/bản ban hành vẫn có
  trường review pending, không suy từ tên file hoặc hai URL thành verified.
- Chỉ map document, Chương II, Điều 22 và Khoản 1–3. Phần tiếp dùng làm bằng
  chứng Điều 88/89; không tạo unit mới cho Điều 88/89. Các bản HTML/PDF khác
  trong snapshot bằng chứng chỉ dùng đối chiếu lịch sử, không thêm đơn vị pilot.

## Đường chạy và tính bất biến

`python -m src.article22_pdf prepare` preflight manifest/hash của evidence,
Stage 4 và comparison đã có; replay Stage 4/2/3. Kiểm law/hash/snapshot và
binding giữa ba bundle trước output. Không cho run mới nằm trong input cũ.
Thiếu input, cấu hình mở rộng phạm vi, hash sai hoặc output đã tồn tại trả 1.

Run mới sao byte input vào `inputs/`, đăng ký PDF bằng Stage 2 không đổi,
chạy extraction Stage 3 không đổi cho hai PDF vào `extraction/`. Stage 2
vẫn để evidence null theo contract đăng ký; điều này không có nghĩa bỏ mất
log thật. `source_facts.pending.jsonl` giữ capture gốc và sự kiện đã biết;
`source_files.prepared.jsonl` dùng URL/thời gian thật cho **đúng PDF**, không
cho DOCX. Lớp facts tách với edition/completeness/quality còn pending.

Config `config/article22_pdf.v1.json` khóa hash hai PDF, sáu vị trí thật và
anchor literal. Không xây parser PDF tổng quát hoặc sửa parser prototype.
`src/content_comparison.py` chứa logic comparison/selector tái sử dụng;
`src/article22_pdf.py` chứa mapping/CLI/report/validation trong mã nguồn dự án.
Không thực thi script chỉ nằm trong staging để tái tạo kết quả mới.

## Nội dung, offsets và định danh

Chọn lát trên từng trace page của normalized.txt mới bằng anchor duy nhất;
heading Chương II phải bắt đầu dòng, tránh dẫn chiếu “tại Chương II” ở trang 10.
Title Điều 22 bỏ marker bằng cận span; Khoản giữ marker, chữ, dấu, LF gốc.
Field là LF nối các lát theo span_order. Không gộp whitespace trong nội dung
chuẩn; whitespace folding chỉ phân loại diff. Root giữ tên/preamble thật từ
PDF; Chương II không mang bản sao Điều 22; Điều 22 giữ riêng đoạn dẫn.

| Namespace | Quy tắc |
|---|---|
| `input_field_*`, `pdf_field_*` trong diff | Code point tương đối trong field DOCX/PDF tương ứng; không phải offset extraction. |
| `field_char_*` trong mapping | Code point trong title/text_original của unit mới; bao gồm LF nối giữa các span nếu có. |
| `extraction_char_*` / source_span.char_* | Tuyệt đối trên normalized.txt Stage 3 mới, [start,end), không phải byte/token. |
| `pdf_page_char_*` trong mapping | Tương đối trong lát **trace page Stage 3 mới**; absolute = page_extraction_char_start + relative. |
| `official_char_*` của comparison cũ / effectiveness_basis | Trên text từng trang của capture bằng chứng cũ; kiểm riêng, không sao sang source_span mới. |

Quote/hash và ba hệ offset của mỗi mapping được lưu riêng. So lại năm field
đã đối chiếu ở comparison cũ: input unit/field, PDF hash, nội dung và quote hash
phải trùng; offsets cũ chỉ kiểm lại bằng chứng, không dùng để sinh spans.
Diff cha gốc có thay đổi chữ hoa/thường trong title là khác biệt nội dung,
không giấu trong format_only. Đây là nguyên văn hai biểu diễn khác nhau, không
phải tự sửa tên luật hoặc suy bản nào verified.

unit_id dùng nguyên unit.v1 của DDD; span_id dùng source-span.v1 của Stage 4.
Cha được hoàn tất trước con. Chỉ giữ ID cũ nếu **tất cả** identity payload
giống; crosswalk lưu payload/field thay đổi và không chuyển quyết định cũ.
File ID dùng namespace source-file.v1 Stage 2 với law/hash; extraction ID
theo Stage 3. Binding mới khóa code/schema/config và manifest input/extraction.

Ordinal giữ thứ tự trong nguồn đầy đủ: document 0, Chương II 1, Điều 22 12,
Khoản 1–3 là 0–2. Mapping kiểm Chương I/II và chuỗi heading Điều 10–21 trước
Điều 22 trên PDF. Cây chọn lọc không đánh ordinal lại từ 0, không sinh 12 Điều
hoặc Chương I giả để lấp khoảng trống. Đây là quy ước cho tập con, không chạy
validator parser DOCX Stage 4 vốn kiểm cây toàn bộ trên một bundle khác.

## Chuẩn bị schema DDD và assessment

`admission.prepared.sqlite` chạy **schema.sql nguyên bản**, FK ON. Chứa dữ
liệu thật: 1 legal_document, 2 source_file, 2 extraction pending, 6 legal_unit
và 8 source_span. Đây là bản chuẩn bị trong staging, không corpus/release.
Không tạo document/source_file giả, corpus_version giả hoặc nới NOT NULL.
legal_document mô tả số hiệu/ngày ban hành có căn cứ; document_effective_from
để null vì chưa có quyết định xác minh. SQL không có review_status cho document
và legal_unit nên tình trạng pending được giữ trong manifest/facts/assessment,
không coi việc INSERT thành công là verified. Corpus/assessment/chunk đều rỗng.

`assessments.pending.jsonl` giữ đề xuất và mapping DDD riêng cho sáu nút:
ba Khoản included, Điều 22 supporting title/đoạn dẫn; document/Chương II chỉ
structural_dependency_only, scope=null, chưa chọn làm context. Hai cha không
bị bắt hoàn thành scope/hiệu lực chỉ để có FK; nếu sau này dùng title/preamble
làm context thì mới cần assessment tương ứng. Ba chiều scope/applicability/
technical đều pending, không ghi reviewer_ref hoặc verified_at giả.

Đơn vị được chọn có căn cứ ứng viên Điều 88 khoản 1–2, Điều 89 (PDF phần tiếp
58–61). Agent đề xuất 2025-01-01, độ chắc chắn có giới hạn vì lịch sử tra cứu
chưa toàn diện. Ngày 2026 của bản hợp nhất/sửa đổi chỉ là đầu mối ngoài snapshot.
Không mặc định không có sửa đổi, không suy hiệu lực từ lần tải 2026.

Các bước còn thiếu để nhập unit_assessment thật:

1. Ghi quyết định tiếp nhận đúng bản/đủ phần của source set bằng bằng chứng.
2. Review chất lượng extraction phần đầu theo đúng mức **file** của DDD và
   các vùng/cha/spans dùng trong tập con. Không gán verified cả extraction
   từ năm field đã so. PDF_PAGE_NO_TEXT trang 21 được giữ; render thấy thông
   tin xuất bản dạng nét, không gọi là trang trắng, chưa OCR/resolve issue.
3. Reviewer thực tế kết luận scope, applicability và technical độc lập cho
   binding PDF mới, ghi bằng chứng/lý do/thời gian thật; có thể bác proposal.
4. Bổ sung adapter nhận các quyết định PDF theo ba chiều/supersedes như v1.1
   và kiểm binding trước promotion. CLI assessment v1.1 hiện chỉ nhận Stage 4
   DOCX; không đưa manifest mapping vào đó hoặc chép event DOCX sang PDF.
5. Khi đủ điều kiện, cấp corpus draft/version/metadata/thành viên thật và
   chuyển decisions sang unit_assessment đúng DDD; verification_ref và người/
   thời gian lấy từ quyết định thật. Chưa thực hiện bước này khi còn blockers.

Việc ký số/định danh quyền hạn chưa thực hiện là giới hạn, không thêm thành
điều kiện bắt buộc. Không có quyết định pháp lý nào được tạo bởi lệnh prepare.

## Kiểm tra và bàn giao

Validator replay Stage 2/3, mapping, nội dung comparison, unit IDs, spans/hash/
locator, quan hệ/ordinal, JSON Schema, SQL schema/FK/integrity/export và cổng
pending; kiểm danh sách file đúng manifest. Reviewer history phải rỗng trong
bản chuẩn bị. `validate --require-corpus-ready` luôn trả 1 trong phiên bản này.
Không có lệnh freeze/activate/chunk/index; không sửa ứng dụng.

Các run khác thời điểm có created_at/manifest khác; cùng raw/config/code/tool
cho cùng text, trace, units/spans và ID. Source refs/DB chứa đường run nên
không yêu cầu byte toàn bundle giống. README và báo cáo ghi lệnh chạy thật.
