# Review hung-feature — 29/10/2026

**Đề nghị chưa tích hợp.** Có UI/API và các thành phần tìm kiếm ở mức prototype,
nhưng hiện chưa chứng minh được luồng bốn mode xuyên suốt, nhất quán nguồn/index.
Các lỗi dưới đây đã được phân biệt với giới hạn môi trường và phần khung từ base.
Đây là báo cáo agent_review, không phải sự kiện review/approval trên GitHub.

## 1. Phạm vi và binding

| Thông tin | Giá trị / bằng chứng |
|---|---|
| Worktree chính đầu phiên | `feature/data-pipeline-huy`, sạch |
| HEAD chính | `c759aa496cb560a984b76a599305d863d9c117d8` |
| Remote đã fetch | `origin`, `https://github.com/24021490-TranNguyenHoang/Legal-Semantic-Search.git` |
| Head review | **`90c37df63276779542f5a5c0c73761c76046a144`** |
| Base review | **`cf9c5ad85ea6a0ff80ad8a2170d9875c658e72d1`**, `origin/main` |
| Merge-base | Bằng base SHA ở trên; cũng là parent trực tiếp của head |
| Phạm vi diff | **1 commit / 16 file / +926 −30 dòng** |
| Worktree detached | `staging/hung-feature-review-001/worktree/` |
| GitHub PR / issues | GET API thành công: không có PR tương ứng, issues state=all trả mảng rỗng |

Base được chọn theo default_branch=main từ GitHub API và lịch sử Git, **không lấy
nhánh Huy làm base**. Không có PR để xác nhận thêm ý định base của tác giả. SHA
được ghim sau fetch, không dùng ref di động để chạy thử. Commit mang thông điệp
“Hoàn thiện hệ thống Ingestion, Search Strategies, Streamlit UI và Evaluation
Benchmark”. Đã đọc toàn diff và code liên quan, không chỉ README.

Đã đọc AGENTS/README/STATUS hiện hành, BRD §2.2/§4/§6, SRS search/result/corpus/
API/operational requirements, DDD và các contract BM25/composition/evaluation có
liên quan. Nhánh Hùng xuất phát từ skeleton cũ, **không mang các tài liệu/pipeline
mới của nhánh dữ liệu**. Đây là khác biệt tích hợp cần xử lý; không quy lỗi Hùng
đã xóa các phần vốn chưa có trong base của nhánh.

BRD ghi Hùng phụ trách môi trường, tích hợp ứng dụng, trải nghiệm tìm kiếm và đo
vận hành phối hợp Long; AC-01 do Hùng, AC-06 Long/Hùng. Không tìm được issue hoặc
tài liệu phân công chi tiết hơn trong repo để tự suy thêm acceptance criteria.

Receipts: `review_binding.json`, `repository-network.json`, `pulls-network.json`,
`issues-network.json`, `hung.diff`, `changed_files.txt` trong run review.

## 2. Findings ưu tiên

Mọi vị trí dưới đây là code **head90c37df**, trong worktree review. F01–F12 là
hành vi từ code mới của nhánh; các placeholder kế thừa được tách ở mục3.
Tên probe tham chiếu `logic_probes.json` hoặc `ui_probes.json`; fixture luôn được
đánh dấu FIXTURE và không được nhập vào dữ liệu pháp luật.

### F01 — P1: thiếu corpus bị thay bằng dữ liệu mẫu mà không báo lỗi

Vị trí: `src/search/bm25.py:19–26`.
Repro: `BM25Searcher('MISSING-corpus.json').search('phương tiện')`, probe
`bm25_missing_corpus`. File không tồn tại nhưng engine vẫn trả hai điều mẫu chứa
`...`; không có trạng thái not-ready hoặc nhãn fixture. Sai cwd cũng có thể đi vào
nhánh này vì path tương đối. Người nhận không biết đang tra dữ liệu giả thay vì
corpus đã cấu hình. Cần fail rõ khi thiếu input; mẫu chỉ được bật riêng và có nhãn.

