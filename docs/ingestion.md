# Ingestion hiện hành — bảy nguồn, preview TT38

Snapshot2025-01-01.7 văn bản đã đăng ký pending; chỉ4 văn bản có dữ liệu
trong dataset/index experimental bàn giao. TT38 preview riêng; TT35/TT51
chưa extraction/parse/chunk. Không coi registered hoặc technical pass là verified.

Danh mục chuẩn và quyết định adapter:
[addendum v1.0](design/Source_Inventory_7_And_TT38_Addendum_v1.0.md).
Số liệu/artifacts thực tế: [STATUS](progress/STATUS.md),
[verification](reviews/Seven_Sources_TT38_Verification.md).

## Nguồn và môi trường

Chạy từ gốc repo, Python3.11, môi trường pipeline đang dùng. Các dependency
trực tiếp: jsonschema, pdfplumber/pdfminer.six; tokenizer-only cần
requirements-stage6.txt (PyVi/transformers assets cục bộ). Không cần chạy
PyTorch encoder, tải model weights, Qdrant hoặc ứng dụng. Windows hiện chặn
DLL PyTorch; lượt này chỉ dùng tokenizer CPU đã kiểm.

Giữ4 DOCX và5 PDF local tại data/raw như cũ. TT38 Công báo bổ sung được giữ
bền vững tại `data/raw/official/38-2024-TT-BGTVT/congbao-1355-1356.pdf` và
capture/provenance trong `data/source_evidence/circulars-2024/`. Không tải
lại nguồn khi chỉ register/extract. SHA
`e27582e2bce4aee27ebc85ffc43731790f887782375ab76e52e2f61981603689`,
file_id `1e28277a-66b1-58c1-900b-360bc4c5ffd5` không đổi khi copy.
PDF7tr local chỉ đối chiếu, không nối vào8tr Công báo.

## Lệnh tái tạo

Thay NEW bằng tên chưa tồn tại; các run cũ giữ nguyên. Các lệnh mới không
có --force hoặc tự chuyển pending thành corpus.

```powershell
# Đăng ký7 văn bản/10 file, không sửa schema/content chính thức
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_registry register --config config/source_registration.seven.v1.json --run-dir staging/seven-sources-registration-NEW

# Chỉ bản Công báo TT38 được chọn cho extraction
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_registry register --config config/source_registration.tt38.v1.json --run-dir staging/tt38-source-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.extraction_pipeline extract --source-manifest staging/tt38-source-NEW/manifest.json --run-dir staging/tt38-extraction-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.extraction_pipeline validate --manifest staging/tt38-extraction-NEW/manifest.json

# Bind rõ run Stage3 vừa tạo; dùng profile layout/builder/tokenizer cố định
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.tt38_preview build --extraction-manifest staging/tt38-extraction-NEW/manifest.json --run-dir staging/tt38-preview-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.tt38_preview validate --manifest staging/tt38-preview-NEW/manifest.json

# Export metadata mới, không ghi đè source_metadata.csv lịch sử
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_inventory export --registry-manifest staging/seven-sources-registration-NEW/manifest.json --dataset-manifest staging/bm25-baseline-v1-001/dataset/dataset_manifest.json --draft-manifest staging/dataset-v2-draft-001/dataset_manifest.json --preview-manifest staging/tt38-preview-NEW/manifest.json --run-dir staging/seven-sources-export-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_inventory validate --manifest staging/seven-sources-export-NEW/manifest.json
```

Build tokenizer cần config/assets theo refs trong `config/tt38_pdf.v1.json`:
encoder_config và tokenizer_assets từ coverage-001 hiện có. Chỉ5 tokenizer
assets, không weights. Chúng được copy vào preview, validate không tokenize
mới; cần runtime/PyVi đúng config/pins khi build. Sau khi dọn coverage run,
có thể phục hồi các assets đúng hash từ preview đã đóng gói vào đường dẫn
profile khai báo; không đổi tokenizer để vượt lỗi. Source/extraction được
tái tạo từ raw/evidence bền vững, không phụ thuộc PDF trong staging cũ.

## Mở artifact và hiểu coverage

- `review.md`: cây đầy đủ, own text, bảng dẫn xuất và chunk/context thực.
- `legal_units.pending.jsonl`, `source_spans.pending.jsonl`: fields tái dựng
  bằng LF-join slices normalized.txt; offsets Unicode code point tuyệt đối.
- `coverage.jsonl`: partition mọi code point, gồm header/signature, source
  whitespace và page separators; không phải phần trăm đã xác minh pháp lý.
- `unit_coverage.jsonl`: trạng thái cho toàn bộ59 units,42 leaf candidates,
  không chỉ các mẫu có chunk. Context/structural-only không phải lỗi.
- `cells.jsonl`:33 ô vật lý, page/bbox và source slices/quote/hash; các ô
  logical None do merge không được nhân bản. `tables.jsonl`:3 bảng thật.
- `tables.derived.jsonl`:9 hàng có header/value cell IDs, own lead và parent
  context. Chỉ biểu diễn dẫn xuất trong quarantine, chưa nhập retrieval.
- `blocked.quarantine.jsonl`:4 target phụ thuộc bảng/context, giữ nội dung/
  spans/cells. `chunks.quarantine.jsonl`: toàn candidate/context quá budget
  nếu có; không truncate. `chunk_issues.jsonl` ghi lý do.
- `encoder_inputs.jsonl`: encoder_text riêng, token IDs/count/unknown; không
  sửa text_original/context/search hoặc source offsets.
- `comparison.jsonl`:12 vùng Điều so bản7tr và8tr, full diff; offsets trong
  field comparison khác extraction offsets, không dùng thay source spans.
- `scope.proposals.jsonl` và `applicability.observed.jsonl`: agent proposals/
  quan sát điều thi hành, không reviewer decisions.

Metadata export `source_metadata.csv` có JSONL tương đương: ô rỗng là null.
DOCX pages=null, local retrieved_at=null khi thiếu log; ngày capture Công
báo thật không phải ngày tải các file khác. Evidence refs có locator/hash;
đường dẫn tương đối theo repo. `source_id_crosswalk.jsonl` giữ alias nội bộ
theo artifact/law, không đổi ID cũ. `source_progress.md` là bảng7 nguồn.

## Kiểm tra

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_tt38_layout tests.test_stage2 tests.test_stage3 tests.test_stage4 tests.test_stage6_points.PointBuilderTests
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_leaf_articles.LeafArticleTests
```

Không cần chạy Dense/BM25/index hoặc toàn suite mô hình để kiểm bước này.
Exit0 của validator chỉ là kỹ thuật; blocked/quarantine có thể là kết quả
hợp lệ của survey. Thiếu nguồn/binding sai/không tái dựng được trả exit1.
Các binary/raw và run staging không tự stage/commit; xem diff trước bước mới.
