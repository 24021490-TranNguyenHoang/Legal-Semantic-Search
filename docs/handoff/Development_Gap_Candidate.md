# Phiên 13 — dùng candidate v6 độc lập

Dataset `vtls-subset-experimental.v6-candidate.1`, snapshot **2025-01-01**.
Run giao: `staging/dataset-v6-gap-002/`. ZIP và hash cạnh thư mục:
`staging/dataset-v6-gap-002.zip`, `staging/dataset-v6-gap-002.zip.sha256`.
**Chưa có URL chia sẻ.** Chuyển cả ZIP và checksum cho người nhận.

Đây là candidate experimental; release=false. Không thay v5 hoặc index nhóm
đang dùng. Không chuyển 59 accepted/2 pending hay evaluation cũ sang candidate.
Target tuổi giữ ID nhưng read closure/binding khác. Đọc `delta.json`,
`disposition.jsonl`, `lineage.json`, `full_read.bindings.json` để đối chiếu.

## Người nhận chỉ cần ZIP và Python >=3.11

Không cần clone repository, pip, model hoặc cache. Đổi tên ZIP ở ví dụ cho đúng
file nhận được; không ghi output vào thư mục candidate đã seal.

```powershell
Get-FileHash dataset-v6-gap-002.zip -Algorithm SHA256
Get-Content dataset-v6-gap-002.zip.sha256
Expand-Archive dataset-v6-gap-002.zip clean-v6
Set-Location clean-v6
python -I -B candidate/consumer.py validate --dataset candidate
python -I -B candidate/consumer.py list --dataset candidate
python -I -B candidate/consumer.py read --dataset candidate --record-id c_fcaa52f3e09aa9b0719e84d05d9d13a9bd68343ff44f596fd379553ded82f4c6
python -I -B candidate/consumer.py read --dataset candidate --record-id c_30a64fc1bea93d7860d4f3821af382006956ca7dcbdc7770e636782e97fb1d9e
python -I -B candidate/consumer.py full-read --dataset candidate --output all-records.jsonl
```

Hash sai/thiếu file/proof/dependency phải lấy lại đúng ZIP; không sửa manifest
hoặc thế nguồn khác. Output tồn tại thì chọn tên mới. `base/consumer.py` là
consumer v5 lưu để kiểm chứng lịch sử; dùng **consumer.py cấp gốc** cho v6.
Table-row/whole-source/form giữ đúng type; encoder view và supporting unit
không phải target độc lập. Full-read trả nguyên record và required-read.

## Replay trong repository đầy đủ input đã ghim

Runtime độc lập khác môi trường build: build cần repo và các input/hash lịch sử
ở config, cùng môi trường pipeline đã có. Không cần chạy tokenizer/model/index
lại: preview đã có token evidence và được validator phiên12 kiểm lại từ cache.

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.gap_candidate build --config config/development_gap_candidate.v1.json --run-dir staging/dataset-v6-gap-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.gap_candidate validate --run-dir staging/dataset-v6-gap-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.gap_candidate zip --run-dir staging/dataset-v6-gap-NEW --zip-path staging/dataset-v6-gap-NEW.zip
$env:VTLS_GAP_CANDIDATE='staging/dataset-v6-gap-NEW'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest -v tests.test_gap_candidate tests.test_subset_candidate
```

NEW phải chưa tồn tại; không dùng lại run đã seal. Input v5-subset-006 và
development-gap-preview-002 được ghim cả tên lẫn SHA, không lấy latest.

Audit gate để lặp thử trên thư mục giải nén **ngoài repository**:

```powershell
python -I -S -B tests/audit_gap_candidate.py --dataset ABSOLUTE_CLEAN_DIR/candidate --report ABSOLUTE_CLEAN_DIR/audit.json --deny-root ABSOLUTE_REPO_DIR --deny-cache ABSOLUTE_USER_CACHE_DIR
```

Gate chặn đọc repository/cache và mạng/subprocess; tự thử hai truy cập bị cấm,
sau đó chạy CLI validate/list/read/full-read. Python stdlib và candidate là
nguồn đọc được phép. Kết quả này là kiểm tra thư mục sạch trên cùng máy/Windows,
không phải chứng nhận chạy trên máy/hệ điều hành khác.

Nguồn/edition/applicability pending, scope proposal; technical pass không xác
minh pháp lý hay chứng minh cải thiện retrieval. Bước tiếp cần được giao riêng:
quyết định phiên bản candidate và kế hoạch đánh giá/binding mới; chưa index,
metrics, chuyển label hay chuyển ứng dụng ở phiên này.
