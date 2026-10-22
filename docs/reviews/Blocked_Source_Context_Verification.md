# Nhóm 13 source/context candidate — kết quả đối chiếu và xử lý

Commit đầu lượt `cc465dafe7015fe4bb748107b43e5d49e4f91a8c`, Git sạch.
Đọc AGENTS/STATUS, parser/chunking contracts, Stage4 review pack, manifest
dataset và mã parser/builder thực. Giữ nguyên công việc Điều lá/evaluation
đã commit trước đó. Không stage/commit/push.

**Kết quả cuối: 1 preview kỹ thuật, 12 deferred; không nhập dataset.**
Run cần xem: `staging/blocked-source-repair-003/review.md`. JSONL đi kèm
có đủ 13 unit_id, citation, own text, context dependencies/spans, issue
impacts, toàn vùng extraction của Khoản, phạm vi bằng chứng và kết quả.

## Mẫu số và bảng trước–sau

Lấy 13 deferred.reason=blocked_source_or_context từ dataset nhúng trong
index vtls-bm25s-lucene.v1, kiểm với unit/status/hash trong coverage.
Dataset vtls-coverage-experimental.v1, content SHA
`2534731881e493a9b1b47b07470cc5d7f4fabbd9553d4e4d6c59e27359b313b5`.
Input binding coverage SHA
`7853192d9be1fac05befe48bbe02d488e2afa8129631474830ca359e2c0d94af`
khớp `staging/stage6-coverage-001/manifest.json`.

| Candidate (đều blocked trước xử lý) | Scope proposal | Lỗi gốc / bằng chứng PDF | Sau xử lý |
|---|---|---|---|
| NĐ168 Điều16 Khoản2 Điểm a | pending | DOCX hai đ), PDF d)/đ), trang40–41 | deferred — context structure nguồn cần bản mới |
| NĐ168 Điều16 Khoản2 Điểm b | pending | Cùng vùng trên | deferred |
| NĐ168 Điều16 Khoản2 Điểm c | pending | Cùng vùng trên | deferred |
| NĐ168 Điều39 Khoản9 Điểm a | excluded | DOCX đ), PDF d), trang84–85 | deferred |
| NĐ168 Điều39 Khoản9 Điểm b | excluded | Cùng vùng trên | deferred |
| NĐ168 Điều39 Khoản9 Điểm c | excluded | Cùng vùng trên | deferred |
| NĐ168 Điều39 Khoản9 Điểm đ | excluded | Ký hiệu chính target khác bản scan | deferred — không relabel/spans giả |
| NĐ168 Điều40 Khoản3 Điểm a | excluded | DOCX đ)/đ)/c), PDF d)/đ)/e), trang85–86 | deferred |
| NĐ168 Điều40 Khoản3 Điểm b | excluded | Cùng vùng trên | deferred |
| NĐ168 Điều40 Khoản3 Điểm c | excluded | Cùng vùng trên, gồm p[1059] | deferred |
| Luật35 Điều84 Khoản1 | pending | Bảng thay thế tbl[2], PDF67/in69 | deferred — chưa hỗ trợ bảng sửa đổi |
| Luật35 Điều84 Khoản2 | excluded | Bảng thay thế tbl[3], cùng trang | deferred — không mở rộng cơ chế ngoài nhu cầu scope |
| Luật35 Điều86 Khoản2 | excluded | p[933] graphic line rỗng, PDF69/in71 | preview — disposition layout có ràng buộc |

13 candidate là **6 nhóm vùng nguồn**. Chúng phụ thuộc **10 issue parser
tại 8 locator**: 7 issue ký hiệu NĐ168, 2 bảng, 1 graphic. Các paragraph
p[518]/p[1057] có nhiều issue cùng vị trí. Paragraph p[1059] bị cách ly
theo vùng, không có issue parser riêng: tổng **9 locator nguồn cần chú ý**.
Không cộng warning Stage3 hoặc record coverage trùng vùng thành lỗi độc lập.
Scope mới nhất gồm 9 excluded proposal, 4 pending; không có quyết định mới.

## Bằng chứng thực sự dùng

Không tải thêm. Tái sử dụng PDF capture ngày 2026-10-16, hash đối chiếu:

