# Bàn giao kỹ thuật bảy nguồn — 24–25/10/2026

**CANDIDATE_TECHNICAL_PASS / FULL_SOURCE_COMPLETION_PENDING**.
Đã hoàn thiện phần reader/provenance, representation và kiểm chứng đóng gói
đang dang dở. **Chưa hoàn thành toàn bộ nội dung, scope và applicability bảy nguồn**.
Snapshot vẫn 2025-01-01; không human review/accepted/verified, không đổi bản nhóm.

HEAD kiểm tra: `7a60f2d375b981092717b8b24bbc6a0a2037ab75`. Đầu lượt 24/10 worktree
sạch; lúc tiếp tục 25/10 đã có AGENTS và các module/config/test chưa commit từ
lượt trước. Giữ lại, tiếp tục sửa trong phạm vi này; không reset/stage/commit/push.
Các run thử/lỗi được giữ, không chọn theo tên mới nhất hoặc ép số lượng đầu ra.

## Artifact hiện hành

| Đầu ra | Run |
|---|---|
| Inventory/ledger/backlog hiện hành | `staging/seven-source-ledger-009/` |
| Bảng tiến độ, CSV20 file, bảng13 blocker TT35, bản đọc146 record | `staging/seven-source-handoff-001/` |
| Ma trận trước–sau từ baseline thật, phân biệt output có sẵn/tạo mới | `staging/seven-source-progress-001/` |
| Candidate mới | `staging/dataset-v4-candidate-006/` |
| Kiểm portable 5 loại read, page/OCR/hash | `staging/seven-source-artifact-checks-003/` |
| Validate/read bản cuối, runtime/payload equivalence | `staging/seven-source-final-read-001/` |
| 8 ca negative có reseal ngoài, lỗi logic bị từ chối | `staging/seven-source-negative-checks-002/` |
| So12 ô DOCX với PDF Công báo, kiểm thêm180 trang | `staging/seven-source-comparison-checks-001/` |
| Logs hồi quy, replay graph, kiểm cuối | `staging/seven-source-validation-001/` |

Candidate version `vtls-seven-source-experimental.v4-candidate.5`, adapter
`seven-source-candidate.v1.3`. Có 146 member: **131 text chunk +9 table record
+4 whole-source record +2 form record**. Form mới chỉ hỗ trợ đọc layout;
chưa có encoder/search projection. Bốn whole-source target gồm TT38 A11K2b
và ba subtree QCVN: 4.1, 4.2, 6.4. Encoder views không là target độc lập.

So v3: **132 unchanged, 14 added, 2.983 removed khỏi membership**, 0 replaced,
0 conflicted. Phần removed là 2.919 pending scope và64 excluded; payload cũ còn
nguyên trong component, không xóa dataset/index/qrels nào. Không chọn lại tất cả
3.115 payload lưu trữ thành target. Dataset có sáu nguồn có member; NĐ165 chưa có
included proposal đủ để chọn, không tự coi toàn NĐ165 excluded.

Các revision candidate001–005 vẫn giữ. Bản006 chỉ thay graph annex QCVN chưa
được chọn; 146 membership và payload target/context/form/whole-source của005 giữ
nguyên byte, runtime validate/read cũng giữ hash. Ba annex observation B/G/K đổi
identity do bỏ ownership suy đoán qua serial part; 525/528 node giữ ID. Crosswalk
ở `qcvn-rule-graph-003/region_crosswalk.jsonl`. Không đổi công thức unit/chunk DDD.

## Ma trận nguồn thực đo

Số PDF tính cả bản đối chiếu/edition thay thế, **không phải số trang duy nhất của
corpus**. 20 file nội dung =10 raw đã đăng ký +4 PDF bằng chứng cũ +1 HTML chính
thức +5 PDF Công báo mới; file metadata/capture HTML phụ được liệt kê riêng.
Không đồng nghĩa đã có20 source_file hợp lệ trong schema DDD chính thức.

