# Trạng thái dataset và BM25 experimental

**DEV_RUN_COMPLETE / LABELS_PENDING / SHARE_PENDING** — đã thử chạy độc lập trong clone
cục bộ và venv sạch trên máy hiện tại; **chưa có URL chia sẻ** artifact.
Snapshot sản phẩm **2025-01-01**; đây chưa phải corpus phát hành.

## Source và binding

Commit đầu lượt 13 source/context candidate: `cc465dafe7015fe4bb748107b43e5d49e4f91a8c`;
Git sạch khi bắt đầu. Công việc Điều lá/evaluation đã được commit trước đó.
Thay đổi hiện tại là hồ sơ đối chiếu và parser disposition layout hẹp;
chưa stage/commit/push. Dataset/index/query set, tokenizer/ranking và các
module parser/builder cũ giữ nguyên byte để replay artifact bàn giao.

| Artifact | Giá trị đọc từ manifest thực tế |
|---|---|
| Index | `staging/bm25-baseline-v1-001/index_manifest.json` |
| Index version | `vtls-bm25s-lucene.v1` |
| Dataset gắn trong index | `staging/bm25-baseline-v1-001/dataset/dataset_manifest.json` |
| Dataset version | `vtls-coverage-experimental.v1` |
| Chunk / context | **3.077 / 5.371** |
| Dataset content SHA-256 | `2534731881e493a9b1b47b07470cc5d7f4fabbd9553d4e4d6c59e27359b313b5` |
| Dataset manifest SHA-256 theo index binding | `2aa5dc595dab7614920ce94317b85c7b21e188cc35b16b54bef9e81f3ccf1b0a` |
| Index content SHA-256 | `629f0214096d7ea013039af9253a5ed8f10f273f89da16f8cd56c69ff7130d18` |

ZIP hiện có được tái sử dụng nguyên byte:
`staging/bm25-baseline-v1-001.zip` (33.424.920 byte), SHA-256
`8678cd66620cbacfae7443e9e0774ac36f8294aeb6edceebf1e06cfaa789d03e`.
File `.zip.sha256` cùng thư mục. Gói gồm index (đã chứa dataset) và bản
dataset standalone giống nhau; không chứa venv/cache/lịch sử staging.

## Đã kiểm chứng trong lượt bàn giao

- ZIP có 113 file, hai root đúng phạm vi; từng byte khớp artifact, hash và
  binding dataset/index đạt. Không build lại artifact hoặc sửa dữ liệu.
- Clone cục bộ từ commit base, áp source bàn giao; venv mới chỉ cài
  bm25s 0.3.13, NumPy 2.4.6, SciPy 1.17.1; pip check đạt. Validate toàn
  gói và search không cần staging upstream hoặc model packages.
- CLI validate exit 0: 3.077 document, source/spans/dataset/matrix replay
  đạt; không ghi index. Query vòng xuyến và OOV exit 0. Top-5/điểm/nguyên
  văn/proofs của query mẫu giữ nguyên so với baseline có sẵn.
- Search thử với audit hook cấm đọc phần workspace ngoài clone: đạt;
  không import Torch/SentenceTransformer/Transformers/PyVi/Qdrant.
- Runtime giữ nguyên manifest/config/engine/dependency/Unicode/mapping
  checks. Chỉ bỏ so sánh tuyệt đối Python patch trong cùng CPython minor,
  có cảnh báo và thông tin môi trường tạo/chạy. Chỉ nhận code binding
  hiện hành hoặc fingerprint loader v1 gốc; tokenizer phải khớp chính xác.
- Kiểm thử tập trung: 16 test đạt và một test bổ sung về cảnh báo patch
  đạt. Patch khác được **mô phỏng policy**, không chạy interpreter khác.
  Không lặp suite tốn thời gian toàn pipeline khi thuật toán không đổi.
- Máy thực thử: Windows 10.0.26200, CPython 3.11.9 / Unicode 14.0.0.
  Validate khoảng 23,15 s; query mẫu load khoảng 886,85 ms, search 14,96 ms.
  Số đo đơn lẻ phục vụ bàn giao, không chứng minh p95/hiệu năng toàn hệ thống.

Evidence thực thi: `staging/bm25-handoff-001/` chứa state, execution logs,
package audit, focused tests, isolation/modules và preservation checks.
Hướng dẫn: [BM25 Quickstart](../handoff/BM25_Quickstart.md).

## Pending và giới hạn

Nguồn DOCX legacy chưa rõ lịch sử tải; extraction/cây và technical review
vẫn pending. Scope trong tập kỹ thuật là proposal: 94 included, 64 excluded,
2.919 pending, không phải quyết định reviewer. Applicability chưa xác minh
toàn bộ tại snapshot; bốn ngoại lệ có evidence được giữ ngoài tập. Tổng
46 target deferred (20 quá dài, 13 source/context lỗi, 9 chưa hỗ trợ,
4 ngoại lệ snapshot); source-gap records giữ riêng, có thể chồng lấn.
`experimental=true`, `release_eligible=false`, `corpus_version=null`.

