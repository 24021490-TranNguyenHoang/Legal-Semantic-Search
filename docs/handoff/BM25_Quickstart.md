# BM25 experimental — Quickstart bàn giao

Tập được bàn giao: `vtls-coverage-experimental.v1` và
`vtls-bm25s-lucene.v1`, snapshot tham chiếu **2025-01-01**. 3.077 chunk,
5.371 context; tất cả review nguồn/hiệu lực còn pending, chưa serving.
Điểm BM25 là điểm xếp hạng, không phải xác suất hoặc độ tin cậy pháp lý.

## 1. Nhận source và artifact

**Chưa có URL chia sẻ** artifact. Nhận bốn file sau từ người bàn giao;
không thay URL bằng đường dẫn tải giả:

- `bm25-baseline-v1-001.zip` và `bm25-baseline-v1-001.zip.sha256`.
- `bm25-handoff-working-tree.patch` và file `.patch.sha256` tương ứng.

Vị trí hiện tại ở máy người bàn giao: ZIP/SHA trong `staging/`;
patch/SHA trong `staging/bm25-handoff-001/`. ZIP 33.424.920 byte, chứa hai
root `bm25-baseline-v1-001/` và `retrieval-dataset-v1-001/`. Index đã chứa
dataset riêng trong `bm25-baseline-v1-001/dataset/`; bản dataset standalone
trong ZIP là bản trùng nguyên byte để tiện dùng chung/evaluation, không
phải staging history. Không có venv/cache/database/model weights.

Source base đã kiểm: `eec0d0142f55e7eecaf6b936504c8c26f82fb2af`.
Thay đổi loader/docs/tests bàn giao **chưa commit/push**; không giả định
clone remote đã có chúng. Patch bên trên áp lên đúng commit này. Người
bàn giao phải cung cấp commit đó qua Git nếu remote chưa có object.

```powershell
git clone -c core.autocrlf=false https://github.com/24021490-TranNguyenHoang/Legal-Semantic-Search.git
Set-Location Legal-Semantic-Search
git checkout eec0d0142f55e7eecaf6b936504c8c26f82fb2af
if ($LASTEXITCODE -ne 0) { throw 'Chưa có commit source; liên hệ người bàn giao.' }
New-Item -ItemType Directory -Path staging/downloads -Force | Out-Null
# Chép bốn file đã nhận vào staging/downloads trước khi chạy phần tiếp.
```

`core.autocrlf=false` bảo toàn byte LF dùng trong source hash của bundle.
Không normalize/nới hash validator để vượt lỗi CRLF. Mọi lệnh tiếp theo
chạy từ root clone; đường dẫn không phụ thuộc máy người tạo.

## 2. Kiểm SHA-256 và áp patch

```powershell
$zipPath = '.\staging\downloads\bm25-baseline-v1-001.zip'
$patchPath = '.\staging\downloads\bm25-handoff-working-tree.patch'
foreach ($artifactPath in @($zipPath, $patchPath)) {
    $expectedHash = ((Get-Content -LiteralPath ($artifactPath + '.sha256') -Raw).Trim() -split '\s+')[0]
    $actualHash = (Get-FileHash -LiteralPath $artifactPath -Algorithm SHA256).Hash
    if ($actualHash -ne $expectedHash) { throw "SHA-256 sai: $artifactPath" }
}
$zipHash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash
if ($zipHash -ne '8678cd66620cbacfae7443e9e0774ac36f8294aeb6edceebf1e06cfaa789d03e') {
    throw 'ZIP không phải bản bàn giao này.'
}
git apply --check $patchPath
if ($LASTEXITCODE -ne 0) { throw 'Patch không khớp source; không áp cưỡng bức.' }
git apply $patchPath
if ($LASTEXITCODE -ne 0) { throw 'Áp patch thất bại.' }
```

Patch làm working tree có thay đổi là có chủ đích; không tự commit.
Nếu maintainer đã commit bộ bàn giao sau này, dùng đúng commit được cung
cấp thay cho bước áp patch; không áp patch lặp lên file đã cập nhật.

## 3. Môi trường tối thiểu

Windows PowerShell, CPython 3.11 64-bit (thực thử 3.11.9). Không cần kích
hoạt venv hoặc đổi ExecutionPolicy:

```powershell
python --version
python -c "import sys; assert sys.version_info[:2] == (3, 11), 'Can CPython 3.11 tren PATH'"
if ($LASTEXITCODE -ne 0) { throw 'Chọn đúng Python 3.11 trước khi tạo venv.' }
python -m venv .venv-bm25
if ($LASTEXITCODE -ne 0) { throw 'Tạo venv thất bại.' }
.\.venv-bm25\Scripts\python.exe -m pip install --disable-pip-version-check -r requirements-bm25.txt
if ($LASTEXITCODE -ne 0) { throw 'Cài dependency thất bại.' }
.\.venv-bm25\Scripts\python.exe -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency không nhất quán.' }
```

| Công việc | Dependency ngoài stdlib | Repository/artifact cần có |
|---|---|---|
| Load/search | bm25s 0.3.13, NumPy 2.4.6, SciPy 1.17.1 | Source/helper/config của repo và toàn thư mục index |
| Validate index + replay dataset đã gói | Cùng ba package trên; không cần tokenizer encoder | Thêm các module pipeline/builder của repo, config selection và nguồn/evidence trong dataset đã gói |
| Build index từ dataset đã gói | Cùng ba package trên, chạy full cached validator | Dataset manifest và run đích mới; không cần staging coverage gốc |
| Dựng lại dataset từ upstream coverage | Môi trường upstream, gồm jsonschema và requirements-stage6.txt (PyVi/CRF/Transformers…); reader PDF nếu đường upstream dùng PDF | Cần coverage/scope/refinement snapshots gốc; không thuộc gói Quickstart này |