| Nguồn | File / trang PDF | Sau xử lý | Giới hạn còn lại |
|---|---:|---|---|
| SRC-001 Luật36 | 3 /82 | Giữ cây DOCX982 unit và extraction PDF có sẵn;70 member text trong candidate | Scope878 vị trí cũ chưa đọc/rà xong; warning PDF phần2 trang21 giữ riêng; không verified toàn file |
| SRC-002 NĐ168 | 3 /111 | HTML chính thức mới:1.309 unit, đủ55 Điều, field/spans roundtrip; đọc ảnh84–86 và so marker A39K9/A40K2–3; giữ nhánh A16K2 đã khôi phục |111 trang PDF scan không text; HTML không tự chứng minh toàn snapshot tương đương; các vùng sửa đổi/trích luật có coverage chưa parse |
| SRC-003 Luật35/QH15 | 2 /69 | Reader mới đủ69 trang,2 bảng/12 ô PDF; cả12 ô đối chiếu DOCX,8 khớp và4 chỉ khác whitespace | Không biến ô thành Khoản; hai bảng danh mục phí/thẩm quyền/quy hoạch đề xuất excluded có lý do BRD; own text/cây DOCX khác vẫn pending |
| SRC-004 NĐ165 | 1 /— | Giữ846 unit DOCX và preview;20 long cases toàn bộ bốn nguồn đã có encoder-view representation |809 scope position của NĐ165 chưa rà xong; không có member NĐ165 trong candidate hiện tại |
| SRC-005 TT38 | 2 /15 | Đọc riêng bản7/8 trang; giữ3 bảng/9 row record; A11K2b đủ279 token gốc được biểu diễn bằng2 view dưới256 | Pending source/edition/applicability; required-read Điểm a và toàn bảng3 được bind; không cắt context hay nâng budget |
| SRC-006 TT51/QCVN | 7 /829 | Bản cũ1+403 giữ nguyên; nguồn Công báo5 phần425 trang mới,0 NUL/U+FFFE;38 bảng/1.153 ô/922 image objects; graph84 Điều/416 decimal rules;3 target text |4 trang reader rỗng không coi trắng;7 trang vector-dense chưa dò bảng;203 OCR draft chưa đạt chất lượng target; hình/caption/annex còn chưa xử lý đủ |
| SRC-007 TT35/BGTVT | 2 /248 |69+179 trang; graph Phần/Chương783 unit;148 bảng/5.541 ô;44 nhóm phụ lục;572 preview rebind ancestry;13 preview hẹp mới,2 mẫu đơn có layout | Trong13 blocker cũ:5 Điểm anh em được gỡ ảnh hưởng bảng;8 owner bảng vẫn chặn;4 long case chỉ đạt representation encoder-view, không tự included |

Graph Part/Chapter783 của TT35 **đã có trước đợt này**, được tái sử dụng. Tám
preview Điều34 cũng đã nằm trong572 preview, không kể thêm lần nữa: lượt này
hoàn thiện membership/dependency của chúng. Sau khi gộp5 sibling target mới,
có577 text preview duy nhất; không cộng572+13 thành585.

Ba nguồn TT giữ source ID khác Luật35/QH15; các alias source/file ID theo law/hash
được lưu, không sửa ID dataset cũ. Inventory009 đã gắn cả extraction HTML, URL và
ngày capture có thật. DOCX không có log tải vẫn null, không điền ngày chạy mới.
CSV trong handoff đã đọc bằng `csv.DictReader` mặc định và đối chiếu đủ20 dòng với
JSONL; URL qua validator scalar đang dùng, không trở lại lỗi PowerShell object.

## Coverage và backlog

Ledger009 có1.354 page rows,44.694 interval rows và6.723 unit/region rows qua các
nhánh nguồn; không gọi6.723 là số legal unit duy nhất. Mọi PDF trong inventory có
extraction branch; PDF scan có reader rỗng vẫn là blocker thật. DOCX dùng trace
part/paragraph/table/row/cell, không tạo số trang giả.

5.685 nhóm backlog gộp theo law/vị trí/locator/loại điều kiện, còn5.626 nhóm:
5.043 scope review;469 page visual/reader;49 nhóm ranh giới annex QCVN;37 source
region;20 source/edition;8 owner bảng TT35. Một vị trí có thể có nhiều điều kiện;
không cộng chúng thành số điều luật lỗi độc lập. 940 dòng continuation QCVN nằm
trong49 nhóm trang nguồn, không phải940 Điều hoặc trang.

Đã nối source-only backlog relevance review: năm Điểm A34K2 và Điểm b TT38 có
member candidate; Khoản34K2 là context, không tạo target thứ hai từ đoạn dẫn.
Không tạo/chuyển qrels hoặc nói query đã có quality metric mới.

Scope pending là **công việc agent còn phải đọc/rà**, không phải yêu cầu người
dùng phê duyệt trước khi tiếp tục preview. Các node graph cũ giữ pending khi
proposal mới chỉ xét đúng subtree/form có hash; không truyền scope xuống con
hoặc lấy membership của một field làm verdict toàn văn bản.

## Nội dung dài, context và applicability

`seven-source-previews-001`:25 full records (20 DOCX,4 TT35,1 TT38),50 encoder
views, token tối đa248,5 unknown được giữ nguyên,0 bị truncate. Unknown không
được mặc định là lỗi nguồn/encoding. Chỉ Điểm b TT38 trong nhóm này có proposal
included được chọn; các long record khác chưa tự vào membership.

