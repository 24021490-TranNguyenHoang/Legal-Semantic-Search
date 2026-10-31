# Phiên 5 — nhận ZIP / validate / list / read / replay

Bản cuối: **vtls-subset-experimental.v5-candidate.1**, snapshot **2025-01-01**,
experimental/candidate, release=false. Không corpus verified/active/index.
**Chưa có URL chia sẻ.** Nhận đúng hai file từ người bàn giao:

- `staging/vtls-subset-experimental-v5-candidate1-002.zip`
- `staging/vtls-subset-experimental-v5-candidate1-002.zip.sha256`

SHA-256: `b1965b3df6373a068a328a8200a9a01d8345e16e73c79e675575a3b7c57fa822`.
ZIP **19.038.752byte**, root bên trong là `candidate/`. ZIP/prototype không có
hậu tố-002 không phải bản bàn giao cuối. Không cần clone repo để validate/read.

## Nhận và chạy trong thư mục mới

Ví dụ chép ZIP/SHA vào thư mục làm việc riêng, mở PowerShell tại đó. Các tên
`unpacked`/`.venv-runtime`/output dưới đây phải chưa tồn tại:

```powershell
$artifactZip = '.\vtls-subset-experimental-v5-candidate1-002.zip'
$expectedSha = ((Get-Content -LiteralPath ($artifactZip + '.sha256') -Raw).Trim() -split '\s+')[0]
$actualSha = (Get-FileHash -LiteralPath $artifactZip -Algorithm SHA256).Hash
if ($actualSha -ne $expectedSha -or $actualSha -ne 'b1965b3df6373a068a328a8200a9a01d8345e16e73c79e675575a3b7c57fa822') {
    throw 'Sai ZIP/SHA; không chạy tiếp.'
}
Expand-Archive -LiteralPath $artifactZip -DestinationPath .\unpacked
py -3.11 -m venv --without-pip .venv-runtime
.\.venv-runtime\Scripts\python.exe -I -B .\unpacked\candidate\consumer.py validate --dataset .\unpacked\candidate
.\.venv-runtime\Scripts\python.exe -I -B .\unpacked\candidate\consumer.py list --dataset .\unpacked\candidate
```

**Không cài requirements.txt của repository hoặc model weights.** Consumer và
validator chỉ stdlib; đã thử CPython3.11.9 Windows. Chưa tuyên bố tương thích thực
nghiệm trên OS/máy/Python khác. `requirements-runtime.txt` trong ZIP ghi đúng
không có pip dependencies. Dùng `-B`, giữ bundle bất biến, không lưu output/cache
vào candidate/ vì inventory sẽ từ chối file thừa.

Lấy ID thật từ list hoặc `candidate/example_record_ids.json`. Ví dụ record NĐ168
thực có trong gói; không fixture hoặc synthetic corpus:

```powershell
.\.venv-runtime\Scripts\python.exe -I -B .\unpacked\candidate\consumer.py read `
  --dataset .\unpacked\candidate `
  --record-id c_f40b4dc8a194af86f8c532e89b170ee49c88d9024b32fd5576431c13776c1dec
.\.venv-runtime\Scripts\python.exe -I -B .\unpacked\candidate\consumer.py full-read `
  --dataset .\unpacked\candidate --output .\all-records.read.jsonl
