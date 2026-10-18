# Scope survey từ coverage Stage 6 — kết quả và giới hạn

Run **staging/stage5-scope-survey-001/**, snapshot **2025-01-01**,
origin=agent_review. Manifest SHA-256:
`40f791c118527bb680a0a8a8c0d61f70016c6446c91164506ecdae2d29ab2894`.
Git ban đầu sạch tại `c02373c`. Không stage/commit/push.

## Phương pháp và mức bao phủ thực tế

Đã đọc AGENTS, BRD/SRS/DDD, contract assessment v1.1, contract/báo cáo
coverage và các proposal/evidence/decision cũ. Dùng cây **Stage4-005** nằm
trong **coverage-001**, đã validate độc lập exit 0 (197,125 giây). Không trộn
mapping/binding PDF Điều 22. Nguồn DOCX/cây/hiệu lực vẫn pending.

Agent đọc own title/text và cha liên quan của **376 Điều/Khoản/Điểm**,
gồm 40 unit pilot cũ và 336 unit bổ sung. Đây là **9,53% của 3.946 unit
nghiệp vụ**, không phải rà ngữ nghĩa 4.000 unit hoặc toàn văn. Tập có chủ
đích gồm quy tắc, quyền/nghĩa vụ người lái, GPLX/điểm, chế tài, ca coverage
quá dài/unknown và các đối chứng hạ tầng/cơ sở. Không suy đại diện thống kê.

Config curation chứa từng unit_id/hash, source quote, regulated_subject,
lý do/BRD, phạm vi own fields và context dependency cụ thể. Code chạy lại
chỉ áp danh sách này và kiểm binding, không chạy keyword classifier hoặc
gọi mô hình phân loại. Các mục chưa đọc có method=unassessed_inventory và
reviewed_for_scope=false. Không gọi chúng là đã đánh giá ngữ nghĩa.

| Văn bản | Unit nghiệp vụ | Đã xét own fields | Chưa xét | Included | Supporting | Excluded | Pending |
|---|---:|---:|---:|---:|---:|---:|---:|
| 165/2024/NĐ-CP | 826 | 104 | 722 | 0 | 0 | 37 | 789 |
| 168/2024/NĐ-CP | 1.291 | 85 | 1.206 | 27 | 12 | 14 | 1.238 |
| 35/2024/QH15 | 857 | 64 | 793 | 9 | 0 | 26 | 822 |
| 36/2024/QH15 | 972 | 123 | 849 | 71 | 20 | 13 | 868 |
| Tổng | 3.946 | 376 | 3.570 | 107 | 32 | 90 | 3.717 |

Pending gồm **147 đã đọc nhưng hoãn kết luận + 3.570 chưa đọc**. Thêm
54 Document/Chương/Mục chỉ có structural role, tổng khớp 4.000 unit. Không
tạo unit/proposal cho bảng hoặc vùng cách ly. Không tìm thấy included trong
phần NĐ165 đã xét không đồng nghĩa toàn NĐ165 bị excluded.

BRD §3.1/SRS §1.2 ưu tiên áp dụng trực tiếp; BRD §3.3 loại hạ tầng/quy
hoạch/quản lý vĩ mô. Điều kiện phương tiện chưa được BRD chốt thành use case
cam kết toàn diện, nên các ca chưa rõ giữ pending. Snapshot mở trong BRD/
SRS dùng quyết định 2025-01-01 đã chốt ở DDD/inventory/người dùng. Giới hạn
40/60 unit của pilot v1.1 là lịch sử đối với yêu cầu mở rộng proposal này;
không sửa validator pilot, schema DDD hoặc quyền ra quyết định.

## Ghép với coverage thật

| Văn bản | Proposed included | Preview kỹ thuật | Vượt 256 | Parser ảnh hưởng | Chưa hỗ trợ | Unknown / candidate | Target cần context pending scope |
|---|---:|---:|---:|---:|---:|---|---:|
| NĐ165 | 0 | 0 | 0 | 0 | 0 | 0 / 0 | 0 |
| NĐ168 | 27 | 24 | 3 | 0 | 0 | 0 / 0 | 1 |
| Luật 35 | 9 | 9 | 0 | 0 | 0 | 0 / 0 | 9 |
| Luật 36 | 71 | 71 | 0 | 0 | 0 | 1 / 1 | 25 |
| Tổng | 107 | 104 | 3 | 0 | 0 | 1 / 1 | 35 |

Toàn 107 included có số đo từ encoder_text trong coverage đã replay, gồm
special tokens. Không đếm từ hoặc token mới để làm đẹp kết quả, không
truncate. Các unit chưa đo trong coverage giữ null. Unknown duy nhất trong
nhóm included thuộc Luật36 Điều62 Khoản5 Điểm c (91 token); chưa chẩn đoán
nguyên nhân mới hoặc suy chất lượng retrieval.

Ba included vượt budget đều NĐ168:

- Điều 6 Khoản 2 Điểm đ: **294 token**.
- Điều 8 Khoản 2 Điểm b: **270 token**.
- Điều 47 Khoản 5 Điểm a: **291 token**.

186 context dependency rows lấy từ builder output thật, gồm 32 unit đề
xuất supporting có target/field/offset/proof cụ thể. 9 cha còn pending scope
ảnh hưởng context của 35 target; đây là việc chọn phạm vi nội dung/role còn
mở, không phải source/span/structure error mới của builder. Không đề xuất
mọi cha là supporting hoặc đưa cả nhánh vào target. Các field cần thiết của
cha pending vẫn được liệt kê để rà đúng phần, không bỏ context cho vừa budget.

Trong toàn tập coverage (không chỉ included): 13 candidate bị parser ảnh
hưởng hiện có 9 excluded/4 pending; 9 Điều lá chưa hỗ trợ có 7 excluded/2
pending; 20 quá dài gồm 3 included/8 excluded/9 pending. **Issue vẫn còn
nguyên**, không vì scope proposal mà đã resolve. Số này chỉ thay đổi ưu
tiên công việc trên tập đang đề xuất, không chứng minh parser đã hoàn chỉnh.

## Ca đã biết và lịch sử

Giữ **40 proposal cũ nguyên byte** trong
coverage_snapshot/inputs/assessment/machine_proposals.jsonl, cùng HTML/PDF,
findings, date rules và decision history cũ. Proposal mới tham chiếu ID/hash
của row trước. Có **22 thay đổi**: 7 role_or_conclusion_changed,
10 conclusion_deferred, 5 pending_to_conclusion; không gọi cả 22 là reviewer
bác đề xuất, cũng không phải 22 xung đột pháp lý đã giải quyết.

| Ca | Proposal mới và lý do |
|---|---|
| Điều22 Luật36 | Điều supporting riêng title/lead cho ba Khoản included; trước Điều cũng included. Nguồn vẫn là DOCX trong khảo sát, không mang review PDF sang. |
| NĐ168 A6K1 | Khoản supporting lead mức phạt cho năm Điểm included, không tạo target từ lead. Trước Khoản included. |
| NĐ168 A39K9 | Giữ excluded theo cơ sở đào tạo/trung tâm sát hạch, giấy phép sát hạch khác GPLX cá nhân. Không có nhu cầu supporting cụ thể; issue ký hiệu vẫn giữ. |
| Luật35 A84K1/K2 | K1 pending: sửa danh mục phí, thiếu phần bảng và scope ca sử dụng chưa chốt. K2 excluded theo own text sửa danh mục quy hoạch, dù bảng vẫn chưa parse; scope không được suy từ kỹ thuật. |
| NĐ168 A16K2 và ba Điểm | Từ included sang pending vì giới hạn use case phương tiện trong BRD chưa chốt, tách riêng cảnh báo ký hiệu/cha. Chưa phải người dùng duyệt thay đổi. |
| NĐ168 A40K3 và ba Điểm | Từ chưa kết luận sang excluded: nghĩa vụ niêm yết/thử nghiệm/phân công của cơ sở chứng nhận sản xuất/lắp ráp/nhập khẩu; không phải người điều khiển. Không sửa vùng cách ly. |
| Căn cứ ngày/ngoại lệ | Nhiều supporting chung trước đây chuyển pending nếu chỉ là evidence hiệu lực, chưa có context tìm kiếm cụ thể. Evidence vẫn giữ, không xóa date rules. |

priority_cases.md có từng citation/unit_id, lý do/source quote, token nếu đo
được và evidence_refs. proposal_comparisons.jsonl giữ so sánh đủ 40 ca, CSV
lọc theo law/citation/scope/coverage/reason. Không ghi human reviewer event,
reviewer_ref, thời gian duyệt hoặc scope_status chính thức.

## Ba ưu tiên đề xuất — chưa triển khai

1. Rà đúng field context của 9 cha pending cho **35 proposed included**;
   không quyết định cả nhánh. Rủi ro ép một nhãn làm mất khác biệt nội dung;
   cần chọn role/context phù hợp trước khi phục vụ hoặc embedding tập chọn.
2. Nghiên cứu segment đủ spans/context cho **3 included quá dài**; không
   tăng budget/bỏ context, tránh mất phủ định/điều kiện. Đây là cận trên cần
   khảo sát, chưa chứng minh tách được mọi trường hợp.
3. Hoàn thiện nguồn và applicability cho **104 included có preview**:
   đối chiếu bản chính thức, ngoại lệ snapshot và ghi quyết định thực tế.
   Có cả unit scope phù hợp nhưng hiệu lực ứng viên không tại 2025-01-01
   (ví dụ Luật36 A10K3); không vì included mà cho vào corpus.

Các nhóm giao nhau, không cộng thành số target mới. Không thêm cổng duyệt,
phân quyền/chữ ký số, parser repair hoặc mở rộng use case trong lượt này.

## Lệnh và artifact

Build thực tế **exit 0, 201,765 giây**. Trước lần cuối đã dừng một lượt
preflight để bổ sung guard output không lồng trong input đã seal; lúc dừng
chưa tạo run output. Không ghi đè một bundle đã seal để chạy lại.

```powershell
# Kiểm artifact thật đã tạo; bao gồm replay coverage bằng tokenizer offline.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.scope_survey validate --manifest staging/stage5-scope-survey-001/manifest.json
# Tạo lại vào run chưa tồn tại, cùng input/config thật.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.scope_survey build --coverage-manifest staging/stage6-coverage-001/manifest.json --run-dir staging/stage5-scope-survey-local-001
$env:VTLS_ARTICLE22_MANIFEST = 'staging/article22-pdf-004/manifest.json'
$env:VTLS_ARTICLE22_PREVIEW_MANIFEST = 'staging/article22-preview-001/manifest.json'
$env:VTLS_STAGE6_MANIFEST = 'staging/article22-stage6-002/manifest.json'
$env:VTLS_POINTS_MANIFEST = 'staging/stage6-points-002/manifest.json'
$env:VTLS_COVERAGE_MANIFEST = 'staging/stage6-coverage-001/manifest.json'
$env:VTLS_SCOPE_MANIFEST = 'staging/stage5-scope-survey-001/manifest.json'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
git diff --check
git diff --cached --stat
```

Log và kết quả thực tế ở **staging/stage5-scope-survey-verification-001/**:
coverage_validate.log/coverage_validation.json, build.log/build_result.json,
validate.log/validate_result.json, unittest.log/unittest_result.json.

Validator CLI **exit 0, 239,969 giây**: replay toàn coverage bằng builder/
tokenizer thật, rồi so toàn bộ proposal/evidence/dependencies/history join,
summary/CSV/report, code/binding và metadata pending. Đây là kiểm tra kỹ
thuật hồ sơ, không tự xác minh kết luận scope hoặc hiệu lực.

Full suite **195/195 tests đạt, không skipped**, unittest 93,121 giây
(subprocess 93,453 giây), exit 0: 184 hồi quy + 11 scope tests mới. Kiểm
unit/hash/evidence/quote, proposal khác decision, cha mixed không ép con,
supporting cần target/field/offset/span thật, history không bị ghi đè, join
không mất/nhân đôi, pending không default excluded, determinism/tổng/CSV,
input thiếu/output nested bị từ chối trước khi ghi. Integration kiểm toàn
4.000 unit, token/unknown trùng coverage và roundtrip toàn catalog 4.152
evidence refs (4.149 spans + 3 BRD excerpts). Fixture gắn nhãn FIXTURE và
không trộn với luật thật; test BM25 cũ chỉ dùng artifact fixture tạm, không
xây index dữ liệu thật. Lần focused trước khi có bundle: 10 fixture đạt,
1 integration skip; full suite đã cấp đủ VTLS, không còn skip.

Preservation: **9.632 file artifact cũ** nguyên byte, không mất file/thêm
file ở raw/processed/Qdrant hoặc 62 thư mục staging cũ. Trong 110 file
workspace ban đầu chỉ README/AGENTS thay đổi. Schema SQL chính thức khớp
ZIP; src/config/tests/schema cũ không đổi. Xem preservation.json.
AST/JSON/whitespace và liên kết tài liệu mới hợp lệ; git diff --check đạt,
index rỗng (static_checks.json). Đã dọn một thư mục scratch CRF rỗng do
lượt preflight ngắt tạo ra, sau khi kiểm đường dẫn tuyệt đối và xác nhận
không có file; không xóa artifact hoặc dữ liệu có trước.

## File thay đổi

| File | Lý do |
|---|---|
| src/scope_survey.py | CLI proposal/join/evidence/history/report và validator replay, tái dùng assessment/coverage |
| config/scope_curation.v1.json | Danh sách 376 unit được agent đọc, nội dung/hash/đối tượng/lý do/BRD và dependency chính xác |
| tests/test_scope_survey.py | Fixture nhãn giả lập và kiểm tra output thật/catalog evidence/coverage |
| Stage5_Scope_Survey_Contract.md | Contract mở rộng proposal, không sửa quyền quyết định hoặc schema DDD |
| Báo cáo này | Phương pháp, kết quả, bất đồng, giới hạn và kiểm thử thực tế |
| AGENTS.md, README.md | Phạm vi mới được cho phép và lệnh chạy lại |

5 file mới, 2 file cập nhật. Code/config/schema/test cũ giữ nguyên; không
sửa raw/parser/builder/encoder hoặc ứng dụng. Nguồn/extraction/cây/hiệu lực
còn pending, chưa tạo corpus chính thức, embedding hoặc index dữ liệu thật.
