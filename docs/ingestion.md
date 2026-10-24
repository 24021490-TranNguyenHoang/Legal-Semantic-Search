# Ingestion hiện hành — bảy nguồn, preview ba Thông tư

Snapshot2025-01-01.7 văn bản đã đăng ký pending; chỉ4 văn bản có dữ liệu
trong dataset/index experimental bàn giao. TT38/TT35 và bản ban hành TT51 có
preview riêng; QCVN còn partial. Không coi registered/technical pass là verified.

## Hiện tại — consumer/index BM25 composition riêng

Index `staging/bm25-composition-001/`, dataset-v3-draft-005 vẫn bất biến.
[Quickstart build/validate/search/read](handoff/Composition_BM25_Quickstart.md),
[verification](reviews/Composition_BM25_Verification.md),
[contract](design/Composition_BM25_Contract_v1.0.md).
3.115 BM25 documents gồm3.106text +9table, không thêm dependency/quarantine;
text_for_search/tokenizer/ranking params giữ nguyên. Search snippet chưa phải
câu trả lời, read trả đủ source/context/required-read units/cells.

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.composition_bm25 validate --index-manifest staging/bm25-composition-001/index_manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.composition_bm25 search --index-manifest staging/bm25-composition-001/index_manifest.json --query "Bằng B số tự động có lái được xe số sàn không?" --top-k 10
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.composition_evaluation --index-manifest staging/bm25-composition-001/index_manifest.json --queries-manifest staging/composition-queries-001/manifest.json --old-index staging/bm25-baseline-v1-001/index_manifest.json --old-evaluation staging/bm25-evaluation-dev-001 --run-dir staging/bm25-composition-evaluation-NEW
```

50dev/limit queries đã cố định, annotations của run mới pending, metrics=null;
không chuyển qrels v1 hoặc suy gap từ khônghit. Nhóm vẫn dùng v1, chưa tích
hợp ứng dụng/Dense/embedding/activate. Các mục dưới giữ lịch sử ingestion.

## Lịch sử — draft experimental composition

Run `staging/dataset-v3-draft-005/`, policy circular-composition.v1.
[Contract](design/Circular_Dataset_Composition_v1.0.md),
[báo cáo/selection/giới hạn](reviews/Circular_Dataset_Draft_Verification.md).
Text3106/table9/context5413/required-read23, không gọi3115 là số text chunk.
13 candidate withheld, mọi trạng thái pháp lý tiếp tục pending/proposed.
Dataset/index v1 và draft3082 không thay đổi.

```powershell
# Build cần repo, upstream manifests/assets/dependencies hiện có; NEW chưa tồn tại
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.tt38_preview dataset-draft --config config/circular_dataset.v1.json --run-dir staging/dataset-v3-draft-NEW

# Sau khi copy nguyên folder draft thành bundle: chỉ Python stdlib
python -X utf8 -I bundle/validate_read.py validate --root bundle
$sampleRecord = Get-Content bundle/table_records.jsonl -Encoding utf8 -TotalCount 1 | ConvertFrom-Json
python -X utf8 -I bundle/validate_read.py read --root bundle --record-id $sampleRecord.retrieval_id
# Phải exit1: consumer thiếu khả năng đọc Part/table/required-read
python -X utf8 -I bundle/validate_read.py validate --root bundle --capabilities chunk.v1

