# Vietnamese Traffic Legal Semantic Search

Prototype tra cứu pháp luật giao thông tiếng Việt. Snapshot sản phẩm đã chốt là
**2025-01-01**. Corpus hiện có **chưa được xác minh pháp lý**; kiểm tra đường chạy
hoặc schema không chứng minh nguồn, hiệu lực hay độ bao phủ đúng.

## Tài liệu và phạm vi đợt 1

- Yêu cầu đích: BRD/SRS trong `docs/requirements/`.
- Thiết kế đích: SDD, DDD và Source Inventory trong `docs/design/`.
- Báo cáo: `docs/reviews/Code_Review_Legal_Semantic_Search_v1.0.md`.
- `docs/architecture.md` mô tả prototype cũ; `docs/scope.md` còn giới hạn bốn
  nguồn/1.457 chunk. Các mục này chưa đồng bộ SRS/SDD/DDD.
- SRS/SDD còn để snapshot mở; Source Inventory/DDD đã ghi 2025-01-01 và người
  dùng đã xác nhận. Không dùng ngày hiện tại hoặc nhãn "mới nhất" làm snapshot.
- Bộ mẫu có ở `docs/design/data_model_v1/Data_Model_Schema_Examples_v1.0.zip`,
  chưa giải nén. README, SQL, JSON Schema và validator trong đó là thiết kế và
  fixture giả lập, không tự thay thế parser hay kiểm định corpus.
- Chưa có kế hoạch đánh giá chi tiết, đề bài PDF được SRS tham chiếu, hồ sơ
  phê duyệt toàn nhóm hoặc bằng chứng kiểm định từng nguồn trong repo. Vì vậy
  đợt này không kết luận đạt nghiệm thu pháp lý, retrieval hoặc hiệu năng.

Đợt 1 chỉ chuẩn hóa đường chạy và môi trường. Giữ nguyên thuật toán cleaning,
parser/chunker, model BKAI, pooling, truncation 256 token và retrieval/heuristic.
BM25 builder vẫn dùng `lower().split()`; retriever vẫn dùng regex riêng và
dựng BM25 trong RAM. Các sai lệch đã khảo sát sẽ xử lý trong đợt sau.

## Cài trên Windows PowerShell

Chạy từ thư mục gốc repository. Dùng **CPython 3.11 x64**. Không cần kích hoạt
venv nên không cần thay đổi PowerShell Execution Policy.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -c requirements-win-py311.lock.txt
.\.venv\Scripts\python.exe -m pip check
```

`requirements.txt` liệt kê dependency trực tiếp, gồm `python-docx`, `pdfplumber`,
`torch`, `transformers`, `numpy` và `jsonschema`. File constraints
`requirements-win-py311.lock.txt` ghi toàn bộ phiên bản đã cài trong môi trường
sạch Windows/Python 3.11.9. Không dùng file này như cam kết tương thích mọi OS,
GPU hoặc Python; chưa kiểm tra các môi trường đó. Model weights không đi kèm
dependency; lệnh inference thật có thể tải weights nếu cache chưa có.

Trong phiên kiểm tra đợt 1, môi trường sạch nằm ở `.venv-stage1/`. Cài package và
`pip check` thành công, nhưng **Windows Application Control chặn DLL PyTorch
(WinError 4551)**, cả khi thử ngoài sandbox. Vì vậy chưa xác nhận được inference
hoặc demo trên máy này. Không tự thay chính sách bảo mật; cần môi trường được
quản trị cho phép chạy DLL trước khi thử model. Smoke import từng dependency
được báo riêng trong báo cáo đợt 1.

## Quy ước CLI và an toàn dữ liệu

Chạy script bằng `python -m src...`, không chạy đường dẫn `.py` trực tiếp.
Các đường dẫn mặc định trong `src/config.py` dựa trên thư mục repo; tham số
đường dẫn tương đối trên CLI được giải theo thư mục làm việc hiện tại.

Các lệnh ingestion/index đều có `--help`, `--run-dir` bắt buộc và `--check-only`:

- `--run-dir` phải là thư mục **chưa tồn tại**, nằm dưới `staging/`. Không có
  `--force`, không ghi vào raw, corpus hay database prototype hiện có.
- Kiểm tra đầu vào trước khi tạo thư mục chạy, mở model hoặc database. Dữ liệu
  JSONL phải có object, ID duy nhất, text không rỗng và không có dòng trắng;
  Qdrant còn kiểm tra vector hữu hạn, 768 chiều, khác vector 0.
- `--check-only` không tạo output/run directory hoặc khởi tạo model/database.
  Cleaner kiểm tra bằng cách đọc và làm sạch nguồn; chunker chạy parser trong
  bộ nhớ. Với embedder/indexer, đây chỉ là kiểm tra input, không phải thử engine.
- Exit code: `0` thành công, `1` lỗi input/xử lý/dependency, `2` sai/thiếu tham số.
  PowerShell đọc bằng `$LASTEXITCODE`. Không có thông báo thành công khi thất bại.
- Khi đã tạo run, `run_report.json` ghi `success`/`failed`; lỗi trước đó ghi ra
  stderr và không tạo run. Report là kết quả kỹ thuật, không phải release
  manifest hoặc bằng chứng pháp lý. Chỉ dùng output của run `success`.
- Embedding/BM25 chỉ đổi tên file `.partial` khi hoàn thành; database dở dang
  trong run lỗi phải giữ cách ly. Dùng run ID mới để chạy lại; không xóa dữ liệu cũ.
- Chưa có activation/release/rollback ở đợt 1. Không trỏ demo sang staging.

## Kiểm tra không ghi dữ liệu

Các đường dẫn `staging/check-*` bên dưới phải chưa tồn tại; check-only cũng từ
chối thư mục đã tồn tại để cùng quy tắc với lệnh ghi.

```powershell
.\.venv\Scripts\python.exe -X utf8 -B -m src.ingestion.cleaner --input-dir data/raw --run-dir staging/check-clean --check-only
.\.venv\Scripts\python.exe -X utf8 -B -m src.ingestion.chunker --input-dir data/processed/cleaned --run-dir staging/check-chunks --check-only
.\.venv\Scripts\python.exe -X utf8 -B -m src.ingestion.embedder --input data/processed/corpus_chunks.jsonl --run-dir staging/check-embed --check-only
.\.venv\Scripts\python.exe -X utf8 -B -m src.database.bm25_store --input data/processed/corpus_chunks.jsonl --run-dir staging/check-bm25 --check-only
.\.venv\Scripts\python.exe -X utf8 -B -m src.database.qdrant_setup --input data/processed/corpus_embedded.jsonl --run-dir staging/check-qdrant --check-only
```

## Chạy cleaning/chunking vào staging

```powershell
.\.venv\Scripts\python.exe -X utf8 -B -m src.ingestion.cleaner --input-dir data/raw --run-dir staging/clean-001
.\.venv\Scripts\python.exe -X utf8 -B -m src.ingestion.chunker --input-dir staging/clean-001/cleaned --run-dir staging/chunk-001
```

Đầu ra là `staging/clean-001/cleaned/` và
`staging/chunk-001/corpus_chunks.jsonl`, cùng report mỗi run. Parser hiện vẫn
thiếu Điểm/Chương, bỏ đoạn dẫn và gán hiệu lực mặc định: đây là output prototype
cách ly, chưa thể phát hành. Không tăng độ tin cậy pháp lý từ việc lệnh trả 0.

## Lệnh có model/index — tham khảo cho các đợt sau

**Không chạy các lệnh ghi embedding/Qdrant sau trong đợt 1.** Chúng được liệt kê
để đối chiếu CLI với code; chưa được smoke test bằng model hoặc database thật.

```powershell
.\.venv\Scripts\python.exe -X utf8 -B -m src.ingestion.embedder --input staging/chunk-001/corpus_chunks.jsonl --run-dir staging/embed-001
.\.venv\Scripts\python.exe -X utf8 -B -m src.database.bm25_store --input staging/chunk-001/corpus_chunks.jsonl --run-dir staging/bm25-001
.\.venv\Scripts\python.exe -X utf8 -B -m src.database.qdrant_setup --input staging/embed-001/corpus_embedded.jsonl --run-dir staging/qdrant-001
```

BM25 nhận chunks trực tiếp, không cần vector; tokenizer/công thức cũ được giữ.
Qdrant mới chỉ nằm ở `staging/qdrant-001/qdrant_db/`; collection cũ không bị xóa.
ID theo vị trí vẫn là giới hạn prototype, chưa chuyển UUID/hash theo DDD.

Demo vẫn đọc corpus/Qdrant prototype hiện có theo config. Dữ liệu đang lệch
vector/text như báo cáo khảo sát; các lệnh dưới không phải kiểm định chất lượng.
Chỉ chạy khi chủ động muốn thử demo và model dependencies chạy được:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B -m src.search.search_db --query "vượt đèn đỏ bị phạt như nào" --top-k 3
.\.venv\Scripts\python.exe -X utf8 -B -m src.search.test_search --query "vượt đèn đỏ" --top-k 3
.\.venv\Scripts\python.exe -m streamlit run src/frontend/app.py
```

