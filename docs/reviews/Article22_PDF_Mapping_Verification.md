# Điều 22 Luật 36 — extraction PDF và chuẩn bị nhập corpus nhỏ

Snapshot **2025-01-01**. Bản bàn giao:
`staging/article22-pdf-004/`. Manifest SHA-256:
`229528f3563556b994bd690aabc397c7dcd7a9b8b32fd1396a9250a1abca3242`.
Đã chạy thực tế; chưa có quyết định reviewer, corpus hoặc phục vụ ứng dụng.

## Kết quả và artifact cần mở

- [Bảng rà soát cuối](../../staging/article22-pdf-004/review.md) và
  [CSV](../../staging/article22-pdf-004/review.csv): nguyên văn, title, cha,
  đề xuất scope, kết quả kỹ thuật, căn cứ hiệu lực và blockers theo từng nút.
- [Toàn bộ diff](../../staging/article22-pdf-004/comparison.md): giữ cả fragment
  và offsets tương đối trong field. Đúng 5 field Điều 22 + ba Khoản khớp bảng
  comparison cũ: title exact, bốn field text chỉ khác 6 lần xuống dòng/space.
- `mapping.pending.jsonl`: 8 lát có field/page/extraction offsets riêng, quote
  và hash; `source_spans.pending.jsonl` là các trường DDD, locator từ trace PDF.
- `identity_crosswalk.jsonl`: cả 6 ID đổi. Root title trên PDF viết hoa khác
  DOCX (8 đoạn diff nội dung, không gọi format_only); cha đổi ID truyền xuống
  con; text Điều/Khoản giữ LF PDF. Không sửa ID dưới payload cũ.
- `source_facts.pending.jsonl`, `source_files.prepared.jsonl`: URL/hash/time
  capture thật cho đúng byte PDF, edition/đủ phần vẫn pending. DOCX không đổi.
- `effectiveness_basis.jsonl`: Điều 88/89, PDF phần tiếp trang 58–61,
  quote/hash/locator riêng. `assessments.pending.jsonl`: ba chiều đều pending.

Nguồn chọn là PDF Công báo phần đầu 977–978 và phần tiếp 979–980, không dùng
bản hợp nhất 2026 làm nội dung áp dụng năm 2025. Lựa chọn nguồn/phương thức
mapping đã được người dùng yêu cầu; không phải quyết định xác minh dữ liệu.

| Đơn vị / field | Trang PDF / in | Extraction [start,end) mới | Page text [start,end) mới | Field [start,end) |
|---|---|---|---|---|
| Gốc / title | 1 / 76 | [134,175) | [134,175) | [0,41) |
| Gốc / preamble | 1 / 76 | [176,294) | [176,294) | [0,118) |
| Chương II / title | 10 / 85 | [19634,19661) | [1088,1115) | [0,27) |
| Điều 22 / title | 19 / 94 | [36927,36963) | [1070,1106) | [0,36) |
| Điều 22 / đoạn dẫn | 19 / 94 | [36964,37116) | [1107,1259) | [0,152) |
| Khoản 1 / text | 19 / 94 | [37117,37363) | [1260,1506) | [0,246) |
| Khoản 2 / text | 19 / 94 | [37364,37473) | [1507,1616) | [0,109) |
| Khoản 3 / text | 19 / 94 | [37474,37577) | [1617,1720) | [0,103) |

Tất cả là Unicode code point [start,end), không phải byte. Page text trong
bảng là lát trace page của extraction **mới**, không phải các file page-019.txt
bằng chứng cũ dù các vị trí tương đối tình cờ giống nhau. Không sao offsets.
Tổng 832 code point được map; không tuyên bố coverage toàn PDF.

