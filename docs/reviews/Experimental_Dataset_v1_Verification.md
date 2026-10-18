# Đóng gói dataset thử nghiệm v1

Snapshot tham chiếu dự kiến **2025-01-01**. Dataset còn pending nguồn,
technical review và applicability; chưa bảo đảm mọi nội dung áp dụng tại
snapshot. Không có quyết định reviewer, corpus verified/frozen, embedding
hoặc index mới.

Đầu vào thật `staging/stage5-pilot-refinement-001/manifest.json` và snapshots
upstream trong run đó. Đã đọc AGENTS, DDD §11–13, contract assessment,
chunk/context, scope survey/refinement và code đang mở. Git trước sửa sạch;
baseline đã lưu trạng thái, diff và hashes 10.708 file artifact, 120 file
source/test/config/schema/tài liệu trước khi sửa.

Contract: [Experimental_Dataset_v1_Contract.md](../design/data_model_v1/Experimental_Dataset_v1_Contract.md).
CLI: `src.experimental_dataset`; config `config/experimental_dataset.v1.json`.

## Quy tắc thực hiện

Không ép kết quả bằng 95 trong báo cáo trước. Tính lại từ 107 candidate,
đối chiếu scope/context proposals và builder replay với nguồn/spans/issues
thật. Chỉ chọn included, preview_available, field context phù hợp và không
có dependency issue chặn. Unknown không bị loại mặc định. Giữ scope pending
và quá budget trong deferred, không segment/truncate hoặc sửa proposal.

Thêm kiểm tra evidence hiệu lực **riêng unit/dependency được dùng**; ngày
chung của văn bản không được gán active. Date rule priority cao nhất phải
gắn đúng finding/capture/quote/page/hash; cùng priority mâu thuẫn cần xem
thêm. Khoảng ngày là [from,to), `effective_to` exclusive theo assessment
v1.1. Chưa kết luận có thể giữ trong dataset với applicability pending.

Một căn cứ âm đã có cần giữ ngoài tập theo snapshot: Luật 36 Điều 10
khoản 3. Finding cũ ở PDF Công báo phần tiếp, trang PDF 58 (từ 1), ghi:

> 2. Khoản 3 Điều 10 của Luật này có hiệu lực thi hành từ ngày 01 tháng 01 năm 2026.

Quote từ evidence đã capture; normalized page text có offsets [537,619).
URL `https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/9/36-2024-qh15_tiep.pdf`;
accessed_at lịch sử capture `2026-10-16T14:33:01.270301Z`, không phải ngày
hiệu lực hoặc thời điểm tải DOCX legacy. Không mở web/tải bản mới trong lượt
này vì quote/capture cần thiết đã có. Finding/rule/review vẫn pending; kết
quả lựa chọn bộ thử nghiệm không ghi thành assessment reviewer hoặc ngày
hiệu lực trên chunk. Scope của đơn vị cũng không bị đổi thành excluded.

## Dataset thực tế đã tạo

Run `staging/experimental-dataset-v1-001/`, version
`vtls-pilot-experimental.v1`. Số liệu tính từ artifact thật:

| Chỉ tiêu | Kết quả |
|---|---:|
| Candidate đầu vào | 107 |
| Target / chunk | **94 / 94** |
| Context rows | **164** |
| Context units / field dùng chung khác nhau | 33 / 35 |
| Target Khoản / Điểm | 30 / 64 |
| Luật 36 / NĐ168 / Luật 35 | 70 / 22 / 2 |
| Candidate deferred, không mất/nhân đôi target | 13 |
| Token encoder gồm special: min / max / tổng | 38 / 239 / 8.764 |
| Target có unknown / tổng unknown | 1 / 1 |
| Metadata gap rows, source/technical/applicability | 774, mỗi chiều 258 |
| Nguồn/technical review/applicability còn pending | Toàn bộ 94 target |
| Human reviewer event / release eligible | 0 / false |

