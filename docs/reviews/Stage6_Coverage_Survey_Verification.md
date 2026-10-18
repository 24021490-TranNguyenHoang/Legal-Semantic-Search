# Stage 6 — khảo sát khả năng chunking bốn cây DOCX

## Kết quả thực tế

Run **`staging/stage6-coverage-001/`**, nguồn cây DOCX
**`staging/stage4-docx-005/`**. Snapshot **2025-01-01**,
origin=agent_review, preview_only=true, release_eligible=false.
Không trộn mapping PDF Điều 22 vào khảo sát. Manifest khảo sát SHA-256:
`7853192d9be1fac05befe48bbe02d488e2afa8129631474830ca359e2c0d94af`.

Git ban đầu sạch, HEAD `238e752`. Đã đọc AGENTS, DDD, BRD, các contract
Stage6, code builder/encoder/CLI và config/test thực tế. Validator Stage4
xác nhận 4 văn bản, 4.000 unit, 4.149 spans, 10 parser issues và 13
extraction warnings; assessment v1.1 revision-pilot-003 cũng hợp lệ kỹ thuật.
Các validator này không xác nhận pháp lý. Không sửa parser, builder,
encoder, policy/model/budget hoặc schema DDD.

| Văn bản | Tổng unit | Context-only | Target Khoản/Điểm lá | Preview | Chặn source/context | Vượt 256 | Điều lá chưa hỗ trợ |
|---|---:|---:|---:|---:|---:|---:|---:|
| 165/2024/NĐ-CP | 846 | 229 | 613 | 607 | 0 | 6 | 4 |
| 168/2024/NĐ-CP | 1.304 | 258 | 1.044 | 1.021 | 10 | 13 | 2 |
| 35/2024/QH15 | 868 | 198 | 668 | 664 | 3 | 1 | 2 |
| 36/2024/QH15 | 982 | 192 | 789 | 789 | 0 | 0 | 1 |
| Tổng | 4.000 | 877 | 3.114 | 3.081 | 13 | 20 | 9 |

Không có candidate lỗi thực thi. Phân hoạch:
**877 + 3.081 + 13 + 20 + 9 = 4.000**, không đếm trùng.
Mẫu số hỗ trợ gồm **916 Khoản lá + 2.198 Điểm lá**; có 3.123 candidate nếu
tính cả 9 Điều lá chưa hỗ trợ. Tỷ lệ hỗ trợ kỹ thuật **3.081/3.114 = 98,94%**,
không phải độ phủ nghiệp vụ hoặc toàn nguồn. Document/Chương/Mục và cha có
con không phải target bị thất bại; không tạo target từ đoạn dẫn mức phạt.

Toàn cây gồm 4 document, 28 Chương, 22 Mục, 300 Điều, 1.448 Khoản và
2.198 Điểm. Bảng chi tiết theo loại/văn bản, tỷ lệ từng văn bản và primary
reason ở coverage_report.md/coverage_summary.json. Thứ tự ưu tiên primary
reason đã công bố trong contract; mỗi unit chỉ có một trạng thái cuối,
mọi builder issue/impact trả về được giữ riêng.

## Token trên đầu vào encoder thật

| Văn bản | Mẫu đo | p50 | p95 | Max | 257–384 | 385–512 | >512 | Unknown | Candidate có unknown |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 165/2024/NĐ-CP | 613 | 108 | 195 | 348 | 6 | 0 | 0 | 7 | 6 |
| 168/2024/NĐ-CP | 1.034 | 129 | 216 | 302 | 13 | 0 | 0 | 0 | 0 |
| 35/2024/QH15 | 665 | 71 | 120 | 275 | 1 | 0 | 0 | 3 | 3 |
| 36/2024/QH15 | 789 | 75 | 123 | 169 | 0 | 0 | 0 | 14 | 12 |
| Tổng | 3.101 | 97 | 187 | 348 | 20 | 0 | 0 | 24 | 21 |