### F02 — P1: ingest và search dùng hai collection khác nhau

Vị trí: `run_ingest.py:54`, `src/database/qdrant_client.py:15`, `:26–31`;
`src/ingestion/embedder.py:43` là đường nạp khác dùng manager.
Script README quảng bá `run_ingest.py` nạp vào **legal_documents**, trong khi
DenseSearcher dùng manager mặc định **vietnamese_laws**. Probe
`ingest_search_collection_mismatch_and_write_on_read_init` kiểm literal ingestion
và constructor manager bằng spy: khi chưa có collection, **khởi tạo đường đọc
lại tạo collection rỗng** vietnamese_laws. Không chạy ingest/upsert thật.
Hậu quả: nạp xong vẫn tìm nhầm index hoặc tưởng không có kết quả. Cần một binding
cấu hình dùng chung và khởi tạo search chỉ đọc/kiểm readiness, không tự tạo index.

### F03 — P1: Hybrid gộp các căn cứ khác nhau chỉ bằng tiêu đề Điều

Vị trí: `src/search/hybrid.py:27–40`.
Probe `hybrid_same_title_collision`: hai record FIXTURE-A/FIXTURE-B có chunk_id
khác, cùng article_title; output chỉ còn FIXTURE-A, điểm của B được cộng sang A.
Tiêu đề như “Điều 1. Phạm vi điều chỉnh” có thể lặp giữa văn bản. Đây là lỗi mất
record/sai liên kết điểm–nguồn, không cần qrels để xác nhận. Cần join/dedup bằng
ID ổn định trong cùng phiên bản corpus, không theo title.

### F04 — P1: bộ lọc văn bản không được áp lên nhánh Sparse

Vị trí: `src/search/hybrid.py:18–22`, `src/frontend/app.py:146–149`.
Probe `hybrid_filter_leak`: filter FIXTURE-A nhưng Sparse trả FIXTURE-B và B vẫn
được xếp đầu. UI ở BM25 mode cũng không chuyển document_filter cho engine.
Hậu quả: kết quả khác văn bản người dùng đã chọn. Cần áp cùng filter trên các
engine; nếu một mode chưa hỗ trợ thì từ chối/ẩn lựa chọn rõ ràng.

### F05 — P1: Hybrid + Reranker chưa có reranker như công bố

Vị trí: `src/search/reranker.py:3–6`, `:15–21`; UI `app.py:92–96`.
Probe `reranker_is_query_independent_score_scaling`: đổi query không đổi output;
code chỉ sort theo score cũ, nhân **1.15** và sửa dict đầu vào. Không nạp/gọi
Cross-Encoder. Không thể dùng mode này để tuyên bố đã so sánh bốn cấu hình hoặc
độ chính xác cao nhất như sidebar/README. Cần tích hợp component thật do phụ trách
mô hình cung cấp, hoặc công bố unavailable; không dùng hệ số điểm như rerank.

### F06 — P1: query rỗng/OOV vẫn được trả các điều luật

Vị trí: `src/search/bm25.py:28–39`; UI `app.py:134`, `:157–167`.
Các probe `bm25_empty`, `bm25_whitespace`, `bm25_oov` trên **corpus thật của nhánh**
đều trả hai record score0. AppTest cho OOV và whitespace vẫn dựng thẻ nguồn và câu
“Dựa trên các quy định pháp luật hiện hành…”. Cần kiểm input trước search, và xác
định tập lexical candidates rỗng đúng semantics của engine. **Không mặc định cứ
bỏ mọi score<=0**: rank_bm25 Okapi trên corpus hai record này có score âm ngay với
query có từ khớp; threshold phải phù hợp thuật toán, không là ngưỡng tin cậy pháp lý.

### F07 — P1: BM25 UI bị chặn bởi Dense; lỗi search làm hỏng lượt UI

