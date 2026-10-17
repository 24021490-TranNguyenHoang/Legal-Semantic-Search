# Stage 5A — báo cáo contract assessment và pilot

Ngày chạy **2026-10-16**; snapshot pháp lý mục tiêu **2025-01-01**.
Kết quả: triển khai công cụ/contract và pilot **40 đơn vị**, kiểm tra kỹ thuật
đạt; **0 quyết định rà soát thực tế**, 40 applicability_status=pending_review,
40 scope_status=null; **0 ứng viên target, 0 ứng viên context**, không phát hành.
Không tuyên bố nguồn/extraction/cây hoặc assessment đã verified.

## Đọc trước, Git và phạm vi

Đã đọc AGENTS, DDD/schema/README mẫu trong ZIP, contract Stage 2–4 và bộ rà soát
`staging/stage4-review-pack-001/`; đối chiếu BRD §3.1/3.3, inventory và các giới
hạn SRS/SDD. Git có sẵn thay đổi Stage 1–4 và file untracked; bảo toàn chúng,
không stage/commit/reset/clean. Inference Windows WinError 4551 vẫn là giới hạn
đã ghi nhận, không thử tải/chạy model ở Stage 5A.

Mâu thuẫn đã giữ rõ trong contract: architecture.md/scope.md thuộc prototype;
scope.md chưa đồng bộ tên NĐ165/NĐ168 và 1.457 chunk không phải mục tiêu mới.
SRS/SDD còn snapshot mở, DDD/inventory/người dùng chốt 2025-01-01. Không dùng
ngày chạy thay snapshot. Không thiếu contract/schema cần cho phạm vi công cụ;
thiếu quyết định thực tế và hồ sơ pháp lý đầy đủ được giữ pending, không bịa bù.

## File thay đổi trong lượt Stage 5A

| File | Lý do |
|---|---|
| AGENTS.md | Ghi quyền làm Stage 5A giới hạn và mốc dừng mới; giữ nguyên chỉ dẫn/lịch sử cũ. |
| README.md | Lệnh Windows cho capture/validate/pilot/candidates, artifact và giới hạn thực tế. |
| src/assessment_evidence.py | CLI tải HTTPS nguồn chính thức vào run mới; byte/hash/timestamp/HTTP metadata, text PDF theo trang, validator; import không network/IO. |
| src/assessment_contracts.py | Binding/ID, quy tắc ngày/ngoại lệ, dossier và chuỗi quyết định, assessment pending, ánh xạ unit_assessment. |
| src/assessment_pipeline.py | CLI pilot/validate/candidates, snapshot input, 40 unit, tác động issue, proposals/decisions riêng, SQLite/FK/replay, CSV/Markdown/ảnh bằng chứng. |
| config/assessment_evidence.v1.json | Bảy URL chính thức cho ba văn bản có mặt trong pilot, không tải NĐ165 không được chọn. |
| config/assessment_pilot.v1.json | Danh sách unit_id rõ ràng, nhóm pilot, đề xuất scope và hash/locator tài liệu căn cứ. |
| config/assessment_findings.v1.json | Yêu cầu trích lát PDF, quan sát máy theo trang và rule ngày ứng viên; không phải quyết định pháp lý. |
| schemas/assessment_v1/pending_schema.sql | SQLite staging riêng, không giả bảng corpus/legal_unit chính thức. |
| schemas/assessment_v1/pending_assessment.schema.json | Contract JSON của assessment pending, ba cổng target/context/release đóng. |
| tests/test_stage5a.py | 23 test synthetic, độc lập luật thật, không live network/model. |
| docs/design/data_model_v1/Stage5_Assessment_Contract.md | Quyết định triển khai bổ sung và đường chuyển sang DDD khi đủ điều kiện. |
| docs/reviews/Stage5A_Verification.md | Báo cáo này. |