Nearest-rank trên nhóm được đo, gồm cả candidate vượt budget. 13 target bị
chặn trước encoder, 9 Điều chưa hỗ trợ và context-only không được gán token
0 hoặc đếm bằng text_original. 20 candidate quá dài giữ nguyên toàn bộ
target/context trong quarantine. Không truncate, bỏ context hoặc tăng ngưỡng.

Dùng đúng `leaf-clause-point-context.v1`, `phobert-pyvi-input.v1`, model
`bkai-foundation-models/vietnamese-bi-encoder`, revision
`84f9d9ada0d1a3c37557398b9ae9fcedcdf40be0`. Giới hạn preview/model hiện cùng
256 gồm hai special tokens; tokenizer.model_max_length sentinel không được
dùng để tăng ngưỡng. PyVi CPU/CRF và tokenizer asset/package hashes không đổi.
Worker offline, không import encoder/PyTorch, không tải weights hoặc tạo vector.

Đã đối chiếu cả 3.101 encoder rows: count đúng len(token_ids) sau tiền xử lý,
hai special tokens, unknown count nhất quán, encoder_text/hash đúng,
truncation=false. Unknown là số đo, chưa chẩn đoán nguyên nhân mới trong lượt
này; không suy encoding hỏng hoặc chất lượng retrieval từ con số này.

Đối chiếu năm Điểm Điều 6 Khoản 1 NĐ168 với pilot stage6-points-002:
chunk_id, nguyên văn/context/search/content hash và token/unknown giữ nguyên.
Theo a/b/c/d/đ: **239/132/170/138/151 token, unknown đều 0**. Source proofs
có prefix đường dẫn của run mới, không phải đổi identity payload.
Chi tiết ở encoder_and_pilot_crosscheck.json trong thư mục verification.

## Chặn kỹ thuật và source gaps

13 target bị PARSER_OR_EXTRACTION_ISSUE_IMPACT:

- NĐ168: Điểm a/b/c Điều 16 Khoản 2; Điểm a/b/c/đ Điều 39 Khoản 9;
  Điểm a/b/c Điều 40 Khoản 3. Giữ conflict/sequence gap/ambiguous/suspended
  vùng nguồn và quan hệ ảnh hưởng, không khôi phục ký hiệu bằng suy đoán.
- Luật 35: Khoản 1/2 Điều 84 liên quan hai bảng chưa parse; Khoản 2 Điều 86
  liên quan source content chưa giải mã/visual warning.

Không có trường hợp thiếu context/spans/quan hệ thuần túy trong dữ liệu
thật được khảo sát; samples.md ghi rõ nhóm này rỗng. Fixture kiểm riêng các
nhánh lỗi; không trình bày fixture như ví dụ luật thật.

source_gaps.jsonl có **33 record**: 10 parser issue, 13 coverage record,
10 bảng. Có thể trùng vùng giữa các lớp, không phải 33 lỗi độc lập hay unit
pháp lý mới. Trong 10 bảng có 8 supporting/non-body, 2 unprocessed. Các
warning Stage3 vẫn đủ trong input snapshot/inventory issue, không thêm
chúng thành unit giả. Coverage chỉ đo được trên cây đã parse; chưa chứng
minh mọi vùng sửa đổi/phụ lục/bảng hoặc nội dung cách ly đã được bao phủ.

## Scope và blocker nguồn/pháp lý

Chỉ nối hồ sơ đúng checksum cây và unit từ
`staging/stage5a-revision-pilot-003/`: **0 quyết định scope**, 34 unit có
proposal scope, 3.966 unit chưa đánh giá/kết luận scope. Có 40 proposal
records, trong đó 6 scope_candidate=null; 34 proposal có kết luận gồm 15
included, 11 supporting, 8 excluded. Không tạo assessment mới hoặc mượn
decision của PDF Điều 22.

BRD §3.1/§3.3 ưu tiên nội dung áp dụng trực tiếp cho người tham gia giao
thông; không suy quy hoạch/hạ tầng hoặc quản lý cơ sở tự thuộc target.
Không coi cả bốn văn bản là included bằng keyword hay tên luật.

