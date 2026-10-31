# Phiên 6 — BM25 subset v5 và bàn giao portable

**BM25_BUILT_BATCH_READ_AND_PORTABLE_VERIFIED**, ngày **2026-10-31**.
Snapshot **2025-01-01**, experimental/release=false/corpus_version=null.
Đã build index, chạy query thật, read đầy đủ và kiểm ZIP giải nén; không chỉ thiết kế.
Source/edition/applicability vẫn pending, scope proposal, human events0.

## 1. Trạng thái và đầu vào

HEAD thực tế **441efbea1fbecc9a0d61e6c3962661862beb74ec**, branch
`feature/data-pipeline-huy`, Git đầu phiên sạch. Không dùng HEAD từ báo cáo cũ.
Đã đọc AGENTS, STATUS/ingestion, contract/reports/replay phiên5, dataset/consumer
thực tế, baseline/composition code/config/contracts, evaluation/query contract và
review Hùng. Không sửa/tích hợp nhánh Hùng hoặc lấy hai record prototype của nhánh đó.

Config mới `config/source_session6.v1.json` ghim input/hash và code baseline:

| Binding | Giá trị |
|---|---|
| Dataset gốc | staging/dataset-v5-subset-006 |
| Dataset version | vtls-subset-experimental.v5-candidate.1 |
| Dataset manifest SHA | 2a33d8fa503b54c574c453c33297c153074b2c3c08cdfb8a08b558d613e2d897 |
| Dataset content SHA | 708d3c40fbd6e5a384792b4a717f595aa5edb8023c32fb4efb6ef136a3aa2be4 |
| Consumer source SHA | c96add34342a48af9db1fc6d72da78d3904a50135d81570d8b80dc9ebb1ecd60 |
| ZIP dataset v5 input | vtls-subset-experimental-v5-candidate1-002.zip |
| ZIP dataset SHA | b1965b3df6373a068a328a8200a9a01d8345e16e73c79e675575a3b7c57fa822 |
| Queries | staging/composition-queries-001/manifest.json |
| Query manifest SHA | f8cc9257c410c8eb578d43a0bd1912e3aa5c572829be5e33d7ee0a2045e546f0 |

Đã chạy consumer validate trên candidate006 trước build:138target,238supporting,
XXVI, graph/spans/proof kỹ thuật đạt. Không tìm latest, không thay bằng v3/v4.
Mỗi build cũng validate lại input trước tạo output. Không cache vào candidate.

## 2. Artifact bàn giao cuối

| Thành phần | Giá trị |
|---|---|
| Index version / adapter | vtls-bm25s-subset.v1 / subset-bm25-adapter.v1 |
| Index chính / replay | staging/bm25-subset-v5-003 / bm25-subset-v5-004 |
| Index manifest SHA | 657ababc157e3e509c874628bd695b20220baeec514d3f201c2d53bcfc7138af |
| Index content SHA | 359b93ec8834f6388dc8bd129371ba8a7f8133ff0c9c25ccb56d0913f488d9f8 |
| Batch chính | staging/bm25-subset-v5-batch-002 |
| Core checkpoints | staging/source-session6-checks-002 |
| Final validation report | staging/source-session6-portable-003/validation_report.json |
| ZIP index + dataset + runtime + queries | staging/vtls-bm25s-subset-v1-002.zip |
| SHA sidecar | Cùng tên ZIP + .sha256 |
| ZIP size | **19.212.146 byte** |
| ZIP SHA | **ddf9e5c2f90439ea5b057792a609ea05e99e43e223bf64e327c2ff492023a759** |

ZIP index khác ZIP dataset đầu vào. Chưa có URL chia sẻ. Không đóng gói venv,
weights/cache hoặc staging history. Dataset bên trong index giữ byte-exact cả
manifest, consumer và assets; runtime không cần repository/staging upstream.
102file inventory +2manifest/sidecar;103payload/manifest so với replay giống byte,
ZIP replay giống SHA. Receipt/timing thật nằm ngoài index, không là ngày thu thập.

## 3. Membership và projection

| Đại lượng | Thực đo |
|---|---:|
| BM25 documents | **138**, một document/target |
| chunk.v1 / table-retrieval.v1 / source-retrieval.v1 | **125 / 9 / 4** |
| Source target counts SRC001/002/003/004/005/006/007 | **70 / 22 / 2 / 0 / 18 / 3 / 23** |
| Supporting units / form XXVI được giữ để read | **238 / 1**, không index độc lập |
| Encoder views trong whole records | **6**, không index độc lập |

