# Điều 22 — hồ sơ review có phạm vi và adapter corpus draft

Snapshot **2025-01-01**. Bước này tiếp tục từ `staging/article22-pdf-004/`.
Git sạch lúc bắt đầu; không stage/commit. Đã đọc AGENTS, DDD/schema/README mẫu,
assessment v1.1 và contract mapping trước khi sửa. Không tải thêm nguồn.

## Bàn giao và trạng thái thực tế

| Artifact | Nội dung / kết quả |
|---|---|
| [review.md](../../staging/article22-scoped-review-001/review.md) | Hồ sơ cuối: nguồn/phần, nguyên văn sáu nút, 8 spans, catalog bằng chứng, giới hạn kỹ thuật/lịch sử |
| [decision_template.md](../../staging/article22-scoped-review-001/decision_template.md) | Phiếu ngắn để đọc/ghi nháp; **CHƯA CÓ QUYẾT ĐỊNH** |
| [decision_template.json](../../staging/article22-scoped-review-001/decision_template.json) | Mẫu CLI nhận; reviewer/thời gian/status null, bound PDF IDs mới |
| [page21.png](../../staging/article22-scoped-review-001/page21.png) | Ảnh warning được render từ PDF cũ vào run mới, không OCR/resolve |
| staging/article22-draft-blocked-001/ | Thử nhập mẫu trống: rc=2, technical_valid=true, **13 quyết định còn thiếu**, không tạo content.sqlite/corpus.jsonl |
| staging/article22-draft-fixture-001/ | Đường nhập thành công **synthetic fixture**, schema DDD, draft, 6 units/8 spans/4 assessments, không serving |

Review manifest SHA-256:
`4d61e334558f9a23cead2ef513d3fda9403a380daf62d3519cfc2cb3e840493a`.
Mapping manifest và PDF IDs/hash cũ không thay đổi. Bundle review có binding
riêng: mapping manifest/binding, units/spans, catalog và code/schema. Mẫu có
4 unit PDF mới, không phải IDs DOCX.

**Chưa có corpus draft pháp luật thật**, vì không có quyết định reviewer
thực tế. Đã triển khai đường nhập, không dùng proposal để lấp chỗ trống.
Mẫu thật và history thật vẫn không có event. Thời gian chạy kiểm thử không
được điền vào reviewed_at của người dùng.

## Hồ sơ nguồn và phạm vi đã kiểm

Nguồn là Công báo gốc ngày 24-8-2024:

- Phần 977–978: `36-2024-qh15.pdf`, SHA-256
  `e83b092fd1e93a63d3082424bd63e7ad99afcf39ba3729f6d82ce19fe8b33690`,
  capture thật `2026-10-17T12:15:08.153174Z`.
- Phần tiếp 979–980: `36-2024-qh15_tiep.pdf`, SHA-256
  `55ba152f3abe925d9a75418c3e61bc0122824db41a0d2352053dbff2c6264f8c`,
  capture thật `2026-10-17T12:15:09.952942Z`.
- Cả hai từ `https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/9/`,
  metadata công bố có liên kết hai phần; phần tiếp nêu Tiếp theo Công báo
  số 977 + 978. Catalog giữ URL/log/hash; reviewer cần xác nhận đúng bản và
  các phần cần thiết trong phạm vi này, không xác nhận toàn nội dung hai PDF.

| Vùng | Vai trò và phạm vi |
|---|---|
| Trang 19 / in 94 | Title/đoạn dẫn Điều 22 + Khoản 1–3; đúng 5 fields, 5 spans |
| Trang 1 / in 76 | Root title/preamble: 2 spans, chỉ dependency cấu trúc |
| Trang 10 / in 85 | Title Chương II: 1 span, chỉ dependency cấu trúc |
| Tổng 8 spans / 832 code point | Đã kiểm slice/hash/roundtrip kỹ thuật và đối chiếu hẹp, không đồng nghĩa reviewer accepted |
| Phần tiếp trang PDF 58–61 / in 59–62 | Các lát Điều 88/89 dùng làm bằng chứng; không mở rộng thành unit corpus |
| Ngoài các vùng trên | Chưa đối chiếu toàn văn phần đầu 21 trang hoặc phần tiếp 61 trang; không dùng làm target/context |
| Trang 21 phần đầu | PDF_PAGE_NO_TEXT; ảnh có thông tin xuất bản dạng nét, ngoài 8 spans. Agent chưa thấy ảnh hưởng trực tiếp đến Điều 22; reviewer ghi nhận ảnh hưởng/phạm vi. Không gọi trang trắng, không OCR/resolve |

Chỉ bổ sung ảnh trang 21 được khóa hash trong review catalog vì mapping-004
chưa chứa ảnh cho warning này. Không tải bằng chứng mới; các quote/capture
cũ được sao nguyên byte. accessed_at của ảnh/span dẫn xuất là capture của
PDF nguồn, không phải sự kiện tải ảnh từ Internet hoặc thời gian review.

