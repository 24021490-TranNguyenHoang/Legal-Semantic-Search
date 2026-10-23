# Hoàn thiện ingestion TT38 / TT35 / TT51

Thực hiện 2026-10-22–23, snapshot **2025-01-01**. HEAD được kiểm tra:
`3faaf98946ac24ff5abbf2bdd38e53d1c8975ecb`. Có thay đổi chưa commit trong lượt
này; không stage/commit/push. Các kết quả dưới đây là kiểm tra kỹ thuật và
đề xuất `origin=agent_review`, không phải human review hoặc xác minh pháp lý.

Contract mới: [addendum v1.1](../design/Circulars_Ingestion_Addendum_v1.1.md).
Lệnh tái tạo đầy đủ: [ingestion guide](../ingestion.md). Các addendum/báo cáo
cũ giữ nguyên, không viết lại lịch sử như thể trước đây đã xử lý ba Thông tư.

## 1. Artifact cuối và phạm vi

Đường dẫn tính từ gốc repository. Dùng đúng các run cuối dưới đây; các lần
chạy trung gian vẫn được giữ nhưng không phải bản bàn giao hiện tại.

| Kết quả | Run | SHA-256 của manifest.json |
|---|---|---|
| Metadata 7 nguồn / 10 file | staging/seven-sources-export-006 | a07183e32cc4463a31086615bc116ae404c83ae22a0b201c8a2b2bcbda4e5e1d |
| TT38 bảng | staging/tt38-tables-003 | 884ca64a2c437c47381c5048e164f442fef9f555a56de8c07e7d8a6dff45adcf |
| TT35 cây / preview | staging/tt35-preview-005 | 2336ec69aa9c2927761c9c9de7aa7e696ff6c1b9fe8d5cf742cfce86bd9f1607 |
| TT51 extraction partial | staging/tt51-extraction-005 | f2fd23702436a74b9b03f0cafc0c8876ff409648141a9ee22b4d16ab36125585 |
| TT51 preview bản ban hành | staging/tt51-preview-003 | c31b9d7f07ecc50e4dbba2f1e6102bc98f2b106f0ab39796094320842128184b |

Hồ sơ nguồn mới: `tt35-source-001`, `tt51-source-001`; TT35 extraction:
`tt35-extraction-001`. TT38 tái sử dụng `tt38-extraction-001` và
`tt38-preview-003`. Audit thực thi/ảnh nguồn ở
`staging/circulars-completion-audit-001/`.

| Nguồn | File/trang extraction | Units / spans | Candidate → chunk / context | Chưa xử lý |
|---|---:|---:|---|---|
| TT38 Công báo | 1 / 8, tái sử dụng | 59 / 180, giữ nguyên | 38 chunk / 56 context v1; thêm 9 preview bảng dẫn xuất | Điểm b 279 token; biểu diễn bảng chưa là chunk DDD |
| TT35 bản chính + phụ lục | 2 / 69+179 | 767 / 2.287 | 589 → 572 / 1.070 | 13 source/context blocked, 4 quá budget; toàn 179 trang annex chưa grammar |
| TT51 bản ban hành + QCVN | 2 / 1+403 | 5 / 24, chỉ bản ban hành | 3 → 3 / 3 | QCVN partial, 0 target QCVN |

Tổng phạm vi extraction được sử dụng: 5 PDF / 660 trang. Bản TT38 local
7 trang là nguồn đối chiếu riêng, không nối vào Công báo 8 trang.
Các bộ đếm trang là thực thi reader, **không phải số trang đã đọc rà bằng mắt**.

## 2. Metadata đã sửa

Nguyên nhân: PowerShell `Get-Content` tạo chuỗi có note properties;
`ConvertTo-Json` biến nó thành object gồm value/PSPath/PSDrive/PSProvider…;
exporter cũ chuyển object vào CSV dưới dạng JSON khoảng 46,8 triệu ký tự.
Điểm tiếp nhận/export hiện hành kiểm scalar URL HTTP(S), không chấp nhận
object, JSON nhét trong string, credentials, whitespace/control hoặc URL
quá 8.192 ký tự. Script/capture đã seal giữ nguyên làm bằng chứng lịch sử.

