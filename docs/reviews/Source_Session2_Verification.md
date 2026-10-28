# Phiên 2 — NĐ168, tám owner bảng TT35 và lô vùng QCVN

28/10/2026; snapshot **2025-01-01**. Origin **agent_review**, human events **0**,
release_eligible **false**. Không tạo dataset/index, embedding hoặc đổi ứng dụng.

Đầu phiên HEAD `be7f661109a77dc6c0fb22d72bd6d48ed6ecfc34`, Git sạch, khác HEAD
đầu phiên 1. Phiên này chỉ thêm module/config/test/contract/report; cập nhật đầu
STATUS và ingestion, giữ lịch sử. Không stage/commit/push. Raw, evidence/run cũ,
dataset/index/evaluation/qrels/ZIP không được sửa. Baseline kiểm tra **2.827 file**.

Đã đọc AGENTS, STATUS, ingestion, báo cáo/replay phiên 1, backlog handoff bảy
nguồn, contract completion/representation/source proof/encoder và code thực tế.
Số liệu dưới đây lấy từ output đã chạy, không dùng baseline để ép kết quả.

## Mở kết quả

| Hồ sơ | Artifact chính | Replay |
|---|---|---|
| 86 field, hai giá trị đầy đủ, locator/offset/evidence | `staging/nd168-field-review-003/fields.review.csv`, `.jsonl` | `nd168-field-review-004` |
| DOCX dẫn xuất mới, registration/extraction/graph/crosswalk | `staging/nd168-docx-session2-001/` | `nd168-docx-session2-002` |
| Tám bảng owner, whole consumer read, encoder views | `staging/tt35-owner-tables-002/tables_preview.md`, `tables.preview.jsonl`, `tr_*.read.json` | `tt35-owner-tables-003` |
| Từng ca trước–sau, token, ID, trạng thái | `staging/source-session2-checks-002/tt35.before_after.md`, `.csv`, `.jsonl` | sinh lại bằng artifact checker |
| QCVN lô hẹp, đính chính, backlog còn lại | `staging/qcvn-region-recovery-004/review.md`, `regions.pending.jsonl`, `source_differences.json` | `qcvn-region-recovery-005` |
| Ảnh mới, OCR nhãn riêng, baseline, log và downstream trace | `staging/source-session2-001/` | cùng input đã seal; không cần tải lại |
| Kiểm chứng tổng hợp, negative cases, replay | `staging/source-session2-checks-002/validation_report.json`, `negative_checks.jsonl` | lệnh trong handoff |

Các run thử nghiệm thấp hơn trong cùng phiên được giữ nguyên; bảng này chỉ rõ
run bàn giao, không áp dụng quy tắc “chọn run mới nhất”. Không coi staging là
nội dung được Git quản lý; cần chuyển kèm các dependency thật nếu bàn giao máy khác.

## NĐ168: 86 trường khác không phải 86 lỗi

Input thực tế: `source-revision-checks-002/docx_html.full_comparison.jsonl`,
đối sánh DOCX đã sửa phiên 1 với HTML full-002. Có **1.309 canonical_path**,
**2.618 field**: 2.283 exact, 249 chỉ whitespace, 86 khác ngoài whitespace.
Module mới kiểm ID/content/spans/FK, canonical_path duy nhất, loại unit,
designation, field và hai giá trị phải trùng đúng bản comparison đã bind.
Không dùng tương đồng chuỗi để tự gán hai căn cứ pháp lý thành một.

| Phân loại primary | Field | Kết luận kỹ thuật |
|---|---:|---|
| Biểu diễn/đối sánh | 67 | 64 quote/dấu thanh, 2 ngắt từ có gạch nối, 1 hoa/thường. Các path đã match; không sửa payload chỉ để giống HTML. |
| Khác nội dung | 18 | Đọc ảnh PDF đúng vùng; 20 edit trong 18 paragraph DOCX được sửa trong bản dẫn xuất mới. |
| Lỗi extraction → graph boundary HTML | 1 | Widget liên kết tin liên quan bị gán vào text Điều 55. Projection mới loại đúng vùng widget, vẫn giữ normalized HTML và offsets gốc. |
| Chưa xác định primary category | 0 | Không đồng nghĩa toàn văn/edition/applicability đã verified; 67 khác biệt biểu diễn vẫn được giữ và trạng thái pháp lý vẫn pending. |

