# Stage 4 — Parser cây pháp lý có truy vết

Ngày báo cáo kỹ thuật: 2026-10-16. Snapshot sản phẩm: **2025-01-01**.
Policy hiện hành: **legal-tree.v1.1**. Run kết quả cuối:
`staging/stage4-docx-005/` và `staging/stage4-docx-006/`.

Đã đọc AGENTS, DDD/schema/README trong ZIP mẫu, Stage3_Extraction_Contract,
Stage3_Verification và code/artifact Stage 2–3. Kiểm tra Git và chụp baseline
trước khi sửa. Không stage/commit. Inference WinError 4551 vẫn là giới hạn của máy;
không tải/chạy model, chọn scope/hiệu lực, tạo chunk/context tìm kiếm hoặc index.

## Thay đổi và contract

Kế thừa parser Stage 4 đã có trên đĩa; bổ sung theo yêu cầu tiếp tục hiện tại.
Báo cáo trước được giữ tại staging/stage4-verification-002/previous-Stage4_Verification.md.

| File thay đổi trong lượt tiếp tục | Lý do |
|---|---|
| AGENTS.md | Ghi contract/policy hiện hành, cây dễ đọc và mốc dừng Stage 4. |
| README.md | CLI thực tế, cách mở cây/ví dụ, version và giới hạn. |
| config/legal_parser.v1.1.json (mới) | Policy riêng; giữ nguyên config v1 cũ. |
| src/ingestion/legal_tree.py | Thêm cách ly phụ lục, heading/list/số không rõ, sửa đổi không có delimiter, quote chưa đóng; title hai paragraph có chữ hoa/thường; boundary bảng chữ ký và coverage phần mở đầu. |
| src/ingestion/legal_tree_render.py (mới) | Cây đọc được từng văn bản, own text, parent/ID/spans và vùng chưa xử lý. |
| src/legal_parser.py | Xuất/kiểm lại cây và hai ví dụ, ghi version/config/code hash mới vào manifest. |
| tests/test_stage4.py | 21 test Stage 4, thêm 9 ca so với lượt trước. |
| docs/design/data_model_v1/Stage4_Parser_Contract.md (mới) | Contract được yêu cầu: grammar, 13 warning, quyết định bổ sung, pending và chuyển chính thức. |
| docs/reviews/Stage4_Verification.md | Báo cáo hiện hành này. |

Các schema pending trong schemas/legal_tree_v1/ đã có và được tái sử dụng không
đổi. Schema DDD chính thức, extraction Stage 3, cleaner/chunker prototype,
requirements, model, retrieval và các thay đổi có sẵn khác giữ nguyên.
Tài liệu Stage4_Legal_Tree_Contract.md và các run v1 cũ giữ nguyên để đối chiếu.

Contract hiện hành: [Stage4_Parser_Contract.md](../design/data_model_v1/Stage4_Parser_Contract.md).
Không thiếu tài liệu bắt buộc. README mẫu nằm trong ZIP, không có bản rời.
SRS/SDD còn mốc mở; dùng quyết định snapshot 2025-01-01 đã được chốt, không lấy
ngày chạy thay thế. Các mốc dừng Stage 2/3 trong AGENTS là lịch sử, đã được yêu
cầu hiện tại cho phép tiếp tục Stage 4.

## Đầu vào và pending

Dùng staging/stage3-docx-001/manifest.json: 4 DOCX, normalized.txt, trace, metadata
và source snapshot. Trước output, validator Stage 3/2 replay raw, đối chiếu hash,
contract, SQLite/export/FK; không đọc cleaned TXT hoặc corpus prototype để tạo cây.

Nguồn/extraction/units/spans vẫn **pending**, release_eligible=false,
legal_verification=not_performed. SQLite pending riêng bật FK trên mỗi kết nối;
parent cùng law và span cùng law/extraction. Không tạo hồ sơ chính thức giả.
content.sqlite trong snapshot vẫn rỗng; retrieved_at/evidence thiếu vẫn null.
CLI thành công chỉ chứng minh tính nhất quán kỹ thuật.

13 warning Stage 3 đã được liệt kê đầy đủ theo law_id/locator trong contract:
6 visual/symbol, 3 generated content ở header, 4 ancillary-parts warning.
Cả 13 vẫn có issue ID gốc trong source_warning_review.jsonl, chưa resolved.
Header có text số 2/73/2 và ancillary nếu bị nối nhầm vào thân luật có thể làm
sai nhận diện cấu trúc. Visual ở bảng quốc hiệu và paragraph rỗng p[933] Luật 35
không được suy thành heading/số. Field/numbering/revision chưa giải mã trong thân
luật được cách ly và phát issue; không lấy text tạm làm số pháp lý đã xác minh.