Blocker nguồn/provenance DOCX, extraction/cây, scope/hiệu lực còn pending;
chưa tạo corpus hoặc quyết định reviewer. Lỗi thực thi khảo sát là 0 nhưng
không làm blocker pháp lý biến mất. source_url là candidate trong inventory,
không phải chứng cứ lịch sử tải. Không triển khai dẫn chiếu ngoài cây cha,
parser repair, tách dài, target Điều hoặc index trong lượt này.

## Tối đa ba ưu tiên — chưa triển khai

| Đề xuất | Số candidate liên quan, cận trên chưa chứng minh | Scope hiện có | Rủi ro và điều kiện trước embedding |
|---|---:|---|---|
| Nghiên cứu segment có spans, giữ đủ context | 20 | Cả 20 chưa đánh giá scope | Có thể mất điều kiện/phủ định, context tự nó có thể dài; chỉ làm cho vùng chọn sau assessment, không tăng budget model |
| Đối chiếu vùng parser/context/nguồn bị chặn | 13 | 3 proposal included, 1 supporting, 4 excluded, 5 chưa kết luận; chưa có quyết định | Không đoán ký hiệu/nội dung thiếu; cần xử lý vùng ảnh hưởng trước khi embedding các target thực sự chọn |
| Thiết kế hỗ trợ Điều lá sau khi xác định scope | 9 | Cả 9 chưa đánh giá scope | Phải giữ trọn điều kiện/cấu trúc và source proofs; cần nếu các Điều này được chọn làm target |

Các con số không hứa mọi candidate đều phục hồi được hoặc đều cần đưa vào
corpus. Không triển khai các đề xuất này trong lượt khảo sát.

## Lệnh tái chạy

```powershell
# Kiểm lại artifact có sẵn; validator replay toàn bộ bốn cây và tokenizer thật.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.coverage_survey validate --manifest staging/stage6-coverage-001/manifest.json
# Tạo run mới, không ghi đè 001. Input staging phải có thật, dependency Stage6 đã cài.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.coverage_survey build --tree-manifest staging/stage4-docx-005/manifest.json --assessment-manifest staging/stage5a-revision-pilot-003/manifest.json --run-dir staging/stage6-coverage-local-001 --tokenizer-dir staging/stage6-coverage-001/tokenizer_assets
$env:VTLS_ARTICLE22_MANIFEST = 'staging/article22-pdf-004/manifest.json'
$env:VTLS_ARTICLE22_PREVIEW_MANIFEST = 'staging/article22-preview-001/manifest.json'
$env:VTLS_STAGE6_MANIFEST = 'staging/article22-stage6-002/manifest.json'
$env:VTLS_POINTS_MANIFEST = 'staging/stage6-points-002/manifest.json'
$env:VTLS_COVERAGE_MANIFEST = 'staging/stage6-coverage-001/manifest.json'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
git diff --check
git diff --cached --stat
```

