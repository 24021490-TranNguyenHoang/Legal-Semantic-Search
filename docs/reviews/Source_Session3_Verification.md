# Phiên 3 — chốt nhánh nguồn và đề xuất membership

28/10/2026; snapshot **2025-01-01**. **PROPOSAL_ONLY / SOURCE_SELECTED /
SCOPED_MEMBERSHIP_REVIEW_PARTIAL**. Chưa build dataset/index, inference/embedding,
đổi ứng dụng hoặc yêu cầu nhóm chuyển bản. Không stage/commit/push.

HEAD đầu phiên `2afb65c3f955d149da5a3b25f17c0436d1dcb792`, Git sạch. Đã đọc AGENTS,
STATUS/ingestion, BRD §3–5, scope prototype, contract composition/candidate/consumer,
report/replay/contract phiên2, manifest/ledger009/backlog và code thực tế. Baseline
phiên3 ghi hash **3.381 file**, gồm công việc phiên2 đã được commit và artifact
bảo vệ. Không suy trạng thái Git hoặc số liệu từ chat.

## Quyết định người dùng và đề xuất agent

**Người dùng chọn nhánh nguồn xử lý**, không xác nhận hiệu lực hoặc đã đọc từng
đơn vị. Chỉ source_selection có `selection_origin=user_instruction`, bind nguyên
chỉ dẫn đã nhận và SHA. Scope/membership/dependency mới đều `origin=agent_review`,
human review/reviewer_ref null, release=false. Không tạo assessment verified,
accepted relevance label hoặc ghi người dùng đã phê duyệt đơn vị.

| Nguồn | Nhánh đã ghim | Vai trò nguồn khác |
|---|---|---|
| SRC-001 Luật36 | `data/raw/36.2024.QH15.docx`, graph/extraction `stage4-docx-005` | PDF Điều22 cũ là evidence riêng, không chuyển binding review sang DOCX |
| SRC-002 NĐ168 | `nd168-docx-session2-001`, DOCX SHA `e31ebb1464cb0a5d56ec0b7e2237cf08b667247d8d9786bd1a872e76bd24bd41` | HTML/PDF chỉ đối chiếu; không áp lại5sửa phiên1 hoặc20edit phiên2 |
| SRC-003 Luật35/QH15 | DOCX raw + `stage4-docx-005`, giữ2bảngA84K1–2/12ô/proofPDF | Không nhầm TT35/BGTVT |
| SRC-004 NĐ165 | DOCX raw + `stage4-docx-005` | Không loại cả nguồn; đã rà thêm nhóm20/21/61 |
| SRC-005 TT38 | Công báo8tr `data/raw/official/38-2024-TT-BGTVT/congbao-1355-1356.pdf`, SHA `e27582e2bce4aee27ebc85ffc43731790f887782375ab76e52e2f61981603689`, extraction/graph `tt38-preview-003` | Bản7tr chỉ đối chiếu; không nối hai bản |
| SRC-006 TT51/QCVN | Năm PDF Công báo425tr, native `qcvn-gazette-extraction-001`, graph003 | DOC/Antiword/403tr/transcription chỉ đối chiếu tại vùng có bằng chứng |
| SRC-007 TT35/BGTVT | Hai raw PDF69+179tr, native `tt35-full-layout-001`, graph Part/Chapter `circular-priority-006`, tám owner từ `tt35-owner-tables-002` | Adapter mới sửa dependency có bằng chứng, không sửa run cũ |

TT38 là lựa chọn kỹ thuật được người dùng giao agent quyết định: bản8tr đã có
raw bền vững, đúng text/trace/cells/graph và consumer proof binding. Raw7tr không
được ghép thêm. Full file_id/path/hash/part_order, extraction IDs/text SHA và
graph manifest SHA của **12 file thuộc7nhánh** nằm ở source_selection.jsonl.
Không lấy thời điểm chạy làm ngày tải hoặc hiệu lực. Nguồn/edition/applicability
tiếp tục pending theo hồ sơ thật.

