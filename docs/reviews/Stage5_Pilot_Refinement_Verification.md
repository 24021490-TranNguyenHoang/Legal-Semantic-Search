# Kiểm chứng pilot refinement — snapshot 2025-01-01

Input: `staging/stage5-scope-survey-001/manifest.json`. Output mới:
`staging/stage5-pilot-refinement-001/`. Log, baseline và bằng chứng kiểm tra
trong `staging/stage5-pilot-refinement-verification-001/`.
Contract: [Stage5_Pilot_Refinement_Contract.md](../design/data_model_v1/Stage5_Pilot_Refinement_Contract.md).

Đây là rà soát đề xuất của agent trên đúng 107 target included trước đó;
không mở rộng corpus, tạo decision reviewer hoặc xác minh pháp lý. Đã đọc
code hiện hành, AGENTS, DDD, BRD và các contract assessment/scope/chunking.
Snapshot mở trong BRD/SRS tiếp tục được xử lý theo quyết định DDD/người
dùng 2025-01-01; không dùng ngày hiện tại thay snapshot.

## Kết quả nội dung và context

| Hạng mục | Kết quả thực tế |
|---|---:|
| Target đã đọc đủ và có annotation theo unit/hash | 107 |
| Giữ nhãn included, bổ sung lý do cụ thể | 97 |
| Đổi đề xuất included thành pending | 10 |
| Target chưa đọc đủ | 0 |
| Dependency từ cha pending đã rà theo target/field | 42 |
| Target liên quan / field cha khác nhau | 35 / 9 |
| Đề xuất dùng field / cần xem thêm / không dùng | 41 / 1 / 0 |
| Target có tất cả field được đề xuất dùng / còn vướng field | 34 / 1 |
| Included mới có thể preview / quá budget | 95 / 2 |
| Toàn bộ hồ sơ pilot giữ lại, kể cả pending/quarantine | 107 |
| Reviewer event / release eligible | 0 / false |

Tập included đề xuất mới: 71 Luật 36, 24 NĐ168, 2 Luật 35. Đây là đề xuất
scope, không phải danh sách đã áp dụng được tại snapshot. Mỗi unit có đối
tượng, hành vi/quyền/nghĩa vụ, UC BRD, giới hạn dẫn chiếu và đánh giá lý do
cũ. Lý do trước chủ yếu theo nhóm và trích đầu đoạn; các proposal cũ giữ
nguyên byte. Cả 107 proposal giải thích lại có ID mới và previous ID/hash;
97 nhãn không đổi không có nghĩa payload proposal không đổi.

| Các đề xuất chuyển pending | Lý do còn thiếu |
|---|---|
| NĐ168 Điều 47 khoản 5 điểm a | Đoạn dẫn chứa nhiều đối tượng; hành vi phụ thuộc các dẫn chiếu Điều 12, chưa xác định ca người trực tiếp tham gia giao thông. Field đoạn dẫn khoản 5 cũng cần xem thêm. |
| NĐ168 Điều 54 khoản 1–2 | Quy tắc chuyển tiếp/chọn văn bản theo thời điểm; chưa xác định target trực tiếp hay dependency supporting cụ thể. Giữ giá trị làm căn cứ applicability, không loại chỉ vì ngày. |
| Luật 35 Điều 59 khoản 1 điểm a, b, c, đ; khoản 6 | Quyền/nghĩa vụ người lái và nhân viên dịch vụ vận tải hoặc dẫn chiếu rộng; cần giới hạn ca sử dụng. Điểm đ còn dẫn Điều 60 khoản 2 điểm c ngoài context đang chọn. |
| Luật 35 Điều 63 khoản 1 điểm a–b | Trộn điều kiện an toàn, tải/khổ với quyền vận tải/giấy vận tải. Không tách riêng câu thuận lợi để tuyên bố cả leaf là target phù hợp. |

Luật 35 Điều 59 khoản 2 và Điều 63 khoản 2 vẫn được đề xuất included do
đối tượng/hành vi cụ thể của người lái thực tế; không loại toàn nhánh vận
tải. Không ép scope cha xuống con. Các title/đoạn dẫn phù hợp có thể được
đề xuất dùng riêng trong khi scope toàn cha pending. Sau thay đổi scope,
27 target included vẫn dùng các field đã rà từ cha pending; không tự chặn
chúng vì nhãn cha, cũng không gán cha verified.

Toàn bộ 107 candidate giữ nguyên chunk ID/hash, nguyên văn, context,
text_for_search và quarantine. Source/extraction/technical/applicability
vẫn pending, decision/reviewer và ngày hiệu lực null. Ví dụ Luật 36 Điều
10 khoản 3 vẫn có scope đề xuất included nhưng applicability chưa kết
luận; finding/date rule cũ về ngoại lệ thời điểm được liên kết riêng,
không mặc định áp dụng ở 2025-01-01.

## Unknown: tái hiện bằng tokenizer thật

