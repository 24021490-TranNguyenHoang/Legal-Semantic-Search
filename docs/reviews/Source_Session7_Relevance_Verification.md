# Phiên 7 — relevance và coverage BM25 subset v5

Ngày **2026-10-31**, snapshot **2025-01-01**.
**AGENT_REVIEW_PROPOSALS_READY / CALIBRATION_PENDING / METRICS_NULL**.
Đã đọc/rà nội dung thực tế; không chỉ tạo template. Không có accepted labels,
human event hoặc xác minh pháp lý. Không sửa/rebuild/tuning index/dataset/query.

## Đầu vào và Git

HEAD thực tế **4144437306340901c62a27c04850480c5b5bcd17**, Git đầu phiên sạch.
Đã đọc AGENTS/STATUS/ingestion, report/replay/Quickstart phiên6, contract v5 và
search→read, rubric/evaluation/review pack composition cũ, code validator/consumer.
Chỉ kế thừa rubric và helper kiểm chứng, **không sao chép nhãn hoặc qrels v1/v3**.

| Binding | Giá trị |
|---|---|
| Index | staging/bm25-subset-v5-003 |
| Batch | staging/bm25-subset-v5-batch-002 |
| Dataset | vtls-subset-experimental.v5-candidate.1 / candidate006 |
| Index version | vtls-bm25s-subset.v1 |
| Index manifest SHA | 657ababc157e3e509c874628bd695b20220baeec514d3f201c2d53bcfc7138af |
| Dataset manifest SHA | 2a33d8fa503b54c574c453c33297c153074b2c3c08cdfb8a08b558d613e2d897 |
| Dataset content SHA | 708d3c40fbd6e5a384792b4a717f595aa5edb8023c32fb4efb6ef136a3aa2be4 |
| Frozen query manifest SHA | f8cc9257c410c8eb578d43a0bd1912e3aa5c572829be5e33d7ee0a2045e546f0 |

Đã load index read-only, kiểm manifest/hash, dataset consumer validation, từng
batch payload/hash,50query nguyên object và re-read117detail cũ, so response.
Không chạy matrix rebuild hoặc thay loader để vượt lỗi compatibility.

## Gói rà và số liệu thực đo