Lựa chọn DOCX NĐ168 của người dùng thay **đề xuất** HTML trong báo cáo phiên2;
không sửa lại báo cáo lịch sử. Các hồ sơ PDF Điều22 ở AGENTS là nhánh lịch sử
riêng, không mặc định là lựa chọn source cho lượt này. BRD/scope prototype còn
thông tin snapshot/corpus cũ được báo rõ; không dùng số1.457 hoặc bốn nguồn
để admission. Không thấy mâu thuẫn buộc sửa BRD đối với116record được đề xuất:
GPLX cá nhân thuộc UC03, hạ tầng/cơ sở/chương trình chuyên ngành không tự mở
thành target; supporting chỉ qua điều kiện cụ thể.

## Artifact bàn giao

Run chính **`staging/source-session3-proposal-009/`**, replay **010**. Không chọn
theo số lớn nhất. Config versioned `config/source_session3.v1.json` bind input
hashes và128review unit cụ thể. Các run probe001/005/006 giữ lại; probe002–004
dừng trước output do lỗi checker/validation đang triển khai, không là bản bàn giao.

| File trong run009 | Nội dung |
|---|---|
| source_selection.jsonl | Lựa chọn nguồn, path/hash/run/extraction và origin |
| membership.proposals.csv / .jsonl | Từng unit, nguyên văn trong JSONL, role/scope/technical/membership, reason, spans, blocker và candidate refs |
| membership_review.md | Bản dễ đọc các đơn vị đã rà; chưa rà giữ trong CSV/JSONL |
| table_row.membership.proposals.csv / .jsonl | Chín row record TT38, ID/anchor thật; không gộp thành một row tùy ý |
| nonunit.membership.proposals.jsonl | Form/annex/table amendment/recovery region, tách khỏi legal units và text target |
| dependencies.jsonl | Required-read theo unit/record; gồm inventory candidate cũ và các closure hữu hạn mới |
| tt35_owner.decisions.csv / .jsonl | Từng ca8owner, scope/use/annex/crosswalk/read_ref |
| table_owner.records/views/crosswalk.jsonl + table_owner_reads/ | Typed preview, full read, encoder view và ID delta |
| nd168.phase1_to_phase2 / legacy_branch_mapping / span_crosswalk.jsonl | Ba loại mapping không được đánh đồng |
| law36.lead_checks.jsonl / law35.table_checks.jsonl | Kiểm tra cụ thể đoạn dẫn22/26 và hai bảng/12ô |
| qcvn.remaining.jsonl |929dòng chưa gắn owner giữ nguyên locator/reason |
| v3.comparison.jsonl / v4.comparison.jsonl | Delta đề xuất riêng từng bản; không xóa payload/qrels |

Coordinator `staging/source-session3-001/` giữ user_instruction/hash, baseline,
logs, runtime probe và initial Git. Word probe riêng `source-session3-word-001/`.
Validator/negative/replay/preservation bản cuối ở `source-session3-checks-003/`;
checks002 là kiểm run007/008 trước khi bổ sung cặp required-read A32K6. Staging không thuộc Git; clone code phải có
đúng các input artifact trong config để replay.

## Scope và membership: số liệu, không phải nghiệm thu toàn corpus

Inventory gồm **5.375 unit/region graph node** của bảy nhánh, không chỉ v4.
Trong đó có528node graph QCVN riêng, không ép thành enum Khoản/Điểm DDD.
**128 unit được agent đọc/rà mới có hash cụ thể**; các kết quả cũ chỉ reuse khi
full unit payload/source binding còn đúng. Nhánh NĐ168 mới không nhận assessment
cũ. Năm nghìn vị trí chưa quyết định scope không bị chuyển sang excluded.
Method thực tế:128review mới,327hồ sơ reuse đúng binding,3whole-subtree review
có sẵn;4.917node còn unassessed_inventory. Trong5.013unresolved có96vị trí đã
xét nhưng chưa đủ kết luận; không gọi tất cả unresolved là đã/chưa đọc như nhau.

