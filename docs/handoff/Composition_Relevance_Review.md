# Bàn giao rà relevance composition v1.1

Snapshot **2025-01-01**. Đây là nhãn development do agent đề xuất, không phải
human-reviewed, xác minh pháp lý hoặc số đo retrieval đã nghiệm thu.

Run mới: `staging/composition-relevance-review-001/`.
Log thực thi sau seal: `staging/composition-relevance-review-checks-001/`.

| Muốn xem | File trong run review |
|---|---|
| Bắt đầu rà 10 câu / 19 cặp | `calibration.md` |
| Mẫu phản hồi trống | `calibration_submission.template.json` |
| Toàn bộ 500 cặp | `annotations_review.md`, `annotations.proposed.jsonl` |
| 34 positive ngoài pool | `outside_pool.proposed.jsonl` |
| Khảo sát 50 câu và giới hạn | `coverage.jsonl` |
| Tìm sâu 45 dev / 4.500 hits chưa chấm toàn bộ | `deep_run.jsonl` |
| Source-only chưa thành target | `source_only_backlog.jsonl` |
| So sánh v1/v3, lỗi và đề xuất | `review_report.md`, `error_cases.jsonl` |
| 300 proposal riêng đúng binding v1 | `v1.proposed.jsonl` |

Mở nguyên văn, context, ô bảng và required-read dependency theo link detail
trong phiếu. Một hàng đúng chưa trả lời toàn câu so sánh; target chỉ dẫn chiếu
không biến source unit thành kết quả được rank.

Sao chép template ra ngoài bundle seal, ví dụ
`staging/composition-relevance-submission-001/calibration_submission.json`.
Điền `reviewer_outcome` = agree/edit/uncertain, nhãn/quan hệ/mức đầy đủ khi đã
kết luận, lý do và evidence_refs_used thực sự dùng. Reviewer_ref/thời gian chỉ
lấy từ người và sự kiện thật; chưa kết luận để null. Gửi lại file JSON đó hoặc
bản sao Markdown đã điền. Không cần sửa hash/binding/proposal.

Duyệt mẫu chỉ hiệu chuẩn các cặp được xem; không chấp nhận ngầm 500 nhãn hay
độ phủ toàn corpus. Người rà có thể bác proposal bằng lý do và bằng chứng.

```powershell
# Từ thư mục repository, môi trường BM25 hiện hành; không build lại index.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.composition_review --manifest staging/composition-relevance-review-001/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_composition_review tests.test_evaluation -v
```

Validator kiểm input inventory/hash, frozen query, record membership/type,
nguyên payload và detail/spans/cells/dependency, missing/duplicate labels,
pending/null, template chưa điền và v1 binding riêng. Không chấm đúng/sai thay
reviewer. Cần giữ các input run đúng manifest; không tìm “run mới nhất”.

Sau khi có quyết định thật: lưu submission/annotation lịch sử trong run mới,
không sửa bundle này; chốt từng nhãn và mức đầy đủ qrels bằng evidence. Chỉ
tính metrics cho câu đủ accepted judgments, positive và coverage review theo
[rubric v1.1](../design/Composition_Relevance_Review_v1.1.md).
Metrics hiện **null**, qrels rỗng; unjudged không thành0.

CLI score accepted composition có cả table record **chưa triển khai**. Scorer
v1 chỉ nhận chunk_id; bước đó cần adapter hẹp giữ record_id/type và tái dùng
hàm metric đã kiểm thử của `src.evaluation`. Không giả table là chunk DDD,
không chép proposal/mẫu đồng ý thành qrels hoặc tự ghi human event.
