# Scope proposal survey v1 — mở rộng có giới hạn từ coverage

Snapshot **2025-01-01**, origin=agent_review. Công cụ
`src.scope_survey build/validate`, policy **agent-scope-curation.v1**.
Chỉ tạo proposal phạm vi và nối coverage; không có CLI ra quyết định,
verified, promotion corpus hoặc thay đổi source/parser/chunker.

## Căn cứ và phạm vi cho phép

BRD §3.1/§3.2, SRS §1.2 và DDD §8 được chụp nguyên byte trong
requirements_snapshot. BRD tập trung quy tắc tham gia, GPLX/điểm GPLX và
vi phạm/xử phạt áp dụng trực tiếp. Quyền/nghĩa vụ của người lái được xét theo
nội dung và đối tượng thực tế. GPLX cá nhân khác giấy phép hoạt động cơ sở.
Điều kiện phương tiện/đăng ký/kiểm định chưa thành use case cam kết toàn
diện theo BRD §3.1: những ca chưa rõ giữ pending, không âm thầm mở rộng.
BRD §3.3 loại quy hoạch, xây dựng hạ tầng và quản lý vĩ mô.

BRD/SRS còn ghi snapshot mở; dùng 2025-01-01 theo quyết định đã chốt trong
DDD/Source Inventory/người dùng. architecture.md/scope.md là prototype,
không dùng số chunk hoặc bốn nguồn để suy tất cả nội dung đều included.
Contract Stage5A v1.1 và code pilot còn giới hạn 40/60 unit: yêu cầu mới đã
cho phép **mở rộng proposal**, không phải mở rộng quyền ghi decision.
Giữ nguyên validator/schema/các bundle pilot; không tăng max_units cũ hoặc
thêm enum chính thức chỉ để nạp dữ liệu chưa quyết định.

## Phương pháp tạo proposal

`config/scope_curation.v1.json` là danh sách **unit_id + unit_sha256 cụ thể**
được agent đọc own title/text và cha liên quan, kèm source quote, đối tượng,
lý do/tiêu chí BRD, review_scope và dependency field/target nếu có.
Danh sách được chọn có chủ đích theo các ca pilot, quy tắc/quyền người lái,
GPLX, chế tài và các nhóm coverage cần phân biệt với hạ tầng/cơ sở.
Đây không phải lấy mẫu ngẫu nhiên hoặc đánh giá ngữ nghĩa toàn bộ cây.

Runtime không có classifier từ khóa hoặc thuật toán truyền nhãn cha xuống
con; chỉ kiểm binding và dựng proposal từ danh sách đã ghi. Phần chưa đọc
có method=unassessed_inventory, reviewed_for_scope=false, scope pending.
Agent review cũng không phải quyết định người rà hoặc xác minh pháp lý.
Validator kiểm tính nhất quán hồ sơ, không chứng minh nhận định scope đúng.

Mỗi Điều/Khoản/Điểm có một hàng proposal hiện tại. Document/Chương/Mục ở
structural_roles.jsonl, không ép scope hoặc biến thành target thất bại.
Nguồn parser cách ly/bảng chưa có unit vẫn chỉ ở source_gaps của coverage,
không tạo ID hay proposal giả để bổ sung mẫu số.

## Hình dạng và liên kết

Mỗi proposal có law_id/unit_id/unit_sha256/citation/parent, scope_candidate,
đối tượng/lý do, method/policy, reviewed_for_scope, evidence_refs, source
spans, binding, snapshot và origin. Pending trong **lớp proposal này** ánh xạ
sang scope_candidate=null của assessment v1.1; không thêm pending vào enum
scope_status của DDD. scope_status, reviewer_ref, reviewed_at, ba decision_ids
và corpus_version đều null; review_status=pending, ready_to_load_ddd=false,
release_eligible=false. Hiệu lực và nguồn tách riêng, không suy từ scope.

Tái sử dụng assessment_contracts.SCOPES, DIMENSIONS, identity/canonical hash;
proposal_id=pr_ + SHA-256 canonical payload không chứa proposal_id. Đây là
ID hồ sơ staging, không đổi unit_id của DDD. Không tạo decision_event,
unit_assessment, DB chính thức hoặc hệ thống quyết định song song.

Binding mở rộng từ assessment v1.1 thật, gồm tree/parser/extraction/units/
spans/history/evidence trước, checksum coverage, curation và requirement
snapshot. Không chuyển binding DOCX sang PDF Điều 22. Cùng nội dung/config/
snapshot cho cùng proposals/IDs; built_at riêng trong manifest.

review_basis.jsonl tái dùng dạng source_span/project_requirement:

- Source span trỏ đúng normalized.txt của extraction Stage3, có extraction,
  unit/field, offsets Unicode code point [start,end), quote hash và locator.
