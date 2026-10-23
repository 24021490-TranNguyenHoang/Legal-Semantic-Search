# Ứng viên TT38/TT35 và pilot QCVN — 2026-10-23

Snapshot2025-01-01. HEAD đầu phiên3faaf98946ac24ff5abbf2bdd38e53d1c8975ecb.
Đầu phiên có7 tracked modified và10 untracked từ ingestion trước; giữ snapshot
status/diff/hash tại `staging/circular-priority-audit-001/`. Không nhận các thay
đổi ingestion đó là thay đổi mới của phiên. Không stage/commit/push.

Contract/decision trước sửa code:
[Circular Priority v1.2](../design/Circular_Priority_Representation_v1.2.md).
Không sửa báo cáo hoàn thiện ingestion cũ. Trạng thái dưới đây là agent_review,
không reviewer decision; release_eligible=false.

## Run cuối và bảng từng ứng viên

`staging/circular-priority-006/manifest.json` bind đúng năm manifest:
seven-sources-export-006, tt38-tables-003, tt35-preview-005,
tt51-extraction-005, tt51-preview-003. TT38 dependency đọc từ tables/base:
base manifest SHA có trong manifest bảng và config extraction trong base,
không chọn run theo tên/latest. Upstream validators replay trước build mới.

`priority.jsonl` và `review.md` có46 dòng:8 TT38 text,9 hàng bảng,1 Điểm b,
25 TT35 text,3 TT51 supporting conditional. Mỗi dòng có unit/candidate ID,
law/source ID, own text, locator/spans, scope reason, dependency/context,
trạng thái và blocker. Không suy572 TT35 preview đều thuộc scope.

| Nhóm | Trước | Sau phiên này |
|---|---|---|
| TT38 text included | 8 chunk v1 | Giữ8 ID/content/proof, xuất lại tt38_text.* trong run mới |
| TT38 bảng | 9 tp_ preview chưa là DDD | 9 table-retrieval.v1 records có owner/cells/header/row/proof, đạt budget |
| TT38 A11K2b | 279 token | Giữ279, quarantine; toàn a+bảng3 là dependency, chưa có phép rút gọn an toàn |
| TT35 included | 25 target trên projection thưa | 25 chunk tái dựng trên graph có Part/Chapter,71–184 token,2 unknown |
| TT51 supporting | 3 chunk bản ban hành | Conditional: chưa có QCVN target cụ thể để dùng context; không biến thành target |

TT35 graph mới:783 nodes =1 document,7 Phần,9 Chương,67 Điều,217 Khoản,
482 Điểm. Parent/path/citation/ordinal theo vị trí nguồn; ChươngI ở các Phần
khác nhau có ID khác nhau. Title marker/name nguồn có spans riêng, own text
Điều/Khoản/Điểm giữ nguyên. Không còn dùng projection thưa làm graph đầy đủ;
tables/annex chưa hỗ trợ vẫn được bảo toàn, không tuyên bố toàn nguồn đã parse.

`unit_crosswalk.jsonl`:767 old units mapping sang graph mới,16 ancestors mới;
chỉ root giữ unit_id,766 ID đổi do parent/path/citation/ordinal. `chunk_crosswalk`
ghi25 cặp cũ/mới; ID đổi theo chunk.v1 vì unit/citation/context IDs, ba Điều lá
còn đổi chunk_policy_version sang leaf-article-part-ancestry.v1.
Không thay ID3077chunk đang phục vụ.

Bảng vẫn không phải nguyên văn chunk DDD: retrieval_id tr_ của biểu diễn dẫn
xuất; owner_unit_id thật, source_original tách derived_text/search. Rows/cells
và conditions gốc không đổi,9 records đạt137–168 token,unknown0. Điểm b279
không tự giảm budget hoặc bỏ dependency. Dataset adapter hiện hành chưa biết
record_type mới; đó là blocker downstream, không phải nguồn/table proof pass giả.

