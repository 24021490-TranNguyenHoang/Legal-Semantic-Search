# Phiên 13 — candidate experimental từ preview phiên 12

Ngày thực hiện: **2026-11-17**; snapshot pháp luật **2025-01-01**.
Run bàn giao: `staging/dataset-v6-gap-002/`.
Dataset: **vtls-subset-experimental.v6-candidate.1**; candidate/experimental,
release_eligible=false, corpus_version=null. Scope proposal, source/edition/
applicability pending; origin=agent_review, không human reviewer event mới.

## Đầu vào và bảo toàn công việc

Đã đọc AGENTS, STATUS, contract/handoff/report phiên 12, code producer/consumer
v5 và preview, plan/manifest thật; kiểm Git status/diff. HEAD đầu phiên
`c9c33b1371622d6fd90338d5fb98d2e951fb10b8`. Đã có STATUS modified và **13 file
untracked** từ phiên 11–12. Đây không phải thay đổi mới của phiên 13.

Config mới `config/development_gap_candidate.v1.json` ghim:

| Input | Manifest SHA-256 |
|---|---|
| dataset-v5-subset-006 | `2a33d8fa503b54c574c453c33297c153074b2c3c08cdfb8a08b558d613e2d897` |
| development-gap-preview-002 | `cf14e7c9dce927e4400ea925e4f68c8cedf0c95691eca5980007d039aa83a469` |

Build gọi validator preview phiên 12, kiểm tiếp các binding nguồn, source
selection, aggregate accepted và evaluation ghim trong preview. Không chọn
latest, không sửa seal, không áp corrections hoặc extraction/parser lại.
Tái dựng preview kiểm bằng encoder evidence đã có; không chạy tokenizer mới,
encoder inference hoặc tính metrics. v5 nguyên byte nằm trong `base/`; preview
phiên 12 nguyên byte nằm trong `preview/`. Consumer cũ cũng giữ nguyên byte.

## Kết quả đóng gói thực đo

| Thành phần | v5 | Candidate mới | Thay đổi |
|---|---:|---:|---|
| Target records | 138 | **139** | +1 A6K9b |
| chunk.v1 | 125 | 126 | +1 |
| table-retrieval.v1 | 9 | 9 | Không đổi |
| source-retrieval.v1 | 4 | 4 | Không đổi |
| Target unit IDs | 132 | 133 | +1 unit được dùng làm target |
| Supporting unit reads, khử trùng | 238 | 250 | +12 membership |
| Supporting form | 1 | 1 | XXVI giữ nguyên |
| Graph nodes | 365 | 376 | +11 |
| Source spans | 542 | 553 | +11 |
| Encoder views | 6 | 6 | Không đổi, không target độc lập |
| Raw assets / extraction | 7 / 7 | 7 / 7 | Không thêm/sửa nguồn |

Số liệu được tính từ hợp record và dependency, không ép tổng 139. Cả **138
ID/type/payload/context** cũ giữ nguyên. **137 frame** nguyên nội dung; frame
tuổi đổi read closure/proof. Không mất table/whole-source/form hoặc nội dung view.
Inventory bảy nguồn giữ nguyên; sáu nguồn có target ở subset này, không tuyên
bố bao phủ toàn bảy văn bản.

Chi tiết từng ID trước–sau: `delta.json`, `disposition.jsonl`, `lineage.json`,
`full_read.bindings.json` trong bundle; bản dễ đọc ở
`staging/source-session13-checks-001/disposition.md`.

### A6K9b NĐ168

Thêm target `c_fcaa52f3e09aa9b0719e84d05d9d13a9bd68343ff44f596fd379553ded82f4c6`
từ preview; unit đã có trong graph v5 dưới vai trò dependency, không phải
đơn vị pháp luật vừa được tạo. Nguồn vẫn DOCX session2-001 SHA
`e31ebb1464cb0a5d56ec0b7e2237cf08b667247d8d9786bd1a872e76bd24bd41`.

> b) Không chấp hành hiệu lệnh của đèn tín hiệu giao thông;

Context title Điều 6 và lead Khoản 9 đúng nhóm ô tô; 7 required own-unit reads
giữ K16b/lead, điều kiện gây tai nạn K10b/lead và K16d. Không dùng lead K1,
không sao qrels/assessment/offset từ nhánh HTML. Token evidence giữ 120/0unknown.
Source spans/proof được consumer kiểm lại trên extraction DOCX đã chọn.
Bằng chứng agent review PDF trang 14–16 và ghi chú khác dấu phẩy trong K10b
được đóng gói; không coi đây là sửa nguồn hay xác minh toàn file.