Chỉ unwrap trường legacy TT38 khi đúng cấu trúc 7 keys, law/file receipt,
SHA/size/actual capture timestamp, HTTP200/valid_pdf và exact value trong
HTML Công báo đã capture. Không lấy URL theo tên file hoặc arbitrary value.

Kết quả `metadata_final.json`: 10 dòng, đủ 7 source_id; 6 download_url có căn
cứ, 4 DOCX giữ null. URL Công báo 252 ký tự; 9 retrieved_at lịch sử giữ null.
Riêng Công báo có thời điểm capture thật `2026-10-22T10:43:08.5203746Z`.
CSV đọc bằng `csv.DictReader` mặc định (field limit 131.072), khớp JSONL.
Evidence refs chứa hash/locator tới HTML, observed record và receipt; không
dùng thời gian export/copy làm ngày tải. Không tải thêm nguồn trong lượt này.

Nguồn capture bền vững: `data/source_evidence/circulars-2024/`, cùng raw trong
`data/raw/`. Các trang chính thức đã lưu là docid 211984 (TT35), 211873
(TT38), 211908 (TT51) trên vanban.chinhphu.vn; Công báo TT38 có đường dẫn
`/van-ban/thong-tu-so-38-2024-tt-bgtvt-43378/53130.htm`. URL đầy đủ, hash và
thời điểm có trong metadata/evidence; không suy remote full-file verification
cho các PDF local chỉ từ tên/kích thước attachment.

## 3. TT38: kết luận cho cả bốn đơn vị

| Đơn vị | Trước | Sau policy tt38-cell-row-preview.v1 |
|---|---|---|
| Điều 6 khoản 1 | Blocked bởi bảng | 1 hàng bảng có cell/header/source proof, đạt budget |
| Điều 6 khoản 2 | Blocked bởi bảng | 4 hàng bảng, giữ loại xe/đường và ngoại lệ, đạt budget |
| Điều 11 khoản 2 điểm a | Blocked bởi bảng | 4 hàng khoảng cách, giữ điều kiện trước/sau bảng, đạt budget |
| Điều 11 khoản 2 điểm b | Thiếu dependency dẫn chiếu | Giữ toàn điểm b + điểm a + bảng 3; 279 token, quarantine |

10 ứng viên dẫn xuất: 9 đạt, 1 quarantine; 9 bản đạt có 137–168 token,
unknown=0; không truncate hoặc đổi budget 256. Ba bảng có 33 ô vật lý,
9 hàng dữ liệu. Bất đẳng thức `60 < V ≤ 80`, `80 < V ≤ 100`, `100 < V ≤ 120`
giữ nguyên, cùng đơn vị đo/điều kiện đường khô ráo, tầm nhìn và tốc độ dưới60.
Header/value/row/cell/bbox/page và source slices có trong từng candidate.

**Chín hàng này chưa phải chunk DDD**: ô bảng không thuộc own text của legal
unit hiện có. Lưu `tables.preview.jsonl` với ID `tp_`, representation riêng;
không tạo Khoản/Điểm giả, không sửa chunk.v1. Cần quyết định biểu diễn DDD/cells
trước nhập dataset. 38 chunk/56 context cũ được copy nguyên byte. Xem
`review.md`, `candidates.jsonl`, `tables.quarantine.jsonl`, `encoder_inputs.jsonl`.

## 4. TT35: toàn bộ trang đã extraction, phạm vi đọc rà còn giới hạn

Stage3 giữ 152.791 code point bản chính và 223.087 phụ lục; không có lỗi
extraction. Grammar cũ qua adapter layout tạo 1 document, 67 Điều,
217 Khoản, 482 Điểm; title/text tái dựng bằng 2.287 spans trên PDF normalized.

Nguồn có 7 Phần và các Chương lặp số theo Phần. DDD chưa có cấp Part nên
legal units là projection thưa document→Điều→Khoản→Điểm. Header thật được
giữ trong `structure.pending.jsonl`; 766 liên kết ancestor theo vị trí ở
`unit_structure_dependencies.jsonl`. `SPARSE_PART_CHAPTER_PROJECTION_PENDING`
chặn nhập DDD chính thức; không trình bày cây này là cây cha đầy đủ.