Các lệnh upstream đã chạy trước build:

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.legal_parser validate --manifest staging/stage4-docx-005/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.assessment_pipeline validate --manifest staging/stage5a-revision-pilot-003/manifest.json
```

Build tạo run_report.status=success, survey_completed=true và không có
execution error. Lệnh build đầu dùng PowerShell `2>&1 | Tee-Object` bị
PowerShell bọc dòng progress stderr thành NativeCommandError và wrapper
trả 1; không lấy mã wrapper đó làm bằng chứng CLI thành công. Lần validate
sau thu mã subprocess trực tiếp và so toàn bộ artifact bằng replay.
Log và kết quả kiểm thử độc lập nằm tại
`staging/stage6-coverage-verification-001/`.

Validator CLI độc lập **exit 0**, 270,172 giây, technical_valid=true,
survey_completed=true, execution_error_candidates=0. Đã replay tất cả
3.123 candidate, gồm 3.101 input encoder được đo và 22 candidate dừng trước
encoder (13 parser impact + 9 unsupported). Không chỉ kiểm mẫu hoặc tin
validation_report đã lưu. Log validate.log và validate_result.json giữ mã
trả về thật. all_candidates_successful=false phản ánh đúng phần bị chặn.

Full suite: **184/184 tests đạt, không skipped**, 147,610 giây trong
unittest (subprocess 148,0 giây), exit 0. Gồm 171 hồi quy và 13 kiểm thử
survey mới: phân hoạch/mẫu số, nhiều issue một trạng thái, context-only,
source gap không tạo unit, pending không thành lỗi chunking, quarantine và
token binding, cô lập runtime failure, batching so đúng builder, binding
scope, percentile/unknown/CSV và duplicate accounting. Hai test integration
đọc toàn cây thật và đo lại các mẫu theo từng trạng thái/văn bản bằng
builder/tokenizer thật. Full CLI validator riêng replay tất cả candidate.

Hồi quy bao gồm Stage1–5A, PDF mapping, ba preview Điều 22 và pilot Điểm.
Fixture synthetic được giữ tách biệt; test BM25 cũ chỉ tạo artifact fixture
tạm trong staging, không xây chỉ mục cho dữ liệu thật hoặc dùng Qdrant.
Các dòng ERROR trong negative tests là lỗi được mong đợi, không phải test
thất bại. Lần focused trước khi có artifact: 11 test fixture đạt, 2 test
integration skip có lý do; full suite cuối đã cấp đủ năm biến VTLS và không
còn skip.

CLI thử manifest thiếu trả **1**, không tạo thư mục run mới; xem
missing_input_result.json. Kiểm 3.101 encoder rows và năm Điểm pilot ở
encoder_and_pilot_crosscheck.json. Preservation xác nhận **9.123 file
artifact cũ** không mất/đổi byte, không có file mới ở raw/processed/Qdrant
hoặc 60 thư mục staging cũ. Trong 105 file workspace ban đầu, chỉ README.md
và AGENTS.md thay đổi; toàn bộ code/config/schema/test cũ nguyên byte.
SQL chính thức vẫn khớp bộ ZIP. Chi tiết ở preservation.json.
AST/JSON/whitespace các file mới và liên kết README mới hợp lệ;
git diff --check đạt, index rỗng. Git cảnh báo LF→CRLF theo cấu hình máy,
không có lỗi whitespace. Xem static_checks.json. Không chạy encoder
inference/embedding hoặc xây index cho dữ liệu thật; đây là giới hạn chủ
động của lượt khảo sát, không phải bằng chứng retrieval đã được kiểm.

## File và cách đọc artifact

| File | Vai trò |
|---|---|
| src/coverage_survey.py | CLI/adaptation/thống kê/replay, gọi builder và dependency logic thật |
| config/coverage_survey.v1.json | Khóa input manifests, model preprocessing và policy/budget hiện hành |
| tests/test_coverage_survey.py | Fixture accounting/isolation và đối chiếu builder/tokenizer thật |
| Stage6_Coverage_Survey_Contract.md | Mẫu số, trạng thái, reasons, scope, nguồn và cổng pending |
| Báo cáo này | Kết quả, giới hạn và bằng chứng kiểm tra thực tế |
| AGENTS.md, README.md | Phạm vi cho phép và lệnh chạy lại |

Mở coverage_report.md, samples.md và unit_coverage.csv để rà nhanh. JSONL
giữ đầy đủ unit binding/hash, source spans, reasons và scope. Các preview
đầy đủ tách riêng trong preview/chunks.preview.jsonl và contexts.preview.jsonl;
encoder_inputs.preview.jsonl giữ cả input vượt ngưỡng, quarantine giữ nguyên
candidate/context. dependency_checks.jsonl giữ vùng phụ thuộc/impacts.
inputs/ giữ nguyên byte nguồn, cây và hồ sơ scope để replay.

Chỉ thêm công cụ khảo sát/config/tests/docs và cập nhật hai tài liệu hướng
dẫn; không sửa thuật toán parser/chunker/encoder hoặc dữ liệu cũ. Staging
không đưa vào Git. Không stage, commit hoặc push.
