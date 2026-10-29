# Phiên 3 — source selection và membership proposal v1.0

Snapshot 2025-01-01. Lựa chọn nguồn lấy trực tiếp từ chỉ dẫn người dùng phiên3;
đó không phải human review nội dung/hiệu lực. `origin=user_instruction` chỉ dùng
cho source selection; scope/membership mới có `origin=agent_review`, không accepted,
reviewer_ref/human_review=null, release_eligible=false. Không tạo dataset/index.

Ghim đúng manifest/file/hash/extraction/source-set. Inventory theo từng unit của
bảy graph, kể cả ngoài candidate v4. Tách role target/supporting/structural,
scope in_scope/out_of_scope/unresolved, technical ready/blocked và membership
proposed_include/supporting_only/pending/excluded. Unit chưa đọc có review_method
unassessed_inventory và unresolved; không gán excluded qua keyword hoặc cha.
Scope cũ chỉ reuse khi unit ID/full payload hash và nguồn còn đúng; ND168 source
mới không nhận assessment cũ. Rà mới theo danh sách unit/hash/field/context hữu hạn.

Proposal là kế hoạch membership, không thành viên corpus. Unit có scope phù hợp
nhưng chưa có record/proof/context đúng nguồn phải pending với blocker riêng.
Supporting chỉ được chọn khi có target và dependency cụ thể, không tính thành
target. Encoder view không là record pháp lý độc lập. Graph ancestors được giữ
để cấu trúc, không tự thành target hay suy scope xuống con.

So sánh v3 và v4 riêng. Crosswalk ND168 phiên1→2, nhánh stage4 cũ và HTML là ba
phép mapping khác nhau. Mapping khác branch dùng legal path duy nhất, kiểm loại,
designation, parent và so nội dung; ghi khác biệt, không tự chuyển assessment,
proof offsets hoặc qrels. Bản nhánh cũ không có proof mới thì chỉ là lineage.

## TT35: đính chính dependency có bằng chứng

Ảnh raw PDF trang8 và graph A7K2a dẫn **Phụ lục II**, trái mapping AnnexIII trong
tt35-owner-tables-002. Không sửa run/code hash-bound phiên2. Adapter hữu hạn dùng
compose/read_record/encoder_views hiện có, thay dependency theo sidecar có source
span + ảnh. `table-owner-retrieval.v1` vẫn giữ nguyên identity recipe: dependency
payload đổi thì record ID đổi. Encoder text/token IDs không đổi; wrapper view ID
đổi vì bind source record SHA mới. Legal unit IDs và bảy owner khác giữ nguyên.
Consumer khai báo whole-owned-table/physical-cell/bounded-dependency capabilities,
trả toàn record và dependencies. Thiếu capability/dependency/header/cell/proof
phải fail. Không fake bảng thành chunk.v1, không coi technical pass là scope.

Scope tám owner được rà riêng theo đối tượng/nội dung; chương trình đào tạo,
huấn luyện sát hạch viên không tự thành quy tắc tham gia giao thông. Dependency
được kiểm cả khi owner cuối cùng đề xuất excluded; giữ để tái dùng có căn cứ.

QCVN Công báo ưu tiên theo từng vùng; Antiword không thay toàn PDF. Ba subtree
đã có record cần đọc trọn, không tự chọn sáu recovery region hoặc11dòng B18 làm
target. Caption I.418/I.416 blocked membership thống nhất. 4.1 áp đính chính lỗi
agent transcription; không gắn cờ xung đột nguồn cho câu này.929dòng chưa gắn
owner tiếp tục pending ngoài phần có bằng chứng mới. Image-only không đủ nghĩa
cho target chỉ vì đã có ảnh hoặc OCR draft.

Validator kiểm source selection/hash/proof, graph/source spans, ND crosswalk,
record/dependency binding, stale source IDs, duplicate legal target qua DOCX/HTML,
capability và target/view separation. Replay so payload deterministic, timestamp
technical riêng. Raw/artifact/SQL/code hash-bound cũ giữ nguyên byte.
