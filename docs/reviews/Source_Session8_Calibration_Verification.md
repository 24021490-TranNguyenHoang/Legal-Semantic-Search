# Phiên 8 — phản hồi hiệu chuẩn subset v5, 04/11/2026

**RESPONSE_RECORDED / AWAITING_REVIEWER_METADATA / ACCEPTED_IMPORT_NOT_RUN**.
Snapshot pháp luật **2025-01-01**. Đây là phản hồi **người dùng đã đọc lại và
xác nhận, có ChatGPT hỗ trợ**; không phải chấm độc lập hoặc blind. Phạm vi chỉ
22 cặp; không xác nhận 500 cặp, coverage50query, chất lượng dataset hay hiệu lực
nguồn. Metadata reviewer chưa có; không dùng tên Git/Windows hoặc giờ chạy thay.

## Đầu vào, Git và bảo toàn

HEAD thực tế đầu phiên `f75ab698aa1dd3e8acb97d946916c55c8dc7e0b8`, Git sạch.
Đã đọc AGENTS, STATUS, handoff/rubric v5, rubric composition, evaluation contract,
template/crosswalk/proposal/detail và code validator thực tế. Không dùng SHA của
phiên7 làm HEAD hiện tại. Baseline **6.856 file** gồm file Git đang theo dõi,
raw/evidence, các dataset/index/evaluation/ZIP và review bundles được bảo vệ;
danh sách chính xác trong checks/preservation.baseline.json.

Nguồn template: `staging/subset-v5-relevance-002/calibration_submission.template.json`.
Review manifest SHA `25ad1481015179b782a466af9edb689e21d493a935202a57dfdc1bb938e73d2b`.
Dataset `vtls-subset-experimental.v5-candidate.1`; index `vtls-bm25s-subset.v1`.
Submission giữ nguyên toàn binding và IDs/query/record/proposal hashes của template.
Existing validator `src.subset_review validate` đã chạy exit0 trên bundle gốc.
Không load model/build index hoặc đổi query/ranking.

Handoff cũ yêu cầu gán độc lập; chỉ dẫn mới của người dùng nêu rõ AI hỗ trợ.
Áp dụng chỉ dẫn mới cho response mới và ghi provenance trung thực; không sửa
gói blind/contract/proposal/template cũ hoặc mô tả phản hồi này là độc lập.

## Bàn giao

Run mới **`staging/subset-v5-calibration-submission-001/`**, ngoài bundle cũ:

| File | Nội dung |
|---|---|
| submission.json | Shape template, đủ22items; label/reason nguyên văn, relation/completeness/evidence đã điền; reviewer_ref/reviewed_at=null |
| feedback.received.json | Xác nhận và22relevance/reason người dùng cung cấp; tách khỏi proposal |
| provenance.json | user_reviewed_ai_assisted, blind=false/independent=false, SHA inputs/response/feedback/evidence; giờ agent ghi hồ sơ riêng |
| evidence.used.jsonl | Quote/pointer/code-point offsets tương đối field, detail hash và file thật cho từng cặp; giữ source spans/cells trong detail cũ |
| comparison.jsonl / comparison.md | Bảng22cặp, query nguyên vẹn, citation, reason, proposal–response và trích evidence cần thiết |
| README.md | Cách mở và validate; metadata còn thiếu và điểm dừng |

Checks/log/private mutations/preservation:
**`staging/source-session8-checks-001/`**. Các private copies chỉ dùng negative
tests, không phải submission thật hoặc accepted labels.

## Kết quả nội dung

| Nhãn | Số cặp | Quan hệ/mức đầy đủ |
|---|---:|---|
| 2 | **7** | direct_target:1full,6partial |
| 1 | **6** | 2supporting_target,4dependency_only; tất cảpartial |
| 0 | **7** | unrelated/none |
| null | **2** | uncertain/uncertain; người dùng chủ đích giữpending |
| Tổng | **22** | Không thiếu/trùng Calibration ID |

**Bất đồng giữ nguyên:** `CAL-b69c61257d`, proposal2/direct_target/partial →
response null/uncertain/uncertain. Query vẫn là “Trong thành phố, đường hai chiều
không có dải phân cách thì tốc độ tối đa là bao nhiêu?”; không thêm giả định xe
ô tô hoặc đồng nhất thành phố với khu đông dân cư để ép nhãn2. Reason giữ đúng
người dùng: chưa xác định loại xe và phạm vi áp dụng; không dùng50km/h vô điều kiện.

`CAL-a46415f601` giữ null như proposal. Tổng21cặp không đổi bộ
relevance/relation/completeness,1cặp khác.20nhãn số có outcome=agree;2null có
outcome=uncertain, dù pending đã được người dùng xác nhận. Đây không phải lỗi
thiếu phản hồi. Không sửa proposal để giống response và không tính agreement
statistic như một phép chấm độc lập.

