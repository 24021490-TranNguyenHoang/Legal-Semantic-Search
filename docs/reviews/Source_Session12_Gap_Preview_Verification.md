# Phiên 12 — preview căn cứ trực tiếp, closure GPLX và bằng chứng80/81

Ngày2026-11-16; snapshot **2025-01-01**, origin=agent_review. HEAD đầu phiên
**c9c33b1371622d6fd90338d5fb98d2e951fb10b8**. Worktree đã có STATUS modified
và6file untracked của phiên11; giữ nguyên, không nhận là thay đổi phiên12.
Không stage/commit/push, nhập dataset/labels hoặc thay index/query/ranking.

## Bản giao đã dựng và kiểm chứng

Run **staging/development-gap-preview-002/**, manifest SHA
`cf14e7c9dce927e4400ea925e4f68c8cedf0c95691eca5980007d039aa83a469`.
Có2frame đọc (1target đề xuất mới,1target cũ mở closure),23supporting own-unit
reads,31graph nodes gồm structural ancestors,41source spans. Không coi các
supporting/ancestor hoặc view là target. Reader trả đủ own fields và proof.

Đầu vào ghim qua `config/development_gap_preview.v1.json` và manifest:

| Input | Manifest/hash |
|---|---|
| dataset-v5-subset-006/dataset_manifest.json | 2a33d8fa503b54c574c453c33297c153074b2c3c08cdfb8a08b558d613e2d897 |
| subset-v5-label-aggregate-001/manifest.json | 7c4dbee482e5bc7d38e96b12e4a75684b3756a47b48d4385c713e2fd846cd56e |
| subset-v5-five-query-evaluation-001/manifest.json | 71b249f6626120cf2137ab86675874f6e6131438758df8ca64e9faa0dbbff4d1 |
| nd168-docx-session2-001/graph/manifest.json | 05823eedc958ccbd09d9c65a5acddfc3f3394f99bf39e38105c78aaf5809e1e7 |
| stage4-docx-005/manifest.json | ca30426fea4f39e797ffa0e922010cd507cf131b86df76c9174d2a0518e1c938 |

Các run dưới staging; source selection run009 và revision_manifest/encoder/
builder config cũng được pin. Aggregate59accepted/2pending được validate;
evaluation kiểm seal/input binding, không tính metrics lại. Consumer validate
toàn138targets và required-read, không load index/search/model.

## A — ô tô không chấp hành đèn tín hiệu

Trên138target: A6K9b không có own target, xuất hiện trong required-read của
1record; leadK9 tương tự. A6K16b ở required-read5record,0own target. Nội dung
có trong dependency không đồng nghĩa có document riêng để BM25 tìm trực tiếp.
Quan sát được lưu `membership.observations.jsonl`, không suy từ Top10 thiếu hit.

Giữ nguồn đã chọn:
`staging/nd168-docx-session2-001/sources/168.2024.NĐ-CP.docx`, SHA
`e31ebb1464cb0a5d56ec0b7e2237cf08b667247d8d9786bd1a872e76bd24bd41`.
Extraction `e_1d98dab5400c9b8c91ca524c10668d2ca5b211daadf94199e34c9c75d207ad90`,
normalized text SHA `26d399d5c0cad194b1b8901991b159d124b967de982cf33fd32a5fa5236074e5`.
Không sửa raw/áp corrections lần nữa/đổi sang HTML.

Target unit
`u_e374681158c47d1faf034dd565aa0520ff7e0dbd4fec1f87a7674114f2013468`:

> b) Không chấp hành hiệu lệnh của đèn tín hiệu giao thông;

DOCX paragraph164(0-based), `/w:document/w:body/w:p[165]`, extraction
offset **[31045,31102)**, source span
`s_533e37faffd21462c9febf91be50174b99bcc25712ce0f8b20b55d94204532fa`.
Chunk preview
`c_fcaa52f3e09aa9b0719e84d05d9d13a9bd68343ff44f596fd379553ded82f4c6`.
Context gồm titleĐiều6 đúng nhóm ô tô và leadKhoản9, không Khoản1.
Đo **120tokens/0unknown**, budget256, không truncate/views mới.

Required-read7own units: titleA6, leadK9, leadK16+K16b, leadK10+K10b+K16d.
Giữ nguyên toàn câu dẫn chiếu; K10b ghi điều kiện gây tai nạn và trỏ9b/c/d,
K16d liên quanKhoản10. K15 được đọc đối chiếu, không gán vào9b vì các nhánh
của nó chỉ trỏe5/K12/K11/K13/K14. Các hành vi khác trong danh sách dẫn chiếu
không tự trở thành target hoặc mở đệ quy toàn Điều6.

Tái dùng PDF chính thức SHA
`7bb11b939d162499ab404aa41a940cce05dbf071d9cbae7a8898b00d4b4a48bd`,
URL `https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/01/168-nd-cp.signed.pdf`,
accessed_at đã lưu **2026-10-16T14:33:07.439116Z**. Không tải mới hoặc lấy giờ
render làm ngày tải. Đã nhìn ảnh đầy đủ trangPDF/in **14,15,16**: lead/9b,
điều kiện10b, lead16/16b và16d. Ảnh/provenance/hash/thời điểm agent review ở
`checks/official/`; không tạo PDF text offsets/bbox chưa đo hoặc human event.

Giới hạn so nguồn: giữ dấu phẩy DOCX trong `điểm p, khoản 3` của K10b,
ảnhPDF đọc `điểm p khoản 3`. Khác biệt biểu diễn dấu câu được ghi riêng
`checks/official/comparison_notes.json`; không tự correction hoặc khẳng định
toàn đoạn khớp từng ký tự. Điều kiện gây tai nạn và dẫn chiếu9b/c/d còn nguyên.
Đối chiếu vùng này không xác minh toàn file, nguồn gốc DOCX hay hiệu lực.

## B — tuổi, hạng GPLX và loại phương tiện

Target Luật36 A59K1b giữ nguyên **payload/ID/context** từ datasetv5:
`c_30a64fc1bea93d7860d4f3821af382006956ca7dcbdc7770e636782e97fb1d9e`.
Unit `u_342199dc58177c2f4ae70a680f1e79a9c96600bb039e68e91516e36df987f6af`.
Raw `data/raw/36.2024.QH15.docx`, SHA
`db16c0345afba3b6c2ce68de8223dacd1be752abc01480941f73c8fecf58f617`;
EID `e_6150573f798da52c78b6b16bf5149a0c2046843a957393f34f6197f7c3f672ae`.
Đo lại **96tokens/0unknown**, không đổi nguyên văn hoặc offsets.

Required-read từ2 lên16own-unit reads (**14thêm**, gồm title/lead cha):
A57K1a(A1),b(A),c(B1); A34K1e(mô tô),g(gắn máy); A56K1/K1b liên kết GPLX
phù hợp loại xe, A56K4 và A59K1a giữ ngoại lệ xe gắn máy. Có title/lead cha
thực, không toàn chương. B1 cần vì query nguyên văn không giới hạn hai bánh.
Không thêm dung tích/công suất vào query hoặc gọi mọi “xe máy” là mô tô.

Tách hai vấn đề: direct tuổi ở rank15 trong frozen run là **retrieval miss**;
thiếu phân hạng/định nghĩa là **đầy đủ nội dung read closure**. Bổ sung closure
không thay text_for_search, ranking hoặc tự cải thiện metrics. Không thay nhãn
partial cũ thànhfull. Sức khỏe chi tiết, giấy tờ khác và chuyển tiếp GPLX cũ
không được kết luận từ closure hữu hạn này; dẫn chiếu vẫn giữ nguyên.

## C — tập bằng chứng80/81

Contract/checker `distance-80-81-evidence.v1`, không đổi completeness accepted.
Header/cells/row/owner/raw/EID/offset được bind consumer thật, giữ source
original riêng với derived text. Có điều kiện normal nguyên văn A11K2a và
bất lợi A11K2b, không dùng hai giá trị làm đáp án vô điều kiện.

| Tập bằng chứng | Kết quả |
|---|---|
| Hai target rows80/81 + record điều kiện bất lợi | Đạt yêu cầu khai báo |
| Bảng nhúng + required-read đủ proof | Đạt yêu cầu khai báo |
| Chỉ80; chỉ81 | Thiếu hàng còn lại và điều kiện bất lợi |
| Hai hàng không điều kiện bất lợi | Không đạt |
| Thiếu điều kiện normal; thiếu adverse | Không đạt |
| Thiếu header/đơn vị | Không đạt |
| Dependency thiếu proof; sai ranh giới; sai source | Không đạt |

Tổng11ca,2đạt/9không đạt; fixture bổ sung có trường hợp hàngV=60 hợp lệ nhưng
không chứng minh80/81. Checker kiểm80∈(60,80]→55m,81∈(80,100]→70m, so sánh
normal-only55<70/chênh15m. Bất lợi không xuất khoảng cách cố định. Có thể đủ
tập bằng chứng dù câu trả lời đến từ dependency, nhưng không sửa label1 của
record thành2, không suy Hit là đủ mọi yêu cầu hay tạo human review mới.

Đo lại cùng encoder: hai table-row **168/168tokens**,0unknown. Whole-source
TT38 **279tokens**,0unknown, giữ trọn record; hai view **237/44**, đo lại token
ID hash khớp, từng view≤256. Không encoder inference, truncate hoặc tăngbudget.

## Disposition và tác động dự kiến (chưa đóng gói)

| Vấn đề | Bằng chứng/preview | Closure | Proposal/consumer | Còn pending |
|---|---|---|---|---|
| Đèn đỏ chỉ dependency | observation138 + ảnh14–16 + red.reads | 7own units/proof | Thêm1target; thêm A6K10b vào graph hiện chưa có; chunk/required-read capability cũ đủ | Source/edition/applicability; quyết định chọn member candidate, ghi rõ khác dấu câu |
| Tuổi chưa đủ phân hạng | age.reads + raw/spans Luật36 | 16reads,14mới so target cũ | Giữ target ID/payload; bổ sung9unit vào graphv5 đang thiếu và các proof/mounts | Scope dùng supporting riêng; sức khỏe/chuyển tiếp ngoài giới hạn, không đổi ranking |
| Câu80/81 nhiều record | distance.evidence_cases + native cells/conditions | Hai hàng hoặc bảng nhúng+điều kiện | Không thêm target; giữ typed table/whole read, checker development | Chỉ yêu cầu khai báo, không nghiệm thu/phán quyết pháp lý |

Delta ID/graph đầy đủ trong `checks/membership.delta.proposed.jsonl`.
Tính cả tổ tiên cấu trúc, graph dự kiến thêm11nút:10nút đọc nêu trên và ChươngIII
Luật36 structural_only; xem `checks/graph.delta.proposed.json`. Không bỏ tổ tiên
để né FK hoặc biến ChươngIII thành nội dung target.
23supporting reads khác với sốtarget; không biến hỗ trợ thành tìm kiếm độc lập.
Own-field issue impacts của25unit đọc đã kiểm, không có warning ảnh hưởng
trực tiếp: `checks/dependency.issue_impacts.json`. Builder vẫn kiểm cả cửa sổ
cấu trúc target/cha. Không giải quyết mọi issue toàn corpus từ kết quả này.

## Kiểm chứng và lệnh

Đã chạy exit0:

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.development_gap_preview build --config config/development_gap_preview.v1.json --run-dir staging/development-gap-preview-002
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.development_gap_preview validate --manifest staging/development-gap-preview-002/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.development_gap_preview build --config config/development_gap_preview.v1.json --run-dir staging/source-session12-checks-001/preview-replay
```

Replay17file gồm manifest/sidecar giống byte. Source proof tái dựng đúng own
text/title/context, ID/parent/spans/required fields; token/view coverage không
né budget. Native read/check giữ pending. Eleven resealed preview mutations
bị từ chối: sai source/offset/parent/ID, mất target/lead/modifier/dependency,
thiếu phân hạng, giả verified/checker pass; bad pinned input lỗi trước output.

**70tests pass/0skip**,70.879s: checker fixture, real preview và hồi quy frame
reader/builder/encoder/consumer/evaluation math liên quan. Lệnh/biến môi trường
đầy đủ ở [handoff](../handoff/Development_Gap_Preview.md). Lần đầu59tests có1
lỗi import helper test_stage6 và3real opt-in skips; giữ `checks/tests.final.log`.
Lần đúng thêm tests vào PYTHONPATH trong process và chọn lớp fixture cũ,
bật3tests artifact mới: `checks/tests.corrected.log`, `artifacts-002/`.
Không sửa helper cũ chỉ để test pass. Trước đó8fixture checker đã pass.

Run001 giữ trạng thái blocked vì adapter gọi text_ref tuyệt đối; nguồn/parser
không sai. Sửa cách gọi relative ở adapter mới, tạo002, không sửa run001;
source prototype giữ trong checks. Không sửa portability ngoài phạm vi.

Preservation/diff receipt `checks/preservation.final.json`/`diff-check.log`:
đã đối chiếu7.450file baseline,7.449file giữ nguyên; chỉ STATUS thêm đầu.
raw, dataset/index/query/59accepted/2pending/qrels/ZIP/evaluation001 và file
phiên11 giữ nguyên, STATUS chỉ thêm đầu và lịch sử cũ nguyên byte. Không
claim sốtest/ảnh render là xác minh đầy đủ nguồn hoặc chất lượng retrieval.

## Thay đổi và bước tiếp theo

Thêm `src/development_gap_preview.py`, `src/distance_evidence.py`, tests,
config ghim, contract, handoff và báo cáo này; prepend STATUS. Không sửa
parser/builder/encoder/consumer cũ hoặc artifact đã seal.

Đủ bằng chứng kỹ thuật để **đề xuất phiên tạo candidate mới có version** từ
các preview trên: nạp target đỏ, mở read closure tuổi, mount nodes/spans/proof
còn thiếu và kiểm record/graph membership. Chưa làm bước đó. Consumer type
hiện có đủ, nhưng adapter candidate phải biểu diễn nguồn/frames/closure mới;
không sửa manifest/frame trongv5. Same targetID tuổi vẫn khác binding read
response; không tự chuyển accepted/qrels sang phiên mới.

Còn pending nguồn/edition/applicability, phạm vi chính xác trước lựa chọn member
và các giới hạn nội dung đã nêu. Không thêm gate chữ ký số/phân quyền hoặc
human review để chạy experimental preview. Chưa rà toàn luật/nguồn, chạy OS/máy
khác hoặc sửa bố cục DOCX; PDF chỉ so vùng hẹp. Chưa build dataset/index,
retrieval/tuning/Dense/embedding/Hybrid/Reranker/UI/API, chưa đo metrics mới.

`checks/` trong báo cáo là `staging/source-session12-checks-001/`.
