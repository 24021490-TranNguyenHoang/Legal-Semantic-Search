# Stage 6 — kiểm chứng chín Điều lá

Commit đầu lượt: `b72b9fdac78d549faaa02742321218877737a070`, Git sạch.
Đọc AGENTS, STATUS, DDD/source proof và contract Stage6 Điểm/coverage;
kiểm mã builder/tokenizer/validator thực tế. Không đổi dataset/index/query
evaluation đã bàn giao, không stage/commit/push.

## Đầu vào đã kiểm bằng manifest

Dataset được xác định từ `staging/bm25-baseline-v1-001/index_manifest.json`:
`dataset/dataset_manifest.json`, version `vtls-coverage-experimental.v1`.
Dataset input_binding trỏ coverage bằng SHA-256
`7853192d9be1fac05befe48bbe02d488e2afa8129631474830ca359e2c0d94af`, khớp
`staging/stage6-coverage-001/manifest.json`. Coverage khóa cây Stage4 bằng
SHA `ca30426fea4f39e797ffa0e922010cd507cf131b86df76c9174d2a0518e1c938`.
Không dùng report cũ thay validation: kiểm manifest/inventory/code/config,
upstream Stage4→3→2 và unit hashes trước khi tạo output.

Lấy đúng chín hàng unsupported_structure, đều article; không lấy 20 hàng
over_token_budget hoặc 13 blocked_source_or_context. Scope ở coverage là
unassessed; scope proposal mới hơn trong dataset được nối bằng unit/hash,
coverage/scope binding và lịch sử refinement. Không đánh giá scope mới.

## Kết quả thực tế

Run cuối: `staging/leaf-articles-preview-002/`.
Run `001` là lần đầu trước khi siết validator trạng thái/report; giữ nguyên,
không đề nghị replay nó bằng fingerprint CLI mới. Dùng `002` để rà/replay.

| law_id | Điều | Token gồm special | Unknown | Scope proposal hiện có | Kết quả |
|---|---:|---:|---:|---|---|
| 35/2024/QH15 | 1 | 31 | 0 | pending | preview |
| 35/2024/QH15 | 71 | 93 | 0 | excluded | preview |
| 36/2024/QH15 | 1 | 68 | 0 | pending | preview |
| 165/2024/NĐ-CP | 2 | 82 | 0 | excluded | preview |
| 165/2024/NĐ-CP | 3 | 72 | 0 | excluded | preview |
| 165/2024/NĐ-CP | 12 | 77 | 0 | excluded | preview |
| 165/2024/NĐ-CP | 49 | 139 | 0 | excluded | preview |
| 168/2024/NĐ-CP | 49 | 91 | 0 | excluded | preview |
| 168/2024/NĐ-CP | 55 | 77 | 0 | excluded | preview |

**9 preview, 0 blocked, 0 quarantine.** Mỗi Điều có một paragraph body,
một title; không có Khoản/Điểm con. Cả 18 field khớp paragraph DOCX thật
theo locator. Không phát hiện tag numPr/field/revision chưa giải mã trong
những paragraph này; inventory issue Stage3/4 không có ảnh hưởng trực tiếp
được builder xác định. Không tự khôi phục/chữa số hay bổ sung nội dung.

`articles_preview.md` và `inspection.jsonl` liệt kê đầy đủ law_id/unit_id,
citation, title, nguyên body (JSON giữ khoảng trắng/NBSP cuối), cha thật,
spans/offsets/hash, raw paragraph và scope cũ/mới. `dependency_checks.jsonl`
giữ cửa sổ nguồn/impact; `chunks.preview.jsonl` và `contexts.preview.jsonl`
giữ bằng chứng nguồn. `encoder_inputs.jsonl` giữ encoder_text, token IDs,
counts/unknown thực đo, không ước lượng bằng số từ.

Title chính Điều dùng làm heading context, không chép body vào context.
Những cụm từ vốn lặp tự nhiên giữa title và body vẫn giữ nguyên chữ luật.
Không thêm text Chương/Mục hoặc mở rộng dẫn chiếu Điều khác. `text_for_search`
theo công thức cũ; ID mới chỉ áp dụng cho Điều với policy mới, không đổi
ID/unit/content của các Khoản/Điểm cũ.

