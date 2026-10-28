# Phiên1 — hiệu chỉnh NĐ168 và đánh giá DOC TT51/QCVN

Ngày28/10/2026. Snapshot **2025-01-01**. **SCOPED_CORRECTION_PASS /
DOC_DIAGNOSTICS_COMPLETE / FULL_SOURCE_REVIEW_PENDING**.

Đã làm trong repository, không chỉ lập kế hoạch. Đầu phiên HEAD
`e5c3665bf600f5f3d37cc0f588bf4f65a546ebaa`, Git sạch. Không stage/commit/push.
Không thay raw, schema DDD/parser cũ, dataset/index/evaluation/qrels/ZIP hoặc app.
Không xử lý tám bảng TT35, tạo dataset, embedding/inference. Origin=agent_review;
human reviewer events0; source/edition/scope/applicability chưa được phê duyệt.

## Đầu ra chính và phạm vi

| Đầu ra | Vị trí |
|---|---|
| NĐ168 hiệu chỉnh + registration/extraction/graph + crosswalk | `staging/nd168-docx-corrected-002/` |
| Replay NĐ168 | `staging/nd168-docx-corrected-003/` |
| HTML/receipt Công báo mới,5DOC/receipt, tool, ảnh và so sánh mẫu | `staging/source-revision-session1-001/` |
| Full DOC diagnostic extraction, inventory5file, manifest | `staging/qcvn-doc-assessment-003/` |
| Replay DOC diagnostic extraction | `staging/qcvn-doc-assessment-004/` |
| Kiểm graph/spans, đối chiếu HTML toàn cây, sequences/references, preservation/replay | `staging/source-revision-checks-002/` |

Đã đọc AGENTS, STATUS, ingestion/replay guide, Stage2–4 contract, báo cáo hoàn
thiện bảy nguồn, raw-readiness review/checklist, ledger009 và code thực tế.
Không coi các báo cáo là bằng chứng thay code/file. Input raw-readiness:
`staging/raw-source-readiness-review-20261028-001/`; PDF/ảnh và graph trước vẫn
giữ nguyên. Không chọn run mới nhất theo tên. Các run thử/lỗi trước bản chính
vẫn lưu: DOC assessment001 lỗi relative/absolute ref,002 trước hardening URL;
corrected001 trước bổ sung crosswalk. Không dùng chúng thay các run chính ở bảng.

## NĐ168 — năm chỗ đã sửa trong bản dẫn xuất

Đã mở lại ảnh PDF41/85/86, đọc marker/nội dung và kiểm SHA ảnh/PDF. Input là
DOCX raw có SHA `d6f009d30ba828b51e0a1a7b2dcb702c171bcddf030bac83afca1a22ece2588a`.
PDF chính thức SHA `7bb11b939d162499ab404aa41a940cce05dbf071d9cbae7a8898b00d4b4a48bd`.
Không tải lại PDF111tr scan đã có từ16/10; URL/time thật nằm trong bằng chứng cũ.

| Vị trí | Before → after | XML paragraph / PDF |
|---|---|---|
| Điều16K2, “Điều khiển xe gắn biển số…” | `đ)` → `d)` | p518 /41 |
| Điều16K2đ, đoạn về chi nhánh ngân hàng | `ngán hàng` → `ngân hàng`; giữ `đ)` | p519 /41 |
| Điều39K9, “Trung tâm sát hạch… điểm k khoản5, khoản7…” | `đ)` → `d)` | p1038 /85 |
| Điều40K3, “Sử dụng thiết bị, dụng cụ…” | `đ)` → `d)` | p1057 /86 |
| Điều40K3, “Lưu trữ hồ sơ… dữ liệu chứng nhận…” | `c)` → `e)` | p1059 /86 |

Giữ nguyên p1058 “đ) Có từ02lượt đăng kiểm viên…” và mọi nội dung khác. Đã chọn
theo Điều/Khoản + toàn bộ before, không Replace All hoặc chỉ dùng index.
Nguyên văn đầy đủ before/after, hash ảnh và locators nằm trong `corrections.jsonl`.
Ảnh nguồn: `staging/blocked-source-review-002/evidence_pages/ND168-page-041.png`,
`ND168-page-085.png`, `ND168-page-086.png`.

