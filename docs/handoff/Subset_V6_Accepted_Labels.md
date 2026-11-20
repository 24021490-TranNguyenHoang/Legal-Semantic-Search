# Bàn giao nhãn relevance v6, phiên 16

Phiên 16 đã nhập 54 quyết định cho năm query. Người dùng tiếp nhận đề xuất ChatGPT và cung cấp thời điểm xác nhận `2026-11-20T08:08:00+07:00` (`2026-11-20T01:08:00Z`). Các tham chiếu EV6 ghi bằng chứng trợ lý đã dùng. Provenance ghi `user_adopted_ai_assisted`, `independent=false`, `blind=false` và để trống thông tin người dùng có tự mở các tệp chi tiết hay không.

| Thành phần | Đường dẫn |
|---|---|
| Snapshot nguyên byte và manifest | `staging/subset-v6-response-capture-001/` |
| Nhãn, receipt và provenance | `staging/subset-v6-accepted-labels-001/` |
| Gói để đọc lại độc lập | `staging/subset-v6-accepted-labels-001.zip` |
| SHA-256 ZIP | `71c6000d986324d82cee98d0aa602568cd6b692f492aeba5c1298e968ed8e535` |

Nhãn có phạm vi đúng năm query, với binding dataset v6 và index v2. Đọc `accepted.annotations.jsonl` để lấy lý do, evidence và lineage. Đọc `receipt.json` để xem phép nhập và `provenance.json` để xem vai trò của trợ lý và người xác nhận.

## Validate và replay trong repository

Chạy từ thư mục gốc. Nếu replay, chọn đường dẫn mới dưới `staging/`.

```powershell
$packet = 'staging/subset-v6-binding-review-008'
$capture = 'staging/subset-v6-response-capture-001'
$accepted = 'staging/subset-v6-accepted-labels-001'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.v6_acceptance validate --packet $packet --capture $capture --accepted $accepted
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.v6_acceptance admit --packet $packet --capture $capture --accepted $accepted
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.v6_acceptance admit --packet $packet --capture $capture --accepted staging/subset-v6-accepted-replay-NEW --replay
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest -v tests.test_v6_acceptance
```

Lần gọi `admit` lặp trên đúng artifact trả `ALREADY_IMPORTED` với `newly_imported=0`. Bản replay có cùng import ID và cùng byte nhãn. Thời điểm ghi bản replay được lưu riêng trong receipt. Dùng import ID để nhận biết bản sao của cùng một lần nhập.

## Đọc ZIP độc lập

Đối chiếu SHA-256 ở trên hoặc sidecar cùng tên. Gói chứa packet phiên 15, bản capture, bản accepted và validator Python chỉ dùng thư viện chuẩn. Đã thử trên Windows với CPython 3.11.9.

```powershell
Get-FileHash subset-v6-accepted-labels-001.zip -Algorithm SHA256
Expand-Archive subset-v6-accepted-labels-001.zip accept-v6-unpacked
Set-Location accept-v6-unpacked
python -X utf8 -I -S -B validate.py validate --packet packet --capture capture --accepted accepted
```

Validator đọc lại submission bằng mã đã seal trong packet, dựng lại từng nhãn từ quyết định và EV6, rồi so toàn bộ file accepted. Gói mang theo bằng chứng nguồn của packet. Phiên này chỉ bàn giao artifact cục bộ.