### Target tuổi A59K1b Luật36

Giữ target `c_30a64fc1bea93d7860d4f3821af382006956ca7dcbdc7770e636782e97fb1d9e`,
payload/context và token evidence 96/0unknown. Required-read **2 → 16**:
bổ sung A1/A/B1, định nghĩa mô tô/xe gắn máy, liên kết GPLX phù hợp và ngoại lệ,
cùng title/lead cha theo preview. Không tự mở đệ quy toàn luật.

14 dependency thêm vào riêng target tuổi không đồng nghĩa 14 unit mới trong
dataset: hợp toàn bộ target chỉ tăng 12 supporting membership. Trong 12 unit
này, 2 unit A56K1b/A56K4 đã có trong graph, 10 còn lại cần bổ sung graph.
Thêm Chương III Luật36 là tổ tiên structural_only nên graph tăng tổng 11.
Không đổi payload của 365 graph node hay 542 span có sẵn.

Read binding tuổi:

- Trước: `88c03eb68284829c71060b76988771ceb93c238c4422beed21efbd510af57585`.
- Sau: `cd1663123e193841e70a0910f1f41d23fdf2ae1eba123a26770f377306bc46b3`.

Các response khác cũng đổi hash do dataset_version, adapter_version và package
locator có prefix `base/`; không phải mọi hash đổi đều là nội dung luật đổi.
`delta.json` ghi riêng frame hash, payload/context và read-response hash.
Không tự chuyển **59 accepted/2 pending** sang v6, kể cả khi target ID giữ nguyên.
Hai pending V3-D02 và evaluation phiên 11 giữ binding v5. Không tính metrics mới.

## Adapter và proof

Contract `Development_Gap_Candidate_v1.0.md`; producer `src/gap_candidate.py`,
consumer `src/gap_candidate_portable.py`. Tái dùng v5 reader/graph/cell/encoder
checks; adapter hữu hạn chỉ hợp base với preview ghim. Consumer v5 vẫn kiểm
toàn bộ base và lineage cũ; target mới có added-target lineage riêng, không bịa
old_record_id hoặc coi thêm target là thay nguồn.

41 source/evidence asset mounts của base được chuyển locator nội bộ sang
`base/objects/...`; không đổi bytes, alias hoặc extraction bindings. Thêm 4
mounts cho bằng chứng agent review (PDF và 3 ảnh). Raw/extraction cần cho các
span mới đã nằm trong base, không cần tải hay extraction lại. New graph proposal
chỉ ghi vai trò supporting/structural có giới hạn; không gán verified.

Consumer tái tạo hợp xác định rồi so plan/graph/spans/frames/proposals đã xuất;
kiểm parent/identity/position duplicate, full closure và required capability.
Full-read đọc **139 target, 250 supporting units và 1 form**. Form/bảng/whole
record giữ type và nội dung; view không trở thành target độc lập. Report delta
và full-read hashes cũng được tái tính để đối chiếu, không tin report tự khai.

## Artifact và lệnh đã chạy

Manifest SHA:
`47b23b4f8742a308f32b4c1efd0d7749a81a8aae792459b95e7035490802bdfc`.
Dataset content hash:
`02440b59ca37c71e6e39683e8d741cfd4ccdfae50d8fb3b1aabc625d644b5cab`.