Vị trí: `src/frontend/app.py:26–39`, `:143–152`; API `src/api/main.py:21`.
UI khởi tạo Dense, BM25, Hybrid (tạo thêm Dense) trước khi dựng bộ chọn mode.
Probe `bm25_cannot_be_selected_when_dense_init_fails` có exception ngay trước UI;
`ui_service_exception` có uncaught ConnectionError khi backend search lỗi. Đây là
kiểm tra lỗi có kiểm soát, không phải model/search thật. Import API thật trong môi
trường đã có dependencies cũng dừng vì thiếu model trong cache offline.
Cần phân biệt readiness của mode và lỗi có thể hiển thị/thử lại; không để lỗi
component làm mất toàn bộ UI hoặc âm thầm chuyển chiến lược.

### F08 — P1: dữ liệu trả lời chưa bind nguồn/version, metadata bị mất

Vị trí: `data/processed/chunks.json:1–12`, `src/search/dense.py:32–39`,
`src/frontend/app.py:50`, `:164–167`.
BM25 đọc hai bản ghi tự kèm, không chunk_id, URL nguồn, snapshot hoặc version.
Đối chiếu **chính cleaned files của nhánh**, script ingest sẽ tách7Điều nhưng
JSON chỉ chứa2Điều; hai text tương ứng cũng không khớp nguyên văn cleaned input
(`data_binding_audit.json`). Không dùng phép so này thay xác minh pháp lý.
Probe `dense_formatter_drops_source_and_context` đưa payload FIXTURE có URL,
context, citation, applicability pending và required_dependencies; formatter bỏ
hết các field đó. UI chỉ có title/text/score, lại nói “hiện hành”, không công bố
snapshot2025-01-01/pending. Cần giữ metadata nguồn và trạng thái thật, đồng thời
chốt dataset/index binding trước tích hợp; không trỏ đại sang artifact khác để demo.

### F09 — P1: API chấp nhận input sai và bỏ qua mode mà vẫn trả success

Vị trí: `src/api/main.py:24–27`, `:35–43`.
TestClient với **FakeDense boundary** tái hiện: query rỗng/space/1001ký tự,
top_k=-1/1000/true/3.0 đều được nhận; mode không hợp lệ hoặc mode=bm25 bị bỏ qua
và vẫn gọi Dense. as_of_date không hỗ trợ cũng bị bỏ qua; không trim/NFC.
Null/missing query có422, cần giữ hành vi tốt này. Đây là đối chiếu contract
SRS FR-SEARCH-01/02 và API§7, không tuyên bố có retrieval thật ở test này.
Cần request validation chặt, từ chối extra fields và dispatch mode minh bạch.

### F10 — P2: lỗi Sparse bị che và Hybrid âm thầm thành Dense

Vị trí: `src/search/hybrid.py:7–10`, `:48`.
Probe `hybrid_silent_fallback`: BM25 init báo input lỗi nhưng Hybrid vẫn trả
Dense-only, không báo thay mode. Kết quả/latency sau đó bị gắn nhãn Hybrid dù
pipeline khác. Cần báo mode unavailable hoặc trạng thái degraded công bố rõ,
theo contract; không dùng kết quả fallback cho benchmark Hybrid.

### F11 — P2: trạng thái dịch vụ/lỗi chưa đủ để vận hành

Vị trí: `src/api/main.py:30–45`.
`api_service_error` nhận500 và nguyên văn exception (fixture có internal path),
không503/mã lỗi/request_id; `/` vẫn200. `/api/v1/health`, `/api/v1/ready`, `/api/v1/corpus`
đều404 trong TestClient; UI cũng không có xử lý lỗi có kiểm soát như F07.
Cần readiness/version metadata và mã lỗi phù hợp; không trả chi tiết backend
trực tiếp. Các router rỗng từ base không phải bị Hùng xóa, nhưng API mới chưa
hoàn thành các hành vi vận hành trong SRS.

