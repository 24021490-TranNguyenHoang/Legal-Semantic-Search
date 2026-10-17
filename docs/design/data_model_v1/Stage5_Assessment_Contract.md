# Stage 5A — contract assessment và pilot (assessment-pilot.v1.1)

**Bổ sung sau pilot:** mapping PDF Điều 22 có contract riêng
`Article22_PDF_Mapping_Contract.md`. Nó không giả làm bundle Stage 4 DOCX hoặc
tự chuyển quyết định/binding v1.1. Ba chiều vẫn độc lập; bốn đơn vị được chọn
có proposal và bản ánh xạ unit_assessment pending cho unit/hash PDF mới.
CLI assessment v1.1 hiện yêu cầu bundle Stage 4; adapter tiếp nhận hồ sơ review
PDF và promotion có kiểm soát chưa triển khai. Không đổi validator cũ để tự
chấp nhận PDF hoặc coi source/content matching là quyết định reviewer.

Snapshot cố định **2025-01-01**. Được phép làm assessment thử trong staging,
chưa mở rộng 4.000 đơn vị, sửa parser, tạo chunk/context truy hồi hoặc phát hành.
Đã đọc AGENTS, DDD §8/§13, schema/README trong ZIP, contract Stage 2–4 và
`staging/stage4-review-pack-001/`. Inference WinError 4551 vẫn chưa giải quyết;
Stage này không tải/chạy mô hình. Mốc dừng Stage 2–4 trong AGENTS là lịch sử.

## Căn cứ và giới hạn quyết định

SRS/SDD/DDD là đích thiết kế; architecture.md và scope.md mô tả prototype cũ,
không dùng số 1.457 chunk hoặc tên nguồn trong scope.md để quyết định scope.
SRS/SDD còn mốc mở, DDD/inventory/người dùng đã chốt 2025-01-01. BRD §3.1
ưu tiên quy tắc/GPLX/xử phạt trực tiếp; điều kiện phương tiện còn cần chốt bao
phủ. BRD §3.3 loại quy hoạch/xây dựng hạ tầng/quản lý vĩ mô. Đây là căn cứ
đề xuất, chưa phải ma trận scope từng đơn vị được người rà soát thông qua.
Các tệp căn cứ có hash và bản chụp trong requirements_snapshot của run.

Chưa có hồ sơ quyết định thực tế hoặc bằng chứng đầy đủ về lịch sử sửa đổi,
tương đương DOCX/bản ban hành, các văn bản đích của sửa đổi và toàn bộ dẫn
chiếu/chuyển tiếp. Không tự đặt yêu cầu pháp lý thay thế. Bản PDF mới tải
không khôi phục retrieved_at lịch sử của DOCX, không tự chuyển nguồn thành
verified. Các khoảng trống tiếp tục chặn phát hành. Có thể hoàn thành một chiều
quyết định phù hợp bằng chứng trong khi nguồn hoặc các chiều khác vẫn pending.

v1.1 thay contract v1 cho run mới; không ghi lại bundle/lịch sử v1. Validator
hiện hành kiểm v1.1 và code hash tương ứng; không tự chuyển event v1 gộp hai
chiều thành quyết định mới. Không mở rộng 40 unit pilot hoặc sửa schema DDD.

## Đầu vào và ràng buộc phiên bản

CLI `src.assessment_pipeline pilot` nhận ba manifest: Stage 4, review pack,
evidence; config chọn unit và yêu cầu lấy lát bằng chứng. Preflight trước khi
ghi output/DB: replay readonly Stage 4 và Stage 2–3/raw, kiểm sidecar/hash/files,
quan hệ review pack với bundle, quote bằng chứng và lựa chọn unit không trùng.
Tối đa 60 unit theo policy 5A; cấu hình thực tế chọn 40. Dataset fixture phải
khớp loại fixture của bundle; không trộn với luật thật.

