# Hiện tại — relevance review composition (2026-10-24)

**AGENT_REVIEW_RECORDED / CALIBRATION_PENDING / METRICS_NULL**.
Snapshot2025-01-01; dataset/index/query/ranking gốc bất biến. Run mới
`staging/composition-relevance-review-001/`, rubric `composition-relevance-review.v1.1`.
Đã xét500cặp/50query,313detail:497proposed (377nhãn0/57nhãn1/63nhãn2),
3pending/null do loại xe chưa rõ;28full/35partial trong nhãn2. Khôngaccepted.

33positive-pairs ngoài pool cho24devquery; thêm1dependency-only cho limitL05,
tổng34pairs/17records.45dev tìm sâu nguyên query Top100,4.500hits chưa chấm
toàn bộ;101record khảo sát citation. Coverage50câu là agent proposal hữu hạn,
không chứng minh hết relevant; unjudged không là0. Source-only/withheld không
thành target qrels.300proposal v1 có binding riêng; không chuyển nhãn cũ.

Validator bundle seal exit0;27tests liên quan đạt.715file input của phiên
giữ hash; baseline962 trước chỉ khác3tài liệu có sẵn, không sai lệch artifact
bảo vệ. Logs `staging/composition-relevance-review-checks-001/`.
Metricsnull/qrelsrỗng/human events0; nguồn/edition/scope/applicability pending.
Dataset/index v1 nhóm dùng3.077, draft3.082/v3, ZIP/evaluation không đổi.

Bước tiếp: rà10query/19cặp trong `calibration.md`, trả bản sao template ngoài
bundle seal. Chấp nhận mẫu không chấp nhận500nhãn/coverage. Scorer accepted
composition có table chưa triển khai; chỉ làm sau khi thực sự có nhãn đủ điều
kiện. Chưa tuning, rebuild, Dense/embedding/index mới hoặc chuyển bản cho nhóm.

[Rubric](../design/Composition_Relevance_Review_v1.1.md),
[hướng dẫn phiếu](../handoff/Composition_Relevance_Review.md),
[bằng chứng và giới hạn](../reviews/Composition_Relevance_Review_Verification.md).

---

# Lịch sử — BM25 composition experimental (2026-10-23)

**INDEX_READY / SEARCH_READ_PASSED / V3_LABELS_PENDING**. Index riêng
`staging/bm25-composition-001/`, version `vtls-bm25s-composition.v1`, bind
nguyên dataset-v3-draft-005 (`vtls-coverage-experimental.v3-draft.1`), snapshot
2025-01-01.3.106text +9table =3.115documents, không index dependency/withheld.
BM25S Lucene/tokenizer/preprocessing/params v1 giữ nguyên; không lọc scope.
Consumer đọc Part/table/source proof và đầy đủ required-read theo IDs/mounts.

Queries đã seal trước ranking:30dev cũ nguyên byte,15dev corpus-derived mới,
5limit. Run `staging/bm25-composition-evaluation-001/`:50query/500Top10,
313detail,0queryerror.500annotations pending,0accepted/qrels, metrics=null.
V1 regression30query khớp ID/score; trênv3 có12Top10 và1Top1 thay đổi, chưa
kết luận retrieval tốt hơn. Query form/QCVN/y tế chi tiết/rain dependency có
coverage observations từ selection/graph, không suy gap chỉ từ Top10.

Index+dataset đã thử copy độc lập, venv mới cài offline đúng bm25s/numpy/scipy,
validate/search/read đạt với audit gate chặn workspace ngoài folder thử.
Cùng Windows/Python3.11.9, chưa OS/máy khác. Dataset validate/read stdlib;
index search cần sparse dependencies. Tests/binding không xác minh pháp lý.

Bản nhóm đang dùng vẫn dataset/index v1 **3.077**, draft3082 và draftv3 giữ
nguyên; evaluation/qrels/ZIP cũ không đổi. Scope/source/edition/applicability
pending/proposed; khônghumanreview, khôngindexactivate/app/Dense/embedding.

