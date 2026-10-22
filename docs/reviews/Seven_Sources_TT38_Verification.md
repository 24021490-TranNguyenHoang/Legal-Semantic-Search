# Bảy nguồn và TT38 — kiểm chứng triển khai

HEAD đầu lượt `2aebab4e4cbc10c4b550a1571855c0fe3bd9d278`. Đã bảo toàn
STATUS/config/report và5 PDF untracked có trước. Đọc AGENTS, Inventory,
BRD/SRS/SDD/DDD liên quan, các contract/code Stage2–4/builder/encoder, báo
cáo đăng ký và manifests thực tế trước sửa. Không stage/commit/push.

## Kết quả và artifact chính

**7 văn bản/10 file đã đăng ký pending;4 văn bản trong dataset/index v1.**
Ba Thông tư chưa thuộc dataset/index hoặc draft3.082. TT38 có preview riêng.

| Source | Văn bản | Hồ sơ file | Parse trong pipeline | Chunk trong dataset v1 |
|---|---|---:|---:|---:|
| SRC-001 | 36/2024/QH15 | 1 DOCX | 982 units; PDF Điều22 riêng | 788 |
| SRC-002 | 168/2024/NĐ-CP | 1 DOCX | 1.304 units; HTML A16K2 riêng | 1.018 |
| SRC-003 | 35/2024/QH15 | 1 DOCX | 868 units, còn deferred | 664 |
| SRC-004 | 165/2024/NĐ-CP | 1 DOCX | 846 units | 607 |
| SRC-005 | 38/2024/TT-BGTVT | 2 PDF khác edition/layout | 59 units PDF mới | 0 |
| SRC-006 | 51/2024/TT-BGTVT | main + QCVN | Chưa extraction/parse/chunk | 0 |
| SRC-007 | 35/2024/TT-BGTVT | main + annex | Chưa extraction/parse/chunk | 0 |

Các số file ở bảng là phạm vi manifest đăng ký tổng hợp, không đếm mọi
capture PDF/HTML cũ làm nguồn/văn bản mới. Tình trạng review nguồn và
applicability vẫn pending. Bốn nguồn cũ và TT38 có agent scope proposals;
TT35/TT51 chưa assessment theo đơn vị. Không có human reviewer event.

Mở:

- `staging/seven-sources-registration-001/manifest.json`: config7/10, JSONL,
  SQLite pending FK/integrity và schema chính thức trống;92 placeholder gates.
- **`staging/seven-sources-export-003/source_progress.md`**: bảng tiến độ.
  `source_metadata.csv`/JSONL có đủ các cột yêu cầu và evidence refs/hash.
  Manifest export SHA `54fe2f5ebaebe5cc5c1e7a8ef967b8a0231c028f74e62fe5e18c1fa6c5205530`.
- **`staging/tt38-preview-003/review.md`**: toàn cây, tất cả own fields,
  bảng/cells, hàng dẫn xuất và preview/context, không chỉ vài mẫu thành công.
  Manifest SHA `a0b664c3bbff8850aadd1ced2d1646b299485943b515067d21ebfbf7b0b044c4`.
- `staging/tt38-extraction-001/`: Stage3 đầy đủ đã validate. Preview có bản
  chụp nguyên extraction snapshot để kiểm lại cùng raw đã lưu bền vững.
- `staging/tt38-verification-001/`: logs validate, determinism, tampering,
  preservation và test summaries. Các run preview001/002, export001/002 là
  bước hoàn thiện trước phiên bản code cuối; không ghi đè chúng. Dùng003.

## Metadata, mapping và độ bền nguồn

Nguồn Công báo copy append-only sang
`data/raw/official/38-2024-TT-BGTVT/congbao-1355-1356.pdf`, SHA
`e27582e2bce4aee27ebc85ffc43731790f887782375ab76e52e2f61981603689`,
file_id **`1e28277a-66b1-58c1-900b-360bc4c5ffd5`** giữ nguyên. Không đổi
raw7 trang, file trong staging cũ hoặc Source Inventory gốc. Không tải thêm.

`data/source_evidence/circulars-2024/` có17 file gồm15 capture/diagnostic/
receipt và manifest/checksum archive mới; các capture/diagnostic được copy
nguyên byte. Ngày archive là sự
kiện copy kỹ thuật, không retrieved_at. Capture gốc của Công báo vẫn
**2026-10-22T10:43:08.5203746Z**. Những đường dẫn cũ trong records copied
là lịch sử, archive_receipt ghi rõ; export mới trỏ tới paths thật bền vững.