.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_circular_dataset tests.test_circular_priority tests.test_circular_completion tests.test_stage6_points.PointBuilderTests tests.test_leaf_articles.LeafArticleTests
```

Không cài tokenizer/model khi chỉ validate/read. Build mới vẫn replay validators
cũ và priority với môi trường pipeline/tokenizer CPU, không encoder inference.
Không đổi các paths trong payload: đọc membership.proof_base trước, table dùng
manifest.mounts cho logical root. Read trả record, membership và nguyên văn/
spans của required-read dependencies. Xem selection.jsonl, dependencies.jsonl,
delta.jsonl, candidate_comparison.jsonl, crosswalk và review.md.
Metadata historical evidence refs/rebuild-only được ghi trong
evidence/dependency_roles.json; không phải path resolver runtime.
Không nạp flat chunks vào loader v1 hoặc âm thầm bỏ table/Phần. Trên Windows
dùng -X utf8 để tránh lỗi charmap khi xuất nguyên văn. Các mục sau là lịch sử.

## Lịch sử — ưu tiên và pilot hẹp sau ingestion

Run mới `staging/circular-priority-006/` và `staging/qcvn-pilot-002/`.
[Contract v1.2](design/Circular_Priority_Representation_v1.2.md),
[báo cáo](reviews/Circular_Priority_QCVN_Pilot_Verification.md).
Đọc priority.jsonl/review.md cho46 candidate; TT35 chunks.preview/context
trỏ source proof tương đối run này qua tt35/. TT38 text copy nguyên ID/proof
từ binding.tables.parent/base; table records có source_proof_base_ref theo repo.
Không nạp các record này bằng adapter dataset v1 hoặc coi graph Part là DDD v1.

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.tt38_preview priority --config config/circular_priority.v1.2.json --run-dir staging/circular-priority-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.tt38_preview validate-priority --manifest staging/circular-priority-NEW/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.tt38_preview qcvn-pilot --manifest staging/tt51-extraction-005/manifest.json --run-dir staging/qcvn-pilot-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.tt38_preview validate-qcvn-pilot --manifest staging/qcvn-pilot-NEW/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_circular_priority tests.test_circular_completion tests.test_tt38_layout tests.test_stage6_points.PointBuilderTests tests.test_leaf_articles.LeafArticleTests
```

Phiên âm QCVN nằm config/qcvn_pilot.agent_transcription.v1.json: agent đọc ảnh,
không OCR/human review, chỉ phần chọn; không dùng offsets mới thay extraction cũ.
Không có Tesseract/pdftotext trên máy đã thử; không cần tải model/OCR dịch vụ.
Chưa tạo dataset mới. Các mục sau là hướng dẫn/baseline ingestion lịch sử.

## Cập nhật 2026-10-23 — hoàn thiện ingestion

Contract/changelog mới: [Circulars ingestion v1.1](design/Circulars_Ingestion_Addendum_v1.1.md).
Báo cáo bàn giao: [Circulars completion verification](reviews/Circulars_Ingestion_Completion_Verification.md).
Addendum v1.0 và các báo cáo cũ giữ nguyên để replay lịch sử.

| Nguồn | Extraction | Preview hiện hành | Chưa xử lý |
|---|---|---|---|
| TT38 | Công báo8tr, giữ run cũ | tt38-tables-003:38 chunk v1 +9 hàng bảng dẫn xuất | Điểm b A11K2:279 token quarantine; hàng bảng chưa là chunk DDD |
| TT35 | tt35-extraction-001:69+179tr | tt35-preview-005:767 units projection thưa,572 chunk/1070 context | 179tr phụ lục chưa grammar/forms;13 blocked,4 quá budget; Phần/Chương ở sidecar |
| TT51 | tt51-extraction-005:1+403tr, QCVN partial | tt51-preview-003:3 supporting chunk/3 context bản ban hành | QCVN100 trang không text,302 trang U+FFFE; không target QCVN |

Metadata mới dùng `staging/seven-sources-export-006/`: download_url Công báo
TT38 là scalar252 ký tự đã đối chiếu receipt/HTML/hash. Đọc CSV bằng
csv.DictReader mặc định, không nâng field_size_limit để né object lỗi.
Export003/004/005 là lịch sử; manifest006 bind riêng các preview mới.

Pipeline cần pypdfium2 trực tiếp (đã có bản5.14.0 trong lock Windows), ngoài
pdfplumber/pdfminer.six/jsonschema và requirements-stage6.txt để tokenize.
Môi trường hiện kiểm Python3.11.9/Windows; dùng lock cùng assets đã bàn giao.
Không cần tải weights hoặc chạy encoder. Chưa thử lại cài sạch/OS khác ở lượt này.

