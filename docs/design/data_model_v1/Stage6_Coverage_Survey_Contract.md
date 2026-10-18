# Stage 6 — khảo sát khả năng chunking trên bốn cây DOCX

Phiên bản công cụ `chunk-coverage-survey.v1`. Snapshot **2025-01-01**.
Đây là phép đo kỹ thuật bằng builder hiện hành trên cây đã parse, không
phải độ phủ nghiệp vụ, xác minh pháp lý hoặc quyết định phát hành corpus.

## Đầu vào và đường chạy

`src.coverage_survey build/validate` dùng đúng bundle Stage4
`staging/stage4-docx-005/`, đã kiểm bằng validator Stage4 trước khi nhận.
Config `config/coverage_survey.v1.json` khóa checksum manifest cây và
assessment v1.1 `staging/stage5a-revision-pilot-003/`, gồm proposal pilot
đã điều chỉnh và lịch sử quyết định thực tế. Không trộn mapping PDF Điều 22.

Run mới sao nguyên byte bundle cây, bundle assessment, bốn raw DOCX và
Source Inventory cần cho upstream validator. Các source snapshots tiếp tục
pending; `source_url` của DOCX là **candidate URL từ inventory**, không
phải bằng chứng đã tải DOCX từ URL đó. Không đánh giá lại hoặc sửa chúng.

Adapter chia dữ liệu theo law_id, nối warning Stage3 với trace bằng locator
chính xác để lấy extraction ranges khi có một node khớp. Inventory issue
đưa vào builder gồm parser issues, coverage needs_review/unparsed và
warnings extraction. Không viết lại logic kiểm dependency hoặc tự resolve.

```text
Stage4 validator + assessment validator
 -> units/relations/spans/files/extractions/issues theo law_id
 -> phân loại context-only và target candidates
 -> chunk_preview_v2.build_chunks (batches 64)
 -> encoder_input.encode_inputs (PyVi CPU + tokenizer local)
 -> kết quả từng unit + thống kê + preview/quarantine + replay validator
```

Giữ nguyên builder `leaf-clause-point-context.v1`, preprocessing
`phobert-pyvi-input.v1`, model/revision/assets đã pin ở Stage6, budget **256**
gồm special tokens. Config survey phải khớp config Điểm hiện hành, chỉ bỏ
target IDs pilot. Không đổi policy, model, context, segmentation hay budget
để tăng số đạt. Không tải weights, gọi encoder inference hoặc tạo index.

## Mẫu số và phân hoạch

| Nhóm | Cách tính |
|---|---|
| Context-only | Document/Chương/Mục; Điều/Khoản có con; không tạo target từ đoạn dẫn cha |
| Target được hỗ trợ | Khoản hoặc Điểm không có con; builder vẫn kiểm toàn bộ quan hệ, nội dung, bằng chứng và context |
| Target chưa hỗ trợ | Điều lá có nội dung và dạng lá khác không thuộc khả năng hiện hành; vẫn gọi builder để ghi issue thật |
| Vùng nguồn chưa đủ trong cây | Parser/coverage quarantine và bảng chưa phân tích; liệt kê riêng, không tạo unit hoặc tăng mẫu số |

Mỗi legal_unit có đúng một hàng `unit_coverage.jsonl`/CSV và một trạng thái
cuối: context_only, preview_available, blocked_source_or_context,
over_token_budget, unsupported_structure hoặc execution_error. Tỷ lệ thành
công chỉ là preview_available / số **target được hỗ trợ**. Không chia cho
toàn bộ unit hoặc tính context-only như target hỏng.

Một candidate có nhiều issue vẫn chỉ tính một lần. Primary reason ưu tiên:

1. EXECUTION_ERROR.
2. INVALID_RELATION_OR_SOURCE.
3. DUPLICATE_UNIT_ID.
4. MISSING_TARGET.
5. MISSING_REQUIRED_CONTEXT.
6. PARSER_OR_EXTRACTION_ISSUE_IMPACT.
7. TOKEN_BUDGET_EXCEEDED.
8. UNSUPPORTED_STRUCTURE.

Giữ đầy đủ builder_issues và impacts đã trả về, kể cả code nguồn bên trong.
Builder dừng sớm khi lỗi; survey không suy nguyên nhân hoặc token count ở
bước chưa chạy. Parent IDs và spans input vẫn có; context IDs/proofs là
kết quả builder thực trả về, nếu bị chặn sớm ghi
`context_resolution=not_returned_by_builder`. Không dựng context giả.

Lỗi batch bất ngờ được tách đôi để cô lập đến từng candidate; lỗi còn lại
ghi execution_error với exception type/detail, không tạo token giả hay
tính đạt. Input bundle không hợp lệ bị từ chối trước khi tạo run mới.

