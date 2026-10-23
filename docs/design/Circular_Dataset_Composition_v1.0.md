# Dataset composition revision — quyết định trước triển khai

2026-10-23, snapshot2025-01-01. Giữ base draft v2-draft.1 và mọi payload
hash-bound nguyên byte. Thêm manifest `circular-composition.v1`, dataset
`vtls-coverage-experimental.v3-draft.1`; không đổi DDD/schema/validator v1.

Components: base draft3082 bất biến; TT35 graph revision có Part; TT38 source
graph/cells. Root text chunks vẫn chunk.v1; table records giữ table-retrieval.v1
và tr_ ID, không giả text_original. Membership gắn record type/ID với graph và
proof_base. Resolver mount ánh xạ logical source_proof_base_ref TT38 sang root
được đóng gói, không đổi payload/ID. TT35 proof tt35/ resolve tại component
priority root. Base membership tiếp tục resolve tại hai graph con cũ.

Tách target text, table retrieval, encoder contexts và required-read supporting
dependencies. Dependency bắt buộc để đọc đúng được bind subtree/source spans
cụ thể; consumer phải hỗ trợ required-read dependency và graph Part/table
records, nếu thiếu capability phải fail. Không tự ghép supporting vào encoder,
không đổi search/tokenizer/preprocessing/budget256. Không kỳ vọng search_text
một mình trả lời mọi chi tiết trong supporting record. Các biểu mẫu chưa có
biểu diễn phù hợp hoặc reference chưa hiểu đủ bị withheld, không chỉ cảnh báo.

Selection là agent technical disposition, không accepted scope/applicability.
Nguồn/edition/applicability pending không chặn experimental; bằng chứng ngoài
snapshot hoặc thiếu nội dung bắt buộc thì chặn. Điều kiện cá nhân giữ nguyên
trong luật; không đòi biết người dùng cụ thể. TT51/QCVN không nhập phiên này.

Build tái dùng experimental_draft.validate/copy_component và priority.validate.
Portable validator/read stdlib được đóng gói, không import repo hoặc truy cập
network. Kiểm inventory/chunks/graph/span/identity/proof/cells/budget/dependency,
selection replay, base exact preservation. Build/replay đầy đủ cần repository
đúng version và các tokenizer assets; validate/read chỉ Python stdlib.
Manifest ghi hash input/code/selection/mounts, consumer capabilities bắt buộc.
Không bỏ validator cũ hoặc gọi portable check thay xác minh pháp lý.