Một field có thể chứa khác biệt phụ về typography; primary category không che
hai nguyên văn. CSV/JSONL giữ **đủ cả hai giá trị**, unit IDs, spans, ảnh và việc
còn thiếu, không thay bằng các đoạn trích bên dưới.

PDF đối chiếu: `staging/bm25-baseline-v1-001/dataset/evidence/captures/05/snapshot.pdf`,
111 trang, SHA `7bb11b939d162499ab404aa41a940cce05dbf071d9cbae7a8898b00d4b4a48bd`.
URL và lần capture thật **2026-10-16T14:33:07.439116Z** có trong
`dataset/evidence/catalog.jsonl` của cùng bundle; phiên này reuse, không tải lại.
Ảnh mới `source-session2-001/visual/ND-NNN.png`; contact sheets chỉ để tìm trang,
không được tính thành đọc rà toàn 111 trang.

| Vị trí | DOCX trước → sau theo ảnh | Trang PDF |
|---|---|---:|
| Căn cứ văn bản | 15 tháng 11 năm 2020 → 13 tháng 11 năm 2020 | 1 |
| A6K4a | điều kiện đã thu phí → điều kiện để thu phí | 10 |
| A8K7 | Phạt liền → Phạt tiền | 25 |
| A12K9 | vỉa hè, → vỉa hè. | 32 |
| A12K15 | giấy phép lát xe → giấy phép lái xe | 33 |
| A13 title | tương tư → tương tự | 33 |
| A13K2a | điểm d khoản 4 Điều 26 → điểm đ khoản 4 Điều 26 | 33 |
| A13K3a | được lấp theo → được lắp theo | 34 |
| A13K5b | hệ thống hàm → hệ thống hãm | 35 |
| A13K10b | ngàn hàng → ngân hàng; không: do → không do | 36 |
| A14K5b | quy định lại điểm → quy định tại điểm | 38 |
| A20 title | trật trị, → trật tự, | 46 |
| A32K18đ | (nếu có), → (nếu có). | 73 |
| A34K3c | khép giới hạn → khổ giới hạn | 77 |
| A39K4b | giấy phép đào tạo lái xe: → giấy phép đào tạo lái xe; | 82 |
| A39K5e | xe trong tỉnh → xe trong hình; điều, kiện → điều kiện | 84 |
| A47K12 | hạ tầng kỹ thuật thông tin → hạ tầng, kỹ thuật, thông tin | 100 |
| A48K3a | Người cỏ thẩm quyền → Người có thẩm quyền | 102 |

Sửa bằng **src.source_revision hiện có**, trên nguồn dẫn xuất phiên 1, không sửa
raw legacy. Before là paragraph thật, sửa substring đã đối chiếu; không tuyên bố
toàn paragraph dài đã được phiên âm lại độc lập. ZIP/CRC đạt, **22 package member**
khác giữ nguyên; XML ngoài text node nguyên byte; **18/1.368 paragraph** đổi.
DOCX mới SHA `e31ebb1464cb0a5d56ec0b7e2237cf08b667247d8d9786bd1a872e76bd24bd41`.
Graph **1.309 unit/1.351 span**, parser issue 0, **4 source warning còn nguyên**.
Do own text gốc document đổi, identity root đổi và parent ID trong identity con
đổi theo: **1.309 unit ID đổi**. Không đổi công thức ID; có unit/span crosswalk.
Không mang assessment binding cũ sang ID mới, không tự migrate qrels/dataset.

HTML cũng có lỗi thật: DOM `VCSortableInPreviewMode`, type `RelatedNewsBox`, chứa
“Tham khảo thêm” sau Điều 55. PDF111 chấm dứt ở “Nghị định này./.” trước phần ký.
Projection giữ nguyên extraction, chuyển các span widget sang non-body sidecar,
tính lại riêng ID/span Điều 55; không sửa HTML capture hoặc giả PDF offsets.