Coverage bản chính theo code point: parsed 142.014; unprocessed 5.951;
supporting/non-body 2.473; layout 2.285; separator 68, tổng 152.791.
Detector đo 11 bảng/cụm ô bản chính và 137 ở annex, tổng 5.541 cells.
So độc lập từng cell với table extraction sau NFC/whitespace fold:
5.541/5.541 khớp. Điều này kiểm slice/binding, chưa xác nhận ngữ nghĩa mọi bảng.
Annex có 28 image objects trên 9 trang, 2 trang có vector curves.

13 candidate bị chặn, tất cả có unit_id/locator/range trong
`blocked.quarantine.jsonl`, `chunk_issues.jsonl`, `source_spans.pending.jsonl`:

- Điều 46 khoản 2; Điều 6 khoản 1; Điều 7 khoản 1.
- Điều 8 khoản 1 điểm a, b, c, d.
- Điều 21 khoản 4 điểm a, b, c, d, đ, e.

Đây là dependency tới vùng bảng/chưa phân tích của **TT35**, không phải nhóm
13 candidate NĐ168 từ lượt trước. Không tạo unit từ ô hoặc bỏ vùng lỗi.
Bốn candidate quá budget: A22K1c=273, A43K2b=273, A43K1b=296,
A16K3b=287 token; toàn nội dung/context giữ trong quarantine.

572 preview đạt kỹ thuật có 60–225 token, tổng unknown=11; tính cả bốn
quarantine thì unknown=13, max296. Hai proposed included A15K1b/A15K2b mỗi
target có 1 unknown: diagnostic cho thấy fragment `chứng_th@@` của lexeme
segmented `chứng_thực_từ` trên encoder_text. Đây chưa phải bằng chứng lỗi
encoding nguyên văn; không sửa model/preprocessing hoặc source offsets.

Agent đọc 133 unit cho scope proposal: 25 included, 27 supporting,
81 excluded; 634 còn pending. Trong 572 preview: 25 included, 15 supporting,
69 excluded, 463 pending. Kết quả kỹ thuật không tự quyết định scope.
179 trang annex giữ extraction/coverage; 3 vùng biểu mẫu XI/XII/XXIII
(PDF34/35/127) proposed supporting theo dẫn chiếu Điều15/28, còn176 pending.
Chưa có policy chunk biểu mẫu; annex không bị coi mặc định excluded.

Đã đọc ảnh mẫu bản chính PDF1/5/18/32/35/47 và annex34/35/127; không tuyên bố
đã đọc bằng mắt toàn248 trang. Các ảnh khác có trong audit chỉ là file render
nếu không có ghi nhận đọc. Các proposal ghi nội dung/lý do/hash trong config.

## 5. TT51 và QCVN: reader hoàn tất nhưng extraction vẫn partial

Bản ban hành 1 trang: Stage3 nguyên bản, 1.609 code point, complete;
1 document/2 Điều/2 Khoản, 24 spans, 3 chunk supporting/3 context,
40–64 token, unknown0. Scope 4 unit supporting và root pending.

QCVN403 trang: adapter PDFium dùng lại normalizer, extraction identity,
trace và SQLite pending Stage3. 349.179 code point trên artifact mới;
không sao offsets từ reader khác. **100 trang không lấy được text,
302 trang có tổng61.891 U+FFFE; trang368 còn lại chỉ có số trang**.
100 warning +302 error =402 issue. Reader hoàn tất, technical_valid=true,
processing_success=false, partial_files=1. `extract-circular` và
`validate-reader` trả exit1 có chủ đích; không báo extraction thành công.

Font diagnostic PDF7 cho thấy CMap ánh xạ CID→U+0000: pdfplumber trả NUL,
PDFium trả U+FFFE. Chưa có phép sửa đã chứng minh trên toàn font/file;
không xóa hoặc biến các ký tự thành dấu cách. Xem `qcvn-font-diagnostic.json`
và `qcvn_font_evidence.json` trong audit. Ảnh PDF7/214/300/368 đã xem:
trang7 có chữ nhìn được; 214/300 không trích text nhưng có nội dung hình/bảng;
368 không chỉ là số trang. Không mô tả nghĩa biển báo từ các ảnh này.

