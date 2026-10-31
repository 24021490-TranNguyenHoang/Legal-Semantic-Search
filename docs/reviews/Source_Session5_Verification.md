# Phiên 5 — dataset subset138 và bàn giao portable

Ngày phiên: **2026-10-30**, snapshot **2025-01-01**.
**Đã tạo gói thực tế và kiểm full-read từ ZIP giải nén**, không còn chỉ là plan.
Trạng thái `PACKAGED_AND_FULL_PORTABLE_READ_VERIFIED`, experimental/candidate,
release_eligible=false, corpus_version=null, không legal verified/human decision.

## Binding và bảo toàn đầu vào

HEAD thực tế `c759aa496cb560a984b76a599305d863d9c117d8`, nhánh
`feature/data-pipeline-huy`. Đầu phiên đã có file review Hùng chưa commit:
`docs/reviews/Hung_Feature_Review_2026-10-29.md`; giữ nguyên bytes, không nhận là
thay đổi của phiên5. Không stage/commit/push/merge hoặc chuyển phiên bản cho nhóm.

Đã đọc AGENTS, STATUS, ingestion, DDD, contract/reports/replay phiên4 và plan thực,
source selection/membership/dependencies phiên3. Input ghim bằng
`config/source_session5.v1.json`: **source-session4-preview-007**, checks002,
source-session3-proposal-009 cùng hashes; không tìm latest. Đã chạy validator
phiên4 read-only/cached-token evidence trước build, không tokenize/model lại.

## Gói bàn giao chính

| Thành phần | Vị trí / giá trị |
|---|---|
| Dataset version | **vtls-subset-experimental.v5-candidate.1** |
| Policy | subset-candidate.v1 |
| Candidate chính | `staging/dataset-v5-subset-006/` |
| Replay | `staging/dataset-v5-subset-007/` |
| ZIP bàn giao | `staging/vtls-subset-experimental-v5-candidate1-002.zip` |
| SHA sidecar | Cùng tên ZIP + `.sha256` |
| ZIP SHA-256 | **b1965b3df6373a068a328a8200a9a01d8345e16e73c79e675575a3b7c57fa822** |
| ZIP size | **19.038.752 byte** |
| Dataset manifest SHA | **2a33d8fa503b54c574c453c33297c153074b2c3c08cdfb8a08b558d613e2d897** |
| Dataset content SHA | **708d3c40fbd6e5a384792b4a717f595aa5edb8023c32fb4efb6ef136a3aa2be4** |
| Checks cuối | `staging/source-session5-checks-002/validation_report.json` |
| Giải nén độc lập | `staging/source-session5-checks-002/independent/unpacked/candidate/` |

Chỉ ZIP **-002** và candidate006 là bản bàn giao cuối. Các run/prototype/ZIP
trước đó được giữ làm lịch sử, không ghi đè hay thay nhãn thành bản cuối.

## Membership và closure thực đo

| Đại lượng | Kết quả |
|---|---:|
| Retrieval targets | **138** |
| chunk.v1 / table-retrieval.v1 / source-retrieval.v1 | **125 / 9 / 4** |
| Unit IDs mục tiêu | **132** =129DDD +3reader-region QCVN |
| Supporting unit reads duy nhất | **238** |
| Supporting form XXVI | **1**,23dòng/field nguồn |
| Unit đồng thời target và supporting | **35** |
| Union unit IDs được chọn | **335** |
| Ancestors chỉ phục vụ cấu trúc | **30** |
| Graph nodes | **365** =346unit.v1 +19QCVN-region |
| DDD source spans | **542**; QCVN giữ source_proofs trong region nodes |
| Encoder views | **6** gắn4whole-source record; không thêm target |
| Context records trong typed frames | **210**; table/whole còn context gốc bên trong typed payload |
| Cell nguồn duy nhất trong payload | **33**,61lượt tham chiếu; không tính thành units |
| Raw source assets / extractions cần đọc | **7 / 7** |
| Content-addressed objects | **41**, gồm cả evidence assets |
| ND168 target lineage | **22** |