Căn cứ ứng viên hiệu lực: Điều 88 khoản 1–2 và Điều 89 đã lưu đủ quote/hash/
locator. Agent đề xuất áp dụng từ 2025-01-01 cho bốn đơn vị; ngoại lệ Điều 88
khoản 2 nêu Khoản 3 Điều 10. **Chưa có quyết định hiệu lực thực tế**. Giữ
giới hạn tra cứu lịch sử cũ, gồm lỗi DNS khi tải VBPL trực tiếp; không tuyên
bố không có sửa đổi từ kết quả tra cứu chưa toàn diện. Bản hợp nhất/sửa đổi
2026 chỉ là đầu mối sau snapshot, không thay nội dung năm 2025.

## Xử lý giới hạn review cấp file của DDD

Không yêu cầu reviewer xác nhận toàn file chỉ từ Điều 22. DDD hiện chưa biểu
diễn scoped review trong extraction.review_status; giữ field này **pending**.
Kết quả thực tế theo source_span nằm ở decision_history/catalog và
scoped_review_uses.jsonl, không đổi enum/schema hay cắt extraction giả.

Khi đủ quyết định, draft có thể ghi unit_assessment thật độc lập với trạng
thái review cấp file. DQ-03 vẫn chưa đạt để release. Mọi serving_eligible và
release_eligible false; không chunk/index/freeze/activate. Muốn phục vụ sau
này cần quyết định thiết kế/phương thức review phù hợp được công bố, không
âm thầm nâng pending thành verified hoặc tự yêu cầu ký số/phân quyền.

## Chính xác những hồ sơ còn thiếu

| Đơn vị | Technical | Scope | Applicability |
|---|---|---|---|
| Điều 22 — u_4634338a… | Chưa có accepted/needs_fix cho title/đoạn dẫn | Chưa có; đề xuất supporting | Chưa có kết luận + căn cứ/lịch sử tại snapshot |
| Khoản 1 — u_0ed1674d… | Chưa có | Chưa có; đề xuất included | Chưa có |
| Khoản 2 — u_ade69160… | Chưa có | Chưa có; đề xuất included | Chưa có |
| Khoản 3 — u_bbdec27c… | Chưa có | Chưa có; đề xuất included | Chưa có |

Ngoài 12 ô này, **1 source_review còn thiếu**: đúng hai phần PDF/bản nguồn,
phạm vi đã xem, các spans cha chỉ cấu trúc và ảnh warning, kèm bằng chứng/lý
do thật. Cần reviewer_ref/thời gian rà thực tế cho các quyết định được gửi.
Hai nút cha không cần scope/applicability để chỉ tồn tại trong quan hệ FK;
không tạo assessment giả cho chúng.

Trong JSON, điền đúng các ô đã thực sự kết luận; các ô khác giữ null. Đổi
record_status=submitted khi gửi hồ sơ thật. Có thể hoàn thành một chiều
trước; các chiều khác vẫn pending. Có thể bác proposal bằng lý do/bằng chứng;
ngày kết luận không bị ép theo máy. Không cần tự tính event ID/hash.

Adapter lưu bản submission nguyên byte, history nguồn và unit events; kiểm
supersedes theo unit + chiều (source riêng). Lịch sử cũ không bị ghi đè.
Nếu cần bằng chứng ngoài bộ đã có để kết luận khác, cần bổ sung cụ thể và
binding mới phù hợp, không dùng free-text thay artifact/quote có kiểm tra.

## Adapter và fixture thành công

`src.article22_draft` có review-pack/admit/validate. Dùng lại
assessment_contracts.decision_errors v1.1; source review có validator riêng.
Các mã trả về:

- **0**: hồ sơ review hoặc draft đã tạo/validate thành công.
- **2**: input hợp lệ nhưng thiếu/deferred/needs_fix; báo từng unit/chiều,
  không tạo corpus hoặc DB chuẩn giả.
- **1**: lỗi kỹ thuật/input/binding/hash/evidence/ngày/ràng buộc.

Nhập đủ điều kiện dùng schema DDD nguyên byte, FK ON, refs trong run draft:
1 document, 2 source_file, 2 extraction pending, 6 units, 8 spans, 1 corpus
draft, 1 corpus_document, 4 unit_assessment từ quyết định thật. Metadata có
version/schema/snapshot/time/config/coverage/manifest; document_count=0 vì
chưa có chunk, registered_document_count=1 ghi số văn bản đã nạp riêng.

Fixture tạo được trạng thái trên với `dataset_kind=synthetic_fixture`,
law_id=FIXTURE/0001, version=fixture-20250101-v0.1.0 và cờ --allow-fixture.
Các nguồn/text/reviewer/ngày trong fixture là mô phỏng có ghi nhãn, không
phải tải nguồn hay phê duyệt luật thật. Fixture thử adapter/SQL/decision gates,
không thử reader PDF hay chứng minh chất lượng extraction pháp luật.