Model `bkai-foundation-models/vietnamese-bi-encoder`, revision
`84f9d9ada0d1a3c37557398b9ae9fcedcdf40be0`; preprocessing
`phobert-pyvi-input.v1`, PyVi 0.1.1. Dùng assets/config và môi trường đã pin
trong coverage snapshot; tokenizer-only CPU, không tải weights/inference.

Luật 36 Điều 62 khoản 5 điểm c:

| Input đo thực tế | Token gồm special | Unknown |
|---|---:|---:|
| text_for_search trước tiền xử lý | 123 | 4 |
| Probe chỉ chuẩn hóa whitespace | 119 | 0 |
| encoder_text hiện hành, có PyVi | 91 | 1 |

Probe whitespace không được dùng thay policy. Sau tiền xử lý, unknown
ở token position **87** (từ 0, gồm special), ID **3**, piece **`_do`** từ
`có_lý_do`. Piece `_do` vắng trong vocabulary đã pin, `do` có mặt. Đây là
tương tác segmentation/BPE/vocabulary quan sát được, chưa có bằng chứng
lỗi encoding. Nguồn chứa cụm “không có lý do chính đáng”; giữ nguyên cả
phủ định, dấu và nội dung.

| Namespace offset Unicode code point, từ 0 | Lát cắt |
|---|---|
| encoder_text | [440,443) = `_do` |
| text_for_search | [434,436) = `do` |
| text_original riêng của Điểm | [214,216) = `do` |
| normalized.txt extraction Stage 3 | [114300,114302) = `do` |
| Locator DOCX | word/document.xml, paragraph_index 725, `/w:document/w:body/w:p[726]` |

Tokenizer slow không có native offset_mapping. Source fragment được chứng
minh bằng regex/BPE replay khớp token IDs. Mapping về search chỉ được ghi
nhận sau khi chứng minh hai chuỗi ký tự không-whitespace bằng nhau trên
toàn văn, source đã NFC và không có underscore nguyên gốc. Underscore
encoder tại 440 là ký tự thêm, không được gán offset nguồn. Sau đó trừ
offset component thật và tra spans/LF join đã roundtrip. Khi các điều kiện
không thỏa, phương pháp trả unavailable; không đoán inverse segmentation.

Chưa đo ảnh hưởng tới embedding/retrieval hoặc ngữ nghĩa của model. Không
đổi model, vocabulary, preprocessing, nguyên văn hay offset để ép unknown
về 0. JSON diagnostics giữ config, toàn đầu vào, proof và các phép đo thật;
MD trình bày giới hạn. Các token count khác dùng evidence cũ được upstream
validator replay; không gọi chúng là toàn bộ số đo mới của lượt refinement.

## Các ca dài và bản đọc đầy đủ

| NĐ168 | Token encoder gồm special | Scope đề xuất mới |
|---|---:|---|
| Điều 6 khoản 2 điểm đ | 294 | included |
| Điều 8 khoản 2 điểm b | 270 | included |
| Điều 47 khoản 5 điểm a | 291 | pending |

Budget preview vẫn 256. Giữ đủ cả ba candidate/context trong quarantine
cũ, không truncate, split hoặc bỏ context. `priority_cases_fulltext.md`
có **13 ca, 50.043 Unicode code point**, đầy đủ target và mọi context của
ba ca dài, ca unknown và mười ca scope pending (có ca giao nhau). Kèm
citation, unit ID, field offset, source locator/hash; không chỉ trích đầu.

`pilot_candidates.csv/JSONL` giữ đủ 107 hồ sơ, tách proposal scope,
khả năng chunk/context, token/unknown, bằng chứng nguồn, technical review,
applicability và việc tiếp theo. Không có trạng thái ready. Trong nested
context_dependencies, các row lịch sử vẫn tính base từ `scope_snapshot/`;
proof mới tính từ run như contract. Đã kiểm riêng 186 lát cắt nguồn context
qua đúng base, hash file và quote hash, không phải chỉ kiểm đường dẫn có tồn tại.

