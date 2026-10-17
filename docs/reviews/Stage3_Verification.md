# Stage 3 — Báo cáo extraction có truy vết

Ngày báo cáo: 2026-10-16. Snapshot sản phẩm: 2025-01-01.
Đã đọc AGENTS, DDD, Stage2_Source_Contract và báo cáo Stage 2 trước triển khai.
Inference vẫn bị Windows Application Control chặn (WinError 4551); không tải
weights, chạy model, OCR, embedding hoặc index từ corpus thật trong Stage 3.

## Quyết định và file thay đổi

Nguồn pending được extraction kỹ thuật vào staging. Cả nguồn và extraction
vẫn pending; chưa đủ điều kiện phát hành. Không tạo document/file/corpus chính
thức giả để thỏa FK. Schema DDD chính thức và các run nguồn Stage 2 không đổi.
Thiết kế đầy đủ, gồm cách chuyển khi có bằng chứng, nằm trong
`docs/design/data_model_v1/Stage3_Extraction_Contract.md`.

| File/nhóm | Thay đổi |
| --- | --- |
| `src/ingestion/extractors.py` | Reader DOCX paragraph/table/nested cell và các part phụ; PDF theo trang; issues. |
| `src/ingestion/extraction_normalizer.py` | NFC/LF riêng, không cleaning; offsets/hash, raw fragments và separator log. |
| `src/extraction_pipeline.py` | CLI, snapshot Stage 2, pending SQLite/FK, manifest, replay validator, quarantine/release gate. |
| `src/source_registry.py` | Thêm nhận diện header PDF để đăng ký fixture qua Stage 2 đúng file_id; DOCX/UUID cũ giữ nguyên. |
| `config/extraction.v1.json`, `schemas/extraction_v1/` | Chính sách, contract extraction pending và DDL staging riêng. |
| `tests/test_stage3.py` | 16 ca kiểm tra mới và generator fixture PDF/DOCX. |
| `AGENTS.md`, `README.md`, tài liệu contract/báo cáo Stage 3 | Phạm vi được cho phép, lệnh và giới hạn. |

Giữ toàn bộ thay đổi có sẵn. Không sửa cleaner/parser/chunker prototype hoặc
requirements. Không stage/commit hay thêm DB/artifact staging vào Git.

## Bốn DOCX thật

Đã tạo `staging/stage3-docx-001/` và `staging/stage3-docx-002/` từ
`staging/stage2-sources-001/manifest.json`. Có run pilot riêng giữ nguyên.

| Nguồn | Code point normalized.txt | Table main body | Paragraph toàn bộ các part | SHA-256 text |
| --- | ---: | ---: | ---: | --- |
| 168/2024/NĐ-CP | 254247 | 2 | 1381 | d277c4022312afc1385268d56099d15e22b0f51fec12f18a60c2ae10d1d0dc2f |
| 165/2024/NĐ-CP | 168154 | 2 | 982 | 0d6c3838a5c5b6c5c9ff2314d99fc362e2842656fd230c76be3cc87455b50e8e |
| 36/2024/QH15 | 163297 | 2 | 1026 | b6995ae863f8c74df0806f7ca0de3aa7de69fb303f868e0ded54a59ab5972bc7 |
| 35/2024/QH15 | 147573 | 4 | 973 | fe5b160ca998ebc6d80f1515a59e387bf1e19a7939afe78a7b4c4a188e9765a7 |

Kết quả: 4 extraction pending; **4.450 locator**; 0 file partial/quarantine.
Có **13 warning**: 6 visual/symbol-review, 3 generated-content-review và 4 thông
báo ancillary parts được nối có nhãn. Các warning không phải bằng chứng nội
dung đã được kiểm định. Không khẳng định coverage pháp lý 100% từ các con số.

Hai run có cùng text hash, trace hash và extraction_id cho cả bốn nguồn.
created_at/built_at ghi thời điểm chạy thực tế riêng nên không yêu cầu manifest
hoặc SQLite chứa timestamp phải giống byte.

`extraction.pending.sqlite` giữ FK tới pending_source sao chụp Stage 2. Bản
content.sqlite trong source_snapshot vẫn trống; không nạp extraction vào bảng
chính thức. retrieved_at lịch sử trong hồ sơ nguồn vẫn null. review_status và
source_status vẫn pending, release_eligible=false.

## Ví dụ locator/offset thực tế của bảng Luật 35

Chọn record law_id=35/2024/QH15 trong `extractions.pending.jsonl`, rồi mở
text_ref và trace_ref tương ứng. Một paragraph trong bảng phí có:

```json
{
  "part": "word/document.xml",
  "xpath": "/w:document/w:body/w:tbl[2]/w:tr[1]/w:tc[2]/w:p[1]",
  "table_index": 1,
  "row_index": 0,
  "cell_index": 1,
  "paragraph_index": 0,
  "char_start": 142445,
  "char_end": 142505,
  "quote_sha256": "2bb58bdc05aec6838ef2bc188fff297c0e1e56cfb553190221644a9ff30e7c1f"
}
```

Lát `normalized_text[142445:142505]` là:

> Phí sử dụng đường bộ thu qua đầu phương tiện đối với xe ô tô

XPath 1-based; các index phụ 0-based. Offset tính code point, không phải byte.
Table/row/cell cha có locator và span riêng. Dữ liệu bảng này trước đây bị reader
prototype bỏ qua; Stage 3 ghi lại trực tiếp và không quyết định phạm vi pháp lý.

## PDF fixture kiểm soát được