Relation/completeness/evidence do agent hoàn thiện theo nhiệm vụ, ghi rõ trong
provenance. Không suy người dùng đã mở từng file/pointer. Các nhãn2 về tuổi,
chế tài, bảng tốc độ/khoảng cách và câu so80/81 giữpartial, không tự nângfull.
`CAL-f3043beef8` là dependency_only: hàngV=60 nằm trong bảng/Điểma của closure,
còn own text nói khoảng cách khi điều kiện bất lợi. Ba dependency-only khác
được dẫn đúng căn cứ đèn đỏ, bảo lưu thi và mẫuXXVI; không gắn mức phạt sai lead.

## Kiểm chứng đã chạy

| Kiểm tra | Kết quả thực tế |
|---|---|
| Original sealed review validator | Exit0; template/crosswalk/query/detail/binding gốc hợp lệ |
| Filled response validator | technical_valid=true,22items,7/6/7/2; **exit2 đúng dự kiến** vì thiếu metadata |
| Unit/regression suite | **46tests pass,0skip**:11mới+8subset-review+9composition-review+18evaluation |
| Private negative mutations | **21/21 bị từ chối**; rehash wrapper khi cần để kiểm lỗi bên trong |
| Null, user reason và proposal difference | Giữ2null;22reason/label khớp captured feedback;1bất đồng được giữ |
| Evidence | Detail đúng record/hash, frozen query hash, native spans/cells/full-read binding, quote roundtrip và required-read role |

21mutation gồm: sai binding/query hash/record hash/proposal hash; thiếu/trùng/ID
lạ; thiếu hoặc dùng evidence record khác; enum sai; null→0; viết lại reason;
giảblind; duyệt tất cả từ mẫu; bịa reviewer/time; quote offset sai; dependency-only
chỉ cite own text; trùng evidence ledger; boolean thay integer relevance.
Logs ở `negative_checks.jsonl`, `tests.final.log`, `validation_report.final.json`.
Tests dùng fixture SYNTHETIC/FIXTURE; không tuyên bố chất lượng pháp lý/retrieval.

Validator mới **chỉ đọc/validate**, không nhập accepted hoặc tính metrics.
Nó tái dùng quote/template/manifest helpers hiện có vì blank-template validator
không phải validator cho bản đã điền; không nới hoặc sửa module hash-bound cũ.
Contract mới [submission v1](../design/Subset_V5_Calibration_Submission_v1.0.md).
Metadata hợp lệ cũng chỉ trả METADATA_COMPLETE_NOT_ADMITTED trong reader này;
scorer chunk-only v1 chưa là đường nhập typed table/whole-source v5.

## Metadata thiếu và bước tiếp theo

Chính xác hai field còn thiếu trong submission và captured feedback:

1. **reviewer_ref**: tên/mã tham chiếu người rà do người dùng cung cấp.
2. **reviewed_at**: thời điểm người dùng thực tế hoàn tất việc rà, có múi giờ.

`agent_recorded_at` trong provenance chỉ là lúc agent ghi hồ sơ04/11, không là
thời điểm người dùng rà và không tự điền sangreviewed_at. Chưa có attributed
reviewer event để nạp accepted labels theo contract. **Accepted imported=0**;
hai null pending; qrels cũ giữ nguyên, metrics=null, coverage approval=null/false.

Sau khi có hai metadata thực tế: tạo snapshot response mới ngoài seal, giữ
feedback/lineage/provenance AI hỗ trợ; kiểm lại binding và đường nhập typed
accepted annotations riêng cho20nhãn số. Hai null tiếp tụcpending. Không dùng
22cặp để duyệt500nhãn hoặc công bố metrics50query; còn cần completeness qrels
và coverage thực tế trước scorer. Không thêm yêu cầu xác minh pháp lý mới để
tiếp nhận relevance.

## Chạy lại và thay đổi

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_review validate --manifest staging/subset-v5-relevance-002/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_calibration --submission staging/subset-v5-calibration-submission-001/submission.json
# Exit 2: thiếu reviewer_ref/reviewed_at; xem technical_valid và missing_metadata.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_subset_calibration tests.test_subset_review tests.test_composition_review tests.test_evaluation -v
git diff --check
```

File mới được Git quản lý khi người dùng chọn commit sau này:
`src/subset_calibration.py`, `tests/test_subset_calibration.py`, contract bổ sung
và báo cáo này. STATUS được prepend hiện tại, lịch sử giữ nguyên bytes.
Staging response/checks không đưa vào Git. Không sửa old raw/evidence/run,
dataset/index/query/evaluation/qrels/ZIP hoặc thuật toán. Không tuning/rebuild,
embedding/UI/API, stage/commit/push. Preservation cuối và git diff check ở
`staging/source-session8-checks-001/final_preservation.json`.