Export mới gồm source_id/law_id/file_id/source_set/role/part_order,
local_ref/official_page_url/download_url/SHA/size/pages/retrieved_at/status/
evidence_ref, có locator/hash cho evidence. JSON null/CSV trống là chưa biết:
4 DOCX không có page count đáng tin,5 PDF local chưa có log tải lịch sử.
Không dùng mtime, ngày kiểm tra, ngày copy hoặc2025-01-01 để lấp trường.
Observed/candidate facts không được ghi thành verified.92 Stage2 gates
là profile null/pending, không đồng nghĩa92 facts đều chưa có bằng chứng.

`source_id_crosswalk.jsonl` xác nhận DOCX dataset dùng đúng Inventory. Có
một mapping cần công khai:5 chunk HTML NĐ168 trong draft mang internal
SRC-004, canonical Inventory là SRC-002. Crosswalk bind law_id, artifact
path/SHA, count; **không đổi object/IDs/hash hoặc alias SRC-004 toàn cục**
vì SRC-004 vẫn là NĐ165. Không nhầm Luật35/QH15 với TT35/TT-BGTVT.

## TT38 — đã đọc toàn bộ8 trang

Đã xem ảnh render cả8 trang Công báo, không chỉ text extraction. Nhận diện
12 Điều,3 Chương, các Khoản/Điểm,3 bảng thật, header từng trang và chữ ký.
PDF8tr ưu tiên extraction; PDF7tr là bản đối chiếu riêng, không continuation.
Không yêu cầu xác minh chữ ký số hoặc thêm cổng duyệt mới.

Stage3 hiện có chạy trực tiếp: pdf_text, NFC/LF UTF-8,8 page nodes + root,
**12.694 Unicode code points**,0 warning/error/quarantined file. Text SHA
`a344547ec6d8e0f657931247c3bf8aa99e36b44823b5d6fdaa04939c6feccb97`.
Extraction ID `e_d6d01fb016a96d6aa60b1b5c0aedeb62567f4bb55b1691483e54c1a835bbd361`.
Nguồn/script/tool/config có hash/version, thời điểm extraction thật tách
khỏi thời điểm thu thập; không dùng page-text bằng chứng cũ làm extraction.

Adapter layout kiểm từng dòng bằng slice Stage3 rồi gọi grammar cũ qua
view paragraph/table trong bộ nhớ. Các compatibility tags DOCX của API cũ
không được ghi thành hồ sơ nguồn; mọi span output có format=pdf, page/
offset thật. Root title THÔNG TƯ lấy từ slices thật. Không sửa byte module
grammar cũ để tránh làm hỏng code binding dataset bàn giao. Chi tiết quyết
định và giới hạn: [addendum](../design/Source_Inventory_7_And_TT38_Addendum_v1.0.md).

**59 units** =1 document +3 chapter +12 article +32 clause +11 point;
**180 spans** roundtrip title/text, IDs/parents/citations/ordinal không lỗi,
không chu trình hoặc cấp giả. Header21–28 và chữ ký không vào Khoản cuối.
Khoản12.1 nối đúng qua trang7→8 bằng slices gốc, không nhận dẫn chiếu Điều15
trong câu thành heading hoặc gán header vào nội dung.

| Coverage theo code point | Số lượng |
|---|---:|
| Parsed title/own text pháp lý | 10.058 |
| Supporting/non-body (gồm preamble/header/signature) | 1.173 |
| Unprocessed trong unit text, nhưng có bảng/cells riêng | 1.285 |
| Whitespace/layout từ nguồn | 171 |
| Separator kỹ thuật giữa trang | 7 |
| **Tổng / độ dài extraction** | **12.694 / 12.694** |

Partition100% không có nghĩa100% nội dung đã hiểu/xác minh pháp lý. Tất cả
59 units có unit_coverage;17 context/structural nodes không là target lỗi.

### Ba bảng và bốn candidate bị chặn