**Đề xuất build sau:** nhánh HTML có projection loại widget, kèm đối chiếu PDF
cho các field quan trọng, là ứng viên text nguồn có capture chính thức; DOCX
đã hiệu chỉnh là nhánh đối chiếu/khả năng replay. Chưa quyết định thay toàn bộ
nguồn, chưa khẳng định hai edition tương đương mọi mặt, không nhập cả hai như
hai căn cứ độc lập. 67 khác biệt và phần ngoài vùng đọc vẫn phải được công bố.
Không có winword/soffice/libreoffice/pandoc trên PATH hiện tại; **chưa render DOCX**.
ZIP/XML là kiểm tra cấu trúc, không chứng minh bố cục Word sau sửa.

## TT35: tám owner đã khép blocker biểu diễn kỹ thuật

Xác định đúng tám dòng `table_owner_semantic_representation_still_blocked` trong
`seven-source-handoff-001/tt35_blockers.before_after.jsonl`; không gom năm dòng
đã xử lý trước. Tái sử dụng inventory **148 bảng/5.541 ô**, native extraction
`tt35-full-layout-001`, source-regions001 và graph Part/Chapter `circular-priority-006`.
Trong phạm vi này có **11 physical table / 590 cell**, không phải 8 bảng vật lý.

| Owner TT35 | PDF bản 69 trang | Ô | Token toàn search input | Encoder views | Max token/view | Sau xử lý |
|---|---|---:|---:|---:|---:|---|
| A6K1 | 5–6 | 43 | 980 | 5 | 241 | Technical pass |
| A7K1 | 7–8 | 93 | 3.229 | 14 | 247 | Technical pass |
| A8K1a | 9–10 | 108 | 3.587 | 15 | 248 | Technical pass |
| A8K1b | 11 | 94 | 3.098 | 14 | 247 | Technical pass |
| A8K1c | 12 | 94 | 3.064 | 14 | 248 | Technical pass |
| A8K1d | 13 | 122 | 4.079 | 18 | 248 | Technical pass |
| A21K4c | 25 | 12 | 237 | 1 | 237 | Technical pass |
| A46K2 | 48 | 24 | 604 | 3 | 248 | Technical pass |

Trước phiên này cả tám bị chặn biểu diễn owner/table. Sau: **8 typed table-owner
record, 84 encoder view, quarantine 0, unknown trên full input 0**. Không có 84
target pháp lý độc lập. View phủ kín toàn search input, giữ nguyên projection,
không truncate/tăng budget 256; đọc kết quả luôn trả toàn record/dependency.

**Cả tám scope proposal vẫn pending**, source/edition/applicability pending;
không có target pháp lý được duyệt mới. Đây là đóng blocker kỹ thuật đã kiểm
được, không ghi “sẵn sàng phát hành”. File before_after có đủ owner ID và path.

Mapping hữu hạn giữ header 2/3 tầng, merged slot tham chiếu cell có bbox phủ slot,
không điền text vào null vật lý. Bảng trang tiếp nối trỏ header bảng đầu, giữ
row/group/cell/proof. Nhãn b/c/d ở trang trước không làm bảng bị gán nhầm trang.
Title/lead, Part/Chapter thật và nội dung không nằm trong bảng giữ riêng.

Dependencies đọc đầy đủ: A6K2+AnnexII cho A6; A7K2+AnnexIII cho A7; A8K2+AnnexII
cho bốn điểm A8; A21K4a/b cho A21K4c; A46K1 cho A46K2. Không tự mở mọi dẫn chiếu
trong các phụ thuộc thành graph toàn corpus. AnnexII PDF6–17 và AnnexIII PDF18
được giữ/consumer trả toàn vùng, **chưa đọc rà ngữ nghĩa đầy đủ mọi dòng phụ lục**.
Không dùng thiếu đọc rà đó làm verified. Mọi source slice giữ đúng extraction
offset space bản thân; không trộn offset tt35-preview005 và full-layout001.

Contract mới additive `table-owner-retrieval.v1`; không sửa DDD v1/SQL/policy cũ,
không fake chunk từ bảng. Source original/cells tách khỏi derived search recipe;
record ID riêng, legal unit IDs gốc không đổi. Consumer v1 cũ chưa tự đọc type mới;
phiên 3 phải có adapter/capability rõ trước khi packaging dataset mới.