Main **staging/subset-v5-relevance-002/**; replay003; companion dễ đọc
**staging/subset-v5-relevance-handoff-001/**. Tests/CLI/negative receipts tại
**staging/subset-v5-relevance-checks-001/**, coordinator/inspection/preservation
**staging/source-session7-work-001/**. Không chọn latest.

| Đại lượng | Kết quả |
|---|---:|
| Query gốc / cặp Top10 | **50 /500** |
| Unique detail trong Top10 đọc lại | **117** |
| Unique detail được gắn proposal/disposition, kể cả ngoài pool | **118** |
| Top10 proposed / pending-null | **495 /5** |
| Relevance2 /1 /0 /null | **38 /54 /403 /5** |
| Direct /supporting /dependency-only /unrelated /uncertain | **38 /46 /8 /403 /5** |
| Deep queries được chọn trước ranking sâu | **15**, query nguyên gốc Top138 |
| Deep retrieved pairs | **1.980**, không phải1.980nhãn |
| Positive ngoài Top10 đọc và đề xuất | **11cặp /6query /7record** |
| Calibration blind | **10query /22cặp** |
| Accepted / human events / qrels | **0 /0 /rỗng** |
| Metrics chính thức | **null** |

Đã đọc own text/title của các unit cần thiết trong graph subset, cùng context,
required-read,9hàng bảng/header/cells và formXXVI. Shared unit được đọc một lần
và dùng lại, mỗi cặp query-record có phán đoán riêng. Inventory138target và238
supporting đã đối chiếu; không gọi đây là rà toàn raw/bảy nguồn.6packet theo luật,
full consumer responses và alias inspection nằm trong work001. AliasRxxx chỉ là
hỗ trợ đọc nội bộ; mọi bản ghi chính thức của review dùng record_id thật/hash.

Nhãn được viết trong bảng500cặp tường minh ở config, không phân loại theo score/
từ khóa hoặc gán0 cho cặp bị thiếu. Mỗi dòng có rationale theo query và nội dung
record, evidence quote/pointer, payload/detail/native proof/DDD span/cell binding.
Offsets quote tương đối field JSON, không phải offset PDF/extraction mới.
Source/edition/applicability vẫn pending, scope proposal; positive chỉ là đề xuất
phù hợp nội dung, không là kết luận được áp dụng pháp luật tại snapshot.

Rubric [v1.2](../design/Subset_V5_Relevance_Review_v1.2.md) giữ nghĩa0/1/2 cũ,
chỉ làm rõ whole-source/embedded table dependency/form và proof v5. Một hàng đúng
có thể2/partial. Đáp án chỉ trong closure là1/dependency_only, không tạo target
mới từ unit/form.5null: D02 với ngoại lệ xe chở người/chở hàng4bánh và xe gắn máy;
D03 với nhóm đầu kéo/chuyên dùng và xi téc/kéo. Chưa đoán loại xe để chốt nhãn.

## Coverage50query và ngoài Top10

| Đề xuất coverage | Số query |
|---|---:|
| Đủ nội dung trong subset theo điều kiện đã ghi |17|
| Partial/conditional |19|
| Query mơ hồ |2|
| Chưa có target phù hợp trong subset đã rà |3|
| Nội dung cần thiết ngoài membership/bị chặn |9|

Mọi nhóm vẫn mang legal-status pending riêng. Bảng từng câu trong companion
Coverage_50_Queries.md giữ lý do/phần thiếu, không là coverage approval hoặc qrels
complete. Không suy thiếu corpus từ một ranking miss hoặc coi403proposal0 là
precision/error rate đã nghiệm thu.

Các ca đáng chú ý đã đối chiếu:

- **Mô tô ra/vào chỗ đỗ:** NĐ168Điều6 khoản1b áp ô tô/nhóm tương ứng, không
  dùng làm positive cho mô tô. Subset138/closure không có nội dung đúng đã hỏi;
  đây là gap của membership, không kết luận raw/toàn luật thiếu hoặc scope excluded.
- **Đèn đỏ ô tô:** căn cứ Điều6 khoản9b, dẫn mức phạt và modifier có trong closure
  của Điều6 khoản1a. Với câu hỏi dev-red_light-2, record này ở deep20, proposal1/
  dependency-only; không lấy400–600nghìn của khoản1 làm mức phạt đèn đỏ. QCVN6.4
  chỉ hỗ trợ xét đèn mũi tên/điều kiện, không là mức phạt; Điều7 là mô tô.
- **Trời mưa:** whole Điểm b trực tiếp nêu khoảng cách lớn hơn trị số biển/bảnga.
  Các hàng khô ráo chỉ supporting cho câu mưa. Ngược lại, whole record mang đủ
  bảnga/cells: với câu đường khô, positive của record này chỉ qua dependency,
  không gọi nguyên văn về mưa là quy định trực tiếp cho đường khô.
- **60/80/81:** giữV=60→35,60<V≤80→55,80<V≤100→70 theo điều kiệnbảng. Câu so80với81
  cần cả hai hàng, không dùng Top1 trả lời toàn câu hoặc bỏ thời tiết/biển báo.
- **Tuổi mô tô:** Điều59 khoản1b có18tuổi nhưng ở deep15/41 cho hai câu; Điều28
  khoản1 TT35 là pointer tới tuổi trong closure, ở deep49/48. Không lấy16tuổi xe
  gắn máy thay mô tô; unit phân loại110cm3/hạng tương ứng chưa có trong closure này.
- **Bảo lưu trước2025:** Điều67 TT35 có trong closure của record khoản2Điều34,
  gồm R045 đã ởTop10; thêm R104/R018/R099 ở deep36/13/42. Không gọi là thiếuĐiều67
  chỉ vì own snippet nói PET/ngày cấp/thi lại. Proposal là dependency-only.
- **MẫuXXVI:** đủ23field/line trong supporting closure R104/R018 ở deep13/14;
  không là target form riêng. Query yêu cầu mẫuXI vẫn ngoài membership được chọn.
- **I.418 và y tế5độ:** quy tắcQCVN4.1/4.2/6.4 không cung cấp thiết kế/kích thước
  I.418. Vùng xung đột I.418/I.416 không admitted. Tiêu chuẩn y tế5độ cũng không
  nằm trong membership/closure. Không mô tả hình hay tự kết luận điều kiện sức khỏe.

Deep pool15query có150cặp Top10 đã có disposition, thêm11outside đã đọc/gán
proposal =161cặp được xét theo query trong pool. **1.819cặp deep còn lại không
được chấm từng cặp**,5pending vẫn thuộc nhómTop10. Đọc inventory record không
đồng nghĩa đã chấm mọi query-record combination. Lý do chọn15query được ghi trước
tìm sâu trong deep_selection.json; work001/deep_commands.json giữ interface/
query thực tế. Không query expansion/tuning hoặc khảo sát sâu thêm query khác.

## Portability: hai vấn đề riêng, chưa sửa

Người dùng cung cấp kết quả kiểm bên ngoài: ZIP/files khớp và dataset full-read
trên Linux. Phiên này không có Linux execution receipt độc lập, chỉ tự kiểm trên
Windows và mô phỏng với PureWindowsPath/PurePosixPath trên102inventory entries.

1. **PORT-001 — inventory order:** `src/subset_bm25.py:inventory()` dùng
   `sorted(root.rglob('*'))`; load_index so list tuyệt đối. Native Windows sort
   đặt `config/bm25_baseline.v1.json` trước, POSIX đặt `QUICKSTART.md` trước;
   cùng tập file/hash nhưng thứ tự và inventory hash khác. Stored list khớp
   Windows, không khớp POSIX. Simulation JSON trong review chứa hai hash và first
   difference. Dataset consumer riêng dùng relative POSIX string sort, là code
   khác; không quy lỗi loader index thành hỏng bytes dataset.
2. **PORT-002 — runtime:** CPython cùng minor/Unicode, đúng bm25s/numpy/scipy pins
   và source BM25S vẫn bắt buộc. Sửa order về sau không tự giải quyết Python3.12
   hoặc Unicode/dependency khác. Tách lỗi runtime khỏi lỗi inventory.

Đề xuất lượt riêng: compatibility adapter/version có test canonical path ordering,
vẫn kiểm hash từng file, original content hash, config/matrix/mapping và code
binding; không reseal payload cũ hoặc bỏ validator. Sau đó mới kiểm Linux thật
với runtime phù hợp. **Không sửa loader, config BM25 hoặc index hash trong phiên7**.
Inventory POSIX của gói review mới không là sửa hồi tố BM25.

## Calibration và kiểm chứng

[Handoff](../handoff/Subset_V5_Relevance_Calibration.md) chỉ đúng calibration.md,
template trống, crosswalk riêng và proposal xem sau.22cặp đại diện direct/partial/
conditional/dependency-only, sai xe/đường/boundary, table/whole, outside coverage và
pending ambiguity. Bản blind không có score/rank/nhãn hoặc rationale agent; full
detail giữ đủ source/proof/dependency. Người dùng điền bản sao ngoài seal; chưa
ghi reviewer/time/approval thay người dùng. Duyệt22cặp không duyệt500 hoặc nguồn.

**35tests đạt,0skip**, gồm8test mới +9composition review +18evaluation hồi quy.
Fixture SYNTHETIC/FIXTURE tách khỏi corpus thật. **15negative checks thực** từ
annotation v5 bị từ chối: sai query/payload/type/dataset/hash, thiếu evidence,
accepted/reviewer giả, null→0 sai trạng thái, mất/trùng cặp, sai native proof dù
rehash detail, quote offset sai, dependency-only cite own field và template giả
approval/mất item. Chỉ sửa bản sao trong checks/private; input không đổi.

Validator CLI exit0, kiểm500+11proposals/50coverage/22calibration, exact typed
consumer detail, native/source quote/cell/dependency binding, input/hash, read
ledger và deep rankings. Blind/template/crosswalk được đối chiếu lại với cấu
hình mẫu. Validator kiểm kỹ thuật, không chứng minh rationale/coverage đúng pháp lý.
Replay003 giữ labels/IDs/detail/evidence/calibration/ranking, chỉ technical build
time/manifest liên quan khác; receipt trong checks001/replay.json.

## Thay đổi, preservation và lệnh

File mới: config/subset_relevance_review.v1.json (500phán đoán tường minh,focus/
coverage/calibration/binding), src/subset_review.py (adapter dùng helper cũ),
tests/test_subset_review.py, rubric v1.2, handoff và báo cáo này. STATUS chỉ
prepend hiện tại; ingestion/history/index/consumer/tokenizer/query không sửa.
Proto001 giữ nguyên, source validator prototype lưu riêng tại work001; bản giao
là002/replay003. Git không stage/commit/push/merge; không app/embedding/buildindex.

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_review build --config config/subset_relevance_review.v1.json --run-dir staging/subset-v5-relevance-002
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_review build --config config/subset_relevance_review.v1.json --run-dir staging/subset-v5-relevance-003
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_review validate --manifest staging/subset-v5-relevance-002/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_subset_review tests.test_composition_review tests.test_evaluation -v
git diff --check
```

Build là đóng gói review, không build BM25. Chạy lại dùng output mới theohandoff,
giữ inputs cố định. Preservation baseline26.372file và suffix STATUS/head/staged/
diffcheck ở work001/final_preservation.json. Raw/evidence/run, dataset v1/draft3082/
v3/v4/v5,index/batch/query/qrels/ZIP cũ nguyên trạng.

Cần người phụ trách evaluation xem5null, conditional boundaries/loại xe, phân biệt
direct và dependency-only, và phản hồi mẫu độc lập. Backlog tách retrieval miss,
membership gap, scope, ambiguity, legal pending và hai portability issues. Chưa
có accepted labels nên metrics vẫn null; chưa chứng minh qrels completeness,
chất lượng retrieval hơn/kém v1/v3, hiệu lực nguồn hoặc tương thích Linux thực tế.