[Quickstart](../handoff/Composition_BM25_Quickstart.md),
[verification và hash](../reviews/Composition_BM25_Verification.md),
[contract](../design/Composition_BM25_Contract_v1.0.md).
Bước tiếp: người phụ trách evaluation rà relevance/direct-vs-dependency và
độ phủ nhãn v3; chưa tự chuyển qrels hoặc yêu cầu nhóm đổi phiên bản.

---

# Lịch sử — draft composition TT38/TT35 (2026-10-23)

**EXPERIMENTAL_DRAFT_BUILT / PORTABLE_VALIDATION_PASSED / LEGAL_REVIEW_PENDING**.
Run `staging/dataset-v3-draft-005/`, version
`vtls-coverage-experimental.v3-draft.1`, snapshot2025-01-01, draft/experimental,
release_eligible=false, scope proposed, nguồn/edition/applicability pending.
Không human review. Nhóm vẫn dùng dataset/index v1 **3.077**; draft cũ **3.082**
giữ nguyên, không đổi evaluation/qrels/ZIP hoặc yêu cầu chuyển phiên bản.

Draft mới: **3.106 text chunk +9 table records =3.115 retrieval records**,
5.413 encoder contexts;23 required-read dependency bindings. Delta giữ3082,
thêm24text (8TT38+16TT35) và9table;0replaced/removed/conflicted.13 withheld:
9TT35 thiếu biểu diễn form/reference,1TT38 b279token,3TT51 conditional.
Không nhậpQCVN/572previewTT35, không thay tokenizer/preprocessing/budget256.

Adapter dùng composition components và resolver mounts, giữ payload/ID;
Part/Chapter TT35 và table-retrieval.v1 có contract riêng. Required-read source
subtrees bind chính xác; không ghép thêm vào encoder. Consumer không hỗ trợ
Part/table/dependency phải fail. Validate/read đã thử trong folder độc lập,
venv stdlib sạch trên cùng Windows, audit hook chặn đọc ngầm workspace khác.
Chưa kiểm máy/OS khác. Không index/embedding/retrieval hoặc xác minh pháp lý.

[Báo cáo và lệnh chạy](../reviews/Circular_Dataset_Draft_Verification.md),
[contract](../design/Circular_Dataset_Composition_v1.0.md),
[ingestion guide](../ingestion.md). Bước tiếp nếu được phép: consumer/index
revision, bind version/hash và evaluation phù hợp; chưa triển khai trong phiên.

---

# Lịch sử — ưu tiên TT38/TT35 và pilot QCVN (2026-10-23)

**PRIORITY_PREVIEW_COMPLETE / LEGAL_REVIEW_PENDING / DATASET_ADAPTER_PENDING**.
Snapshot2025-01-01. Dataset/index v1 **3.077** và draft **3.082** giữ riêng,
ba Thông tư chưa nhập; evaluation/qrels/ZIP không đổi. Không stage/commit/push.

Run `staging/circular-priority-006/`:46 dòng rà soát, gồm8 TT38 text,
9 table retrieval records đạt budget,1 Điểm b279 token quarantine,
25 TT35 text đạt71–184 token/2unknown,3 TT51 supporting conditional.
TT35 graph mới783 nodes có7Phần/9Chương thật; crosswalk giữ root,766 unit
đổi ID và16 ancestors mới. Graph/schema pending revision riêng, không sửa
schema DDD v1; adapter dataset hiện hành chưa hỗ trợ Part/table records.
Nguồn/edition/applicability pending, scope chỉ agent proposal.

Pilot `staging/qcvn-pilot-002/` chỉ PDF7/214/300/368: render/reader và phiên âm
hẹp từ ảnh,0QCVNchunk. Font chưa giải mã tự động, không có OCR executable;
214/300/368 vẫn phụ thuộc hình/bảng, không suy ý nghĩa biển từ hình.
Chưa có bằng chứng để mở rộng tự động toànQCVN.13+4 ca TT35 ngoài nhóm ưu
tiên giữ backlog; chưa rà toàn463preview pending hoặc toànannex.

