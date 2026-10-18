# Stage 6 — preview Điểm thuộc Khoản

## Kết quả và phạm vi

Run kết quả **`staging/stage6-points-002/`**. Pilot dùng đúng **Điều 6
Khoản 1 NĐ168**, năm Điểm a/b/c/d/đ từ `staging/stage4-docx-005/`. Đã tạo
**5 chunk, 10 context rows, 0 bị chặn, 0 quarantine** ở budget 256.
Giữ nguyên đoạn dẫn mức phạt ở context; không tạo target Khoản 1 riêng.

Snapshot **2025-01-01**, origin=agent_review. Nguồn DOCX legacy/extraction/
cây/hiệu lực vẫn pending, không có quyết định reviewer hoặc corpus mới.
Không chạy encoder inference, embedding, BM25/Qdrant hoặc kích hoạt ứng dụng.
Không stage/commit/push.

Manifest SHA-256:
`0689075e440a75187542d14404df6039874e935e1811fd0b295ec8e705f7d8f3`.

Git ban đầu sạch tại `b06bad9`; đã đọc status/diff, AGENTS, DDD, contract,
code builder/encoder/CLI và test/config trước khi sửa. Builder/encoder/CLI
v1 giữ nguyên byte để validator của run cũ vẫn kiểm được code hashes.
Policy mới **leaf-clause-point-context.v1**, không đổi công thức chunk.v1.

## Kiểm tra vùng thật trước khi dùng

Nguồn thực `data/raw/168.2024.NĐ-CP.docx`, file_id
`06431cc5-ad00-5024-bbc2-5b2d45fb8336`, raw SHA-256
`d6f009d30ba828b51e0a1a7b2dcb702c171bcddf030bac83afca1a22ece2588a`.
Stage3 extraction_id
`e_d559951c947c242755db466fc8e4bb170d6c8053cc8873457a6b7e372b1ac540`.
Các offsets bên dưới thuộc normalized.txt NFC/LF bất biến của extraction đó,
tính Unicode code point [start,end). Paragraph index của trace tính từ 0.

| Nội dung | Locator word/document.xml | Extraction offsets |
|---|---|---|
| Title Điều 6 | paragraph_index=94, /w:document/w:body/w:p[95] | [16245,16451) |
| Đoạn dẫn Khoản 1 | paragraph_index=95, /w:document/w:body/w:p[96] | [16452,16574) |
| Điểm a | paragraph_index=96, /w:document/w:body/w:p[97] | [16575,16999) |
| Điểm b | paragraph_index=97, /w:document/w:body/w:p[98] | [17000,17102) |
| Điểm c | paragraph_index=98, /w:document/w:body/w:p[99] | [17103,17396) |
| Điểm d | paragraph_index=99, /w:document/w:body/w:p[100] | [17397,17530) |
| Điểm đ | paragraph_index=100, /w:document/w:body/w:p[101] | [17531,17724) |

Điều 6 có title và text_original rỗng hợp lệ, không bịa lead Điều. Mỗi Điểm
nhận hai context theo thứ tự: **title Điều 6 → text_original Khoản 1**.
Context field offsets lần lượt [0,206), [0,122). Builder kiểm lại toàn slice/
quote hash/extraction hash/raw hash, unit/span IDs và quan hệ cha thật
document → Chương II → Mục 1 → Điều 6 → Khoản 1 → Điểm.

Đoạn dẫn Khoản 1 thực dùng:

```text
1. Phạt tiền từ 400.000 đồng đến 600.000 đồng đối với người điều khiển xe thực hiện một trong các hành vi vi phạm sau đây:
```

Ví dụ target Điểm b:

```text
b) Khi ra, vào vị trí dừng xe, đỗ xe không có tín hiệu báo cho người điều khiển phương tiện khác biết;
```

Các con số/phương tiện/chế tài không được suy ra bằng keyword; chỉ giữ
nguyên text của cây và slices nguồn. Chưa đối chiếu với bản Công báo hoặc
xác minh provenance DOCX. source_url trong JSONL là candidate đã khai báo
ở Source Inventory, được ghi rõ là chưa xác minh trong source_inspection
và bản dễ đọc, không phải log tải DOCX.

## Warning/issue và giới hạn context

Inventory giữ **36 bản ghi** của bundle bốn văn bản: 10 parser issues,
13 coverage needs_review, 13 extraction warnings. Đây không phải 36 lỗi
độc lập; một vùng có thể được ghi ở nhiều lớp. Riêng NĐ168 có 7/8/4 bản
ghi theo ba lớp này. Không resolve hoặc xóa chúng.

Các vùng xung đột/nhảy ký hiệu NĐ168 ở khoảng 92549–93405 và
196418–199140 nằm ngoài Điều 6 Khoản 1. Các warning visual của bảng đầu
văn bản và generated header/ancillary parts cũng không giao với vùng chọn.
Đã nối warning locator Stage3 với trace để xác định ranges khi có node
khớp; warning part phụ có part riêng, không gán vào thân luật.