Đã đọc lại text_for_search/encoder_text của b: law_title/citation, title Điều,
lead Khoản, toàn điểm a, nguyên văn b và4 hàng bảng3. Không có hai field context
trùng hẳn để xóa an toàn; phần dưới60km/h trong a là điều kiện riêng, chưa có
policy chứng minh bỏ nó vẫn đủ nghĩa. Đã xem lại PDF7/trang in27: lead Khoản2
thực sự kết thúc ở chữ “đường” như extraction; không tự thêm chữ “bộ” hoặc dấu
hai chấm để sửa câu nguồn. Ảnh nằm audit/tt38-page7.png.

## Dependency có mục tiêu và applicability

`targeted_dependencies.jsonl` giữ nguyên văn/spans nhóm Điều14/15/28/29/32/36/
44/45/66/67 và bốn trang annex XI/XII/XXIII/XXVI (PDF34/35/127/138).
Phụ lụcXXVI được phát hiện thêm từ A29K3b/A32K2; đã đọc text và ảnh PDF138:
mẫu đơn đổi/cấp lại GPLX, proposed supporting, chưa form-chunk.
XI/XII/XXIII tái dùng bằng chứng đã đọc ở ingestion trước; không coi mọi
annex là excluded. Chưa đọc toàn179 trang hoặc463 preview pending.

Các dependency chưa ghép tự động, cần xét theo nhu cầu query/context:

- A14K3→A15K1; A15K2a→A15K1; A29K3a→A15K1b: nội dung có trong cây,
  giữ nguyên câu dẫn chiếu và bản dependency đọc được, chưa tự mở rộng context.
- A15K1a→XI; A15K2c→XII; A28K2→XXIII; A29K3b/A32K2→XXVI:
  có trang nguồn cụ thể, chưa có biểu diễn form dùng tìm kiếm đầy đủ.
- A28K1→Luật36 Điều59; A67→Luật36 Điều89K3; A32K6b/A45→điều ước:
  chưa hoàn tất đối chiếu căn cứ ngoài nhánh TT35. Không suy câu trả lời đầy
  đủ chỉ từ chunk kỹ thuật. Các reference extractor trong priority chỉ là
  quan sát, không phải resolver; kể cả dẫn chiếu xuống dòng có thể chưa được bắt đủ.

Đã đọc TT35 Điều66 và67: ngày chung01-01-2025, danh sách văn bản bãi bỏ,
quy định bảo lưu kết quả sát hạch trước ngày hiệu lực. Với A67, cần phân biệt
ngày sát hạch cũ, phần đã đạt và hạng GPLX theo Luật36, không dùng nhãn active
đồng loạt. TT38 A12K1 ghi ngày chung/thay thế31/2019 và Điều15 TT06/2023;
A12K2 yêu cầu áp dụng văn bản sửa đổi/thay thế khi dẫn chiếu thay đổi.

Kết luận agent: nội dung ngày chung và chuyển tiếp được bảo toàn, tin cậy cao
về việc các câu có trong extraction hiện có; **applicability từng đối tượng
vẫn pending** vì chưa chứng minh đầy đủ lịch sử sửa đổi/điều ước và các điều kiện
cá nhân tại snapshot. Không thêm ngày tải lịch sử hoặc suy full-file verified.
PDF TT35 mang số/ngày15-11-2024 và annex liên kết cùng văn bản; TT38 Công báo
đúng attachment đã capture. Đây là nhận diện edition quan sát được, không
xác nhận remote hash cho toàn file TT35 legacy.

Tra cứu bổ sung cổng Chính phủ/CSDLQG: search thấy ngày chung; mở trang lịch
sử TT38 bịHTTP403. Capture trực tiếp từ môi trường Python bịWinError10013
(socket restriction), lỗi/URL/thời điểm thật ở audit official-captures.json.
Không tạo HTML/hash giả hoặc dùng search snippet làm bằng chứng lịch sử đầy
đủ. Tái dùng capture cũ trong data/source_evidence/circulars-2024. Không có
capture byte mới thành công trong phiên; giới hạn này không chặn preview.

