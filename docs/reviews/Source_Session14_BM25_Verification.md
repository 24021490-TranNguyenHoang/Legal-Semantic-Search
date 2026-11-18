# Phiên14 — BM25 experimental v6, build / comparison / portable handoff

Ngày thực thi 2026-11-18, snapshot **2025-01-01**. Origin=agent_review.
**BM25 v6 được build/chạy thật; experimental, release_eligible=false.** Chưa thay bản nhóm dùng hoặc ứng dụng Hùng. Nguồn/edition/applicability pending; scope proposal. Không accepted labels hoặc metrics v6 mới.

## Trạng thái và input đã ghim

HEAD đầu/cuối phiên `e9b98249a1297ccecc5e232b1444c577fb7a2bea`, nhánh feature/data-pipeline-huy; đầu phiên Git sạch. Đọc AGENTS/STATUS, handoff/contract/config BM25v5, báo cáo/handoff candidate phiên13, evaluation11, preview12 và review tích hợp Hùng18/11. Worktree Hùng giữ nguyên ở staging/hung-integration-review-001/integration, vẫn ghim v5. Không chọn latest, sửa seal, correction/extraction lại hoặc chuyển assessment/labels.

| Binding | Giá trị |
|---|---|
| Dataset input | staging/dataset-v6-gap-002 |
| Dataset version | vtls-subset-experimental.v6-candidate.1 |
| Manifest dataset SHA256 | 47b23b4f8742a308f32b4c1efd0d7749a81a8aae792459b95e7035490802bdfc |
| Dataset content SHA256 | 02440b59ca37c71e6e39683e8d741cfd4ccdfae50d8fb3b1aabc625d644b5cab |
| Consumer cấp gốc SHA256 | f42bcc914ee1b4b8bf9c313fccc38bff6511e9199ccab5676bf1901037fe3f5c |
| Dataset ZIP SHA256 | 8c9f3a50157bdf5ccc7e6df3dae8be0124ba8f7c469e436de410f6849e60b844 |
| Frozen query manifest | f8cc9257c410c8eb578d43a0bd1912e3aa5c572829be5e33d7ee0a2045e546f0 |
| Frozen v5 index manifest | 657ababc157e3e509c874628bd695b20220baeec514d3f201c2d53bcfc7138af |
| Frozen v5 batch manifest | baa811c55622580eb081b21e2df1868a3dba3d12f6f2a63acd532e6ca6b2fa09 |

Consumer root v6 validate toàn payload/graph/spans/proof/closure; base/consumer.py chỉ là dependency lịch sử của consumer v6, không dùng trực tiếp để giả đọc v6. Đúng139target=126chunk/9table-row/4whole-source;250supporting/1form/6encoder views. Chỉ139target vào engine; supporting/form/ancestors/views không thành document tìm kiếm.

## Adapter và algorithm

Thêm src/subset_bm25_v6.py và config/source_session14.v1.json, contract Source_Session14_BM25_Contract_v1.0.md. Adapter v1 dùng globals/binding cố định và hash-bound nên tách orchestration v2; không sửa v1 hoặc patch globals của v1 lúc chạy app. Tái dùng nguyên byte baseline/composition.create/tokenizer; tests so AST projection/mapping/query_set/search_loaded/read_loaded với v1. Index version **vtls-bm25s-subset.v2**, adapter subset-bm25-adapter.v2; projection/recipe vẫn subset-text-for-search.v1.

Giữ BM25S0.3.13/Lucene/k1=1.2/b=.75, numpy2.4.6/scipy1.17.1, lexical preprocessing/query/tie/filter toàn corpus của v5. Không thêm required-read vào text_for_search, đổi ranking, truncate hoặc tăng budget. Inventory index sort bằng relative POSIX string thay vì Path order phụ thuộc platform. Chưa chạy Linux BM25; đây không là bằng chứng Linux từ việc chuẩn hóa path.

Runtime build/search pins nằm trong runtime.json/index manifest; runtime sources và engine files được hash. Load kiểm nguồn/dataset/config/consumer/mapping; search chỉ đọc engine. Validate replay matrix trong RAM theo tolerancev1, không ghi lại index.

## Artifact chính và số liệu thực đo