| Vùng | Nguồn | Xử lý |
|---|---|---|
| Điều6 Khoản1 | Bảng1, PDFtr4 | Lưu loại xe, ngoại lệ Điều7/8,2 loại đường,60/50 km/h; chặn chunk thiếu bảng |
| Điều6 Khoản2 | Bảng2, PDFtr4 | Lưu4 hàng xe/ngoại lệ/trọng tải,2 loại đường và các tốc độ; chặn chunk thiếu bảng |
| Điều11 Khoản2 Điểma | Bảng3, PDFtr7 | Giữ điều kiện khô ráo, các bất đẳng thức/tốc độ/khoảng cách và đoạn dưới60km/h sau bảng; chặn target thiếu bảng |
| Điều11 Khoản2 Điểmb | Dẫn chiếu giá trị Điểma/bảng3 | Chặn riêng dependency này; không giả context cha đã đủ so sánh giá trị |

**33 ô vật lý**,4 logical None slots do merge và **9 hàng dẫn xuất**. Các
ô có bbox/page/raw PDF hash, source slices/quote/hash trên normalized.txt.
Đối chiếu độc lập33 cell texts bằng `table.extract()` với các source slices
đã map đạt, không sai khác sau NFC/whitespace folding dùng riêng để so sánh.
Hàng dẫn xuất dùng header/value cell IDs, title Điều và own lead/điều kiện
của cha, có ngoại lệ đường cao tốc; không sửa nguyên văn. Chưa table chunk
policy, nên9 hàng ở quarantine và không có chunk ID/embedding/index giả.

Ví dụ Bảng3 giữ chính xác `V = 60 →35m`, `60 < V ≤ 80 →55m`,
`80 < V ≤ 100 →70m`, `100 < V ≤ 120 →100m`. Các ký hiệu/đơn vị lấy từ ô,
không suy số bằng từ khóa. Detector còn báo vùng Điều12 ở trang7–8 như
bảng; ảnh đối chiếu cho thấy false-positive nên profile chỉ nhận3 bảng có
caption/bbox/shape đã xem, giữ Điều12 là text. Không tự bỏ phần thi hành.

### Preview và proposal

**42 leaf candidates →38 chunks/56 contexts;4 blocked;0 over-budget**.
Token measured trên encoder_text bằng preprocessing/tokenizer cũ:
**59–168 token gồm special; unknown0; budget/model limit256**. Không truncate,
đổi tokenizer/model, chạy encoder/inference hoặc tăng budget. Fixtures cũ
được chạy lại cho trường hợp quá budget, thiếu context và issue source.

38 preview kỹ thuật có scope proposals:8 included,13 supporting,17 excluded.
Không dùng con số38 làm số target pháp lý được duyệt. A5 thiết kế đường và
A10 thẩm quyền/quản lý đặt biển được đề xuất excluded theo BRD; các units
vẫn xuất đủ cho coverage kỹ thuật. Context không chứa Điểm anh em hoặc
toàn bộ text con trong own text cha.

Ví dụ Điều9 Khoản3 giữ cả quy tắc60km/h và ngoại lệ đường cao tốc thiết kế
60km/h/phương án được phê duyệt. Ba spans `[7703,7779)`, `[7780,7860)`,
`[7861,7933)` ở normalized.txt tái dựng đúng own text bằng LF, context là
title Điều9 có source proof. Không cắt ngoại lệ để rút ngắn token.

`applicability.observed.jsonl` lưu ngày hiệu lực chung01/01/2025 từ nguyên
Khoản12.1 cùng7 span IDs trang7–8. Đây là agent observation; lịch sử sửa đổi/
chuyển tiếp và applicability từng unit còn pending. Không tự tạo assessment
verified, ngày hiệu lực trên chunk hoặc human decision.

`comparison.jsonl` so đủ12 vùng Điều giữa7tr và8tr:4 exact,5 format_only,
3 bị helper gắn content_difference (Điều6/10/11). Điều6 có khác thứ tự text
flatten trong bảng; không dùng linear diff làm quan hệ hàng/cột. Điều10/11
các fragment diff thực tế là whitespace; chuỗi bỏ whitespace khớp nhưng
không vì vậy tự xác nhận legal equivalence. Full diff/offset trong field
được giữ; không sửa raw hoặc lấy các offset này làm source spans.

