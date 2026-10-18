# Pilot refinement v1 — context theo field và proposal có phạm vi

Phiên bản `pilot-field-refinement.v1`, snapshot **2025-01-01**. CLI
`src.pilot_refinement build/validate`, annotation
`config/pilot_refinement.v1.json`. Chỉ 107 target có proposal included từ
scope-survey-001; không mở rộng đánh giá corpus, sửa parser/builder/encoder
hoặc schema DDD. Scope/technical/applicability của reviewer vẫn độc lập và
pending theo assessment v1.1. Sidecar này không thêm tầng phê duyệt.

## Input và bảo toàn

Input là manifest scope-survey-001, đã kiểm scope/coverage/Stage4 cùng source
snapshots. Build preflight bằng validator cũ trước khi tạo run, từ chối input
sai hoặc output lồng trong input đã seal. Mọi output vào run staging mới;
giữ scope_snapshot nguyên byte cùng toàn bộ lịch sử/bằng chứng. Config khóa
manifest, unit_sha256 và proposal_id/canonical hash trước. Không viết lại
config/code/run cũ để hợp thức hóa thay đổi proposal.

Tái dùng builder Khoản/Điểm lá, source_proof, identity và search_components
hiện hành. Replay 107 target trong memory, dùng **số đo encoder cũ đã được
upstream replay**, kiểm exact chunk IDs/nội dung/source proofs/context.
Không gọi cached measurements là số đo tokenizer mới. Chỉ ca unknown được
tokenize lại riêng, cùng model/revision/PyVi/assets/packages/config cũ.

## Context field review

Đối tượng là 42 dependency rows của 35 target từ 9 field cha pending. Mỗi
row khóa target_unit_id/hash, context unit/hash, field, offsets trong field,
context order/role và bằng chứng nguồn. Annotation author ghi thông tin
field cung cấp (subject/topic/condition/legal effect/penalty), lý do và
selection_proposal: use, needs_more_review hoặc do_not_use. Run này có đúng
một field đã chọn trên mỗi cha; chưa hỗ trợ tự mở rộng cấu trúc annotation.

