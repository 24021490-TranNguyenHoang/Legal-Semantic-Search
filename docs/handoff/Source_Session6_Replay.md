# Phiên 6 — replay hữu hạn

Snapshot2025-01-01, HEAD đầu phiên `441efbea1fbecc9a0d61e6c3962661862beb74ec`.
Giữ source config `config/source_session6.v1.json`, không chọn run latest.
Dataset gốc candidate006/ZIPv5-002 và queries composition-queries-001 bất biến.

## Artifact chính

- Index: `staging/bm25-subset-v5-003/`, replay `bm25-subset-v5-004/`.
- Batch: `staging/bm25-subset-v5-batch-002/`.
- Matrix/replay/negative checkpoints: `staging/source-session6-checks-002/`.
- Portable/final report: `staging/source-session6-portable-003/validation_report.json`.
- ZIP: `staging/vtls-bm25s-subset-v1-002.zip` và `.sha256`.
- Đọc [Quickstart](Source_Session6_BM25_Quickstart.md) để chạy ZIP độc lập.
- Báo cáo/hash/kết quả thực tế: [Verification](../reviews/Source_Session6_BM25_Verification.md).

Các run001/002, batch001, checks001 và ZIP001 là development trước sửa encoding
stdout CLI Windows, không là bản bàn giao cuối. Checks002 đã chạy5CLI thành công
nhưng gate chặn Windows NUL, được giữ nguyên như lần thử chưa đạt audit. Portable003
chạy lại gate đã sửa, không sửa/reseal ZIP002. Giữ lịch sử; không overwrite.

## Lệnh tái tạo

Thay mọi output bằng tên mới chưa tồn tại. Không đổi input/hash để làm lệnh pass.

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_bm25 build --config config/source_session6.v1.json --run-dir staging/bm25-subset-v5-NEW-A
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_bm25 build --config config/source_session6.v1.json --run-dir staging/bm25-subset-v5-NEW-B
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_bm25 batch --index staging/bm25-subset-v5-NEW-A --output staging/bm25-subset-v5-batch-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m tests.check_subset_bm25_artifacts --index staging/bm25-subset-v5-NEW-A --replay staging/bm25-subset-v5-NEW-B --batch staging/bm25-subset-v5-batch-NEW --output staging/source-session6-checks-NEW --zip staging/vtls-bm25s-subset-NEW.zip
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_subset_bm25 -v
git diff --check
```

Lệnh resume thực tế sau khi sửa gate (không lặp các mutation đã có receipt):

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m tests.check_subset_bm25_artifacts --index staging/bm25-subset-v5-003 --batch staging/bm25-subset-v5-batch-002 --resume-portable staging/source-session6-checks-002 --output staging/source-session6-portable-003 --zip staging/vtls-bm25s-subset-v1-002.zip
```

Resume vẫn validate dataset/index/matrix lại và so ZIP với từng byte index,
SHA/replayZIP, signatures và checkpoint negatives; giải nén/venv/cài pins mới.
Chỉ phần thử mutation riêng được tái sử dụng, không suy portable pass từ receipt cũ.
Đổi output thành tên mới nếu chạy lại lệnh này.

Checker validate/replay matrix, so mọi inventory payload, chạy lại50query/đọc mọi
hit; full-read138/238support/XXVI; thử mutation trên private_index rồi ZIP +so
ZIP replay. Sao3wheel đã có từ `composition-bm25-independent-001/wheels` sang
independent/wheels và ghi SHA; venv mới/pip offline đúng pins, không dev venv.
Nếu wheel cache không có, checker báo thiếu thay vì âm thầm lấy dependencies/model.
Quickstart cho người nhận dùng pip với pins hoặc wheel cache đúng OS/Python.

ZIP giải nén riêng dưới checks/independent/unpacked/bm25. Audit gate cấm mở
repo/staging/dev venv/HF cache gốc/network; chỉ cho package, output, clean venv,
base Python stdlib và harness. Chỉ cho phép thiết bị null đúng `os.devnull`
ngoài các root; không mở quyền device/path khác. Subprocess bị chặn; truy vấn
metadata hệ thống tùy chọn của platform.py fallback, được log riêng. Có4denial
probes, kiểm modules/distributions.
Wrapper thực thi5CLI trong cùng process (validate,batch,3read types), thêm full-read
dataset138. Không gọi là5cold processes hoặc máy khác. Command/stdout/stderr ở
checks/independent/runtime-output; pip/venv/command receipts ở checks root.

Compare `ranking_and_response_signature.jsonl` nguyên byte giữa main/replay/
portable: ID/type/rank/score và hash dataset_response, loại timing. Detail envelope
còn hash index manifest; dữ liệu nguyên thủy không bị formatter. Full-read compare
response_content hash riêng; manifest inventory/index binding giữ nguyên.

Output report có metrics=null/PENDING_LABELS, không nhận qrels v1/v3, human events0.
`source-session6-001/Coverage_Observations.md` là quan sát agent theo membership,
không phải accepted annotation. `Search_Read_Examples.md` là ví dụ có full detail links.
Không dùng private mutation copy như artifact bàn giao.

Preservation snapshot đầu phiên ở `source-session6-001/preservation.baseline.json`.
STATUS/ingestion chỉ được prepend, phải giữ suffix byte-exact; raw/evidence/dataset/
index/qrels/ZIP/run cũ giữ hash. Git staged rỗng/HEAD nguyên và diff --check ở final
receipt. Không stage/commit/push, UI/API/embedding hoặc chuyển phiên bản cho nhóm.