Extraction chính: `e_882b3dd8e38859122916639d7be2d500b080134f560fb930c4e944185eb6e4ad`,
38.966 code point, text SHA-256
`96c03cef1346ac820e9f7b817e0e749d1d11f5d5dbf21419e0491ccb562f32ac`.
Text nằm dưới `extraction/extractions/<extraction_id>/normalized.txt`, trace
cùng thư mục. Phần tiếp có 127.604 code point, dùng làm bằng chứng và giữ
extraction pending riêng; không thêm unit Điều 88/89 vào tập con.

Ví dụ đoạn dẫn mới (giữ LF của PDF):

```text
Khi đến gần đường giao nhau, người điều khiển phương tiện tham gia giao thông
đường bộ phải quan sát, giảm tốc độ và nhường đường theo quy định sau đây:
```

Điều 22 có ID
`u_4634338abbd679afb04375a66fe5c3d463c7465f2e6ee06ef2492087882f6f0e`.
Các ID/hash đầy đủ của ba Khoản và cha nằm trong review.md/crosswalk, không
chuyển binding/quyết định DOCX sang những ID này.

## DDD: đã chuẩn bị và còn thiếu

`admission.prepared.sqlite` dùng nguyên schema từ ZIP, bật foreign_keys.
Hash schema trong ZIP, mã nguồn và run đều là
`37280458080d308ca5201be78bb1c59d8bcfbc79a424eb833b6efd2de7bff786`.

| Bảng / lớp | Kết quả thực tế | Điều kiện còn thiếu |
|---|---|---|
| legal_document | 1 hàng thật; law/source ID, title, ngày ban hành có căn cứ, URL metadata; ngày hiệu lực chung null | Quyết định tiếp nhận đúng bản, không suy verified từ INSERT |
| source_file | 2 hàng thật; size/hash/URL/time/part order có log; giữ PDF nguyên byte | Review edition/đủ phần của bộ Công báo; không bù provenance DOCX |
| extraction | 2 hàng pending, tool/config/time/text/trace/hash mới | Review chất lượng extraction theo file; không nâng verified từ 5 field |
| legal_unit/source_span | 6 nút / 8 spans; source slices/hash/ID/FK/roundtrip đạt | Review đúng phạm vi title/text/cha/context; hai cha không chứa lặp con |
| assessment pending | Ba Khoản đề xuất included; Điều 22 supporting; hai cha structural only | Quyết định scope/applicability/technical thực tế, độc lập, theo binding PDF |
| unit_assessment chính thức | 0 hàng | Adapter PDF cho hồ sơ ba chiều + corpus_version thật; không chép proposal thành decision |
| corpus/corpus_document/chunk/chunk_context | Đều 0 | Metadata/version/thành viên thật sau khi đủ điều kiện; chưa freeze/activate |

Hai cha chỉ giữ FK/cấu trúc. Không bắt buộc scope/hiệu lực riêng cho chúng
trong kế hoạch hiện tại vì chưa dùng làm context. Nếu chọn title/preamble của
cha làm context sau này, phải đánh giá phần đó riêng. Điều 22 title/đoạn dẫn là
dependency cần rà của ba Khoản; chưa tạo context truy hồi hoặc chunk_context.

## Việc cụ thể còn cần rà soát