Query còi ban đêm, phân biệt xe máy/chuyên dùng và điểm GPLX còn failure
case. Chưa có qrels được chấp nhận hoặc Recall/MRR/nDCG thực. Số test/validate kỹ thuật không
chứng minh chất lượng pháp lý, nội dung hoặc retrieval đã nghiệm thu.
Chưa kiểm trên máy khác, OS khác, Python patch khác hoặc remote clone
qua mạng; thư mục sạch trên máy này không phải kiểm chứng liên máy.

## Bước tiếp theo

Long/nhóm cần rà query, positive ngoài pool, nhãn và độ đầy đủ theo
[Evaluation Quickstart](../handoff/BM25_Evaluation_Quickstart.md).
Sau đó mới có metrics development; không coi chúng là test cuối.
Dense trên cùng dataset/chunk_id/text_for_search vẫn là bước tiếp theo,
chưa triển khai. Chưa có URL chia sẻ artifact.

## Development evaluation thực chạy

- `staging/bm25-evaluation-dev-001/`: 30 câu/10 intent, mỗi intent có
  direct/paraphrase/scenario; năm câu smoke nghiệp vụ giữ nguyên. Query
  cố định trước ranking, không sửa sau xem kết quả.
- Load index một lần, 30 query thành công, 300 kết quả Top-10, không lỗi.
  Load 1.658,79 ms; tổng search 100,82 ms, tuần tự, không warmup.
  Đây là số đo một lần trên máy hiện tại, không phải SLA.
- Phiếu chứa nguyên văn/context/source spans cho 300 cặp. Submission ở
  `staging/bm25-evaluation-review-001/` có 5 proposal agent, 295 pending,
  **0 accepted**. Không ghi người dùng đã duyệt.
- `staging/bm25-evaluation-labels-001/`: validate/score đạt về cấu trúc;
  0/30 query đủ điều kiện, 30 loại vì rà độ đầy đủ nhãn pending.
  **metrics=null**, chưa có corpus coverage gap được kết luận; cả 30 câu
  cần khảo sát độ đầy đủ. Không nhầm thiếu hit Top-10 với thiếu trong corpus.
- 18 fixture evaluation + 14 regression BM25 đạt (32 tổng). Kiểm công thức
  tính tay, graded/multiple positive, cutoff, nhãn thiếu, lỗi, trùng, binding.
  Không dùng số test làm kết luận pháp lý hoặc chất lượng retrieval.
- Báo cáo: [BM25 Development Evaluation Verification](../reviews/BM25_Development_Evaluation_Verification.md).

## Chín Điều lá — ứng viên phiên bản dữ liệu tiếp theo

Run đề nghị xem: `staging/leaf-articles-preview-002/`, policy
`leaf-article-title-context.v1`. Cả 9 Điều có preview kỹ thuật, 0 blocked,
0 quarantine; token 31–139, unknown=0, budget 256/preprocessing không đổi.
Title chính Điều là heading context; target giữ trọn nội dung riêng, không
lặp body thành context. Source spans và paragraph DOCX được đối chiếu.

Proposal scope hiện có: 7 excluded, 2 pending; không có quyết định mới.
Nguồn/extraction/cây/applicability vẫn pending, release_eligible=false.
9 preview **chưa nhập dataset 3.077 chunk**, chưa thay index hoặc query set.
Không xử lý 20 trường hợp dài hoặc 13 lỗi nguồn/context của tập bàn giao.
Bước evaluation/Dense của nhóm tiếp tục trên dataset đã bàn giao nguyên vẹn.

Chi tiết và kiểm chứng: [Stage6 Leaf Article Verification](../reviews/Stage6_Leaf_Article_Verification.md).

## 13 candidate source/context — đã đối chiếu, chưa cập nhật dataset

Run cuối đề nghị xem: `staging/blocked-source-repair-003/`.
13 candidate → 6 nhóm vùng nguồn; 10 issue parser tại 8 locator, thêm một
paragraph continuation cách ly không có issue riêng. Đã xem tám trang
ảnh từ hai PDF capture cũ; không tải thêm nguồn, không OCR.

- 10 candidate NĐ168: DOCX khác ký hiệu trên PDF scan, không phải parser
  cần nới để nhận literal sai. Giữ deferred; cần nguồn text hoặc cơ chế
  transcription/mapping scan có truy vết trước khi dựng extraction mới.
- 2 Khoản Luật35 có bảng sửa đổi: giữ deferred, chưa triển khai bảng tổng
  quát; scope một pending, một excluded proposal.
- 1 Khoản Luật35 Điều86K2: disposition graphic line rỗng sau thân luật vào
  layout trong projection mới, units/spans giữ nguyên. Preview 77 token,
  unknown=0. Scope excluded proposal giữ nguyên; nguồn/hiệu lực pending.

Kết quả: 1 preview kỹ thuật, 12 deferred trong run riêng. Tập bàn giao vẫn
3.077 chunk; danh sách deferred cũ không bị viết lại. Không tạo reviewer
quyết định, sửa raw/offset cũ hoặc nhập preview vào dữ liệu evaluation.
Chi tiết: [Blocked Source Context Verification](../reviews/Blocked_Source_Context_Verification.md).