Binding trên mỗi assessment/proposal/decision gồm hash manifest Stage 4,
parser version/tool code hash, hash toàn bộ legal_units và source_spans,
extraction manifest hash, review pack manifest hash, evidence manifest hash,
policy/config/findings hash. unit_id giữ nguyên DDD; unit_sha256 là SHA-256
canonical JSON của hàng unit, không cấp ID pháp lý mới. Snapshot luôn ghi rõ.
Bundle/parser/content/config/bằng chứng thay đổi thì quyết định cũ không tự áp
sang bản mới. Các snapshot input được sao nguyên byte, không sửa run gốc.

ID hồ sơ phụ dùng SHA-256 canonical JSON UTF-8 (sort_keys, không khoảng trắng),
tiền tố as_/pr_/dec_/find_/rule_/reg_/impact_/bind_. Đây là ID staging,
không thay công thức unit_id. Assessment ID khóa binding/unit/snapshot;
proposal/decision ID khóa toàn bộ payload. Quyết định mới tạo run mới.

## Ba lớp độc lập

| Lớp | Artifact | Ý nghĩa |
|---|---|---|
| Kỹ thuật | technical_impacts.pending.jsonl, regions.pending.jsonl | Vùng, locator/offset, own content/context, ảnh hưởng riêng từng đơn vị; không kết luận hiệu lực. |
| Đề xuất máy | machine_proposals.jsonl, date_rules.pending.jsonl | scope_candidate có thể null, ngày và applicability ứng viên, rule/finding và việc cần rà; không có reviewer/approved giả. |
| Quyết định thực tế | review_decision_history.jsonl, review_submissions.json | Chỉ từ submission bên ngoài có bằng chứng và người/thời điểm thật. Mặc định events/attestations rỗng. |

assessments.pending.jsonl liên kết ba lớp, không chép scope_candidate thành
scope_status. Chưa quyết định: scope_status=null, applicability_status=pending_review,
decision_ids có ba giá trị null. `no_direct_issue_observed_in_pilot` chỉ nói chưa thấy lỗi trực
tiếp trong phần lấy mẫu, không tuyên bố đơn vị hoặc nguồn đã đầy đủ/verified.
Own content và context có trạng thái riêng; không đồng nhất lỗi ký hiệu với
thiếu con hoặc việc một Điểm cần context của Khoản đang chưa đầy đủ.

Từ v1.1, thay `decision_id` đơn bằng `decision_ids` có ba khóa scope,
applicability, technical. Mỗi event chỉ chứa trường của chiều được rà:

| Chiều | Kết quả | Bằng chứng phù hợp |
|---|---|---|
| scope | included/supporting/excluded | Nội dung unit qua source_span và tiêu chí phạm vi dự án (BRD/inventory/DDD). Không bắt nộp kết luận ngày/hiệu lực. |
| applicability | Các enum DDD, mặc định pending_review | Bản chính thức có locator, lịch sử/ngoại lệ và đối chiếu nội dung; không ép chọn ngày của máy. |
| technical | pending/accepted/needs_fix/rejected | Source spans đúng unit, phạm vi đã rà ghi rõ title/text/spans/context; không xác minh nguồn gốc toàn file. |

`dimension_complete` ghi riêng tiến độ. Reviewer có thể kết luận needs_fix ở
kỹ thuật mà scope đã hoàn thành; kết luận hiệu lực cũng có thể đi trước scope.
`aggregate_status=pending` và ba cổng serving tiếp tục false vì upstream/corpus
chưa được tiếp nhận. Không đồng nhất hoàn thành review với dữ liệu được phục vụ.
Quan sát kỹ thuật máy giữ riêng trong technical; kết quả reviewer ở
technical_review_status. Không đổi quan sát máy thành quyết định thực tế.

## Theo dõi ảnh hưởng cụ thể

Review pack vẫn giữ 10 issue parser và 13 warning nguồn. Không resolve/chuyển
trạng thái những bản ghi đó. 9 vùng riêng ở assessment là 8 locator của issue
cũ cộng p[1059] chưa có issue riêng; không gọi đó là issue parser thứ 11.