- Requirement có bản chụp BRD, section, offsets trên **nguyên text UTF-8**
  của snapshot, quote/hash. Không trộn namespace này với extraction offsets.
- evidence_refs phải tồn tại trong catalog, own field có chữ phải có span.
  Quote curation khớp field của đúng unit; hash unit không lấy từ citation.

Hồ sơ HTML/PDF/findings/date rules/decisions cũ được giữ nguyên trong
coverage_snapshot/inputs/assessment, không giả rằng đã rà lại toàn bộ bằng
chứng hoặc xác minh lịch sử hiệu lực trong lượt scope. Nội dung DOCX có
spans không tự xác minh provenance hoặc tương đương bản chính thức.

## Target, context và cha hỗn hợp

Included hiện chỉ áp cho unit có own text, không có con, đã đọc nội dung.
Không tạo target từ đoạn dẫn cha có Điểm. Supporting chỉ có khi:

- Có target cụ thể với proposal included.
- Có context thực từ builder trong artifact coverage: field, offsets trong
  field, context order/role, unit IDs và source proof chính xác.
- Có spans và lý do cho phần được dùng. Không dùng toàn nhánh hoặc thêm
  các Điểm anh em/dẫn chiếu ngoài cây cha.

Supporting chỉ nói **own fields đã chọn**, không gán scope cho con. Cha có
nội dung/phạm vi hỗn hợp được ghi rõ mixed_parent=true và giữ pending,
vẫn liệt kê các field mà target cần. Context pending scope là việc nghiệp
vụ chưa kết luận, không tự gán thành lỗi source/structure của builder.
Không có dependency/target cụ thể thì không được dùng supporting để chứa
nội dung chưa chắc chắn. Evidence hiệu lực không mặc định là search context.

context_dependencies.jsonl nối chính xác context đã xuất cho preview và
quarantine bằng chunk_id→unit_id. source_locator_base_ref=coverage_snapshot/
cho biết gốc của các đường dẫn trong proof gốc, không sửa proof/offsets cũ.
source_span_artifact_ref trên proposal chỉ đến catalog spans của cây gốc.

## Lịch sử và bất đồng

Giữ nguyên machine_proposals.jsonl cũ trong snapshot. Proposal mới có
previous_proposal_ref gồm ID, artifact và canonical row hash. Không ghi đè
proposal trước, không dùng supersedes của decision cho proposal.
proposal_comparisons.jsonl phân biệt: unchanged, pending_to_conclusion,
conclusion_deferred, role_or_conclusion_changed. Bất đồng cần đọc lý do và
bằng chứng mới, không phải reviewer_override hoặc lỗi ràng buộc dữ liệu.
Lịch sử decision thật không được tự tạo/thay thế từ những thay đổi này.

Các ca Điều 22/ba Khoản, NĐ168 A6K1, A39K9 và Luật35 A84 có trong
priority_cases.md. Không sửa ký hiệu d/đ, tạo phần cách ly hoặc dùng hiệu
lực/kỹ thuật để tự ra scope. Chọn excluded do đối tượng cơ sở khác với
bị parser chặn; pending use case phương tiện khác với needs_fix kỹ thuật.

## Input, thống kê, validator và CLI

Nhận coverage-001 đã seal, chứa cây Stage4-005. Build chạy lại validator
coverage đầy đủ trước khi tạo run, từ chối output lồng trong input seal hoặc
run có sẵn. Sao toàn coverage/snapshots nguyên byte, requirement/config vào
run staging mới. Validate kiểm inventory/manifest/code/binding, replay
coverage với builder/tokenizer thật, rồi tái tính proposals/catalog/join/
summary/CSV/report từ input. Không đếm token mới bằng word count.

Ghép theo unit_id duy nhất và unit hash, không theo dòng/citation gần đúng.
Một unit có một proposal row hoặc role cấu trúc; tổng không mất/nhân đôi.
Per law/total thống kê included/supporting/excluded/pending, mức đã xét/chưa
xét, coverage của proposed included, token/unknown với mẫu số đo được và
dependency scope pending. Token chưa đo giữ null. Không gọi tỷ lệ là Recall
hoặc chất lượng retrieval. Có tối đa ba đề xuất ưu tiên, nhóm có thể giao
nhau; không cam kết mọi candidate đều khắc phục được/phát hành được.

Output: scope_report.md, scope_proposals.jsonl/CSV, structural_roles.jsonl,
context_dependencies.jsonl, proposal_comparisons.jsonl, review_basis.jsonl,
scope_coverage_summary.json, priority_cases.md, manifest và validation report.
CLI exit 0 = hồ sơ nhất quán kỹ thuật, không phải scope được duyệt; exit 1
= lỗi input/binding/evidence/replay. Không có lệnh approve/admit/index.
Lệnh thực tế và kết quả ở README/Stage5_Scope_Survey_Verification.md.
