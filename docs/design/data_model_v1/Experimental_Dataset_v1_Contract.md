# Dataset thử nghiệm v1 từ pilot

Policy `experimental-pilot-packaging.v1`, dataset_version
`vtls-pilot-experimental.v1`. Đây là bộ đầu vào thực nghiệm BM25/Dense và
gán nhãn sau này, không phải corpus_version DDD, serving release hoặc bộ
qrels đã có nhãn. Snapshot tham chiếu dự kiến **2025-01-01**; applicability
pending nên chưa bảo đảm mọi đơn vị áp dụng tại ngày đó.

## Input, lựa chọn và bằng chứng hiệu lực

CLI `src.experimental_dataset build` nhận manifest refinement, chạy lại
validator refinement/scope/coverage cùng các upstream trước khi tạo output.
Đọc 107 candidate thật và các chunk/context/token evidence, không lấy số
95 trong báo cáo làm chỉ tiêu. Không sửa raw/parser/builder/encoder hoặc
policy preview đã seal; không segment/truncate hay thêm context.

Candidate được chọn khi đồng thời có scope proposal included,
chunk_capability preview_available, context_selection_proposal
all_fields_proposed_for_use và không có parser/extraction dependency impact
theo builder hiện hành. Unknown token không tự loại candidate.

Scope pending vẫn pending trong deferred; included quá budget cũng ở
deferred. Một candidate có nhiều lý do, vì vậy số lượng lý do có thể lớn
hơn số candidate deferred. Không chuyển pending thành excluded và không
chép proposal thành decision.

Kiểm riêng date rules có binding **unit_id cụ thể** từ evidence đã lưu.
Chỉ ngoại lệ/ngày ngoài snapshot có finding text_slice khớp capture, trang,
quote, offsets và hash mới được dùng để giữ target/dependency ngoài tập
thử nghiệm. Chọn rule priority cao nhất của đúng unit; rule xung đột cùng
priority cần xem thêm. Khoảng thời gian theo assessment v1.1 là
[effective_from, effective_to), ngày kết thúc exclusive. Visual observation
không phải bản chép nguyên văn và không được nâng thành text evidence.

Không suy active từ ngày chung của văn bản. Ngày trước snapshot chưa đủ
kết luận áp dụng vì còn sửa đổi/chuyển tiếp và lịch sử. Không có rule riêng
hoặc chưa kết luận thì có thể giữ target trong dataset với applicability
pending. Việc loại khỏi tập thử nghiệm bằng chứng ngoại lệ không ghi thành
assessment verified/not_yet_effective của reviewer và không điền ngày vào
chunk. Những ngày ứng viên vẫn chỉ nằm ở evidence/date_rules.pending.jsonl.

Nguồn DDD/Inventory/người dùng chốt snapshot; BRD/SRS còn snapshot mở là
mâu thuẫn đã được ghi nhận. Không dùng tiêu chí corpus cũ 1.457 chunk của
prototype để chọn hoặc đánh giá kết quả.

## Nội dung và identity

Giữ nguyên object chunk/context upstream, gồm nguyên văn, context_text,
text_for_search, source_locator, offsets và spans. Đường dẫn proof
`inputs/...` vẫn resolve từ gốc bundle; không cần đổi identity payload.
unit.v1, source-span.v1 và chunk.v1 tiếp tục dùng implementation hiện hành;
content_sha256 vẫn SHA-256 UTF-8 của text_for_search. Không dùng số dòng
làm ID. Chunks sắp chunk_id; context sắp chunk_id/context_order. Hai file
ID có LF cuối và được manifest hash.

Dataset_version và dataset_content_sha256 khóa bộ dùng chung/qrels.
corpus_version=null, release_eligible=false, preview_only=true; ngày hiệu
lực null và applicability_status=pending_review trên chunk. Scope chỉ là
đề xuất agent. Source/extraction/technical/applicability không tự verified,
không có human reviewer event hoặc trường reviewer/thời điểm giả.

Dataset version này chỉ dùng cùng input/config/content đã định. Nếu thay
tập target, context, policy hay nội dung, phải dùng dataset_version mới;
người dùng qrels phải kiểm cả version và content checksum. Chưa thiết kế
hệ thống đăng ký version hoặc quyền truy cập mới.

## Bundle gọn và quy ước đường dẫn

Không copytree run refinement hoặc lịch sử staging. Chỉ đóng gói:

- 107 bản ghi pilot phục vụ kiểm lựa chọn/deferred; chunk/context và encoder
  evidence tương ứng, scope history/field review chiếu sang dạng portable.
- Cây/spans/issues của các văn bản có candidate, để builder tái kiểm đúng
  quan hệ và ranh giới structural window. Các unit còn lại trong cây là
  support kiểm chứng, không được đưa vào target/context tìm kiếm.
- DOCX raw nguyên byte, normalized.txt và trace tương ứng; hồ sơ pending
  nguồn/extraction thật. Full normalized giữ nguyên offsets tuyệt đối.
