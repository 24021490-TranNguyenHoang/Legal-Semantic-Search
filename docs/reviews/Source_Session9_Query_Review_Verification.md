# Phiên 9 — lô review relevance năm query subset v5

Ngày **05/11/2026**, snapshot pháp luật **2025-01-01**.
**REVIEW_POOL_READY / 14 ACCEPTED INHERITED / 39 AWAITING USER REVIEW**.
Không nhập nhãn mới, chạy retrieval/tuning hoặc tính metrics.

## Git và đầu vào đã ghim

HEAD đầu phiên **c77447bc1ae8b2d5a3369d37d1bf06ed504379c4**. Worktree **đã có**
STATUS modified cùng năm file untracked của lượt nhập nhãn phiên8. Đã ghi status
và hashes trước khi sửa, giữ nguyên các file đó; chỉ prepend STATUS mới, không
nhận implementation phiên8 là thay đổi của phiên9. Baseline **6.889 file**,
danh sách ở `staging/source-session9-checks-001/preservation.baseline.json`.

Đã đọc AGENTS/STATUS, rubric/handoff/contracts phiên7–8 và code thực tế, cùng
manifest/data đã seal. Config mới `config/subset_query_review.v1.json` ghim:

| Input | Manifest | SHA-256 |
|---|---|---|
| Dataset vtls-subset-experimental.v5-candidate.1 | staging/dataset-v5-subset-006/dataset_manifest.json | 2a33d8fa503b54c574c453c33297c153074b2c3c08cdfb8a08b558d613e2d897 |
| Index vtls-bm25s-subset.v1 | staging/bm25-subset-v5-003/index_manifest.json | 657ababc157e3e509c874628bd695b20220baeec514d3f201c2d53bcfc7138af |
| Frozen queries | staging/composition-queries-001/manifest.json | f8cc9257c410c8eb578d43a0bd1912e3aa5c572829be5e33d7ee0a2045e546f0 |
| Retrieval batch | staging/bm25-subset-v5-batch-002/manifest.json | baa811c55622580eb081b21e2df1868a3dba3d12f6f2a63acd532e6ca6b2fa09 |
| Review phiên7 | staging/subset-v5-relevance-002/manifest.json | 25ad1481015179b782a466af9edb689e21d493a935202a57dfdc1bb938e73d2b |
| Accepted phiên8 | staging/subset-v5-accepted-labels-002/manifest.json | 8a14c067ed5165fb757ad55f7508f27fea8cb3fa8af33b7f861aea291cf9b9a8 |

Không chọn latest. Giữ nguyên query object/hash gồm batch_group; không sửa câu
sau khi xem kết quả. Typed accepted validator kiểm lại input manifests/payload;
frozen consumer validate/read thực tế, không load engine hoặc gọi ranking/model.

## Pool và tiến độ thực đo