**Vì sao khác 95:** sau khi chỉ xét scope/chunk/context có 95 candidate phù
hợp kỹ thuật; Điều 10 khoản 3 Luật 36 bị giữ ngoài tập theo căn cứ ngoại lệ
trên nên còn 94. Điều này không xác nhận 94 đơn vị còn lại đều có hiệu lực
tại snapshot. Không trộn mapping/ID PDF Điều 22 mới vào cây DOCX pilot.

Phân hoạch deferred không giao nhau: 10 scope pending; 2 included quá
budget (NĐ168 Điều 6 khoản 2 điểm đ: 294 token; Điều 8 khoản 2 điểm b:
270); 1 included có preview nhưng ngoài snapshot theo evidence (L36 A10K3).
Thống kê theo **từng lý do** có giao nhau: scope pending 10, quá budget 3,
context cần xem thêm 1, ngoài snapshot 1. NĐ168 A47K5a nằm trong nhóm
pending, đồng thời 291 token và field context cần xem thêm; không phải
candidate deferred mới ở mỗi lý do.

Metadata gaps đếm theo target–dependency–field–chiều, gồm 94 target fields
và 164 context dependencies, không phải 774 vấn đề pháp lý độc lập. Context
chia sẻ vẫn có trách nhiệm đối chiếu cho từng target. Cây full ba văn bản
trong support phục vụ ranh giới builder, không mở rộng target ngoài 94.

## Bằng chứng kiểm tra đã chạy

Validator input refinement: **exit 0**, 242,496 giây. Chạy trên artifact thật,
bao gồm upstream scope/coverage/builder/tokenizer; không coi báo cáo cũ là
kết quả. Log `staging/experimental-dataset-v1-verification-001/input_validate.log`
và result JSON lưu command, exit code và thời gian đo thực tế.

Build chính thức: **exit 0**, 207,048 giây; validator độc lập: **exit 0**,
1,123 giây. Cả hai kiểm lại source/trace/evidence/IDs/context/selection và
thống kê thật. Thiếu input: exit 1 rõ ràng, không tạo output.

Full suite **232/232 test đạt, không skip**, exit 0; test runner 103,010
giây, gồm 25 test mới (22 fixture synthetic và 3 integration dataset thật)
cùng 207 test hồi quy. Đã bật tám VTLS_* manifest bindings. Log
`regression.log` và `regression_result.json` giữ kết quả thực tế.
Tests bao gồm lệch unit/history/hash, thiếu span/cha, locator trace sai,
source/capture/quote hash sai, context order/FK và field không phù hợp,
count token không khớp IDs, candidate deferred không lọt vào selected,
ngày kết thúc exclusive, date-rule conflict, metadata corpus/reviewer giả,
CSV/MD/counts, giữ unknown và bản copy portable.
Trong phát triển đã dừng preflight
trước khi tạo output để chốt quy ước ngày exclusive và thứ tự inventory
POSIX ổn định giữa Windows/Linux; không xóa/ghi đè bundle đã tạo.

Bản copy thật `staging/experimental-dataset-v1-transfer-001/` được validate
trong process `-I -S -B`, chỉ thêm runtime trong bundle vào sys.path, tắt
site-packages/PYTHONPATH và chạy từ thư mục đã chuyển: **exit 0**. Toàn bộ
62 file còn nguyên byte sau kiểm. Lần ghi log tiếp theo thêm `-X utf8` để
stdout chuyển hướng không phụ thuộc code page Windows: exit 0, 1,104 giây.
Không coi khác biệt hiển thị stdout do code page là lỗi encoding dữ liệu.

Đã tạo ZIP bàn giao và so từng file trong ZIP với bundle: 62/62 khớp byte.
Bundle 22.183.896 bytes, ZIP 9.684.613 bytes tại
`staging/experimental-dataset-v1-verification-001/experimental-dataset-v1.zip`.
ZIP không chứa venv/cache/SQLite/index/weights. Các sources/normalized/trace
được copy nguyên byte, không phải bản nguồn mới đã xác minh.