Chi tiết: [verification](../reviews/Circular_Priority_QCVN_Pilot_Verification.md),
[contract v1.2](../design/Circular_Priority_Representation_v1.2.md),
[lệnh chạy](../ingestion.md). Kiểm tra kỹ thuật không xác minh pháp lý/retrieval.
Bước tiếp: adapter draft revision cho graph/table + rà dependency có mục tiêu;
chưa đủ đóng gói bằng adapter v1, chưa yêu cầu nhóm chuyển phiên bản.

---

# Lịch sử — trạng thái dataset và BM25 experimental

**DEV_RUN_COMPLETE / LABELS_PENDING / SHARE_PENDING** — đã thử chạy độc lập trong clone
cục bộ và venv sạch trên máy hiện tại; **chưa có URL chia sẻ** artifact.
Snapshot sản phẩm **2025-01-01**; đây chưa phải corpus phát hành.

**Cập nhật7 nguồn/TT38:** đã đăng ký7 văn bản/10 file pending;4 văn bản trong
dataset/index v1,3 Thông tư chưa được nhập. TT38 có preview riêng, xem bảng
cuối trang và [ingestion guide](../ingestion.md). Các mục trước cập nhật này
được giữ làm lịch sử theo từng lượt.

## Source và binding

Commit đầu lượt draft: `aee22f0173affc406cfccc443a9132c43c1c98fb`.
Đầu lượt đã có thay đổi recovery A16K2 chưa commit (README/STATUS và năm
file config/contract/report/code/test); đã bảo toàn. Lượt này thêm adapter
composition draft, config/contract/tests/report và hướng dẫn. Chưa stage/
commit/push. Dataset/index/evaluation/ZIP bàn giao và các module cũ giữ nguyên.

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

## NĐ168 Điều16 Khoản2 — đã khôi phục experimental riêng

Run cuối: `staging/nd168-a16k2-preview-004/`. Đã capture text chính thức
trên Cổng Chính phủ và đối chiếu đủ title/lead/năm Điểm với ảnh scan40–41
đã lưu; không cần phiên âm/OCR. HTML tải 2026-10-22, bài hiển thị2025-04-03;
không coi đó là bản website lịch sử tại snapshot. Applicability vẫn pending.

10 units/10 spans trong cây chọn lọc, 5 Điểm a/b/c/d/đ có preview, 0 quarantine,
0 blocked; token101/143/187/121/212, unknown=0. Hai vùng d/đ trước không có
unit nay có extraction/spans mới; không sửa marker trên DOCX hoặc offsets cũ.
Bảng comparison/crosswalk giải thích đầy đủ ID đổi do identity của cha/field
biểu diễn mới, không do ép phiên bản/source ID vào unit identity.

Scope proposal mới: 5 included targets, title/lead supporting đúng dependency;
không có quyết định reviewer hoặc xác nhận hiệu lực. Chưa nhập dataset3.077,
chưa sửa index/query/evaluation/ZIP. Không mở rộng Điều39/40 hoặc bảng Luật35.
Chi tiết: [ND168 A16K2 Recovery Verification](../reviews/ND168_A16K2_Recovery_Verification.md).

## Bản draft tiếp theo — chưa chuyển bản cho nhóm

`staging/dataset-v2-draft-001/dataset_manifest.json`, version
**vtls-coverage-experimental.v2-draft.1**, policy
`coverage-source-branches-draft.v1`, status=draft:

- 3.082 chunk/5.381 context; **added5, unchanged3.077, replaced0, removed0,
  conflicted0**, duplicate0 sau đối chiếu toàn dataset theo vị trí/nội dung/ID.
- Dataset content SHA: `729bc28b63f773de9d4f5c35c8d77c5f53c5311fa64f7d9c49e8e69496b376be`.
- Manifest SHA: `42c59623d6d921429cd45f2bdfaab3deabab002efa4f13e8720b9645d8944237`.
- Hai component nguồn độc lập giữ nguyên cây/proofs. Cha DOCX (document
  NĐ168 có628 code points own text) không bị own text chưa chọn của HTML đè.
  Metadata graph/membership là sidecar pending, không sửa schema DDD/ID.
- a/b/c trước có unit deferred, chưa có chunk; d/đ chưa có unit/chunk.
  Ba hồ sơ deferred cũ có alternate-source targets trong draft;43 còn lại
  được giữ. Cả46 hồ sơ và issue DOCX gốc vẫn bất biến trong base component.