### F12 — P2: evaluation so title nên có thể tính hit sai văn bản

Vị trí: `evaluate.py:7–16`, `:19–33`, `:44–48`.
Probe metric helper với kết quả FIXTURE sai document_id nhưng trùng title vẫn
cho MRR=1 và Recall=1. Đây là **fixture kiểm logic**, không metrics corpus thật.
Script chỉ có2query/1title-positive mỗi query, không IDs/qrels/annotations/
intent groups/split/version, không mode rerank; chỉ mean latency, không raw
per-query/p50/p95/cold-warm. Cần phối hợp Long dùng contract evaluation và query/
qrels thật, tách đề xuất nhãn khỏi accepted. Chưa chạy script đầy đủ hoặc báo
metrics chất lượng bằng hai query này.

## 3. Phân công và mức hoàn thành

| Nhiệm vụ / căn cứ | Kết luận | Bằng chứng và phần thiếu |
|---|---|---|
| Môi trường chạy, tái tạo — BRD2.2, AC07 | **Thiếu** | requirements/Docker/compose rỗng; README mới là báo cáo, không có quy trình setup/start thực tế |
| UI nhập query/chọn mode/history/thẻ text — AC01 | **Hoàn thành một phần thành phần UI** | AppTest thao tác được; BM25 real với Dense bootstrap stub, chưa tự khởi động tự nhiên |
| API tìm kiếm — SRS§7 | **Thiếu** | Dense-only, validation/mode/version/readiness/lỗi chưa đúng; TestClient boundary đã kiểm |
| Bốn pipeline hoạt động xuyên suốt — BR06/AC04 | **Chưa kiểm chứng đầy đủ; reranker thiếu** | Dense/Hybrid thật bị chặn model/service; fusion bugs kiểm bằng fixture; reranker chỉ nhân điểm |
| Nội dung/nguồn/citation/snapshot — BR03–05 | **Thiếu** | JSON2record không binding, thiếu nguồn, UI thiếu context/proof/status và nói hiện hành |
| Trạng thái rỗng/không sẵn sàng/lỗi — BR11 | **Thiếu** | Nil message có thể hiển thị khi boundary trả[]; BM25 OOV không rỗng, lỗi service uncaught |
| Đo vận hành phối hợp Long — AC06 | **Thiếu** | Có time.time/latency caption; chưa benchmark tái tạo có điều kiện/percentile và raw run |
| Gán nhãn/metrics/evaluation bàn giao Long — BR07/AC05 | **Thiếu / chưa nghiệm thu** | Hai query title-only không thay query set/qrels có binding hiện có; không có accepted labels được kiểm |
| Test/CI triển khai mới | **Thiếu** | unittest discover thực thi0test; không thêm regression tests cho16file thay đổi |

**Attribution baseline:** `requirements.txt`, `Dockerfile`, `docker-compose.yml`,
hai test file và hai API router đều **0byte ở cả base và head**, không bị Hùng làm
rỗng. Đây là thiếu sót bàn giao vẫn cần khắc phục, không phải regression xóa file.
Ngược lại các engine/UI/API/evaluation mới, dữ liệu mẫu và hành vi F01–F12 nằm
trong commit head. Các thiết kế experimental mới ở nhánh dữ liệu không được coi
là đã nằm trong base Hùng hoặc đã được tích hợp chỉ vì README nhắc “blueprint”.

## 4. Dataset/index thật sự được dùng và capability