8 Điểm/Khoản lá Điều34 TT35 dùng nguyên văn/citation/ancestry và ID/hash giống
preview Part/Chapter đã rebind. Nguyên nhân source-only là selection/dependency,
không phải không có text. Cả Điều34 và Khoản cha giữ own text riêng. A34K2a/b có
5 subtree hồ sơ/sát hạch bắt buộc và mẫu XXVI qua A29K3b; tất cả8 target có thêm
A66K1/A67 và Luật36 A89K3 để đọc chuyển tiếp. Không chép chúng vào encoder text.

Đã đọc căn cứ: TT35 A66K1 ghi hiệu lực01/01/2025; A67 bảo lưu kết quả một số kỳ
sát hạch trước ngày hiệu lực và dẫn Luật36 A89K3. TT38 A12 ghi ngày hiệu lực,
văn bản thay thế và quy tắc dẫn chiếu. TT51 Công báo trang1 ghi01/01/2025 và thay
TT54/2019. Đây là quan sát nguồn, **chưa phải kết luận mọi target active**. Chưa
tra cứu hoàn chỉnh mọi sửa đổi/ngoại lệ lịch sử toàn bảy văn bản; applicability
giữ pending. Thời điểm tải/copy không dùng làm ngày hiệu lực hoặc retrieved_at
lịch sử của DOCX. Không nạp official corpus/assessment giả để thỏa schema DDD.

## QCVN: phạm vi đọc và OCR

Đã đối chiếu metadata HTML Công báo và5 PDF nối tiếp, số/ngày TT51, QCVN
41:2024/BGTVT; không nối edition425 với bản403. Receipt trong
`seven-source-completion-001/evidence/` có URL/hash/thời điểm truy cập thật.
Chọn nguồn mới không xác nhận hiệu lực/nội dung toàn bộ.

Reader/layout chạy425 trang; agent chỉ đọc rà các ảnh được ghi cụ thể trong
`visual/` và calibration, không gọi render425 trang là đọc rà425 trang. Hai mẫu
đơn TT35 XI/XXVI được đọc cả text và ảnh trang34/138. Scan NĐ168 đã đối chiếu các
trang84–86, bảng Luật35 trang67 và vùng liền kề68. Các vùng khác giữ disposition.

OCR local: Tesseract5.5.3, vie tessdata_fast, scale3/OEM1/PSM3/thread1. Năm mẫu
calibration, bốn ảnh đối chiếu có ghi nhận: sai dấu;75 thànhT75;cm thànhem;
subscript/kích thước mất hoặc lẫn. Gate tự động tạo target **FAIL**; chỉ gate
lưu draft/boxes/offsets đạt.203 trang image-dependent được lưu draft riêng,
6.270 word confidence<80,0 word offset không khớp. Confidence không là accuracy;
chưa tính CER/WER, chưa hiệu đính cả203 trang, không đưa OCR draft vào candidate.
Không xóa NUL/U+FFFE của bản cũ, không OCR mù403 trang hoặc suy nghĩa biển báo.

Parser revision1.2 không gán text serial part mới vào annex đọc được cuối cùng.
Chưa đọc được đầy đủ heading M/N/O/P từ reader; giữ940 dòng ở disposition cần
rà ảnh. Quan sát `48.1.1` dưới Điều49 ở Công báo part1 PDF68/in69 đã xem ảnh:
nguồn in đúng `48.1.1`; không tự sửa thành49.1.1. Ba subtree được chọn không
phụ thuộc vùng này. Một lỗi số và ranh giới annex không được che bằng số unit.

## Kiểm chứng đã chạy

- Rebuild candidate/validate: exit0,146 member, đúng types/bindings/pending gates.
- Portable005: validate và5 read (A34K2a, rain, QCVN, form, table), exit0.
  Bản006: validate/read QCVN trong bản sao mới, exit0; runtime và toàn membership/
  target/context/form payload bằng005. Python isolated, audit gate chặn đọc repo
  ngoài bundle. Cùng máy Windows/Python3.11.9, chưa phải thử OS/máy khác.
- Negative integration:8 ca bị từ chối đúng lý do sau reseal checksum ngoài:
  pending scope, sai type/location, giả human review, thiếu dossier, thiếu form,
  thiếu Điểm a rain, thiếu transition, thiếu capability. Fixture riêng, không nhập.
-167 tests hồi quy đã chạy, exit0,7 skip opt-in; bộ focused mới nhất được chạy
  riêng sau các thay đổi, xem log cuối. Không cộng các lần chạy trùng thành số
  kiểm thử hoặc quality claim. Import module có audit chặn write/network/process;
  missing input không tạo output; run ngoài staging/sealed bị từ chối; resume
  được thử cả sau interruption serialization, giữ bytes cũ.