- NĐ168: [PDF Chính phủ](https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/01/168-nd-cp.signed.pdf),
  SHA `7bb11b939d162499ab404aa41a940cce05dbf071d9cbae7a8898b00d4b4a48bd`,
  accessed_at `2026-10-16T14:33:07.439116Z`. Đã xem ảnh trang40,41,84,85,86.
- Luật35: [PDF Công báo](https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/9/35-2024-qh15.pdf),
  SHA `debf33ad3b4781c04c143b3b684aaace3e4ecc24110d87ca551ab1cd0221c9fc`,
  accessed_at `2026-10-16T14:33:07.750822Z`. Đã xem ảnh PDF67–69/in69–71.

Đã xem cả ảnh NĐ168 cũ trong assessment trước khi render lại tám trang
để lưu hồ sơ hiện tại. `staging/blocked-source-review-002/evidence_catalog.json`
ghi URL/capture time/PDF hash, page, image hash, page-text hash và render time.
Ngày render/agent review không được dùng thay ngày thu thập hoặc hiệu lực.
Ảnh/page text ở `evidence_pages/`; scan NĐ168 không có text dùng được,
không OCR. Không dựa vào OCR để đoán ký hiệu.

Config lưu quote đọc từ ảnh và quan sát khác biệt. Ví dụ:

> d) Điều khiển xe gắn biển số không đúng với chứng nhận đăng ký xe hoặc gắn biển số không do cơ quan có thẩm quyền cấp (kể cả rơ moóc);

DOCX p[518] có đ). p[519] còn có chữ `ngán hàng`, ảnh là `ngân hàng`, nên
chỉ đổi marker chưa bảo đảm khớp nội dung. Ở Điều40, ảnh ghi:

> e) Lưu trữ hồ sơ, tài liệu, dữ liệu chứng nhận không đúng quy định.

DOCX p[1059] là c). Bản quote là quan sát của agent, không phải source_span
hoặc phiên âm toàn bộ văn bản. Không tuyên bố mọi ký tự toàn file đã khớp.
Toàn vùng lỗi và các Khoản/trang liền kề đã được đọc; source windows giữ
nguyên text extraction gồm cả vùng chưa có unit, ghi rõ không phải span
pháp lý cho nội dung chưa parse.

## Hành động theo nguyên nhân

**Mười candidate NĐ168:** parser đúng khi cách ly literal trùng/nhảy chữ
của DOCX. Nguồn DOCX khác bản scan; giữ nguyên raw và offsets. Hiện không
có cơ chế hiệu chỉnh DOCX dựa scan đã triển khai với provenance/spans hợp lệ.
Mapping PDF Điều22 dùng PDF có text, không thể chép offsets/page text sang
scan này. Giữ deferred với đề xuất cụ thể: tìm đúng bản text chính thức,
hoặc triển khai transcription/OCR có kiểm chứng thành extraction mới, rồi
mapping vùng/cha và tính lại toàn identity bị ảnh hưởng. Không làm trong
lượt này, không tạo nhãn hiệu lực/scope từ sửa ký hiệu.

**Hai bảng Luật35:** ảnh xác nhận là bảng thay thế của luật khác, không
phải danh sách Khoản/Điểm của Luật35. Body hiện tại mới có chỉ dẫn sửa đổi.
Không ghép chuỗi ô tuyến tính hoặc tạo đơn vị giả để làm chunk có vẻ đủ.
Do scope K1 pending và K2 excluded proposal, chưa mở rộng parser bảng.
Cần chốt nhu cầu riêng và quy tắc giữ hàng/cột, văn bản đích, title/context
và spans của ô trước khi khôi phục. Không suy excluded cho K1.

**Luật35 Điều86K2:** XML có DrawingML line cy=0/VML horizontal fallback,
không text/field/numbering; paragraph tiếp theo là câu thông qua. Ảnh
Công báo cho thấy đường kẻ ngăn thân luật với phần ký. Toàn body và title
khớp page text với quy tắc NFC+bỏ whitespace; đã đối chiếu ảnh. Thực hiện
parser disposition hẹp chỉ cho raw SHA/locator/range/bằng chứng đã khóa.
Gọi lại parser cũ, giữ nguyên **868 units/900 spans** của Luật35. So DDD
quan hệ/ID/roundtrip và coverage đạt. Chỉ đổi coverage zero-width thành
layout trong projection mới; sidecar giữ 1 parser issue, 1 coverage
dependency và 2 source warning gốc, vẫn pending ở nguồn cũ.