File mới: `sources/168.2024.NĐ-CP.docx`,93.565byte, SHA
`33b9c76fa3c03a7ca562d238797f308f259141fee302dbcf15d0bb736710d721`.
22ZIP member ngoài document.xml giữ nguyên payload;1.368paragraph chính và
tags/properties/XML ngoài w:t giữ nguyên byte. CRC hợp lệ, đúng5paragraph đổi.
ZIP được nén lại nên không đòi container ngoài5substring byte-identical.
**Chưa render DOCX**: không có Word/LibreOffice executable hoạt động; registry
Word.Application cũ không có LocalServer32. Không coi kiểm XML là kiểm layout.

Adapter gọi pipeline Stage2→3→4 hiện có, không sửa grammar. File mới có UUID
`646fcd83-5dc9-583c-bc5b-254d04cd7aa8`; extraction mới
`e_65fb69fbceb5886b79ddc51b3e45426cb7388eaed8698fdcdf19840a0ca51eb3`.
Các locators/offsets/slice hash được tính lại trên extraction mới. Evidence về
ngày tải DOCX legacy vẫn null; PDF download không biến thành DOCX download.

Kết quả: **1.309unit /1.351span /0parser issue /4source warnings /2bảng**.
Bốn warning cũ liên quan visual quốc hiệu/header PAGE/ancillary vẫn còn;
không xóa chỉ để đạt. Validator graph/extraction/FK/identity/roundtrip đạt.
Sequences: Điều16K2 `a,b,c,d,đ`; Điều39K9 `a,b,c,d`; Điều40K3 `a,b,c,d,đ,e`.
15Điểm thuộc ba Khoản khớp HTML sau chuẩn hóa khoảng trắng để so sánh.
Tham chiếu Điều16K4b “điểm c, điểm đ khoản2” còn nguyên và truy được hai đích;
không tuyên bố đã resolve mọi legal reference toàn văn.

Crosswalk: **1.303unit giữ ID,1unit đổi ID,5unit khôi phục từ vùng cách ly**.
Unit đổi là A39K9đ→d, đổi designation/canonical_path/citation_path/text_original.
Năm unit trước chưa có ID: A16K2d/đ và A40K3d/đ/e, ghi old=null + locator thật.
Không ép giữ ID hoặc tạo unit lịch sử giả. `span_crosswalk.jsonl` ghi binding
extraction mới; số offsets có thể giống vì sửa không đổi độ dài code point,
nhưng vẫn là kết quả replay, không sao binding cũ.

## Đối chiếu HTML và đề xuất nhánh cho lần build sau

So toàn1.309canonical paths với `staging/nd168-html-full-002/`; đủ1.309match.
Trong2.618field title/text:2.283exact,249chỉ whitespace,**86khác ngoài whitespace**.
Đây không phải86lỗi luật đã xác minh. Có khác quote typography/đường gạch ở root,
và ví dụ đáng rà riêng A6K4a: DOCX “đã thu phí” /HTML “để thu phí”. Không sửa thêm
ngoài năm chỗ. Báo cáo full field diff giữ toàn văn hai phía trong checks002.

**Đề xuất** dùng nhánh HTML chính thức đã capture làm một nguồn text cho lần build
tiếp, PDF scan làm đối chiếu; DOCX hiệu chỉnh là nhánh audit/backup có crosswalk.
Không nhập đồng thời hai nhánh như hai căn cứ. Lựa chọn này chưa phải nhận định
verified/edition tại snapshot;86field diff và các vùng sửa đổi/trích dẫn chưa parse
vẫn cần disposition riêng. Không thay dataset hoặc ép unit IDs giữa hai nguồn.

## TT51 — nguồn DOC thực tế