`test_search` là demo Dense cũ, không phải evaluator và vẫn giữ dot-product của
script cũ; không dùng nó để kết luận chất lượng encoder hoặc so sánh bốn mode.

## Tự kiểm tra lại đợt 1

```powershell
.\.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
git diff --check
git status --short --untracked-files=all
git diff
```

Test suite dùng fixture tạm dưới staging, so hash các file `data/` và `qdrant_db/`
trước/sau, kiểm tra import không ghi/xóa/kết nối mạng hoặc khởi tạo dependency
nặng, CLI lỗi, không ghi đè, parser không đổi và lỗi build có report. Không tạo
embedding hoặc Qdrant. `-B` tắt cache bytecode của Python trong phép thử import.
Tệp môi trường, cache và staging được ignore; chưa stage hoặc commit thay đổi.

## Stage 2: đăng ký nguồn và kiểm tra manifest

Xem [contract nguồn Stage 2](docs/design/data_model_v1/Stage2_Source_Contract.md)
về schema chính thức, lớp pending, định danh và cách chuyển khi có bằng chứng.
Stage này dùng standard library và jsonschema đã cài; không tải hoặc chạy model.

Chạy từ repo root; mỗi lần register dùng run directory mới:

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_registry register --run-dir staging/sources-local-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_registry validate --manifest staging/sources-local-001/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_registry validate --manifest staging/sources-local-001/manifest.json --require-release-ready
$LASTEXITCODE
```

Hai lệnh đầu trả 0 khi đăng ký/kiểm tra kỹ thuật thành công. Lệnh thứ ba **phải
trả 1**: bốn nguồn còn pending, chưa đủ bằng chứng và chưa chạy các cổng release.
`built_at` không phải `retrieved_at`; không lấy nhãn active trong CSV cũ làm xác minh.

Mặc định đọc `config/source_registration.v1.json`. `--config PATH` chọn khai báo
khác; `--raw-root DIR` là root chứa raw/inventory theo các ref tương đối (mặc định
repo root). Không chuyển namespace file_id khi chạy lại. Để tái tạo SQLite, chạy
register với cùng config/raw vào run mới, rồi validate:

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_registry register --config config/source_registration.v1.json --run-dir staging/sources-local-002
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_registry validate --manifest staging/sources-local-002/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
```

`content.sqlite` có 12 bảng/view DDD nhưng chưa nạp hồ sơ thiếu bằng chứng;
`pending.sqlite` đăng ký bốn file và quality issue riêng. Các JSONL pending có
nhóm measured/declared/evidence tách biệt; evidence chưa có là null. Chưa tạo
extraction. Manifest và sidecar hash kiểm tra cả SQLite/JSONL/config/schema.
Các artifact nằm trong staging và được ignore, không đưa database vào commit.

## Stage 3: extraction có truy vết

Xem [contract extraction Stage 3](docs/design/data_model_v1/Stage3_Extraction_Contract.md).
Luồng mới đọc nguồn pending Stage 2, tách reader và NFC/LF khỏi cleaner prototype,
ghi paragraph/table/row/cell hoặc page cùng offsets và hash. Không sửa parser,
không OCR hoặc model. Mọi nguồn/extraction vẫn pending, không được phát hành.