Run giao **staging/subset-v5-query-review-002/**. Replay cuối:
`staging/source-session9-checks-001/artifacts-001/replay/`.

| Query | Pool | Accepted kế thừa | Chưa có quyết định người dùng | Agent null |
|---|---:|---:|---:|---:|
| dev-night_horn-3 | 10 | 3 | 7 | 0 |
| dev-driving_age-2 | 12 | 3 | 9 | 0 |
| dev-red_light-2 | 11 | 3 | 8 | 0 |
| V3-D05 | 10 | 3 | 7 | 0 |
| V3-D07 | 10 | 2 | 8 | 0 |
| Tổng | **53** | **14** | **39** | **0** |

Có **50 cặp Top10**, **14 memberships accepted**, **3 outside-positive**,
union thành53 cặp/41record khác nhau. Trong3outside, hai cặp đã accepted
(Luật36A59K1b về tuổi và NĐ168A6K1a có closure đèn đỏ); một cặp chưa accepted
là TT35A28K1/tuổi dự sát hạch. Không tạo target từ dependency. Mỗi pool entry có
origin và SHA dòng nguồn; manifest giữ toàn bộ pool, không bỏ cặp vì giới hạn phiếu.

Accepted14 khớp đúng dự kiến và nguyên object/hash/binding/reason/relation/
completeness/evidence/reviewer metadata/provenance AI hỗ trợ. File
`accepted.inherited.jsonl` chỉ là snapshot kế thừa, không phải nhập lại hoặc
nhãn mới. Accepted20/qrels cũ không sửa. Hai pending V3-D02 vẫn ở bundle phiên8,
không có template hoặc quyết định mới cho chúng trong lô này.

39 cặp có phán đoán từng cặp rõ trong config, không dùng score/rank hoặc mặc
định0 cho missing. **35 đề xuất0,4 đề xuất1** (2supporting_target,2dependency_only),
chưa là accepted. Cả39 vẫn pending quyết định người dùng; agent null0 không có
nghĩa review đã hoàn thành hoặc qrels/coverage đủ để tính metrics.

## Nội dung và bằng chứng

Đã đối chiếu own text/context và required-read cần thiết cho từng cặp; consumer
đọc đầy đủ41detail, scope payload có157unique required units và1form. Inspection
packets giữ nguyên văn/cells/closure trong checks, không gọi đây là rà toàn raw
hoặc xác minh ngữ nghĩa/pháp lý toàn bộ mọi supporting unit.

Các kết luận quan trọng:

- Còi ban đêm: các hàng tốc độ tối đa, quy định đèn chiếu xa và giảm tốc độ có
  cùng từ “khu đông dân cư” nhưng không trả lời việc bấm còi lúc23giờ.
- Tuổi mô tô: TT35A28K1 chỉ dẫn Điều59; mốc18tuổi nằm trong required-read,
  đề xuất1/dependency_only. Các quy tắc chuyển làn, dùng ô, lùi xe, mở cửa hoặc
  tuổi tối đa lái ô tô không là căn cứ tuổi tối thiểu mô tô.
- Đèn đỏ: accepted NĐ168A6K1a có căn cứ trong closure A6K9b +leadK9 +modifierK16b;
  không dùng khung400–600nghìn của Khoản1. Cảnh báo xe sự cố, tín hiệu vượt xe,
  GPLX quá hạn, đeo dây đai và dùng còi vượt xe là các nội dung khác.
- V=60: giữ đúng hàng35m đã accepted; các hàng70m/100m không chứa V=60.
  A11K1 là supporting về khoảng cách/biển báo; bảng tốc độ tối đa không phải
  bảng khoảng cách. Giữ điều kiện mặt đường/tầm nhìn, không trả35m vô điều kiện.
- So80/81: hai hàng55m/70m đã accepted vẫnpartial riêng từng hàng. Whole Điểmb
  cung cấp bảng Điểma qua dependency, đề xuất1/dependency_only; không dùng bảng
  khô ráo thành mức cố định trong mưa. A11K1 hỗ trợ điều kiện/biển báo.

Đề xuất có quotes/pointers đúng detail, source spans/cells/locator giữ nguyên,
so lại với frozen consumer. Bảng giữ header/row/đơn vị/bất đẳng thức và loại xe;
whole-source có đúng type/embedded table/required-read. Supporting formXXVI trong
closure của record GPLX không được biến thành target hoặc đáp án xử phạt đèn đỏ.

## Phiếu và template

- **A:** năm phiếu theo query, **7/9/8/7/8** cặp, chỉ cặp chưa accepted.
  Không rank/score/nhãn/reason đề xuất. Có target/context, bảng/cells và link
  trang evidence toàn required-read/proof của record.
- **B:** `proposals/comparison.md` và JSONL riêng, có proposal/reason/evidence/
  missing-part/uncertainty; không chép nhãn B vào A.
- Template mỗi phiếu có binding/pool/query/record/detail/proposal hashes và
  review_pair_id; mọi quyết định/reviewer/time/evidence-used còn trống.
  Không tự điền reviewer từ accepted14 hoặc tạo sự kiện human mới.
- `proposal_consulted/ai_assisted/independent/blind` hiện null. Nếu người dùng
  xem B/nhận AI hỗ trợ khi quyết định, ghi AI-assisted và không independent/blind;
  việc tạo phiếu không chứa nhãn không chứng minh một quá trình chấm blind.

[Handoff](../handoff/Subset_V5_Five_Query_Review.md) chỉ đúng phiếu đầu/template,
cách sao chép phản hồi ra ngoài seal, các phiếu tiếp và CLI. Phiên9 chưa có lệnh
nhập feedback mới; không đưa template mới trực tiếp vào adapter22cặp phiên8.

## Kiểm chứng đã thực thi

**68tests pass/0skip**, gồm9fixture pool/template/render mới +1artifact check
thật +58fixture/regression liên quan. Không lặp bộ nhập nhãn thật của phiên8;
chỉ validate/read accepted làm input, không gọi admit.

**14private mutations bị từ chối dù reseal**: thiếu/trùng pool, mất origin,
đổi query, sửa accepted hoặc metadata cũ, sai quote, nâng proposal thànhaccepted,
giả reviewer/điền nhãn/thiếu-trùng item template, chèn rank-score hoặc nhãn vàoA.
Các output-only mutations dùng cùng một projection input vừa validate để tránh
đọc lại upstream14lần; CLI validate riêng vẫn đọc và kiểm toàn input thực.

Replay giữ toàn payload và manifest giống byte, kể cả accepted14/templates/
phiếu/evidence/proposals/query hashes; không thêm timestamp reviewer hoặc nhãn.
Run001 prototype giữ nguyên trước khi sửa bố cục bảngprogress; code cũ giữ tại
checks/query_review.prototype.py. Bản giao002; không sửa seal001.

Lệnh thực tế và logs ở checks/build.final.receipt.json, validate.receipt.json,
tests.final.receipt.json, tests.final.log, artifacts-001/validation_report.json:

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.query_review build --config config/subset_query_review.v1.json --run-dir staging/subset-v5-query-review-002
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.query_review validate --manifest staging/subset-v5-query-review-002/manifest.json
```

Build lại cần tên NEW chưa tồn tại; dùng handoff để bật artifact test ở output
mới. Không dùng số tests/proposal để kết luận chất lượng retrieval/pháp lý.

## Thay đổi và giới hạn

Thêm src/query_review.py, tests/test_query_review.py, config/subset_query_review.v1.json,
contract/handoff/báo cáo phiên9; chỉ prepend STATUS đang có thay đổi từ phiên8,
giữ lịch sử nguyên byte. Không sửa producer/consumer/index, rubric hoặc code
hash-bound và các file chưa commit của phiên8.

Pool hữu hạn, không chứng minh qrels completeness hoặc đủ mọi positive corpus.
Source/edition/applicability pending, scope proposal, source gaps và giới hạn
phân loại xe/hạng GPLX giữ rõ trong progress. Metrics50query vẫnnull; newly
accepted0, human reviewer events created0. Không tạo qrels/accepted mới, sửa hai
pending V3-D02, chạy model/index/embedding/UI/API hoặc stage/commit/push.
Preservation và git diff --check cuối: checks/final_preservation.json.