| Ca | Liên kết cụ thể và quyết định kỹ thuật staging |
|---|---|
| NĐ168 A16K2 p[518–519] | Vùng chưa có unit; Khoản thiếu một số con. Những Điểm a/b/c giữ text riêng, có context_dependency_needs_review riêng; không tự đổi text/status con từ cha. |
| NĐ168 A39K9 p[1038] | Điểm đ còn unit/span, unit_present_with_structure_warning. Cha có child_designation_review, không tự khẳng định thiếu con. |
| NĐ168 A40K3 p[1057–1059] | Ba vùng cách ly; cha thiếu một số con; không bỏ p[1059] khỏi phạm vi rà. Các Điểm giữ lại có link context riêng. |
| Luật 35 A84K1/K2, tbl[2]/tbl[3] | unparsed_table_content_dependency ở đúng Khoản, extraction_region_without_unit cho bảng; không tạo con giả cho hàng/ô. |
| Luật 35 p[933] | Vùng text rỗng/non-body trước thông qua/chữ ký; không có legal parent, không gán vào A86K2 hoặc truyền lỗi ra toàn luật. |

Các link là đề xuất kỹ thuật pending, có lý do và blocks_roles riêng. Không
dùng một quy tắc chung suy toàn bộ trạng thái/hiệu lực cha–con hoặc loại cả
Điều/văn bản. Vùng chưa thành unit không được tạo assessment unit giả; nó có
region/context ID riêng. Đơn vị ngoài lựa chọn không được assessment hàng loạt.
Sáu context_review_links trong cấu hình pilot liệt kê chính xác từng Điểm,
context_unit_id, region_xpaths và lý do theo nội dung thực tế. Chúng chỉ yêu cầu
rà việc chọn context (blocks_roles=context), own_content_impact=not_observed;
không kết luận Điểm hỏng hoặc bắt buộc dùng toàn Khoản. Không có link được
khai báo thì parser issue ở cha không tự sinh link hoặc trạng thái ở con.

## Thu thập và định vị bằng chứng

CLI `src.assessment_evidence capture` chỉ nhận HTTPS trên allowlist chính thức,
kiểm cả redirect; lưu HTML/PDF nguyên byte, URL đầu/cuối, HTTP headers/status,
request_started_at/accessed_at UTC thực tế, size/SHA-256 và inventory trang.
Hash evidence ID khóa law_id/URL/byte hash, không phải dấu chứng thực pháp lý.
Thời điểm truy cập là thời điểm chạy tải mới, tách ngày ban hành/hiệu lực.
Không sửa Stage 2 để bù retrieved_at còn thiếu. Cần run mới cho mọi lần tải lại.

PDF giữ bản gốc, text từng trang bằng pdfplumber (tool/version), NFC/LF.
Lát text có page/text_ref/hash, offsets Unicode code point [start,end) trên
đúng tệp trang, quote/hash và legal_locator. Các offsets này khác offsets trên
normalized.txt Stage 3; namespace/text_ref được ghi rõ. Không gán offsets ảnh
thành offsets chữ. PDF NĐ168 scan không lấy text: observations là quan sát máy
theo trang, có PNG render để người rà mở; không OCR hoặc giả bản chép nguyên văn.

Capture để historical_status=pending_review; chưa kiểm chữ ký số, đủ phần,
tương đương nội dung DOCX hay toàn bộ sửa đổi trước snapshot. Metadata website
hiện tại hoặc ngày chung không chứng minh lịch sử cho từng đơn vị. Evidence
review ghi edition ứng viên là PDF Công báo/bản ký số được trang Chính phủ
liên kết; chưa có kết luận chấp thuận bản đó làm corpus. Không dùng bản hợp nhất
2026 làm luật năm 2025. Các slice có thể chỉ bao phủ một trang của điều dài;
ghi rõ phần còn phải đọc, không tuyên bố rà toàn bộ.

## Ngày, ngoại lệ và scope ứng viên