```powershell
# Từ gốc repo; NEW là thư mục chưa tồn tại. Giữ nguyên các run cũ.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.tt38_preview tables --base-manifest staging/tt38-preview-003/manifest.json --run-dir staging/tt38-tables-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.tt38_preview validate-tables --manifest staging/tt38-tables-NEW/manifest.json

.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_registry register --config config/source_registration.tt35.v1.json --run-dir staging/tt35-source-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.extraction_pipeline extract --source-manifest staging/tt35-source-NEW/manifest.json --run-dir staging/tt35-extraction-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.tt38_preview circular --extraction-manifest staging/tt35-extraction-NEW/manifest.json --run-dir staging/tt35-preview-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.tt38_preview validate-circular --manifest staging/tt35-preview-NEW/manifest.json

.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_registry register --config config/source_registration.tt51.v1.json --run-dir staging/tt51-source-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.tt38_preview extract-circular --source-manifest staging/tt51-source-NEW/manifest.json --run-dir staging/tt51-extraction-NEW
# Dự kiến exit1: reader hoàn tất nhưng QCVN có lỗi text; xem validation_report.json.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.tt38_preview validate-reader --manifest staging/tt51-extraction-NEW/manifest.json
# Main complete tiếp tục độc lập; annex partial không thành target/context.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.tt38_preview circular --extraction-manifest staging/tt51-extraction-NEW/manifest.json --run-dir staging/tt51-preview-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.tt38_preview validate-circular --manifest staging/tt51-preview-NEW/manifest.json
```

TT51 dùng reader adapter hẹp để tránh giữ đồ họa403tr trong RAM; core Stage3/
parser/builder cũ giữ nguyên byte. Chưa hiệu đính NUL/U+FFFE hoặc OCR. CLI gốc
`src.tt38_preview` có thêm subcommands, không tạo executable/framework khác.
`--survey-manifest` chỉ là cache phép đo **cùng SHA manifest extraction**.
Ví dụ tái dùng khảo sát TT35 có sẵn mà vẫn replay cây/chunk và kiểm nguồn:

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.tt38_preview circular --extraction-manifest staging/tt35-extraction-001/manifest.json --survey-manifest staging/tt35-preview-001/manifest.json --run-dir staging/tt35-preview-REPLAY

.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_inventory export --registry-manifest staging/seven-sources-registration-001/manifest.json --dataset-manifest staging/bm25-baseline-v1-001/dataset/dataset_manifest.json --draft-manifest staging/dataset-v2-draft-001/dataset_manifest.json --preview-manifest staging/tt38-preview-003/manifest.json --circular-manifest staging/tt35-preview-005/manifest.json --circular-manifest staging/tt51-preview-003/manifest.json --table-manifest staging/tt38-tables-003/manifest.json --run-dir staging/seven-sources-export-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_inventory validate --manifest staging/seven-sources-export-NEW/manifest.json

.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_circular_completion tests.test_tt38_layout tests.test_stage2 tests.test_stage3 tests.test_stage4 tests.test_stage6_points.PointBuilderTests tests.test_leaf_articles.LeafArticleTests
```

Đường dẫn trên là dependency thực của run hiện tại. Nếu chưa có staging cũ,
khôi phục đúng bundle/assets đã seal hoặc dựng TT38 bằng các lệnh bên dưới
rồi bind manifest mới; không tự chọn tokenizer/model khác. Các scope proposal
TT35 bind unit/hash trong config/circular_scope.proposed.v1.json; đổi nội dung
phải rà lại proposal, không mang reviewer event hoặc tự promote pending.

Mở `review.md`, `page_coverage.jsonl`, `main_coverage.jsonl`, `unprocessed_regions.jsonl`,
`unit_structure_dependencies.jsonl`, `scope.proposals.jsonl`, `region_scope.proposals.jsonl`.
TT35 tables/cells là cấu trúc đo được, annex chưa thành target. TT51 tables=null
trên403tr nghĩa là chưa đo layout bảng, không phải không có bảng. Hình có bbox
không đồng nghĩa đã hiểu nội dung; root inventory bị giới hạn/nested Forms giữ issue.
QCVN page368 chỉ trích được số trang vẫn có hình, không được coi là quy định đủ nghĩa.

TT38 `tables.preview.jsonl`/`tables.quarantine.jsonl` dùng ID tp_ và biểu diễn
dẫn xuất riêng; nguyên văn/cell/source slices không bị thay bằng text_derived.
Đừng ghép thẳng các hàng này vào dataset DDD. Ba Thông tư vẫn ngoài dataset/index
v1 và draft3.082; corpus chưa verified và applicability tiếp tục pending.

## Đường chạy TT38 v1 và đăng ký bảy nguồn (vẫn replay được)

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