| Artifact | Đường dẫn |
|---|---|
| Index chính / replay | staging/bm25-subset-v6-001 / bm25-subset-v6-002 |
| Index manifest SHA | 58c05ef0f6c2bb39d4a6af8d62d5520843c028e538a0b5d8abeb2ce5d3589c5f |
| Index content SHA | 81966166d529f590935a5a8d5f1377dbe292a7037b49357fb05614f33f8f2b32 |
| Batch50 Top10 | staging/bm25-subset-v6-batch-001 |
| Batch manifest SHA | 43cda4d3c35b416c56d8c7da1bdefbec2e2ab1a8910b04c574d54a75d649bef2 |
| Comparison + diagnostic139 | staging/bm25-v5-v6-comparison-001 |
| Replay/negative/portable report | staging/source-session14-validation-001/validation_report.json |
| ZIP | staging/vtls-bm25s-subset-v2-001.zip |
| ZIP SHA256 | 00e966c92a655f6405a64f4cb352eef89252508ecb75e1bd6bce6f66a63538cb |
| ZIP bytes | 26376034 |

Batch dùng đúng50query/30old+15new+5limit, nguyên thứ tự/ID/hash/câu chữ/top_k10; **500hits**, **118unique details**,0queryerror,0zerohit. Hit types: {'chunk.v1': 386, 'source-retrieval.v1': 39, 'table-retrieval.v1': 75}. Chỉ là số đo chạy, không đặt trước số hit. Query/ranking timesteps và load/hydration tách riêng; quá trình tuần tự có validation/các job khác cùng máy nên không coi là benchmark cold/warm hoặc SLA.

## So sánh retrieval v5–v6

Frozen v5 được kiểm inventory/binding, load bằng runtime v1 hash-bound (code repository trùng exact SHA của package v5), replay50query khớp **exact ID/type/rank/score**. Không dùng v6 runtime giả lập v5. V6 có thể đổi BM25 statistics/score do corpus thêm1document; không yêu cầu score hai corpus bằng nhau.

- Top1 thay đổi: **1/50**; danh sách Top10 thay đổi: **13/50**.
- Thêm đúng1ID A6K9b; không xóa target cũ hoặc coi các required-read mới là target.
- query_deltas.jsonl giữ Top1/Top10 trước–sau, vào/ra Top10, rank và score các ID chung. Ra Top10 khác với mất membership.
- Diagnostic toàn139 tách riêng diagnostic-all-documents.jsonl; không ghi đè frozen Top10.

| Query | Quan sát |
|---|---|
| dev-red_light-2 | A6K9b mới rank4; v5 chưa là document riêng. LeadKhoản9 đúng ô tô,7required-read nguyên bản, có context/proof. |
| dev-driving_age-2 | Rank15→15; payload/context/ID giữ nguyên. Closure2→16 tách riêng ranking, không tự cải thiện rank. |
| V3-D05 | Whole-source rank1; hàng V=60/35m rank2, không nhầm hàng60<V≤80/55m. Header/đơn vị/điều kiện và proof được giữ. |
| V3-D07 | Whole-source rank1; hai hàng60<V≤80/55m và80<V≤100/70m rank2/3. Mỗi hit hàng là một phần, không tự đủ câu trả lời so sánh. |

Đọc [báo cáo bốn query](../handoff/Source_Session14_Deep_Checks.md) để xem nguyên văn/lead/required-read và nguồn; deep_checks.json chứa full responses. Checker distance_evidence.v1 được tái dùng: xem distance80-81.evidence_check.json, phân biệt hai hàng riêng với hai hàng+whole-source giữ điều kiện bất lợi. Không thay completeness accepted hoặc applicability bằng kiểm kỹ thuật.

## Kiểm chứng thực thi