| Nguồn | Node | In scope | Out of scope | Unresolved | Target unit có bound record được đề xuất |
|---|---:|---:|---:|---:|---:|
| Luật36 |982|91|13|878|70|
| NĐ168 |1309|28|0|1281|0 — record nguồn mới chưa dựng |
| Luật35/QH15 |868|2|26|840|2|
| NĐ165 |846|16|88|742|0 —16unit supporting hữu hạn |
| TT38 |59|27|22|10|9:8text +1whole-source, thêm9table-row record riêng |
| QCVN |528|3|0|525|3whole-subtree record |
| TT35/BGTVT |783|39|7|737|23text |

**116 retrieval record đề xuất đủ kỹ thuật để xét packaging**:103chunk.v1,
9table-retrieval.v1,4source-retrieval.v1. Đây là proposal, chưa tạo dataset mới,
chưa legal verified. Tách supporting/structural, không cộng encoder views thành
target. Scope của **5.013 node còn unresolved** là backlog thật, không bỏ khỏi
inventory hoặc tự đánh dấu đã đọc. Có3.224dòng dependency inventory/closure;
chỉ quan hệ của target tương ứng mới có nghĩa khi xét target đó, không phải
3.224dependency được kích hoạt hay đọc rà ngữ nghĩa đầy đủ.

NĐ165: đã đọc toàn own text các subtree20/21/61, xem danh mục tiêu đề70Điều để
phân nhóm, không gọi việc xem tiêu đề là rà đầy đủ70Điều. Nhóm cơ quan bảo vệ
hạ tầng/cơ sở dữ liệu đề xuất ngoài scope theo BRD3.3; điều kiện A21K1/K2/K8
được gắn **supporting cho NĐ168 A12K12**, cùng Luật36 A77K1/K3a-b. Mục đích,
loại đường, phương án và nghĩa vụ người dùng lòng đường giữ đủ. NĐ168 target
đó vẫn pending preview nguồn mới; không mở hạ tầng thành use case độc lập.

Luật36: own lead Điều22/26 và source spans được roundtrip. **Ba chunk Điều22 và
ba chunk Điều26** trong v3 giữ đầy đủ field đoạn dẫn trong context, offsets0→len,
không đem lead prototype đã mất trở lại. Luật35/QH15: hai bảng/12ô giữ nguyên
source proof DOCX và ảnhPDF67. Proposal excluded của vùng bảng vẫn có lý do
phí/thẩm quyền/quy hoạch, không biến thành bảng mức phí hay Khoản mới.

## NĐ168: lineage và source binding

- Phiên1→2: **1.309→1.309**, bijection đầy đủ,1351span có cả đầu cũ/mới.
  Parent/FK/unit IDs/spans được kiểm trên extraction DOCX mới. Root text đổi làm
  parent identity đổi theo; không đổi công thức ID hoặc áp lại corrections.
- Stage4 DOCX cũ: **1.304 mapping qua chuỗi phiên1 rồi phiên2**, không chỉ lookup
  citation. Đặc biệt marker A39K9đ cũ phải theo locator-chain sang ký hiệu d đã
  sửa, không gán nhầm vào Điểm đ mới. Năm đơn vị phục hồi phiên1 vẫn còn.
- HTML full: **1.309** correspondence riêng; v3 HTML sparse: **10** correspondence
  riêng. Own-text bằng nhau sau whitespace lần lượt1242/1309 và9/10; các chỗ khác
  giữ cảnh báo, không coi correspondence là chứng minh tương đương edition.
  Đây chỉ số so **text_original**, không kết luận full payload/title/provenance.
- So DOCX Stage4 own-text:1287/1304khớp ngoài whitespace,17khác. Cả hai full unit
  hashes được lưu, không đổi raw để ép giống. Phase2 report86field vẫn nguyên.
- Mapping không chuyển offset, assessment hay qrels. Các record NĐ168 cũ cần
  dựng lại chunk/context/proof theo graph mới trước admission.28scope mới gồm
  chế tài/quy tắc/chuyển tiếp; không phát hành1309unit chỉ vì parser đạt.

