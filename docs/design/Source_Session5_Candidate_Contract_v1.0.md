# Phiên 5 — subset candidate độc lập v1.0

Snapshot **2025-01-01**, input cố định source-session4-preview-007 và checks002,
proposal nguồn/membership source-session3-proposal-009. Config/hash ở
`config/source_session5.v1.json`. Dataset riêng
`vtls-subset-experimental.v5-candidate.1`, policy `subset-candidate.v1`.
Không sửa DDD/schema/code hash-bound, dataset/index/qrels/ZIP hoặc run lịch sử.

## Admission và trạng thái

Membership đúng target ID/type/hash trong plan phiên4. Supporting unit reads và
form XXVI giữ vai trò riêng; encoder view không thành target. Không thêm A16K2,
A28K2/XXIII/course tables hoặc vùng QCVN caption xung đột. Nếu target không đạt,
build thất bại kèm record/blocker, không xuất bundle thành công thiếu target.

Candidate experimental, release_eligible=false, corpus_version=null; scope chỉ
proposal, source/edition/applicability pending, human_reviewer_events=0. Input
được xác thực kỹ thuật không trở thành legal verified. Không giả assessment,
nhãn, reviewer, ngày tải hoặc thời điểm build. Receipt build thực tế ở run điều
phối; payload/manifest deterministic không dùng timestamp giả.

## Payload, graph và mounts

Typed frames/packaging plan giữ nguyên byte input phiên4; record/context/search/
ID bên trong không sửa. Package membership tham chiếu record theo ID, không theo
số dòng. `artifact_mounts` phân biệt source_artifact this_run và historical source
refs; một mount chỉ cung cấp record được chọn, không sao cả corpus nguồn.

Raw/normalized/trace/identity và bằng chứng cần đọc được copy vào objects theo
SHA-256. `asset_mounts` ánh xạ nhãn lịch sử → package ref; không fallback repo.
Định danh extraction/raw/text được kiểm, không chỉ kiểm file tồn tại. Consumer
tạo view tạm của native proof với package refs cho validator phiên4, không thay
payload gốc. Locator gốc và package_locator được trả riêng.

Graph giữ đầy đủ payload và source spans của target/supporting cùng ancestors
cần thiết. Ancestor structural_only không tự thành target/context/required-read.
Phần/Chương TT35 giữ identity unit.v1 hiện có. QCVN giữ graph vùng qg_ và policy
qcvn-source-rule-graph.v1.1; không ép decimal rule thành Điều/Khoản DDD giả.
Nguyên văn own fields không sao toàn bộ con vào cha.

Offsets extraction là code point NFC/LF; context offset tương đối field unit;
encoder-view offset tương đối text_for_search. Giữ tất cả, không tokenize/model
inference lại. Table source cells/header/rows và text dẫn xuất tách riêng. Whole
record trả toàn nội dung cùng mọi view. XXVI layout-only supporting, không index.

Payload XXVI lịch sử ghi scope_proposal=included (liên quan nghiệp vụ); plan
phiên4 gán role=supporting. Hai chiều không đồng nghĩa. Giữ cả hai nguyên trạng,
kiểm membership supporting theo plan và cấm form thành retrieval target.

## Consumer và kiểm chứng

Runtime `consumer.py` chỉ dùng Python stdlib, tái dùng bản nguyên byte các helper
hash/graph và frame reader hiện hành. Capabilities được khai báo/kiểm bắt buộc:
target types, graph Part, required-read, whole-record, encoder views, source spans,
table cells/header và supporting form layout. Thiếu capability/asset/dependency
hoặc sai binding phải lỗi, không fallback fixture.

Validate đối chiếu plan + input manifests, toàn graph/spans/native proofs, target
payload/context, required-read closure, physical cells/header và form completeness.
Full-read thực sự dựng response cho mọi target, đọc mọi supporting unit/form,
trả đủ nội dung; không chỉ smoke năm mẫu. Inventory/hash không thay xác minh pháp lý.

Bảy nguồn trong selection inventory; usage riêng nêu nguồn có target/supporting/
structural và asset thực. Không chép NĐ165 chỉ vì có inventory. Raw/text đầy đủ có
thể chứa vùng ngoài subset để giữ source hash; không đồng nghĩa admission vùng đó.

ZIP có SHA-256 riêng; entry timestamps cố định phục vụ tái tạo archive, không là
ngày thu thập hay review. Giải nén run mới, dùng venv sạch Python, chặn repo/staging
gốc/cache, validate và full-read toàn tập. Công bố đúng OS/máy đã thử. Mutation
tests chỉ trên private copy; replay so payload tách receipt thực tế. Chưa build
index/embedding, chạy evaluation hoặc tích hợp ứng dụng/Hùng.