Đã thử portable trên Windows hiện tại trong thư mục/process biệt lập;
**chưa chạy trên máy khác hoặc Linux thực tế**. Inventory sắp theo POSIX
path string để tránh phụ thuộc thứ tự WindowsPath/PosixPath. Chưa tạo
BM25/Dense index, embedding, qrels hoặc đo chất lượng truy hồi.

## Nội dung bàn giao và giới hạn

Dataset_version riêng với experimental=true, corpus_version=null và
release_eligible=false. Chunks/context giữ nguyên object/nội dung/ID/hash
upstream; source proof dùng đường dẫn inputs/... từ gốc bundle. Cây/spans
toàn văn các luật có candidate chỉ phục vụ tái kiểm structural windows
và issue; chúng không trở thành target/context của bộ thử nghiệm.

Không copy đệ quy lịch sử staging. Bundle đóng gói raw DOCX nguyên byte,
normalized và trace, source/extraction records pending, 107 hồ sơ pilot,
scope history/field review portable, chunk/context/encoder evidence tương
ứng, findings/rules và capture/page text cần thiết, tokenizer assets/config,
diagnostics và một số helper code chuẩn chạy validator offline stdlib.

Portable validator replay builder và kiểm nguồn/FK/context/identity/hash/
trace/evidence/selection/counts/CSV/MD. Token count là cached evidence đã
được upstream tokenizer replay trong build, không phải số đo mới của
portable validator. Không gọi PyVi/Transformers/encoder khi validate portable.

PyVi/CRF/Transformers packages và encoder weights không có trong bundle.
Muốn tokenize lại cần môi trường requirements-stage6.txt đúng pins và
encoder_input hiện hành của repository; ghi kết quả vào run khác. Chưa thử
inference trên máy bị Windows Application Control chặn DLL PyTorch. Không
cần inference để kiểm bundle; không đổi model để vượt chặn.

Metadata gaps phân biệt source, technical và applicability theo mỗi
target/dependency/field, có span IDs và date-rule IDs cụ thể nếu đã có.
Legacy target finding IDs là hồ sơ cũ liên kết với target, không chứng minh
đã kiểm từng dependency. Nguồn DOCX legacy thiếu log tải vẫn pending dù
một số đoạn có finding PDF đối chiếu. Không yêu cầu người dùng duyệt tay
từng đơn vị để đóng gói thử nghiệm hoặc tạo thêm cổng phục vụ.

BM25 và Dense phải dùng cùng chunk_id và text_for_search nền. Encoder có
preprocessing riêng, BKAI chưa là lựa chọn cuối cùng; không dùng encoder_text
đã PyVi mặc định cho mọi model. Qrels sau này tham chiếu dataset_version,
dataset_content_sha256 và ID đúng bộ. Chưa tạo qrels/query/index; tập pilot
có chọn lọc không đại diện đầy đủ miền pháp luật giao thông.

## Lệnh tái chạy

```powershell
# Tên run mới chưa tồn tại.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.experimental_dataset build --manifest staging/stage5-pilot-refinement-001/manifest.json --run-dir staging/experimental-dataset-v1-local-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.experimental_dataset validate --manifest staging/experimental-dataset-v1-local-001/dataset_manifest.json
python -X utf8 -B staging/experimental-dataset-v1-local-001/runtime/validate_dataset.py validate --manifest staging/experimental-dataset-v1-local-001/dataset_manifest.json
# Full suite đã chạy với các artifact thật sau:
$env:VTLS_ARTICLE22_MANIFEST = 'staging/article22-pdf-004/manifest.json'
$env:VTLS_ARTICLE22_PREVIEW_MANIFEST = 'staging/article22-preview-001/manifest.json'
$env:VTLS_STAGE6_MANIFEST = 'staging/article22-stage6-002/manifest.json'
$env:VTLS_POINTS_MANIFEST = 'staging/stage6-points-002/manifest.json'
$env:VTLS_COVERAGE_MANIFEST = 'staging/stage6-coverage-001/manifest.json'
$env:VTLS_SCOPE_MANIFEST = 'staging/stage5-scope-survey-001/manifest.json'
$env:VTLS_REFINEMENT_MANIFEST = 'staging/stage5-pilot-refinement-001/manifest.json'
$env:VTLS_DATASET_MANIFEST = 'staging/experimental-dataset-v1-001/dataset_manifest.json'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
```