## Kết quả trên bốn DOCX thật

| law_id | Chương | Mục | Điều | Khoản | Điểm | Đoạn dẫn Điều có con |
|---|---:|---:|---:|---:|---:|---:|
| 168/2024/NĐ-CP | 4 | 8 | 55 | 332 | 904 | 0 |
| 165/2024/NĐ-CP | 9 | 10 | 70 | 288 | 468 | 8 |
| 36/2024/QH15 | 9 | 0 | 89 | 440 | 443 | 3 |
| 35/2024/QH15 | 6 | 4 | 86 | 388 | 383 | 6 |

Tổng **4.000 đơn vị pending**, gồm 4 gốc document, và **4.149 spans**.
Khôi phục 28 Chương; không thêm Mục/Khoản cho văn bản không có cấp đó.
17 đoạn dẫn được kiểm nguyên văn bằng equality với paragraph extraction:

| law_id | Điều | Paragraph tương ứng |
|---|---|---|
| 165/2024/NĐ-CP | 1,20,32,36,46,47,48,53 | 17,225,478,537,672,690,709,763 |
| 36/2024/QH15 | 22,26,66 | 240,272,777 |
| 35/2024/QH15 | 2,24,46,49,55,83 | 14,324,570,597,662,902 |

Mọi paragraph ở bảng trên là word/document.xml, XPath /w:document/w:body/w:p[N].
Các Điểm gồm đ giữ đúng cha, own text và thứ tự; không sao con vào parent.
unit_id áp dụng nguyên unit.v1 của DDD, không thêm timestamp/config vào đối tượng
hash. Kiểm không chu trình, cha sai law, ID/vị trí trùng, ordinal/path/citation,
quote hash/locator/offset và LF-join spans để tái dựng title/text.
Không dùng 1.457 chunk prototype làm chỉ tiêu. Hồi quy prototype chỉ đối chiếu
artifact cũ nhằm phát hiện thay đổi ngoài phạm vi.

## Coverage và các vùng cần review

Coverage phân hoạch **733.271 code point**, không cộng container trùng lá.

| law_id | Parsed | Supporting/non-body | Unprocessed | Needs review | Layout | Separator |
|---|---:|---:|---:|---:|---:|---:|
| 168/2024/NĐ-CP | 250737 | 881 | 0 | 1246 | 3 | 1380 |
| 165/2024/NĐ-CP | 165380 | 1788 | 0 | 4 | 1 | 981 |
| 36/2024/QH15 | 161827 | 368 | 0 | 74 | 3 | 1025 |
| 35/2024/QH15 | 145721 | 394 | 481 | 0 | 5 | 972 |

Phần mở đầu giữ ở root có spans nhưng được đếm supporting/non-body trong v1.1.
Nhãn này là kỹ thuật, không phải quyết định scope. Separator LF/TAB có record
riêng. Locator rỗng vẫn có record: Needs review=0 ký tự của Luật 35 không có nghĩa
không có review tại p[933]. Đủ ký tự được ghi nhận không phải toàn bộ đã hiểu.

10 bảng được inventory: 8 bảng mở đầu/chữ ký supporting và 2 bảng nội dung Luật 35
unprocessed, B/w:tbl[2] [142441,142830), B/w:tbl[3] [143125,143228).
B=/w:document/w:body. Có context_unit_id, locator, lý do; không tạo Khoản từ ô.
481 là ký tự lá chưa phân tích, separator trong bảng đếm riêng.

10 issue parser (tách khỏi 13 warning nguồn):
- NĐ168: 3 POINT_SEQUENCE_GAP ở p[518], p[1038], p[1057]. Không thêm chữ thiếu.
- NĐ168: 2 AMBIGUOUS_POINT ở p[519], p[1058] và 2 CONFLICTING_POINT_DESIGNATION ở
  p[518], p[1057]. Hai cặp đ) trùng dưới Điều 16 Khoản 2 và Điều 40 Khoản 3 được
  cách ly cả hai vị trí; không tự sửa thành d)/e). p[1059] ở vùng tiếp theo chưa rõ
  được ghi STRUCTURE_SUSPENDED; phục hồi ở Khoản liên tiếp rõ ràng.