## Blocked / quá budget / unknown

13 source/context blocked và4 overbudget TT35 là hai nhóm riêng, giữ trong
tt35_backlog.jsonl và tt35_original_quarantine.jsonl, có locator/spans/unit_id.
Đối chiếu binding cho thấy **0 trong25 ưu tiên thuộc17 ca này**; không tự sửa
ngoài phạm vi.13 ca: A46K2,A6K1,A7K1,A8K1a–d,A21K4a–e (gồmđ).
4 ca: A22K1c273,A43K2b273,A43K1b296,A16K3b287. Không truncate hoặc tăng budget.

`audit/unknown_comparison.json` lưu source_original/search/encoder_text,
token pieces/positions trước và sau cho A15K1b/A15K2b. Mỗi target vẫn1 unknown
ở lexeme segmented chứng_thực_từ (BPE fragment chứng_th@@); NFC source/spans
không đổi. Chấp nhận kỹ thuật **có cảnh báo tokenizer** cho preview, chưa có
bằng chứng lỗi nguồn và không đổi vocabulary/preprocessing.25 ưu tiên tổng
unknown2, không dùng số unknown toàn572preview để áp cho nhóm này.

## QCVN pilot bốn trang

Run `staging/qcvn-pilot-002/` có source manifest/hash, PDFium5.14.0/render1.5,
PNG, reader text giữ lỗi, transcription config, UTF8/NFC/LF mới và offsets.
PDF page và số trang in đều7/214/300/368. Locator full-page bbox đo thật;
không tuyên bố bbox ký tự/crop chưa đo. Agent đã xem bốn ảnh của nguồn.

| Trang | Nguồn → kết quả | Giới hạn |
|---|---|---|
| 7 | Font diagnostic CMap CID→U+0000 đã lưu; PDFium U+FFFE. Phiên âm hẹp Điều4/4.1/4.1.1–6 từ ảnh | Chưa tự khôi phục font;4.2/Điều5 chưa phiên âm; không suy U+FFFE luôn là dấu cách |
| 214 | Reader rỗng; phiên âm nhãn Phụ lụcM/M.1/P.101/P.102/P.103a | Bảng kích thước, đơn vị, nét vẽ vẫn phụ thuộc hình; không suy nghĩa biển |
| 300 | Reader rỗng; phiên âm nhãn Phụ lụcM/I.418 Đường tránh | Mũi tên, kích thước, bảng loại đường và hình chưa chuyển thành quy định text |
| 368 | Reader chỉ số368; phiên âm nhãn kích thước A/B/C/D/E theo danh sách | Không có caption/mã biển nhìn thấy; chưa xác định liên kết trang kề, không đoán ý nghĩa |

Không có Tesseract/pdftotext hoặc module OCR/PyMuPDF/pypdf trong môi trường
đã kiểm. Không cài dịch vụ/model lớn; **không chạy OCR**. Visual transcription
là agent review có phạm vi, không human review và không sửa reader/raw.
Offsets mới chỉ trên từng file transcription, không thay offsets extraction
005. Phiên âm là đoạn chọn, không phải text hoàn chỉnh của trang.

Đủ bằng chứng cho cơ chế lưu pilot hẹp/provenance, **chưa đủ để mở rộng tự
động giải mã/OCR toàn QCVN**.0 unit/chunk QCVN mới. Các hình/bảng chưa có
diễn giải đầy đủ vẫn là dependency/blocker, không đưa text nhãn vào target.

## Kiểm tra và lệnh chạy