Tìm được Word ở HKLM AppPaths dù PATH không có. Đã thử **DispatchEx Word riêng,
ẩn, macro disabled, mở bản copy read-only**, không gọi lại sửa DOCX. COM thất bại
`-2147023584` (“A specified logon session does not exist…”). Receipt và copy tại
word-001; hash bản nguồn nguyên vẹn. **Chưa render/kiểm bố cục Word**. Đây là
blocker môi trường/bố cục riêng, không dừng source/span/membership checks khác.

## Tám owner TT35: scope và dependency được rà riêng

| Owner | Đề xuất của agent | Required-read đã kiểm | Kết luận |
|---|---|---|---|
| A6K1 | supporting-only cho A28K2 | A6K2 +AnnexII | Không target chương trình độc lập |
| A7K1 | supporting-only cho A28K2 | A7K2 +**AnnexII** | **Đính chính AnnexIII phiên2** |
| A8K1a | supporting-only cho A28K2 | A8K2 +AnnexII | Giữ hạng/giờ/km/header/continuation |
| A8K1b | supporting-only cho A28K2 | A8K2 +AnnexII | Như trên, owner/nguồn riêng |
| A8K1c | supporting-only cho A28K2 | A8K2 +AnnexII | Như trên |
| A8K1d | supporting-only cho A28K2 | A8K2 +AnnexII | Như trên |
| A21K4c | excluded target | A21K4a/b | Thời gian tập huấn sát hạch viên, không người tham gia |
| A46K2 | excluded target | A46K1 | Chương trình bồi dưỡng chuyên ngành, chưa có target cần đọc |

Sáu bảng là supporting theo điều kiện chương trình ghi ở **A28K2**, không
included toàn đào tạo. A28K2 dẫn **Phụ lụcXXIII PDF phụ lục trang127**; native
region giữ đầy đủ nhưng chưa có checked form representation. Vì vậy **target
A28K2 vẫn pending**, không suy chỉ có bảng là đủ nghĩa. XI/XXVI là hai mẫu khác,
không dùng thay XXIII. AnnexII trả toàn source/cells, chưa tuyên bố đọc rà ngữ
nghĩa đầy đủ12trang; các dẫn chiếu chỉ điều hướng không mở đệ quy toàn corpus.

A7K2a và ảnh rawPDF8 nói “Phụ lục II”. Adapter tối thiểu gọi lại compose/
read_record/encoder_views có sẵn, sidecar override có unit SHA và image SHA.
Run002/code cũ bất biến. **Một table record ID và wrapper view ID đổi** do payload
required_dependencies/source-record SHA đổi;7record khác, toàn legal unit IDs,
text_for_search/content hash/token IDs giữ nguyên. Không fake bảng thành chunk.
Tám full read giữ11table/590cell,84encoder view, budget256không đổi; sửa dependency
không đòi tokenization/inference mới. Consumer thiếu capability hoặc bỏ cell/
header/dependency/proof bị từ chối. composition consumer v1 cũ vẫn giữ nguyên;
adapter preview mới chỉ mở type table-owner, chưa tích hợp serving/dataset.

## QCVN và các giới hạn còn thực

Ba target text đã có subtree đầy đủ **4.1,4.2,6.4** được giữ theo proof Công báo,
đọc cả nội dung con/context. **Không** nhận6recovery region hay11dòng B18 thành
text target.929dòng chưa gắn owner giữ nguyên; không OCR/khôi phục hình thêm.
Caption I.418/I.416 có source_conflict/blocked trong nonunit proposal, không nằm
membership trả lời thống nhất. 4.1 dùng reader Công báo đúng và đính chính lỗi
agent cũ, không còn bị gọi là xung đột nguồn. Antiword không thay toàn QCVN.
Lưu ảnh chỉ là dependency ảnh, không chứng minh đã hiểu ý nghĩa hay kích thước.