Chỉ **AGENTS.md và README.md** thay đổi trong các file đã tồn tại trước lượt
này; 11 file còn lại là file mới. Không sửa parser/extraction/chunker, retrieval,
requirements hoặc schema DDD chính thức. Thay đổi Stage 1–4 vẫn hiện trong Git
diff/status do chưa commit, không phải tất cả đều phát sinh ở Stage 5A.
Không đưa staging/SQLite/venv/cache vào Git; artifact phục vụ xem tại workspace.

## Artifact nên mở

Run chính: **staging/stage5a-pilot-006/**. Run lặp cùng code/input:
**staging/stage5a-pilot-007/**. Capture nguồn: **staging/stage5a-evidence-001/**.
Log/kết quả kiểm tra cuối: **staging/stage5a-verification-002/**; baseline trước
lượt triển khai nằm ở **staging/stage5a-verification-001/baseline.json**.

| Artifact trong run pilot chính | Nội dung |
|---|---|
| pilot.md / pilot.csv | Bảng 40 đơn vị, nội dung riêng, source spans/locator, kỹ thuật và đề xuất; CSV UTF-8 mở bằng Excel Data → From Text/CSV. |
| evidence_review.md | 16 lát/quan sát bằng chứng, URL, hash, trang, thời điểm truy cập và việc chưa kết luận. |
| evidence_pages/*.png | Năm trang PDF scan NĐ168: 8, 41, 85, 86, 110; bản chụp để rà bằng mắt, không OCR. |
| technical_review.md | 9 vùng và 34 link ảnh hưởng cụ thể, source quote, locator/offset và lý do. |
| pending_work.md | Các việc cần rà trước quyết định/phát hành. |
| subjects.pending.jsonl | 40 unit_id/nội dung thật lấy nguyên từ cây Stage 4, không tạo cấp/ID pháp lý mới. |
| machine_proposals.jsonl / date_rules.pending.jsonl | 40 đề xuất máy và 5 rule ngày ứng viên, tách quyết định. |
| review_decision_history.jsonl / review_submissions.json | Lịch sử rỗng / events và attestations rỗng, không ghi reviewer giả. |
| assessments.pending.jsonl / ddd_mapping.pending.jsonl | Assessment và ánh xạ dự kiến; chưa nạp DDD, corpus_version=null, ready_to_load=false. |
| assessment.pending.sqlite | Binding 1, subject 40, evidence 7, region 9, impact 34, proposal 40, decision_event 0, assessment 40; FK bật và kiểm readonly. |
| validation_report.json / manifest.json / manifest.sha256 | Kết quả kỹ thuật, inventory/checksum/version/binding. |
| input_snapshot/ / review_pack_snapshot/ / evidence_snapshot/ / requirements_snapshot/ | Bản chụp bất biến các đầu vào và tài liệu căn cứ scope. |

Các run stage5a-pilot-001…005 là run thử trước lần chốt code cuối; giữ nguyên
byte nhưng không dùng thay run 006/007. Validator yêu cầu đúng tool/code hash,
không tự coi run của code cũ là replay bằng phiên bản hiện hành.

## Binding đầu vào đã kiểm

Stage 4 policy legal-tree.v1.1, 4.000 unit/4.149 spans, vẫn pending:

| Thành phần | SHA-256 |
|---|---|
| staging/stage4-docx-005/manifest.json | ca30426fea4f39e797ffa0e922010cd507cf131b86df76c9174d2a0518e1c938 |
| legal_units.pending.jsonl | a6730564d31b274e23ff9d22b48ce94e9ed54ee757318023233bddc6a97780d9 |
| source_spans.pending.jsonl | d744a3015a1e93b6bc6d54237b89528fd7657b8bc823b68887d65e144989dbc1 |
| Stage 3 manifest trong snapshot | 39d4895c9105e96b5e87661e2b1b65244f888bd3172478754cebfec075f145f0 |
| Review pack manifest | 8c3a345bf0283e3376171f32e2f804d54b08a9bdf715fb36173bad8c8229d9f2 |
| Evidence manifest mới | 5b90034e1a8f934876e3ef3580af1812b37f7a52ffd1654bc594e66c4fdd90dc |

binding.json còn khóa code/tool parser, config/findings, policy assessment.
Mỗi assessment/proposal giữ unit_id, unit_sha256 và snapshot. Thay bundle hoặc
bằng chứng không tự chuyển quyết định cũ. Manifest hash không phải chữ ký pháp lý.

## Bằng chứng chính thức đã lưu và giới hạn lịch sử

Đã tải **3 HTML metadata + 4 PDF**, giữ byte gốc cùng headers/URL đầu-cuối,
size/SHA-256 và UTC thực tế. Thời điểm truy cập từ **2026-10-16T14:32:59Z đến
2026-10-16T14:33:07Z** (đầy đủ microsecond ở evidence.jsonl). Đây là lần tải mới,
không phải retrieved_at lịch sử của bốn DOCX.

| Văn bản | Trang chính thức / tệp đã lưu | Trang PDF / SHA-256 PDF |
|---|---|---|
| L36 | [Metadata Chính phủ](https://vanban.chinhphu.vn/?pageid=27160&docid=211194); [Công báo phần đầu](https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/9/36-2024-qh15.pdf), 02/snapshot.pdf | 21; e83b092fd1e93a63d3082424bd63e7ad99afcf39ba3729f6d82ce19fe8b33690 |
| L36 | [Công báo phần tiếp](https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/9/36-2024-qh15_tiep.pdf), 03/snapshot.pdf | 61; 55ba152f3abe925d9a75418c3e61bc0122824db41a0d2352053dbff2c6264f8c |
| NĐ168 | [Metadata Chính phủ](https://vanban.chinhphu.vn/?pageid=27160&docid=212167); [PDF ký số](https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/01/168-nd-cp.signed.pdf), 05/snapshot.pdf | 111; 7bb11b939d162499ab404aa41a940cce05dbf071d9cbae7a8898b00d4b4a48bd |
| L35 | [Metadata Chính phủ](https://vanban.chinhphu.vn/?pageid=27160&docid=211193); [Công báo](https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/9/35-2024-qh15.pdf), 07/snapshot.pdf | 69; debf33ad3b4781c04c143b3b684aaace3e4ecc24110d87ca551ab1cd0221c9fc |

Trong capture có **262 trang**, **112 trang không lấy được text**: 111 trang
NĐ168 và một trang phần đầu L36. Flag needs_ocr nghĩa không có text để đọc bằng
công cụ, cần phân biệt scan/trang trống; không khẳng định mọi trang đều có chữ
cần OCR. Không thực hiện OCR, không kiểm chữ ký số. NĐ168 được xem trực quan ở
năm trang được trích, không giả offsets chữ trên ảnh hoặc tuyên bố đọc cả 111 trang.

PDF Công báo L36 có header số 977+978/979+980 ngày 24-8-2024; L35 số 983+984
ngày 25-8-2024. Điều này là căn cứ nhận diện bản ứng viên ban hành, chưa chứng
minh DOCX tương đương, đủ phần hay toàn bộ sửa đổi trước/tại snapshot. Trạng thái
hiện tại trên trang metadata không được dùng thay lịch sử. Chưa dùng bản hợp
nhất năm 2026 để suy ngược luật tại 2025-01-01. Hồ sơ evidence/historical đều pending.

## Bảng pilot và kết quả quan sát

| Nhóm | Unit | Đề xuất máy / điều cần rà |
|---|---:|---|
| A: L36 Điều 22 + K1–3 | 4 | included ứng viên; giữ nguyên dẫn và đủ ba Khoản. PDF phần đầu trang 19 (trang in 94) có đoạn tương ứng; hiệu lực chung ứng viên 2025-01-01, chưa quyết định. |
| B: NĐ168 A6K1 + a/b/c/d/đ | 6 | included ứng viên; mức tiền dẫn của Khoản không sao chép vào own text Điểm. Trang ảnh 8 có các phần tương ứng; cần rà dẫn chiếu/ngoại lệ và lịch sử. |
| C: L36 A10K3 | 1 | included ứng viên về scope; **not_yet_effective ứng viên**, effective_from=2026-01-01 theo A88K2, không áp ngày chung 2025-01-01 cho đơn vị này. |
| D1: NĐ168 A16K2 + a/b/c giữ lại | 4 | Cha thiếu con, hai p[518–519] chưa có unit; các con giữ own text, có dependency context riêng. Trang ảnh 41 thấy d), đ), khác hai đ) trong DOCX. |
| D2: NĐ168 A39K9 + bốn Điểm đang có | 5 | Điểm đ hiện còn unit/span và warning; trang ảnh 85 thấy d). Không tự khẳng định mất một con hoặc đổi ID. |
| D3: NĐ168 A40K3 + a/b/c giữ lại | 4 | Scope chờ rà; cha thiếu ba vùng p[1057–1059]. Trang ảnh 86 thấy d), đ), e) ở các vị trí DOCX đ), đ), c). |
| E: L35 A84K1/K2 | 2 | Scope chờ rà; own content chưa đủ vì hai bảng chưa phân tích. Công báo trang 67 (trang in 69) có bảng. K1 có ngày ứng viên **2024-10-01** theo A85K2, K2 ngày chung ứng viên 2025-01-01. |
| F: L35 A5K3/K4, A12K1 | 3 | excluded **đề xuất máy** theo phạm vi quy hoạch/quỹ đất/hạ tầng BRD §3.3; không đồng nghĩa hết hiệu lực hoặc quyết định loại đã có người duyệt. |
| G: Điểm neo hiệu lực/chuyển tiếp | 11 | supporting ứng viên: L36 A88K1/K2, A89K1; L35 A85K1/K2, A86K1/K2; NĐ168 A53K1/K2, A54K1/K2. Chưa đủ để nói đã rà toàn bộ ngoại lệ/chuyển tiếp. |
| Tổng | **40** | Chỉ pilot, không mở rộng 4.000 unit. |

Thống kê scope của **máy**: included 20, supporting 11, excluded 3, chưa đề xuất
6. Scope **quyết định thực tế**: 0; cả 40 scope_status=null. Applicability thực
tế: cả 40 pending_review. Kỹ thuật: 12 needs_review, 28 chưa quan sát lỗi trực
tiếp trong pilot; số 28 không có nghĩa nguồn/cây hay nội dung đã verified.

Các quan sát d/đ/e từ PDF là **máy đối chiếu trực quan**, có URL/hash/page/PNG,
không ghi người dùng/nhóm đã duyệt. Cần reviewer kiểm và mở nhiệm vụ sửa có
phiên bản mới nếu chấp thuận. Raw và cây Stage 4 vẫn giữ nguyên ký hiệu cũ.

Tác động được tách: unit còn trong cây có warning; cha thiếu một số con; vùng
extraction không có unit; own content/context phụ thuộc bảng/vùng chưa xử lý.
Sáu link context cho các Điểm giữ lại được liệt kê riêng trong config theo ID,
vùng và lý do cụ thể. Chỉ chặn việc dùng context chưa rà, không kết luận own
text bị thiếu hoặc tự chặn target từ trạng thái cha. Không khai báo link thì
không tự truyền cảnh báo xuống con; cổng upstream vẫn chặn phục vụ toàn pilot.
Vùng p[933] không được gán vào A86K2 hoặc phát tán lỗi sang mọi đơn vị Luật 35.
Giữ đủ 10 issue/13 warning ở input snapshot; 9 region không phải chín issue mới.

## Lệnh thực tế và kết quả

Môi trường `.venv-stage1`, Python 3.11.9. Không cài dependency mới. CLI đều có
main guard. Các lệnh chạy từ repo root PowerShell:

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.assessment_evidence capture --requests config/assessment_evidence.v1.json --run-dir staging/stage5a-evidence-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.assessment_evidence validate --manifest staging/stage5a-evidence-001/manifest.json

.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.assessment_pipeline pilot --tree-manifest staging/stage4-docx-005/manifest.json --review-manifest staging/stage4-review-pack-001/manifest.json --evidence-manifest staging/stage5a-evidence-001/manifest.json --run-dir staging/stage5a-pilot-006
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.assessment_pipeline pilot --tree-manifest staging/stage4-docx-005/manifest.json --review-manifest staging/stage4-review-pack-001/manifest.json --evidence-manifest staging/stage5a-evidence-001/manifest.json --run-dir staging/stage5a-pilot-007
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.assessment_pipeline validate --manifest staging/stage5a-pilot-006/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.assessment_pipeline validate --manifest staging/stage5a-pilot-007/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.assessment_pipeline candidates --manifest staging/stage5a-pilot-006/manifest.json --role target
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.assessment_pipeline candidates --manifest staging/stage5a-pilot-006/manifest.json --role context

.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.assessment_pipeline pilot --tree-manifest staging/nonexistent-stage5a-input.json --review-manifest staging/stage4-review-pack-001/manifest.json --evidence-manifest staging/stage5a-evidence-001/manifest.json --run-dir staging/stage5a-missing-must-not-exist
$LASTEXITCODE

.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m pip check
git diff --check
git status --short --untracked-files=all
```

| Kiểm tra | Kết quả thực tế |
|---|---|
| Capture/validate evidence | Exit 0; 7 hồ sơ, pending; original PDF/HTML và text theo trang có hash. Capture cần mạng được cho phép, validate/pilot dùng offline artifacts. |
| Pilot 006/007 và validator riêng từng run | Exit 0, technical_valid=true; legal_verification=not_performed, release_eligible=false. |
| Candidates target/context | Exit 0 khi input hợp lệ, hai danh sách rỗng; không kích hoạt dữ liệu. |
| CLI thiếu manifest input | Exit **1**, báo lỗi thiếu tệp, không tạo staging/stage5a-missing-must-not-exist. |
| Test toàn bộ | **91/91 đạt**, gồm 68 hồi quy Stage 1–4 và 23 test Stage 5A. Log cuối unittest-final.log, kết quả từng lệnh command_results.json. |
| Repeatability | 19 artifact so sánh nguyên byte giống nhau giữa 006/007, gồm toàn bộ JSONL, binding, SQLite và bảng dễ đọc; repeatability.json. built_at/manifest thời điểm chạy không nằm trong mục so bằng byte. |
| SQLite | integrity_check=ok; foreign_key_check rỗng; schema/hàng khớp export, không tạo corpus/legal_unit/unit_assessment chính thức. |
| pip check | Exit 0, No broken requirements found. |
| Git diff check | Exit 0; chỉ có cảnh báo LF/CRLF của working copy, không có lỗi whitespace diff. |
| Bảo toàn | Baseline 738 file: 736 nguyên hash, 2 thay có chủ đích là AGENTS.md/README.md; không mất file. **673 file data/Qdrant/staging cũ giữ nguyên hash**. |

23 test mới dùng fixture SYNTHETIC riêng: binding/unit/hash/version sai, evidence
thiếu/đổi, trạng thái verified không dossier, reviewer/time thiếu, current-page
không thay historical basis, nguyên văn/ngày ngoại lệ, cận trên exclusive,
supersedes, FK/schema sai, báo cáo kỹ thuật tự nhận verified, pending bị chèn
candidate kể cả rehash manifest, pilot không quá giới hạn, tác động riêng từng
vùng và không suy cha–con chung, repeatability, missing-input và import không
network/ghi file/SQLite/model. Live network không chạy trong test suite.

Trong triển khai có hai lỗi fixture/test đã sửa: tên class attribute trùng
unittest.TestCase.run và connection SQLite fixture chưa đóng làm Windows khóa
file khi cleanup. Một lát quote A12K1 ban đầu kết thúc nhầm ở chuỗi trong heading
bị preflight từ chối trước output; đã chốt ranh giới xuống dòng trong config.
Đây không phải kết quả xác minh pháp lý; các lần kiểm cuối nêu trên chạy sau sửa.

## Chưa kiểm tra / chưa đủ điều kiện

- Chưa có reviewer thực tế, quyết định scope/applicability hay duyệt ma trận
  từng đơn vị. Không ghi Hoàng/người dùng/nhóm hoặc timestamp review giả.
- Chưa chứng minh lịch sử sửa đổi đầy đủ đến 2025-01-01, tính tương đương DOCX
  và bản ban hành, toàn bộ điều kiện/chuyển tiếp/dẫn chiếu. A89 L36 slice mới
  lấy một trang, các trang tiếp và quy định liên quan vẫn phải rà.
- Chưa kiểm chữ ký số PDF hoặc xác thực danh tính/thẩm quyền người nộp review.
  Cấu trúc attestation chỉ lưu submission để đối chiếu; không phải hệ thống ký duyệt.
- Chưa OCR; PDF NĐ168 scan chỉ có quan sát trang ảnh. Không chứng minh mọi
  PDF/nguồn thực tế đều được đọc tốt. Không sửa extraction/cây từ các quan sát này.
- Hai bảng L35 còn ngoài legal units; chưa rà đủ văn bản đích của sửa đổi.
  Khoản chứa bảng và context liên quan chưa thể coi đầy đủ.
- Rule chỉ là ứng viên có target ID rõ; không đánh giá ngoại lệ ngoài pilot,
  hiệu lực toàn văn, các lần sửa sau đó hoặc mở rộng sang NĐ165.
- Chưa triển khai đường promote/corpus chính thức, phân quyền ký duyệt hoặc
  phép đưa unit vào serving. Dù decision đúng hình dạng, các cổng upstream/corpus
  của Stage 5A vẫn đóng. Công cụ kiểm kỹ thuật không thay xác minh pháp lý.
- Không thử inference đã bị chặn, không build môi trường sạch lần nữa vì
  không thêm dependency; pip check chỉ xác nhận môi trường đang dùng nhất quán.

## Tự mở và chạy lại

Mở pilot.md → evidence_review.md + PNG/PDF đúng trang → technical_review.md →
pending_work.md. Đọc JSONL nếu cần giữ nguyên newline/TAB và ID đầy đủ; SQLite
chỉ mở readonly. Spans pilot tiếp tục dùng normalized.txt Stage 3 ở input_snapshot;
spans evidence text dùng tệp page-NNN.txt riêng, không trộn hai hệ offsets.

```powershell
Get-Content -Encoding UTF8 staging/stage5a-pilot-006/validation_report.json
Get-Content -Encoding UTF8 staging/stage5a-pilot-006/pilot.md
Get-Content -Encoding UTF8 staging/stage5a-pilot-006/pending_work.md
Get-Content -Encoding UTF8 staging/stage5a-verification-002/preservation.json
```

Để tái tạo SQLite/JSONL, chạy lệnh pilot trên vào **run mới**, ví dụ
staging/assessment-local-001; không dùng lại 006/007, không xóa run để chạy lại.
Dùng evidence manifest đã lưu nếu muốn cùng binding; tải lại URL là capture
mới, có thể khác hash/time/nội dung và không tự bảo đảm replay quote cũ.
Thiếu artifact ignored ở checkout khác thì phải chuyển bundle đầu vào đúng hash
hoặc tái chạy các stage tương ứng, không tạo hồ sơ chính thức giả để đi tắt.

Baseline trước lượt Stage 5A ở staging/stage5a-verification-001/baseline.json;
log/kết quả cuối sau khi siết explicit context links ở stage5a-verification-002.
Không ghi đè các run/log thử đã tạo trước đó.

Git diff thông thường chưa hiện nội dung các file untracked mới; xem status và
mở 11 file mới ở bảng trên. Dừng sau Stage 5A để người dùng xem diff và pilot;
ứng dụng vẫn dùng artifact prototype, chưa dùng assessment/extraction/cây mới.
