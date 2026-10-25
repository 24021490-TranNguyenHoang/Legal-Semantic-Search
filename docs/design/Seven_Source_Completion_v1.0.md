# Hoàn thiện bảy nguồn — revision offline v1.0

Quyết định triển khai 2026-10-24, snapshot 2025-01-01. Thay giới hạn pilot bằng
inventory/ledger toàn nguồn; không sửa DDD v1, artifact hoặc code hash-bound cũ.
Nguồn/edition/applicability/review không được tự chuyển verified.

1. Tái dùng source IDs/file UUID allocation, NFC/LF, unit.v1/source-span.v1,
   encoder PyVi/PhoBERT/budget256 và composition/source proof hiện có.
   Orchestrator mới chỉ nối các bước, checkpoint ở page/file; đọc cũ không ghi.
2. QCVN: ưu tiên edition Công báo gắn đúng TT51/2024, ngày15/11/2024, thay
   reader đầu vào bằng source-set riêng gồm năm PDF theo thứ tự trang Công báo
   thật. Không ghép bản403tr và Công báo thành một văn bản dài nối đuôi. Receipt
   có URL/byte/hash/thời điểm truy cập thật. Text reader cũ vẫn giữ nguyên;
   extraction mới có offsets riêng. Chọn nguồn không là xác minh lịch sử toàn
   nội dung. OCR chỉ dùng nếu reader thay thế không đủ; không bỏ trang vì rỗng.
3. PDF page cache lưu nguyên reader text và NFC/LF, lines/bbox, tables/cells,
   image/vector inventory, trạng thái quality/content-review riêng. Resume kiểm
   source/config/output checksum, không xem file tồn tại là checkpoint đạt.
   Vùng page được phân hoạch bằng line/region có disposition; lấy được một dòng
   hoặc render không làm cả trang complete. Trích text mọi trang không đồng
   nghĩa agent đã đọc rà mọi trang/ô/hình.
4. Biểu mẫu: graph annex/form/table/cell là representation riêng, không tạo
   Khoản/Điểm giả; nhãn/giá trị/bbox/source slice và trạng thái cần đọc giữ riêng.
   Chưa chứng minh đủ nghĩa thì không thành target; excluded cần căn cứ BRD.
5. Nội dung dài: đơn vị nguồn và target giữ toàn nguyên văn/context. Thử
   representation có encoder views theo các ranh giới câu/đoạn/điểm chấm phẩy
   có thật, offsets riêng trong field; các view không phải đơn vị pháp lý hoặc
   câu trả lời độc lập. Toàn bộ view phải phủ kín source field, không truncate,
   không nâng budget. Consumer phải đọc full target/context/dependency trước
   diễn giải; không đưa một view lên như target mất điều kiện. Nếu không có
   ranh giới an toàn trong budget, giữ quarantine. Record/policy mới phải khai
   báo capability; chunk.v1 và consumer cũ vẫn replay được nguyên payload.
6. Ledger phân biệt technical extraction, structural coverage, scope proposal,
   applicability và content review. Chưa rà semantics giữ pending có công việc
   cụ thể; không dùng pending/excluded để che lỗi reader. Backlog gom theo
   law/edition/vị trí/lỗi gốc, liên kết lịch sử và crosswalk, không cộng deferred
   cơ học qua các run. “Resolved” chỉ cho điều kiện validator kiểm được.
7. Dataset candidate mới chỉ chọn proposal included có bằng chứng kỹ thuật
   và dependency đủ; supporting chỉ qua dependency cụ thể. Các bản cũ không bị
   thay. Membership/delta/identity/source branch và capability phải tường minh;
   pending scope không được suy thành included. Không đóng băng/active/index.

Giới hạn cần báo theo số thực đo: nguồn chưa định edition, vị trí text không
khôi phục chắc, nội dung phụ thuộc hình, scope chưa đọc và thiếu căn cứ lịch sử.
Không tuyên bố hoàn thành toàn bảy nguồn chỉ từ tests/ledger đầy đủ hàng.

## Chốt triển khai 2026-10-25 — candidate adapter v1.3

Không sửa schema SQL DDD v1. `unit.v1`, `source-span.v1`, `chunk.v1` và các
policy/model/preprocessing cũ giữ nguyên. Các representation mới ở lớp pending:

| Representation | Ý nghĩa và identity | Điều kiện sử dụng |
|---|---|---|
| `source-regions.v1` | `rg_` hash policy + loại vùng + source proof/bbox; cells liên kết ô vật lý | Không giả Khoản/Điểm; header/row semantics chưa rà vẫn pending |
| `qcvn-source-rule-graph.v1.1` | `qg_` hash kind/designation/parent/own text/proofs | Decimal rule không ép vào enum Khoản DDD; phân biệt lời dẫn chiếu `Phụ lục I.` với heading thật |
| `whole-record-encoder-views.v1` | `rv_` hash policy + hash source record + offsets các view | Target nguyên vẹn; view là đầu vào encoder, không là target/câu trả lời độc lập |
| `form-retrieval.v1` | `fr_` hash law/citation/raw hash/extraction/range/original/field geometry | Đọc layout/fields; không có encoder/search projection, không tự flatten thành text chunk |
| `seven-source-candidate.v1.3` | Manifest/content hash riêng; membership là danh sách target duy nhất | Consumer thiếu capability phải từ chối; corpus=null, draft, release=false |

