# Phiên 10 — tiếp nhận và nhập 39 nhãn mới subset v5

Thực thi 2026-11-05 trên Windows tại repository; Python `.venv-stage1`.
HEAD đầu phiên `8ad0c2ff01244219eef0fe2496d2be24f0bde7fc`, Git sạch.
Snapshot pháp luật 2025-01-01. Không stage/commit/push, không thay nguồn,
dataset/index/query/ranking hoặc qrels lịch sử.

## Kết quả đã thực hiện

- Capture nguyên chỉ dẫn người dùng, tạo feedback và năm bản điền template mới.
  Giữ đúng 39 relevance/reason, ID/type/hash/binding; không nhập lại 14 inherited.
- Reviewer opaque reference `## CAL-039998018b`; thời điểm review giữ nguyên
  `2026-11-05T09:07:00+07:00` (=02:07 UTC). Thời điểm import riêng trong receipt.
  Origin user_reviewed_ai_assisted; không independent/blind. Đã xem đề xuất
  ChatGPT=true; lịch sử mở bảng B và từng detail=null, không tự suy đã xem.
- Nhập **39 mới: 35 nhãn 0 + 4 nhãn 1**. Type: **25 chunk / 12 table-row /
  2 whole-source**. Nhãn 1 giữ **2 supporting_target / 2 dependency_only**,
  completeness partial. Nhãn 0 unrelated/none. Evidence gồm field quote/offset,
  source spans/cells nguyên bản; dependency-only có focus đúng required-read.
- So proposal: cả39 trùng triple relevance/relation/completeness; lý do giữ
  nguyên phản hồi người dùng, không thay bằng lý do máy. Chi tiết từng cặp ở
  `staging/source-session10-checks-001/reviewed_decisions.md` và submission
  `comparison.jsonl`. Sự đồng thuận này không chứng minh rà độc lập.
- Aggregate tham chiếu batch cũ20 và batch mới39: **59 cặp duy nhất**, phân bố
  **7 nhãn2 / 10 nhãn1 / 42 nhãn0**. Không sao inherited/replay thành nhãn mới.
- **2 pending cũ** của V3-D02: CAL-a46415f601, CAL-b69c61257d vẫn null.
  Không thiếu metadata để nhập39 và không cần người dùng xác nhận lại các cặp này.

| Query | Pool | Accepted cũ | Mới phiên10 | Accepted sau nhập | Chưa quyết định trong pool |
|---|---:|---:|---:|---:|---:|
| dev-night_horn-3 | 10 | 3 | 7 | 10 | 0 |
| dev-driving_age-2 | 12 | 3 | 9 | 12 | 0 |
| dev-red_light-2 | 11 | 3 | 8 | 11 | 0 |
| V3-D05 | 10 | 3 | 7 | 10 | 0 |
| V3-D07 | 10 | 2 | 8 | 10 | 0 |
| Tổng | 53 | 14 | 39 | 53 | 0 |

## Bản giao và binding

| Artifact | Run | Manifest SHA-256 |
|---|---|---|
| Review ghim | subset-v5-query-review-002 | 04ad32955c1443aedcc7b6f6f82e4e63e1bcd9a8adfe903159ff93463444b2f2 |
| Prior accepted | subset-v5-accepted-labels-002 | 8a14c067ed5165fb757ad55f7508f27fea8cb3fa8af33b7f861aea291cf9b9a8 |
| Submission mới | subset-v5-query-submission-002 | a523a7264e91e8e14fc923790e2d0800e71b3d7858f6293931541184b5333f7c |
| Accepted mới | subset-v5-query-accepted-001 | 6efed38a188b3c32b769d4f69337e45c2b7be9f01f55e4509e9b0efd35f62766 |
| Aggregate | subset-v5-label-aggregate-001 | 7c4dbee482e5bc7d38e96b12e4a75684b3756a47b48d4385c713e2fd846cd56e |

Các run ở dưới `staging/`, dùng `manifest.json`. Các file binding đầy đủ trong
`staging/source-session10-checks-001/handoff.bindings.json` và submission.
Dataset `vtls-subset-experimental.v5-candidate.1`, index `vtls-bm25s-subset.v1`;
dataset006/index003/query001/batch002 giữ nguyên đúng binding phiên9.
Không chọn run mới nhất. Import ID:
`import_bb68d61951bb6c986a886e4fa5f4230f2aba346c835367067e0c3567a7118f57`.

Run submission001 là lần ghi thử dừng vì chưa tạo thư mục responses; giữ nguyên
hai file capture/feedback, không seal/import. Đã sửa chỗ tạo thư mục và dùng
run002. Không ghi đè hoặc sửa artifact lịch sử để giấu lỗi.