Ví dụ dùng run Stage 2 hiện có (hoặc thay bằng manifest từ lệnh register ở trên):

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.extraction_pipeline extract --source-manifest staging/stage2-sources-001/manifest.json --run-dir staging/extraction-local-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.extraction_pipeline validate --manifest staging/extraction-local-001/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.extraction_pipeline validate --manifest staging/extraction-local-001/manifest.json --require-release-ready
```

Run dir phải mới. Hai lệnh đầu trả 0 nếu reader hoàn tất và bundle nhất quán;
lệnh cuối phải trả 1 vì nguồn và extraction chưa verified. `--config` mặc định
`config/extraction.v1.json`; `--raw-root` mặc định repo root, cần chỉ rõ nếu ref
của fixture ở root khác. Validator replay cần cùng code/tool version của run.

Output chính: `extractions.pending.jsonl`, `file_status.jsonl`, `quality_issues.jsonl`,
`extraction.pending.sqlite`, `extractions/<id>/normalized.txt` và `trace.json`;
source snapshot, config/schema, manifest/sidecar và reports cũng nằm trong run.
Offsets [start,end) tính theo code point của normalized.txt. Mỗi fragment có text
trước normalization; separators LF/TAB có record riêng. Không gọi clean_text.

File partial/quarantine vẫn có status/issue, phần thành công của batch được lưu;
batch trả 1 và run_report=failed. Trang PDF không text có page node rỗng và issue
PDF_PAGE_NO_TEXT; cần rà soát trang trống hay scan, không tự chạy OCR. Header/note
DOCX có part riêng; không giả định thứ tự trang Word hay giải mã ý nghĩa hình.

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p test_stage3.py -v
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
```

PDF fixture trong `tests/test_stage3.py` có một trang text ASCII biết trước và một
trang rỗng; fixture DOCX có tiếng Việt, negation, số/đơn vị, bảng và merged cell.
Test tạo dưới staging riêng và không nhập vào corpus thật. Fixture không chứng
minh mọi PDF (font, scan, nhiều cột, bảng phức tạp) đều được đọc đúng. Báo cáo
Stage 3 có kết quả bốn DOCX thật, ví dụ locator và các giới hạn còn lại.

## Stage 4: parser cây pháp lý có truy vết

Xem [contract parser Stage 4](docs/design/data_model_v1/Stage4_Parser_Contract.md)
và [báo cáo kiểm tra](docs/reviews/Stage4_Verification.md). Parser mới dùng bundle
Stage 3, không dùng cleaned TXT hoặc corpus prototype. Nguồn/extraction pending
được phân tích vào staging; units và spans tiếp tục pending, không được phát hành.
Không chạy model, chunking, đánh giá scope/hiệu lực hoặc xây chỉ mục.

Chạy tại repo root trên PowerShell, chọn run directory **chưa tồn tại**:

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.legal_parser parse --extraction-manifest staging/stage3-docx-001/manifest.json --run-dir staging/legal-tree-local-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.legal_parser validate --manifest staging/legal-tree-local-001/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.legal_parser validate --manifest staging/legal-tree-local-001/manifest.json --require-release-ready
$LASTEXITCODE
```

Hai lệnh đầu trả 0 khi kỹ thuật nhất quán; lệnh thứ ba trả **1** vì chưa đủ
bằng chứng phát hành. Thay manifest đầu vào bằng `staging/extraction-local-001/manifest.json`
nếu vừa tạo bằng ví dụ Stage 3 ở trên. Có thể truyền `--raw-root DIR` cho cả parse
và validate; mặc định repo root. `--config` nhận bản policy v1.1 khớp config đã khóa
ở `config/legal_parser.v1.1.json`; config v1 cũ được giữ để đối chiếu lịch sử.
Không cần dependency mới so với Stage 3. Inference WinError 4551 không chặn CLI này.

Output: `legal_units.pending.jsonl`, `source_spans.pending.jsonl`,
`legal_tree.pending.sqlite`, `coverage.jsonl`, `coverage_report.json`, `tables.jsonl`,
`quality_issues.jsonl`, `source_warning_review.jsonl`, `examples.json`, `examples.txt`,
`trees/index.json` và `trees/01.txt`… (cây dễ đọc từng văn bản),
`extraction_snapshot/`, config/schema và manifest/sidecar. Validator replay
Stage 2/3 và parser, kiểm FK/hash/offset/field roundtrip và coverage; cần cùng
code/tool version đã ghi trong manifest. Để tái tạo SQLite, chạy parse cùng input
vào run mới; không dùng lại hoặc xóa run cũ.

Chương/Mục/Điều/Khoản/Điểm chỉ được tạo khi có marker nguồn phù hợp; parent giữ
text riêng và đoạn dẫn, không sao text con. Bảng nội dung chưa phân tích và
numbering/field/revision hoặc ký hiệu xung đột được báo với locator. Coverage
ghi nhận đủ ký tự không có nghĩa toàn bộ nội dung đã được hiểu hoặc verified.
Stage 4 chưa hỗ trợ cấu trúc PDF, nhiều file cùng law_id hoặc merge bản thay
thế; từ chối trước output, không đoán thứ tự/chọn bản. Fixture tách khỏi luật thật.

Policy hiện tại v1.1 giữ quote sửa đổi đã có ranh giới làm nội dung của đơn vị
chứa nó; quote chưa đóng hoặc thay thế thiếu dấu phân cách được cách ly với issue.
Phụ lục nhận diện được giữ unprocessed; bảng chưa phân tích có locator/context.
Danh sách minh họa và heading không rõ không bị ép thành Khoản/Điều. Quy tắc có
giới hạn đã ghi trong contract, chưa chứng minh mọi định dạng Word đều đọc đúng.

Hai run cuối v1.1 là `staging/stage4-docx-005/` và `staging/stage4-docx-006/`.
Mở `trees/index.json` để chọn law_id; mở file TXT tương ứng để xem title/text riêng,
unit/parent ID và spans. `examples.txt` có trọn Điều 22 Luật 36 và Điều 6 Khoản 1
NĐ168 cùng các con; `examples.json` giữ trường và ID đầy đủ. Muốn đọc trong PowerShell:

```powershell
Get-Content -Encoding UTF8 staging/stage4-docx-005/trees/index.json
Get-Content -Encoding UTF8 staging/stage4-docx-005/examples.txt
Get-Content -Encoding UTF8 staging/stage4-docx-005/coverage_report.json
```

Các run Stage 4 v1 cũ không đổi byte; validator v1.1 kiểm code/tool hash hiện hành,
không tự chấp nhận replay v1 bằng code mới. Stage 2/3 vẫn được replay bằng code
extraction không đổi. Chưa đưa cây/extraction mới vào ứng dụng tìm kiếm prototype.

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p test_stage4.py -v
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
git diff --check
git status --short --untracked-files=all
git diff
```