| Việc | Căn cứ đã có | Cần ghi nhận / cách giải quyết |
|---|---|---|
| Tiếp nhận nguồn PDF | Hai PDF nguyên byte, URL, log tải 2026-10-17; metadata liên kết; dòng “Tiếp theo…” | Reviewer ghi đúng ấn bản và đủ phần. Đây không phải xác nhận hiệu lực |
| Chất lượng extraction | NFC/LF, trace, replay; ảnh render trang 1/10/19/21 | Rà chất lượng phần đầu theo mức file mà DDD yêu cầu; không tuyên bố đã rà toàn văn từ 4 unit |
| Warning PDF trang 21 | PDF_PAGE_NO_TEXT; render thấy thông tin xuất bản dạng nét, 0 chars/0 images trong inventory pdfplumber | Reviewer xác nhận non-body/ảnh hưởng đến phần luật; không coi trang trắng, chưa OCR hoặc resolve issue |
| Nội dung và context | Năm field đối chiếu khớp; cha/root/preamble có spans; ảnh trang 1/10/19 đã được agent xem | Review title/đoạn dẫn/Khoản 1–3 và phần cha thực được dùng. Không phê duyệt cả Chương II |
| Scope | Quy tắc nhường đường trực tiếp cho người điều khiển phương tiện | Ghi included cho ba Khoản hoặc bác bằng căn cứ; supporting Điều 22 nếu dùng title/đoạn dẫn. Chưa ghi người dùng duyệt |
| Hiệu lực tại 2025-01-01 | Điều 88 khoản 1 đề xuất ngày chung; khoản 2 chỉ Điều 10 khoản 3; Điều 89 đã lưu đủ 58–61 | Reviewer kết luận riêng cho bốn đơn vị, xác nhận lịch sử/ngoại lệ đã kiểm đủ cho kết luận. Agent có độ chắc chắn vừa về hiệu lực vì lịch sử tra cứu chưa toàn diện |
| Chuyển assessment và nhập corpus | IDs/FK/SQL/JSONL và bản mapping DDD đã có | Agent còn có thể làm adapter PDF/promotion khi được cho phép bước tiếp; dùng hồ sơ quyết định thật, không tạo corpus giả. Chỉ tạo draft khi metadata/thành viên thật sẵn sàng |

Các thiếu sót là hồ sơ review và bước chuyển có kiểm soát cụ thể; không thêm
yêu cầu chữ ký số hoặc hệ thống phân quyền. Không có căn cứ để xác nhận toàn
DOCX/cây/extraction hoặc toàn văn luật từ kết quả so hẹp này. Giới hạn tra cứu
lịch sử cũ, gồm việc tải trực tiếp VBPL từng lỗi DNS, vẫn giữ trong
`inputs/comparison/agent_findings.json`; lượt này không tuyên bố đã tra cứu
toàn diện trở lại. Nguồn sửa đổi/hợp nhất năm 2026 chỉ là đầu mối sau snapshot.

## Lệnh đã chạy và kết quả

