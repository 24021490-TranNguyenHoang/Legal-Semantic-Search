# Dataset experimental tiếp theo — draft có nhánh nguồn

Policy `coverage-source-branches-draft.v1`, dataset version
`vtls-coverage-experimental.v2-draft.1`. Bổ sung hẹp cho contract dataset/BM25
v1, không sửa DDD, unit.v1/source-span.v1/chunk.v1 hoặc policy chunking.

## Xung đột biểu diễn và quyết định triển khai

Dataset v1 dùng `support/laws.json`, mỗi law_id một cây DOCX đầy đủ. Nhánh
HTML A16K2 là sparse projection: document/Chương/Mục chỉ chọn title; own text
chưa chọn không có nghĩa là nguồn rỗng. ID các cha khác DOCX, kéo theo ID
con khác. Union hai cây theo law_id/canonical_path hoặc nối con HTML vào cha
DOCX sẽ làm sai identity/provenance hoặc ghi đè nội dung chưa chọn.

Draft dùng **hai component bất biến**, `components/base/` và
`components/nd168-a16k2/`, mỗi component giữ cây/spans/proofs và manifest gốc.
Không có cây hợp nhất hoặc legal_document chính thức thứ hai. Các cha HTML
là bản biểu diễn nguồn thay thế của cùng vị trí pháp lý, không phải căn cứ
mới. Đây là lớp đóng gói pending bên ngoài schema DDD chính thức.

`memberships.jsonl` ánh xạ mỗi chunk_id tới graph_id `base-docx` hoặc
`nd168-html-a16k2`. Root `chunks.jsonl`/`contexts.jsonl` giữ nguyên objects
upstream; raw/text refs trong source_locator phải resolve từ **component
root theo membership**, không từ root draft. Context thuộc cùng graph với
target; FK cha chỉ resolve trong graph đó. Người dùng artifact bắt buộc đọc
membership trước proof; loader BM25 v1 từ chối policy mới, không sửa loader.
Không nhập trực tiếp flat union này vào SQLite DDD hoặc index cũ.

## Lựa chọn hữu hạn

Base khóa manifest/content/version thật trong config. Addition chỉ năm Điểm
a/b/c/d/đ của Điều16 Khoản2 NĐ168 và đúng dependencies đã khôi phục. Không
thêm chín Điều lá, L35 A86K2, 20 trường hợp dài hoặc sửa source/context khác.

Đối chiếu toàn dataset bằng law_id + canonical_path của unit (kiểm citation
khớp), citation, exact/whitespace-NFC content, unit/chunk IDs và crosswalk.
Khác ID không đủ để thêm mới: cùng vị trí/nội dung là duplicate, khác nội
dung là conflict; cả hai phải dừng build chờ phương án rõ ràng. Policy này
chỉ thêm vị trí chưa có target, chưa tự động thay thế hoặc xóa target.
Nội dung giống ở vị trí khác chỉ là match cần ghi, không tự gộp căn cứ.
Kiểm duy nhất vị trí pháp lý của toàn bộ targets sau composition.

`candidate_comparison.jsonl` ghi đầy đủ match; `delta.jsonl` ghi mỗi chunk
added/unchanged (reserved replaced/removed/conflicted), `unit_crosswalk.jsonl`
giữ mapping cha/con và changed_identity_fields, không chuyển decision.
`parent_dependencies.jsonl` nêu rõ các field chưa chọn và hash/độ dài cha
DOCX giữ nguyên. Base deferred giữ bất biến trong component; root deferred
chỉ bỏ những representation cũ có cùng vị trí đã được nhánh mới thay thế
trong draft, giữ lịch sử tại `deferred_history.jsonl`. Không resolve issue
DOCX cũ hoặc suy d/đ từng có old unit/chunk.

## Validation và tái tạo

Build chạy validator base và recovery hiện có trước khi tạo output. Copy
chính bundle cần dùng theo inventory, không copy staging history/tokenizer
weights/index/venv. Validate draft tái dùng validator base; replay extraction
HTML/mapping, DDD shapes/IDs/parents/spans/trace/source facts, so legacy
snapshot với base; replay builder hiện có bằng token evidence đã đo có
binding input/encoder/token IDs/count/hash và budget256, không tokenize mới
hoặc inference. Cấu hình encoder phải giống base. Recompute toàn bộ exports,
membership, metadata, delta, crosswalk, residual deferred và thống kê; kiểm
inventory/version/content/code hash. Không nới validator cũ.

Version/hash của cả hai input khóa trong manifest/config; draft inventory
và content hash riêng. Runtime event nằm trong execution.json ngoài hash
nội dung. Output mới bắt buộc dưới staging, không ghi đè. Validate không cần
run coverage hoặc recovery gốc, nhưng cần repository/module/dependency đúng
phiên bản (lxml/jsonschema + môi trường pipeline); không cam kết khác Python
hoặc lxml vì extraction identity có tool version. Build recovery từ đầu vẫn
cần input/tokenizer theo contract recovery; draft chỉ dùng kết quả đã có.

Draft luôn status=draft, experimental=true, preview_only=true,
corpus_version=null, release_eligible=false, origin=agent_review. Scope chỉ
proposal; source/edition/technical review và applicability pending; ngày
hiệu lực null, không human reviewer event. Capture HTML sau snapshot và
đối chiếu scan vùng hẹp không xác minh lịch sử hiệu lực hoặc toàn file.

## Tác động evaluation/index

Crosswalk chunk v1→draft chỉ cho phép carry-over ID khi object/hash/context
không đổi, không tự migrate qrels hoặc tạo judgment mới. Dù ID cũ giữ nguyên,
thêm documents có thể đổi BM25 IDF/ranking và denominator relevance; phải
bind lại version/hash, rà nhãn coverage và build/evaluate index mới ở lượt
được cho phép sau. Không dùng index v1 như index của draft; nhóm tiếp tục v1.

CLI `src.experimental_draft build --config ... --run-dir staging/NEW` và
`validate --manifest .../dataset_manifest.json`; exit0 là nhất quán kỹ thuật,
exit1 là lỗi input/binding/conflict, không xác minh pháp lý/phát hành.