Các file mới chưa được Git theo dõi sẽ chưa hiện trong `git diff` thông thường;
xem thêm danh sách untracked và nội dung file. Staging/database/cache/venv vẫn
được ignore, không đưa vào commit mới. Dừng sau Stage 4 để xem diff.

## Stage 5A: contract assessment và pilot pending

Xem [contract assessment](docs/design/data_model_v1/Stage5_Assessment_Contract.md)
và [báo cáo Stage 5A](docs/reviews/Stage5A_Verification.md). Pilot chọn rõ **40 unit**,
không đánh giá cả 4.000 unit. Nguồn/extraction/cây giữ pending. Không tải model,
OCR, sửa parser/raw, tạo chunk hoặc kích hoạt dữ liệu cho ứng dụng. Không cần
dependency mới so với Stage 3; dùng `pdfplumber` và `jsonschema` đã có.

Từ PowerShell tại repo root, dùng môi trường Stage 1 hoặc môi trường đã cài
`requirements-win-py311.lock.txt`. Các thư mục output phải **chưa tồn tại**:

```powershell
# Có mạng: lưu bản HTML/PDF chính thức, log thời điểm truy cập mới và hash.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.assessment_evidence capture --requests config/assessment_evidence.v1.json --run-dir staging/evidence-local-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.assessment_evidence validate --manifest staging/evidence-local-001/manifest.json

# Có thể dùng evidence đã lưu: staging/stage5a-evidence-001/manifest.json.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.assessment_pipeline pilot --tree-manifest staging/stage4-docx-005/manifest.json --review-manifest staging/stage4-review-pack-001/manifest.json --evidence-manifest staging/evidence-local-001/manifest.json --run-dir staging/assessment-local-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.assessment_pipeline validate --manifest staging/assessment-local-001/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.assessment_pipeline candidates --manifest staging/assessment-local-001/manifest.json --role target
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.assessment_pipeline candidates --manifest staging/assessment-local-001/manifest.json --role context
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
```

CLI trả 0 khi kiểm tra kỹ thuật đạt, trả khác 0 khi thiếu input/hash/version sai,
hồ sơ quyết định sai, hoặc output đã tồn tại. Hai lệnh `candidates` hiện trả danh
sách rỗng vì Stage 5A chưa mở cổng promote/release. Kết quả kỹ thuật không phải
xác minh pháp lý. `--raw-root` hỗ trợ kiểm snapshot trên bản raw tương ứng;
`--config`, `--findings` chọn policy pilot và các yêu cầu lấy lát bằng chứng.

Run pilot lưu `pilot.md`/`pilot.csv` (nội dung riêng, spans và đề xuất),
`evidence_review.md`, `evidence_pages/*.png` (trang ảnh NĐ168, không OCR),
`technical_review.md`, `pending_work.md`; JSONL và SQLite nằm cùng run.
`machine_proposals.jsonl` tách khỏi `review_decision_history.jsonl` (pilot chưa
có quyết định). `ddd_mapping.pending.jsonl` giữ `corpus_version=null`,
`ready_to_load=false`; không nhập trực tiếp vào schema chính thức.

Muốn tái tạo SQLite, chạy `pilot` cùng ba manifest/config/findings vào run mới.
Hash bundle bằng chứng và config được khóa vào assessment/decision; tải lại
cùng URL là một sự kiện mới, có thể đổi byte/hash hoặc phiên bản. Nếu lát text
không còn khớp, CLI sẽ thất bại; không tự thay quote hoặc suy bản lịch sử.
`--decisions FILE.json` chỉ dành cho hồ sơ rà soát thực tế do người rà soát cung
cấp đúng contract, không dùng proposal làm decision. Công cụ giữ nguyên bản
submission, chuỗi quyết định và bản chụp input; không xác thực danh tính/chữ ký
người nộp và không tự chấp thuận hồ sơ nguồn.

Artifact cụ thể và kết quả chạy nằm trong báo cáo Stage 5A. Staging/DB/venv/cache
vẫn được ignore. Dừng sau Stage 5A để xem diff và pilot.

### Điều chỉnh Stage 5A v1.1: quyết định độc lập

Contract hiện hành `assessment-pilot.v1.1` tách scope/applicability/technical.
`--decisions FILE.json` nhận `{"events":[...]}` với `dimension` và chỉ trường
của chiều đó; supersedes theo `(unit_id, dimension)`. Ghi reviewer/thời điểm,
bằng chứng/locator và lý do thật. Không cần attestation lặp payload, chữ ký số
hoặc hệ thống phân quyền mới. `proposal_relation=override` với lý do/bằng chứng
cho phép bác đề xuất máy; ngày quyết định chỉ cần đúng ràng buộc ngày/trạng thái,
không bị ép bằng ngày máy. `review_basis.jsonl` liệt kê các ID bằng chứng có thể
trích: project_requirement, source_span và finding chính thức đã lưu.

`decision_ids`, `dimension_complete` và `technical_review_status` thể hiện từng
chiều; `aggregate_status` vẫn pending, serving false. Nhóm NĐ168 A39K9 đề xuất
excluded theo đối tượng cơ sở đào tạo/trung tâm; cảnh báo d/đ vẫn tách riêng.
Không có quyết định reviewer nào được tạo cho dữ liệu thật.

Các lệnh `pilot/validate/candidates` phía trên vẫn dùng được; chọn run mới,
ví dụ `staging/assessment-v11-local-001`. Run dữ liệu v1 cũ giữ nguyên; validator
v1.1 không tự coi bundle/tool hash v1 là bản chạy mới. Xem thêm
[báo cáo điều chỉnh](docs/reviews/Stage5A_Revision_Verification.md) và
[đề xuất DOCX legacy](docs/design/data_model_v1/Legacy_DOCX_Content_Comparison_Policy_Proposal.md).
Không chạy parser PDF, chunk/index hoặc phát hành corpus trong bước này.

