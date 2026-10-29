# Phiên 4 — record preparation / packaging plan v1.0

Snapshot **2025-01-01**; nguồn/scope bind run009 phiên3, không chọn latest.
Không thay schema DDD, identity policy hay artifact đã phát hành. Không tạo
dataset/index/official assessment. Trạng thái PREVIEW_AND_PLAN_ONLY,
origin=agent_review, human_review=null, release_eligible=false.

## Dựng lại NĐ168 trong phạm vi hữu hạn

Disposition riêng từng old record ID, old unit, lineage/crosswalk, selected unit
và new record. Chỉ scope in_scope/role target trong run009 được dựng target;
năm A16K2 unresolved không nhận nhãn HTML. Không correction/parse lần nữa DOCX
session2-001; reuse extraction và graph, dựng context/proof từ source spans mới.
Không mang assessment/qrels/offsets từ nhánh cũ.

Builder leaf-clause-point-context.v1, tiền xử lý PyVi/PhoBERT và budget256
không đổi. Chuỗi original/context/search và native offsets không được truncate
hoặc sửa để vừa ngưỡng. Nếu thật sự quá budget, có thể dùng policy encoder views
hiện có, giữ trọn record; view không là target. Không có boundary an toàn thì
quarantine. 22 record thực tế phiên4 không cần view mới.

Required-read là closure hữu hạn theo run009 và mapping ngoại lệ trong config:
các ngoại lệ A6/A7/A10, chế tài bổ sung/trừ điểm A6K15–16/A7K12–13 và Luật36A27.
Giữ own title/text/spans và cha của Điểm được dẫn chiếu; không suy tiền phạt,
không dò mọi citation trong corpus. Nhánh NĐ165/Luật36 cho A12K12 kiểm riêng;
A12K12 ngoài27seed nên không tự thêm target hoặc dependency thừa vào plan.

## Mẫu XXIII / A28K2

Mẫu XXIII dùng form-retrieval.v1 hiện có, không giả chunk hoặc cell table.
Giữ nguyên trang127, 18 dòng/nhãn/trường trống/chữ ký/hướng dẫn với bbox và
native source proof; ranh giới xác nhận qua ảnh126–128. Không điền giá trị giả.
Identity không chứa thời gian chạy hoặc agent/human decision giả.

Form ready không kéo theo A28K2 ready. Sáu programme table owners supporting,
A7 dùng AnnexII; completion conditions A6K4/A7K4–5/A8K4–5 có nội dung/proof.
A7K4d/A8K4d yêu cầu AnnexXV/XVI/XVII; nếu chưa đủ kiểm layout/nội dung và
required-read thì A28 blocked với đúng49trang48–96. Không mở đệ quy mọi dẫn chiếu;
A21K4c/A46K2 vẫn ngoài target. Không coi ảnh/native inventory là full review.

## Typed read sidecar và packaging plan

Plan chỉ targets đủ kỹ thuật cùng union required-read của chính targets đó;
không lấy toàn inventory supporting_only. Không tạo dataset/corpus_version.
Một unit có thể là target và supporting cho target khác; phải phân biệt số
record, số unit và số read obligations. Hàng bảng có ID riêng cùng owner thật.

Read sidecar có typed payload, contexts, normalized native proofs, required
dependency IDs, dependency units và encoder evidence. Manifest hash-bind toàn
sidecar; validator dựng lại từ đầu vào ghim, không tin riêng expected IDs do
sidecar tự khai. Consumer table-owner phiên3 trả whole record và dependencies;
form giữ whole-page+field read. Không biến projection hoặc view thành target.

Nguồn DOCX Stage3 không có identity.json: sidecar lưu đúng identity payload
extraction.v1 từ metadata thật, kiểm EID/trace-content/text/file/raw hash. Không
tạo extraction giả. PDF native có identity.json thì đọc đúng artifact đó.

Offsets: native proof là Unicode code point trong normalized extraction;
context ranges tương đối field unit; encoder-view ranges tương đối search text.
Bbox là PDF top-origin theo native region. Không hoán đổi không gian offsets.

ND self artifact trong plan tương đối this_run; nguồn lịch sử còn refs rõ để
copy/mount theo hash ở phiên packaging sau. Portable read-probe chỉ copy assets
cần cho năm loại ca kiểm, reader stdlib và typed payload; audit gate cấm đọc
workspace gốc. Không gọi probe là dataset portable hoặc kiểm trên máy khác.

Replay so byte payload; timestamp kỹ thuật ngoài identity. Kiểm source/locator/
slice/hash, context, identity, view coverage/boundary/budget, missing required read,
form completeness, duplicate legal target DOCX/HTML, capability và QCVN caption
conflict. Source/edition/applicability và human decision tiếp tục pending.