Đã truy cập/capture đúng [trang53152 Công báo](https://congbao.chinhphu.vn/van-ban/thong-tu-so-51-2024-tt-bgtvt-43387/53152.htm).
Trang ghi TT51/2024/TT-BGTVT ban hành15/11/2024, hiệu lực chung01/01/2025 và
năm cặp số Công báo. Đây là nhận diện nguồn/quan sát ngày chung, không xác nhận
applicability từng vùng. Tái sử dụng cả5PDF đã capture24/10, chỉ tải5DOC thiếu
vào coordinator001/doc-captures. Mỗi receipt giữ URL/final URL/time/SHA/size/magic.

| Part / Công báo | DOC byte | Code point NFC/LF | `[pic]` | DocBook table quan sát |
|---|---:|---:|---:|---:|
|1 /1359+1360|5.652.480|187.145|132|21|
|2 /1361+1362|17.645.568|128.662|341|3|
|3 /1363+1364|18.235.392|39.387|114|3|
|4 /1365+1366|23.281.664|1.888|95|1|
|5 /1367+1368|20.725.760|534|45|0|

Tổng85.540.864byte,357.616code point diagnostic,727placeholder. Không cộng
placeholder hoặc DocBook table thành số hình/bảng pháp lý. Cả5OLE magic đúng,
text UTF-8 strict đọc được;0NUL/U+FFFE/U+FFFD/PUA trong output plain text.
**Không đồng nghĩa toàn DOC đủ nội dung**: phần4/5 chủ yếu là hình, bảng/mã biển
không hiện trong text. Đã trích toàn file, chỉ đọc rà các mẫu được nêu dưới.

Đã xác nhận order/continuation theo body heading/footer của5DOC và PDF:
part1 TT51/QCVN→B.17/P.117;part2 tiếp B.18…→G;part3 tiếp G→K/M;
part4 tiếp M→N/O/P;part5 tiếp P. DOC1–4 có thêm mục lục issue, không phải phần
luật mới. Không suy số trang DOC từ metadata. Các metadata nhúng còn title2007,
num_pages=1; không dùng chúng làm bằng chứng edition hoặc pagination.

Tool Antiword0.37 từ MSYS2, executable/mapping SHA trong manifest; chạy cả text
và DocBook trên5file. Không convert DOC→DOCX. Tool đọc text, không chứng minh giữ
bố cục. Dòng/offset diagnostic không là DOC native page hoặc PDF span.
Inventory mới `qcvn-doc-assessment-003/inventory.jsonl` có5UUID theo law+SHA,
URL/receipt/time thật, part/source-set/paired-PDF. Chưa nạp DOC vào schema DDD.

## Mẫu so sánh chi tiết — không áp cùng số trang giữa hai edition

`qcvn_comparison.jsonl` giữ16mẫu, source hashes, refs, quotes/offset diagnostic
khi có;9mẫu không có anchor text nên offsets=null. Ảnh PDF được render riêng,
proof giữ page/hash/tool/scale. Đã mở ảnh, không chỉ đọc OCR/cache.

| Vùng | Mapping theo nội dung | Kết luận mẫu DOC /PDF |
|---|---|---|
| PDFgốc7: Điều4/4.1–4.2 | Công báo part1 PDF8/in9 | DOC đọc được, khớp câu Công báo; bản403 ghi “có bố trí…ở cùng”, Công báo/DOC “có, bố trí…cùng ở”. Giữ khác biệt, không tự đồng nhất edition |
| PDFgốc214: M.1,P101/P102/P103a | part3 PDF44/in45 | DOC plain thiếu heading/cells; ảnh OLE đã mở có đúng sơ đồ và z(mm)140/126/87,5/70 như mẫu Công báo. Vẫn là ảnh, không có native cell proof |
| PDFgốc300: Đường tránh/HÒA BÌNH | part4 PDF36/in37 | Reader DOC không trả nhãn/hình; ảnh Công báo ghi I.416. Phiên âm cũ ghi I.418; glyph bản403 mờ, giữ vấn đề marker chưa kết luận, không sửa raw. Mapping dựa caption/geometry, không dựa số trang |
| PDFgốc368: hình A–E | part5 PDF10/in11; bảng liền trước PDF9/in10 ↔gốc367 | DOC JPEG lấy được hình tương ứng; plain text không có. Phải đọc bảng11 “Nơi rửa xe”,đơn vịcm ở trang trước, không dùng hình A–E độc lập |

Đối chiếu text/table/image theo từng part:

- Part1: Điều16–17 PDF20/in21, số0,5/1,7/3,5m; bảng1/2 PDF15/in16 đối chiếu
  các giá trị700/100/50 và700/50/35/30, header/mm. DocBook có table diagnostic,
  chưa có native cell/span. Hình vẫn cần PDF; chưa xác minh ảnh DOC toàn phần1.
- Part2: C.14 W.214/C.15 W.215 ở PDF20/in21: text/caption đọc được, hình là
  placeholder. BảngG.1 PDF83/in84 đối chiếu30→120,80→245 và đơn vị; typography
  V85/subscript/hình G.7 chưa được bảo đảm bởi plain text.
- Part3: G.9.6/HìnhG.82 PDF30/in31: câu giữ75cm×120cm,110×170,170×275. K.1
  PDF37/in38: không lấy các số rời cuối DOC làm cells khi thiếu header/order.
  M.1 PDF44/in45 có ảnh nhúng tương ứng, nhưng không đọc được text bằng Antiword.
- Part4: N bắt đầu PDF75/in76;O PDF77/in78;P PDF81/in82, đã mở ảnh xác nhận
  heading. DOC text không phục hồi các heading này. Ảnh OLE mẫu N/CT.01..08 còn
  bảng, không chuyển thành native cells hoặc tự resolve49nhóm backlog annex.
- Part5: bảng11 PDF9/in10 và hình PDF10/in11 phụ thuộc nhau. P.24/IE.472a PDF40/in41
  có ảnh DOC màu xanh và bảng so với PDF grayscale; plain text không trả caption/
  subscript/table. Không suy ý nghĩa hoặc màu áp dụng toàn QCVN từ mẫu này.

Đã kiểm20PDF image streams:0khớp byte JPEG; không ép coi khác encoding là khác
nội dung. Khảo sát OLE Data ghi stream/byte-range/hash riêng và mở một số ảnh
được chọn. Nearest-thumbnail gợi nhầm (ví dụ mẫu Đường tránh ra ảnh EXIT, G.7 ra
ảnh làn bus); giữ trạng thái candidate, không dùng score làm bằng chứng. Một số
mẫu M.1/N/hình A–E/P.24 đã đối chiếu thị giác; không tuyên bố toàn ảnh đã khớp.
Không OCR lại toàn bộ hoặc xóa ký tự lỗi. Metadata/source/image diagnostics giữ
ở coordinator001, không dùng như extraction pháp lý chính thức.

## Kiểm chứng đã thực thi

- 62tests Stage2/3/4 + correction/DOC diagnostic: exit0. Log chuẩn
  `tests.clean.log`, `tests.result.json` trong coordinator001;7ca test mới nằm
  trong62, không cộng lặp. Log đầu bị PowerShell gói stderr thành ErrorRecord
  dù unittest ghiOK; đã chạy lại bằng subprocess và lưu returncode0 rõ ràng.
- `src.qcvn_doc_assessment validate` trên003: technical_valid=true,5part,
  native_DOC_layout_verified=false, release=false.
- Artifact check: graph/FK/ID/spans, finite source edits, sequences/reference,
  toàn cây HTML diff và preservation đạt. Replay5NĐ168payload +20DOCpayload
  giữ SHA; manifest time không đòi byte-identical.
- Baseline2.226file: không có thay đổi ngoài hai tài liệu hiện hành được phép
  cập nhật. Bao gồm raw, evidence, dataset/index/eval/qrels/ZIP và candidate cũ.
- `git diff --check` đã chạy; kết quả cuối/log nằm trong coordinator001.

## Chưa làm, blocker và đầu vào đề xuất cho phiên2

1. NĐ168: có bản hiệu chỉnh kỹ thuật, chưa render Word;86field khác HTML cần
   phân loại/đối chiếu riêng nếu dùng DOCX rộng hơn. Chọn một nhánh HTML cho build
   sau theo đề xuất, không tự chuyển dataset hoặc coi edition/applicability đạt.
2. QCVN text: ưu tiên PDF Công báo425tr hiện có source-page proof; DOC1–3 là
   nguồn đối chiếu text/table bổ sung, chưa thay reader/graph. DOC không tự sửa
   typo nguồn48.1.1 dưới Điều49 (ảnh part1 PDF68/in69 cũng in như vậy).
3. QCVN bảng/hình: PDF page/cell/image vẫn là proof chính; có thể dùng ảnh màu
   DOC theo từng vùng đã match, giữ native stream proof + PDF mapping. M/N/O/P
   vẫn cần reader/OCR/phiên âm hẹp và kiểm số/ký hiệu; không phải chỉ cài reader
   DOC là xong. Vùng I.416/I.418 cần đọc chắc marker trước khi tạo identity.
4. Chưa có DOC→DOCX/native DOC page/cell mapping, không render toàn5DOC hoặc
   đọc rà425tr. Chưa chạy trên máy/OS khác hoặc clean install toàn môi trường.
5. Phiên này chưa sửa8bảng TT35, tạo chunk/dataset/index/assessment; nguồn/scope/
   applicability và gate phát hành vẫn pending. Không mở phiên2 tự động.

## File Git thay đổi

Thêm2module `src/source_revision.py`, `src/qcvn_doc_assessment.py`; config
`nd168_docx_revision.v1.json`;2unit-test files và artifact checker
`tests/check_source_revision_artifacts.py`. Thêm contract, replay guide và báo
cáo này; cập nhật đầu STATUS/ingestion, giữ lịch sử. Artifact/raw/tool không stage.
Lệnh đầy đủ: [Source_Revision_Session1_Replay.md](../handoff/Source_Revision_Session1_Replay.md).