- Scope của năm target chỉ proposed included; source/edition/technical và
  applicability pending tại2025-01-01. Không reviewer events hoặc corpus
  verified. Không thêm chín Điều lá, L35 A86K2 hoặc20 trường hợp dài.

Build/validate và30 tests tập trung đạt; đối chiếu exact3077 chunk/5371
context/3077 metadata cũ đạt. Kiểm kỹ thuật không chứng minh chất lượng
pháp lý/retrieval. Bản đang dùng của nhóm vẫn **v1 3.077 chunk** cùng index,
query/evaluation và ZIP cũ; không build index draft hoặc chuyển qrels.
Evaluation/Dense tiếp tục trên cùng v1; nếu thử draft sau này, phải bind
version/hash mới và rà coverage/nhãn/ranking, không dùng index v1 cho draft.
Chi tiết: [Experimental Dataset Draft Verification](../reviews/Experimental_Dataset_Draft_Verification.md).

## PDF Thông tư35/38/51 — đã kiểm tra và đăng ký pending

Lượt kiểm tra bắt đầu tại commit `2aebab4e4cbc10c4b550a1571855c0fe3bd9d278`;
đầu lượt chỉ có5 PDF người dùng thêm chưa tracked. Config mới
`config/source_registration.circulars.v1.json` giữ Source Inventory IDs
SRC-005=TT38, SRC-006=TT51, SRC-007=TT35. Không lẫn với Luật35/QH15.

- 5 file local: TT35 chính69tr/phụ lục179tr; TT38 chính7tr; TT51 chính1tr/
  QCVN41:2024 kèm403tr. Tên/kích thước khớp attachments chính thức.
- TT38 local trống số/ngày, kể cả ảnh; GET attachment Chính phủ xác nhận
  byte-identical. Bổ sung riêng Công báo8tr trong staging có số/ngày đầy đủ,
  không ghi đè raw. Không tải lại bốn PDF35/51; remote full-hash còn chưa kiểm.
- QCVN có100 trang PDFium không lấy được text; ảnh trang214 không trắng.
  pdfplumber mẫu đầu có NUL. Cần xử lý reader/hình/bảng ở bước extraction,
  chưa OCR hoặc bỏ nội dung. Lời nói đầu QCVN còn trống số thông tư.
- Run `staging/circulars-registration-001/`:3 documents/6 files pending,
  SQLite FK/integrity/schema/ID/hash đạt; `content.sqlite` vẫn0 bản ghi.
- `staging/circulars-source-check-001/source_metadata.csv` và observed JSONL
  lưu hash/IDs/URL/relationships/capture facts riêng. Năm local không có log
  retrieved_at lịch sử; không hồi điền ngày hiện tại. Source/applicability
  và full-content review pending, origin=agent_review, không human approval.

Validate/register và18 tests Stage2 đạt; require-release-ready exit1 đúng
chính sách.10 raw giữ nguyên hash; dataset/index v1, draft3082 và ZIP giữ
nguyên inventory/hash. Không thay dataset nhóm dùng hoặc nạp nguồn mới vào
chunk/index. Chi tiết: [Circulars Source Registration Verification](../reviews/Circulars_Source_Registration_Verification.md).

## Đồng bộ7 nguồn và xử lý TT38 — chưa cập nhật dataset/index

HEAD đầu lượt `2aebab4e4cbc10c4b550a1571855c0fe3bd9d278`; bảo toàn config,
báo cáo, STATUS và5 PDF untracked có trước. Config tổng hợp mới là
`config/source_registration.seven.v1.json`; snapshot vẫn2025-01-01.