## Lệnh và bằng chứng kiểm tra

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.scope_survey validate --manifest staging/stage5-scope-survey-001/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.pilot_refinement build --scope-manifest staging/stage5-scope-survey-001/manifest.json --run-dir staging/stage5-pilot-refinement-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.pilot_refinement validate --manifest staging/stage5-pilot-refinement-001/manifest.json
```

| Lệnh/kiểm tra đã chạy | Kết quả |
|---|---|
| Validator input scope survey | Exit 0; 202,797 giây |
| Build refinement run mới | Exit 0; 209,015 giây |
| Validator độc lập refinement, gồm replay upstream | Exit 0; 329,720 giây |
| Full unittest, bật bảy nhóm artifact integration | **207 test đạt, không skip**, exit 0; 168,857 giây trong test runner |
| Hash/quote context qua base lịch sử | 186 lát cắt đạt |
| AST Python, JSON, whitespace file mới, liên kết tài liệu mới | Đạt |
| git diff --check / staged files | Exit 0 / không có |

Validator và suite chạy đồng thời; thời gian gồm replay tokenizer CPU/I/O
không phải thời gian inference. Full suite gồm 12 test mới: 10 fixture và
2 integration thật. Log actual exit code/thời gian ở `*_result.json`,
`validate.log`, `unittest_final.log`; không suy kết quả từ báo cáo cũ.
Không chạy lại build vào run đã tồn tại; README có tên run mới cho tái tạo.

Lệnh suite đã chạy với các binding artifact thật:

```powershell
$env:VTLS_ARTICLE22_MANIFEST = 'staging/article22-pdf-004/manifest.json'
$env:VTLS_ARTICLE22_PREVIEW_MANIFEST = 'staging/article22-preview-001/manifest.json'
$env:VTLS_STAGE6_MANIFEST = 'staging/article22-stage6-002/manifest.json'
$env:VTLS_POINTS_MANIFEST = 'staging/stage6-points-002/manifest.json'
$env:VTLS_COVERAGE_MANIFEST = 'staging/stage6-coverage-001/manifest.json'
$env:VTLS_SCOPE_MANIFEST = 'staging/stage5-scope-survey-001/manifest.json'
$env:VTLS_REFINEMENT_MANIFEST = 'staging/stage5-pilot-refinement-001/manifest.json'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
```

Test fixture tập trung kiểm field/offset/hash/target binding, scope cha
pending không chặn field đã đề xuất dùng, không verified cha, missing
field không fallback toàn cha, giữ candidate khi field cần xem thêm,
107-ID join/history, giữ nguyên input, không claim included khi chưa đọc,
mapping có điều kiện và fulltext không cắt. Hai integration test dùng
artifact/tokenizer thật kiểm ID/hash/context, số lượng và offsets unknown.

Lần chạy hồi quy đầu dừng với `TypeError: 'WindowsPath' object is not
callable`: biến `cls.run` trong test integration mới đè phương thức run
của unittest. Đã sửa tên biến thành `bundle`; không đổi code xử lý hoặc
seal bundle để sửa lỗi test. Log lần lỗi được giữ riêng `unittest.log`.

## Bảo toàn và diff

Baseline trước sửa: 10.159 file raw/processed/Qdrant/artifact staging và
115 file source/test/config/schema/tài liệu đã có. Kiểm SHA-256 sau chạy:
không mất/sửa file artifact cũ hoặc thêm file vào các thư mục artifact cũ.
Trong 115 file đã có, chỉ AGENTS.md và README.md được nối thêm nội dung;
toàn byte prefix trước lượt này giữ nguyên. Schema chính thức khớp byte
`schema.sql` trong ZIP thiết kế; không dùng nhầm `eval_schema.sql`.

Trạng thái Git trước lượt này đã có AGENTS/README sửa cùng năm file scope
survey chưa theo dõi; giữ nguyên chúng, không stage/commit/reset/clean.
Lượt này thêm config/module/test/contract/báo cáo refinement, nối AGENTS
và README; không sửa module scope/builder/encoder hoặc policy/run cũ.

| File của riêng lượt này | Mục đích |
|---|---|
| src/pilot_refinement.py | CLI build/validate, joins/history, review sidecar, chẩn đoán offset và xuất bản đọc đầy đủ. |
| config/pilot_refinement.v1.json | 107 annotation scope và 9 annotation field có binding/hash; không phải classifier từ khóa. |
| tests/test_pilot_refinement.py | 10 test fixture và 2 test artifact/tokenizer thật. |
| docs/design/data_model_v1/Stage5_Pilot_Refinement_Contract.md | Quy tắc field context, proposal/history, namespace/base đường dẫn và giới hạn chẩn đoán. |
| docs/reviews/Stage5_Pilot_Refinement_Verification.md | Báo cáo này, bằng chứng và lệnh tái chạy. |
| AGENTS.md, README.md | Nối lần lượt 1 dòng và 39 dòng: phạm vi được phép, hướng dẫn thực thi; giữ prefix trước lượt này. |

`git diff --stat` chỉ hiện file đã được Git quản lý (còn gộp thay đổi của
lượt trước). Năm file refinement mới hiện untracked, chưa stage. Năm file
scope survey untracked từ trước vẫn nguyên byte; không đưa chúng vào số
file mới của lượt này. Hai run mới ở staging không được Git theo dõi.

## Ba bước đề xuất tiếp theo, chưa thực hiện

1. Giải quyết 10 proposal scope pending và field Điều 47 khoản 5 bằng
   đối tượng, dẫn chiếu và ca BRD cụ thể; chưa thêm context ngoài cây cha.
2. Thiết kế xử lý dài riêng cho hai included 294/270 token, giữ nguyên
   điều kiện và source spans; không dùng việc xóa context để pass budget.
3. Hoàn thiện hồ sơ nguồn, technical review có phạm vi và applicability
   cho tập chọn. Unknown cần giữ bằng chứng và đánh giá tác động riêng
   nếu đề xuất đổi policy; chưa biến technical pass thành xác minh pháp lý.

Không mở rộng 4.000 unit, sửa parser, tạo corpus verified, embedding/index
hoặc kích hoạt ứng dụng. Không có quyết định reviewer mới hay ngày hiệu
lực được tự điền. Các bước tiếp theo là đề xuất, chưa triển khai.