Ngày pháp lý ISO YYYY-MM-DD có kiểm ngày thật; hiệu lực theo khoảng
effective_from <= snapshot < effective_to. Cận trên exclusive; null không phải
bằng chứng hiệu lực vĩnh viễn. Rule máy có đơn vị đích liệt kê rõ, priority,
finding_id/evidence_ids, ngày ứng viên và trạng thái pending. Ngoại lệ ưu tiên
hơn ngày chung khi máy đề xuất. Xung đột cùng priority được ghi vào
date_rule_conflicts, ngày ứng viên để null; reviewer có thể giải quyết bằng
bằng chứng. Rule/priority máy không phải ràng buộc bắt buộc cho quyết định.

Pilot ghi riêng L36 A88K2 → A10K3 ngày 2026-01-01; L35 A85K2 → A84K1 ngày
2024-10-01. Ngày chung chỉ là ứng viên cho các unit ghi rõ; không xác minh
applicability hoặc truyền ngày theo cây. NĐ168 A53K2 còn ngoại lệ cho các đơn vị
ngoài pilot, một ngoại lệ khí thải không có ngày cố định: chỉ ghi nhận nội dung,
không triển khai đánh giá chúng. Điều 54 liên quan thời điểm hành vi, không chỉ
một ngày. Ngày truy cập/verified_at không thay ngày hiệu lực.

Scope included/supporting/excluded tách applicability. Nhóm quy hoạch/hạ tầng
có đề xuất excluded theo BRD; không coi đã hết hiệu lực. Điều kiện phương tiện,
đăng kiểm hoặc bảng sửa đổi có scope cần xem riêng. Chưa có ma trận reviewer
thông qua, mọi scope_status của pilot vẫn null.

## Hồ sơ quyết định và lịch sử

`--decisions FILE.json` nhận `{ "events": [...] }`. Chỉ dùng quyết định thật do
người rà cung cấp; mặc định events rỗng. Giữ byte input ở
external_review_submission.input.json và JSON chuẩn hóa. Không cần bản attestation
lặp payload, chữ ký mật mã hoặc hệ thống phân quyền mới để ghi quyết định.

Trường chung: decision_id (dec_ + SHA-256 canonical payload bỏ decision_id),
unit_id/unit_sha256, dimension, binding, snapshot_date, supersedes, reviewer_ref,
reviewed_at UTC thật, decision_note, record_origin=external_review_submission,
evidence_ids/finding_ids, proposal_id, proposal_relation và override_reason.

- dimension=scope chỉ thêm scope_status; không buộc có effective_from hoặc
  historical_basis khi đang quyết định phạm vi dự án.
- dimension=applicability thêm applicability_status, effective_from/to,
  historical_basis, historical_review_note, content_comparison_note. Khi kết luận
  khác pending_review phải có căn cứ chính thức và ghi rõ rà bản/lịch sử.
- dimension=technical thêm technical_review_status và review_scope_note.
  Chấp nhận kỹ thuật của nội dung được rà không tự chuyển extraction/source verified.

review_basis.jsonl tham chiếu các bằng chứng đã có: finding chính thức; source
span có unit/locator/offset/hash; tài liệu phạm vi có path/hash/section. Không
nhận ID tự khai mà thiếu artifact đã kiểm. Các tài liệu phạm vi được chụp nguyên
byte; spans được Stage 4 kiểm và replay. Reviewer ghi bằng chứng theo chiều,
không bắt mọi quyết định phải dựa một date_rule được máy sinh.

Lịch sử supersedes theo **(unit_id, dimension)**. Event scope không thay event
applicability; ba event đầu có thể đều supersedes=null. Sự kiện thay thế phải
đúng cùng unit/chiều và thời gian không trước event trước. Binding/hash/snapshot
sai, evidence thiếu, ngày không hợp lệ hoặc trạng thái trái khoảng ngày vẫn là
lỗi dữ liệu và bị từ chối. Không tự chuyển quyết định khi unit/input thay đổi.