## Kiểm chứng đã chạy

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_registry register --config config/source_registration.seven.v1.json --run-dir staging/seven-sources-registration-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_registry register --config config/source_registration.tt38.v1.json --run-dir staging/tt38-source-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.extraction_pipeline extract --source-manifest staging/tt38-source-001/manifest.json --run-dir staging/tt38-extraction-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.tt38_preview build --run-dir staging/tt38-preview-003
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.tt38_preview validate --manifest staging/tt38-preview-003/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.extraction_pipeline extract --source-manifest staging/tt38-source-001/manifest.json --run-dir staging/tt38-extraction-002
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.tt38_preview build --extraction-manifest staging/tt38-extraction-002/manifest.json --run-dir staging/tt38-preview-004
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_inventory export --registry-manifest staging/seven-sources-registration-001/manifest.json --dataset-manifest staging/bm25-baseline-v1-001/dataset/dataset_manifest.json --draft-manifest staging/dataset-v2-draft-001/dataset_manifest.json --preview-manifest staging/tt38-preview-003/manifest.json --run-dir staging/seven-sources-export-003
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_inventory validate --manifest staging/seven-sources-export-003/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_tt38_layout tests.test_stage2 tests.test_stage3 tests.test_stage4 tests.test_stage6_points.PointBuilderTests
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_leaf_articles.LeafArticleTests
git diff --check
```

Build/validate exit0. **78+9=87 tests đạt**, gồm10 fixture layout mới:
heading nhiều dòng, lead, continuation/header qua trang, chữ ký, ô bảng
đánh số không thành Khoản, line/trace mismatch, offset sai, không mutate
input, derived context giữ ngoại lệ và profile không tăng budget. Fixture
synthetic không nhập vào dữ liệu thật. Các module cũ giữ code hashes đúng
binding dataset, không chỉ cập nhật expected values để test đạt.

Tái lập bằng Stage3 run002 có timestamp mới và explicit input binding:
units, spans, chunks, contexts, cells và coverage JSONL **giống nguyên byte**
giữa preview003/004. Không cam kết SQLite/manifest bytes giống do timestamps.
Validate dùng cached encoder evidence có input/token/count/hash; không gọi
tokenize mới. Toàn bộ phép thử trên cùng Windows/môi trường hiện có, chưa
kiểm OS/máy khác hoặc encoder inference bị WAC chặn.

Fault probes trên bản copy (không stub validator): đổi60→600 trong cell,
lệch source span offset, bỏ dependency bảng3 đều bị từ chối sau reseal.
Metadata export thử status=verified hoặc snapshot sai cũng bị từ chối.
Logs thực tế tại `staging/tt38-verification-001/`. Baseline263 file từ đầu
lượt không đổi: raw cũ, CSV/manifests đăng ký cũ, dataset/index, evaluation/
queries, ZIP và draft3082. PDF mới là bản copy append-only duy nhất, không
thay nội dung nguồn cũ. Chưa chạy BM25/Dense/embedding/index/app.

## Thay đổi và việc còn thiếu

Mới:3 config (seven registry, TT38 selection, TT38 layout); adapter layout,
CLI TT38 và exporter inventory;10 fixture tests; ingestion guide/addendum/
báo cáo này; durable PDF/evidence archive. README/STATUS/AGENTS cập nhật có
lịch sử. Config/report Circulars từ lượt trước giữ nguyên; BRD/SRS/SDD/DDD/
Inventory và schema SQL gốc không sửa byte.

Chưa triển khai policy đưa bảng thành chunk, mở rộng dẫn chiếu ngoài cây
cha, promote nguồn/assessment/corpus hoặc corpus-wide legal review. Cần rà
source/edition/độ đầy đủ, scope và applicability có bằng chứng trước corpus.
TT35/TT51 giữ đúng trạng thái chưa extraction; danh sách100 trang PDFium
text rỗng, mẫu NUL trang1–2 và cảnh báo hình/bảng QCVN được lưu nguyên trong
durable evidence. Chưa khảo sát NUL toàn403 trang hoặc OCR/nhận diện biển báo.

Cách tự chạy lại và phục hồi dependency khi dọn staging:
[ingestion guide](../ingestion.md). Nguồn/evidence đã ngoài staging; vẫn phải
giữ các data files chưa commit khi chia sẻ workspace. Không tự yêu cầu nhóm
chuyển dataset, nhập TT38 hoặc rebuild index ở lượt này. Dừng để xem diff.
