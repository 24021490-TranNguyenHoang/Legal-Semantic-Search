# Rà relevance subset v5 — rubric/contract v1.2

Snapshot2025-01-01. Kế thừa nghĩa nhãn của Composition_Relevance_Review_v1.1
và evaluation contract v1; không migrate nhãn hay decision v1/v3.

- 2/direct_target: target chứa căn cứ thực chất trả lời một phần hoặc toàn câu;
  full/partial riêng. Một hàng đúng có thể 2/partial, không tự trả lời mọi hàng.
- 1/supporting_target: hỗ trợ/điều kiện còn thiếu, gồm context có nội dung thực;
  1/dependency_only: đáp án chỉ trong required-read của record được rank.
- 0/unrelated: đã đọc target/context/closure và không trả lời câu hỏi. Cùng từ
  khóa/chủ đề, sai loại xe/đường/tình huống không là positive mặc định.
- null/pending/uncertain: chưa kết luận do thông tin còn mơ hồ; không thành0.
  Source/edition/applicability pending chung giữ riêng; proposal chỉ xét nội dung
  hiện được đóng gói, không là kết luận áp dụng pháp luật tại snapshot.

Không đổi nghĩa0/1/2. Revision chỉ bổ sung whole-source, source proof và form
supporting của consumer v5: whole được đọc đầy đủ, không chấm một encoder view;
table source_original khác derived_text, giữ cell/header/row/điều kiện; supporting
form/source unit không thành ranked target. Không dùng bảng khô ráo trả lời trực
tiếp cho mọi tình huống mưa. Boundary tốc độ, loại xe, hạng GPLX và thời điểm phải
được ghi rõ. Chế tài có đoạn dẫn/ngoại lệ/modifier/transition trong closure.

## Binding, dispositions và evidence

Run mới từ index003/batch002/candidate006 đúng manifest/content/consumer SHA và
50query đã ghim. Mỗi cặp có ID thật, query hash (toàn object gồm batch_group),
payload hash, type, versions/input hashes, detail hash, native proof/DDD span/cell
và quote pointer. Offsets quote là code point tương đối field JSON được chỉ rõ;
không thay extraction offsets. Native proofs giữ extraction_id/file/hash/locator/
offset gốc và package_locator, không bịa span cho derived text hoặc QCVN regions.

Tái dùng composition_review.validate_pair_set/validate_annotation cho thang nhãn,
binding, date, pending/proposed và evidence. Facade chỉ thêm view có citation,
DDD spans/cells và full dataset_response nguyên trạng; không sửa dataset consumer.
Validator mới kiểm exact500cặp, actual consumer detail, used evidence/dependency,
read ledger, coverage50query, deep pool/annotations riêng và calibration binding.
Nhãn do agent ghi bằng bảng phán đoán từng cặp; assembler không dự đoán bằng
score/từ khóa, không default nhãn0 cho cặp bị thiếu. Không accepted/human events.

Mỗi proposal có reason/answered_part/missing_part/uncertainty, origin=agent_review,
reviewer_ref=null, recorded_at sự kiện ghi thực tế. Evidence phải có quote đúng
field và proof/dependency thuộc đúng record. Đọc shared unit một lần được dùng
lại cho các cặp, nhưng nhận xét query-record riêng. Không coi hydration/hash check
là tự động đọc rà nội dung pháp lý hoặc xác minh nguồn/hiệu lực.

## Coverage và deep survey

Coverage tách khỏi pair relevance: sufficient_content / partial_conditional /
no_matching_target_in_reviewed_subset / outside_membership_or_blocked /
query_ambiguous. Tách ranking miss, membership gap, thiếu required content,
ambiguity và legal status pending. Inventory138 và closure238 đã rà trong phạm
vi gói, không phải toàn raw/bảy nguồn. Source-only không nhận label/target giả.

Chọn tối đa15query và ghi lý do trước tìm sâu, dùng query gốc Top138 cùng index.
deep_run là retrieved pool, khác read ledger và khác outside proposals. Chỉ đề
xuất positive ngoài Top10 sau khi đọc/bind; không chấm toàn deep pool hoặc tuyên
bố completeness qrels. Ranking không thay đổi; metrics=null/accepted qrels rỗng.

## Calibration và seal

Khoảng10query/20–25cặp. Bản blind chỉ câu hỏi/nội dung/context/dependency/proof,
không rank/score/nhãn/lý do agent. Crosswalk và proposal riêng. Template có binding
và hash, reviewer/time/labels/reason=null, evidence_refs_used=[]; người dùng điền
bản sao ngoài bundle seal. Gán nhãn độc lập rồi mới đối chiếu agent. Duyệt mẫu
không duyệt500cặp/coverage hoặc nguồn. Không tự ghi acceptance từ "tiếp tục".

Inventory review mới dùng relative POSIX string sort; không sửa inventory/loader
BM25 hash-bound cũ. Lỗi Windows/POSIX order được ghi backlog riêng với runtime
CPython-minor/Unicode/pins. Mô phỏng đường dẫn không là thực nghiệm Linux.
Giữ raw/run/dataset/index/query/qrels/ZIP cũ; không tuning/rebuild/model/app/commit.