Không nhận5NĐ168A16K2, TT35A28K2 hoặc vùng QCVN I.418/I.416 xung đột.7nguồn
inventory nhưng6nguồn có target/supporting; không gọi là index toàn bảy nguồn.

`subset-text-for-search.v1` lấy nguyên `record.text_for_search` theo từng type:
chunk dùng search input hiện có; table giữ header/row/đơn vị/điều kiện dẫn xuất;
whole dùng toàn search text gồm dependency đã biểu diễn, không lấy một view/snippet.
Nguyên văn, table derived text, context và spans không sửa. Không ghép thêm238
supporting vào corpus search, không join/dedup bằng title. Source_id lấy từ graph
node, citation từ proposal gắn unit; không giả định plan có source_id hoặc QCVN
node có field citation_path như DDD. ID/type/unit/source/payload/recipe/text/token
hashes đều có trong mapping/projection và được tái kiểm khi load.

Lexical token min–max: chunk30–227, table147–182, whole74–280. Đây khác encoder
token count; BM25 không chịu budget256. Whole TT38A11K2b giữ đầy đủ text/bảng/
conditions, không truncate, segment hoặc đổi target. Encoder views chỉ còn ở read.

## 4. Engine, interface và behavior

Tái dùng nguyên byte `composition_bm25.create`, `bm25_baseline.engine/rank/runtime`
và tokenizer lexical `vi-unicode-lexical.v1`. BM25S **0.3.13**, method/idf Lucene,
k1=1.2,b=.75,float32/int32,NumPy backend; NumPy2.4.6/SciPy1.17.1.
Không rank_bm25, PyVi/BPE/stopword/stem/boost/expansion/tuning.

Adapter mới `src/subset_bm25.py`: build/validate/search/read/batch/zip. Load kiểm
index inventory/status/config/code/runtime, exact dataset/consumer binding,
consumer full validation, search projection/mapping/vocab/CSC. Validate riêng
rebuild matrix trong RAM, tolerance1e-6/1e-7; search không build/rebuild/write.
Runtime giữ policy CPython cùng minor/Unicode/dependency/engine source của baseline;
patch khác ghi cảnh báo, không bỏ validator. Môi trường tạo/chạy đều có receipt.

Filters source_id/law_id/record_type exact AND, áp trước Top-k trên mọi positive
candidate do baseline rank trả, không chỉ lọc một Top-k đã cắt. Corpus statistics
vẫn toàn index. SRC004 hợp lệ nhưng rỗng. Top_k int>0; tie score giảm/record_id
Unicode tăng. BM25S Lucene contribution không âm, score>0 dùng cho lexical match,
không là ngưỡng tin cậy pháp lý; không pad. Empty/whitespace/punctuation query,
top_k/filter sai lỗi; OOV/no lexical match trả[]. Missing index không tự tạo và
không fallback corpus mẫu/dataset khác. Record ngoài membership bị từ chối.

Hit giữ ID/type/source/law/citation/rank/score/dataset/index version. Read trả
envelope index binding + **dataset_response nguyên trạng** cùng hash, không
formatter làm mất record/contexts/source_proofs/required_read/proposal/pending.
Dependency units/form không trở thành hit. API Python dùng load_index một lần,
search_loaded/read_loaded trên snapshot bất biến; không tạo service/UI ở phiên này.
Xem [contract](../design/Source_Session6_BM25_Contract_v1.0.md) và
[Quickstart tích hợp](../handoff/Source_Session6_BM25_Quickstart.md).

## 5. Batch thật và detail

Giữ nguyên bytes/ID/text/query manifest30old+15new+5limit từ composition đã seal.
Không chỉnh query sau xem ranking, không chạy lại/tuning dataset cũ để so chất lượng.

| Kết quả | Thực đo |
|---|---:|
| Queries / errors / zero-hit | **50 / 0 / 0** |
| Top10 hits thực | **500** |
| Hits chunk / table / whole | **387 / 75 / 38** |
| Unique detail records | **117** =104chunk+9table+4whole |
| Unique supporting units/forms đọc trong hit pool | **220 / 1** |
| Full-read độc lập toàn dataset | **138targets /238supporting /1form** |
| Qrels / query đủ nhãn accepted | **0 / 0** |
| Relevance metrics | **null / PENDING_LABELS** |