Builder kiểm cả source slices, các dependency unit và vùng cấu trúc: mở
đầu Điều, Khoản chứa Điểm và vùng target đến heading ngang/cao hơn kế tiếp.
Issue cùng Khoản có thể chặn Điểm nếu đánh số/citation không chắc chắn;
không truyền mọi warning ở Khoản khác xuống toàn cây. Issue không đủ vị
trí/part bị chặn vì chưa chứng minh được không ảnh hưởng. Năm target có
impacts=[] trong dependency_checks.jsonl; điều này là kết quả kỹ thuật
có phạm vi, không xác minh toàn file hoặc hiệu lực.

Điểm a/c chứa dẫn chiếu và ngoại lệ tới các đơn vị khác. Chúng được giữ
nguyên; không truy tìm/ghép thêm ngoài cây cha. CROSS_REFERENCES_NOT_EXPANDED
ghi giới hạn preview, không phải yêu cầu reviewer mới hoặc chứng minh đủ
mọi context để kết luận pháp lý. Nội dung/context đã chọn không tự đủ điều
kiện phát hành; các blocker pending vẫn giữ.

## Token và quarantine

Dùng nguyên module/config encoder phobert-pyvi-input.v1 của Article22
Stage6-002; model/revision/assets/packages không đổi. Đếm toàn encoder_text,
gồm hai special tokens; không truncate/bỏ context.

| Điểm | Token search trước preprocessing | Unknown trước | Token encoder | Unknown sau | Kết quả |
|---|---:|---:|---:|---:|---|
| a | 282 | 4 | 239 | 0 | preview_only |
| b | 171 | 4 | 132 | 0 | preview_only |
| c | 218 | 4 | 170 | 0 | preview_only |
| d | 180 | 4 | 138 | 0 | preview_only |
| đ | 195 | 4 | 151 | 0 | preview_only |

Ngưỡng preview/model hiện cùng 256. Điểm a dưới ngưỡng trên **đầu vào
encoder đúng policy**, không cắt search gốc 282 token để cho pass. Nguyên
văn/context/text_for_search và content hash vẫn theo DDD; encoder_text/hash
riêng. Hết unknown không chứng minh chất lượng retrieval.

Pilot thật không có quarantine; các file issues/quarantine vẫn được xuất
rỗng và có trong manifest. Fixture kiểm riêng trường hợp vượt budget:
target/context còn nguyên ở quarantine, không nằm trong chunks/contexts
sẵn sàng. Kiểm thêm bằng tokenizer thật: budget vừa target đơn lẻ nhưng
không vừa toàn context+target phải bị chặn, không bỏ context để pass.

## Hồi quy Điều 22

Validator chạy lại nguyên baseline `staging/article22-stage6-002/`. Run/ID cũ
giữ nguyên. Builder mới dựng ba Khoản từ mapping PDF cũ trong
article22_regression/ với policy mới. So từng field payload, kết quả:

- text_original/context_text/text_for_search/content_sha256 trùng baseline.
- Token encoder Khoản 1/2/3 vẫn **106/83/82**, unknown đều 0, không truncate.
- unit_id/spans không đổi. **Chỉ chunk_policy_version** khác trong identity:
  article22-context-preview.v1 → leaf-clause-point-context.v1. Vì thế ba
  chunk ID mới khác đúng theo DDD; không cập nhật expected value tùy ý.
- article22_comparison.json lưu đủ ID trước/sau và changed_identity_fields.
  Cảnh báo PDF p21/blocker của baseline vẫn giữ, không tái đánh giá toàn PDF.

