# BM25 baseline thử nghiệm v1

Snapshot tham chiếu **2025-01-01**. Lượt này được phép tạo index BM25 thử
nghiệm; các giới hạn “chưa index” của các đợt trước là lịch sử. Không thay
schema DDD, prototype, parser, builder, encoder hoặc tạo corpus verified.

## Dataset và trạng thái

`src.retrieval_dataset` lấy toàn bộ preview thành công từ coverage đã
validate. Dataset 94 chunk cũ chỉ dùng hồi quy. Giữ proposal scope mới nhất
đúng unit/hash/coverage binding và supersedes; **không lọc scope included**.
Excluded nghĩa là proposal ngoài phạm vi nghiệp vụ, vẫn thuộc tập kỹ thuật.
Proposal và kết luận agent không phải quyết định reviewer.

Deferred gồm lỗi parser/source/context, cấu trúc chưa hỗ trợ, vượt budget
encoder 256 của tập dùng chung và bằng chứng capture rõ ràng ngoài snapshot.
Context-only không phải target bị lỗi. Source-gap records có thể chồng lấn,
không tạo unit giả hoặc cộng như các lỗi độc lập.

Dùng lại các rule text_slice đã capture. Ba liên kết bổ sung unit/hash từ
ảnh NĐ168 trang 110 Điều 53 khoản 2 chỉ dùng để lọc thử nghiệm: A6K3m,
A26K4e, A27K1b bắt đầu 2026-01-01. Config ghi finding ID, ảnh/hash và danh
sách hẹp. Không giả offsets/OCR, sửa rule/assessment cũ hoặc tạo reviewer
event. A32K1b phụ thuộc quy định môi trường chưa có ngày đủ rõ nên pending.
Không tìm thấy ngoại lệ không chứng minh đơn vị có hiệu lực tại snapshot.

Bundle chỉ chứa cây/phần nguồn DOCX, normalized/trace, hồ sơ pending,
projection coverage, proposal/revision, token evidence đã đo và evidence
được dùng. Không copy đệ quy staging history, database hoặc model weights.
Quarantine giữ đầy đủ 20 candidate/context quá dài.

Validator dùng builder cũ, replay với token evidence đúng input/hash/count;
kiểm chunk ID/hash, context, spans, raw/normalized/trace, scope history và
evidence/ngày. Không chạy encoder hoặc ước lượng token. Giữ nguyên payload,
IDs và source proofs. Manifest content SHA-256 tính trên inventory; thời
điểm chạy kỹ thuật nằm ở execution.json riêng. Proof relative với dataset.

Source, extraction/tree, technical review và applicability vẫn pending;
`experimental=true`, `release_eligible=false`, `corpus_version=null`.
Kiểm kỹ thuật không xác minh provenance DOCX hoặc lịch sử hiệu lực.

## Tokenizer và công thức

`src.bm25_tokenizer`, `vi-unicode-lexical.v1`, dùng chung index/query. Trên
bản sao: NFC → lowercase → gom Unicode whitespace → regex trong config.
Giữ dấu, đ, phủ định, số; không stopword/stemming/PyVi/BPE/expansion/boost.
Index toàn bộ text_for_search gốc; không sửa nguyên văn hoặc source offsets.

Ví dụ `đ)` → `đ`; `400.000` và `0,25` nguyên một token;
`168/2024/NĐ-CP` → `168/2024/nđ-cp`; `mg/l` nguyên token;
`10%` → `10`, `%`. Không đổi dấu thập phân/tiền tệ hoặc ghép từ đồng nghĩa.

Engine **BM25S 0.3.13**, method=lucene, idf_method=lucene, k1=1.2, b=0.75,
float32/int32, numpy backend. Đây là công thức Lucene trong BM25S, không
phải chạy Apache Lucene. Pin NumPy 2.4.6, SciPy 1.17.1; manifest còn ghi
Python/Unicode và hash mã BM25S thực cài. Implementation đã kiểm có:

`idf = log(1 + (N - df + 0.5)/(df + 0.5))`

`tf_weight = tf / (tf + k1 * (1 - b + b * length/avg_length))`

Score là tổng idf*tf_weight cho query tokens, kể cả token lặp; không tự
thêm k1+1. Điểm xếp hạng không phải xác suất hoặc độ tin cậy pháp lý.
Nguồn: [BM25S 0.3.13](https://pypi.org/project/bm25s/0.3.13/),
[mã chính thức BM25S](https://github.com/xhluca/bm25s). Run verification lưu
source/METADATA thực dùng vì nhánh main có thể thay đổi.

## Build, load và search

`src.bm25_baseline` là đường BM25S mới duy nhất. `database/bm25_store.py`
vẫn phục vụ prototype cũ; ứng dụng chưa đổi sang index thử nghiệm.

Build validate dataset trước khi ghi run, sắp chunk_id và vocab tăng dần;
mapping tường minh internal_doc_id → chunk_id/unit_id/content hash/token
count/hash. Không dựa thứ tự dòng trong file khác. Lưu CSC arrays/vocab/
params native BM25S, allow_pickle=false; chụp đúng dataset mở rộng đã gói.

Search kiểm inventory/binding/version/config/mapping/vocab/array shape rồi
load saved arrays; không gọi index() hoặc replay nguồn/encoder mỗi query,
không ghi dataset/index. Validate CLI riêng còn replay dataset và matrix
đối chiếu float32 với rtol=1e-6, atol=1e-7.

Query rỗng/chỉ dấu câu, top_k không là số nguyên dương, hash/mapping/input
sai: exit khác 0. OOV: rỗng; chỉ trả score>0, không lấp top_k bằng điểm 0.
top_k giới hạn N; tie theo score giảm rồi chunk_id tăng. Query BM25 không
chịu budget encoder. Không truncate query/document.

Kết quả giữ citation, nguyên văn, context/source proofs, URL candidate
legacy và pending. Proof tính từ dataset/ trong index. Không coi URL
candidate là bằng chứng provenance toàn DOCX.

Timing load gồm hash/read/import/kiểm mapping/load arrays; search gồm
tokenize/score/rank/ghép kết quả; không tính Python startup. Sáu smoke query
chạy process mới riêng biệt, cố định trước xem ranking. Lưu tokens/Top-5
nguyên văn/context MD/JSON. Chưa có qrels hoặc Recall/MRR/nDCG; sáu mẫu
không chứng minh p95 hệ thống hoặc chất lượng truy hồi đã nghiệm thu.
