# Phiên 4 — chạy lại preview / validate / packaging plan

Chạy từ thư mục repository bằng môi trường hiện có. Không cài model weights,
không chạy inference. Chỉ đọc đúng đầu vào source-session3-proposal-009 và các
hash trong `config/source_session4.v1.json`; không chọn latest.

Run chính `staging/source-session4-preview-007`, replay008,
checks `staging/source-session4-checks-002`. Không ghi đè các run này.

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_session4 validate `
  --config config/source_session4.v1.json `
  --run-dir staging/source-session4-preview-007 `
  --replay-run staging/source-session4-preview-008
```

Để dựng lại, chọn **hai thư mục chưa tồn tại** (thay tên ví dụ nếu đã dùng):

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_session4 build `
  --config config/source_session4.v1.json --run-dir staging/source-session4-replay-A
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_session4 build `
  --config config/source_session4.v1.json --run-dir staging/source-session4-replay-B
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m tests.check_session4_artifacts `
  --config config/source_session4.v1.json --run staging/source-session4-replay-A `
  --replay staging/source-session4-replay-B --output staging/source-session4-checks-new
```

Build tái dùng extraction/graph session2, builder v2, table-owner adapter phiên3,
source regions TT35 và tokenizer assets tại tt35-preview-005. Không sửa DOCX hoặc
áp corrections lần nữa. Manifest cũ cùng raw/source/evidence assets phải còn đúng
path/hash như config; thiếu dependency phải báo lỗi. Không có URL ZIP mới.

Validator read-only kiểm binding config/code, checksum, replay builder từ source
spans mới, content/search identity, selected scope, closure, capability, form đủ
dòng và header/cell/annex whole-read. Exit0 là **technical_valid**, không phải
corpus/legal verified. A28 blocked và năm A16 scope unresolved là kết quả hợp lệ
của một run trung thực; không được coi exit0 là nhận các đơn vị đó vào plan.

Test đã chạy:

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest `
  tests.test_session4 tests.test_session3_membership tests.test_session2_sources -v
# Các test cũ dùng import sibling; cần PYTHONPATH=tests cho đúng invocation.
$savedPythonPath = $env:PYTHONPATH
try {
  $env:PYTHONPATH = (Resolve-Path tests).Path
  .\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest `
    tests.test_stage6_points tests.test_stage6 tests.test_circular_completion -v
} finally { $env:PYTHONPATH = $savedPythonPath }
git diff --check
```

27 pass; suite sau46 collected/7skip (opt-in artifact tests không có manifest),
không phải pass73. Checker là đường kiểm artifact mới thật:19negative,58payload
replay, five-type isolated reader. Không lặp các suite/model/evaluation không liên quan.

Mở lần lượt:

1. `staging/source-session4-checks-002/ND168_Disposition.md` — đủ27ca, ID/lineage,
   nguyên văn/context/kết quả. JSONL expanded chứa đầy đủ proof/dependency.
2. `staging/source-session4-preview-007/nd168_preview.md` —22preview dễ đọc;
   `nd168.reads.jsonl` có nguồn/proofs/required-unit content.
3. `staging/source-session4-checks-002/TT35_XXIII_A28_Review.md` — mẫu đủ18dòng,
   completion units,49trang required-read còn thiếu; ảnh tại
   `staging/source-session4-001/visual/TT35-annex-{126,127,128}.png`.
4. `staging/source-session4-checks-002/Packaging_Plan.md` và
   `staging/source-session4-preview-007/packaging_plan.{jsonl,csv}` —138target,
   238supporting-unit reads/1formXXVI; chưa dataset.
5. `staging/source-session4-checks-002/validation_report.json`, negative checks,
   isolated report và coordinator logs/receipt. Portable probe chỉ5reads, không
   là bundle đóng gói toàn138. Ngầm đọc workspace gốc bị audit hook từ chối.

Các offsets trong native_proofs là Unicode code point của normalized extraction;
context.char_start/end tương đối theo field unit; encoder view.search_char_start/end
tương đối text_for_search. Bbox lấy PDF native top-origin. Không đổi qua lại ba
không gian offsets. ND self source_artifact tương đối this_run; historical source
artifact refs cần được mount/copy rõ khi đóng gói ở phiên sau.

Word retry/copy/receipt tại `staging/source-session4-word-001/`: COM lỗi logon
session dù ứng dụng có sẵn, rendered=false. Chưa xác minh layout; chỉ cùng máy
Windows, không máy khác. Không giữ bản copy Word như raw chính thức.

Source/edition/applicability pending, scope chỉ proposal, human_review=null và
release=false. Năm A16K2 chưa nhận nhãn HTML; A28 blocked; I.418/I.416 chưa hòa
giải. Không stage/commit/push, dataset/index/embedding/app hoặc chuyển bản.