Từ PowerShell tại root, dùng `.venv-stage1`, Python 3.11.9, pdfplumber 0.11.10,
pdfminer.six 20260107. Không tải/chạy model hoặc inference.

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.article22_pdf prepare --evidence-manifest staging/stage5a-article22-evidence-001/manifest.json --tree-manifest staging/stage4-docx-005/manifest.json --comparison-manifest staging/stage5a-article22-comparison-001/manifest.json --run-dir staging/article22-pdf-004
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.article22_pdf validate --manifest staging/article22-pdf-004/manifest.json --require-corpus-ready
$env:VTLS_ARTICLE22_MANIFEST = 'staging/article22-pdf-004/manifest.json'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
git diff --check
```

| Kiểm tra | Kết quả thực tế |
|---|---|
| Prepare, gồm Stage 2/3 và hai lượt validation nội bộ | rc=0, technical_valid=true, 6 units/8 spans, 0 reviewer decisions |
| Validate độc lập + require-corpus-ready | rc=1 đúng kỳ vọng; technical_valid=true, release_eligible=false |
| Toàn bộ unittest, gồm Stage 1–5A + 15 test mới | **107/107 đạt**, 52,397 giây; không skipped khi cung cấp biến môi trường |
| Thiếu input / sai PDF hash / sai snapshot / output đã có | Cả 4 rc=1; ba ca đầu không tạo output |
| Tamper sau reseal | Sai code/policy version/offset và tự gán extraction verified đều bị từ chối; thử FK cha thiếu bị SQLite chặn |
| Tái tạo trên PDF thật | 13 đối chiếu giữa run 003/004 đều trùng: units/spans/mapping/comparison/crosswalk, extraction ID/hash/count/trace cả hai PDF |
| Bảo toàn | 5.203 file baseline raw/processed/Qdrant/staging cũ: 0 đổi, 0 mất |
| Schema DDD | Nguyên byte ZIP, FK/integrity/export đạt; không có corpus/assessment/chunk giả |
| Git diff --check | Đạt; không stage/commit |

Test tamper mới dùng bản sao temporary riêng. Để tập trung vào mapping/DB,
các test này mock hai kiểm tra upstream đã được CLI validate đầy đủ kiểm
riêng; không tuyên bố các test cô lập tự replay 82 trang PDF mỗi ca.
Chạy tests không có VTLS_ARTICLE22_MANIFEST vẫn chạy được fixture độc lập,
nhưng 6 ca integration cần artifact local sẽ được báo skipped rõ ràng.

Bằng chứng kỹ thuật: `staging/article22-verification-001/` có
`unittest_final.log`, `unittest_final_result.json`, `negative_checks.json`,
`corpus_gate.log`, `corpus_gate_result.json`, `preservation.json`, `preservation_final.json` (đo lại sau tests cuối),
`determinism.json`, `schema_check.json`. Baseline/ảnh render tại
`staging/article22-preservation-001/`. Không đưa staging/DB vào Git.

Giữ cả log các lượt thử: run 001 dừng vì selector Chương II bắt cả dẫn chiếu
trong câu; đã sửa thành anchor đầu dòng. Run 002/003 là các bản trước hoàn
thiện guard/report, không ghi lại để khớp code hiện tại. Lượt test mở rộng đầu
có 4 lỗi helper reseal do dùng hàm tạo manifest exclusive; đã sửa helper trên
bản sao test, chạy lại 107/107 đạt. Log lỗi cũ giữ riêng, không bỏ qua hoặc
đánh dấu đã pass khi chưa chạy lại. Run bàn giao chỉ là **004**.

## File thay đổi và chạy lại

| File | Lý do |
|---|---|
| src/article22_pdf.py | CLI prepare/validate, Stage 2/3, mapping hẹp, binding/replay, JSONL/SQL/report và pending gates |
| src/content_comparison.py | Selector unique anchors, diff nguyên văn và renderer có thể tái sử dụng |
| config/article22_pdf.v1.json | Khóa nguồn/phạm vi sáu nút và anchor, không nhập offsets cũ |
| tests/test_article22_pdf.py | 9 test fixture + 6 integration; import an toàn, IDs/spans/namespace, scope, negative cases/FK/pending |
| docs/design/data_model_v1/Article22_PDF_Mapping_Contract.md | Quyết định chọn PDF, partial-tree ordinals, namespace, DDD/pending và chuyển review |
| Legacy_DOCX_Content_Comparison_Policy_Proposal.md / Stage5_Assessment_Contract.md | Ghi lựa chọn đường PDF và ranh giới với contract assessment v1.1 |
| AGENTS.md / README.md | Phạm vi mới được phép và lệnh thực tế trên Windows |
| docs/reviews/Article22_PDF_Mapping_Verification.md | Báo cáo này |

Muốn tái tạo, chạy prepare phía trên và đổi `--run-dir` sang thư mục chưa có,
ví dụ `staging/article22-pdf-local-001`; lệnh validate bỏ
`--require-corpus-ready` trả 0 khi kỹ thuật đạt. README có cả lệnh kiểm riêng
Stage 2/3. Ba input local không nằm trong Git; clone mới phải khôi phục đúng
bundle/hash, không bịa lịch sử capture hoặc sửa checksum cho qua kiểm tra.

Chưa làm: parser PDF tổng quát, OCR, mở rộng pilot, ghi quyết định reviewer,
promotion assessment/corpus, chunk/context truy hồi, embedding/index hoặc
kích hoạt ứng dụng. Dừng ở bản chuẩn bị và danh sách việc cần review.