ZIP: `staging/dataset-v6-gap-002.zip`, **26.200.261 bytes**.
SHA-256 (có sidecar `.zip.sha256`):
`8c9f3a50157bdf5ccc7e6df3dae8be0124ba8f7c469e436de410f6849e60b844`.
Chưa có URL chia sẻ.

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.development_gap_preview validate --manifest staging/development-gap-preview-002/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.gap_candidate build --config config/development_gap_candidate.v1.json --run-dir staging/dataset-v6-gap-002
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.gap_candidate zip --run-dir staging/dataset-v6-gap-002 --zip-path staging/dataset-v6-gap-002.zip
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.gap_candidate build --config config/development_gap_candidate.v1.json --run-dir staging/source-session13-checks-001/replay
```

Các lệnh trên đã thành công. Không dùng lại đường dẫn đã có khi tự replay:
chọn run NEW theo [handoff](../handoff/Development_Gap_Candidate.md).
Replay **112/112 file giống byte**, gồm manifests/sidecars; ZIP replay cũng
giống SHA/bytes. Receipt: `checks/replay.summary.json`.

Run001 là lần đóng gói thử trong phiên này, giữ nguyên; run002 bổ sung kiểm
report delta/full-read và frozen consumer binding trước bàn giao. Không lấy
run001 làm input mới hay sửa seal run001 để trông như run002.

## Kiểm thử và portable read

Lần đầu 13 tests báo OK, gồm 16 mutation đã reseal; PowerShell redirect stderr
gắn NativeCommandError và wrapper exit1. Giữ nguyên log, không coi exit1 đó là
kiểm chứng CLI thành công. Bốn kiểm tra trên run002 (payload/context/views,
closure tuổi, full-read/graph, budget/truncate/proof) chạy qua subprocess có
exit0, 72.053 giây. Suite đầy đủ được chạy lại trên run002: **14 tests pass,
0 skip, native exit0**, wall time 455,506 giây; có receipt để loại bỏ nhập nhằng
của wrapper. Xem `checks/tests-controlled.log` và `tests-controlled.receipt.json`.
Không cộng các lần chạy lặp thành số ca kiểm thử độc lập.

```powershell
$env:VTLS_GAP_CANDIDATE='staging/dataset-v6-gap-002'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest -v tests.test_gap_candidate tests.test_subset_candidate
```

Lần cuối gọi argv trên qua `subprocess.run(..., stdout=log,
stderr=subprocess.STDOUT)` và lưu `returncode`; không diễn giải stderr log
tiến độ unittest thành lỗi test.

Negative cases: mất/trùng target, stale unit ID, context/proof/offset/parent sai,
thiếu dependency/span/form/header/view, giả label transfer/verified, sai delta
hoặc full-read response hash. Kiểm thêm capability gate từng type, target không
thuộc membership, budget>256 và truncate. Không nới validator để pass.

Đã giải nén ZIP vào thư mục mới ngoài repository và chạy **validate/list/read/
full-read** bằng consumer đóng gói, `-I -S -B`, không site-packages. Audit gate
chỉ cho đọc candidate và Python stdlib; chặn repository/cache gốc, mạng và
subprocess. Hai truy cập thử bị chặn; bốn lệnh exit0, full-read đủ 139 target.
Log/receipt ở `checks/audit.log`, `checks/audit.json`; đường dẫn thư mục sạch
thực tế ở `checks/clean_location.json`. Đây là **cùng máy/Windows**, không phải
thử máy khác. Không dùng repository/cache để lấp file thiếu khi đọc.

## Giới hạn và phần không chạy

- Chưa thử máy hoặc OS khác; không cài môi trường trên máy người nhận.
- Không lặp toàn suite Stage1–12: chọn tests consumer/delta bị ảnh hưởng.
- Không chạy lại tokenizer hoặc encoder inference; kiểm token evidence và
  budget/view có sẵn từ preview. Không build index, đổi ranking/query, chạy
  BM25 search, Dense/embedding, tuning, UI/API hoặc tính metrics.
- Không correction/extraction/parser, render DOCX hay đối chiếu ảnh nguồn mới.
  Tái sử dụng bằng chứng phiên12, giữ khác dấu phẩy và giới hạn đọc hữu hạn.
- Không xác minh pháp lý toàn nguồn/edition/applicability; phạm vi sức khỏe,
  giấy tờ/chuyển tiếp GPLX ngoài closure tuổi vẫn là giới hạn đã ghi.
- Không nhận candidate là corpus phát hành hoặc tự yêu cầu nhóm chuyển bản.

## File của phiên này

Thêm 2 module producer/consumer, config ghim, test delta, audit harness stdlib,
contract, quickstart/handoff và báo cáo này; prepend STATUS. Không sửa module
hash-bound, schema DDD, source, parser/builder/encoder hoặc consumer v5. Báo
cáo preservation và Git diff/check ở `checks/`; các file phiên11–12 giữ nguyên.

Preservation đối chiếu **7.912 file baseline**, 7.911 nguyên vẹn; thay đổi duy
nhất trong baseline là STATUS prepend, nội dung cũ giữ nguyên byte ở cuối.
13 file untracked có trước giữ nguyên; không file bị mất, HEAD không đổi,
`git diff --cached --stat` rỗng, `git diff --check` exit0. Các file mới cũng
được kiểm whitespace và compile Python trong bộ nhớ, không tạo cache.

Đủ điều kiện kỹ thuật để bàn giao candidate experimental cùng consumer độc
lập. Việc dùng index/labels/evaluation mới cần nhiệm vụ và binding riêng, không
được suy từ lần đóng gói này. Không stage, commit hoặc push.

`checks/` là `staging/source-session13-checks-001/`.
