# BM25 candidate v6 — phiên 14

Experimental, release=false, snapshot 2025-01-01. Index `vtls-bm25s-subset.v2` chỉ cho dataset `vtls-subset-experimental.v6-candidate.1`; không thay indexv5 hay ứng dụng Hùng. Nguồn/edition/applicability pending, scope proposal. Không chuyển 59accepted/2pending hoặc tính metrics v6.

## Gói độc lập

Chưa có URL chia sẻ. Nhận `vtls-bm25s-subset-v2-001.zip` và `.zip.sha256` từ người bàn giao; kiểm hash đối chiếu báo cáo phiên14. ZIP chứa bm25/ gồm datasetv6, consumer cấp gốc, engine, runtime source/config, query50 và dependency pins. Không cần clone repo hoặc lấy thêm staging nguồn. Supporting/form/views không là document tìm kiếm.

Ví dụ PowerShell trong thư mục chứa ZIP, mọi output/venv mới:

```powershell
$zip = 'vtls-bm25s-subset-v2-001.zip'
$expected = (Get-Content "$zip.sha256").Split(' ')[0]
if ((Get-FileHash $zip -Algorithm SHA256).Hash.ToLower() -ne $expected) { throw 'ZIP SHA mismatch' }
Expand-Archive -LiteralPath $zip -DestinationPath unpacked-v6
py -3.11 -m venv .venv-bm25-v6
.\.venv-bm25-v6\Scripts\python.exe -m pip install -r unpacked-v6/bm25/requirements-bm25.txt
# Offline: thêm --no-index --find-links WHEELS_DIR nếu đã nhận ba wheel đúng phiên bản
.\.venv-bm25-v6\Scripts\python.exe -I -B unpacked-v6/bm25/search.py validate --index unpacked-v6/bm25
.\.venv-bm25-v6\Scripts\python.exe -I -B unpacked-v6/bm25/search.py search --index unpacked-v6/bm25 --query 'Ô tô vượt đèn đỏ bị xử phạt như thế nào?' --top-k 10
.\.venv-bm25-v6\Scripts\python.exe -I -B unpacked-v6/bm25/search.py read --index unpacked-v6/bm25 --record-id c_fcaa52f3e09aa9b0719e84d05d9d13a9bd68343ff44f596fd379553ded82f4c6
.\.venv-bm25-v6\Scripts\python.exe -I -B unpacked-v6/bm25/search.py batch --index unpacked-v6/bm25 --output batch-v6-NEW
.\.venv-bm25-v6\Scripts\python.exe -I -B unpacked-v6/bm25/dataset/consumer.py full-read --dataset unpacked-v6/bm25/dataset --output full-read-v6.jsonl
```

Runtime dùng CPython3.11, bm25s0.3.13, numpy2.4.6, scipy1.17.1. requirements-bm25.txt khóa đúng ba dependency; wheel cache Windows CPython311 có trong kiểm chứng phiên14, không chứa model/venv trong ZIP. Người nhận OS/Python khác phải kiểm compatibility, không tắt validator hoặc dùng wheel sai platform. Chưa có kiểm BM25 Linux trong phiên này; consumer dataset đã có kiểm Linux riêng không chứng minh index chạy Linux.

Validate kiểm inventory/config/code/dataset/proof và replay matrix; search/load không rebuild. Timing load+validate tách query ranking và detail hydration. Query rỗng bị từ chối, OOV rỗng, unknown ID hoặc thiếu binding/dependency lỗi; không fallback mẫu. Table/whole/form phải đọc đúng type và đủ required-read. Hit partial không tự đủ câu trả lời nhiều phần.

## Replay từ repository

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_bm25_v6 build --config config/source_session14.v1.json --run-dir staging/bm25-subset-v6-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_bm25_v6 batch --index staging/bm25-subset-v6-NEW --output staging/bm25-subset-v6-batch-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_bm25_v6 zip --index staging/bm25-subset-v6-NEW --output staging/vtls-bm25s-subset-v2-NEW.zip
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest -v tests.test_subset_bm25 tests.test_subset_bm25_v6
```

Dùng config đã ghim; không chọn latest hoặc sửa v1 modules/seal. So sánh và negative/portable harness: `python -X utf8 -B tests/check_subset_bm25_v6.py --index staging/bm25-subset-v6-001 --replay staging/bm25-subset-v6-002 --batch staging/bm25-subset-v6-batch-001 --output staging/source-session14-validation-NEW --zip staging/vtls-bm25s-subset-v2-001.zip`. Thiết lập `PYTHONPATH=.` khi chạy test script. Harness cần ba wheels cache đúng tên/hash; ghi receipt khi sao chép, sau đó gate chặn repo/cache gốc. Mọi thư mục NEW phải chưa tồn tại. Không gọi chạy lại cùng Windows là kiểm máy/OS khác.