Khảo sát root objects thấy 4.057 image objects trên254 trang và177 trang có
vector paths. Có59 trang trên10.000 root objects: chỉ ghi root count và cờ
inventory incomplete. Giới hạn max_depth=1; các số đếm không phải số biển báo
hoặc chứng minh đã đọc toàn bộ đồ họa. Layout bảng QCVN chưa đo: tables=null
cho403 trang; số tables/cells=0 trong summary là số đã đo, không phải không
có bảng. Danh sách trang cụ thể nằm `page_coverage.jsonl`, `figures.jsonl`,
`unprocessed_regions.jsonl` và audit `qcvn_page_summary.json`.

Không có QCVN target. Backlog hẹp: giải mã/font review trang7; đọc/OCR có
đối chiếu ảnh tại214/300; phân tích dependency hình tại368; đánh giá reader
đồ họa cho59 trang vượt giới hạn. Chưa OCR toàn403 trang hoặc nhận diện hình.
Nếu không giải được font, giữ nguyên lỗi và giới hạn phạm vi, không ghép text
thiếu nghĩa vào context.

Lần pdfplumber toàn QCVN ban đầu dùng trên6GB RAM và bị ngắt sau khoảng20 phút;
`tt51-extraction-001` chưa seal, không tính thành kết quả hoàn tất. Lần002 lỗi
API context manager của PdfPage, đã sửa đóng page/textpage tường minh; các run
trung gian được giữ. Final005 mới là extraction được kiểm/replay và báo partial.

## 6. Kiểm chứng đã thực thi

Windows, Python3.11.9; pdfplumber0.11.10, pypdfium2 5.14.0. Chỉ tokenizer/PyVi
CPU hiện hành; không encoder inference. Chưa thử cài mới từ môi trường sạch
hoặc OS/máy khác trong lượt này. requirements.txt bổ sung dependency trực
tiếp pypdfium2; lock Windows đã có phiên bản đó.

Các lệnh chạy từ gốc repo, prefix:
`$py = '.\.venv-stage1\Scripts\python.exe'`.

```powershell
& $py -X utf8 -B -m unittest tests.test_circular_completion tests.test_tt38_layout tests.test_stage2 tests.test_stage3 tests.test_stage4 tests.test_stage6_points.PointBuilderTests tests.test_leaf_articles.LeafArticleTests
& $py -X utf8 -B -m unittest tests.test_circular_completion
& $py -X utf8 -B -m src.tt38_preview validate-tables --manifest staging/tt38-tables-003/manifest.json
& $py -X utf8 -B -m src.source_inventory validate --manifest staging/seven-sources-export-006/manifest.json
& $py -X utf8 -B -m src.tt38_preview validate-reader --manifest staging/tt51-extraction-005/manifest.json
```

- Suite liên quan: **98 tests đạt, 18,402 giây**; sau bổ sung assertion cấu
  trúc, chạy focused **11 tests đạt, 0,121 giây**. Không cộng hai lần chạy
  thành số test độc lập. Log: `tests-final.log` trong audit.
- Build TT35preview005 và TT51preview003 đã gọi validator/replay cuối build,
  đạt kỹ thuật; danh sách quarantine/pending vẫn được giữ. CLI validate-tables
  và metadata exit0. Validate-reader exit1 đúng với partial QCVN, không né lỗi.
- 7 bản sao bị sửa rồi seal lại để kiểm nội dung: thiếu trang, sai span,
  human review giả, đổi cell value, xóa dependency bảng, URL object,
  xóa U+FFFE đều bị từ chối. `tampering.json` ghi lỗi thực tế; không sửa bundle gốc.
- 572 chunk TT35 giữ ID/content/sourceproof khi thêm structural blocker;
  units/spans/context JSONL byte-identical giữa preview001 và005. Chỉ metadata
  release_blockers thay đổi ngoài identity. Không sửa expected ID để test đạt.