## Kiểm chứng thực thi

Đã chạy các lệnh dưới đây (PowerShell, từ repo), exit0:

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.query_labels submit --review-manifest staging/subset-v5-query-review-002/manifest.json --prior-manifest staging/subset-v5-accepted-labels-002/manifest.json --feedback staging/source-session10-checks-001/feedback.received.json --run-dir staging/subset-v5-query-submission-002
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.query_labels admit --submission-manifest staging/subset-v5-query-submission-002/manifest.json --prior-manifest staging/subset-v5-accepted-labels-002/manifest.json --run-dir staging/subset-v5-query-accepted-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.query_labels aggregate --review-manifest staging/subset-v5-query-review-002/manifest.json --batches staging/subset-v5-accepted-labels-002/manifest.json staging/subset-v5-query-accepted-001/manifest.json --run-dir staging/subset-v5-label-aggregate-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.query_labels validate-submission --manifest staging/subset-v5-query-submission-002/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.query_labels validate --manifest staging/subset-v5-query-accepted-001/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.query_labels validate-aggregate --manifest staging/subset-v5-label-aggregate-001/manifest.json
```

Chạy thêm submit với cùng inputs vào
`staging/source-session10-checks-001/submission-replay`: **12 file, gồm cả
manifest/sidecar, giống byte** bản bàn giao. Unit/integration tests dùng biến
môi trường trong handoff, lệnh:

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest -v tests.test_query_labels tests.test_query_review.QueryReviewTests tests.test_subset_labels.TypedLabelsTests tests.test_subset_calibration tests.test_subset_review
```

**53 tests pass / 0 skip**, 52.282s. Log `checks/tests.final.log`; các kiểm tra
thật trong `checks/artifacts-001/`. Trước đó 47 unit/regression cũng exit0.
Đây là kiểm chứng adapter/integrity, không phải chất lượng pháp lý/retrieval.

- **25 resealed negative mutations** bị từ chối: 18 submission/evidence/feedback
  và7 accepted. Gồm sai binding/type/hash, thiếu/trùng cặp, đổi nhãn/reason,
  null/bool, thời điểm sai, giả review độc lập/đã mở file, thiếu/sai evidence,
  cells sai, đổi dependency_only thành direct, mở rộng coverage.
- Prior sai bị từ chối trước khi tạo output; overlap prior/pending không implicit
  reimport/supersedes. Aggregate chứa replay/cùng import bị từ chối.
- Admit lại cùng run trả newly_imported=0 và inventory giữ nguyên. Replay vào
  run mới giữ import ID, byte-identical accepted/pending/qrels; receipt ghi thời
  điểm import thực tế riêng. Không cộng bản replay vào59.
- Submission được tái dựng từ templates+capture, accepted từ submission typed,
  aggregate từ row references; không chỉ dựa outer checksum. Trạng thái nguồn,
  pending, native proof không được chuyển thành verified.
- Preservation và diff kiểm cuối lưu trong `checks/preservation.final.json` và
  `checks/diff-check.log`: các baseline cũ giữ nguyên ngoại trừ STATUS thêm đầu;
  toàn bộ nội dung STATUS cũ được giữ nguyên bytes ở phần lịch sử.

`checks` trong đoạn này là `staging/source-session10-checks-001/`.

## File thêm/sửa và giới hạn

Thêm `src/query_labels.py`: adapter hẹp submit/validate/admit/aggregate, tái dùng
helper consumer/evidence/typed labels có sẵn. Thêm `tests/test_query_labels.py`.
Thêm contract `Subset_V5_Query_Acceptance_v1.0.md`, handoff
`Subset_V5_Query_Acceptance.md` và báo cáo này; STATUS chỉ thêm trạng thái hiện tại.
Không sửa query_review/subset_labels/producer/scorer cũ hoặc schema DDD.

Chưa đo metrics50 query, chưa tìm hết positive ngoài pool hoặc duyệt500 cặp.
Không có nhãn legal verified. Source/edition/applicability pending chung giữ
nguyên. Không chạy máy/hệ điều hành khác; artifact phụ thuộc các bundle ghim
trong workspace theo manifest, chưa là gói bàn giao portable riêng.

Bước tiếp theo chỉ là đề xuất: người phụ trách evaluation rà hai pending khi
đủ thông tin, chọn lô query tiếp và chốt điều kiện metric phù hợp. Không tự
mở rộng nhập nhãn/tuning hoặc thay dataset/index từ kết quả39 cặp này.