- Build chính, build replay, batch, ZIP và comparison đều native exit0; receipts/logs tại staging/source-session14-checks-001. Cấu hình và source bị ảnh hưởng được đọc thực tế, không dùng báo cáo cũ thay code.
- Suite final: **43tests,39pass/4skip**, exit0; tests-final.log/receipt. Bốn skip là opt-in actual baseline index3077 vì không đặt VTLS_BM25_MANIFEST; không tuyên bố đã chạy. Unit/synthetic fixtures được phân biệt actual v6 harness. Không cộng các lượt chạy lặp vào số test độc lập.
- Replay **143files** và manifest/hash, engine matrix đạt; signatures ID/type/rank/score/response của500hit giống byte giữa main/replay/portable. Timestamp/timing không thuộc signature. ZIP replay cùng SHA256.
- Full-read: **139target/250support/1form**, hash ce49564fc285bdc9dd4c98a418f647942a54bd5f672209dbc08cba5c3e060632; source mounts/cells/header/whole/views/closure được rootconsumer kiểm. Full-read portable khớp hash main.
- **16private mutations** bị từ chối, có reseal outerinventory: ID/type/source/recipe/tokens mapping, dataset/index/consumer/runtimehash, projection/query, thiếuengine/sourceasset/dependency, thiếucapability. Không sửa artifact thật hoặc nới validator.
- **9input probes** từ chối empty/whitespace/no tokens/topk/filter/unknown/supportingID/missingindex; OOV và nguồn hợp lệ không có target trảrỗng. Không fallback hoặc ngưỡngscore tùy ý.
- Portable: venv mới cài offline đúng3wheels, receipt wheelSHA/pipcommand/piplog; ZIP giải nén vào thư mục sạch trong validation/independent. Audit gate chặn repository/devvenv/cachegốc/network và childprocess; chỉ cho bundle/output/cleanvenv/stdlib/harness, thiết bịnull đúngos.devnull. **5CLI** (validate,batch search50,3readtypes) exit0 và full-read139/250/1; **4denial probes**,0unexpecteddenials/foreignmodules. Metadata subprocess tùy chọn bị chặn được ghi riêng. Đây là cùng máy Windows/CPython3.11.9; không gọi mô phỏngPOSIX làLinux.

## Lệnh chạy lại và bàn giao

[Quickstart](../handoff/Source_Session14_BM25_Quickstart.md) gồm install online/offline từZIP, validate/search/read/full-read/batch và build/replay. Chưa có URL chia sẻ. Chuyển đúngZIP+sidecar và requirements-bm25.txt; nếu offline chuyển thêm3wheel được ghi hash ở validation/offline_wheels.json, không chuyểnvenv hoặc history staging.

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_bm25_v6 build --config config/source_session14.v1.json --run-dir staging/bm25-subset-v6-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_bm25_v6 batch --index staging/bm25-subset-v6-NEW --output staging/bm25-subset-v6-batch-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_bm25_comparison --config config/source_session14.v1.json --index staging/bm25-subset-v6-NEW --batch staging/bm25-subset-v6-batch-NEW --output staging/bm25-v5-v6-comparison-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest -v tests.test_subset_bm25 tests.test_subset_bm25_v6 tests.test_bm25_baseline tests.test_composition_bm25
```

Chọn outputNEW chưa tồn tại. Lệnh harness đầy đủ trong quickstart/receipt; đừng sửa manifest hoặc chạy correction để khắc phục hash sai. Replay cần pinned inputs trong repo; runtime ZIP độc lập cần đúng Python/dependency.

## Bảo toàn và giới hạn

Preservation baseline8421file gồm raw/evidence/run cũ, v5/v6dataset, indexv5/query/qrels/evaluation/ZIP, và cả file đang sửa ở worktree Hùng. Pre-docs tất cả nguyên hash; cuối phiên chỉ STATUS được prepend giữ suffixbyte-exact. Receipt cuối preservation.final-002.json/git.final-002.json ghi HEAD/staged/diff/whitespace. Không stage/commit/push/merge.

Chưa kiểm BM25 trên máy/OS/Pythonminor khác; kiểm consumer Linux3.12.14 được người dùng cung cấp không mở rộng thành kiểm BM25Linux. Không lặp toàn bộ suite ingestion/source/parser, không chạy lại correction/OCR/render/encoder/Dense/Hybrid/reranker/embedding/UIAPI. Không tuning, query expansion, đổi score/tokenizer hoặc ứng dụng Hùng. 59accepted+2pending và diagnostic5query phiên11 giữ bindingv5; metricsv6/official50 vẫnnull. Không dùng sốtest hoặc hit để xác minh pháp lý/retrieval.

Bước tiếp chỉ là đề xuất: rà chênh lệch retrieval và lập protocol label/binding v6 trước đánh giá; quyết định chuyển ứng dụng là phiên riêng. Bản nhóm dùng hiện tại vẫnv5.