### Tiếp nhận PDF hẹp cho Điều 22 Luật 36

Yêu cầu tiếp theo cho phép extraction PDF Stage 3 và mapping hẹp; không xây
parser PDF tổng quát. Nguồn là hai phần PDF Công báo đã capture, tách khỏi
DOCX legacy. Xem [contract mapping](docs/design/data_model_v1/Article22_PDF_Mapping_Contract.md).
Chạy từ thư mục gốc bằng PowerShell; `--run-dir` phải chưa tồn tại:

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.article22_pdf prepare --evidence-manifest staging/stage5a-article22-evidence-001/manifest.json --tree-manifest staging/stage4-docx-005/manifest.json --comparison-manifest staging/stage5a-article22-comparison-001/manifest.json --run-dir staging/article22-pdf-local-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.article22_pdf validate --manifest staging/article22-pdf-local-001/manifest.json
# Có chủ ý trả 1: chưa đủ điều kiện corpus, không phải lỗi extraction.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.article22_pdf validate --manifest staging/article22-pdf-local-001/manifest.json --require-corpus-ready
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
```

Lệnh prepare tự chạy Stage 2 vào `source_registration/` và Stage 3 vào
`extraction/` bên trong run mới. Muốn kiểm riêng hai bundle đã sinh:

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_registry validate --manifest staging/article22-pdf-local-001/source_registration/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.extraction_pipeline validate --manifest staging/article22-pdf-local-001/extraction/manifest.json
```

Mở `review.md`/`review.csv` để xem sáu nút, nguyên văn/cha và tám spans;
`comparison.md` có toàn bộ diff, `identity_crosswalk.jsonl` giải thích ID đổi,
`source_facts.pending.jsonl` giữ log capture, `effectiveness_basis.jsonl` giữ
căn cứ. `mapping.pending.jsonl` phân biệt offsets trong field, trong extraction
và tương đối trong trace page mới. Không dùng offsets trang bằng chứng cũ làm
spans. Chạy lại cùng lệnh, đổi sang `staging/article22-pdf-local-002` để tái tạo
SQLite/JSONL; không ghi đè run trước.

`admission.prepared.sqlite` dùng schema DDD nguyên bản với dữ liệu PDF thật;
corpus, unit_assessment và chunk vẫn rỗng. Extraction và legal units còn pending.
`assessments.pending.jsonl` là bản chuẩn bị cho binding PDF mới, chưa phải
submission được CLI assessment DOCX v1.1 tiếp nhận. Cần adapter/promotion có
kiểm soát và quyết định review thực tế trước khi nhập unit_assessment.
Không tự sửa raw/parser, mở rộng pilot, tạo index hoặc kích hoạt ứng dụng.

Ba input bundle trên là artifact local bị Git ignore theo quy định. Clone
chỉ có code không có các snapshot đó thì lệnh sẽ trả lỗi thiếu input; cần khôi
phục đúng bundle/checksum từ nơi lưu của dự án. Một capture mới có timestamp/
manifest mới, phải tái tạo comparison/binding bằng quy trình tương ứng, không
sửa hash input cũ cho qua validator. Kết quả thực tế và giới hạn nằm trong
[báo cáo mapping](docs/reviews/Article22_PDF_Mapping_Verification.md).

### Review có phạm vi và nhập corpus draft Điều 22

Adapter mới giữ extraction cấp file `pending`; kết quả review các spans nằm
ở sidecar riêng. DDD/schema không đổi. Chỉ tạo **draft** khi có đủ quyết định
nguồn và ba chiều cho bốn unit; chưa chunk/index/serving. Xem
[contract draft](docs/design/data_model_v1/Article22_Corpus_Draft_Contract.md).

```powershell
# Run phải chưa tồn tại. Dùng đúng mapping PDF có sẵn, không chạy lại extraction.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.article22_draft review-pack --mapping-manifest staging/article22-pdf-004/manifest.json --run-dir staging/article22-review-local-001
# Mở review.md, decision_template.md và page21.png trong run vừa tạo.
# Tạo bản làm việc bên ngoài bundle; sau đó tự điền quyết định thực tế vào JSON.
New-Item -ItemType Directory -Path staging/article22-review-submission-local-001
Copy-Item -LiteralPath staging/article22-review-local-001/decision_template.json -Destination staging/article22-review-submission-local-001/decisions.json
# Reviewer_ref/thời gian/status đều còn null. Không đổi submitted trước khi có quyết định thật.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.article22_draft admit --review-manifest staging/article22-review-local-001/manifest.json --decisions staging/article22-review-submission-local-001/decisions.json --corpus-version traffic-20250101-v0.1.0 --run-dir staging/article22-draft-local-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.article22_draft validate --manifest staging/article22-draft-local-001/manifest.json
```

**Mã trả về:** 0 = draft/hồ sơ review tạo thành công; 2 = hồ sơ hợp lệ kỹ
thuật nhưng thiếu quyết định/đang deferred/needs_fix; 1 = lỗi input, binding,
hash, bằng chứng hoặc ràng buộc. Mẫu chưa điền trả 2, ghi đúng 13 ô thiếu,
không tạo content.sqlite/corpus.jsonl. `pending_work.md` và
`validation_report.json` chỉ rõ unit/chiều còn thiếu. Một chiều có thể hoàn
thành trước; quyết định được lưu mà không làm những chiều khác tự hoàn thành.

`decision_template.md` là phiếu dễ đọc/ghi nháp; CLI đọc JSON tương ứng.
Trong JSON điền reviewer_ref/reviewed_at thật, source_review, các ô cần kết
luận, note và evidence_refs đã thực tế xem. Suggested evidence/proposals là
gợi ý, không phải đã rà hoặc phê duyệt. Chỉ đổi record_status=submitted khi
gửi quyết định thực tế. Có thể bác proposal với lý do/bằng chứng. Applicability
khác pending_review cần effective dates phù hợp, historical_basis,
history_note và content_note. Không cần tự tính decision ID/hash.

Khi có quyết định bổ sung/thay thế, truyền
`--history staging/<run-trước>/decision_history.json`, điền supersedes đúng
event ID của cùng unit/chiều, và dùng run/corpus-version mới phù hợp. Source
review có chuỗi supersedes riêng. Bản submission và history cũ không bị sửa.