proposal_relation=accept/override/defer. Khi khác scope hoặc ngày/status đã được
máy đề xuất, phải ghi override và override_reason, liên kết bằng chứng cụ thể.
Không âm thầm bỏ qua ngoại lệ: người rà phải giải thích vì sao đề xuất/rule đó
sai hoặc không áp dụng. Bất đồng được lưu ở proposal_conflicts.jsonl với
reviewer_override, không bị coi là lỗi ràng buộc. Không sửa code/policy cho từng
bất đồng có căn cứ. Validator kiểm hồ sơ/logic ngày, không tự chứng minh kết luận
pháp lý của reviewer là đúng. Giữ proposal cũ và event mới để đối chiếu.

Timestamp review không được trước capture bằng chứng đang trích; hồ sơ thu thập
sớm hơn phải có artifact riêng, không bịa ngày. Không xác thực chữ ký số hoặc
xây hệ thống phân quyền trong bước này. Reviewer/thời điểm/bằng chứng/lý do thật
vẫn cần theo DDD; các giới hạn chữ ký/danh tính không phải cổng mới của bài tập.

## Pending SQLite và ánh xạ DDD

Schema chính thức giữ nguyên byte từ ZIP. `assessment.pending.sqlite` dùng DDL
riêng dưới schemas/assessment_v1, không tạo corpus/legal_document/legal_unit
chính thức giả. Bảng binding, pending_subject/evidence/region/impact/proposal/
decision_event/assessment có FK, UNIQUE, JSON hợp lệ; mọi connection bật FK.
Validator mở readonly/query_only, kiểm integrity/FK, schema SQL và đối chiếu
từng hàng JSON với export/replay. Có JSON Schema riêng cho assessment pending.

ddd_mapping.pending.jsonl chuẩn bị đủ trường unit_assessment. Chưa có corpus:
corpus_version=null; scope chưa quyết định=null; ready_to_load=false. Không
nhập chúng vào DDD, không thay bằng excluded hoặc nới NOT NULL. Về sau cần
nguồn/extraction/cây được rà thật, corpus và thành viên thật, quyết định/evidence
hợp lệ, xác nhận dependency/context, rồi cấp corpus_version thật và chuyển
verification_ref sang artifact quyết định/bằng chứng theo quy ước corpus.
verified_at/reviewer_ref chỉ lấy từ quyết định applicability thực tế; decision_note và dimension_decision_refs liên kết các chiều đã rà. Scope có thể hoàn thành trước khi nạp DDD; không điền null thành excluded giả.

Stage 5A không triển khai promote/activate. Cổng target/context luôn đóng với
nguồn/cây pending và corpus chưa tồn tại, kể cả nhập một decision đúng hình
dạng. Candidate exports phải rỗng; validator replay phát hiện cả việc chèn unit
rồi tính lại manifest hash. Mọi row giữ blockers, target/context/release=false.
Không tạo context truy hồi; context_dependency là quan hệ rà soát.

## CLI và kiểm tra

Lệnh tái chạy ở README và Stage5A_Verification.md. Các subcommand: evidence
capture/validate; assessment pilot/validate/candidates --role target|context.
Mọi đầu ra dưới run staging mới; thiếu input/hash/version/decision sai trả khác 0.
Import không IO/network/model/database. Validator replay unit/proposal/impact/
decision/mapping và DB; sidecar/hash không tự chứng minh pháp lý hoặc chống
người có quyền sửa toàn bộ chuỗi tin cậy. Giữ manifest hash để đối chiếu bên ngoài.

Cùng bundle/config/findings/evidence/submission cho cùng hồ sơ semantic/ID;
built_at/run report khác thời điểm. Tải lại website có thể đổi HTML/PDF và thời
điểm capture, nên là binding mới. Kết quả kiểm kỹ thuật không thay rà soát pháp
lý. Dừng sau pilot Stage 5A; chỉ mở rộng/sửa cây khi có yêu cầu tiếp theo.