Không cài `requirements.txt` chung chỉ để chạy BM25: nó còn có Torch,
SentenceTransformers, UI/Qdrant không cần cho bàn giao này. Validate đã gói
dùng token evidence cache đúng hash, không chạy tokenizer encoder/weights.

Search hiện import các module nội bộ: `bm25_baseline`, `bm25_tokenizer`,
`config`, `source_contracts`, `experimental_dataset`, `retrieval_dataset`,
`chunk_preview`, `chunk_preview_v2`, `ingestion.legal_tree` dưới `src/`.
Full validate còn import `coverage_survey`, `encoder_input`, `preview_tokens`,
`assessment_*`, `legal_parser`, `extraction_pipeline`, `article22_*`,
`content_comparison`, `source_registry`, `pipeline_cli` và các helper ingestion.
Giữ nguyên `src/`, `config/`, `schemas/` của clone; không chép riêng một CLI.
Các module này không đồng nghĩa việc chạy các stage tương ứng.

## 4. Giải nén, validate, query

```powershell
if ((Test-Path .\staging\bm25-baseline-v1-001) -or (Test-Path .\staging\retrieval-dataset-v1-001)) {
    throw 'Run đích đã tồn tại; dùng clone sạch, không ghi đè artifact.'
}
Expand-Archive -LiteralPath $zipPath -DestinationPath .\staging
$manifest = 'staging/bm25-baseline-v1-001/index_manifest.json'
.\.venv-bm25\Scripts\python.exe -X utf8 -B -m src.bm25_baseline validate --index-manifest $manifest
if ($LASTEXITCODE -ne 0) { throw 'Validate thất bại; chưa chạy query.' }
.\.venv-bm25\Scripts\python.exe -X utf8 -B -m src.bm25_baseline search --index-manifest $manifest --query 'Nhường đường tại vòng xuyến' --top-k 5
if ($LASTEXITCODE -ne 0) { throw 'Search thất bại.' }
```

Validate phải trả `technical_valid=true`, `documents=3077`,
`save_load_replay=true`, `release_eligible=false`. Nó đối chiếu source/spans/
dataset và tái tạo matrix **trong RAM** để so với saved arrays; không build
lại hoặc ghi index/dataset. Không sửa manifest/hash nếu validate thất bại.

Query mẫu đứng đầu Luật 36 Điều 22 khoản 3, score khoảng 10.5966 trong bản
đã thử; không dùng ví dụ này như qrels/chứng minh retrieval đạt yêu cầu.
OOV `zzzxxyybm25oov` trả `results=[]`. Query rỗng/chỉ dấu câu hoặc top_k
không dương báo lỗi. Không lấp danh sách bằng điểm 0, không truncate.

JSON có `timings_ms.load` (hash/read/import/kiểm mapping/load arrays) và
`timings_ms.search` (tokenize/score/rank/ghép kết quả), loại Python startup.
Chạy CLI mới mỗi query sẽ load lại; `search_loaded()` tái dùng index trong
process nếu tích hợp sau này. Không so thời gian toàn lệnh với riêng search,
không kết luận p95 từ query mẫu.

## 5. Runtime và lỗi thường gặp

- Python khác **patch** trong cùng CPython 3.11: cho phép nếu Unicode,
  dependency pins và source BM25S khớp. Có cảnh báo `PYTHON_PATCH_DIFFERS`
  và môi trường tạo/chạy trong JSON `runtime_compatibility`.
- Python khác minor/implementation, Unicode khác 14.0.0, dependency hoặc
  mã BM25S khác: từ chối có lý do. Dùng đúng môi trường; chưa kiểm máy/OS
  khác và chưa thực chạy patch khác. Test patch khác chỉ là mô phỏng policy.
- `Index source binding mismatch`/`Dataset validator/builder version changed`:
  kiểm đúng commit + patch và LF; tokenizer/thuật toán không được sửa.
  Loader chỉ nhận binding hiện hành hoặc đúng fingerprint loader v1 gốc;
  không chấp nhận source bất kỳ.
- `File inventory/hash/size mismatch`, manifest hash hoặc mapping sai:
  lấy lại nguyên ZIP, kiểm SHA, giải nén mới; không sửa hash để pass.
- `No module named src`: chạy từ root clone. `No module named ...` hoặc
  dependency mismatch: dùng đúng executable trong `.venv-bm25` và pip check.
- Trên máy thử, `python --version` là 3.11.9 nhưng `py -3.11` báo
  `No installed Python found!`; Quickstart dùng `python` đã kiểm phiên bản.
  Nếu PATH khác, chọn executable CPython 3.11 thực tế hoặc cài đúng bản;
  không dùng Python minor khác để né lỗi.
- Pip không tìm thấy version/network bị chặn: kiểm index/network được phép;
  không tự thay version hoặc engine. Lần thử sandbox hạn chế đã thất bại;
  cài được phép vào venv sạch đã thành công.
- Console tiếng Việt/JSON: dùng `-X utf8`; chuyển hướng `>` ở Windows
  PowerShell có thể ghi UTF-16. Khi cần lưu UTF-8, dùng môi trường output
  encoding phù hợp; không sửa dữ liệu luật vì lỗi hiển thị.

Nguồn legacy, scope proposal, extraction/tree và applicability chưa được
reviewer xác minh. Tập còn cả 64 proposal excluded và 2.919 pending, không
phải tập target nghiệp vụ đã duyệt. Còi ban đêm/điểm GPLX còn failure case;
chưa có qrels/Recall/MRR/nDCG. Chưa tạo Dense/embedding/Qdrant hoặc tích hợp
ứng dụng. Xem [STATUS](../progress/STATUS.md) trước khi báo cáo tiến độ.