- Baseline281 file raw/evidence/dataset/index/evaluation/ZIP/draft/artifact cũ:
  không thay đổi hoặc mất file (`preservation.after.json`). Đây là tập file
  được chụp baseline, không phải tuyên bố đã hash mọi file staging.

Lệnh build/register/extract cụ thể và dependency có trong ingestion guide.
Mỗi run mới cần thư mục chưa tồn tại; không overwrite các run cũ. Các kiểm tra
tampering/cell/ID độc lập có kết quả JSON trong audit. Kiểm kỹ thuật không kết
luận độ đúng pháp lý hoặc chất lượng retrieval.

## 7. Hiệu lực, giới hạn và đề xuất dataset tiếp theo

Quan sát ngày chung2025-01-01 trong `applicability.observed.jsonl`:
TT38 A12K1, TT35 A66K1, TT51 A2K1, có unit/spans thật.
TT35 A67 chuyển tiếp và TT51 A2K2 thay thế giữ trong cây/spans; chưa đánh giá
ngoại lệ/sửa đổi cho từng unit. Source provenance/edition/applicability vẫn
pending. Không suy mọi quy định active từ ngày hiệu lực chung.

Ưu tiên xem xét cho dataset mở rộng, **chưa nhập**:

1. TT35: 25 target proposed included đã có preview; cần xử lý sparse
   Phần/Chương, scope/applicability và unknown của2 target nêu trên.
2. TT38: 8 target văn bản proposed included đã có ở preview v1; 9 hàng bảng
   dẫn xuất cần quyết định biểu diễn DDD/source cells trước nhập. Điểm b vẫn
   quarantine279, không ép qua budget.
3. TT51: 3 chunk supporting của bản ban hành chỉ dùng khi có dependency
   context phù hợp; chưa có target QCVN đủ nghĩa để đề xuất nhập.

Không đưa 69 TT35 preview proposed excluded hoặc463 pending vào danh sách
included chỉ vì tokenize thành công. Annex/forms/hình cần policy riêng có
nguồn, không bị âm thầm bỏ. Dataset/index v1 **3.077 chunk**, draft **3.082**,
evaluation và ZIP bàn giao vẫn nguyên trạng; không yêu cầu nhóm chuyển bản.

## 8. File mã nguồn/tài liệu thay đổi

| File/nhóm | Lý do |
|---|---|
| src/source_inventory.py | URL scalar có kiểm chứng, CSV semantics và progress binding các run mới |
| src/tt38_preview.py | Thêm routes vào CLI có sẵn; compatibility đúng hash entrypoint v1, không bỏ source/replay checks |
| src/ingestion/table_preview.py | Sidecar bảng TT38 và dependency điểm b, replay/token/quarantine |
| src/ingestion/circular_layout.py | Layout→grammar cũ→PDF spans; structural sidecar Phần/Chương |
| src/ingestion/circular_preview.py | Survey toàn trang, scope/coverage, builder cũ và validator preview |
| src/ingestion/circular_reader.py | Reader PDFium hẹp TT51, bảo toàn lỗi, Stage3 pending DB/trace và exit partial |
| config/source_registration.tt35.v1.json, source_registration.tt51.v1.json | Chọn đúng main/annex đã đăng ký |
| config/circular_scope.proposed.v1.json | Proposal có nội dung/hash/lý do, không reviewer decision |
| tests/test_circular_completion.py | 11 ca URL/structure/table/reader và kiểm chứng hành vi mới |
| requirements.txt | Dependency trực tiếp pypdfium2 |
| AGENTS.md, README.md, docs/ingestion.md, docs/progress/STATUS.md | Phạm vi cho phép, trạng thái, replay và giới hạn |
| Addendum v1.1 và báo cáo này | Contract bổ sung và bằng chứng thực thi; tài liệu gốc không bị sửa hồi tố |

Không sửa schema DDD, raw, core parser/chunker/encoder/hash-bound modules,
ranking/query preprocessing hoặc ứng dụng. Các output mới ở staging, không
stage/commit artifact hoặc mã nguồn trong lượt này.