## QCVN: đính chính hai quan sát và coverage thực tế

**Đính chính kết luận phiên 1 về 4.1:** cả ảnh bản403 trang **PDF7** và Công báo
part1 **PDF8/in9** cùng có **“Khi đồng thời có, bố trí…”**, **“cùng ở một khu vực”**.
Bản agent transcription cũ bỏ dấu phẩy và đảo thành “ở cùng”. Đây là **lỗi
phiên âm agent**, không phải bằng chứng hai edition khác câu dẫn. Báo cáo/config/
pilot cũ được giữ nguyên; `source_differences.json` là đính chính riêng, kèm ảnh,
old SHA và bản text mới có offset riêng. Không ghi người dùng từng đọc/duyệt.

**Đường tránh:** ảnh bản403 **PDF300** đọc **I.418**; Công báo part4 **PDF36/in37**
đọc **I.416**. Hai OCR nhãn hẹp cùng kết quả với quan sát ảnh, nhưng chỉ là draft.
Kết luận giới hạn: khác caption hiển thị giữa hai nguồn; không sửa phiên âm
403 thành 416 để ép khớp, không coi là lỗi matching offset, không tạo global
ID alias và chưa kết luận mã pháp lý đúng/edition nào được ưu tiên cho mọi vùng.
Thông số bản vẽ chưa được đối chiếu hết.

Nguồn403 SHA `b6b99d0a0aeb13fe79072831857ece15bb254d8fb7817e80e4a2739a0d2145ce`;
nguồn Công báo part4 SHA `0b34bcb003a07adb2fbaeb7d1ccfb273d63101ae44891bcef0f9b27d14251ebb`.
URL/time capture của từng part ở `seven-source-completion-001/evidence/*.receipt.json`.
Không áp page300 của bản403 sang bản425. Ảnh crop có raster pixel bbox; locator
source dùng PDF page/bbox thật hoặc full page có nhãn, không bịa tọa độ glyph.

| Vùng | File Công báo / PDF / trang in | Đã đối chiếu | Còn thiếu và quyết định kỹ thuật |
|---|---|---|---|
| Văn bản Điều4 | part1 / 8 / 9 | Reader 4.1–4.2, các mức ưu tiên; câu dẫn so cả nguồn403 | Đính chính phiên âm hẹp, pending pháp lý |
| BảngG.1 | part2 / 83 / 84 | 6×4 = 24 cell, giá trị/đơn vị/header; HìnhG.7, V85, dẫn G.6 | Giữ full page + figure dependencies; chưa text target độc lập |
| C.14/W.214 | part2 / 20 / 21 | Body/caption HìnhC.16 + measured image bbox | Không coi embedding ảnh/[pic] là hiểu hình; giữ dependency ảnh |
| Thiết kế M.1 | part3 / 44 / 45 | Title, P.101/P.102/P.103a và hàng z(mm):140/126/87,5/70 | Kích thước nhỏ trong hình chưa phiên âm; partial image-dependent |
| Chuyển tiếp B.18 | part2 / 1 / 2; giáp part1 / 94 / 95 | Footer số Công báo kế tiếp, B.17→B.18→trước B.19 | Gắn owner vùng nguồn cho 11 dòng cũ, không tạo legal unit giả |
| Caption Đường tránh | part4 / 36 / 37; đối chiếu403/300 | I.416 so I.418 theo hai ảnh | Pending source-caption reconciliation, không rewrite source |

Lô này: **6 region record, 59 reader-region links** (không phải 59 unit),
**1 bảng/24 cell**, **3 scoped agent transcription** mới. Hai OCR label draft dùng
Tesseract5.5.3 vie/psm7/thread1, receipt/tool hash trong coordinator; OCR không là
phiên âm được chấp nhận tự động. Inventory TT35 và QCVN tách biệt; 24 cell ở đây
thuộc source-regions QCVN, không cộng vào 5.541 ô TT35.