Form identity không chứa thời điểm đọc rà; sửa field/bbox/source làm ID thay đổi.
`reviewed_at` ở sidecar chỉ là sự kiện agent đọc, không phải nguồn identity hoặc
human approval. Nguyên văn form là lát cắt extraction; nhãn, khoảng trống cần điền
và chỉ dẫn giữ từng dòng/bbox. Cả trang phải roundtrip, không chỉ giữ tên mẫu.

Offsets trên normalized extraction là Unicode code point tuyệt đối. Page cache
là code point tương đối trang và có nhãn riêng; khi export cells phải cộng đúng
page start, gắn extraction thật và tính identity mới. Encoder view offsets chỉ
áp dụng lên `text_for_search`; không dùng chúng thay source spans. Word bbox OCR
ghi pixel và PDF point với scale thật; không giả tọa độ từ text reader.

Encoder views dùng ranh giới LF/câu/dấu chấm phẩy có thật, phủ kín toàn bộ search
text. Greedy estimate chỉ đề xuất boundary; lần tokenization cuối kiểm chính
chuỗi encoder input, <=256, không truncate. Một atom dài hơn budget bị quarantine.
Giữ PyVi CPU CRF và tokenizer/revision đã chốt. Portable validation kiểm hash,
range, token IDs/count/unknown và recipe; replay tokenizer cần môi trường build,
không tuyên bố stdlib tự tái chạy BPE/PyVi.

Candidate dùng v3 nguyên byte như component lưu trữ nguồn/proof. **Không** nhập
toàn bộ 3.115 record của component vào target list. Chỉ proposal included được
chọn; pending/excluded không tự thành included. Delta `removed` là bỏ membership
ở candidate mới, không xóa payload hoặc dữ liệu nhóm đang dùng.

Phạm vi dependency mới hữu hạn: Điều34 TT35 giữ Điều66K1, Điều67 và dẫn chiếu
Luật36 Điều89K3 để đọc chuyển tiếp. Điểm a/b Khoản2 còn giữ các subtree Điều17
Khoản1–3, Điều29K3, Điều15K1b và mẫu XXVI qua Điều29K3b. Không thêm chúng vào
encoder text; không mở rộng tiếp đệ quy. Các nguồn/điều kiện cá nhân và pháp luật
khám chữa bệnh được dẫn chiếu vẫn là giới hạn, chưa thành applicability verdict.

Binding nguồn mới trong candidate gồm PDF, normalized text, trace và extraction
identity thật. Validator kiểm cả locator thuộc trang nào và range nằm trên trang,
không chỉ kiểm quote hash. Logical ref trong payload được mount vào object store
đóng gói; không fallback sang staging bên ngoài khi thiếu file. Bộ đọc trả rõ
`component_root`, `text_refs_root`, contexts, required units/spans và required form.

Policy `bounded-sibling-table-impact.v1` chỉ tách cảnh báo bảng khi chứng minh
table nằm hoàn toàn trong Điểm anh em, không chạm own text/ancestor fields đang
dùng và không có marker nằm giữa vùng bảng. Không áp dụng cho lỗi numbering,
revision hoặc xung đột ký hiệu. Issue cũ và disposition mới cùng được giữ lại.

Ledger discovery liệt kê extraction identities và alias, không chọn run mới nhất.
Bản sao thiếu logical mount hoặc test copy sai hash vào `discovery_rejected`;
không được admission. Manifest đầu vào bắt buộc vẫn fail nếu sai checksum.
Source gap và parser coverage cùng locator gộp một root group, có đủ history;
scope issue và source issue vẫn là hai điều kiện khác nhau, không cộng số nhóm
thành số đơn vị pháp lý lỗi. Page coverage có disposition không nghĩa đã đọc rà.

Changelog: v1.0 thiết kế trước code (24/10); bổ sung binding trang/trace, finite
transition/dossier/form dependencies, adapter v1.3 và kết quả kiểm thử (25/10).
Candidate thử v1–v1.2 và các run lỗi giữ nguyên để đối chiếu, không dùng làm bản
bàn giao hiện hành. Nội dung/ID của 146 member không đổi khi bổ sung adapter proof.

QCVN parser revision `qcvn-reader-boundaries.v1.2` dừng ownership annex khi đổi
serial PDF mà chưa quan sát được heading tiếp theo. Dòng continuation/heading
ảnh giữ disposition chưa xử lý; không đổ vào annex K. Identity policy riêng vẫn
`qcvn-source-rule-graph.v1.1`: chỉ node có own source payload đổi mới đổi ID.
Graph003 đổi ba annex B/G/K, giữ525 node khác và cả ba selected retrieval record
nguyên byte. Replay revision1.1 có flag tường minh và known limitation; không
âm thầm dùng chế độ cũ cho nguồn mới.

CLI guard mọi output dưới staging, input checksum trước khi tạo run, resume chỉ
partial run. Serialization replay vào temporary directory riêng rồi so byte;
artifact đã có không bị ghi đè, phần thiếu chỉ được bổ sung nếu phần hiện hữu
khớp. Discovery loại bản sao test hỏng khác với lỗi input manifest bắt buộc.