Khi đủ điều kiện, content.sqlite dùng schema DDD nguyên bản, corpus.status=draft,
6 unit/8 spans/4 assessment thật, extraction vẫn pending và serving false.
Document/Chương II chỉ là cha cấu trúc; không có assessment/target/context cho
hai nút này. Nếu chưa đủ quyết định, không tạo corpus giả chỉ để thử đường nạp.

```powershell
# Bật 6 test integration mapping đã có; toàn bộ test mới dùng fixture cô lập.
$env:VTLS_ARTICLE22_MANIFEST = 'staging/article22-pdf-004/manifest.json'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
```

Fixture adapter được ghi nhãn synthetic, dùng FIXTURE/ law ID, fixture- corpus
version và cờ --allow-fixture riêng; không dùng fixture làm bằng chứng luật thật.
Không có lệnh freeze/activate. Chi tiết lệnh/kết quả thực tế và phần còn thiếu:
[báo cáo draft](docs/reviews/Article22_Corpus_Draft_Verification.md).

### Agent review và ba chunk/context PREVIEW

Được phép tạo preview từ mapping pending, độc lập với corpus đã duyệt.
Không chạy admit hoặc ghi quyết định thay reviewer. Xem
[contract preview](docs/design/data_model_v1/Article22_Chunk_Preview_Contract.md).

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.article22_preview build --mapping-manifest staging/article22-pdf-004/manifest.json --agent-review staging/article22-preview-inspection-001/observations.json --run-dir staging/article22-preview-local-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.article22_preview validate --manifest staging/article22-preview-local-001/manifest.json
$env:VTLS_ARTICLE22_MANIFEST = 'staging/article22-pdf-004/manifest.json'
$env:VTLS_ARTICLE22_PREVIEW_MANIFEST = 'staging/article22-preview-local-001/manifest.json'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
```

Các input staging là artifact local, không có trong Git. observations.json
là hồ sơ ảnh agent thực tế đã xem, có source/image hash và thời gian agent;
không được bịa khi thiếu file. Muốn tái chạy chọn run chưa tồn tại. Tokenizer
mặc định dùng cache model/revision được khóa trong config/article22_preview.v1.json;
có thể truyền `--tokenizer-dir staging/article22-preview-001/tokenizer_assets`
để dùng lại đúng 5 asset đã sao trong run cũ. Không tải/load weights.

Mở chunks_preview.md để xem nguyên văn ba Khoản, context và text_for_search;
agent_review.md cho kết quả đối chiếu ngắn. JSONL/proofs và token_report.json
giữ IDs/spans/counts đầy đủ. Preview dùng null corpus/effective dates và
pending_review, không phải dữ liệu serving, không có unit_assessment verified.
Vượt ngưỡng token trả 2 và giữ nguyên văn, không tự truncation. Chi tiết:
[báo cáo preview](docs/reviews/Article22_Chunk_Preview_Verification.md).

### Stage 6: builder dùng chung và đầu vào encoder

Code hiện hành cho preview: `src/chunk_preview.py` tạo Khoản không có con
và context Điều cha; `src/encoder_input.py` chuẩn bị cùng một cấu hình cho
document/query và đếm đúng đầu vào encoder. `src.article22_stage6` là CLI
ví dụ hẹp gọi hai thành phần này. CLI/worker v1 được giữ nguyên để kiểm
lại code hashes của preview-001 đã seal.

Model/revision không đổi. Model card yêu cầu word segmentation; môi trường
Stage 6 dùng PyVi CPU CRF, không nạp encoder/PyTorch hoặc chạy inference
vector. Cài thêm dependency đã pin trong venv dự án:

```powershell
.\.venv-stage1\Scripts\python.exe -m pip install -r requirements-stage6.txt
# Input staging là artifact local, không có trong Git. Run đích phải chưa tồn tại.
# Dùng lại tài liệu model đã capture; không ghi ngày truy cập mới thay capture cũ.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.article22_stage6 build --baseline-manifest staging/article22-preview-001/manifest.json --model-evidence staging/article22-stage6-002/model_evidence --run-dir staging/article22-stage6-local-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.article22_stage6 validate --manifest staging/article22-stage6-local-001/manifest.json
$env:VTLS_ARTICLE22_MANIFEST = 'staging/article22-pdf-004/manifest.json'
$env:VTLS_ARTICLE22_PREVIEW_MANIFEST = 'staging/article22-preview-001/manifest.json'
$env:VTLS_STAGE6_MANIFEST = 'staging/article22-stage6-local-001/manifest.json'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
```

`chunks_preview.md` hiển thị nguyên văn, context, text_for_search và bản sao
encoder_text; `unknown_diagnostics.md` hiển thị các unknown trước/sau cùng
component và offsets được chứng minh. JSONL giữ đầy đủ token IDs/pieces,
source spans và hashes. Config khóa PyVi packages/CRF assets, tokenizer
assets/revision và policy `phobert-pyvi-input.v1`; thiếu/sai pin trả lỗi,
không tự đổi model hoặc fallback sang đếm từ.

Nguyên văn/context/search/spans không bị tiền xử lý ghi lại. Token budget
áp dụng lên encoder_text có special tokens, không truncate. Vượt budget hoặc
cấu trúc chưa hỗ trợ tạo issue/quarantine; CLI trả 2, không trả chunk như đã
sẵn sàng. Lỗi binding/input/runtime trả 1; preview thành công trả 0.

Đây vẫn là PREVIEW pending với origin=agent_review, chưa nối vào ứng dụng.
Khi tích hợp retrieval phải dùng cùng hàm/config cho query và document;
không được chỉ preprocessing một phía. Không tạo corpus/assessment verified,
embedding/BM25/Qdrant index. Chi tiết:
[contract Stage 6](docs/design/data_model_v1/Stage6_Encoder_Chunk_Preview_Contract.md),
[báo cáo kiểm tra Stage 6](docs/reviews/Stage6_Encoder_Chunk_Preview_Verification.md).

### Stage 6 tiếp: Điểm thuộc Khoản và context hai cấp

Builder mới `src/chunk_preview_v2.py`, policy `leaf-clause-point-context.v1`,
hỗ trợ Khoản lá và Điểm lá. Context của Điểm là title Điều, đoạn dẫn riêng
Điều nếu có, rồi đoạn dẫn riêng Khoản cha; không sao nội dung anh em hoặc
tự mở rộng dẫn chiếu. Có issue nguồn/parser ảnh hưởng thì chặn, không đoán.
Builder/CLI v1 giữ nguyên byte để kiểm lại các run đã seal.

```powershell
# Dùng dependency Stage 6 đã cài; encoder/model/config không đổi.
# Run đích phải chưa tồn tại; các input staging phải được khôi phục từ artifact thật.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.points_preview build --tree-manifest staging/stage4-docx-005/manifest.json --article22-manifest staging/article22-stage6-002/manifest.json --run-dir staging/stage6-points-local-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.points_preview validate --manifest staging/stage6-points-local-001/manifest.json
$env:VTLS_ARTICLE22_MANIFEST = 'staging/article22-pdf-004/manifest.json'
$env:VTLS_ARTICLE22_PREVIEW_MANIFEST = 'staging/article22-preview-001/manifest.json'
$env:VTLS_STAGE6_MANIFEST = 'staging/article22-stage6-002/manifest.json'
$env:VTLS_POINTS_MANIFEST = 'staging/stage6-points-local-001/manifest.json'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
```

`config/stage6_points.v1.json` khóa đúng năm Điểm a–đ của Điều 6 Khoản 1
NĐ168, các input manifests và encoder config cũ. Raw được sao nguyên byte
vào run mới cùng Source Inventory để upstream validator replay độc lập;
không sửa raw hoặc tạo hồ sơ document/source đã xác minh.

Mở chunks_preview.md để xem cả nguyên văn, context theo Điều/Khoản, nguồn,
text_for_search/encoder_text, token/unknown và trạng thái từng candidate.
chunks.preview.jsonl/contexts.preview.jsonl chỉ chứa candidate dưới budget;
quarantined.preview.jsonl giữ đủ candidate/context vượt ngưỡng, encoder input
giữ theo chunk_id. issues.jsonl/dependency_checks.jsonl ghi phần bị chặn.

Trong article22_regression/ có ba chunk Điều 22 dựng bằng policy mới;
article22_comparison.json chỉ rõ ID đổi vì chunk_policy_version, nội dung/
context/search/hash không đổi. Snapshot/run/ID cũ được giữ nguyên.

Exit 0 = mọi candidate preview đạt; 2 = có issue/quarantine; 1 = lỗi input,
binding/runtime. Không truncate hoặc bỏ context để pass. Dữ liệu vẫn pending,
origin=agent_review; source_url của DOCX là candidate inventory, không phải
provenance đã xác minh. Không tạo reviewer event, corpus verified, embedding
hoặc index. Chi tiết:
[contract Điểm](docs/design/data_model_v1/Stage6_Point_Context_Contract.md),
[báo cáo Điểm](docs/reviews/Stage6_Point_Context_Verification.md).

### Stage 6: khảo sát khả năng chunking trên bốn cây DOCX

`src.coverage_survey` gọi builder Khoản/Điểm lá hiện hành cho toàn bộ bốn
cây DOCX, cùng logic source/dependency và encoder preprocessing đã chốt.
Không trộn PDF Điều 22, đổi policy/model/budget 256 hoặc truncate. Chỉ dùng
tokenizer/PyVi CPU, không encoder inference. Cần các artifact local thật
Stage4-005 và assessment v1.1 revision-pilot-003; staging không có trong Git.

```powershell
# Dùng môi trường/dependency Stage 6 đã cài. Run đích phải chưa tồn tại.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.coverage_survey build --tree-manifest staging/stage4-docx-005/manifest.json --assessment-manifest staging/stage5a-revision-pilot-003/manifest.json --run-dir staging/stage6-coverage-local-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.coverage_survey validate --manifest staging/stage6-coverage-local-001/manifest.json
# Nếu tokenizer không còn ở cache mặc định, thêm vào lệnh build:
# --tokenizer-dir staging/stage6-points-002/tokenizer_assets
$env:VTLS_ARTICLE22_MANIFEST = 'staging/article22-pdf-004/manifest.json'
$env:VTLS_ARTICLE22_PREVIEW_MANIFEST = 'staging/article22-preview-001/manifest.json'
$env:VTLS_STAGE6_MANIFEST = 'staging/article22-stage6-002/manifest.json'
$env:VTLS_POINTS_MANIFEST = 'staging/stage6-points-002/manifest.json'
$env:VTLS_COVERAGE_MANIFEST = 'staging/stage6-coverage-local-001/manifest.json'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p test_coverage_survey.py -v
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
```

Mở `coverage_report.md` để xem số liệu từng văn bản; `samples.md` có citation,
reason, token và đường dẫn mẫu. `unit_coverage.jsonl`/CSV ghi đủ 4.000 unit,
phân biệt context-only, preview, bị chặn, vượt budget và chưa hỗ trợ.
`source_gaps.jsonl` liệt kê parser/coverage/table riêng, có thể trùng vùng
giữa các lớp, không tạo unit giả. Preview/context/encoder/quarantine nằm ở
`preview/`. Mẫu số tỷ lệ là các Khoản/Điểm lá builder hỗ trợ; token quantile
chỉ trên candidate được đo, không phải context-only hoặc bị chặn sớm.

Scope nối từ hồ sơ assessment đúng hash cây/unit, không biến proposal thành
quyết định. Không có assessment mới, nguồn/extraction/cây vẫn pending,
origin=agent_review, corpus_version=null, release_eligible=false. Tỷ lệ kỹ
thuật không chứng minh độ phủ nghiệp vụ, toàn nguồn hoặc hiệu lực.

Validator replay toàn bộ bốn cây bằng builder/tokenizer thật, so output,
summary và báo cáo. **Exit 0 của survey** nghĩa khảo sát hoàn tất không có
lỗi thực thi, vẫn có thể có target bị chặn/vượt budget/chưa hỗ trợ; exit 2
có candidate lỗi thực thi; exit 1 lỗi input/binding hoặc tiến trình. Xem
`validation_report.json` và bảng trạng thái, không suy mọi candidate pass.
Chưa triển khai các ưu tiên được đề xuất, tạo corpus, embedding/index hoặc
kích hoạt ứng dụng. Chi tiết:
[contract khảo sát](docs/design/data_model_v1/Stage6_Coverage_Survey_Contract.md),
[báo cáo kiểm chứng](docs/reviews/Stage6_Coverage_Survey_Verification.md).

### Mở rộng proposal scope từ coverage Stage 6

`src.scope_survey` dùng cây DOCX/coverage đã có, giữ assessment v1.1 và
schema DDD. `config/scope_curation.v1.json` ghi các unit/hash/quote, đối tượng
và lý do agent đã đọc; runtime không phân loại bằng keyword hoặc truyền
nhãn cha xuống con. Các unit chưa xem giữ pending, method=unassessed_inventory.
Không coi mọi unit trong CSV là đã đánh giá ngữ nghĩa.

```powershell
# Input staging là artifact local thật; dùng môi trường/dependency Stage 6.
# Cả build và validate replay coverage/tokenizer offline; không inference.
# Run đích phải chưa tồn tại và không lồng trong input đã seal.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.scope_survey build --coverage-manifest staging/stage6-coverage-001/manifest.json --run-dir staging/stage5-scope-survey-local-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.scope_survey validate --manifest staging/stage5-scope-survey-local-001/manifest.json
$env:VTLS_ARTICLE22_MANIFEST = 'staging/article22-pdf-004/manifest.json'
$env:VTLS_ARTICLE22_PREVIEW_MANIFEST = 'staging/article22-preview-001/manifest.json'
$env:VTLS_STAGE6_MANIFEST = 'staging/article22-stage6-002/manifest.json'
$env:VTLS_POINTS_MANIFEST = 'staging/stage6-points-002/manifest.json'
$env:VTLS_COVERAGE_MANIFEST = 'staging/stage6-coverage-001/manifest.json'
$env:VTLS_SCOPE_MANIFEST = 'staging/stage5-scope-survey-local-001/manifest.json'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
```

Mở scope_report.md và scope_proposals.csv để lọc theo law/citation/scope/
coverage/reason; JSONL giữ binding, source spans và evidence_refs. Các nút
Document/Chương/Mục ở structural_roles.jsonl. Supporting chỉ dùng fields
cho target cụ thể trong context_dependencies.jsonl; cha mixed pending.
priority_cases.md trình bày các ca cũ, candidate quá dài và bất đồng với
proposal trước. Lịch sử và toàn bộ bằng chứng trước giữ nguyên trong
coverage_snapshot/. Token/unknown lấy từ coverage thật, chưa đo giữ null.

Proposal included không phải corpus duyệt, tỷ lệ không phải Recall.
pending ở proposal ánh xạ null trong assessment v1.1; scope_status và
decision_ids vẫn null. Nguồn/hiệu lực là chiều độc lập, chưa có reviewer
event mới hoặc corpus/index. Exit 0 chỉ là validator hồ sơ kỹ thuật đạt;
exit 1 lỗi input/binding/evidence/replay. Không có lệnh approve/admit.
Chi tiết: [contract scope survey](docs/design/data_model_v1/Stage5_Scope_Survey_Contract.md),
[báo cáo kiểm chứng scope](docs/reviews/Stage5_Scope_Survey_Verification.md).

### Pilot refinement: field context và chất lượng proposal

`src.pilot_refinement` chỉ rà lại 107 target included của scope-survey-001,
gồm 35 target dùng 42 dependency từ 9 field cha pending. Sidecar đề xuất
use/needs_more_review/do_not_use cho field cụ thể; scope cha giữ nguyên.
Proposal mới có đối tượng, hành vi/quyền/nghĩa vụ, use case và giới hạn theo
từng unit; chưa kết luận thì pending. Không mở rộng phân loại corpus.

```powershell
# Giữ môi trường/dependency Stage 6; input staging thật cần có tại máy.
# Run đích chưa tồn tại, không lồng trong input đã seal.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.pilot_refinement build --scope-manifest staging/stage5-scope-survey-001/manifest.json --run-dir staging/stage5-pilot-refinement-local-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.pilot_refinement validate --manifest staging/stage5-pilot-refinement-local-001/manifest.json
$env:VTLS_ARTICLE22_MANIFEST = 'staging/article22-pdf-004/manifest.json'
$env:VTLS_ARTICLE22_PREVIEW_MANIFEST = 'staging/article22-preview-001/manifest.json'
$env:VTLS_STAGE6_MANIFEST = 'staging/article22-stage6-002/manifest.json'
$env:VTLS_POINTS_MANIFEST = 'staging/stage6-points-002/manifest.json'
$env:VTLS_COVERAGE_MANIFEST = 'staging/stage6-coverage-001/manifest.json'
$env:VTLS_SCOPE_MANIFEST = 'staging/stage5-scope-survey-001/manifest.json'
$env:VTLS_REFINEMENT_MANIFEST = 'staging/stage5-pilot-refinement-local-001/manifest.json'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
```

Build/validate replay scope/coverage và builder hiện hành, không thay config
encoder. Token cũ lấy đúng evidence đã replay; riêng unknown chạy tokenizer
thật lại. Không encoder inference, weights, embedding hoặc index mới.
Exit 0 là nhất quán hồ sơ kỹ thuật, exit 1 là lỗi; không phải xác minh pháp lý.

Mở pilot_refinement_report.md, pilot_candidates.csv và
priority_cases_fulltext.md (trọn target/context của ca dài, unknown và scope
cần xem). JSONL giữ binding, history, evidence/locators; context_field_reviews
chỉ cho target/field cụ thể. unknown_diagnostics.md/JSON tách encoder/search/
field/extraction offsets và ghi rõ điều kiện mapping, không đoán inverse.
Nguyên văn/spans/chunk ID/hash và quarantine cũ giữ nguyên; field chưa phù
hợp không bị xóa để pass budget. Nguồn/hiệu lực/reviewer còn pending/null,
không thêm cổng duyệt hoặc tạo trạng thái ready. Chi tiết:
[contract refinement](docs/design/data_model_v1/Stage5_Pilot_Refinement_Contract.md),
[báo cáo kiểm chứng](docs/reviews/Stage5_Pilot_Refinement_Verification.md).
