# Stage 5A v1.1 — điều chỉnh contract và đối chiếu Điều 22

Ngày thực hiện 2026-10-17; snapshot sản phẩm **2025-01-01**. Dừng sau bước này.
Đã đọc AGENTS, contract/code/schema assessment, BRD, DDD và hồ sơ Stage 2–4.
Không stage/commit, sửa raw/parser, nới schema DDD, tạo chunk/index hoặc phát hành.
Inference WinError 4551 không được thử lại; không cần mô hình cho công việc này.

## Kết quả chính

- Contract/code hiện hành **assessment-pilot.v1.1**; ba chiều scope,
  applicability, technical có thể hoàn thành độc lập. Lịch sử theo
  `(unit_id, dimension)`; không tự chuyển quyết định giữa các chiều.
- Reviewer có thể bác/điều chỉnh proposal với bằng chứng và override_reason;
  validator không bắt ngày bằng ngày máy hoặc bắt chọn rule priority cao nhất.
  Xung đột đề xuất được lưu, lỗi binding/bằng chứng/ngày/trạng thái vẫn bị từ chối.
- Giữ đúng **40 unit pilot cũ**, không thêm unit. Năm unit nhóm NĐ168 A39K9
  đổi đề xuất scope sang excluded theo đối tượng nghiệp vụ, không dùng cảnh báo
  ký hiệu làm lý do phạm vi. Không có quyết định reviewer cho dữ liệu thật.
- Đối chiếu Điều 22 + K1/K2/K3: **5 trường** gồm title, dẫn và ba own text;
  **0 khác biệt nội dung**, **6 khác biệt whitespace/xuống dòng**. Spans tái dựng
  nguyên văn chính xác; marker Điều 22. được kiểm riêng ở cả hai nguồn.
- **92/92 test đạt**: 68 hồi quy Stage 1–4 và 24 test assessment. Hai run v1.1
  cho **21 artifact giống nguyên byte**, gồm SQLite/JSONL/bảng đọc được.
- Nguồn/extraction/cây legacy vẫn pending, mọi aggregate_status=pending,
  **0 reviewer event, 0 target/context candidate**, không có corpus mới.

## File thay đổi

| File | Thay đổi |
|---|---|
| src/assessment_contracts.py | Event theo chiều, kiểm bằng chứng riêng, supersedes theo cặp unit/chiều, override proposal, hard date checks tách rule máy, tổng hợp pending và mapping DDD. |
| src/assessment_pipeline.py | review_basis tham chiếu requirements/spans/findings có hash; proposal_conflicts; latest theo chiều; SQLite/JSONL/replay/report cập nhật. |
| src/assessment_evidence.py | Kiểm inventory policy v1.1; thêm đúng hai hostname chính thức VBPL MOJ và Công báo CDN để tải bằng chứng. Không thay quy tắc capture pending. |
| schemas/assessment_v1/pending_schema.sql | Chỉ schema pending: dimension, FK supersedes cùng unit/chiều, ba decision refs và bảng tham chiếu review_basis. |
| schemas/assessment_v1/pending_assessment.schema.json | decision_ids, dimension_complete, technical_review_status và aggregate pending; các cổng serving vẫn false. |
| config/assessment_pilot.v1.json | Policy v1.1, nhóm A39K9 excluded và lý do BRD; giữ nguyên 40 IDs, nhóm khác và links kỹ thuật. |
| tests/test_stage5a.py | Cập nhật kỳ vọng v1.1 và test độc lập từng chiều, override, lịch sử, evidence/binding/date, SQLite/replay và cổng phục vụ. |
| docs/design/data_model_v1/Stage5_Assessment_Contract.md | Contract hiện hành, bỏ ép ngày theo máy và yêu cầu attestation lặp payload/phân quyền trước phát hành. |
| docs/design/data_model_v1/Legacy_DOCX_Content_Comparison_Policy_Proposal.md | Đề xuất riêng về sử dụng đoạn đã đối chiếu; chưa thông qua đường nhập corpus từ nguồn mới. |
| AGENTS.md, README.md | Phạm vi được cho phép, cách dùng v1.1 và giới hạn. |
| docs/reviews/Stage5A_Revision_Verification.md | Báo cáo này. |

Có **10 file đã tồn tại được cập nhật**, **2 tài liệu mới**. Các thay đổi khác
hiện trong Git từ các stage trước giữ nguyên. Venv/cache/database/staging vẫn
được ignore, không tự đưa vào commit. Schema DDD chính thức vẫn SHA-256
`37280458080d308ca5201be78bb1c59d8bcfbc79a424eb833b6efd2de7bff786`.