- Luật 35: 2 TABLE_STRUCTURE_NOT_PARSED và 1 UNDECODED_SOURCE_CONTENT tại p[933],
  [147382,147382); giữ riêng hai warning visual gốc cùng locator.

Các trích dẫn sửa đổi nhiều paragraph trong nguồn thật, gồm 5a. trong Luật 35,
được giữ là nội dung của đơn vị chứa trích dẫn, không tạo Điều/Khoản gốc mới.
Fixture riêng chứng minh phụ lục, số không rõ, danh sách minh họa, quote chưa
đóng và thay thế thiếu delimiter được báo/cách ly thay vì ép vào cấp trước.
Chưa có phụ lục độc lập được nhận diện trong bốn main body này; test fixture
không chứng minh mọi kiểu phụ lục hay cách trình bày Word đều được hỗ trợ.

## Ví dụ A — Điều 22 Luật 36

Ví dụ này ở examples.json mục A, examples.txt và cây trees/03.txt.
Article unit_id (A):
`u_6a8c7d8846b7b4a85271ac2ddac92baa413919e8bafbb121e835d71f6754ecc1`.
Ba Khoản có parent_unit_id=A; Điều thuộc Chương II, không có Mục trung gian.

Title: Nhường đường tại nơi đường giao nhau.
Text riêng của Điều, giữ nguyên nguồn:

> Khi đến gần đường giao nhau, người điều khiển phương tiện tham gia giao thông đường bộ phải quan sát, giảm tốc độ và nhường đường theo quy định sau đây:

Các con có text riêng:

```text
1. Tại nơi đường giao nhau giữa đường không ưu tiên với đường ưu tiên hoặc giữa đường nhánh với đường chính thì xe đi từ đường không ưu tiên hoặc đường nhánh phải nhường đường cho xe đi trên đường ưu tiên hoặc đường chính từ bất kỳ hướng nào tới;
2. Tại nơi đường giao nhau không có báo hiệu đi theo vòng xuyến, phải nhường đường cho xe đi đến từ bên phải;
3. Tại nơi đường giao nhau có báo hiệu đi theo vòng xuyến, phải nhường đường cho xe đi đến từ bên trái.
```

| Đơn vị / field | Locator B/w:p[N] | Code-point span |
|---|---|---|
| Điều 22 / title | p[239] | [36246,36282) |
| Điều 22 / text_original — đoạn dẫn | p[240] | [36283,36435) |
| Khoản 1 / text_original | p[241] | [36436,36682) |
| Khoản 2 / text_original | p[242] | [36683,36792) |
| Khoản 3 / text_original | p[243] | [36793,36896) |

Part word/document.xml, B=/w:document/w:body. Extraction A:
`e_6150573f798da52c78b6b16bf5149a0c2046843a957393f34f6197f7c3f672ae`.
Chữ Điều 22. là marker được coverage ghi riêng; title chỉ lấy tên Điều.
text_original của Điều chỉ có đoạn dẫn, không chứa bản sao ba Khoản.
Spans giữ extraction_id/locator_json/quote_sha256 và span_order=0 cho từng field
ở ví dụ này. Full unit/span/parent ID có trong examples.json.

## Ví dụ B — NĐ168, Điều 6 Khoản 1 có năm Điểm

Ví dụ ở examples.json mục B, examples.txt và cây trees/01.txt.
Khoản unit_id (P):
`u_c45877c28ba1e64f6bccbefd5e5aa763bbf486ac419426b7891b01f0ad962613`.
Cha là Điều 6: `u_4231753fa0f5b846724d3849eb343362f68ee5fbbb2919010fc7be7ef1b26a9e`.
Tất cả Điểm a,b,c,d,đ có parent_unit_id=P, ordinal 0,1,2,3,4.

Nội dung riêng của Khoản (title rỗng vì không có tên Khoản riêng):

> 1. Phạt tiền từ 400.000 đồng đến 600.000 đồng đối với người điều khiển xe thực hiện một trong các hành vi vi phạm sau đây:

Nội dung riêng từng Điểm, không sao vào text riêng của Khoản:

```text
a) Không chấp hành hiệu lệnh, chỉ dẫn của biển báo hiệu, vạch kẻ đường, trừ các hành vi vi phạm quy định tại điểm a, điểm c, điểm d, điểm đ khoản 2; điểm a, điểm d, điểm đ, điểm e, điểm n, điểm o khoản 3; điểm a, điểm b, điểm đ, điểm e, điểm i, điểm k, điểm l khoản 4; điểm a, điểm b, điểm c, điểm d, điểm đ, điểm i, điểm k khoản 5; điểm a khoản 6; khoản 7; điểm b, điểm d khoản 9; điểm a khoản 10; điểm đ khoản 11 Điều này;
b) Khi ra, vào vị trí dừng xe, đỗ xe không có tín hiệu báo cho người điều khiển phương tiện khác biết;
c) Không báo hiệu bằng đèn khẩn cấp hoặc không đặt biển cảnh báo “Chú ý xe đỗ” theo quy định trong trường hợp gặp sự cố kỹ thuật (hoặc bất khả kháng khác) buộc phải đỗ xe chiếm một phần đường xe chạy hoặc tại nơi không được phép đỗ xe, trừ hành vi vi phạm quy định tại điểm c khoản 7 Điều này;
d) Không gắn biển báo hiệu ở phía trước xe kéo, phía sau xe được kéo; điều khiển xe kéo rơ moóc không có biển báo hiệu theo quy định;
đ) Sử dụng còi trong thời gian từ 22 giờ ngày hôm trước đến 05 giờ ngày hôm sau trong khu đông dân cư, khu vực cơ sở khám bệnh, chữa bệnh, trừ các xe ưu tiên đang đi làm nhiệm vụ theo quy định.
```

| Đơn vị / field text_original | Locator B/w:p[N] | Code-point span |
|---|---|---|
| Khoản 1 | p[96] | [16452,16574) |
| Điểm a | p[97] | [16575,16999) |
| Điểm b | p[98] | [17000,17102) |
| Điểm c | p[99] | [17103,17396) |
| Điểm d | p[100] | [17397,17530) |
| Điểm đ | p[101] | [17531,17724) |

Part word/document.xml, B=/w:document/w:body. Extraction B:
`e_d559951c947c242755db466fc8e4bb170d6c8053cc8873457a6b7e372b1ac540`.
Đây là trích dữ liệu DOCX pending, chưa phải kết luận mức phạt áp dụng tại snapshot.

## Lệnh đã chạy và kết quả

Tiền tố thực tế: `.\.venv-stage1\Scripts\python.exe -X utf8 -B`.
Command/exit code đầy đủ tại staging/stage4-verification-002/final-commands.json;
log final-*.log. Tên tag log parse-003/parse-004 là tag runner, command thực tế ở
final-commands.json ghi rõ run-dir stage4-docx-005/006. Các log trước đó giữ nguyên.

| Lệnh sau tiền tố | Kết quả cuối |
|---|---|
| -m src.source_registry validate --manifest staging/stage2-sources-001/manifest.json | Exit 0. |
| -m src.extraction_pipeline validate --manifest staging/stage3-docx-001/manifest.json | Exit 0. |
| -m src.legal_parser parse --extraction-manifest staging/stage3-docx-001/manifest.json --run-dir staging/stage4-docx-005 | Exit 0; 4.000 unit/4.149 span, pending. |
| Cùng input với --run-dir staging/stage4-docx-006 | Exit 0. |
| -m src.legal_parser validate --manifest staging/stage4-docx-005/manifest.json | Exit 0; replay/FK/hash/roundtrip/coverage/views khớp. |
| Cùng validate, thêm --require-release-ready | Exit 1 đúng yêu cầu; release=false. |
| -m unittest discover -s tests -p test_stage4.py -v | 21/21 đạt. |
| -m unittest discover -s tests -v | 68/68 đạt: 13 Stage 1 + 18 Stage 2 + 16 Stage 3 + 21 Stage 4. |
| git diff --check | Exit 0; chỉ có cảnh báo LF/CRLF của Git. |
| git status --short --untracked-files=all; git diff --cached --stat | Đã xem; index không có file staged. |
| git check-ignore staging/stage4-docx-005/legal_tree.pending.sqlite staging/stage4-verification-002/final-commands.json | Cả hai output được ignore. |

Đã thử thiếu manifest ở lượt kiểm tra trước cùng phiên: exit 1, không tạo output.
Test suite cũng thử input bị sửa/hash sai, output ngoài staging, run đã tồn tại,
reseal checksum vẫn bị replay từ chối, FK/ID/cha sai/chu trình/cấp giả, import
không ghi/xóa/kết nối hoặc tải model, và runtime parser chặn inference/index engines.
Fixture synthetic tách khỏi luật thật. Hồi quy Stage 1 có BM25 fixture nhỏ tạm;
không xây BM25 phục vụ từ corpus thật.