Không cộng record, unit, graph node, cell hay encoder view thành một số lượng
corpus. Bốn whole records giữ nguyên own text/search/view coverage; TT38A11K2b
vẫn là whole279token với2view237+44, không truncate hoặc tách thành target mới.

**138/138 ID, type, payload hash và required-unit closure khớp plan phiên4**.
Hai typed frame files và supporting-frame file được copy byte-exact và đối chiếu
manifest phiên4. Context bên trong cũng nguyên trạng. Các supporting rows của
plan giữ riêng, không lấy toàn inventory supporting_only. Không chuyển qrels,
assessment hoặc offsets từ nhánh nguồn cũ.

ND168 dùng đúng DOCX hiệu chỉnh phiên2 SHAe31ebb14…, extraction e_1d98dab5…,
graph/current IDs và source spans mới. Gói giữ22lineage/crosswalk cùng18correction
observations và ảnh có hash đã lưu; không áp corrections/extraction/parser lại.
Correction evidence giải thích derivation, không xác nhận provenance/hiệu lực.

Không nhận nămA16K2 scope unresolved, A28K2, XXIII/sáuprogramme tables, vùng caption
I.418/I.416, recovery/OCR draft hoặc inventory chưa được chọn. Full raw/normalized
files vẫn chứa vùng ngoài subset để bảo toàn hash; điều đó **không** là admission.

Bảng từng ID và so plan: `staging/source-session5-001/membership_comparison.jsonl`,
`Membership_Closure_Comparison.md`, `membership_closure_report.json`.

## Bảy nguồn inventory, sáu nguồn có nội dung được chọn

| Source | Văn bản | Target records | Supporting units | Graph nodes |
|---|---|---:|---:|---:|
| SRC-001 | 36/2024/QH15 | 70 | 78 | 132 |
| SRC-002 | 168/2024/NĐ-CP | 22 | 99 | 125 |
| SRC-003 | 35/2024/QH15 | 2 | 2 | 6 |
| SRC-004 | 165/2024/NĐ-CP | **0** | **0** | **0** |
| SRC-005 | 38/2024/TT-BGTVT | 18 | 15 | 22 |
| SRC-006 | 51/2024/TT-BGTVT/QCVN | 3 | 11 | 19 |
| SRC-007 | 35/2024/TT-BGTVT | 23 | 33 | 61 |

`source_selection.jsonl` giữ đúng7nguồn, `source_usage.jsonl` được validator tính
lại từ dữ liệu. Không đóng gói raw/content NĐ165 chỉ vì có trong inventory.
Đây là subset chọn lọc, **không phải độ phủ đầy đủ bảy nguồn**.

## Resolver, consumer và giới hạn của contract

Runtime `consumer.py` stdlib tái dùng nguyên byte `preview_read_check.py` và các
helper graph/hash/table/encoder hiện có. Không sửa schema DDD hay code hash-bound.
Graph Part/Chapter TT35 giữ original IDs/ancestors; qg_ QCVN giữ typed region
graph, không giả document/Khoản DDD. Structural ancestors không thành context/
target nếu không có required-read cụ thể.

`artifact_mounts` phân biệt ND168 this_run với source_artifact lịch sử. Không
copy cả dataset-v3 hoặc mở lại old JSONL khi read; typed payload được chọn có
hash và mount theo record ID. `asset_mounts`/extraction bindings/aliases theo EID
resolve raw/text/trace/identity vào objects/. Không rewrite path trong payload.
Response trả `original_locator` và `package_locator` riêng, full record/context,
đủ own fields của required units và form supporting, giữ nguyên mọi encoder view.
Offsets extraction/field/search tách rõ, không dùng lẫn.

XXVI có historic `scope_proposal=included`, còn membership role=supporting; giữ
cả hai, không tự sửa proposal và không biến form thành retrieval target. Các
downstream_blocker strings lịch sử trong table payload cũng giữ nguyên;
`technical_admission` chỉ mô tả adapter package đã kiểm, không gán legal verified.