Các run v1 cũ không đổi byte; v1.1 không tự diễn giải lại event gộp hai chiều
hoặc chấp nhận code hash v1 như run hiện hành. Không có migration ngầm lịch sử.

## Mở artifact

| Đường dẫn | Nội dung |
|---|---|
| staging/stage5a-revision-pilot-002/ | Run v1.1 chính: pilot.md/csv, assessments, review_basis, proposal_conflicts, decisions, SQLite, manifest/report. |
| staging/stage5a-revision-pilot-003/ | Run lặp cùng input/config để kiểm xác định. |
| staging/stage5a-article22-comparison-001/comparison.md | Bảng đối chiếu đầy đủ hai phía và từng khác biệt cho năm trường. |
| staging/stage5a-article22-comparison-001/comparison.jsonl / comparison.csv | Nguyên văn, full diffs, spans/offsets/hash, locator và PDF refs. |
| staging/stage5a-article22-comparison-001/agent_findings.json | Kết luận và độ chắc chắn của agent, không phải reviewer event. |
| staging/stage5a-article22-comparison-001/effectiveness_basis.jsonl | Điều 88 và trọn vùng Điều 89 trên PDF trang 58–61, có locator/quote/hash. |
| staging/stage5a-article22-evidence-001/ | Năm snapshot tải trực tiếp, URL/time/hash/HTTP metadata và text PDF theo trang. |
| staging/stage5a-revision-verification-001/ | Baseline, test/lệnh/log, research_log, browser history extract, repeatability và preservation. |
| staging/stage5a-article22-history-001/run_report.json | Lần tải trực tiếp VBPL thất bại DNS; không coi là capture thành công. |

revision-pilot-001 là run thử trước khi chốt code; giữ nguyên, dùng 002/003 để
kiểm phiên bản hiện hành. Không dùng lại hoặc xóa run cũ để chạy thử.

## Hợp đồng quyết định độc lập và các cổng

Ví dụ synthetic trong test chứng minh scope=excluded được ghi khi hiệu lực và
kỹ thuật còn pending; cũng kiểm applicability hoặc technical hoàn thành trước.
Mỗi event có dimension, unit/hash/binding/snapshot, proposal_id, reviewer/time,
evidence/findings và lý do. Hồ sơ thiếu bằng chứng hoặc sai binding bị từ chối.

Scope dùng căn cứ phạm vi dự án + span nội dung thật. Applicability dùng căn cứ
pháp lý chính thức, lịch sử/ngoại lệ và đối chiếu nội dung. Technical mô tả phạm
vi đã rà và source spans. Không bắt scope phải có ngày hiệu lực/historical_basis.
Không nhận observation_origin=machine hoặc agent analysis làm reviewer event.

Ngày ISO thực, khoảng ngày hợp lệ, effective_to exclusive và status tương ứng
snapshot vẫn bắt buộc. Trái đề xuất máy là proposal_conflict có disposition
reviewer_override, không phải lỗi dữ liệu nếu có hồ sơ hợp lệ. Bằng chứng/lý do
vẫn cần reviewer thực tế xem; test kỹ thuật không chứng minh họ kết luận đúng luật.

dimension_complete là tiến độ review, không phải quyền phục vụ. Kể cả cả ba
chiều hoàn thành, nguồn/extraction/cây chưa được tiếp nhận và corpus chưa tồn
tại nên aggregate vẫn pending, ready_to_load=false và candidates rỗng.
Không tạo hệ thống phân quyền/chữ ký số hoặc bắt chúng làm cổng mới. Reviewer
ref/thời điểm thật theo DDD vẫn được giữ. Không còn bắt attestation lặp payload.

## Scope NĐ168 Điều 39 khoản 9

Đơn vị cha `u_726313465179af0292819fe3b60390042875c66ece7e8a3825cdc80491c4c5f4`.
BRD §3.1 tập trung xử phạt áp dụng trực tiếp cho người tham gia giao thông;
giấy phép sát hạch của cơ sở không đồng nhất GPLX của người lái xe.

| Nội dung từng đơn vị trong nhóm | Đề xuất mới, chưa có reviewer quyết định |
|---|---|
| Khoản 9: dẫn các hình thức xử phạt bổ sung của nhóm dưới | excluded khỏi target sau khi xét nội dung con |
| Điểm a: đình chỉ tuyển sinh cơ sở đào tạo 01–03 tháng | excluded |
| Điểm b: đình chỉ tuyển sinh cơ sở đào tạo 02–04 tháng | excluded |
| Điểm c: tước giấy phép sát hạch của trung tâm 01–03 tháng | excluded |
| Điểm đ theo cây hiện có: tước giấy phép sát hạch của trung tâm 02–04 tháng | excluded; ký hiệu cần rà riêng với PDF |