## Lệnh đã chạy và kết quả

Chạy từ root repository, CPython 3.11.9, môi trường `.venv-stage1` hiện có:

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.leaf_articles_preview build --coverage-manifest staging/stage6-coverage-001/manifest.json --dataset-manifest staging/bm25-baseline-v1-001/dataset/dataset_manifest.json --run-dir staging/leaf-articles-preview-002
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.leaf_articles_preview validate --manifest staging/leaf-articles-preview-002/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_leaf_articles tests.test_stage6_points.PointBuilderTests
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.retrieval_dataset validate --manifest staging/bm25-baseline-v1-001/dataset/dataset_manifest.json
git diff --check
```

- Build exit 0: 9 candidates/9 preview; roundtrip qua source_proof.
- Validate exit 0: replay tokenizer thật, mọi chunk/context/ID/hash/issues/
  inspection/report giống run đã seal; release_eligible=false.
- 22 tests đạt: 9 Điều lá và 13 Khoản/Điểm. Có trường hợp Điều có con,
  thiếu spans, thiếu cha, sai hash, parser issue, dấu hiệu Khoản bỏ sót,
  257 token giữ full quarantine, title vắng hợp lệ, content/identity ổn
  định và dispatcher legacy trả output bằng nhau. Fixture là synthetic.
  Lần đầu hai test mutation bị identity guard từ chối; đã sửa fixture
  tính lại unit/span IDs khi đổi nội dung, không nới guard để test pass.
- Dataset validator replay toàn bộ builder với token evidence đã đo:
  **3.077 chunk/5.371 context**, nội dung/ID/hash/spans giữ đúng artifact.
  46 deferred cũ vẫn 9 unsupported, 20 over-budget, 13 source/context,
  4 applicability evidence. Chín preview mới chưa nạp vào tập đó.
- Audit hash inventory index/dataset, hai bundle evaluation, bốn raw thật
  và ZIP bàn giao đạt; source builder/encoder/BM25/evaluation bằng byte HEAD.
  Query config CRLF khác Git blob LF đã có trước: so với SHA input query
  lưu trong batch evaluation cho kết quả **khớp byte**, không normalize
  hoặc sửa query. Evidence: `staging/leaf-articles-verification-001/preservation.json`.

Không chạy full suite không liên quan, inference/embedding/Dense/Hybrid,
Qdrant hoặc search; không sửa ứng dụng. Không kiểm máy/OS khác. Số test
không chứng minh relevance, hiệu lực hoặc xác minh corpus.

## Thay đổi và blocker còn lại

- `src/chunk_preview_articles.py`: handler hẹp cho Điều, dùng lại helper
  source/context-dependency/identity; legacy dispatch nguyên trạng.
- `src/leaf_articles_preview.py`: chọn đúng chín theo coverage đã binding,
  kiểm raw paragraph, build/validate và bảng dễ đọc; không framework mới.
- `tests/test_leaf_articles.py`: fixture tập trung cho phạm vi này.
- Contract Điều lá, báo cáo này, README và STATUS: policy, tương thích,
  cách replay và trạng thái ứng viên phiên bản dữ liệu tiếp theo.

Không còn blocker chunking quan sát được trong chín Điều. Nguồn DOCX legacy,
extraction/cây và applicability vẫn pending; chưa reviewer quyết định scope.
Bảy proposal excluded không tự được đổi thành included vì chunk chạy được;
hai pending không bị loại theo mặc định. Muốn đưa vào dataset sau cần chốt
phạm vi/version mới riêng; chưa thay dữ liệu phục vụ công việc mô hình và
evaluation hiện tại. Dẫn chiếu ngoài cây cha chưa được ghép, chưa xác minh
toàn văn hoặc pháp lý từ chín paragraph.

Để chạy lại, dùng lệnh build trên với run-dir mới, rồi validate manifest
run đó. Giữ hai input bundle và tokenizer assets; preview này không tự đóng
gói toàn lịch sử staging. Source proof paths tính từ `inputs/` của coverage
manifest được tham chiếu. Mở `articles_preview.md` trước, dùng JSONL khi
cần kiểm slice/ID/hash chính xác.
