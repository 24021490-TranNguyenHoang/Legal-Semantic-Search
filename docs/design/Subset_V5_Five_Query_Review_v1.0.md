# Phiên 9 — pool review hữu hạn cho năm query subset v5

Contract `subset-v5-five-query-review.v1`, 05/11/2026. Snapshot sản phẩm
**2025-01-01**. Kế thừa rubric v1.2 và contracts/accepted labels phiên7–8;
không đổi schema/payload đã seal. Không nhập nhãn hoặc gọi scorer.

Query cố định: dev-night_horn-3, dev-driving_age-2, dev-red_light-2, V3-D05,
V3-D07. Giữ nguyên toàn query object/hash, gồm batch_group. Config ghim cụ thể
review002, accepted002, dataset/index/query/batch phiên6–7 bằng SHA manifest.
Không chọn latest hoặc chạy retrieval/ranking lại.

Pool = union theo **query_id + record_id** của toàn Top10 đã ghim, accepted
hiện có và các outside positive có evidence của **đúng query** trong phiên7.
Mỗi nguồn giữ row SHA và provenance origin trong pool, không tạo target từ
supporting unit/form/encoder view. Deep_run không phải nguồn judgments/pool.
Khử trùng không làm mất các nguồn thành viên; cùng record ở hai query vẫn là
hai cặp khác. Pool không chứng minh đã tìm đủ mọi positive corpus.

Accepted kế thừa copy nguyên object trong `accepted.inherited.jsonl` với SHA
annotation gốc; giữ binding/label/relation/completeness/evidence/reviewer và AI
provenance. Không tạo receipt nhập hoặc qrels mới, không tính replay là nhãn mới.
Hai pending V3-D02 ở artifact phiên8 nằm ngoài năm query, giữ nguyên.

39phán đoán mới là bảng rõ từng cặp trong config, sau khi đọc target/context/
required-read; không default0 theo score/từ khóa hoặc suy pending pháp lý thành
null relevance. Chưa đủ nội dung có thể đề xuất null/uncertain. New proposals
có origin=agent_review, status=proposed/pending, reviewer_ref/human_review=null,
recorded_at của lần đọc đã ghi, prior_proposal_sha256 và quotes thực tế. Dùng
helper rubric/quote/native proof cũ và frozen dataset consumer đọc đủ nội dung.
Không load engine hoặc model khi chuẩn bị/validate lô này.

## Hai phần đọc riêng và template

- **A**: chỉ các cặp chưa accepted, xếp theo query/record ID, không rank/score/
  nhãn/reason đề xuất. Có nguyên văn/context, đúng type, bảng giữ row/header/
  cells; whole-source có text/dependency table. Trang evidence riêng giữ đủ
  required units/form/source locator và full detail. Không tóm tắt thay luật.
- **B**: bảng proposal riêng có relevance/relation/completeness, lý do ngắn,
  evidence pointers/quotes và phần chưa chắc. Không đưa nhãn B vào A.
- Mỗi phiếu tối đa20cặp, chia riêng theo query; phân trang không bỏ cặp.
  Manifest giữ toàn pool, kể cả accepted. Templates chỉ chứa cặp chưa accepted,
  có binding/pool SHA/pair ID/type/query/record/detail/proposal hash.
  reviewer_ref/reviewed_at/outcome/relevance/relation/completeness/reason và các
  field về phương pháp rà giữ null; evidence_refs_used=[] trước phản hồi thật.
- `proposal_consulted`, `ai_assisted`, `independent`, `blind` chưa biết giữnull.
  Nếu người dùng xem B khi rà, ghi proposal_consulted=true, ai_assisted=true,
  independent=false, blind=false; không tự chứng nhận independent/blind chỉ vì
  tạo được một phiếu không chứa nhãn.

Pair ID thuộc namespace review riêng, không đổi DDD unit/chunk identity.
Quote offsets tương đối field JSON; extraction offsets/locator nguyên trạng.
Đề xuất dependency-only phải cite required-read/embedded dependency đúng binding,
không lấy lead xử phạt của target khác làm đáp án. Bảng tách source original và
derived text; mọi header/cell/đơn vị/ranh giới/điều kiện giữ trong nguồn/detail.

## Validator và replay

CLI hẹp `src.query_review build/validate` tái dùng consumer/validators/helpers
cũ, không tạo evaluation framework/scorer khác. Kiểm input seals/hash và typed
accepted, đủTop10/union, query hash, evidence so với consumer thật, exact39manual
judgments và toàn bộ inherited decisions. Validate tái lắp ráp payload/phiếu/
templates rồi so byte; chặn cả artifact reseal bị mất cặp hoặc lộ nhãn/rank.
Replay cùng config/input giữ toàn payload/manifest giống byte; config lưu thời
điểm đọc đã ghi, không tự giả một sự kiện reviewer hoặc lần đọc pháp lý mới.

Progress tách accepted_inherited, unreviewed_by_user/user_decisions_pending,
agent_null_pending và coverage chưa đủ. Đề xuất không phải quyết định; agent
null=0 không có nghĩa không còn pending người dùng. Không có metrics hoặc
accepted mới và không suy legal verified từ validation.

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.query_review build --config config/subset_query_review.v1.json --run-dir staging/subset-v5-query-review-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.query_review validate --manifest staging/subset-v5-query-review-002/manifest.json
```

Mọi output vào run mới. Submission sau này phải ở ngoài seal và chỉ chứa quyết
định thực tế; phiên9 chưa triển khai/khởi chạy bước nhập feedback của lô mới.
