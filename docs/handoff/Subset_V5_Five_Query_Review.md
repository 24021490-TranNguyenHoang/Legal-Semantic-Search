# Bắt đầu lô review năm query subset v5 — phiên 9

Run bàn giao: **staging/subset-v5-query-review-002/**. Snapshot pháp luật
**2025-01-01**, dataset/index experimental giữ nguyên. Có **53 cặp**, gồm
**14 accepted kế thừa** và **39 cặp chưa có quyết định người dùng**. Không cần
chấm lại 14 cặp đã accepted; không có nhãn mới được nhập trong phiên này.

## Bắt đầu bằng phiếu thứ nhất

1. Mở [phiếu A — còi ban đêm](../../staging/subset-v5-query-review-002/review/01-dev-night_horn-3-01.md).
   Có bảy cặp chưa accepted, câu hỏi nguyên vẹn, citation, nguyên văn/context,
   cells/header nếu là bảng và đường dẫn required-read/proof đầy đủ. Không có
   rank/score/nhãn hoặc reason đề xuất.
2. Sao chép [template phản hồi thứ nhất](../../staging/subset-v5-query-review-002/templates/01-dev-night_horn-3-01.json)
   sang một thư mục mới ngoài bundle đã seal, ví dụ
   `staging/subset-v5-query-feedback-NEW/01-response.json`.
3. Điền từng cặp thực tế đã đọc: relevance/relation/completeness/reason và
   evidence_refs_used. Chưa đủ căn cứ giữ null; không mặc định thành 0.
   reviewer_ref/reviewed_at lấy từ người/sự kiện rà thực tế. Giữ IDs/hashes/binding.
4. Nếu dùng [bảng B đề xuất](../../staging/subset-v5-query-review-002/proposals/comparison.md)
   hoặc ChatGPT hỗ trợ khi quyết định, ghi proposal_consulted=true,
   ai_assisted=true, independent=false, blind=false. Không gọi là chấm độc lập
   chỉ vì phiếu A không hiển thị nhãn.
5. Tiếp tục bốn phiếu còn lại theo
   [sheets.json](../../staging/subset-v5-query-review-002/sheets.json).
   Mỗi query có phiếu riêng, lần lượt **7/9/8/7/8 cặp**, đều dưới 20 cặp.

Các template hiện **chưa có quyết định hoặc reviewer event**; flags phương pháp
rà chưa biết giữ null. Bản response phải ở ngoài seal. Phiên9 chưa triển khai
hoặc gọi nhập nhãn từ các template mới; không đưa trực tiếp chúng vào adapter
calibration22cặp của phiên8 hoặc scorer chunk-only v1.

## Tiến độ và nguồn pool

| Query | Pool | Accepted giữ nguyên | Cần rà |
|---|---:|---:|---:|
| dev-night_horn-3 | 10 | 3 | 7 |
| dev-driving_age-2 | 12 | 3 | 9 |
| dev-red_light-2 | 11 | 3 | 8 |
| V3-D05 | 10 | 3 | 7 |
| V3-D07 | 10 | 2 | 8 |
| Tổng | **53** | **14** | **39** |

Pool union theo query_id+record_id: toàn Top10 từ batch phiên6; accepted002;
outside_positive_session7 có evidence của đúng query. Có 50 cặp Top10, 14 lượt
thuộc nguồn accepted và 3 outside-positive, chồng lấn thành 53 cặp duy nhất.
Không cộng 50+14+3 thành số cặp mới. Không đưa toàn deep_run vào pool.

- `pool.jsonl` và manifest giữ toàn 53 cặp cùng nguồn pool/row SHA.
- `accepted.inherited.jsonl` giữ nguyên 14 object quyết định và metadata/AI
  provenance từ accepted002, không phải một đợt nhập mới.
- `review/`, `templates/`: chỉ 39 cặp chưa accepted; không yêu cầu rà lại 14 cặp.
- `proposals/`: phán đoán của agent, tách khỏi phiếu A và quyết định người dùng.
- `details/`, `evidence/`: đúng record/type, nguyên văn, bảng/cells, whole-source
  và required-read; supporting unit/form/encoder view không thành target riêng.
- `progress.jsonl/.md`: pending quyết định người dùng tách khỏi agent null và
  các giới hạn nội dung/coverage. Cả 39 cặp vẫn chờ người dùng, dù agent đã đề xuất.

Hai pending **CAL-a46415f601/CAL-b69c61257d** của V3-D02 nằm ngoài lô và giữ
nguyên trong accepted002. Pool hữu hạn không chứng minh đầy đủ mọi positive;
source/edition/applicability vẫn pending, scope proposal, metrics50query=null.

## Validate, replay và test

Từ root repository, dùng môi trường hiện hành; không build/search lại index:

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.query_review validate --manifest staging/subset-v5-query-review-002/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.query_review build --config config/subset_query_review.v1.json --run-dir staging/subset-v5-query-review-NEW
```

NEW phải chưa tồn tại. Replay giữ pool/accepted/proposals/evidence/phiếu/template
và manifest ổn định; không giả thêm thời điểm reviewer hoặc accepted labels.
Các input manifest/consumer và source bindings trong config phải giữ nguyên.

Fixture/regression gọn:

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_query_review.QueryReviewTests tests.test_subset_labels.TypedLabelsTests tests.test_subset_calibration tests.test_subset_review tests.test_composition_review tests.test_evaluation -v
```

Để chạy thêm artifact/replay/negative test với output mới:

```powershell
$env:VTLS_QUERY_REVIEW_MANIFEST = 'staging/subset-v5-query-review-002/manifest.json'
$env:VTLS_QUERY_REVIEW_CHECKS_DIR = 'staging/subset-query-review-check-NEW'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_query_review tests.test_subset_labels.TypedLabelsTests tests.test_subset_calibration tests.test_subset_review tests.test_composition_review tests.test_evaluation -v
Remove-Item Env:VTLS_QUERY_REVIEW_MANIFEST
Remove-Item Env:VTLS_QUERY_REVIEW_CHECKS_DIR
```

Không dùng artifact test này để nhập lại accepted hoặc tính metrics. Run001 là
prototype trước khi sửa bố cục bảng progress Markdown; giữ payload/source lịch sử.
Bản giao là002, replay cuối trong `staging/source-session9-checks-001/artifacts-001/replay/`.