Nếu reviewer loại Điều 22 khỏi context, adapter giữ quyết định scope con và
đóng phạm vi dùng phụ thuộc title/đoạn dẫn đó; không suy status cha sang con.
Hai cha luôn structural-only, không target/context. Scoped uses không phải
serving candidates và không đưa vùng chưa rà vào truy hồi.

## Lệnh đã chạy và kết quả

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.article22_draft review-pack --mapping-manifest staging/article22-pdf-004/manifest.json --run-dir staging/article22-scoped-review-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.article22_draft admit --review-manifest staging/article22-scoped-review-001/manifest.json --decisions staging/article22-scoped-review-001/decision_template.json --corpus-version traffic-20250101-v0.1.0 --run-dir staging/article22-draft-blocked-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.article22_draft validate --manifest staging/article22-draft-blocked-001/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.article22_draft admit --review-manifest staging/article22-draft-fixture-review-001/manifest.json --decisions staging/article22-draft-fixture-submission-001.json --corpus-version fixture-20250101-v0.1.0 --allow-fixture --run-dir staging/article22-draft-fixture-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.article22_draft validate --manifest staging/article22-draft-fixture-001/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p test_article22_draft.py -v
$env:VTLS_ARTICLE22_MANIFEST = 'staging/article22-pdf-004/manifest.json'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
git diff --check
```

| Kiểm tra | Kết quả thực tế |
|---|---|
| Review pack thật | rc=0; 0 quyết định; mẫu null; không auto approval |
| Nhập mẫu thật trống | rc=2; 13 ô thiếu; technical_valid=true; không tạo draft/content.sqlite |
| Validate run thật bị chặn | rc=2 đúng kỳ vọng |
| Nhập/validate fixture | rc=0; draft, FK/integrity/export/IDs/spans đạt; extraction pending; serving_chunks rỗng |
| 14 test mới | Đạt: missing decision vs error, binding/hash/evidence/date, independent dimensions, overrides, history/supersedes, FK/schema/state, fixture isolation, import an toàn |
| Toàn bộ hồi quy | **121/121 đạt**, 61,231 giây, bật cả 6 integration mapping cũ; không skipped |
| Tamper sau reseal | Cha vào target/context, frozen DB hoặc extraction verified đều bị từ chối |
| Bảo toàn | **6.436 file baseline** raw/processed/Qdrant/staging cũ: 0 đổi/mất |
| Schema chính thức | Không chỉnh sửa; fixture SQLite dùng đúng byte schema.sql, FK ON |
| Git diff --check | Đạt; không stage/commit |

Log ở `staging/article22-draft-verification-001/`: unittest.log/result,
real_admit.log/result, real_validate.log, fixture_validate.log,
missing_input.log, cli_checks.json và preservation.json. Baseline byte ở
`staging/article22-draft-preservation-001/before.json`.

Fixture demo đã tạo từ các hàm fixture_context/filled_fixture_form trong
`tests/test_article22_draft.py`, không bằng cách điền mẫu dữ liệu thật. Muốn
tái kiểm đường nhập thành công ở máy khác chỉ cần chạy 14 tests trên; chúng
tự tạo nguồn/pack/submission/draft fixture trong TemporaryDirectory staging,
kiểm tra rồi dọn bản sao test. Demo lưu lại nằm trong các run có tên fixture.

## File thay đổi và cách tự làm tiếp

| File | Lý do |
|---|---|
| src/article22_draft.py | Review pack, mẫu/catalog/binding, compiler ba chiều/source history, adapter draft và validator |
| tests/test_article22_draft.py | 14 ca fixture cô lập và negative gates; không mô phỏng approval của người dùng thật |
| docs/design/data_model_v1/Article22_Corpus_Draft_Contract.md | Scoped review sidecar, giữ extraction pending, atomic draft/exit codes/history và fixture boundary |
| Article22_PDF_Mapping_Contract.md / Stage5_Assessment_Contract.md | Ghi bước tiếp đã triển khai, bảo toàn contract/bundle cũ |
| AGENTS.md / README.md | Phạm vi mới và lệnh Windows, cách sao/điền mẫu, nhập/validate/history |
| docs/reviews/Article22_Corpus_Draft_Verification.md | Báo cáo này |

Mở review.md và phiếu Markdown trước, sao JSON ra ngoài run sealed rồi điền
phần thực tế đã rà. README có lệnh Copy-Item/New-Item để làm bản submission,
sau đó admit vào run **mới**. Không sửa mẫu trong bundle, mapping-004 hoặc
run blocked để bổ sung quyết định. Chưa đủ thì giữ pending; đủ mới tạo draft.
Không mở rộng bốn đơn vị, thay parser/raw, tạo chunk/embedding/index, chạy
inference, freeze/activate hoặc tự commit trong bước này.
