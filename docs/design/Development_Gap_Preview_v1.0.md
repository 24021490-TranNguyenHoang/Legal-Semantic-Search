# Phiên 12 — preview khắc phục khoảng trống development v1.0

Snapshot2025-01-01, policy development-gap-preview.v1. Nguồn được ghim bằng
config/manifest/hash; không đổi DOCX NĐ168 session2-001 hoặc nhánh Luật36 đã
chọn. Không tạo dataset/index hoặc quyết định human/legal verified.

## Record và read closure

Tái dùng parser graph, leaf-clause-point-context.v1, encoder PyVi/PhoBERT,
budget256 và frame reader phiên4; không sửa code hash-bound. Đề xuất một
target từ A6K9b nếu builder/proof/token đạt. Context đúng title A6+lead K9.
K16b cùng lead, K10b (gây tai nạn) cùng lead và K16d là required-read hữu hạn;
không biến cả K9/K16 thành target hoặc dùng mức phạt K1. Giữ nguyên mọi câu
dẫn chiếu của các đơn vị này, không mở rộng tất cả hành vi anh em được liệt kê.
K15 được đọc để đối chiếu: chỉ trỏ e5/K12/K11/K13/K14, không tự gán cho9b.
Đây là closure cho phạm vi đã khai báo, không xác minh toàn luật/hiệu lực.

Luật36: giữ nguyên target A59K1b/payload/ID đã có. Bổ sung required-read A57K1a/b
(A1/A), K1c(B1) vì query không giới hạn mô tô hai bánh; A34K1e/g phân biệt mô
tô/xe gắn máy, A56K1 và K1b liên kết GPLX đúng loại, K4 và A59K1a giữ riêng
ngoại lệ xe gắn máy. Chỉ own fields + title/lead cha, không cả chương. Giữ
required-read cũ. Không thêm dung tích/công suất vào query hoặc đổi nhãn/metric.
Giấy tờ khác, sức khỏe chi tiết và chuyển tiếp GPLX cũ chưa là kết luận từ
closure tuổi/hạng này; các dẫn chiếu nguyên văn vẫn giữ để người đọc nhận biết.

Full supporting fields có native source spans. Tổ tiên document/chapter/section
chỉ structural_only, không tự thêm whole subtree vào required-read. Mỗi frame
có expected dependency IDs, unit hashes, toàn bộ own text và source proof;
reader.check tái dùng kiểm ID/search/context/slices/FK/capability/encoder.
CLI validate còn dựng lại membership/closure từ input ghim, không tin các ID
mà sidecar tự khai. Sidecar không thay schema DDD hoặc nới consumer dataset v5.

Tất cả target encoder input dùng preprocessing hiện hành, không truncate/tăng
budget. Nếu target mới vượt256 hoặc source/parser issue ảnh hưởng thì giữ
quarantine/blocked, không ép thành record hợp lệ. Whole-source TT38 cũ giữ đủ
record và encoder views; full input>256 không thành view target mới. Tokenizer
chỉ CPU/offline; không inference/embedding hoặc thay model.

## Checker80/81 — distance-80-81-evidence.v1

Đây là checker tập bằng chứng development, không đánh giá nhãn completeness
đã accepted. Input packets được lấy qua consumer của đúng dataset đã validate:
target table rows hoặc bảng nhúng của source-retrieval.v1. Packet giữ record
hash/type, access path, row owner, cells/header, native proof và full condition
fields. Không dùng Hit/label1/derived text đơn lẻ thay bằng chứng.

Yêu cầu khai báo:

- 80 thuộc 60<V≤80, ô khoảng cách55m;81 thuộc80<V≤100, ô70m.
- Header Tốc độ lưu hành(V km/h)/Khoảng cách an toàn(m), đúng cột/hàng/bảng.
- Full normal condition/ngoại lệ từ owner A11K2a, và điều kiện bất lợi A11K2b
  có proof. Không đưa hai trị số thành khoảng cách vô điều kiện hoặc tính một
  trị số cố định khi bất lợi. Source_original khác text dẫn xuất của hàng.
- Phép so sánh normal-only dùng cả hai giá trị:55<70, chênh15m.

Checker đối chiếu mỗi cell/row/condition/proof với response/hash nguồn thật,
gọi native proof reader kiểm normalized extraction Unicode offsets và EID/raw
hash/locator. Facet bị bỏ khỏi packet không được tự lấy lại từ full record để
cho pass. Thiếu hàng/header/đơn vị/điều kiện, sai ranh giới/owner/source/proof
trả sufficient_for_declared_requirements=false cùng lỗi. Không suy thêm chữ
hoặc nội dung từ khóa. Cả hai target rows+adverse record hoặc một record nhúng
có đầy đủ bảng+required-read có thể đạt. Chỉ hàng80 hoặc81 thì không.

Trạng thái đạt chỉ đủ yêu cầu bằng chứng đã khai báo, không human review mới,
legal verified hoặc thay completeness từng record. Pending/source/applicability
giữ riêng. Không tự mở rộng đánh giá toàn corpus hoặc cập nhật qrels/metrics.

## Output và replay

Run staging mới có graph projection/spans, hai nhóm read preview, disposition/
membership proposal, encoder evidence, checker cases, source selection và
manifest hash. Manifest bind adapter/checker/reader/contract/config. Validate
tái dựng từ input+token cache và so nội dung, replay build đo tokenizer thật
giữ payload ổn định. Runtime/cache/package/model binding vẫn theo Stage6.
Không tải nguồn mới nếu bằng chứng đã có, không sửa raw/run hoặc phát hành.