README có các biến VTLS_* để bật integration hồi quy. Thời điểm thực thi
nằm trong execution.json, tách khỏi manifest/content hash ổn định. Checksum
không phải chữ ký hoặc xác minh pháp lý. Chuyển cả bundle, giữ path tương
đối và dùng -B; full upstream build cần refinement/repository gốc nhưng
portable validation không phụ thuộc đường dẫn staging gốc.

## File thay đổi

- `src/experimental_dataset.py`: build/validate, lựa chọn có evidence,
  export metadata/statistics/manifest và validator portable.
- `config/experimental_dataset.v1.json`: policy/version thử nghiệm;
  không đổi policy chunking/encoder.
- `tests/test_experimental_dataset.py`: fixture synthetic và integration
  dataset thật, bản copy portable, nguyên văn/ID/context và metadata pending.
- Contract dataset và báo cáo này trong docs.
- AGENTS.md/README.md nối phạm vi được phép và lệnh thực tế.

Không sửa raw/parser/builder/encoder, schema DDD hoặc ứng dụng. Không tự
stage/commit/push. Kết quả bảo toàn byte và diff riêng được lưu cùng log.

## Tái lập, bảo toàn và bàn giao

Build lại cùng input/config vào `staging/experimental-dataset-v1-002/`:
**exit 0**, 211,479 giây. So 62 file mỗi run: chỉ `execution.json` khác do
thời điểm kỹ thuật thực tế; 61 file dữ liệu/manifest/checksum còn lại khớp
byte, dataset_content_sha256 và checksum manifest giống nhau.
`reproducibility_result.json` lưu đối chiếu từng tập file. Hai run có cùng
dataset_version vì nội dung không đổi; không lấy timestamp làm phiên bản.

Kiểm SHA-256 10.708 file artifact có trước: không mất/sửa file và không
thêm file vào raw/processed/Qdrant/các run cũ. Trong 120 file workspace
đã có, chỉ nối AGENTS.md/README.md; prefix trước lượt này giữ nguyên.
Schema chính thức khớp nguyên byte `schema.sql` trong ZIP thiết kế.
HEAD giữ nguyên, staged files rỗng, git diff --check đạt. Các thư mục
scratch rỗng do chính preflight đã dừng tạo ra được dọn sau khi xác nhận
đường dẫn nằm dưới staging; không xóa dữ liệu hoặc artifact cũ.

Các file gửi rà soát (đường dẫn tuyệt đối):

- `C:\Users\Admin\Legal Semantic Search\staging\experimental-dataset-v1-verification-001\experimental-dataset-v1.zip`: toàn bộ 62 file của dataset, gồm validator/bằng chứng.
- `C:\Users\Admin\Legal Semantic Search\staging\experimental-dataset-v1-001\README.md`: hướng dẫn sử dụng và giới hạn.
- `C:\Users\Admin\Legal Semantic Search\staging\experimental-dataset-v1-001\dataset_statistics.md`: số liệu và mẫu số.
- `C:\Users\Admin\Legal Semantic Search\staging\experimental-dataset-v1-001\targets.csv`: 94 target cùng trạng thái.
- `C:\Users\Admin\Legal Semantic Search\staging\experimental-dataset-v1-001\deferred_candidates.csv`: 13 candidate cùng lý do/evidence.
- `C:\Users\Admin\Legal Semantic Search\staging\experimental-dataset-v1-001\metadata_gaps.csv`: việc còn thiếu theo target và context dependency.

Giữ nguyên bundle chính 001; run 002 chỉ để chứng minh tái lập, transfer-001
để chứng minh chuyển đường dẫn. Năm file mới của riêng lượt này là module,
config, tests, contract và báo cáo này; AGENTS thêm 1 dòng, README thêm 42
dòng. Không stage/commit hoặc đưa artifact staging vào Git.