Consumer validate nguyên gói trước read/list/full-read. Nếu validation thất bại
sau một số frame đã qua, read không được dùng kết quả kiểm một phần để bỏ qua
blocker. Regression test cho trường hợp này đã chạy. Missing asset/capability/
dependency không fallback repo hay fixture.

## Kiểm chứng thực thi cuối

- **35 tests pass**: tests mới về resolver/capability/dedupe/header/owner/budget/
  validation không thành công một phần, cùng hồi quy phiên2–4. Không dùng số test
  để tuyên bố đúng pháp luật hoặc retrieval quality.
- **20 negative cases bị từ chối** trong private_bundle: thiếu/corrupt asset,
  sai source/offset/extraction/old unit, missing dependency/unit content,
  capability thiếu, header/cell/owner/proof sai, form mất hướng dẫn dù rehash,
  view gap/view-as-target, truncate/budget, this_run sai và membership đổi dù
  outer manifest được reseal. Mọi mutation chỉ trên private copy.
- **71 payload/manifest replay giống byte**, full response hashes khớp; ZIP từ
  replay giống byte/SHA với ZIP bàn giao. Timestamp/receipts kỹ thuật nằm ngoài
  deterministic payload; entry time ZIP cố định là quy ước archive, không ngày tải.
- Giải nén vào directory khác build root, tạo **venv --without-pip**, chạy Python
  **3.11.9 -I -B**. Installed distributions **[]**, foreign modules **[]**.
- Audit gate chặn repo, staging gốc, dev venv và cache; **4denial probes** đúng
  kỳ vọng, **0unexpected denial**, không network/model lookup.
- **7 lần thực thi CLI đều exit0**: validate, list,4read ví dụ thật,
  full-read. Wrapper dùng runpy trong cùng clean process, không gọi đây là
  7cold-process benchmark. Stdout/stderr và argv được lưu từng lệnh.
- Từ ZIP đã dựng đầy đủ **138responses**, đọc đủ **238unique supporting units**
  và **formXXVI**, không chỉ5mẫu. Full-read output lưu tại
  `checks-002/independent/runtime-output/all-records.read.jsonl`.
- Response-content SHA từ build/replay/giải nén giống nhau:
  **c5fe430bddad6a05d05043a55f0f6ee73ad4fcf4ea0bfb8b1bc4617adb2bde71**.
- Baseline **4.023file** gồm raw/old datasets/index/qrels/ZIP/run phiên4 và review
  Hùng; không có thay đổi ngoài STATUS/ingestion được phép prepend. Receipt
  preservation cuối tại `staging/source-session5-001/final_preservation.json`.

Các lần phát triển ban đầu:001 thiếu evidence page do dùng sai base; đối chiếu
code/contract cũ cho thấy pages/ mới đúng, sửa resolver builder và chạy run mới.
002 từ chối form do nhầm scope với role; giữ payload, sửa rule theo membership
đã ghim, thêm giải thích contract.003–005/prototype ZIP giữ lịch sử. Không sửa
input/hạ ngưỡng/bỏ record để đạt138. Bản cuối006/replay007/checks002 nêu trên đạt.

## Chưa kiểm / blocker còn tồn tại

- Chỉ Windows/máy hiện tại; chưa xác nhận máy hoặc OS/Python khác.
- Word render/layout DOCX vẫn chưa kiểm được do lỗi COM ở phiên trước; phiên5
  không retry render hoặc coi ZIP/XML là thay thế. Package kiểm byte/text/spans,
  không xác nhận bố cục hoặc ý nghĩa hình.
- Provenance DOCX legacy, edition và applicability tiếp tục pending; scope chỉ
  proposal. Ngày truy cập evidence giữ nguyên lịch sử, không là ngày hiệu lực.
- A16K2/A28K2/QCVN unresolved tiếp tục ngoài subset; không xử lý mở rộng.
- Không có index/embedding/retrieval/evaluation mới; không tích hợp Hùng/UI/API
  hoặc kích hoạt corpus. Gói chỉ đủ cho bước tích hợp experimental riêng sau này.

Lệnh nhận ZIP, validate/list/read và rebuild: [Source_Session5_Replay.md](../handoff/Source_Session5_Replay.md).