Chỉ đề xuất supporting khi xác định được đơn vị thuộc phạm vi cần dẫn chiếu
và mục đích context cụ thể. Hiện chưa có nhu cầu đó được ghi nhận cho nhóm,
nên không tự gán supporting. Không sửa d/đ, unit_id hoặc resolve issue.
Scope máy toàn pilot hiện included 15, supporting 11, excluded 8, null 6;
scope quyết định thực tế của cả 40 vẫn null.

## Đối chiếu Điều 22 và ba Khoản

Nguồn DOCX: data/raw/36.2024.QH15.docx, file_id
`963d53d4-d8a4-5074-aa49-2343f914fc80`; hash
`db16c0345afba3b6c2ce68de8223dacd1be752abc01480941f73c8fecf58f617`.
Stage 4 đầu vào vẫn manifest
`ca30426fea4f39e797ffa0e922010cd507cf131b86df76c9174d2a0518e1c938`.

Bằng chứng đối chiếu là [PDF Công báo phần đầu](https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/9/36-2024-qh15.pdf),
snapshot mới 02/snapshot.pdf, PDF trang 19/trang in 94; hash
`e83b092fd1e93a63d3082424bd63e7ad99afcf39ba3729f6d82ce19fe8b33690`.
Lần tải mới `2026-10-17T12:15:08.153174Z`, không thay retrieved_at DOCX.

| Trường | Locator DOCX, word/document.xml | Offset normalized.txt | Kết quả | Số khác biệt |
|---|---|---|---|---:|
| Điều 22 title | B/p[239] | [36246,36282) | exact | 0 |
| Điều 22 own text/đoạn dẫn | B/p[240] | [36283,36435) | whitespace xuống dòng | 1 |
| Khoản 1 | B/p[241] | [36436,36682) | whitespace xuống dòng | 3 |
| Khoản 2 | B/p[242] | [36683,36792) | whitespace xuống dòng | 1 |
| Khoản 3 | B/p[243] | [36793,36896) | whitespace xuống dòng | 1 |

B=/w:document/w:body. Mọi span tái dựng đúng own field theo thứ tự LF DDD.
Không sửa normalized.txt; rule so chỉ gộp whitespace để phân loại định dạng,
không bỏ từ, dấu, số hoặc phủ định. Marker Điều 22. được đối chiếu tách khỏi
field title DDD. comparison.jsonl giữ mọi thao tác replace/insert/delete với
offset và nguyên fragment hai phía; không lược bỏ khác biệt. PDF offsets thuộc
tệp page-019.txt, không phải offsets normalized.txt.

Kết luận agent về **nội dung năm trường**: mức chắc chắn cao cho các lát đã so.
Không suy ra toàn DOCX, các phần khác hoặc provenance đã verified. Ba Khoản
đọc cùng title và đoạn dẫn Điều 22; parent chỉ giữ own text, không sao bản con.
Các nút chapter/document đã có và được kiểm quan hệ; chưa chọn chúng làm
context nội dung bổ sung. Nếu chọn thêm context sau này phải rà phần đó riêng.

## Hiệu lực và lịch sử tại snapshot: căn cứ và giới hạn

[PDF Công báo phần tiếp](https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/9/36-2024-qh15_tiep.pdf),
03/snapshot.pdf, hash
`55ba152f3abe925d9a75418c3e61bc0122824db41a0d2352053dbff2c6264f8c`,
tải mới `2026-10-17T12:15:09.952942Z`:

- Trang 58/in 59, Điều 88 khoản 1: ngày chung 01-01-2025, trừ khoản 2.
- Khoản 2 chỉ nêu Điều 10 khoản 3, ngày 01-01-2026; không nêu Điều 22.
- Đã đọc toàn vùng Điều 89 trên trang 58–61/in 59–62: chuyển tiếp GPLX,
  đào tạo và đấu giá biển số; chưa thấy ngoại lệ riêng Điều 22 trong vùng này.

Tra cứu chính thức đã lưu:

1. [Metadata Luật 36](https://vanban.chinhphu.vn/?pageid=27160&docid=211194),
   capture 01/snapshot.html, đọc trực tiếp ngày 2026-10-17.
2. [Lịch sử VBPL ItemID 170620](https://vbpl.moj.gov.vn/haiduong/Pages/vbpq-lichsu.aspx?ItemID=170620&Keyword=&dvid=250),
   đọc qua công cụ web trong khoảng 12:15:57–12:16:00 UTC ngày 2026-10-17:
   bản trích cached có hai mốc ban hành 27-06-2024 và hiệu lực 01-01-2025.
   Tải trực tiếp thất bại DNS; không lưu giả thành HTTP HTML thành công.
3. [Công báo 193/2026 chứa bản hợp nhất](https://congbaocdn.chinhphu.vn/180507251028987904/2026/4/9/469185-1775546423_v1_1775697063_signed.pdf),
   capture 05/snapshot.pdf, tải 2026-10-17T12:15:16.773333Z, hash
   `e05459f00c88251bf739da75c40a5208272d46e473d14aad72a42f08c06ec140`:
   trang đầu liệt kê sửa đổi bởi Luật 118/2025/QH15, hiệu lực 01-07-2026.
   Chỉ dùng đầu mối lịch sử này; không dùng nội dung hợp nhất thay luật tại 2025.
4. [Metadata Luật 118/2025](https://vanban.chinhphu.vn/?pageid=27160&docid=216534),
   capture 04/snapshot.html, tải 2026-10-17T12:15:16.526718Z: ban hành
   10-12-2025, hiệu lực 01-07-2026, đều sau snapshot.

Các truy vấn, URL, cache/failure và giới hạn nằm ở research_log.json và
history_browser_snapshot.json. Trang VB liên quan chưa truy cập được; không suy
không có văn bản liên quan. Không dựa nhãn còn hiệu lực hiện tại để suy lịch sử.
Một tài liệu tìm trong discovery có số 75-vbhn-vpqh thực tế là luật đường sắt,
đã loại khỏi căn cứ. Chưa lập archive toàn bộ thay đổi pháp luật.

**Kết luận agent:** có căn cứ đề xuất Điều 22 và ba Khoản áp dụng từ 2025-01-01;
chưa tìm thấy sửa đổi trước snapshot tác động trực tiếp Điều 22 trong phạm vi
đã tra. Mức chắc chắn về kết luận lịch sử: **vừa**, do tra cứu phủ định không
toàn diện và một phần dựa cache. Đây là agent analysis, không ghi
verified_at_snapshot hoặc reviewer event vào pilot. Nội dung khớp có mức chắc
chắn cao hơn kết luận đầy đủ về lịch sử/provenance.

## Chính xác những việc còn cần người dùng/nhóm rà soát

| Việc cần ghi nhận thực tế | Đối tượng / lựa chọn |
|---|---|
| Scope nhóm A39K9 | Xem năm đề xuất excluded theo đối tượng cơ sở/trung tâm. Nếu đổi supporting, chỉ rõ đơn vị cần dẫn chiếu và mục đích; không duyệt chỉ vì có chữ GPLX/lái xe. |
| Scope Điều 22 | Ghi riêng cho Điều 22 và K1/K2/K3. Chốt vai trò own lead của Điều và các Khoản; có thể bác proposal included của cha nếu chọn supporting với lý do. |
| Technical review hẹp | Xem comparison.md và PDF trang 19: title, lead, ba Khoản, sáu khác biệt định dạng, spans và context title/lead. Ghi accepted/needs_fix cùng phạm vi đã xem; không nhận cả DOCX đã verified. |
| Applicability của bốn unit | Xem A88/A89 và lịch sử được lưu; chấp nhận hoặc yêu cầu thêm bằng chứng để kết luận tại 2025-01-01, ghi ngoại lệ/giới hạn. Có thể hoàn thành sau scope hoặc để pending. |
| Nguồn legacy và đường tiếp theo | Có log tải gốc đúng DOCX để bổ sung không? Nếu không, chọn giữ staging hoặc xem xét nguồn chính thức mới và mapping hẹp theo đề xuất riêng. Không điền ngày tải PDF cho DOCX. |

Không yêu cầu các việc trên phải do một người hoặc cùng một thời điểm thực
hiện. Chưa có quyết định nào của người dùng/nhóm được ghi. Thiếu log tải không
thể được sửa bằng việc agent xác nhận đoạn văn khớp. Đường chuyển DDD chính
thức vẫn thiếu công đoạn tiếp nhận bằng chứng nguồn/extraction, lựa chọn nguồn
đúng, mapping có rà soát nếu đổi nguồn, corpus draft thật và kiểm FK/manifest.
Đề xuất thiết kế legacy nằm ở tài liệu riêng; chưa âm thầm thực hiện.

## Lệnh đã chạy và kiểm tra

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.assessment_evidence capture --requests staging/stage5a-revision-verification-001/research_requests.json --run-dir staging/stage5a-article22-evidence-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.assessment_evidence capture --requests staging/stage5a-revision-verification-001/history_requests.json --run-dir staging/stage5a-article22-history-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m staging.stage5a-revision-verification-001.build_article22_comparison
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.assessment_pipeline pilot --tree-manifest staging/stage4-docx-005/manifest.json --review-manifest staging/stage4-review-pack-001/manifest.json --evidence-manifest staging/stage5a-evidence-001/manifest.json --run-dir staging/stage5a-revision-pilot-002
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.assessment_pipeline pilot --tree-manifest staging/stage4-docx-005/manifest.json --review-manifest staging/stage4-review-pack-001/manifest.json --evidence-manifest staging/stage5a-evidence-001/manifest.json --run-dir staging/stage5a-revision-pilot-003
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.assessment_pipeline validate --manifest staging/stage5a-revision-pilot-002/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.assessment_pipeline validate --manifest staging/stage5a-revision-pilot-003/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.assessment_pipeline candidates --manifest staging/stage5a-revision-pilot-002/manifest.json --role target
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.assessment_pipeline candidates --manifest staging/stage5a-revision-pilot-002/manifest.json --role context
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m pip check
git diff --check
git status --short --untracked-files=all
```

| Kiểm tra | Kết quả thực tế |
|---|---|
| Test toàn bộ | **92 đạt**, 0 lỗi; unittest-all.log. |
| Độc lập các chiều | Scope, applicability hoặc technical có thể hoàn thành trước; hai chiều còn lại pending. |
| Override | Scope khác proposal và ngày 2025 khác đề xuất 2026 được chấp nhận khi có hồ sơ synthetic đúng; thiếu lý do/bằng chứng bị từ chối. |
| Binding/ngày/lịch sử | Sai unit/hash/snapshot, ngày không hợp lệ, status trái khoảng, supersedes chéo chiều/fork đều bị từ chối. |
| Integration submission | Synthetic scope-only event được replay và nạp SQLite, app/technical pending; bản gốc submission giữ byte, run tham chiếu không đổi, FK đạt. |
| Cổng phục vụ | Một hoặc cả ba chiều hoàn thành không tự mở cổng; candidates thật rỗng, rehash/chèn candidate vẫn bị validator chặn. |
| Capture chính thức | Exit 0, năm snapshot có hash/time thật; capture lịch sử trực tiếp exit 1 DNS, giới hạn được ghi riêng. |
| Pilot/validator 002 và 003 | Exit 0, technical_valid=true, release_eligible=false; 40 unit giống danh sách cũ, không reviewer event. |
| Repeatability | 21 artifact semantic/SQLite/bảng giống byte giữa 002/003; built_at/manifest giờ chạy không so bằng byte. |
| Missing input | CLI exit 1, không tạo run staging/revision-missing-must-not-exist. |
| pip / diff | pip check exit 0; git diff --check exit 0, chỉ cảnh báo LF/CRLF working copy. |
| Bảo toàn | Baseline 3.868 file: 3.858 giữ hash, 10 file nguồn/tài liệu cập nhật có chủ đích, không mất file. Toàn bộ **3.792 file data/Qdrant/staging cũ giữ nguyên hash**; không stage file nào. |

Không kiểm lại môi trường sạch vì không thêm dependency; pip check chỉ nói môi
trường hiện dùng nhất quán. Không kiểm chữ ký số hoặc xây phân quyền; đây là
giới hạn chưa thực hiện, không phải tiêu chí bắt buộc mới. Không có bài kiểm
kỹ thuật nào thay quyết định xác minh pháp lý. Không OCR hoặc triển khai parser PDF.

Để tự kiểm lại, chạy validate/candidates và unittest ở trên. Muốn tái tạo SQLite,
chạy pilot cùng input vào run **chưa tồn tại**, ví dụ staging/revision-local-001;
không xóa/ghi đè run cũ. Bảng comparison.md/csv/jsonl giữ đủ nội dung và diff
để mở độc lập; script xuất một lần được lưu cùng artifact, không phải CLI/parser mới.
Các file untracked không hiện trong git diff thông thường: mở thêm file theo
status. Chứng cứ bảo toàn byte và danh sách thay đổi ở preservation.json và
workspace_delta.json trong verification run; không stage/commit.
