# Phiên 6 — BM25 subset v5 experimental v1.0

Ngày 2026-10-31; snapshot **2025-01-01**. Contract này cho phép index riêng
candidate006, không sửa dataset, baseline/composition hoặc ứng dụng Hùng.

## Binding và projection

Config `source_session6.v1.json` ghim manifest/content/consumer dataset v5,
ZIP phiên5, query manifest composition-queries-001 và source BM25 hiện hành.
Validator dataset phải đạt trước khi tạo thư mục build. Membership bằng ID,
không theo title hoặc số dòng: đúng138 target (125chunk/9table/4whole).
Supporting238unit, XXVI, ancestors và encoder views không thành document.

Projection `subset-text-for-search.v1`: mọi type lấy nguyên `text_for_search`
hash-bound của record, không thêm required-read. Chunk giữ công thức hiện có;
table giữ nguyên header/row/điều kiện dẫn xuất và nguồn gốc riêng; whole giữ
toàn bộ search input, không lấy một encoder view. Recipe theo type, hash text,
tokens, payload và document→record mapping được lưu/kiểm lại khi load.
Budget encoder256 không áp lên BM25, không truncate/chia target.

## Engine và search

Index version `vtls-bm25s-subset.v1`; adapter `subset-bm25-adapter.v1`.
Tái dùng nguyên byte `composition_bm25.create`, `bm25_baseline.engine/rank`,
config và `bm25_tokenizer`: BM25S0.3.13 Lucene, k1=1.2,b=.75, float32/int32,
NumPy backend; lexical NFC/lowercase/Unicode whitespace/regex v1; không tuning.
CPython cùng minor, Unicode/dependency/source-engine khớp, patch khác được ghi
cảnh báo theo runtime compatibility v1. Provenance ghi cả môi trường tạo/chạy.

Rank baseline tính score trên toàn index; adapter áp AND của source_id/law_id/
record_type trên danh sách positive đã sắp rồi mới lấy top_k. Không thay thống
kê corpus theo filter. Mỗi filter là một giá trị chính xác; ID nguồn hợp lệ có
thể không có target (SRC-004), trả rỗng. Filter không hợp lệ bị từ chối. Tie:
score giảm rồi record_id Unicode tăng. BM25S Lucene có contribution không âm;
chỉ score>0 là lexical candidate, không là confidence hoặc relevance threshold.
Top_k là int>0, không padding; query rỗng/chỉ dấu câu hoặc chỉ % không chứa
letter/number bị từ chối theo baseline; OOV/no lexical match trả danh sách rỗng.
Search chỉ đọc: thiếu/sai index/dataset/asset/mapping lỗi, không tự build/fallback.

Hit có ID/type/rank/score/source/law/citation/dataset/index version và detail ID;
snippet chỉ để điều hướng. Read gọi consumer.py của đúng dataset đã bind,
trả nguyên response record/context/proofs/required_read/proposal/pending, thêm
binding index ở envelope riêng; không formatter làm mất field hoặc join title.
Read chỉ nhận target ID. Consumer cần mọi capability trong dataset, gồm table,
whole, graph Part, required-read và supporting form; không cast type.

## Validation, batch và handoff

Load kiểm inventory/hash/source/runtime/config, consumer full validation và
mapping tái projection, vocab/CSC/config. Validate riêng rebuild matrix và đối
chiếu tolerance1e-6/1e-7; search không rebuild. Mọi code copy hash-bound gồm cả
adapter. Manifest có dataset/content/consumer hash, membership/search hashes,
engine/config/runtime, filters/tie/top_k contract. Timestamp thực thi ở receipt
ngoài index, không phải ngày thu thập hoặc lịch sử hiệu lực.

Batch dùng đúng30old+15new+5limit, byte/hash nguyên artifact composition đã seal.
Load một lần; lưu raw per-query, run, query timings, detail duy nhất +hash và
pending annotation riêng. Kiểm ID/type/version và exact required closure của
mọi hit. Không chuyển qrels/nhãn v1/v3; metrics=null/PENDING_LABELS. Nhận xét
coverage dựa membership/dependency, không suy gap từ ranking miss.

ZIP chứa index, dataset nguyên byte, runtime source/config,50query gốc và pins
dependencies; không venv/cache/model. Test portable dùng ZIP giải nén, venv sạch
cài offline wheels đã có, audit chặn đọc repo/staging/cache gốc và network.
Chạy validate/rebatch/all unique hit read/full-read138, so ID/score/hash response.
Không gọi thử cùng máy là kiểm OS/máy khác. Timing load+validation khác ranking
khác hydration; batch tuần tự không warmup không là benchmark/SLA.

Experimental/release=false/corpus=null/source-edition-applicability pending,
scope proposal, origin=agent_review; không human event/accepted/legal verified.
Không sửa dataset/index/query/qrels/ZIP lịch sử, build Dense/embedding/Qdrant,
UI/API/merge/chuyển bản nhóm hoặc stage/commit/push.