21 test tập trung gồm title một/hai dòng (cả chữ hoa/thường), đoạn dẫn trước
Khoản/Điểm trực tiếp, dẫn chiếu Điều trong câu, nested instruction/quote sửa đổi,
quote không đóng, replacement thiếu delimiter, bảng/part/header/chữ ký, phụ lục,
numbering/field/revision chưa giải mã, số/heading/list không rõ, vị trí trùng,
roundtrip/determinism và cây dễ đọc bị sửa sau reseal.

final-determinism.json so SHA-256 **15 artifact** giữa 005/006: sáu JSONL, SQLite,
coverage_report, examples JSON/TXT, trees/index và bốn cây TXT đều giống byte.
Không yêu cầu manifest/built_at giống nhau. unit/spans của bốn nguồn thật cũng
không đổi byte so với run v1 trước; coverage nhãn root và views là thay đổi bổ sung.

## Bảo toàn, giới hạn và tự kiểm tra

Baseline 431 file gồm mã/tài liệu và 369 file được bảo vệ trước lần sửa đầu tiên.
369/369 file data/Qdrant/staging cũ giữ nguyên SHA-256: **11 data, 3 Qdrant,
355 staging**, không thiếu/đổi file. Có baseline.json và preservation.json trong
thư mục bằng chứng. Schema DDD chính thức vẫn khớp byte schema.sql trong ZIP:
`37280458080d308ca5201be78bb1c59d8bcfbc79a424eb833b6efd2de7bff786`.

workspace_delta.json đối chiếu 431 file baseline: chỉ 6 file hiện có được cập
nhật và 3 file mới như bảng đầu báo cáo; không thiếu file, không đổi file khác.

Không sửa raw/extraction hoặc artifact cũ để khớp parser mới. Run v1/003/004 giữ
nguyên byte và code hash lịch sử; replay cần đúng code/tool đã ghi. Dùng 005/006
với code hiện hành. Bản thân ứng dụng tìm kiếm vẫn đọc corpus_chunks.jsonl và
qdrant_db cũ, chưa dùng extraction/cây mới.

Chưa hỗ trợ parser PDF, merge nhiều file/bản thay thế, giải mã Word numbering/
field/revision, OCR, cây phụ lục/figure hoặc ngữ nghĩa bảng. Hai bảng Luật 35 và
các ký hiệu đ) xung đột còn pending. Grammar text/trace có giới hạn (không có
style/indent/render Word); nhãn danh sách và delimiter bảo thủ không chứng minh
mọi dẫn chiếu/quote/cách trình bày đều đúng. Thay thế thiếu delimiter có thể cách
ly cả phần thân hợp lệ sau đó; cần review hoặc policy có bằng chứng để thu hẹp.
Chưa xác minh bản ban hành, hiệu lực/scope hoặc release eligibility.

Mở trees/index.json để chọn văn bản; trees/01.txt=NĐ168, 02=NĐ165, 03=Luật36,
04=Luật35 trong run này. Có full own text, unit/parent ID và spans. Ví dụ A/B đầy
đủ ở examples.txt hoặc examples.json; coverage/quality_issues có locator để đối
chiếu extraction_snapshot/extractions/<extraction_id>/normalized.txt và trace.json.

```powershell
Get-Content -Encoding UTF8 staging/stage4-docx-005/trees/index.json
Get-Content -Encoding UTF8 staging/stage4-docx-005/examples.txt
Get-Content -Encoding UTF8 staging/stage4-docx-005/coverage_report.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.legal_parser validate --manifest staging/stage4-docx-005/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
# Tái tạo: run-dir phải chưa tồn tại; không xóa run cũ để chạy lại.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.legal_parser parse --extraction-manifest staging/stage3-docx-001/manifest.json --run-dir staging/stage4-review-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.legal_parser validate --manifest staging/stage4-review-001/manifest.json --require-release-ready
$LASTEXITCODE # 1 vì pending

git diff --check
git status --short --untracked-files=all
git diff
```

File mới untracked không hiện nội dung trong git diff thông thường. Database,
staging, venv và cache không đưa vào commit. Dừng sau Stage 4 để xem diff/kết quả.