```powershell
$py = '.\.venv-stage1\Scripts\python.exe'
& $py -X utf8 -B -m src.tt38_preview priority --config config/circular_priority.v1.2.json --run-dir staging/circular-priority-NEW
& $py -X utf8 -B -m src.tt38_preview validate-priority --manifest staging/circular-priority-NEW/manifest.json
& $py -X utf8 -B -m src.tt38_preview qcvn-pilot --manifest staging/tt51-extraction-005/manifest.json --run-dir staging/qcvn-pilot-NEW
& $py -X utf8 -B -m src.tt38_preview validate-qcvn-pilot --manifest staging/qcvn-pilot-NEW/manifest.json
& $py -X utf8 -B -m unittest tests.test_circular_priority tests.test_circular_completion tests.test_tt38_layout tests.test_stage6_points.PointBuilderTests tests.test_leaf_articles.LeafArticleTests
git diff --check
```

Run mới phải chưa tồn tại. Build gọi validate/replay; upstream snapshots cũ
vẫn dùng validators cũ nguyên byte.46 tests phù hợp đạt; source roundtrip,
ID/different-Part, missing spans, sai hash/parent có kiểm thử. Không dùng số
test để xác nhận chất lượng pháp lý/retrieval. Audit lưu kết quả negative
cases và kiểm baseline sau phiên; chỉ tính ca thực sự từ chối do replay nội
dung, không tính lỗi code hash từ run trung gian.

Kết quả chốt:46 tests đạt3,617s;3 ca sửa nội dung rồi seal lại trên bản005
(sai cha Phần, xóa cells/header, cho candidate279 token thành pass) bị từ chối
đúng lỗi replay. Bản006 chỉ bổ sung guard snapshot/corpus: graph/spans/chunks/
contexts/encoder/table records byte-identical với005; thử snapshot sai trên
bản sao006 bị từ chối.126 source proof slices của chunk/context được kiểm
độc lập tại đường dẫn tương đối run006. Audit có tampering.final.json,
snapshot-negative.json và final-checks.json.

Baseline539 file:4 file có sửa bổ sung được phép trong phiên (AGENTS, STATUS,
ingestion guide, CLI);535 file còn lại nguyên hash, không có thay đổi bất ngờ.
Bao gồm raw/capture cũ,5 bundle đầu vào, dataset/index/evaluation/ZIP/draft
và code/config ingestion có trước. Không gọi diff tổng của repository là
diff riêng phiên này. Git diff --check đạt, index Git rỗng.

SHA-256 manifest cuối:

- circular-priority-006: b21366fa0c8e22b4c27a29945f0eeab7b254b1193aa7f041b02988ad92b4c20b.
- qcvn-pilot-002: be031b9600e1c355ee16e6a5c6e1865e9856a43750f7f7d1d6822021f929bc44.

Các run priority001–005/pilot001 giữ làm lịch sử thử implementation, không
chọn làm bản hiện hành. Không tuyên bố cài sạch, máy/OS khác hoặc nguồn đã
verified từ các kiểm tra trên. Chưa có đánh giá retrieval trong phiên này.

## Phạm vi thay đổi và điểm dừng

Thêm circular_priority.py và qcvn_pilot.py; thêm routes trong CLI cũ,
config/schema pending/contract/test hẹp. Không sửa parser/chunker/encoder cũ
hoặc schema DDD chính thức. Các thay đổi ingestion có sẵn giữ nguyên; STATUS
và guide cập nhật riêng, không sửa báo cáo lịch sử.

Đã có33 text candidate đạt kỹ thuật (8TT38+25TT35) và9 table retrieval records
đạt budget, một reference candidate quarantine;3 TT51 supporting conditional.
Tất cả scope là proposed, nguồn/edition/applicability pending. Dataset adapter
v1 chưa hỗ trợ Part và table records mới. **Chưa đủ để đóng gói draft mở rộng
bằng adapter hiện hành**; có thể mở phiên phát triển adapter revision và rà
dependency/applicability hẹp, không cần rà toàn463preview để tiếp tục kỹ thuật.
Chưa tạo dataset/index/embedding hoặc yêu cầu nhóm chuyển bản.