| Source | Law | Registered files | Extraction / parse | Dataset/index v1 |
|---|---|---:|---|---:|
| SRC-001 | 36/2024/QH15 | 1 | DOCX đã xử lý; PDF Điều22 riêng | 788 chunk |
| SRC-002 | 168/2024/NĐ-CP | 1 | DOCX đã xử lý; HTML A16K2 riêng | 1.018 chunk |
| SRC-003 | 35/2024/QH15 | 1 | DOCX đã xử lý, còn bảng/vùng deferred | 664 chunk |
| SRC-004 | 165/2024/NĐ-CP | 1 | DOCX đã xử lý | 607 chunk |
| SRC-005 | 38/2024/TT-BGTVT | 2 | Công báo8tr extraction/parse/preview riêng; PDF7tr đối chiếu | 0 |
| SRC-006 | 51/2024/TT-BGTVT | 2 | Đăng ký main/QCVN, chưa pipeline extraction | 0 |
| SRC-007 | 35/2024/TT-BGTVT | 2 | Đăng ký main/annex, chưa extraction/parse/chunk | 0 |

Đăng ký7/10 là manifest tổng hợp gồm4 DOCX và6 PDF; không tính mọi PDF/HTML
bằng chứng cũ là thêm nguồn pháp lý, không giả các nguồn đã verified. Tất
cả source/edition review và applicability pending;4 văn bản cũ và TT38 có
agent scope proposals, TT35/TT51 chưa assessment đơn vị.

Nguồn TT38 bền vững:
`data/raw/official/38-2024-TT-BGTVT/congbao-1355-1356.pdf`; capture/evidence
trong `data/source_evidence/circulars-2024/`. Copy giữ nguyên SHA/file_id,
không ghi đè bản7tr hoặc PDF trong staging cũ. Metadata mới:
`staging/seven-sources-export-003/source_metadata.csv` và progress/crosswalk
JSONL; CSV cũ giữ nguyên. Một alias SRC-004 ở nhánh HTML NĐ168 được map
vềSRC-002 theo law+artifact, không thay chunk/ID hoặc alias toàn cục.

TT38 run chính `staging/tt38-preview-003/`, Stage3
`staging/tt38-extraction-001/`:12.694 code points,8 page locators,0 lỗi/
warning extraction;59 units (1 document/3 chương/12 điều/32 khoản/11 điểm),
180 spans. Coverage: parsed10.058; supporting1.173; unprocessed bảng1.285;
source layout171; separator trang7, tổng đúng12.694.

42 leaf candidates →38 preview/56 context,4 blocked do bảng/cross-reference:
A6K1, A6K2, A11K2a vàA11K2b.0 over-budget,59–168 token gồm special, unknown0.
3 bảng/33 physical cells/9 rows dẫn xuất được giữ riêng trong quarantine,
có loại đường/xe, đơn vị/điều kiện và source slices/bbox. Chưa table chunk
policy; không truncate hoặc tạo chunk có vẻ đủ từ phần mất bảng.

BRD/SRS/SDD/DDD gốc giữ nguyên byte; chỉ thêm addendum/changelog vì bốn
nguồn là khởi đầu, không giới hạn đích. README/AGENTS/ingestion guide cập
nhật trạng thái thật.78 tests tập trung và9 tests Điều lá đạt; kiểm tra/tái lập/tampering và
giới hạn chi tiết trong [Seven Sources TT38 Verification](../reviews/Seven_Sources_TT38_Verification.md).
Dataset3077/index/evaluation/ZIP và draft3082 không được cập nhật. Chưa
chạy embedding/index, chưa OCR TT51 hoặc yêu cầu nhóm chuyển phiên bản.

## Hoàn thiện ingestion ba Thông tư — 2026-10-23

Mục này cập nhật trạng thái hiện tại; các mục phía trên là lịch sử.
HEAD kiểm tra `3faaf98946ac24ff5abbf2bdd38e53d1c8975ecb`, có thay đổi chưa
commit cho ingestion; không stage/commit/push. Snapshot giữ2025-01-01.
Contract [Circulars addendum v1.1](../design/Circulars_Ingestion_Addendum_v1.1.md),
[báo cáo và bằng chứng](../reviews/Circulars_Ingestion_Completion_Verification.md),
[lệnh tái chạy](../ingestion.md).

Metadata cuối: `staging/seven-sources-export-006/`, 7 văn bản/10 file.
URL Công báo TT38 đã sửa thành scalar252 ký tự bằng receipt/HTML/hash;
CSV đọc được bằng csv.DictReader mặc định và khớp JSONL. 6 download_url có
căn cứ,4 DOCX null;9 retrieved_at lịch sử null. Export lỗi được giữ nguyên.