Raw_results/run/outcomes lưu từng query;117detail JSON có SHA và dataset_response
hash, required-unit list/record bindings được kiểm exact. Mọi hit duy nhất được
read; full-read còn kiểm21target không xuất hiện trong hit pool. Không chuyển
qrels v1/v3 hoặc accepted labels sang IDs NĐ168 mới. Pending annotations không là
nhãn agent accepted/human reviewed, reviewer/time/relevance vẫn null.

Ranking+response signature **b12ca36e51323902be169d811657de192ca548a3ac7c2bf2445e1aa69f5ccce5**
giống byte main/replay/portable. Full-read hash **c5fe430bddad6a05d05043a55f0f6ee73ad4fcf4ea0bfb8b1bc4617adb2bde71**
khớp consumer v5, không bị envelope/formatter thay nội dung.

Ví dụ thực: V3-L05 trời mưa rank1 là whole TT38A11K2b; read còn giữ điều kiện
đường khô, bảng3 và dependencies, không là câu trả lời tự động. V3-L03 hỏi kích
thước I.418 vẫn có lexical hits (QCVN4.2/4.1...), nhưng vùng thiết kế I.418 không
được admitted. FormXXVI chỉ là supporting cần read đúng target liên quan, không
phải form target có thể rank. Không suy no-gap từ500hit hoặc gap từ một ranking miss.
Quan sát theo membership: `source-session6-001/Coverage_Observations.md` (50query,
đa số pending review), ví dụ đầy đủ `Search_Read_Examples.md`, không là qrels.

Timing batch chính: load+hash/consumer validation+engine **15.443ms (~15,44s)**;
50query tuần tự, không warmup, first-query rồi cùng process warm. Preprocess/
score/filter/rank min0,245/median0,660/max2,904ms, sum36,715ms; detail hydration
min0,015/median62,351/max1.625,743ms, sum8.933,990ms, có dedupe117detail và ghi JSON.
Các số chỉ mô tả run này; không disk-cache-cold experiment, p95/SLA/benchmark máy
khác hoặc so chất lượng retrieval trên corpus khác. Load/validate không là ranking latency.

## 6. Kiểm chứng thực thi và portable

- Suite cuối: **46test chạy,42pass/4skip**,73,948s; log
  `source-session6-001/tests_final.log`.13test adapter có fixture SYNTHETIC/FIXTURE
  riêng: ties/filter trước Top-k, type/law/source, OOV/empty, input sai, NFC/dấu,
  readonly missing input, projection recipe và stdout UTF-8.4skip là optional
  actual-index tests của baseline cũ do không đặt VTLS_BM25_MANIFEST; không cộng
  skip thành pass. Index v5 thực có harness riêng dưới đây.
- **12private mutation bị từ chối**, kể cả outer inventory reseal: ID/type/source/
  recipe/token mapping, search text, dataset version/manifest SHA, consumer SHA,
  missing source asset, missing engine, query bytes. **9error probes**: empty,
  whitespace,punctuation,top_k0,filter source/type sai,support/unknown ID,missing index.
  Probes bổ sung OOV/SRC004 rỗng,NFC,type/source/law filters và read đủ3types đạt.
  Private copy là test artifact, không là index bàn giao.
- ZIP giải nén mới tại `source-session6-portable-003/independent/unpacked/bm25`,
  venv mới CPython3.11.9 Windows x64; pip **offline/no-cache** từ3wheel đã có,
  lưu wheel SHA. Distributions: bm25s/numpy/scipy đúng pins +pip24.0/setuptools65.5.0;
  không dùng ngầm dev venv/model/cache.
- Audit wrapper `-I -B`:5CLI (validate,batch,read một record mỗi type) exit0;
  batch chạy lại50query/read toàn117hit unique, full-read138/238/XXVI. Signature
  và full-read response hash giống main/replay.4repo/staging/dev-venv/HF-cache
  denial probes đúng, **0unexpected read denial/0foreign module**. Network và
  subprocess bị chặn; chỉ `os.devnull` chính xác được phép ngoài root,6lần NUL;
  6subprocess lấy metadata hệ thống bị chặn/fallback, log riêng. Không mở quyền
  workspace để né gate. Đây là Python audit, không VM/OS sandbox certification.