Không nới validator/parser hiện hành hoặc chấp nhận code hash khác cho
bundle cũ. `src/blocked_source_review.py` là adapter hẹp gọi parser/builder/
validator có sẵn, contract `legal-tree.v1.1.scoped-layout.v1`. Projection
không giả làm bundle Stage4 chính thức đã verified.

## Preview và định danh

Preview duy nhất là Luật35 Điều86K2, 77 token gồm special, unknown=0,
không truncate, preprocessing/model/budget 256 giữ nguyên.

- unit_id cũ/mới: `u_baecee77925b3336a1a53425a7ccc90920f91c5d5c738b682003c5fbfd2ab913`.
- chunk_id mới: `c_44fc2780707d93135616af94fc9674404ac91166c09c575d08be7434578bc013`.
- Cả 13 unit IDs giữ nguyên: không sửa title/body/cha/ordinal. Các deferred
  chưa có identity đã sửa; không bịa mapping ID mới cho chúng.

`chunks.preview.jsonl`, `contexts.preview.jsonl`, `encoder_inputs.jsonl`
giữ nguyên văn/context/bằng chứng, token input thật. Proof refs tính từ
`inputs/` của coverage. Metadata pending/null, release_eligible=false.
Scope excluded của preview giữ nguyên; preview phục vụ kiểm kỹ thuật.

## Kiểm thử và lệnh tái chạy

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.blocked_source_review build --run-dir staging/blocked-source-repair-003
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.blocked_source_review validate --manifest staging/blocked-source-repair-003/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_blocked_source_review tests.test_stage6_points.PointBuilderTests tests.test_stage4.Stage4Tests.test_unresolved_numbering_field_revision_quarantines_and_resumes tests.test_stage4.Stage4Tests.test_duplicate_points_both_quarantined_without_guessing_designations tests.test_stage4.Stage4Tests.test_field_roundtrip_offsets_hash_and_determinism tests.test_stage4.Stage4Tests.test_tables_headers_signature_and_references_not_legal_units
git diff --check
```

Build/validate exit0: 13 candidate, 6 group, 1 preview, 12 deferred; replay
parser/builder/tokenizer và mọi nội dung báo cáo đạt. Đổi run-dir sang tên
mới khi chạy lại; không ghi đè `003`. Hai run `001/002` giữ nguyên các lần
trước khi hoàn thiện hash page text/report windows/guard, dùng `003` với
source hiện tại. Cần các bundle input và evidence review002; không phải
gói portable độc lập.

**23 tests đạt**: gate đường ngang, từ chối text/field/symbol/numbering/
revision/bitmap/shape khác, raw/law/range sai, warning không mong đợi;
reparse không đổi units/spans; hồi quy Khoản/Điểm và parser trùng ký hiệu,
bảng/header/chữ ký, roundtrip. Fixture XML ban đầu dùng encoding alias
`utf8` bị parser XML từ chối; sửa fixture sang chuẩn `utf-8`, không sửa
extraction reader hoặc nới kiểm nguồn.

Thử đổi status trong **bản copy kiểm thử**, tính lại inventory/hash, rồi
validate: exit1 `Review output differs from replay`. Không sửa bundle thật.
Evidence thực thi trong `staging/blocked-source-verification-001/`:
tests.json, validate.json, tampering_test.json, preservation.json.

Audit xác nhận raw thật, coverage, source parser/builder/encoder/retrieval,
dataset 3.077 chunk/5.371 context, index, hai bundle evaluation, query byte
và ZIP bàn giao giữ nguyên. Không build lại dataset/matrix/index hoặc lặp
suite toàn pipeline; upstream Stage2–4 đã chạy cho input trước khi dựng
projection. Không kiểm máy/OS khác, không Word render; chỉ đối chiếu XML
shape giới hạn và ảnh PDF đã lưu. Không OCR/embedding/inference/index.

File thay đổi: thêm adapter, config agent review có bằng chứng, tests,
contract và báo cáo; cập nhật README/STATUS. Không sửa raw hay các module
cũ đã khóa hash. Kết quả kỹ thuật không xác minh nguồn, applicability,
scope hoặc làm corpus đủ điều kiện phát hành.
