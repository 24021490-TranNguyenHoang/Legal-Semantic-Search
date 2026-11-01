# Bàn giao phiên 7 — đọc phiếu hiệu chuẩn

Snapshot **2025-01-01**. Dataset `vtls-subset-experimental.v5-candidate.1`,
index `vtls-bm25s-subset.v1`; không thay index/query/membership.
Nhận xét hiện là **agent proposed**, không accepted/human-reviewed/legal verified.

## Bắt đầu ở đây

1. Mở **staging/subset-v5-relevance-002/calibration.md**:10query/22cặp, không
   rank/score/nhãn hoặc lý do agent. Mỗi cặp có câu hỏi nguyên vẹn, citation,
   nguyên văn, context, bằng chứng liên quan và link full detail/required-read.
2. Đọc **rubric.md** cùng run:2 trực tiếp (full/partial riêng),1 hỗ trợ hoặc
   dependency-only,0 đã đọc không phù hợp; chưa rõ đểnull/uncertain.
3. Sao chép **calibration_submission.template.json** sang run submission mới,
   ví dụ `staging/subset-v5-review-submission-NEW/response.json`, ngoài bundle seal.
4. Điền từng cặp thật sự đã đọc: relevance, relation, completeness, reason,
   evidence_refs_used; reviewer_ref và reviewed_at từ người/sự kiện thực tế.
   Phần chưa kết luận giữnull. Không sửa binding, IDs hoặc hashes.
5. Gán độc lập trước, rồi mới mở annotations.proposed.jsonl/annotations_review.md
   và calibration.crosswalk.jsonl để đối chiếu. Không suy đồng ý toàn bộ từ việc
   duyệt mẫu hoặc yêu cầu tiếp tục. Scorer/nhập accepted labels chưa chạy.

Không ghi "agree" với proposal chưa xem; có thể dùng reviewer_outcome để ghi
đã kết luận/chưa chắc/cần thêm bằng chứng. Không bắt tên/thời gian hay phê duyệt
toàn nguồn khi chỉ xem22cặp. Phản hồi khác agent được giữ cùng lý do/evidence,
không phải lỗi kỹ thuật chỉ vì khác nhãn đề xuất.

## Tìm các đầu ra

| Nội dung | Artifact |
|---|---|
| 500dispositions/5pending | subset-v5-relevance-002/annotations.proposed.jsonl |
| Phiếu đề xuất có lý do | subset-v5-relevance-002/annotations_review.md |
| Full118detail đã gắn nhãn | subset-v5-relevance-002/details/ |
| 11positive ngoài Top10 | subset-v5-relevance-002/outside_pool.proposed.jsonl |
| Coverage50query | subset-v5-relevance-002/coverage.jsonl |
| Coverage dễ đọc | subset-v5-relevance-handoff-001/Coverage_50_Queries.md |
| Ngoài pool dễ đọc | subset-v5-relevance-handoff-001/Outside_Pool_Review.md |
| Backlog và portability | subset-v5-relevance-handoff-001/Backlog.md; review/portability_simulation.json |
| Lý do chọn15query trước tìm sâu | subset-v5-relevance-002/deep_selection.json |
| 1.980cặp retrieved, chưa chấm toàn bộ | subset-v5-relevance-002/deep_run.jsonl |
| Tests/negative/CLI receipts | subset-v5-relevance-checks-001/ |

Các đường dẫn bảng tính từ `staging/`. Companion handoff có manifest bind đúng
review002, không append vào bundle đã seal. Main002/replay003 dùng cùng phán đoán,
khác thời điểm build kỹ thuật; giữ prototype001 và source copy trong work001.
Qrels accepted rỗng/metrics=null, không chuyển nhãn v1/v3.

## CLI và replay

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_review validate --manifest staging/subset-v5-relevance-002/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_subset_review tests.test_composition_review tests.test_evaluation -v
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_review build --config config/subset_relevance_review.v1.json --run-dir staging/subset-v5-relevance-NEW
git diff --check
```

Build ở đây là **đóng gói review**, không build/rebuild BM25. Nó load index003
read-only, kiểm input hashes/117detail cũ bằng consumer, dùng bảng phán đoán từng
cặp đã ghi trong config, gọi query gốc Top138 cho đúng15query đã chọn, xuất run mới.
Không suy nhãn theo score/từ khóa hoặc default0 khi thiếu cặp; thiếu disposition
phải lỗi. Time `agent_reviewed_at` là sự kiện đọc đã ghi; replay không tự nhận đã
thực hiện review mới. technical_built_at là đồng hồ chạy riêng.

Đường validate tái dùng composition_review.validate_annotation/validate_pair_set
và evaluation.validate_queries, thêm facade full response/cells/whole/form.
Giữ producer/consumer/index hash-bound cũ; không gọi validator composition v3 để
nạp nhãn v3. Runtime review cần môi trường/pins BM25 hiện hành để load/search.

Lỗi portability của gói index phiên6 không được sửa trong lượt này: inventory sắp
Path native khác Windows/POSIX; runtime CPython-minor/Unicode/pins là điều kiện
khác. Mô phỏng PureWindowsPath/PurePosixPath không là chạy Linux. Xem
[báo cáo](../reviews/Source_Session7_Relevance_Verification.md) trước khi bàn giao
index sang OS khác; không sửa manifest hoặc bỏ validator để vượt lỗi.
