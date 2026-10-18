# Agent review và chunk/context PREVIEW Điều 22

Policy `article22-context-preview.v1`, snapshot **2025-01-01**. Đây là đường
preview trong staging được người dùng cho phép sau bước draft. Không đòi
corpus được phê duyệt để tính thử chunk/context, nhưng không mở cổng serving.
Không sửa parser, raw, schema DDD, validator/review history hiện có.

## Agent review, không thay quyết định reviewer

Đầu vào là mapping PDF Stage 3/4 hẹp hợp lệ kỹ thuật `article22-pdf-004`,
HTML/PDF/quote/ảnh đã capture và hồ sơ quan sát của agent. Đối chiếu:

- HTML metadata: số/tên luật, ngày 27-06-2024, hai URL PDF đính kèm.
- PDF đầu p1/p10/p19/p20/p21; phần tiếp p1/p58–61: nguồn/cấp cha, Điều 22,
  quan hệ hai phần, warning và căn cứ hiệu lực. Cuối phần đầu nêu xem tiếp
  979+980; đầu phần tiếp nêu tiếp theo 977+978 và mở Điều 24.
- Năm field title/đoạn dẫn/Khoản 1–3 và tám spans của mapping được replay;
  không coi body Điều 21 ở phía trên trang 19 là context Điều 22.

Kết quả ở agent_review.json/md có **origin=agent_review**. Quan sát ảnh
thực tế được lưu với actor=codex_agent, timestamp của agent, PDF/image hash
và locator trang. HTML/captured-page text có quote/offset/hash riêng, không
trộn với offsets extraction. Validator replay kiểm đối chiếu text/hash và
binding ảnh; không tuyên bố tái thực hiện nhận định thị giác từ checksum.

Không ghi người dùng đã xem; human_review_claimed=false,
reviewer_event_created=false. Không tạo submission hoặc human event; contract
assessment v1.1/draft chưa tiếp nhận agent_review làm reviewer decision.
Các quyết định nguồn/scope/technical/applicability thật chưa có vẫn giữ nguyên.

Trang 21 là thông tin xuất bản dạng nét, không trích được chữ. Agent quan
sát nó nằm ngoài spans dùng cho Điều 22, chưa thấy ảnh hưởng trực tiếp đến
vùng chọn; không OCR hoặc resolve PDF_PAGE_NO_TEXT. Căn cứ Điều 88/89 đã xem
gợi ý ngày 2025-01-01; không thấy ngoại lệ riêng Điều 22 trong vùng này.
Lịch sử sửa đổi chưa được tra cứu toàn diện, bản hợp nhất/sửa đổi 2026 không
thay luật tại snapshot. Chưa xác minh toàn file/cây hoặc hiệu lực pháp lý.

## Ba chunk và context có nguồn

Mỗi Khoản 1–3 là đúng một target, segment_no=1, unit_char_start=0,
unit_char_end=len(unit.text_original). Giữ nguyên LF, số, dấu câu và phủ định;
không tách/cắt câu hoặc gộp text con vào cha. Không tạo chunk Điều 22 riêng.

Mỗi target có đúng hai context rows, lấy từ **cùng unit Điều 22**:

| context_order | field | khoảng ký tự | context_role |
|---|---|---|---|
| 0 | title | [0,len(title)) | heading |
| 1 | text_original | [0,len(đoạn dẫn)) | lead_in |

context_text = title + LF + đoạn dẫn. text_for_search = law_title + 2LF +
citation_path + 2LF + context_text + 2LF + text_original. Nút document/Chương II
chỉ giữ cấu trúc/citation, không thêm title/preamble của chúng vào context.

source_locator của target/context giữ đúng file_id, extraction_id/text hash,
span_id, source PDF hash/path, locator, char_start/end và quote hash trên
normalized.txt bất biến. Offsets context là tương đối trong field; source
spans là tuyệt đối trong extraction. Đường dẫn trong preview trỏ snapshot
nguyên byte, không sao offsets từ DOCX hoặc text trang bằng chứng.

## ID/hash và contract pending riêng

unit_id giữ nguyên mapping PDF. content_sha256 = SHA-256 UTF-8 của
text_for_search. chunk_id dùng **đúng** đối tượng chunk.v1 và key `contexts`
trong validate_design.py của ZIP mẫu:

```text
identity_schema, unit_id, segment_no, unit_char_start/end, text_original,
chunk_policy_version, contexts[{unit_id,field_name,char_start/end,context_role,context_order}],
law_id,law_title,citation_path,source_url,effective_from,effective_to,applicability_status
```

ID là `c_` + SHA-256 canonical JSON (sort_keys, ensure_ascii=false, không
khoảng trắng). Không thêm timestamp/corpus_version/token count vào payload.
Nếu sau này có quyết định hiệu lực khác pending/null, phải tính ID mới, không
đổi ý nghĩa dưới ID preview cũ. Có test đối chiếu trực tiếp hàm mẫu trong ZIP.

Schema chunk phục vụ yêu cầu corpus_version, effective_from và trạng thái
verified_at_snapshot. **Không dùng/nới schema này để cho preview pass.**
Schema riêng `schemas/chunk_preview_v1/preview.schema.json` quy định:
corpus_version=null, effective_from/to=null, applicability_status=pending_review,
preview_only=true và release_eligible=false. Preview cố ý không hợp schema
serving. Không tạo corpus, unit_assessment hay SQLite phục vụ để thỏa FK.

Mọi blocker của mapping gốc được giữ và thêm PREVIEW_NOT_A_CORPUS,
AGENT_REVIEW_NOT_REVIEWER_DECISION, TOKEN_BUDGET_NOT_RELEASE_POLICY.

## Token budget: kiểm thật, không inference

Ngưỡng **256** là ngưỡng thử cho preview theo đường chạy prototype hiện có,
chưa chốt chính sách chunking/token budget toàn dự án. Cấu hình riêng khóa
model ID đang dùng `bkai-foundation-models/vietnamese-bi-encoder`, revision
`84f9d9ada0d1a3c37557398b9ae9fcedcdf40be0` và SHA-256/kích thước của 5 file:
bpe.codes, vocab.txt, tokenizer_config.json, special_tokens_map.json, config.json.
Chỉ sao tokenizer assets này vào run; không copy/load model weights.

PhobertTokenizer.from_pretrained(local_files_only=true) chạy trong subprocess
cục bộ. Không thêm word segmentation, không truncation/padding, đếm cả 2 special
tokens. Đếm target, context và toàn text_for_search; lưu input/hash/ID hash,
phiên bản Transformers, hash implementation và số unknown tokens.

Máy vẫn bị App Control chặn PyTorch. Transformers cài tại máy không tuân
USE_TORCH=0 cho mọi probe: worker coi backend inference là không có khi dò
package trong **process riêng**, đồng thời audit chặn import torch/tensorflow/
jax, network, database và ghi file. Không nạp DLL bị chặn hoặc chạy inference;
không thay môi trường/backend ứng dụng. Module import không spawn process/IO.

Thiếu tokenizer/pin sai thì lỗi trước output; không ước lượng số từ thành
token hoặc tải model để lách. Vượt ngưỡng giữ đủ ba chunk trong preview và
báo token_limit_passed=false, trả 2; không tự cắt nội dung hoặc nâng ngưỡng.

## Artifact và kiểm định

CLI `src.article22_preview build/validate`. Run mới có chunks.preview.jsonl,
contexts.preview.jsonl, chunks_preview.md, agent_review.json/md, token_report.json,
validation_report.json, config/tokenizer assets, ảnh quan sát và input snapshot.
Manifest/sidecar khóa toàn bộ file, code/config/schema/mapping hashes.

Validator readonly replay mapping/IDs/spans, đúng ba target/sáu context, schema
pending, toàn bộ text/search/hash/context/link nguồn, đối chiếu agent, token
count thực tế và các view dễ đọc. Tamper sau reseal vẫn bị so với replay.
Cùng input/config/tokenizer/runtime cho cùng nội dung/ID/hash; built_at khác
giữa run. Không có lệnh admit/freeze/index/activate trong module này.

0 = preview hợp lệ và dưới ngưỡng; 2 = preview có cảnh báo vượt ngưỡng; 1 =
input/hash/version/technical lỗi. Kiểm tra thành công không xác minh pháp lý
hoặc tạo quyết định reviewer. Lệnh tái chạy ở README và báo cáo verification.