Lưu đầy đủ field_text, target_text, citation, source_locator và gốc đường
dẫn **scope_snapshot/coverage_snapshot/**. Source proof giữ span/extraction/
raw IDs/hashes, locator và Unicode offsets đã roundtrip. Không thay proof,
đoán số, lấy Điểm anh em hoặc ghép dẫn chiếu ngoài cây cha.

`use` chỉ đề xuất dùng field cho target cụ thể. Không đổi scope toàn cha,
gán nhãn xuống con hoặc làm nguồn/cha verified. Cha pending không tự chặn
field đã được agent đánh giá phù hợp. Target scope cũng không tự đổi vì
field phù hợp. `needs_more_review`/`do_not_use` giữ toàn candidate/context,
không bỏ field để token pass; context_selection_proposal của target yêu cầu
xem lại. Các context khác giữ proposal supporting và bằng chứng trước;
không tự ghi chúng thành reviewer technical acceptance.

## Rà proposal và danh sách thử nghiệm

Agent đọc đầy đủ 107 target và context thật, ghi riêng từng unit: đối tượng,
behavior_right_duty, UC BRD, lý do target hay pending, giới hạn dẫn chiếu và
chất lượng lý do trước. Annotation là danh sách ID/hash rõ ràng, không phải
classifier từ khóa. Lý do cũ theo nhóm + trích ngắn được giữ nguyên trong
snapshot, không dùng test đạt thay đánh giá nội dung.

scope_proposal_revisions chứa mọi proposal giải thích lại, cả khi nhãn giữ
nguyên; mỗi row có proposal_id mới theo hàm identity của assessment v1.1 và
previous_proposal_id/hash/ref. scope_label_relation tách giữ nhãn với đổi
nhãn; không nhầm số proposal payload thay đổi với số scope thay đổi.
Chưa đọc đủ chỉ có thể giữ pending, không claim included. Unit/legal IDs,
nguyên văn/spans/chunk/context/search/hash vẫn nguyên trạng. Không có event
reviewer hoặc supersedes decision mới.

pilot_candidates giữ đủ 107 hồ sơ thử nghiệm, không chỉ danh sách included.
Mỗi row tách scope proposal, khả năng chunk/quarantine, token/unknown,
context field proposal, source evidence đang pending, technical review còn
thiếu, applicability còn thiếu, evidence cũ có thật và công việc tiếp theo.
Prior finding/date_rule là liên kết tới hồ sơ cũ, không phải mọi finding
pilot đều xác minh riêng unit đó. Ngày hiệu lực và reviewer null; không có
trạng thái ready hoặc quyết định phục vụ thay các cổng DDD.

Quy ước đường dẫn trong candidate: `source_proof_base_ref` tính từ run mới
và dùng cho source proof của target/context. `context_dependencies` giữ
nguyên các row lịch sử của scope survey; `source_locator_base_ref` bên
trong những row lịch sử này tính từ **scope_snapshot/**, không phải từ run
mới. Vì vậy `scope_snapshot/` + `coverage_snapshot/` + `inputs/...` trỏ
đúng raw/extraction được giữ nguyên. Field review mới ghi trực tiếp base
`scope_snapshot/coverage_snapshot/`. Không đổi JSON lịch sử để rebase nó.

BRD/SRS còn snapshot mở, áp dụng 2025-01-01 theo DDD/Inventory/người dùng.
Không mở use case quyền dịch vụ vận tải/historical search hoặc phạm vi
phương tiện chỉ vì unit có chữ giao thông/GPLX. Proposal pending của các ca
thủ tục/dẫn chiếu không phải kết luận vô hiệu hoặc ngoài phạm vi vĩnh viễn.

## Unknown và các lớp offset

Ca Luật36 A62K5c tokenize lại toàn text_for_search, cùng cấu hình document
v1 dùng chung query. So từng trường kết quả mới với evidence encoder cũ.
Giữ before, whitespace_only và after như phép chẩn đoán; chỉ after là đầu
vào encoder hiện hành, không dùng probe thay policy để ép unknown=0.

Tokenizer slow không có native offset_mapping. Chỉ dùng source fragment
khi regex/BPE replay và token IDs khớp chính xác theo encoder_input hiện
hành. Piece trả ID unknown được so với vocabulary thật trong asset đã pin.

Mapping encoder → search **có điều kiện**: source đã NFC, không có underscore
nguyên gốc; chuỗi ký tự không-whitespace của source phải bằng toàn chuỗi
encoder sau bỏ whitespace và underscore thêm. Khi bằng nhau, ghép vị trí
ký tự theo đúng thứ tự toàn chuỗi; underscore thêm không có offset nguồn.
Không thỏa điều kiện thì mapping unavailable, không đoán inverse segmentation.
Phương pháp này chỉ là chứng minh offset chẩn đoán, không tiền xử lý mới.

search_components xác định component bằng offsets ghép thật. Chỉ thực hiện
mapping vào extraction cho component target text_original trong lượt hẹp
này: trừ offset component → field positions → spans + LF join. Không lấy
offset encoder làm offset extraction hoặc gán metadata luật/citation vào
nguồn khi không có chứng minh. Tất cả là Unicode code point từ 0; ranges
[start,end), token position từ 0 gồm BOS/EOS.

Giữ unknown nếu còn, không sửa chữ/dấu/phủ định, vocab/model hoặc segmentation.
Kết quả tokenizer không chứng minh ảnh hưởng ngữ nghĩa/retrieval; thay policy
chỉ có thể là đề xuất thử nghiệm riêng với query/document và version đồng bộ.

## Output, validator và giới hạn

Output: pilot_refinement_report.md, context_field_reviews.jsonl,
scope_proposal_revisions.jsonl, unknown_diagnostics.json/MD,
pilot_candidates.jsonl/CSV, priority_cases_fulltext.md, manifest và
validation_report.json. Bản fulltext chứa trọn target và mọi context của ba
ca dài, ca unknown và ca scope đổi/pending, có unit IDs/citation/locators.

Validator kiểm inventory/sidecar/code, replay input scope/coverage, builder
107 target, field binding/proof/order, annotation/previous proposal, joins,
summary và mọi export/readable view. Unknown chạy tokenizer thật lại, không
mock. Exit 0 chỉ hồ sơ nhất quán kỹ thuật; exit 1 lỗi input/binding/evidence/
replay. Scope vẫn là đề xuất agent, nguồn/hiệu lực chưa được xác minh.

Fixture synthetic tách riêng. Không thêm framework, cổng duyệt, phân quyền,
chữ ký số, split dài, OCR/parser, embedding/index hoặc sửa ứng dụng.
Lệnh và bằng chứng thực tế ở README/Stage5_Pilot_Refinement_Verification.md.