## Token, nội dung và bằng chứng

Đếm toàn **encoder_text** sau preprocessing dùng chung, gồm special tokens.
Nguyên văn, context, text_for_search, spans/offsets và công thức ID/hash DDD
không đổi. Survey không tự tính lại bằng đếm từ hoặc text_original đơn lẻ.
Builder giữ đầy đủ candidate/context vượt ngưỡng trong quarantine; không
truncate hoặc bỏ context. Encoder input gồm text/hash/IDs/pieces/counts
theo chunk_id, cho cả preview và quarantine.

Token p50/p95 dùng nearest-rank, có mẫu số n của nhóm đo được. Những unit
context-only hoặc bị chặn trước encoder có token/unknown=null. Thống kê
257–384, 385–512 và >512 không làm thay đổi giới hạn model hoặc preview.
Unknown count không được coi là lỗi encoding hoặc thước đo retrieval.

Mỗi hàng giữ unit binding/hash, cha, context IDs khi builder trả về, source
spans và context proofs. Preview dùng source proof/identity của builder thật.
Các bảng/issue nguồn riêng có locator, ranges và lý do từ artifact gốc.
Record parser/coverage/table có thể trùng vùng; không gọi tổng record này
là số lỗi độc lập. Bảng supporting/non-body cũng được liệt kê để truy vết,
không mặc định là target thất bại. Stage3 warnings nằm trong input snapshot
và inventory dependency, không giả là unit trong bảng source_gaps.

## Scope và cổng pháp lý riêng

Theo BRD §3.1/§3.3, khả năng tạo chunk không tự chứng minh thuộc phạm vi
người tham gia giao thông. Scope chỉ nối từ assessment đúng manifest,
unit_id và unit_sha256; upstream validator kiểm evidence, supersedes và
ngày/trạng thái. Không mượn decision của binding PDF cho cây DOCX.

Ba nhóm scope: có quyết định scope thực tế; chỉ proposal có kết luận;
chưa đánh giá/kết luận scope. Proposal record có scope_candidate=null vẫn
thuộc nhóm thứ ba, số proposal record được báo riêng. Quyết định các chiều
khác không tự là quyết định scope. Không tạo proposal/decision mới hoặc
phân loại bằng keyword trong survey.

Các unit tiếp tục origin=agent_review, preview_only=true,
release_eligible=false, corpus_version=null, metadata hiệu lực null/pending.
Blocker nguồn/provenance, extraction/cây, scope/hiệu lực và corpus nằm riêng
với lỗi kỹ thuật. Không dùng danh sách lỗi kỹ thuật rỗng để hàm ý verified.
Dẫn chiếu ngoài cây cha chưa được truy tìm hoặc ghép thêm.

## Output và kiểm chứng

Run mới gồm coverage_report.md, coverage_summary.json, unit_coverage.jsonl,
unit_coverage.csv, source_gaps.jsonl, samples.md, builder_issues.jsonl,
dependency_checks.jsonl, execution_errors.jsonl, runtime.json, manifest và
validation_report.json. Các file chunk/context/encoder/quarantine nằm riêng
ở `preview/`, nguồn và assessment cũ nguyên byte trong `inputs/`.

Samples chọn tối đa hai văn bản khác nhau mỗi nhóm quan sát được; nhóm rỗng
ghi rõ không có mẫu thật. Tối đa ba ưu tiên là đề xuất chưa triển khai,
số candidate liên quan là cận trên cần khảo sát, không hứa mọi candidate
đều khắc phục được hoặc thuộc nghiệp vụ.

Validator kiểm inventory/hashes/code/config/pending, gọi lại upstream và
**replay toàn bộ bốn cây bằng builder/tokenizer thật**, so từng output,
summary/CSV/report/samples; không chỉ tin validation_report đã lưu. CLI:

- Exit 0: khảo sát hoàn tất, không có candidate lỗi thực thi. Vẫn có thể
  có candidate bị chặn/vượt budget/chưa hỗ trợ hợp lệ theo kết quả đo.
- Exit 2: khảo sát hoàn tất nhưng có candidate lỗi thực thi.
- Exit 1: input/binding/config/output hoặc lỗi toàn tiến trình.

Exit survey khác CLI preview pilot: 0 không có nghĩa mọi candidate pass
hoặc dữ liệu được phát hành. Tests fixture gắn nhãn synthetic/FIXTURE và
test integration có artifact thật; không trộn fixture vào preview thật.
Lệnh chạy lại và kết quả thực tế ở README và
`docs/reviews/Stage6_Coverage_Survey_Verification.md`.