| Đường chạy | Input/binding thực tế |
|---|---|
| BM25 | `data/processed/chunks.json`,2record; SHA256 **9c6fc60e4ea1768e1a0f3c03231ba708d1ce3d08d25596dcda525ced28a4257c**; rank_bm250.2.2 trong venv kiểm (nhánh không pin), lower().split(), index trong RAM |
| Dense/API | SentenceTransformer `all-MiniLM-L6-v2`, không pin revision; Qdrant localhost:6333/vietnamese_laws,384chiều; **chưa xác định nội dung/version DB thật** vì service không chạy |
| run_ingest | cleaned TXT riêng/wholeArticle;legal_documents,384chiều; numeric IDs; ghi chunks.json sau upsert; **không chạy** vì ghi dữ liệu/embedding |
| embedder module | Parser/chunker article riêng, manager vietnamese_laws; đường nạp khác, không thống nhất với run_ingest |
| UI | Gọi Python searchers trực tiếp; không đi qua API; chỉ hỗ trợ dictionary article_title/chunk_text/document_id/score theo code hiện có |

Không có dataset/index version/manifest binding trong nhánh này, không được tự
gán nhãn vtls-coverage-experimental.v1 hoặc vtls-bm25s-lucene.v1 cho BM25 của Hùng.
Thông tin đối chiếu chỉ đọc từ manifest hiện có:

- v1: **3077** document, `vtls-coverage-experimental.v1` /
  `vtls-bm25s-lucene.v1`; index manifest SHA47df11b0… Không được app nhánh đọc.
- composition: **3115** record =3106chunk+9table-row,
  `vtls-coverage-experimental.v3-draft.1` / `vtls-bm25s-composition.v1`;
  manifest6d285b85… Không được app đọc, không build lại.
- candidate v4 vẫn là draft riêng; subset **138 phiên4 chỉ là packaging plan**,
  không dataset/index để trỏ ứng dụng. Không dùng nó làm input demo.

Nhánh cam kết article-level prototype, **không cam kết table-owner/form/whole-source**.
Vì vậy không gán “thiếu hỗ trợ form/table” thành bug của cam kết đó. Yêu cầu tích
hợp bản sau phải bổ sung rõ capability/version/resolver: chunk.v1 có context/source
spans, table-retrieval có cells/conditions, whole-source có đủ views/nội dung,
form có layout-only supporting, và required-read trả đủ dependency. Không cast
các type này thành chunk_text hoặc bỏ dependency cho UI hiển thị được.

Với các record article hiện có, AppTest xác nhận text trên thẻ đúng JSON nhánh,
**không chứng minh đúng bản nguồn pháp luật**. Required-read/URL/version không
có đường hiển thị; các field bổ sung còn bị Dense formatter loại như F08.

## 5. Thực thi, môi trường và các bước bị chặn

Môi trường thử: cùng Windows hiện tại, CPython3.11.9; venv riêng
`staging/hung-feature-review-001/venv/`. Không sửa implementation/worktree data.

| Kiểm tra | Kết quả |
|---|---|
| Tạo venv; pip install -r requirements.txt của nhánh | Exit0 nhưng file rỗng, không có dependency ứng dụng |
| pip check môi trường sạch | Exit0, không chứng minh API/UI cài đủ |
| unittest discover -s tests -v của nhánh | **0test**; không gọi đây là suite pass |
| Import API trong môi trường sạch | ModuleNotFoundError fastapi |
| Lệnh Streamlit trong môi trường sạch | No module named streamlit |
| Import API bằng môi trường đã có thư viện, offline | Model không có cache; OSError từ HuggingFace trước khởi động; không tải weights |
| GET Qdrant healthz/collections thật, ngoài hạn chế socket sandbox | Cả hai WinError10061 connection refused; **không tạo collection** |
| Venv augmented chỉ phục vụ probe | Cài5dependency khai báo ở review-only-requirements.txt + transitive; pip check đạt, lưu freeze. Không coi đây là requirements đã được nhánh cung cấp |
| Logic probes | **27case**: BM25 real; Hybrid/Dense/API boundaries bằng fixture/spies được ghi rõ; không inference hoặc ghi DB |
| UI AppTest | **7case** headless: text cards BM25 real, whitespace/OOV, empty response boundary, lỗi init/service; không phải browser/live bốn-mode demo |
| Full Dense/Hybrid/Rerank demo | **Chưa chạy**: thiếu model/cache và service/index thật; reranker code còn stub |
| Browser Chrome/Edge, OS/máy khác | **Chưa kiểm**; AppTest không thay kiểm trình duyệt |
| Diff check commit base→head | Exit2: trailing whitespace trong diff, log giữ nguyên; không sửa implementation |