## Lệnh và bằng chứng kiểm tra

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.points_preview build --tree-manifest staging/stage4-docx-005/manifest.json --article22-manifest staging/article22-stage6-002/manifest.json --run-dir staging/stage6-points-002
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.points_preview validate --manifest staging/stage6-points-002/manifest.json
$env:VTLS_ARTICLE22_MANIFEST = 'staging/article22-pdf-004/manifest.json'
$env:VTLS_ARTICLE22_PREVIEW_MANIFEST = 'staging/article22-preview-001/manifest.json'
$env:VTLS_STAGE6_MANIFEST = 'staging/article22-stage6-002/manifest.json'
$env:VTLS_POINTS_MANIFEST = 'staging/stage6-points-002/manifest.json'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p test_stage6_points.py -v
git diff --check
git diff --cached --stat
```

Build và validator CLI **exit 0**, full replay Stage2–4 và Article22 trước
khi kiểm outputs, không mock upstream ở hai lần CLI. **171/171 tests đạt,
không skipped**, 76,138 giây (155 hồi quy + 16 mới). Lần focused cuối,
sau bổ sung kiểm budget encoder thật và optional field thiếu spans,
**16/16 đạt**, không skipped, 21,403 giây.

Test mới dùng fixture gắn nhãn FIXTURE/, source bytes simulated; không phải
luật thật và không trộn vào pilot. Kiểm nhiều Điểm/mức phạt, cùng text khác
cha/citation/nguồn, Điều không lead, thiếu cha/spans, issue vùng thiếu/xung
đột và part phụ, budget/quarantine, dẫn chiếu, immutable content/spans,
import không tác dụng phụ. Các test trên bản sao pilot thật kiểm replay,
source/parent context bị sửa sau reseal, issue ảnh hưởng không được ẩn và
hồi quy Điều 22. Test tamper mock upstream để tập trung downstream;
validator CLI riêng đã replay đầy đủ upstream như nêu trên.

Log thực tế trong `staging/stage6-points-verification-001/`:
build_final.log/build_final_result.json, validate.log/validate_result.json,
unittest.log/unittest_result.json, focused_final.log/focused_final_result.json,
preservation.json. SHA-256 **8.241 file cũ** không đổi; không thêm file vào
vị trí raw/processed/Qdrant hoặc run cũ. SQL chính thức khớp ZIP nguyên byte;
builder/encoder/CLI v1 giữ nguyên hash.
AST/JSON/whitespace và các liên kết tài liệu local đạt; git diff --check đạt,
index rỗng. Thử CLI với manifest không tồn tại trả 1, không tạo run output;
chi tiết ở missing_input_result.json trong thư mục verification.

Lần build thử `staging/stage6-points-001/` thất bại vì snapshot chưa sao
Source Inventory mà validator Stage2 cần tại raw_root. Đã bổ sung copy
inventory **có thật**, giữ nguyên validator và dữ liệu; dùng run mới 002.
Run thử có status=failed, không seal, được giữ nguyên; không coi là kết quả
thành công. Không xóa/ghi đè artifact để chạy lại.

## File thay đổi và cách mở lại

| File | Thay đổi |
|---|---|
| src/chunk_preview_v2.py | Mới: leaf clause/point, context hai cấp, issue dependencies/regions và quarantine. |
| src/points_preview.py | Mới: adapter pending Stage4, CLI pilot/replay, Article22 regression, báo cáo. |
| config/stage6_points.v1.json | Mới: policy/target/input/encoder binding và budget. |
| tests/test_stage6_points.py | Mới: 16 tests fixture/pilot thật. |
| Stage6_Point_Context_Contract.md, báo cáo này | Hai tài liệu mới về contract và kết quả thực tế. |
| AGENTS.md, README.md, Stage6_Encoder_Chunk_Preview_Contract.md | Bổ sung phạm vi/lệnh và liên kết phiên bản; giữ lịch sử v1. |

Tổng **6 file mới, 3 file cập nhật**. Không thay code parser/extraction,
encoder/model, policy/config cũ, schema DDD hoặc ứng dụng. Git index rỗng;
không commit/push.

Mở `staging/stage6-points-002/chunks_preview.md` để xem cả năm nguyên văn
và context phân theo Điều/Khoản, citation/source/spans, search/encoder text,
token/unknown/status. Dữ liệu ở chunks.preview.jsonl, contexts.preview.jsonl,
encoder_inputs.preview.jsonl; issue/region ở source_inspection.json và
dependency_checks.jsonl. Manifest/validation_report khóa toàn run.

Tái kiểm bằng lệnh validate trên. Tái build dùng cùng lệnh nhưng đổi
run-dir thành thư mục chưa tồn tại; README có ví dụ local. Run mới giữ cả
raw/inventory/input snapshots để kiểm lại được; input staging không nằm
trong Git và phải khôi phục đúng artifact thật nếu thiếu.

## Phần chưa làm trước khi mở rộng corpus

Chưa hỗ trợ Điều làm target, con sâu hơn Điểm, bảng/phụ lục hoặc tách đơn
vị dài. Chưa mở rộng context dẫn chiếu/ngoại lệ ngoài cây cha; cần thiết kế
phạm vi và source dependencies cụ thể trước khi làm. Chưa chạy encoder
inference, embedding hoặc retrieval để đánh giá chất lượng/giới hạn query
pair; không thử lại PyTorch trong lượt này. CPU PyVi/tokenizer đã chạy thật.

Pending provenance DOCX, scoped technical review, scope/hiệu lực và corpus
membership vẫn chưa giải quyết. Không suy verified từ pilot hoặc từ nguồn
URL inventory. Không thêm cổng reviewer thủ công/phân quyền/chữ ký số.
Các mục chưa làm trên là giới hạn và công việc tiếp theo, chưa được triển
khai hoặc tự coi là đã nghiệm thu.