```

QUICKSTART.md trong ZIP còn ba ID thật cho table-row, whole-source và target cần
formXXVI. Consumer trả đủ record/context và required-read; whole-source giữ cả
text lẫn views, không chỉ snippet. Form layout nằm trong dependency response,
không được tìm như target. Exit0 là kiểm kỹ thuật; không legal approval.

Nếu hash/asset thiếu/sai: kiểm ZIP/đường dẫn, không sửa manifest để pass. Nếu thiếu
capability: consumer tích hợp phải hỗ trợ loại record/required-read, không cast
thành chunk text. Nếu output đã tồn tại: dùng tên mới, không overwrite. Object
nguồn không có đuôi file; dùng metadata/original locator để biết format, đọc bằng
công cụ thích hợp; không đổi tên object trong bundle.

## Response contract cho Hùng và thành viên tích hợp

`Consumer(root, capabilities=CAPABILITIES)`; `validate()`, `list()`, `read(id)`,
`full_read(output=None)`. Python caller dùng source consumer.py của đúng bundle;
không import implementation/prototype từ workspace khác. Khởi tạo/read từ bundle
bất biến, không mutate các dict hoặc file đã load. CLI khuyến nghị như trên.

Read response có dataset_version/snapshot/record_id/record_type, payload `record`
nguyên trạng, contexts, membership proposal, artifact_provenance, source_proofs,
required_read.bindings/unit_reads/supporting_records. `original_locator` giữ nhãn
lịch sử; `package_locator` trỏ object nội gói. Raw/trace/normalized/extraction
identity được bind bằng hash; không dùng đường dẫn cũ như runtime fallback.

- chunk.v1: nguyên văn/context/source spans, identity/search giữ nguyên.
- table-retrieval.v1: original lead, rows/header/cells, derived text riêng.
- source-retrieval.v1: toàn nội dung và encoder_views; view không là target.
- form XXVI: supporting layout/nhãn/trường trống/hướng dẫn, không text target.
- graph Part/Chapter và qg_ giữ schema riêng; structural ancestors không tự
  thành target hoặc required-read own text.

Đủ capability bắt buộc mới load/read; thiếu trả lỗi. `technical_admission` của
package không đổi scope, source/edition/applicability hay human review. Payload
XXVI còn scope_proposal=included lịch sử nhưng **role=supporting** theo plan.
Old downstream_blocker labels giữ nguyên để không sửa payload hash-bound.

Không dùng score/nguồn pending như xác minh pháp lý. Chưa lựa chọn/bổ sung index,
không đổi UI/API hoặc merge hung-feature trong phiên này. Gói có7nguồn inventory
nhưng chỉ6nguồn có target/supporting; NĐ165 **không có nội dung được đóng gói**.

## Lệnh build/replay đã chạy tại repository

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_session4 validate `
  --config config/source_session4.v1.json --run-dir staging/source-session4-preview-007
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_candidate build `
  --config config/source_session5.v1.json --run-dir staging/dataset-v5-subset-006
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_candidate build `
  --config config/source_session5.v1.json --run-dir staging/dataset-v5-subset-007
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m tests.check_subset_candidate_artifacts `
  --config config/source_session5.v1.json --dataset staging/dataset-v5-subset-006 `
  --replay staging/dataset-v5-subset-007 `
  --zip staging/vtls-subset-experimental-v5-candidate1-002.zip `
  --output staging/source-session5-checks-002
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest `
  tests.test_subset_candidate tests.test_session4 tests.test_session3_membership tests.test_session2_sources -v
git diff --check
```

Không chạy lại build vào các tên đã tồn tại: thay mọi output run/ZIP/checks bằng
tên mới nếu muốn tái tạo. Không đổi config input sang latest. Build cần repository
và input được ghim; **runtime trong ZIP không cần repository**. Không tokenizer,
embedding hoặc index build trong các lệnh này.

Checker tạo ZIP, ZIP replay, private mutation copy, giải nén và venv sạch, chạy
audit wrapper `-I -B` cấm repo/staging gốc/cache/network. Wrapper thực thi7CLI bằng
runpy trong cùng tiến trình Python: validate, list,4read,full-read; không gọi là
7cold-process benchmark. Command/exit/stdout/stderr thực tế nằm tại:

`staging/source-session5-checks-002/independent/runtime-output/`

Đặc biệt `audit_report.json`, `01-validate.stdout.json`, `07-full-read.stdout.json`
và `all-records.read.jsonl`. Tất cả138target/238supporting/XXVI đã đọc từ ZIP;
distributions=[], foreign_modules=[],4denial probes thành công. Private_bundle
đã bị mutation cố ý là **quarantine/test copy**, không phải artifact bàn giao.

Source scopes/provenance/edition/applicability và bố cục Word vẫn còn các giới
hạn trong [báo cáo](../reviews/Source_Session5_Verification.md). Không dùng kết
quả full-read hoặc ZIP tạo được để tuyên bố corpus đã verified.
