# Stage 6 — Điều lá, ứng viên dữ liệu phiên bản tiếp theo

Snapshot 2025-01-01. Policy mới `leaf-article-title-context.v1`, CLI
`src.leaf_articles_preview`. Phạm vi đúng chín Điều có trạng thái
unsupported_structure trong coverage manifest gắn với dataset đã bàn giao.
Không xử lý 20 target dài hoặc 13 lỗi nguồn/context của tập cũ.

## Tương thích và tái sử dụng

Dataset manifest khóa byte hash `chunk_preview_v2.py`, `chunk_preview.py`
và coverage survey. Sửa trực tiếp chúng sẽ làm bộ bàn giao không còn pass
validator. Vì vậy handler Điều nằm trong `src/chunk_preview_articles.py`,
tái sử dụng `source_proof`, `chunk_identity`, `search_components`,
`support_windows`, `issue_impacts` và preview schema hiện có. Không sao
toàn bộ builder, không fork logic Điểm/Khoản hoặc nới code binding cũ.
Dispatcher nhận policy Điểm/Khoản cũ thì gọi nguyên builder cũ và trả
nguyên output. Không chuyển chính sách của 3.077 chunk đã bàn giao.

Policy mới chỉ nhận Điều thật không có bất kỳ đơn vị con nào. Chuỗi cha
phải hợp lệ, cùng văn bản, không chu trình, đúng ID và đi tới document.
Không tạo Khoản/cha giả. Dấu hiệu đánh số đầu dòng còn nằm trong body
trả POSSIBLE_UNPARSED_CHILD_STRUCTURE; chỉ chặn để rà parser, không tự
đoán số hoặc sửa cấu trúc. Vùng bị parser/extraction issue ảnh hưởng chặn
theo dependency/range/part của builder cũ.

## Nội dung, context, token

- Target = toàn bộ `text_original` riêng Điều, offsets [0,len(text)),
  giữ nguyên dấu, khoảng trắng cuối/NBSP và dẫn chiếu.
- Context = title của chính Điều, field=title, role=heading, order=0.
  Không lặp body làm lead/context, không thêm toàn văn Chương/Mục/Điều khác.
  Title rỗng hợp lệ có thể vắng; title có nội dung phải có spans.
- `text_for_search` theo công thức DDD cũ: law_title, citation_path,
  context_text nếu có, text_original, nối bằng hai LF. Nếu luật vốn dùng
  lại cụm từ trong title và body thì giữ nguyên; không deduplicate chữ luật.
- Mọi field nguồn roundtrip bằng source_proof: raw/extraction/hash,
  Unicode code point offsets, quote hash, span ID và nối LF đúng field.
  Title được đưa vào context một lần; citation không tự ghép lại title.
- `content_sha256` trên text_for_search. `chunk_id` dùng nguyên chunk.v1;
  policy mới là trường identity mới chỉ cho Điều. Không đổi unit_id.
- Dùng encoder config/tokenizer assets trong coverage manifest, PyVi CPU
  + tokenizer cục bộ, không inference. Budget/model limit 256 gồm special
  tokens. Giữ nguyên preprocessing, không truncate/tách đoạn/tăng ngưỡng.
  Vượt budget lưu candidate và context nguyên vẹn trong quarantine.

## Kiểm tra dữ liệu thật và trạng thái

CLI kiểm checksum/inventory/code bindings coverage và dataset, quan hệ
dataset→coverage, config/encoder pins, upstream Stage4→3→2 trước khi ghi.
Chọn đúng 9 unsupported articles từ bảng coverage, so unit hash với cây.
Đọc paragraph DOCX thật qua locator để ghi nguyên văn, field match và
numPr/field/revision tags; có dấu hiệu chưa giải mã hoặc field không khớp
paragraph thì thêm issue kỹ thuật trong bộ nhớ và chặn, không sửa nguồn.
Không khẳng định kiểm tra tag trực tiếp thay mọi kiểm tra style kế thừa;
inventory cảnh báo Stage3 và validator extraction vẫn là dependency.

Scope nối từ proposal/refinement trong dataset đã kiểm binding; đồng thời
giữ scope ở thời điểm coverage để thấy sự khác nhau. Không suy pending
thành excluded và không thay proposal thành quyết định. Mọi nguồn,
extraction/cây và applicability vẫn pending; effective dates/corpus null,
release_eligible=false, origin=agent_review, không human reviewer event.

## Đầu ra và replay

Run mới chứa chunks/contexts/encoder/quarantine/issues/unit_results/
dependency_checks JSONL, inspection đầy đủ chín Điều (nội dung, cha thật,
spans, raw inspection, scope cũ/mới), bảng Markdown và manifest/report.
Manifest tham chiếu manifest coverage/dataset bằng path tương đối repo và
SHA-256. **Không phải bundle portable độc lập**: cần giữ hai bundle đầu vào.
Source proof paths tương đối với `inputs/` của coverage được tham chiếu.

Validate kiểm inventory/code/binding/pending và replay đúng chín Điều
bằng tokenizer thật, so tất cả output, bản dễ đọc và report. Exit 0 = cả
chín có preview kỹ thuật; exit 2 = có candidate blocked/quarantine nhưng
được ghi rõ; exit 1 = input/runtime/binding không hợp lệ. Không mở serving.

Lệnh và kết quả: [Verification](../../reviews/Stage6_Leaf_Article_Verification.md).
