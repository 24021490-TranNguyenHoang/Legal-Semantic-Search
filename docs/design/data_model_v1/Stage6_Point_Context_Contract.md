# Stage 6 — Điểm lá và context từ Điều/Khoản

Policy **leaf-clause-point-context.v1**, snapshot **2025-01-01**. Chỉ preview
pending, origin=agent_review. Đây là phần mở rộng đã được người dùng cho
phép, không phải quyết định source/scope/applicability hoặc reviewer.

## Builder và policy

`src/chunk_preview_v2.py` nhận cùng dữ liệu units/quan hệ/files/extractions/
spans như v1, thêm **inventory issue đầy đủ** của parser/coverage/extraction.
Config quy định target IDs, fields bắt buộc ở Điều/Khoản, token budget và
phiên bản policy. Không có mã luật, số Điều hoặc mức phạt cố định trong builder.

| Target | Context theo context_order tăng liên tục |
|---|---|
| Khoản không có con | Title Điều → text_original riêng Điều nếu có |
| Điểm không có con | Title Điều → text_original riêng Điều nếu có → text_original riêng Khoản cha |

Target luôn là toàn bộ chữ riêng text_original, offsets [0,len(text)).
Context dùng nguyên field cha; không lấy text của Điểm anh em hoặc sao toàn
nội dung con vào cha. Không suy số tiền, phương tiện, chế tài/điều kiện từ
từ khóa. Khoản có Điểm không được tạo target chỉ từ câu dẫn mức phạt.
Các loại target khác hoặc có con trả UNSUPPORTED_STRUCTURE.

Field rỗng theo cây hợp lệ có thể bỏ qua khi policy không bắt buộc. Field
có chữ luôn cần spans và nguồn, dù policy không bắt buộc field đó. Thiếu
key/cha, cha sai cấp/văn bản, cycle/ID sai, thiếu spans, sai hash/slice phải
phát issue; không tự thêm đơn vị hoặc diễn giải nội dung bị thiếu.

Mỗi context giữ unit_id, field_name, offsets trong field, role heading hoặc
lead_in, context_order và source_locator gồm file/extraction/span IDs,
locator, extraction offsets, text/quote/raw hashes. Nhiều spans dựng lại
bằng LF theo DDD; mọi nguyên văn và offsets nguồn giữ nguyên.

## Ảnh hưởng issue, không suy verified

Builder yêu cầu khóa issues, không coi thiếu inventory là không có lỗi.
CLI nhập đầy đủ parser issues, coverage needs_review/unparsed, warning Stage 3.
Warning Stage 3 được nối locator với trace chính xác để lấy ranges; không
tự suy vị trí ký tự từ số paragraph hoặc nội dung câu.

Một target bị chặn khi issue:

- Nêu trực tiếp unit/affected_unit_ids của target hoặc context.
- Giao với source slices đang dùng, gồm vị trí zero-width chưa giải mã.
- Nằm trong vùng target hoặc vùng mở đầu Điều, hoặc vùng cấu trúc Khoản
  chứa Điểm đang chọn. Ranh giới được đo từ heading/spans thực đến cấp ngang
  hoặc cao hơn kế tiếp; không tạo nội dung hoặc đơn vị mới. Xung đột con
  cùng Khoản có thể làm citation/đánh số không chắc chắn dù lead còn nguyên.
- Có cùng extraction nhưng không đủ thông tin giới hạn vị trí/part: chặn
  vì chưa chứng minh không ảnh hưởng. Part phụ riêng đã xác định không tự
  gắn vào thân luật.

Không truyền mọi warning ở Điều/Khoản khác xuống toàn cây. Dependency/range/
part được ghi riêng trong dependency_checks.jsonl. Issue ngoài vùng vẫn
giữ trong source_inspection/input snapshot, không resolve hoặc đánh verified.
Missing/unresolved target/context trả PARSER_OR_EXTRACTION_ISSUE_IMPACT;
source/quan hệ sai trả INVALID_RELATION_OR_SOURCE.

Câu dẫn chiếu được giữ nguyên; không tự truy tìm/ghép nội dung đơn vị khác
ngoài cây cha. CROSS_REFERENCES_NOT_EXPANDED ghi giới hạn của preview, không
đặt thêm quy trình duyệt thủ công hoặc tuyên bố đã đủ mọi context pháp lý.

## Encoder, budget và identity

Dùng nguyên `encoder_input.encode_inputs`, preprocessing phobert-pyvi-input.v1,
model/revision/assets/packages của run Article22 Stage6-002. Đếm đúng
encoder_text có special tokens; không đổi model, truncate hoặc bỏ context.
Ngưỡng là min(preview token_limit, model_max_tokens), hiện cùng là 256.

Vượt ngưỡng: candidate/context nguyên vẹn ở quarantined.preview.jsonl,
encoder input giữ theo chunk_id, có TOKEN_BUDGET_EXCEEDED. Không nằm trong
chunks.preview.jsonl hoặc contexts.preview.jsonl sẵn sàng. Bản dễ đọc vẫn
hiển thị cả candidate bị quarantine và nguyên nhân.

Giữ công thức chunk.v1/content_sha256 DDD; không đổi schema chính thức.
Policy mới tạo ID mới khi chunk_policy_version khác, kể cả nguyên văn và
context không đổi. Hồi quy Điều 22 so payload từng trường, chỉ chấp nhận
khác chunk_policy_version; không cập nhật expected ID tùy ý. Content hash
vẫn trên text_for_search, không thay bằng hash encoder_text.

Builder/CLI/encoder v1 được giữ nguyên byte vì code hashes trong run cũ.
V2 dùng lại source_proof và chunk_identity của v1; không nạp Điểm bằng cách
giả thành Khoản hoặc tạo parser/unit mới. Không có framework/plugin mới.

## Pilot và artifact

CLI `src.points_preview build/validate`, config `config/stage6_points.v1.json`.
Pilot chọn đúng năm Điểm thật thuộc Điều 6 Khoản 1 NĐ168 Stage4-005, có cha
document/Chương/Mục/Điều/Khoản thật. Đoạn dẫn Điều 6 rỗng hợp lệ; title Điều
và lead Khoản có spans. Giữ DOCX legacy/provenance/extraction/cây pending.
source_url trong preview là **candidate inventory**, không phải URL tải
DOCX đã xác minh. Điều này được ghi rõ trong inspection và bản dễ đọc.

Run mới giữ snapshot Stage4/Stage6, raw và inventory theo byte/hash thực
để upstream validator replay được, không sửa old run. Có chunks/contexts,
encoder_inputs, issues/quarantine/unit_results/dependency_checks JSONL,
chunks_preview.md, source_inspection, Article22 regression/comparison,
manifest và validation report. Metadata corpus/effective dates=null,
applicability_status=pending_review, release_eligible=false; không assessment.

Validator full replay upstream, policy/config/pins, IDs/spans/context/search/
encoder/counts/issues và view dễ đọc; sửa rồi reseal vẫn bị so với replay.
0=mọi candidate preview đạt; 2=preview có issue/quarantine; 1=lỗi đầu vào/
runtime/binding. Mã 2 không phải phê duyệt hay lỗi bị bỏ qua.

Chưa hỗ trợ target Điều, đơn vị có con sâu hơn, bảng, tách dài hoặc context
dẫn chiếu ngoài cây cha. Không chạy encoder inference, embedding/index hoặc
kích hoạt ứng dụng, không thêm reviewer/phân quyền/chữ ký số. Lệnh thực tế
và kết quả ở README, Stage6_Point_Context_Verification.md.