- Reader/cache/hash:248 TT35 +15 TT38 +425 Công báo QCVN và thêm111+69 comparison.
  ND HTML toàn field/spans roundtrip; đủ55 root Điều, không nhân Điều trích sửa đổi.
  Graph002 legacy và003 hiện hành replay đúng nội dung/IDs.16 focused tests cuối
  kiểm ranh giới annex, source page/bbox, form labels và identity/budget.
- Preservation baseline2.022 file: không sai lệch artifact bảo vệ. Các thay đổi
  AGENTS/README/STATUS/ingestion được báo riêng là tài liệu được phép cập nhật.
  Dataset3077, draft3082/v3, index/evaluation/qrels/ZIP giữ nguyên.
- Dependency dry-run `pip install --dry-run --no-index -r requirements-ingestion.txt`
  exit0 trong venv hiện hữu. Không tuyên bố đã cài môi trường sạch hoặc inference.

Lần gọi test Stage6 đầu dùng sai import path cho helper đã có; đã chạy lại bằng
discover và suite cuối có `tests/` trên sys.path. Lần portable đầu thiếu UTF-8
stdout trên Windows đã được sửa bằng `-X utf8`. Một negative-copy hỏng ở staging
được discovery ghi riêng, không làm admission hoặc bỏ integrity check bắt buộc.
Các logs lỗi trước vẫn giữ, không sửa thành lịch sử pass.

## Code và tài liệu thay đổi

- `src/full_ingestion.py`: một CLI nối reader/graph/preview/ledger/packaging;
  guard staging, input preflight và resume không ghi đè artifact đã có.
- `full_source.py`, `ocr_pages.py`: cache trang/trace, measured cells/images,
  OCR drafts có config/bbox/confidence/offsets; không thay reader output âm thầm.
- `full_graph.py`, `qcvn_graph.py`: HTML graph NĐ168 và graph decimal/region QCVN;
  dùng grammar/normalizer hiện có, output locator HTML/PDF thật.
- `source_regions.py`, `completion_repairs.py`: ô/bảng/phụ lục/form và đối chiếu
  nguồn; không biến chúng thành cấp pháp lý giả hoặc sửa XML/offset cũ.
- `full_preview.py`, `encoder_views.py`, `completion_records.py`: rebind ancestry,
  long views, bound table impact, scope proposals hẹp và layout hai mẫu.
- `completion_dataset.py`, `seven_dataset_portable.py`: membership, component/
  mounts, source trace identity, finite dependencies, portable validator/read.
- `completion_ledger.py`: inventory/aliases/coverage/backlog/candidate binding;
  tái dùng URL scalar validator, gộp source/parser cùng locator, không chọn latest.
- `config/seven_source_completion.v1.json`, `requirements-ingestion.txt`, tests
  và các tài liệu mới/STATUS/ingestion/README để chạy lại và chỉ đúng giới hạn.
- `.gitattributes` giữ LF ở13 module ingestion mới có byte hash; không áp lên
  code/raw/artifact lịch sử và không chạy renormalize.

Chưa sửa parser/chunker prototype, DDD SQL, model/tokenizer/preprocessing,
retrieval engine, ứng dụng. Chưa inference/embedding/index hoặc yêu cầu chuyển bản.

## Công việc còn lại và cách tiếp tục

Chưa đủ điều kiện gọi ingestion toàn bảy nguồn hoàn tất. Cụ thể:

1. Agent tiếp tục8 owner bảng TT35, header/row/điều kiện và annex/form chưa được
   diễn giải; hiện mới có physical proof, không tự coi text đủ nghĩa.
2. Agent rà scope những unit/region chưa đọc, gắn BRD và dependency cụ thể;
   không dùng keyword/nhãn cha để lấp5.043 nhóm scope pending.
3. Hiệu đính/đọc ảnh QCVN theo vùng, nhất là số/ký hiệu/annex boundaries;
   automatic OCR target gate chưa đạt, không mở rộng trust từ ba subtree.
4. Rà source edition và applicability tại snapshot bằng evidence lịch sử còn
   thiếu; giữ pending, không yêu cầu human review như cổng mới để tiếp tục preview.
5. Khi form/encoder-view thực sự tích hợp retrieval cần capability/projection
   phù hợp và evaluation riêng. Lượt này không build index hoặc chuyển dataset.

[Lệnh replay/resume/validate](../handoff/Seven_Source_Replay.md). Checkpoint đang
tiếp tục ở `staging/seven-source-completion-001/checkpoint.json`; không làm lại
425 trang extraction/OCR draft/nhánh A16 khi tiếp tục các nhóm chưa xử lý.