- Cùng máy/Windows, chưa kiểm OS/máy/Python patch khác. Không gọi đây là5cold
  process runs: wrapper dùng runpy cùng process; load/validate thực hiện từng CLI.

Receipt cuối: `source-session6-portable-003/validation_report.json`, `portable-command.json`,
pip/venv logs và `independent/runtime-output/audit_report.json`,5stdout/stderr,
batch/details/signatures/full-read. Core negatives/replay/matrix ở checks002.

Các lần phát triển được giữ nguyên:001/002index và batch001 trước fix stdout
Windows; checks001 dừng code-binding khi source CLI được sửa, không tuyên bố pass.
Đã tái hiện qua pipe lỗi charmap, sửa chỉ encoding tại main CLI; test UTF-8 mới
đạt, projection/mapping/matrix/ranking/response giữ nguyên (`cli_fix_projection_regression.json`).
Index003/004 và ZIP002 là bản cuối. Checks002 có5CLI exit0 nhưng gate fail do
NUL; sửa riêng harness cho null-device và chặn subprocess, **không sửa/reseal
index/ZIP**, resume sangportable003. Resume validate lại matrix/input và so ZIP
với từng byte index, không dùng báo cáo cũ thay kiểm index. Không lặp12mutation.

## 7. File thay đổi và preservation

| File mới | Lý do |
|---|---|
| config/source_session6.v1.json | Ghim dataset/ZIP/consumer/queries/code hashes |
| src/subset_bm25.py | Adapter/projection/mapping/filter/read/batch/ZIP tái dùng engine |
| tests/test_subset_bm25.py | Fixture riêng, input/filter/tie/Unicode/readonly |
| tests/check_subset_bm25_artifacts.py | Actual replay, private mutations, clean portable/checkpoint resume |
| docs/design/Source_Session6_BM25_Contract_v1.0.md | Contract index + search→read cho nhóm |
| docs/handoff/Source_Session6_BM25_Quickstart.md | Lấy ZIP/cài pins/validate/search/read/batch |
| docs/handoff/Source_Session6_Replay.md | Run ghim, lệnh tái tạo và audit/resume |
| docs/reviews/Source_Session6_BM25_Verification.md | Kết quả, bằng chứng, giới hạn thực tế |

STATUS/ingestion prepend hiện tại, giữ bytes lịch sử; không viết lại báo cáo cũ.
Baseline **26.132file** cũ đã so hash không đổi trước cập nhật docs. Final receipt
kiểm lại toàn baseline, cho phép đúng2doc prepend/suffix byte-exact; HEAD/staged/
diff--check ở `source-session6-001/final_preservation.json`. Raw/evidence/run cũ,
dataset3077/draft3082/v3/v4/v5,index/evaluation/query/qrels/ZIP lịch sử được giữ.
Không stage/commit/push/merge. Staging/venv/ZIP không đưa vào Git.

## 8. Tái chạy, giới hạn và bàn giao nhóm

[Replay guide](../handoff/Source_Session6_Replay.md) có đúng lệnh build003/004,
batch002, full checker và resume portable003. Thay output bằng tên mới chưa tồn
tại. Quickstart trong ZIP có cài dependency/validate/search/filter/read/batch/
full-read; repo không cần cho runtime. Chưa có URL chia sẻ; người nhận cần lấy
đúng ZIP/SHA, cài pins/wheel đúng nền tảng, validate trước dùng. Source build cần
input ghim trong config; thiếu input báo lỗi, không fallback.

Chưa có accepted v5 judgments nên metrics null; scope/provenance/edition và
applicability tiếp tục pending/proposed. Không xác minh pháp lý, đánh giá toàn
nguồn, Word layout hoặc thiết kế biển bằng kết quả index. Không xử lý A16/A28/
QCVN mới, mở membership, OCR, Dense/embedding/Qdrant/reranker, UI/API, merge Hùng
hoặc yêu cầu nhóm chuyển bản. Bước độc lập tiếp theo có thể là review nhãn v5
theo evaluation contract và tích hợp consumer có đủ capabilities khi được giao;
không dùng score/Top1 làm đáp án pháp lý hoặc so chất lượng với v1/v3.