| Nguồn | Extraction / preview hiện tại | Giới hạn | Dataset/index |
|---|---|---|---|
| SRC-001 Luật36 | DOCX; PDF Điều22 riêng | Pending pháp lý | v1:788 chunk, giữ nguyên |
| SRC-002 NĐ168 | DOCX; HTML A16K2 riêng | Nhánh khôi phục chỉ trong draft | v1:1.018 chunk, giữ nguyên |
| SRC-003 Luật35/QH15 | DOCX | Còn vùng chưa xử lý | v1:664 chunk, giữ nguyên |
| SRC-004 NĐ165 | DOCX | Pending pháp lý | v1:607 chunk, giữ nguyên |
| SRC-005 TT38 | Công báo8tr; tt38-tables-003:38 chunk cũ +9 preview hàng bảng | Điểm b A11K2:279 token; hàng bảng chưa biểu diễn chunk DDD | Chưa nhập |
| SRC-006 TT51 | tt51-extraction-005:1+403tr; tt51-preview-003:3 supporting chunk | QCVN partial:100 trang không text,302 trang U+FFFE,0 target QCVN | Chưa nhập |
| SRC-007 TT35/TT-BGTVT | tt35-extraction-001:69+179tr; tt35-preview-005:767 unit,572 chunk/1.070 context | Cây thưa Phần/Chương;13 source/context blocked,4 quá budget;179tr annex chưa grammar | Chưa nhập |

TT38 đã có kết luận cho cả4 đơn vị bị bảng chặn: A6K1→1 row, A6K2→4 rows,
A11K2a→4 rows; A11K2b giữ dependency đầy đủ và quarantine279. Chín preview
đạt137–168 token,unknown0, giữ33 cells/spans; ID tp_ riêng, chưa phải chunk DDD.

TT35 có133 unit scope proposal (25 included/27 supporting/81 excluded),634
pending. 572 preview kỹ thuật gồm25 included,15 supporting,69 excluded,
463 pending.11 unknown trong preview đạt budget; hai included A15K1b/A15K2b
mỗi target có1 unknown tokenizer, không sửa nguyên văn/preprocessing.
148 bảng/cụm ô đo được,5.541 cells,28 image objects/9 trang annex;
3 vùng annex proposed supporting,176 trang khác pending. Phần/Chương thật
giữ sidecar/dependencies; chưa đủ cây cha DDD chính thức.

TT51 main complete độc lập; QCVN reader hoàn tất nhưng extraction partial:
61.891 U+FFFE,402 issue, validate-reader trả1 đúng chính sách. Không xóa NUL/
noncharacter hoặc gọi text rỗng là trang trắng.403 trang bảng chưa đo layout;
root image inventory quan sát4.057 objects/254 trang,177 trang vector,
59 trang inventory chưa đầy đủ. Chưa OCR/hiểu hình; toàn QCVN giữ unprocessed.

98 tests liên quan đạt;11 focused tests chạy lại đạt sau bổ sung assertion.
7 tampering cases bị từ chối;5.541 cell bindings khớp;572 TT35 ID/content
không đổi khi thêm blocker cấu trúc.281 file baseline được bảo vệ giữ nguyên.
Các số này là kiểm chứng kỹ thuật, không kết luận pháp lý hoặc retrieval.
Chưa thử môi trường sạch/OS khác trong lượt này.

Nguồn/edition/applicability còn pending, scope chỉ agent proposal; ngày hiệu
lực chung có source spans nhưng chưa đánh giá ngoại lệ/sửa đổi cấp unit.
Không human reviewer event. Bản nhóm đang dùng vẫn dataset3077/index/evaluation/
ZIP v1; draft3082 riêng, cả ba Thông tư chưa nhập. Evaluation và Dense của nhóm
tiếp tục trên cùng dataset v1; lượt ingestion này không chạy chúng.

Ứng viên cho đợt dataset tiếp:25 TT35 proposed included (còn blocker cây cha/
review/token), TT38 text đã có và9 hàng bảng sau khi chốt biểu diễn; TT51
chỉ3 supporting khi có dependency cụ thể. Chưa tự ghép các preview vào dataset.
