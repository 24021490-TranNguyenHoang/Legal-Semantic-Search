# Bắt đầu rà năm query v6 — phiên 15

Mở `staging/subset-v6-binding-review-008/review/OVERVIEW.md`. Bản009 chỉ để replay; các bản001–007 giữ lịch sử phát triển, không dùng làm gói bàn giao.

Pool54 cặp/42record:52 A tương đương,1 B tuổi đổi closure,1 C đèn đỏ mới,0 D. Chưa có accepted v6. Mọi proposal đều AI hỗ trợ, không independent/blind; nguồn/edition/applicability pending. 59accepted/2pending v5 vẫn giữ nguyên, không chuyển binding.

Bắt đầu phiếu `review/sheets/01-dev-night_horn-3.md`, tiếp theo02tuổi,03đèn đỏ,04V3-D05,05V3-D07. Mỗi phiếu có câu hỏi nguyên văn, target/context/cells, quyết định cũ, proposal, EV6 evidence IDs và liên kết required-read/locator. File details chứa đầy đủ typed response. source_assets.json ánh xạ package locator sang file proof_assets đọc được; scope chỉ những slices đã chọn, không xem như review toàn file raw.

- Nhóm A: xem equivalence_list.jsonl, liệt kê đúng52cặp và toàn quyết định cũ. Có thể xác nhận danh sách exact hoặc chấm từng cặp.
- Nhóm B `V6PAIR-4a8583ecc08b02`: tuổi vẫn rank15, payload/context không đổi; closure2→16. Rà A1/A/B1, mô tô/xe gắn máy và điều kiện; không tự chuyển partial thành full.
- Nhóm C `V6PAIR-7e53f18e37b234`: đèn đỏ, own target mới từ unit từng là dependency. Rà lead Khoản9,7reads và điều kiện gây tai nạn/trừ điểm. Rank4 không quyết định label.
- Bảng khoảng cách: V=60 khác60<V≤80;80 và81 ở hai hàng khác nhau. Giữ header/điều kiện, mỗi hàng partial; whole-source dependency không tự thành direct.

## Điền phản hồi

Sao chép `templates/submission.template.json` **ra ngoài bundle seal**, ví dụ `staging/subset-v6-response-NEW/submission.json`. Tạo thư mục mới rồi Copy-Item; không sửa bản gốc. Giữ nguyên IDs/hashes/binding.

Reviewer_ref/reviewed_at lấy từ người dùng và sự kiện rà thực tế; không chép metadata v5. Với quy trình này, khi có quyết định thực tế ghi ai_assisted=true, independent=false, blind=false. Mỗi item có thể confirm_previous (giữ exact cả label/relation/completeness/reason), change (lý do/evidence), pending (null/uncertain); chưa kết luận giữ toàn bộ null. Chỉ điền EV6 refs thực sự dùng.

Để xác nhận danh sách A, giữ equivalent_confirmation.pair_ids nguyên vẹn, điền outcome=confirm_list và evidence_refs_used_by_pair cho từng cặp đã đọc. Không điền outcome item trùng danh sách; B/C rà riêng. Không suy đồng ý tiếp tục thành xác nhận đã kiểm tra.

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.binding_review validate --packet staging/subset-v6-binding-review-008
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.binding_review validate-response --packet staging/subset-v6-binding-review-008 --response staging/subset-v6-response-NEW/submission.json
```

Validate-response không nhập nhãn; accepted_created=0 kể cả bản nháp có quyết định. Sau phản hồi thật cần bước tiếp nhận/capture và adapter nhập v6 riêng, không chạy admit v5. Hai pending CAL-a46415f601/CAL-b69c61257d của V3-D02 không nằm trong template này.

## Nhận ZIP độc lập

ZIP `staging/subset-v6-binding-review-008.zip`, checksum cùng tên `.zip.sha256`. Chưa có URL chia sẻ. SHA256 `3f1c975ab6758474e01487824f440f4ed01b68488e2ad4646b1cbfec28192cd5`.

```powershell
Get-FileHash subset-v6-binding-review-008.zip -Algorithm SHA256
Expand-Archive subset-v6-binding-review-008.zip review-unpacked-NEW
Set-Location review-unpacked-NEW/review-v6
python -X utf8 -I -S -B packet_validator.py --packet .
python -X utf8 -I -S -B packet_validator.py --packet . --response ../submission.NEW.json
```

Mở review/OVERVIEW.md bằng editor/Markdown viewer. Không cần pip/model/index/repo để mở và kiểm integrity/evidence. Validator portable không thay consumer replay hoặc legal review. Đã thử cùng máy Windows/Python3.11.9; chưa máy/OS khác, không audit gate riêng trong phiên15.

## Replay trong repository

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.binding_review build --config config/subset_v6_binding_review.v1.json --run-dir staging/subset-v6-binding-review-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.binding_review zip --packet staging/subset-v6-binding-review-NEW --output staging/subset-v6-binding-review-NEW.zip
$env:VTLS_V6_REVIEW_PACKET='staging/subset-v6-binding-review-NEW'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest -v tests.test_binding_review
```

Các outputNEW phải chưa tồn tại. Repo build/validate cần pinned input và validators v5/v6, không dùng cached report thay replay. Không rebuild/search/tuning hoặc tính metrics. Quickstart trong ZIP và contract mô tả hai tầng seal/hashes; kiểm sidecar theo hash người bàn giao đưa, không sửa seal để pass.