Không chạy benchmark trong phiên review; không có cold/warm sample/p50/p95 hay
kết luận chất lượng retrieval. Hai giá trị1.0 trong probe F12 chỉ là minh chứng
lỗi matching của metric helper trên fixture, không kết quả đánh giá thật.

## 6. Chạy lại kiểm chứng

Từ root repository, sau khi giữ nguyên worktree pinned và venv review:

```powershell
.\staging\hung-feature-review-001\venv\Scripts\python.exe -X utf8 -B staging/hung-feature-review-001/probe_logic.py
.\staging\hung-feature-review-001\venv\Scripts\python.exe -X utf8 -B staging/hung-feature-review-001/probe_ui.py
git -C staging/hung-feature-review-001/worktree status --short
git diff --check cf9c5ad85ea6a0ff80ad8a2170d9875c658e72d1 90c37df63276779542f5a5c0c73761c76046a144
```

Probes đặt cwd và import source từ worktree ghim, có kiểm module_paths; không
fallback module của nhánh Huy. Model được stub có nhãn, network/service writes
bị guard chặn; chỉ cho socketpair nội bộ cần cho TestClient/AppTest. Lần harness
đầu chặn cả socketpair gây lỗi kiểm thử; đã sửa **harness ngoài implementation**
và chạy lại, không tính lần lỗi đó thành lỗi ứng dụng. Cài dependency nhẹ dùng:

```powershell
.\staging\hung-feature-review-001\venv\Scripts\python.exe -m pip install -r staging/hung-feature-review-001/review-only-requirements.txt
.\staging\hung-feature-review-001\venv\Scripts\python.exe -m pip check
```

Receipts, freeze, inputs, module paths, stdout/stderr và source/index metadata ở
run review. Không đưa venv/worktree/cache hoặc staging artifacts vào commit.

## 7. Sửa tối thiểu trước tích hợp

1. Hoàn thiện requirements/start guide/test smoke thật; chốt cấu hình source/index/
   collection dùng chung, tách hoàn toàn lệnh build/upsert khỏi đường đọc.
2. Bỏ fallback dữ liệu mẫu ngầm; xử lý input/OOV/not-ready/lỗi rõ. Không để một
   component lỗi làm đổi mode hoặc khiến BM25 không mở được UI.
3. Sửa Hybrid join bằng ID và cùng filter; thống nhất engine/model/RRF/reranker
   với phụ trách mô hình, không giữ hệ số1.15 dưới nhãn Cross-Encoder.
4. Thống nhất API validation/dispatch/metadata/error contract; giữ nguyên văn,
   source/citation/context/pending/snapshot thay lời khẳng định “hiện hành”.
5. Phối hợp Long: qrels/record IDs/binding thật, bỏ title-only ground truth,
   log timings có điều kiện; không dùng evaluate.py này thay bộ evaluation đã bàn giao.
6. Sau các sửa trên mới chọn **một phiên bản dataset experimental có thật** cho
   đợt tích hợp riêng; khai báo capability và trả đủ required-read. Không tự lấy
   toàn v4 hoặc subset138 chưa đóng gói. Thêm regression tests cho các lỗi đã tái hiện.

Không sửa code để làm demo pass, không đổi corpus/index/query set, không chạy
ingestion/embedding, không merge/pull/reset/stash/checkout worktree chính, không
stage/commit/push hoặc đăng comment GitHub. Báo cáo mới là thay đổi tài liệu duy
nhất ngoài run staging; HEAD/branch/worktree chính và source worktree review được
kiểm preservation trong receipt cuối.