Fixture được tạo bằng generator trong `tests/test_stage3.py`: PDF 2 trang,
trang 1 chứa ASCII biết trước, trang 2 trống. Artifact giữ riêng tại:

- `staging/stage3-pdf-fixture-input-001/`: PDF và khai báo synthetic.
- `staging/stage3-pdf-fixture-sources-001/`: Stage 2 registry, dataset_kind=synthetic_fixture.
- `staging/stage3-pdf-fixture-extract-001/`: extraction pending, không trộn bốn nguồn thật.

Text trang 1, offset [0,50):

```text
KHONG duoc vuot 50 km/h; 0.25 mg/l; 1.000.000 VND.
```

Separator LF ở [50,51); trang 2 có page_start=page_end=2 và [51,51).
Issue PDF_PAGE_NO_TEXT và needs_ocr_review=true ghi rõ cần rà soát trang trống
hay scan; không tự kết luận đây là scan và không chạy OCR.

Fixture không chứng minh mọi PDF thực tế đều đọc đúng, đặc biệt font mã hóa,
tiếng Việt PDF, scan, bảng, nhiều cột hoặc thứ tự đọc theo hình học.

## Lệnh đã chạy và kết quả

Tiền tố thực tế: `.\.venv-stage1\Scripts\python.exe -X utf8 -B`.

| Lệnh/kiểm tra | Kết quả |
| --- | --- |
| `-m src.extraction_pipeline extract --source-manifest staging/stage2-sources-001/manifest.json --run-dir staging/stage3-docx-001` | Exit 0; 4 extraction, 4.450 locator, pending. |
| Cùng input, `--run-dir staging/stage3-docx-002` | Exit 0; nội dung/hash/trace/ID ổn định. |
| `-m src.extraction_pipeline validate --manifest staging/stage3-docx-001/manifest.json` | Exit 0; replay nguồn, contract/hash/DB/locator khớp. |
| Cùng validate, thêm `--require-release-ready` | Exit 1 như mong đợi; không phát hành. |
| `-m src.extraction_pipeline extract --source-manifest staging/stage3-pdf-fixture-sources-001/manifest.json --raw-root staging/stage3-pdf-fixture-input-001 --run-dir staging/stage3-pdf-fixture-extract-001` | Exit 0; 2 page node, 1 issue trang rỗng, pending. |
| Validate PDF manifest với cùng `--raw-root` | Exit 0; kiểm tra kỹ thuật, vẫn không được phát hành. |
| `-m unittest discover -s tests -p test_stage3.py -v` | 16/16 đạt. |
| `-m unittest discover -s tests -v` | 47/47 đạt: 13 Stage 1 + 18 Stage 2 + 16 Stage 3. |
| `git diff --exit-code -- data` | Exit 0; không thay dữ liệu tracked. |
| `git diff --check` | Đạt, chỉ cảnh báo LF/CRLF của Git. |

Test gồm thứ tự paragraph/table thực tế cả bốn DOCX; bảng Luật 35; merged cell
vật lý; tiếng Việt NFD→NFC; không mất số, đơn vị và phủ định; source XPath và
offset slice; coverage leaf+separator; hash/ID lặp lại; thời gian chạy thật;
header part riêng; PDF text/rỗng; DOCX/PDF hỏng cách ly nhưng giữ file tốt; cấu
trúc altChunk thành partial; FK; không fake verified hoặc sửa offsets để pass.
Reader từ chối MIME chưa hỗ trợ; nhánh pipeline unsupported còn được thử bằng
fault injection có nhãn. Không khẳng định đã xử lý RTF thật qua Stage 2.

Case hỏng dùng fixture DOCX XML hỏng và PDF header đúng nhưng body hỏng:
2 quarantine + 1 extraction tốt; batch trả thất bại và giữ run_report=failed.
Test import/build chặn model/index engines. Hồi quy Stage 1 vẫn có BM25 fixture
nhỏ tạm thời; không xây BM25 phục vụ từ corpus thật.

## Bảo toàn và giới hạn bằng chứng

- **14/14** SHA-256 raw, manifest/processed và Qdrant cũ khớp các hash đã ghi ở
  lượt Stage 2; không dùng mtime hoặc ngày hệ thống làm bằng chứng.
- Hai bundle nguồn Stage 2 vẫn qua validator/hash/FK và giữ source UUID cũ.
- Trong lượt xác minh cuối, 11 file data, 3 file Qdrant và 72 file staging có
  trước Stage 3 giữ nguyên fingerprint cây. Snapshot đầy đủ đầu phiên bị output
  tool rút gọn nên không dùng nó để tuyên bố before/after toàn phiên cho 72 file;
  bằng chứng cuối được ghi rõ phạm vi, cộng với sealed manifest của Stage 2.
- Các lệnh ghi chỉ tạo run mới; không di chuyển, xóa hoặc ghi lại raw/output cũ.
  Toàn bộ DB/trace/fixture staging được ignore, chưa stage/commit.

Chưa xác minh pháp lý hoặc quyết định review. Chưa giải mã ý nghĩa hình/OLE,
symbol/font đặc thù, field/automatic numbering, chấp nhận/từ chối revision hay
render thứ tự trang Word. Nội dung hiện hữu và issue/source locator cho phép
đối chiếu tiếp; warning không có nghĩa các trường hợp đó đã được giải quyết.
Không triển khai OCR, parser mới, source_span/legal_unit, chunking hoặc index.

Validator replay cần đúng code/tool/config; hash không thay chữ ký xác nhận
nguồn. Extraction pending chỉ được chuyển qua schema chính thức sau khi có
source_file hợp lệ và rà soát có bằng chứng trong run mới. Stage 3 dừng tại đây.