- Findings/date rules liên quan và capture PDF/page text thật mà chúng
  tham chiếu; giữ URL, accessed_at/hash và trạng thái pending. Không coi
  capture mới là thời điểm tải DOCX lịch sử, không giả bản lịch sử đã khớp.
- Config/pins và năm tokenizer assets, diagnostics unknown đã có; một số
  module contract chuẩn của repository để chạy validator portable bằng
  stdlib. Không đóng gói model weights, venv, database hoặc index.

Các source proof giữ nguyên chuỗi JSON gốc, paths tính từ gốc bundle.
Laws data dùng raw/text_ref tính từ `inputs/`; extraction record.trace_ref
tính từ `inputs/tree/extraction_snapshot/`. Finding.text_ref tính từ
`evidence/pages/`; catalog.artifact_ref tính từ gốc bundle.
Document.declared.inventory_ref tính từ gốc bundle. Các snapshot record
được chiếu loại bỏ base/path lịch sử không còn có nghĩa trong bundle;
đây là sidecar packaging, không giả đó là proposal mới hay sửa ID gốc.

input_binding.json lưu manifest SHA/version/code/hash nguồn upstream và
các file thực đã copy. Không mang manifest upstream đầy đủ với hàng nghìn
path không đóng gói; portable validator không giả đã chạy lại toàn lịch sử.
Build từ đầu/full upstream validation cần run refinement gốc và repository
đúng version. Artifact tiêu dùng và portable validation không cần chúng.

## Đầu ra và thống kê

README, dataset_manifest.json/checksum, chunks.jsonl, contexts.jsonl,
targets.csv, deferred_candidates.csv, documents.csv, metadata_gaps.csv,
dataset_statistics.json/MD, validation_report.json, encoder_config.json,
target_unit_ids.txt, chunk_ids.txt, diagnostics và support/evidence/runtime.

Thống kê tính lại target và chunk riêng; số context row, distinct unit/field
chia sẻ, phân bố văn bản/loại target, token/unknown có mẫu số, deferred với
lý do giao nhau, gap theo target/dependency/chiều. Metadata gap có span IDs
thật và explicit_unit_date_rule_ids. legacy_target_finding_ids là hồ sơ cũ
của target, không phải xác minh riêng mọi field dependency trong hàng đó.

Token count trên đầy đủ encoder_text gồm special token, kế thừa evidence đã
được upstream tokenizer replay. Validator portable kiểm IDs/count/hash và
binding evidence; không gọi đó là tokenize mới. Không chạy encoder/inference.

## Dùng chung cho nhóm

BM25/Dense dùng cùng chunk_id và text_for_search nền. Không cấp context
riêng cho một mode. Model BKAI hiện cần bản sao qua phobert-pyvi-input.v1,
NFC/whitespace/PyVi CPU CRF cùng cấu hình query/document; encoder_text không
là text chuẩn mặc định cho mọi model. BKAI chưa là quyết định model cuối.
Qrels cần dataset_version, content SHA và ID đúng bộ; chưa tạo queries,
nhãn/qrels/split hoặc chỉ mục trong lượt đóng gói.

## Validator, portability và tái lập

CLI validate tái dựng 107 candidate bằng builder cũ và cached encoder
evidence đã kiểm upstream; đối chiếu exact IDs/content/proofs, FK/context
order, fields, spans/raw/text/trace, source pending, date evidence,
selection/deferred, CSV/JSON/Markdown/counts. Kiểm inventory đầy đủ, policy,
config/model/code/hash và không có metadata release/reviewer tự tạo.

`runtime/validate_dataset.py` cùng các helper byte-identical chạy offline
với Python 3.11+ stdlib, từ thư mục đã copy hoặc máy khác. Dùng `-B` để
không tạo cache trong bundle seal. Kiểm portable không thay tokenization
hoặc xác minh pháp lý; checksum không phải chữ ký chống người có quyền
viết lại toàn bộ bundle và không cần thêm hệ thống chữ ký/phân quyền.

Muốn chạy lại tokenizer cần packages/assets đúng pins trong môi trường
requirements-stage6.txt cùng encoder_input hiện hành. Các packages và encoder
weights không có trong bundle; chưa cam kết inference chạy trên máy đang
bị Windows Application Control chặn PyTorch. Giới hạn này không chặn kiểm
bundle bằng stdlib. Không tự tải weights hoặc đổi model để vượt lỗi máy.

Manifest nội dung ổn định, chứa inventory và dataset_content_sha256. Không
đưa thời điểm/path tuyệt đối của lần build vào dữ liệu ổn định. execution.json
ghi sự kiện kỹ thuật thật, tách khỏi inventory/content hash; không phải
nguồn/effective/reviewer event. Build vào run mới; validate chỉ đọc.
Exit 0 là nhất quán kỹ thuật của dataset thử nghiệm; exit 1 là lỗi.