TT38 A11K2b giữ whole source279token và2view **237/44token** theo input cũ,
không cộng số view thành target và không cộng naïve hai count có special tokens
để suy full-input count. Điểm a/toàn bảng3/10cell và các context vẫn được giữ qua
payload được validator v4 kiểm. Chín hàng bảng có anchor/record ID riêng.

Các giới hạn khác: source/edition/historical applicability toàn bảy nguồn vẫn
pending; nghĩa vụ điều ước ở TT35A45 và closure chương trình/hồ sơ A14K3 giữ
blocker cụ thể. Không nâng mọi unit active từ ngày hiệu lực chung. Quan sát
ngoại lệ Luật36A10K3ngoài snapshot giữ blocker/evidence cũ, không tự accepted.
TT35A32K6a/b được bind required-read theo cặp quy tắc đổi GPLX/ngoại lệ điều ước;
chỉ hai field nguồn, không đệ quy hoặc khẳng định từng giấy phép quốc gia đã được
điều ước công nhận. Chunk/search/token giữ nguyên, hai dependency thêm vào plan.

## So v3 và v4 riêng

| Delta proposal | v3 (3115member cũ) | v4 (146member cũ) |
|---|---:|---:|
| Giữ retrieval record |104|116|
| Đổi nguồn/ID, pending rebuild |1023|27|
| Supporting-only |33|3|
| Đề xuất excluded |104|0|
| Pending khác |1851|0|
| Added proposal ngoài tập cũ |12|0|

v3 có3127dòng comparison vì3115dòng cũ +12đề xuất thêm. v4 có146dòng. Không ép số
target tăng. Form XI/XXVI và chuyển tiếp A67 được dùng supporting có dependency,
không tự là câu trả lời độc lập. Không xóa payload/member/qrels cũ hoặc yêu cầu
nhóm dùng proposal. Đổi nguồn/ID được ghi trước, không đếm thành hai căn cứ.

## Kiểm chứng, thay đổi và bước có thể làm tiếp

41tests liên quan pass: session3 gates, session2, source_revision, full_ingestion,
circular_dataset; logs/exit/command trong coordinator. Artifact checker kiểm input,
CSV/JSONL, full read; **12ca sai bị từ chối,31payload replay giữ hash**. Baseline3381file không đổi
ngoài STATUS/ingestion được phép; `git diff --check` và whitespace file mới được
kiểm trước bàn giao. Chỉ Windows/Python3.11.9 hiện tại, chưa máy/OS khác.
Không dùng các số này làm kết luận pháp lý hoặc retrieval quality.

File mới: `config/source_session3.v1.json`, `src/membership_proposal.py`,
`src/ingestion/table_owner_adapter.py`, `tests/test_session3_membership.py`,
`tests/check_session3_artifacts.py`, contract/report/handoff phiên3. STATUS và
ingestion thêm đầu hiện trạng, giữ lịch sử nguyên byte. Code/schema/hash-bound
cũ không bị sửa. Probe failures giữ logs: dependency unit-universe của row table,
quote không inline trong proofDOCX và key trong full-read annex khác unit dep;
đã sửa harness/validation view theo source contract thật, không nới dữ liệu để pass.

**Có thể mở lượt packaging candidate experimental** cho116record +đúng supporting
closure đã liệt kê, sau khi kiểm adapter khi đóng gói; chưa đủ để tự tạo ngay cả
bộ nguồn NĐ168 mới hoặc toàn bảy nguồn. Cần dựng preview theo nguồn NĐ168 đã chọn,
giữ lineage; làm formXXIII/closure A28K2 nếu chọn target đó; xử lý A14K3/A45 và
scope5013vị trí còn lại theo từng nhóm có căn cứ. Đó là công việc dữ liệu/đề xuất
agent, không mặc định cần người dùng ký duyệt mọi đơn vị. Chỉ những kết luận pháp
lý thực tế/human decision mới cần được ghi nhận đúng chủ thể khi có.

[Lệnh validate/replay và đầu vào](../handoff/Source_Session3_Replay.md).
