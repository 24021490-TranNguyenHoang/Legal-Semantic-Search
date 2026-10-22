# Đối chiếu 13 source/context-blocked candidate

Policy `blocked-source-review.v1`, snapshot tham chiếu 2025-01-01.
Không sửa dataset/index/query set đã bàn giao, không xử lý 20 target dài.
Mọi kết luận trong hồ sơ này là `origin=agent_review`, không reviewer event.

## Đầu vào và mẫu số

CLI `src.blocked_source_review` dùng manifest dataset thật và input_binding
để kiểm coverage tương ứng; đúng 13 hàng deferred.reason=
blocked_source_or_context, đối chiếu status và unit_sha256 với cây coverage.
Kiểm inventory/code/hash nguồn, upstream Stage4→3→2 trước khi dựng run.
Scope mới nhất lấy từ proposal/refinement đã binding, không suy từ lỗi.

13 candidate thuộc sáu nhóm vùng nguồn: ND168 A16K2 (3), A39K9 (4), A40K3
(3), L35 A84K1 (1), A84K2 (1), A86K2 (1). Có 10 issue parser/8 locator;
đó không phải 13 lỗi độc lập. Vùng tiếp tục p[1059] của A40K3 bị cách ly
không có issue parser riêng: tổng chín locator nguồn cần chú ý, gồm hai
bảng và một paragraph đồ họa. Không đếm record coverage/source-warning
chồng lấn thành lỗi độc lập.

## Bằng chứng và quyết định xử lý

Tái sử dụng hai PDF đã capture, URL/SHA/thời điểm thu thập gốc trong catalog.
Ảnh trang render cục bộ có hash và thời điểm render riêng; không ghi ngày
render/đối chiếu làm retrieved_at lịch sử. Agent đã xem ảnh toàn trang và
vùng liền kề. Quote phiên âm một phần từ ảnh scan chỉ là bằng chứng quan
sát, không phải normalized extraction hoặc source_span có offsets giả.

- ND168 A16K2: PDF có d), đ), DOCX có hai đ); còn khác `ngán/ngân` trong
  phần chữ. A39K9: PDF d), DOCX đ). A40K3: PDF d), đ), e); DOCX đ), đ), c).
  Giữ cả 10 candidate liên quan deferred. Không relabel trên normalized
  cũ; parser cách ly đúng đối với literal DOCX. Đường mapping text PDF của
  Điều22 chưa hỗ trợ scan không text: cần bản text chính thức hoặc contract
  transcription/OCR có kiểm chứng trước khi tạo extraction/tree/spans mới.
- Hai bảng L35 A84: nội dung nhìn được trên PDF trang 67/in 69. Parser hiện
  chưa biểu diễn ngữ nghĩa bảng sửa đổi. A84K1 scope pending, A84K2 proposal
  excluded; chưa có căn cứ mở rộng cơ chế bảng. Giữ deferred, không ghép
  header/cell vào Khoản hoặc tạo cấp pháp lý giả.
- L35 A86K2: paragraph rỗng p[933] là một đường thẳng ngang, trước câu thông
  qua/chữ ký. Khoản và title khớp trang 69/in 71 theo NFC+bỏ whitespace, có
  đối chiếu ảnh. Chỉ sửa ảnh hưởng layout tới preview trong run mới.

## Parser disposition hẹp, không nới policy cũ

`legal-tree.v1.1.scoped-layout.v1` gọi nguyên parser hiện có sau khi kiểm:

1. Đúng raw SHA, law, extraction locator/range rỗng đã đối chiếu.
2. XML không text/symbol/field/numbering/revision/bitmap; DrawingML là line
   có cy=0 và VML fallback là đường nằm ngang.
3. Paragraph tiếp theo là câu thông qua; đúng hai warning visual tại đó.
4. Bằng chứng PDF/ảnh/page text đúng hash; toàn body Khoản và title có
   trong trang đối chiếu, không chỉ một từ khóa trùng.

Chỉ hai warning này được disposition tại lớp parser/preview mới; bản gốc
vẫn pending, ghi cả issue ID/dependency cũ trong sidecar. Reparse phải cho
**units và spans bằng nguyên bản**, nếu khác thì từ chối. Coverage rỗng
được ghi layout, không tạo span start=end. Validator DDD hiện có kiểm lại
quan hệ/citation/ID/offset/quote/roundtrip và coverage. Đây là projection có
contract riêng, không giả làm bundle Stage4 đã verified hoặc thay manifest cũ.

Builder Khoản/Điểm, policy identity chunk.v1 và preprocessing giữ nguyên.
Chỉ chạy đúng 13 target; dự kiến một preview kỹ thuật, 12 deferred. Đếm
token thực trên encoder_text, budget 256, không truncate. Scope/applicability
không đổi; dates/corpus null, release_eligible=false. Không mở serving.

## Output và tái tạo

Run mới chứa candidate before/after (unit/context/spans/issue/source window),
parser projection, layout disposition, preview/token/quarantine/issues,
catalog bằng chứng, report và manifest. Source window review không phải
legal source_span cho phần chưa parse. Tất cả 13 unit IDs giữ nguyên; chỉ
candidate đã bỏ ảnh hưởng layout có chunk ID mới vì trước chưa có chunk.

Validator so inventory/config/code/input binding và replay parser/builder/
tokenizer, so cả bản dễ đọc và report. Exit 0 = xử lý/triage hoàn tất với
deferred được báo rõ, không có nghĩa 13 đã pass hoặc đã xác minh pháp lý.
Exit 1 = lỗi input/binding/runtime. Không dựng dataset/index mới.

Giữ bundle coverage, dataset và evidence review referenced trong config để
chạy lại; đây không phải gói portable độc lập. Xem
[báo cáo và lệnh](../../reviews/Blocked_Source_Context_Verification.md).
