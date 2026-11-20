# Phiên 15 — contract đối chiếu binding / review v6 v1.0

Contract `subset-v6-binding-review.v1`, snapshot 2025-01-01. Đây là hồ sơ review, chưa accepted v6, chưa metrics và không sửa schema DDD hoặc các adapter v5 hash-bound.

Ghim input bằng config/subset_v6_binding_review.v1.json. Tái dùng query_labels.validate_aggregate qua subset_evaluation.inputs (chỉ input validation, không gọi metric functions), pool_union, renderer và quote/rubric validators hiện có. Consumer v6 cấp gốc kiểm toàn nguồn/proof/closure; index và frozen batch kiểm binding/inventory, không search hoặc rebuild. Comparison phiên14 được tính lại từ payload sealed Top10, không đọc Markdown để suy rank.

Đối chiếu 53 accepted của đúng năm query; sáu accepted khác chỉ inventory; hai pending V3-D02 giữ ngoài scope. Pool là union Top10 v6, old accepted còn target, known accepted positives ngoài Top10; khử trùng query+record. Không lấy toàn diagnostic139, supporting/form/view làm target. Vai trò target dùng record_id, dependency dùng unit_id; không nhầm hai namespace.

Facets gồm payload, text_for_search, context, membership, required-read/supporting records, structural ancestors và resolved source proofs. Chỉ bỏ package_locator khỏi so sánh proof sau consumer đã xác nhận các file/hash/slice; giữ nguyên original locators, raw/extraction IDs/hash, Unicode offsets/quote. Class A khi các facets bằng nhau dù wrapper version/response hash khác; B cùng payload/context nhưng closure/evidence đổi; C mới hoặc payload/context/type/search đổi; D thiếu bằng chứng. Không tự chuyển nhãn vì phân loại này.

Bốn hàng bảng khoảng cách có source_proofs cấp ngoài rỗng theo payload hiện hành; proof nằm ở cells/source_slices/context. Validator packet kiểm riêng raw/extraction hash và từng cell slice trên text chuẩn hóa, không đòi một mảng proof giả hoặc xóa kiểm tra nguồn. Consumer chính thức vẫn kiểm toàn binding bảng/header/điều kiện. Text dẫn xuất khác nguyên văn owner; không giả span cho derived text.

Historical decision v5 giữ nguyên toàn object, reason, relation/completeness, evidence, reviewer metadata, provenance và receipt/row hashes. Proposal v6 origin=agent_review, status proposed/pending, human_review/reviewer_ref=null; không có accepted/qrels v6. A đề xuất xác nhận lại exact quyết định cũ; B tuổi giữ proposal partial, bổ sung evidence16reads để người dùng xem; C đèn đỏ proposal2/direct_target/partial theo own target+lead/7reads, không theo rank. Reviewer được đổi nhãn có lý do/evidence.

Gói có hai seal: review/manifest.json bảo vệ nội dung review; template ở ngoài review/ pin hash đó cùng pool/query/record/full-read/proposal hashes. Manifest gốc seal cả review, template và stdlib validator; ZIP SHA bảo vệ toàn gói. Không có vòng template tự pin chính manifest chứa nó. Chi tiết giữ nguyên package locators; source_assets.json ánh xạ sang proof_assets cục bộ, không sửa data response hoặc offsets.

Template mới không có reviewer_ref/reviewed_at/outcome/label/reason/evidence đã dùng. Nhóm A có danh sách exact pair IDs và quyết định cũ riêng; confirm_list chỉ khi người dùng xác nhận đúng danh sách và evidence_refs_used_by_pair đã đọc, không chứa B/C/D. Có thể chấm từng A thay vì xác nhận cả nhóm. Pending phải null/uncertain, không 0. Quyết định mới yêu cầu metadata thực tế, AI-assisted=true/independent=false/blind=false trong quy trình proposal-visible này; không dùng reviewed_at v5 như thời điểm xác nhận v6.

validate-response chỉ kiểm bản nháp ngoài bundle, trả accepted_created=0/import_supported=false, không phát sinh human event hoặc nhãn. Chưa triển khai admit v6 ở phiên15; đường nhập v5 không dùng được cho binding v6. Cần phản hồi thật và nhiệm vụ nhập nhãn riêng trước bước đó.

Validator repo replay nội dung từ consumer/input đã ghim và so tất cả bytes, chặn reseal giả. Validator stdlib trong ZIP chỉ integrity, binding và source/evidence/template/feedback checks; không thay thế replay từ source hoặc xác minh pháp lý. Replay xác định giữ agent_recorded_at đã capture trong config, không giả thời điểm người dùng. Giữ raw/dataset/index/query/labels/history/Hùng worktree; không ranking/model/metrics/stage/commit/push.
