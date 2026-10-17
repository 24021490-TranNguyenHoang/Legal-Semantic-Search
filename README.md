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