Trong backlog **940 dòng**, đúng **11 dòng B.18** được gắn owner vùng phụ lục có
bằng chứng; **929 dòng còn lại** vẫn có region/locator/reason trong remaining_940.
Không gọi đó là 11 legal unit được parser khôi phục. Các bbox/cell/source proof
cũ giữ nguyên; text phiên âm có NFC/LF và **offset Unicode code point mới**,
không thay offsets reader/native PDF. Không xóa NUL/U+FFFE, không OCR toàn403/425.

**Downstream:** literal cũ nằm ở pilot001/002 (text/pages/review), config phiên âm
cũ và báo cáo cũ; giữ nguyên, dùng đính chính này khi đọc lại. Kiểm tra JSONL thực
tế thấy A4 ở qcvn-rule-graph003 và candidate-v4-006 đã dùng **câu Công báo đúng**
(kể cả ngắt dòng giữa “cùng” và “ở”). Search literal sai trong v3/index composition
không có hit, phạm vi/check refs ở `downstream.current_A4.json` và literal_trace.
Không suy từ search đó rằng mọi bản lịch sử đã sạch. `composition_limits.v1.jsonl`
có V3-L03 nêu I.418 về cấu tạo/kích thước: giữ bộ query đã chốt, flag cần xác định
lại binding nếu sau này dùng để đánh giá/khôi phục vùng “Đường tránh”; chưa sửa qrels.

Phương pháp có thể mở rộng **có giới hạn**: bounded native-text paragraph range,
physical table read đủ header/context, source-region continuation có trang giáp.
Sign/design chỉ khôi phục nhãn/vùng có ảnh, chưa đủ để xử lý hàng loạt thông số
hoặc suy nghĩa hình. 929 dòng và trang ngoài lô chưa đọc không được tự gỡ blocker.

## Kiểm chứng, thay đổi và phần tiếp theo

**71 test** liên quan pass; log/command/exit thực tại coordinator `tests.log` và
`tests.result.json`; gồm source revision, DOC diagnostic, full ingestion,
circular priority và Stage3–4. Số test không chứng minh chất lượng pháp lý.
Artifact checker đạt: source slices/identity/FK/graph, ZIP/XML, whole table consumer,
encoder view coverage; **13 negative checks** bị từ chối (7 owner/header/cell/
dependency/proof/page/source, 2 missing/duplicate encoder disposition, 4 QCVN
resealed mutation: dependency/source/backlog/fake review). Replay **17 payload**
của bốn nhánh giữ hash. Timestamp kỹ thuật được ghi thật, không tham gia identity.

Đã kiểm baseline2.827 file, không có thay đổi ngoài STATUS/ingestion được phép.
`git diff --check` và kiểm whitespace các file mới được chạy trước bàn giao.
Chỉ môi trường Windows/Python3.11.9 hiện tại; chưa Word render hoặc máy/OS khác.

Code mới: `nd168_field_review`, `ingestion.tt35_owner_tables`,
`qcvn_region_recovery`; bốn config finite/bound; unit tests và checker thực;
contract additive, báo cáo này/replay guide; STATUS/ingestion cập nhật đầu,
giữ nguyên nội dung lịch sử. Không thay code hash-bound cũ hoặc schema DDD.
Run checks001 dừng do harness định reseal manifest đã có (exclusive write);
harness sửa thao tác trên private copy rồi chạy checks002 đạt; không sửa source run.

**Đủ chuyển phiên 3 về kỹ thuật:** dùng ND derivative/projection/crosswalk làm
ứng viên đầu vào có lựa chọn nguồn rõ; bổ sung consumer adapter có capability
cho tám typed TT35 records và rà scope/dependency thực sự cần; mở bounded QCVN
text/table/continuation bằng phương pháp đã thử. **Chưa đủ tự nhập dataset hay
verified:** tám TT35 scope/source/edition/applicability còn pending; annex semantics
chưa rà hết; source caption I.418/I.416 chưa hòa giải; phần thiết kế/hình và929dòng
còn thiếu. Phiên2 không tạo dataset mới hay yêu cầu nhóm chuyển phiên bản.

Lệnh chính xác: [Source_Session2_Replay.md](../handoff/Source_Session2_Replay.md).
