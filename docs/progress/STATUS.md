# Hiện tại — phiên 8 phản hồi calibration subset v5, 2026-11-04

**USER_REVIEWED_AI_ASSISTED / AWAITING_REVIEWER_METADATA / ACCEPTED_IMPORT_NOT_RUN**.
Snapshot **2025-01-01**. HEAD đầu phiên **f75ab698aa1dd3e8acb97d946916c55c8dc7e0b8**,
Git sạch. Phản hồi người dùng xác nhận đã đọc lại, ChatGPT hỗ trợ đề xuất/diễn đạt;
**không phải chấm độc lập hoặc blind**. Chỉ22cặp, không duyệt500nhãn/coverage50query,
chất lượng dataset hoặc hiệu lực nguồn. Gói blind/proposal/template cũ bất biến.

- Response mới **staging/subset-v5-calibration-submission-001/**, checks
  **source-session8-checks-001/**.22ID đủ/không trùng; relevance/reason nguyên văn.
- Nhãn **2/1/0/null =7/6/7/2**.7nhãn2 có1full/6partial;6nhãn1 có2supporting và
  4dependency-only. Hai null là quyết định giữpending, không đổi0.
- **Bất đồng CAL-b69c61257d: proposal2 → response null**; giữ nguyên phản hồi và
  lịch sử. CAL-a46415f601 vẫnnull.21bộ nhãn/quan hệ/mức đầy đủ giống,1khác;
  không báo inter-annotator agreement vì AI hỗ trợ.
- Nội dung/binding/evidence/enum đạt; CLI **exit2 đúng dự kiến**, thiếu chính xác
  **reviewer_ref, reviewed_at**. Đểnull, không dùng tên Git/Windows/giờ chạy thay.
  Provenance chỉ ghi agent_recorded_at thực tế; accepted imported0, metrics=null.
- **46tests pass/0skip,21private mutations bị từ chối**. Existing review validator
  exit0; filled-copy reader riêng, không nới blank-template validator hash-bound.

Cần người dùng cung cấp tên/mã reviewer và thời điểm rà thực tế kèm múi giờ,
sau đó tạo snapshot mới và kiểm đường nhập typed labels. Hai null vẫnpending;
20nhãn số chưa được nhập. Không dùng scorer v1 chunk-only thay table/whole v5.
Raw/dataset/index/query/evaluation/qrels/ZIP/run cũ giữ nguyên; không tuning,
rebuild/model/embedding/UI/API hoặc stage/commit/push.

[Báo cáo phiên8](../reviews/Source_Session8_Calibration_Verification.md),
[contract response](../design/Subset_V5_Calibration_Submission_v1.0.md).
Lịch sử phía dưới giữ nguyên bytes; CALIBRATION_PENDING trong mục cũ là trạng
thái tại thời điểm phiên7, không phủ nhận phản hồi mới đã nhận.

---

## Lịch sử phiên 7 (giữ nguyên)

# Hiện tại — phiên 7 relevance subset v5, 2026-10-31

**AGENT_REVIEW_PROPOSALS_READY / CALIBRATION_PENDING / METRICS_NULL**.
Snapshot **2025-01-01**. HEAD đầu phiên **4144437306340901c62a27c04850480c5b5bcd17**,
Git sạch. Giữ nguyên index003/batch002/candidate006/query set; không rebuild/tuning,
đổi tokenizer/ranking, sửa ứng dụng, stage/commit/push hoặc chuyển bản nhóm.

- Main **staging/subset-v5-relevance-002/**, replay003; companion
  **subset-v5-relevance-handoff-001/**; checks **subset-v5-relevance-checks-001/**.
- Đọc/rà **500cặp/50query**, re-read117detail Top10 bằng consumer và inventory
 138target/238supporting. Có **495proposed +5pending/null**; nhãn2/1/0/null
  **38/54/403/5**, gồm8dependency-only trong Top10. Không kế thừa nhãn v1/v3.
- Chọn **15query trước tìm sâu**, dùng câu gốc Top138: **1.980cặp retrieved**,
  chỉ **11positive ngoài Top10** được đọc/gán proposal (6query/7record).
  Tổng118detail dùng trong nhãn; không gọi toàn deep pool đã được chấm.
- Coverage đề xuất50query: **17đủ nội dung /19partial-conditional /2mơ hồ /
  3chưa có target phù hợp /9ngoài membership hoặc blocked**, theo inventory đã rà.
  Không suy scope excluded hoặc toàn raw thiếu từ gap subset.
- Calibration **10query/22cặp** có nguyên văn/context/dependency/proof,
  ẩn rank/score/nhãn agent, crosswalk riêng, template reviewer/time/labels trống.
  Mở calibration.md trước proposal; điền bản sao ngoài seal, không sửa bundle.
- **35tests đạt/0skip;15negative bị từ chối**, CLI validate đạt; replay payload/
  nhãn/evidence/calibration/deep ranking giống, chỉ receipt build time khác.
- **Portability backlog riêng:** index inventory native Path sort khác Windows/
  POSIX dù cùng file/hash (đã mô phỏng PureWindowsPath/PurePosixPath, chưa Linux).
  CPython minor/Unicode/pins là ràng buộc khác. Không sửa code/index để bypass.
  Dataset consumer POSIX sort riêng; Linux full-read là thông tin người dùng
  cung cấp, chưa có thực nghiệm Linux của agent trong phiên này.

Qrels accepted rỗng, metrics=null, human events0; source/edition/applicability
pending, scope proposal. Không dùng thống kê nhãn/tests làm xác minh pháp lý hoặc
kết luận chất lượng retrieval. Raw/dataset/index/evaluation/qrels/ZIP/run cũ giữ
nguyên; các mục lịch sử dưới đây không được viết lại.

[Báo cáo phiên7](../reviews/Source_Session7_Relevance_Verification.md),
[hướng dẫn calibration/replay](../handoff/Subset_V5_Relevance_Calibration.md),
[rubric v1.2](../design/Subset_V5_Relevance_Review_v1.2.md).
Việc tiếp theo cần nhóm evaluation xem:5null, điều kiện/loại xe, dependency-only,
phản hồi mẫu thực tế và completeness nhãn; chưa tự accepted hoặc tính metrics.

---

## Lịch sử phiên 6 (giữ nguyên; giới hạn portability được ghi thêm ở phiên7)

# Hiện tại — phiên 6 BM25 subset v5, 2026-10-31

**BM25_BUILT_BATCH_READ_AND_PORTABLE_VERIFIED / EXPERIMENTAL / PENDING_LABELS**.
Snapshot **2025-01-01**. HEAD đầu phiên **441efbea1fbecc9a0d61e6c3962661862beb74ec**,
Git sạch. Không stage/commit/push/merge hoặc chuyển phiên bản cho nhóm.

- Dataset **vtls-subset-experimental.v5-candidate.1**, candidate006/ZIPv5-002
  giữ nguyên. Index mới **vtls-bm25s-subset.v1**, main
  `staging/bm25-subset-v5-003/`, replay004; không dùng candidate-v4/v3 thay thế.
- **138document =125chunk+9table-row+4whole-source**, một target/document,
  giữ ID/type/full search text. Không index238supporting, XXVI,30structural nodes
  hoặc6encoder views độc lập;7nguồn inventory/6nguồn có target, NĐ165 target0.
- Tái dùng BM25S0.3.13 Lucene/k1=1.2/b=.75/lexical v1, NumPy2.4.6/SciPy1.17.1.
  Không tuning/preprocessing/model mới. Source/type/law filter trước Top-k,
  stable score-desc/record-ID-asc; empty sai input, OOV trả[], không pad/fallback.
- **50query ghim (30old+15new+5limit) →500hit,117unique details**,220supporting
  units+XXVI trong hit pool. Full-read riêng **138target/238supporting/XXVI**.
  Read giữ nguyên context/proof/required_read/proposal/pending. Metrics **null**,
  eligible0/PENDING_LABELS, không chuyển qrels v1/v3 hoặc ghi human decisions.
- **42test pass/4skip** (46 chạy),12private mutation và9input error bị từ chối;
  103payload/manifest replay giống byte, ZIP replay cùng SHA. Core checks002;
  final report `staging/source-session6-portable-003/validation_report.json`.
- ZIP giải nén +venv sạch cài3pins offline từwheel cache,5CLI exit0,
  rebatch/read117hit/full-read138, ranking/response hashes giống main/replay.
  Audit4deny probes đúng/0unexpected/0foreign module; chỉ cho os.devnull ngoài
  root, chặn network/subprocess. Cùng Windows/CPython3.11.9, chưa máy/OS khác.
- ZIP giao **staging/vtls-bm25s-subset-v1-002.zip**,19.212.146byte,
  SHA **ddf9e5c2f90439ea5b057792a609ea05e99e43e223bf64e327c2ff492023a759**
  +.sha256. Không dùng ZIP001/index001/002 development; các lần thử giữ lịch sử.

Source/edition/applicability pending, scope proposal, release=false/corpus=null.
Không gọi lexical hits/technical tests là legal verification hoặc chất lượng
retrieval. Dataset3077/draft3082/v3/v4/v5,index/evaluation/qrels/ZIP nhóm dùng
bất biến. Chưa UI/API/merge Hùng, Dense/embedding/Qdrant hoặc yêu cầu đổi bản.

[Báo cáo phiên6](../reviews/Source_Session6_BM25_Verification.md),
[Quickstart search→read](../handoff/Source_Session6_BM25_Quickstart.md),
[Replay](../handoff/Source_Session6_Replay.md),
[contract](../design/Source_Session6_BM25_Contract_v1.0.md).
Bước sau: nhóm rà nhãn v5 có bằng chứng trước metrics; tích hợp typed consumer
khi được giao, giữ notices/pending và required-read. Không tự chạy tiếp.

---

## Lịch sử phiên 5 (giữ nguyên; index subset riêng đã được tạo ở phiên6)

# Hiện tại — phiên 5 subset candidate portable, 2026-10-30

**PACKAGED_AND_FULL_PORTABLE_READ_VERIFIED / EXPERIMENTAL_CANDIDATE / LEGAL_REVIEW_PENDING**.
Snapshot **2025-01-01**. HEAD đầu phiên `c759aa496cb560a984b76a599305d863d9c117d8`;
Git đã có review Hùng chưa commit, giữ nguyên. Không stage/commit/push/merge.

Đã đóng gói **vtls-subset-experimental.v5-candidate.1** từ đúng plan phiên4,
không còn chỉ là packaging plan. Main `staging/dataset-v5-subset-006/`, replay007;
checks `staging/source-session5-checks-002/`. Bản giao là
`staging/vtls-subset-experimental-v5-candidate1-002.zip` + `.sha256`,19.038.752byte,
SHA **b1965b3df6373a068a328a8200a9a01d8345e16e73c79e675575a3b7c57fa822**.
Các bản thử/ZIP trước đó giữ lịch sử, không phải bản giao cuối.

- **138 target** giữ nguyên ID/type/payload/search/context theo plan:
  **125chunk +9table-row +4whole-source**. Có22NĐ168 đúng DOCX hiệu chỉnh phiên2,
  source/spans/lineage mới; không chuyển qrels/assessment từ nhánh cũ.
- **132 target unit IDs** =129DDD+3QCVN-reader-region; **238unique supporting
  unit reads +1formXXVI**,35unit trùng vai trò. Union335selected IDs; graph
  **365node** gồm346unit.v1+19qg_ và30ancestor structural_only. **542DDD spans**,
  embedded QCVN proofs,33unique cells và23field nguồn củaXXVI giữ đủ.
- **6encoder views** gắn4whole records, không tăng target. Không tokenize/model/
  truncate lại. Runtime có typed consumer, required-read, graph Part/Chapter,
  source resolver/mount, cells/header và form layout; không fallback workspace.
- **7nguồn inventory /6nguồn có target-supporting**. NĐ165 target0/support0/
  graph0/raw0, không đóng gói ngầm. Đây không phải full coverage bảy nguồn.
- Không nhận5A16K2 unresolved, A28K2/XXIII/sáuprogramme tables hoặc QCVN caption
  xung đột/recovery/OCR inventory. Raw/text đầy đủ có vùng ngoài subset để giữ
  source hash, không đồng nghĩa admission. XXVI payload scope=included lịch sử
  giữ nguyên nhưng membership role=supporting, không thành target.

**35tests pass,20negative bị từ chối**,71payload/manifest replay giống byte,ZIP
replay cùng SHA. Từ ZIP giải nén khác build root: venv sạch CPython3.11.9,
distributions=[], chỉ stdlib;7CLI exit0 (validate/list/4read/full-read), đọc đủ
**138responses/238supporting/XXVI**. Audit cấm repo/staging/dev venv/cache gốc,
4denial probes đúng/0unexpected, không foreign module. Chỉ cùng Windows/máy này,
không gọi là kiểm máy khác hoặc benchmark. Baseline4023file giữ nguyên ngoài
STATUS/ingestion được phép prepend lịch sử; review Hùng nguyên bytes.

Source/edition/applicability pending, scope proposal, human_review=null,
release=false/corpus_version=null. Word layout DOCX chưa kiểm; technical pass
không legal verification. Dataset3077/draft3082/v3/v4/index/evaluation/qrels/ZIP
cũ bất biến; chưa build index/embedding, chạy evaluation hoặc đổi ứng dụng/nhóm.

[Báo cáo phiên5](../reviews/Source_Session5_Verification.md),
[Quickstart ZIP và replay](../handoff/Source_Session5_Replay.md),
[contract](../design/Source_Session5_Candidate_Contract_v1.0.md).
Bước sau có thể tích hợp experimental riêng theo typed consumer/capabilities
khi được giao; chưa tự thay artifact nhóm dùng hoặc merge hung-feature.

---

## Lịch sử phiên 4 (giữ nguyên; plan138 đã được đóng gói ở phiên5)

# Hiện tại — phiên 4 record preparation, 2026-10-29

**PREVIEW_AND_PLAN_ONLY / TECHNICAL_SUBSET_IDENTIFIED / LEGAL_REVIEW_PENDING**.
Snapshot **2025-01-01**. HEAD đầu phiên `f63d4b629f4b5e44e46f8200a52986cada59cfc4`,
Git sạch; có code/config/tests/docs mới chưa commit. Không stage/commit/push.

Nguồn/proposal ghim **source-session3-proposal-009** và config/hash thật, không
chọn latest, không sửa DOCX session2 hoặc chạy lại corrections/parser toàn nguồn.
Run chính **source-session4-preview-007**, replay008; checks002. Run development
trước đó giữ lịch sử, không dùng thay run chính.

- **27 record NĐ168 cũ / 27 unit khác nhau → 22 chunk mới ready, 5 blocked**.
  Năm A16K2 a/b/c/d/đ có scope unresolved trên nguồn DOCX run009; không nhận
  scope từ HTML. 22 record được dựng lại từ graph/extraction mới, đủ own text,
  context, exceptions/modifiers/required-read và proof mới. Identity đổi đúng
  unit_id + contexts; không chuyển assessment/qrels/offsets. Token **88–239**,
  unknown0, không truncate hoặc đổi budget256. A12K12/NĐ165/Luật36 chỉ probe
  dependency, không tự thêm target ngoài27seed.
- **Mẫu XXIII ready kỹ thuật**: đúng PDF phụ lục **127**,18dòng native/0bảng vật
  lý, đủ nhãn/trường trống/hướng dẫn/ký, bbox/spans. Xem cả126/128 để chốt ranh
  giới XXII/XXIV, không nhầm XI/XXVI. Không điền giá trị giả hoặc tạo chunk từ mẫu.
- **A28K2 còn blocked**, dù target kỹ thuật/mẫu/sáu course owners đã có. A7 dùng
  **Phụ lục II**. Đã đưa18completion units A6K4/A7K4–5/A8K4–5 vào hồ sơ; A7K4d/
  A8K4d yêu cầu chấm thi XV/XVI/XVII ở PDF48–96 (**49trang**) chưa đủ kiểm layout/
  nội dung/whole-read. A21K4c/A46K2 không thành target. Không gọi ảnh/native là đã
  hoàn thiện closure.
- Đã kiểm thực tế **116 record phiên3** (103chunk/9table-row/4whole-source),
  giữ payload/ID. Packaging plan **138target =125chunk+9row+4whole-source**,
  **132unit pháp lý**, chỉ thêm22NĐ. Closure có **238supporting unit reads +
  1formXXVI**;35supporting units cũng là target ở record khác, không cộng số
  record thành số unit. Không lấy toàn supporting_only trong inventory.
- **Chưa tạo dataset**. Tập138 đủ kỹ thuật để giao phiên packaging experimental
  riêng cùng đúng closure/capability/source assets; source/edition/applicability
  pending, scope proposal, human_review=null, release=false. Không nhận nămA16/
  A28 hoặc chuẩn hóa gộp QCVN I.418/I.416 vì technical preview chạy được.

27test pass; suite builder/circular46collected/39pass/7skip (opt-in pilot manifest
chưa truyền). Checker19negative từ chối,58payload replay giống byte. Năm typed
read-probe đọc được trên bản sao, audit hook cấm workspace gốc; chỉ cùng Windows,
chưa máy khác/chưa package toàn138. Baseline3488file kiểm hash, ngoài hai tài liệu
STATUS/ingestion được phép prepend lịch sử nguyên byte. Không dùng các số này
thay xác minh pháp lý hoặc chất lượng retrieval.

Word retry private/ẩn/read-only-copy vẫn lỗi COM logon session; chưa render/kiểm
bố cục. Raw/run cũ/dataset3077/draft3082/v3/v4/index/evaluation/qrels/ZIP giữ nguyên.
Không chạy embedding/inference/index/app hoặc mở rộng5013unresolved/QCVN OCR.

[Báo cáo phiên4](../reviews/Source_Session4_Verification.md),
[handoff và lệnh](../handoff/Source_Session4_Replay.md),
[contract additive](../design/Source_Session4_Record_Preparation_v1.0.md).
Bảng đủ27ca, form review và packaging plan dễ đọc tại
`staging/source-session4-checks-002/`. Dừng sau preview/plan; chưa yêu cầu nhóm
chuyển phiên bản.

---

## Lịch sử phiên 3 (giữ nguyên; mẫu XXIII đã xử lý, closure A28 còn thiếu ở trên)

# Hiện tại — phiên 3 source selection / membership, 2026-10-28

**PROPOSAL_ONLY / SOURCE_SELECTED / SCOPE_REVIEW_PARTIAL**. Snapshot **2025-01-01**.
HEAD đầu phiên `2afb65c3f955d149da5a3b25f17c0436d1dcb792`, Git sạch; hiện có code/
config/tests/docs mới chưa commit. Không stage/commit/push hoặc tạo dataset/index.

Lựa chọn nguồn từ chỉ dẫn người dùng, không là human review/verified: Luật36,
Luật35/QH15,NĐ165 dùng DOCX; NĐ168 dùng **nd168-docx-session2-001**, không áp lại
corrections; TT38 chọn **Công báo8tr SHAe27582e2…**, bản7tr chỉ đối chiếu; TT35
hai PDF/native +graphPart/Chapter; QCVN dùng Công báo theo vùng, không thay bằng
Antiword. Full path/hash/file/extraction binding của7nhánh/12file ở
`staging/source-session3-proposal-009/source_selection.jsonl`.

- Inventory **5375node**,128scope review mới/327reuse đúng binding/3subtree cũ.
  **5013scope unresolved** (4917chưa có review unit,96đã xét chưa kết luận), không
  đổi hàng loạt thành excluded. Raw/source/edition/applicability vẫn pending.
- **116record đề xuất để xét packaging**:103chunk,9table-row,4whole-source.
  Chưa build dataset/chuyển bản. NĐ165 có16unit supporting cụ thể cho NĐ168A12K12,
  không loại cả nguồn; nhiều đơn vị ngoài v4 đã được inventory/rà mới.
- NĐ168:1309unit/1351span đúng nguồn mới;1309phase1→2 mapping đầy đủ. Mapping
  Stage4DOCX1304 dùng chuỗi locator qua phiên1; HTMLfull1309 và sparsev3=10 tách
  riêng. Không mang assessment/proof/qrels cũ sang chỉ bằng đổiID. Cần dựng preview
  nguồn mới;27record NĐ168 của v4 đang chờ đổi nguồn/ID, chưa nhận tự động.
- TT35:8owner có quyết định riêng:6supporting choA28K2,2excluded target. **A7K2a
  và PDF8 dẫn AnnexII; mapping AnnexIII phiên2 được đính chính sidecar mới**.
  Một tableID/view-wrapperID đổi do dependency;7record khác/search/token giữ nguyên.
  A28K2 vẫn pending **mẫuXXIII/PDFannex127**, không coi XI/XXVI là thay thế.
- QCVN giữ3text subtree4.1/4.2/6.4, không chọn6recovery region/11dòngB18 thành
  target.929dòng chưa gắn owner giữ pending. I.418/I.416 ngoài membership thống
  nhất;4.1là đính chính lỗi phiên âm agent, không xung đột nguồn.

41tests pass; checker12negative bị từ chối,31payload replay giữ hash. Baseline
3381file nguyên vẹn ngoài STATUS/ingestion được phép; không coi đây là legal/
retrieval quality. Word có trong registry nhưng DispatchEx ẩn/read-only-copy lỗi
logon session(-2147023584), **chưa kiểm bố cục render**. Chỉ Windows hiện tại.
Dataset3077/draft3082/v3/v4/index/evaluation/qrels/ZIP và mọi run cũ giữ nguyên.

[Báo cáo phiên3](../reviews/Source_Session3_Verification.md),
[lệnh replay/validate](../handoff/Source_Session3_Replay.md),
[contract](../design/Source_Session3_Membership_Contract_v1.0.md).
Run009 chính,010replay; checks003 là kiểm cuối sau cập nhật docs. Bước tiếp:
packaging subset116 cùng supporting closure khi được giao; dựng lại previewNĐ168
và xử lý blockers có vị trí, chưa tự tạo corpus/index hoặc human decision.

---

## Lịch sử phiên 2 (giữ nguyên; dependency A7→AnnexIII được đính chính ở trên)

# Hiện tại — phiên 2 NĐ168 / bảng TT35 / QCVN, 2026-10-28

**FIELD_DIFF_CLASSIFIED / EIGHT_TABLE_OWNERS_TECHNICAL_PASS / QCVN_BOUNDED_RECOVERY / LEGAL_REVIEW_PENDING**.
Snapshot **2025-01-01**. HEAD kiểm tra `be7f661109a77dc6c0fb22d72bd6d48ed6ecfc34`,
Git sạch đầu phiên; hiện có code/config/tests/docs mới chưa commit. Không stage/commit/push.

- NĐ168: đủ86field, **67biểu diễn /18nội dung /1HTML boundary**, không phải86lỗi.
  `nd168-field-review-003` giữ hai giá trị/spans/evidence; `nd168-docx-session2-001`
  sửa18paragraph có ảnh PDF, graph1309unit/1351span. Root text đổi kéo theo1309ID
  đổi, có crosswalk; không sửa ID dataset cũ. HTML Điều55 có projection bỏ widget,
  không mặc định HTML luôn đúng. Chưa render DOCX; source/edition/legal vẫn pending.
- TT35: đúng8owner cũ → **8typed table-owner record,11bảng/590ô,84encoder view**,
  max248/256token, unknown0, quarantine0; `tt35-owner-tables-002`. Header/merge/
  continuation/dependency/source proof và whole consumer read được kiểm.
  **Cả8scope vẫn pending**; phụ lục dependency được bảo toàn, chưa full semantic review.
  Chưa phải DDD text chunk/dataset; consumer cũ không tự hỗ trợ type mới.
- QCVN: **đính chính4.1 phiên1: lỗi phiên âm agent, không phải khác biệt hai nguồn**.
  Hai ảnh đều đọc “có, bố trí…”, “cùng ở…”. Đường tránh: nguồn403/PDF300 ghiI.418,
  Công báo part4/PDF36 ghiI.416; giữ source-caption difference/edition pending,
  không alias ID. `qcvn-region-recovery-004`:6vùng/59reader links/1bảng24ô/
  3phiên âm hẹp mới,0text target. Gắn owner có chứng cứ cho11/940dòngB18;
  **929dòng còn pending**. Hình/thông số nhỏ chưa phục hồi đủ nghĩa.

71tests liên quan pass,13negative checks bị từ chối;17payload replay giữ hash.
Baseline **2827file** không có thay đổi ngoài STATUS/ingestion được phép;
không dùng các kiểm tra này thay legal review/retrieval evaluation. Chỉ Windows hiện tại.
Raw/run cũ, dataset3077/draft3082/v3/candidate-v4-006/index/evaluation/qrels/ZIP nguyên vẹn.
Không tạo dataset mới, embedding/index/app hoặc quyết định human reviewer.

[Báo cáo phiên2](../reviews/Source_Session2_Verification.md),
[handoff/lệnh replay](../handoff/Source_Session2_Replay.md),
[quyết định contract additive](../design/Source_Session2_Contract_v1.0.md).
Bước tiếp theo đề xuất: chọn nhánh ND168 có binding/crosswalk, adapter table-owner
có capability cho dataset sau + rà scope/dependency, mở QCVN theo loại vùng đã kiểm.
Chưa tự chuyển bản hoặc mở rộng OCR/verified.

---

## Lịch sử phiên 1 (giữ nguyên; nhận định4.1 đã được đính chính ở trên)

# Hiện tại — phiên1 NĐ168 / DOC QCVN, 2026-10-28

**SCOPED_CORRECTION_PASS / DOC_DIAGNOSTICS_COMPLETE / FULL_SOURCE_REVIEW_PENDING**.
Snapshot2025-01-01. HEAD đầu phiên `e5c3665bf600f5f3d37cc0f588bf4f65a546ebaa`,
Git sạch trước sửa; có code/config/tests/docs mới chưa commit. Không stage/commit/push.

NĐ168: bản dẫn xuất riêng `staging/nd168-docx-corrected-002/`, sửa đúng5chỗ theo
ảnh PDF41/85/86; raw không đổi. Extraction/graph hiện có chạy lại:1.309unit,
1.351span,0parser issue,4source warnings giữ nguyên. Crosswalk1.303ID giữ,
1đổi(A39K9đ→d),5unit khôi phục từ vùng trước cách ly. Chưa render Word.
Đối chiếu HTML đủ1.309path; ngoài vùng sửa còn86field khác ngoài whitespace,
chưa coi DOCX/HTML tương đương toàn văn. Đề xuất HTML là một nhánh text cho
build sau; chưa tự chọn/migrate dữ liệu hoặc nhập trùng hai nhánh.

TT51: reuse5PDF Công báo425tr; capture5DOC còn thiếu từ trang53152 với receipt
thật28/10. `staging/qcvn-doc-assessment-003/` đọc toàn5DOC bằng Antiword0.37:
357.616code point diagnostic,0NUL/U+FFFE/U+FFFD nhưng727`[pic]`;
part4/5 chỉ1.888/534code point, nội dung chủ yếu vẫn là ảnh. Không kết luận DOC
hoàn thiện QCVN. Đã đọc16mẫu theo Điều/annex/sign, không phải full visual review;
DOC diagnostic offsets không là native DOC/PDF spans. Marker Đường tránh ở
nguồn403tr còn cần đọc chắc; câu dẫn4.1 khác Công báo được ghi riêng.

62tests liên quan exit0; replay5payload NĐ168 +20payload DOC giữ hash.
Artifact checker kiểm FK/spans/ID/sequences/reference và baseline2.226file;
không đổi artifact bảo vệ. Chỉ Windows/Python3.11.9 hiện tại, chưa máy/OS khác.
Không dùng số test làm kết luận pháp lý/retrieval. Human events0, release=false.

Dataset/index v1 **3.077**, draft **3.082**, v3/composition index/evaluation/qrels/
ZIP và candidate-v4-006 giữ nguyên. Chưa sửa8bảng TT35, build dataset/index,
embedding/inference/app. Scope/edition/provenance/applicability vẫn pending;
phiên này dừng trước phiên2, không tự yêu cầu nhóm chuyển bản.

[Báo cáo và blocker](../reviews/Source_Revision_Session1_Verification.md),
[lệnh replay](../handoff/Source_Revision_Session1_Replay.md),
[contract bổ sung](../design/Source_Revision_DOC_Assessment_v1.0.md).
Coordinator/evidence: `staging/source-revision-session1-001/`;
kiểm chứng cuối `staging/source-revision-checks-002/`.

---

# Lịch sử — hoàn thiện bảy nguồn, 2026-10-25

**CANDIDATE_TECHNICAL_PASS / FULL_SOURCE_COMPLETION_PENDING**. Snapshot2025-01-01.
Đã nối tiếp việc24/10 và hoàn thiện phần kiểm chứng/đóng gói; **chưa xử lý xong
nội dung/scope/applicability toàn bảy nguồn**. HEAD kiểm tra
`7a60f2d375b981092717b8b24bbc6a0a2037ab75`; worktree có thay đổi chưa commit,
không stage/commit/push.

Candidate riêng `staging/dataset-v4-candidate-006/`,
`vtls-seven-source-experimental.v4-candidate.5`, adapter `seven-source-candidate.v1.3`:
131text +9table +4whole-source +2form =146member, draft/experimental/release=false.
132member giữ nguyên,14added;2.983pending/excluded bỏ membership ở candidate,
không xóa payload v3. NĐ165 chưa có target included, không coi cả văn bản excluded.
Form chỉ layout-read; encoder views phải đọc whole record và required dependencies.

Inventory/ledger009:20file nội dung/1.354 trang PDF (gồm edition/bản đối chiếu),
44.694 interval/6.723 unit-region rows qua các nhánh, không là số luật đã verified.
425tr Công báo QCVN mới không NUL/U+FFFE;203 OCR draft còn lỗi số/ký hiệu và
6.270word confidence<80, không vào target. Graph QCVN003:84Điều/416decimal rules,
9annex headings đọc được;940continuation lines chưa xác định được ranh giới,
không gán vào annex cuối. Chỉ3subtree text đã đối chiếu được chọn.

TT35:248tr,148bảng/5.541ô,44nhóm annex;5/13blocker được gỡ vì bảng nằm ở Điểm
anh em không dùng,8owner bảng còn chặn. 8target Điều34 đủ own text/context và
finite dossier/form/transition dependencies; source-only backlog đã nối lại,
không tạo qrels. NĐ168 HTML có1.309unit/55Điều, typed source spans thật; PDF111tr
scan giữ trạng thái no-text. Công báo Luật35:69tr,2bảng/12ô so DOCX,8khớp/4whitespace.

Kiểm chứng: suite167tests exit0,7skip opt-in; focused mới nhất có16ca. Negative
8ca từ chối đúng lý do. Portable005 validate+5read,006 validate+read trong bản sao
isolated có gate chặn workspace ngoài bundle; runtime/payload146member giữ nguyên.
Cùng Windows/Python3.11.9, chưa máy/OS khác; clean install chỉ dry-run venv đang có.
Baseline2.022file không đổi artifact bảo vệ; tài liệu hiện hành cập nhật riêng.
Dataset/index v1 **3.077**, draft**3.082**/v3, evaluation/qrels/ZIP giữ nguyên.
Không inference/embedding/index mới/activate/đổi ứng dụng. Human events0.

Backlog hợp nhất5.685nhóm,5.626remaining:5.043scope;469page/visual;49nhóm ranh giới
annex;37source region;20source/edition;8owner bảng TT35. Các nhóm có thể cùng vị trí
nhưng khác điều kiện; không phải5.626Điều lỗi. Scope pending là phần agent cần
đọc/rà tiếp, không yêu cầu người dùng phê duyệt mới được phát triển preview.

Tiếp tục từ checkpoint, ưu tiên8owner bảng và scope/dependency của TT35, rồi vùng
QCVN có vị trí cụ thể; chưa nâng OCR draft thành trusted text hoặc ghép dataset.
Nguồn/edition/applicability còn pending, không dùng ngày hiệu lực chung thay kết luận
unit. Chưa có điều kiện gọi hoàn tất toàn nguồn hay chuyển phiên bản cho nhóm.

[Báo cáo/bằng chứng/giới hạn](../reviews/Seven_Source_Completion_Verification.md),
[replay/resume/đọc độc lập](../handoff/Seven_Source_Replay.md),
[contract revision](../design/Seven_Source_Completion_v1.0.md).
Hồ sơ dễ đọc: `staging/seven-source-handoff-001/`; ledger009, candidate006.
Checkpoint: `staging/seven-source-completion-001/checkpoint.json`.

---

# Lịch sử — relevance review composition (2026-10-24)

**AGENT_REVIEW_RECORDED / CALIBRATION_PENDING / METRICS_NULL**.
Snapshot2025-01-01; dataset/index/query/ranking gốc bất biến. Run mới
`staging/composition-relevance-review-001/`, rubric `composition-relevance-review.v1.1`.
Đã xét500cặp/50query,313detail:497proposed (377nhãn0/57nhãn1/63nhãn2),
3pending/null do loại xe chưa rõ;28full/35partial trong nhãn2. Khôngaccepted.

33positive-pairs ngoài pool cho24devquery; thêm1dependency-only cho limitL05,
tổng34pairs/17records.45dev tìm sâu nguyên query Top100,4.500hits chưa chấm
toàn bộ;101record khảo sát citation. Coverage50câu là agent proposal hữu hạn,
không chứng minh hết relevant; unjudged không là0. Source-only/withheld không
thành target qrels.300proposal v1 có binding riêng; không chuyển nhãn cũ.

Validator bundle seal exit0;27tests liên quan đạt.715file input của phiên
giữ hash; baseline962 trước chỉ khác3tài liệu có sẵn, không sai lệch artifact
bảo vệ. Logs `staging/composition-relevance-review-checks-001/`.
Metricsnull/qrelsrỗng/human events0; nguồn/edition/scope/applicability pending.
Dataset/index v1 nhóm dùng3.077, draft3.082/v3, ZIP/evaluation không đổi.

Bước tiếp: rà10query/19cặp trong `calibration.md`, trả bản sao template ngoài
bundle seal. Chấp nhận mẫu không chấp nhận500nhãn/coverage. Scorer accepted
composition có table chưa triển khai; chỉ làm sau khi thực sự có nhãn đủ điều
kiện. Chưa tuning, rebuild, Dense/embedding/index mới hoặc chuyển bản cho nhóm.

[Rubric](../design/Composition_Relevance_Review_v1.1.md),
[hướng dẫn phiếu](../handoff/Composition_Relevance_Review.md),
[bằng chứng và giới hạn](../reviews/Composition_Relevance_Review_Verification.md).

---

# Lịch sử — BM25 composition experimental (2026-10-23)

**INDEX_READY / SEARCH_READ_PASSED / V3_LABELS_PENDING**. Index riêng
`staging/bm25-composition-001/`, version `vtls-bm25s-composition.v1`, bind
nguyên dataset-v3-draft-005 (`vtls-coverage-experimental.v3-draft.1`), snapshot
2025-01-01.3.106text +9table =3.115documents, không index dependency/withheld.
BM25S Lucene/tokenizer/preprocessing/params v1 giữ nguyên; không lọc scope.
Consumer đọc Part/table/source proof và đầy đủ required-read theo IDs/mounts.

Queries đã seal trước ranking:30dev cũ nguyên byte,15dev corpus-derived mới,
5limit. Run `staging/bm25-composition-evaluation-001/`:50query/500Top10,
313detail,0queryerror.500annotations pending,0accepted/qrels, metrics=null.
V1 regression30query khớp ID/score; trênv3 có12Top10 và1Top1 thay đổi, chưa
kết luận retrieval tốt hơn. Query form/QCVN/y tế chi tiết/rain dependency có
coverage observations từ selection/graph, không suy gap chỉ từ Top10.

Index+dataset đã thử copy độc lập, venv mới cài offline đúng bm25s/numpy/scipy,
validate/search/read đạt với audit gate chặn workspace ngoài folder thử.
Cùng Windows/Python3.11.9, chưa OS/máy khác. Dataset validate/read stdlib;
index search cần sparse dependencies. Tests/binding không xác minh pháp lý.

Bản nhóm đang dùng vẫn dataset/index v1 **3.077**, draft3082 và draftv3 giữ
nguyên; evaluation/qrels/ZIP cũ không đổi. Scope/source/edition/applicability
pending/proposed; khônghumanreview, khôngindexactivate/app/Dense/embedding.

[Quickstart](../handoff/Composition_BM25_Quickstart.md),
[verification và hash](../reviews/Composition_BM25_Verification.md),
[contract](../design/Composition_BM25_Contract_v1.0.md).
Bước tiếp: người phụ trách evaluation rà relevance/direct-vs-dependency và
độ phủ nhãn v3; chưa tự chuyển qrels hoặc yêu cầu nhóm đổi phiên bản.

---

# Lịch sử — draft composition TT38/TT35 (2026-10-23)

**EXPERIMENTAL_DRAFT_BUILT / PORTABLE_VALIDATION_PASSED / LEGAL_REVIEW_PENDING**.
Run `staging/dataset-v3-draft-005/`, version
`vtls-coverage-experimental.v3-draft.1`, snapshot2025-01-01, draft/experimental,
release_eligible=false, scope proposed, nguồn/edition/applicability pending.
Không human review. Nhóm vẫn dùng dataset/index v1 **3.077**; draft cũ **3.082**
giữ nguyên, không đổi evaluation/qrels/ZIP hoặc yêu cầu chuyển phiên bản.

Draft mới: **3.106 text chunk +9 table records =3.115 retrieval records**,
5.413 encoder contexts;23 required-read dependency bindings. Delta giữ3082,
thêm24text (8TT38+16TT35) và9table;0replaced/removed/conflicted.13 withheld:
9TT35 thiếu biểu diễn form/reference,1TT38 b279token,3TT51 conditional.
Không nhậpQCVN/572previewTT35, không thay tokenizer/preprocessing/budget256.

Adapter dùng composition components và resolver mounts, giữ payload/ID;
Part/Chapter TT35 và table-retrieval.v1 có contract riêng. Required-read source
subtrees bind chính xác; không ghép thêm vào encoder. Consumer không hỗ trợ
Part/table/dependency phải fail. Validate/read đã thử trong folder độc lập,
venv stdlib sạch trên cùng Windows, audit hook chặn đọc ngầm workspace khác.
Chưa kiểm máy/OS khác. Không index/embedding/retrieval hoặc xác minh pháp lý.

[Báo cáo và lệnh chạy](../reviews/Circular_Dataset_Draft_Verification.md),
[contract](../design/Circular_Dataset_Composition_v1.0.md),
[ingestion guide](../ingestion.md). Bước tiếp nếu được phép: consumer/index
revision, bind version/hash và evaluation phù hợp; chưa triển khai trong phiên.

---

# Lịch sử — ưu tiên TT38/TT35 và pilot QCVN (2026-10-23)

**PRIORITY_PREVIEW_COMPLETE / LEGAL_REVIEW_PENDING / DATASET_ADAPTER_PENDING**.
Snapshot2025-01-01. Dataset/index v1 **3.077** và draft **3.082** giữ riêng,
ba Thông tư chưa nhập; evaluation/qrels/ZIP không đổi. Không stage/commit/push.

Run `staging/circular-priority-006/`:46 dòng rà soát, gồm8 TT38 text,
9 table retrieval records đạt budget,1 Điểm b279 token quarantine,
25 TT35 text đạt71–184 token/2unknown,3 TT51 supporting conditional.
TT35 graph mới783 nodes có7Phần/9Chương thật; crosswalk giữ root,766 unit
đổi ID và16 ancestors mới. Graph/schema pending revision riêng, không sửa
schema DDD v1; adapter dataset hiện hành chưa hỗ trợ Part/table records.
Nguồn/edition/applicability pending, scope chỉ agent proposal.

Pilot `staging/qcvn-pilot-002/` chỉ PDF7/214/300/368: render/reader và phiên âm
hẹp từ ảnh,0QCVNchunk. Font chưa giải mã tự động, không có OCR executable;
214/300/368 vẫn phụ thuộc hình/bảng, không suy ý nghĩa biển từ hình.
Chưa có bằng chứng để mở rộng tự động toànQCVN.13+4 ca TT35 ngoài nhóm ưu
tiên giữ backlog; chưa rà toàn463preview pending hoặc toànannex.

Chi tiết: [verification](../reviews/Circular_Priority_QCVN_Pilot_Verification.md),
[contract v1.2](../design/Circular_Priority_Representation_v1.2.md),
[lệnh chạy](../ingestion.md). Kiểm tra kỹ thuật không xác minh pháp lý/retrieval.
Bước tiếp: adapter draft revision cho graph/table + rà dependency có mục tiêu;
chưa đủ đóng gói bằng adapter v1, chưa yêu cầu nhóm chuyển phiên bản.

---

# Lịch sử — trạng thái dataset và BM25 experimental

**DEV_RUN_COMPLETE / LABELS_PENDING / SHARE_PENDING** — đã thử chạy độc lập trong clone
cục bộ và venv sạch trên máy hiện tại; **chưa có URL chia sẻ** artifact.
Snapshot sản phẩm **2025-01-01**; đây chưa phải corpus phát hành.

**Cập nhật7 nguồn/TT38:** đã đăng ký7 văn bản/10 file pending;4 văn bản trong
dataset/index v1,3 Thông tư chưa được nhập. TT38 có preview riêng, xem bảng
cuối trang và [ingestion guide](../ingestion.md). Các mục trước cập nhật này
được giữ làm lịch sử theo từng lượt.

## Source và binding

Commit đầu lượt draft: `aee22f0173affc406cfccc443a9132c43c1c98fb`.
Đầu lượt đã có thay đổi recovery A16K2 chưa commit (README/STATUS và năm
file config/contract/report/code/test); đã bảo toàn. Lượt này thêm adapter
composition draft, config/contract/tests/report và hướng dẫn. Chưa stage/
commit/push. Dataset/index/evaluation/ZIP bàn giao và các module cũ giữ nguyên.

| Artifact | Giá trị đọc từ manifest thực tế |
|---|---|
| Index | `staging/bm25-baseline-v1-001/index_manifest.json` |
| Index version | `vtls-bm25s-lucene.v1` |
| Dataset gắn trong index | `staging/bm25-baseline-v1-001/dataset/dataset_manifest.json` |
| Dataset version | `vtls-coverage-experimental.v1` |
| Chunk / context | **3.077 / 5.371** |
| Dataset content SHA-256 | `2534731881e493a9b1b47b07470cc5d7f4fabbd9553d4e4d6c59e27359b313b5` |
| Dataset manifest SHA-256 theo index binding | `2aa5dc595dab7614920ce94317b85c7b21e188cc35b16b54bef9e81f3ccf1b0a` |
| Index content SHA-256 | `629f0214096d7ea013039af9253a5ed8f10f273f89da16f8cd56c69ff7130d18` |

ZIP hiện có được tái sử dụng nguyên byte:
`staging/bm25-baseline-v1-001.zip` (33.424.920 byte), SHA-256
`8678cd66620cbacfae7443e9e0774ac36f8294aeb6edceebf1e06cfaa789d03e`.
File `.zip.sha256` cùng thư mục. Gói gồm index (đã chứa dataset) và bản
dataset standalone giống nhau; không chứa venv/cache/lịch sử staging.

## Đã kiểm chứng trong lượt bàn giao

- ZIP có 113 file, hai root đúng phạm vi; từng byte khớp artifact, hash và
  binding dataset/index đạt. Không build lại artifact hoặc sửa dữ liệu.
- Clone cục bộ từ commit base, áp source bàn giao; venv mới chỉ cài
  bm25s 0.3.13, NumPy 2.4.6, SciPy 1.17.1; pip check đạt. Validate toàn
  gói và search không cần staging upstream hoặc model packages.
- CLI validate exit 0: 3.077 document, source/spans/dataset/matrix replay
  đạt; không ghi index. Query vòng xuyến và OOV exit 0. Top-5/điểm/nguyên
  văn/proofs của query mẫu giữ nguyên so với baseline có sẵn.
- Search thử với audit hook cấm đọc phần workspace ngoài clone: đạt;
  không import Torch/SentenceTransformer/Transformers/PyVi/Qdrant.
- Runtime giữ nguyên manifest/config/engine/dependency/Unicode/mapping
  checks. Chỉ bỏ so sánh tuyệt đối Python patch trong cùng CPython minor,
  có cảnh báo và thông tin môi trường tạo/chạy. Chỉ nhận code binding
  hiện hành hoặc fingerprint loader v1 gốc; tokenizer phải khớp chính xác.
- Kiểm thử tập trung: 16 test đạt và một test bổ sung về cảnh báo patch
  đạt. Patch khác được **mô phỏng policy**, không chạy interpreter khác.
  Không lặp suite tốn thời gian toàn pipeline khi thuật toán không đổi.
- Máy thực thử: Windows 10.0.26200, CPython 3.11.9 / Unicode 14.0.0.
  Validate khoảng 23,15 s; query mẫu load khoảng 886,85 ms, search 14,96 ms.
  Số đo đơn lẻ phục vụ bàn giao, không chứng minh p95/hiệu năng toàn hệ thống.

Evidence thực thi: `staging/bm25-handoff-001/` chứa state, execution logs,
package audit, focused tests, isolation/modules và preservation checks.
Hướng dẫn: [BM25 Quickstart](../handoff/BM25_Quickstart.md).

## Pending và giới hạn

Nguồn DOCX legacy chưa rõ lịch sử tải; extraction/cây và technical review
vẫn pending. Scope trong tập kỹ thuật là proposal: 94 included, 64 excluded,
2.919 pending, không phải quyết định reviewer. Applicability chưa xác minh
toàn bộ tại snapshot; bốn ngoại lệ có evidence được giữ ngoài tập. Tổng
46 target deferred (20 quá dài, 13 source/context lỗi, 9 chưa hỗ trợ,
4 ngoại lệ snapshot); source-gap records giữ riêng, có thể chồng lấn.
`experimental=true`, `release_eligible=false`, `corpus_version=null`.

Query còi ban đêm, phân biệt xe máy/chuyên dùng và điểm GPLX còn failure
case. Chưa có qrels được chấp nhận hoặc Recall/MRR/nDCG thực. Số test/validate kỹ thuật không
chứng minh chất lượng pháp lý, nội dung hoặc retrieval đã nghiệm thu.
Chưa kiểm trên máy khác, OS khác, Python patch khác hoặc remote clone
qua mạng; thư mục sạch trên máy này không phải kiểm chứng liên máy.

## Bước tiếp theo

Long/nhóm cần rà query, positive ngoài pool, nhãn và độ đầy đủ theo
[Evaluation Quickstart](../handoff/BM25_Evaluation_Quickstart.md).
Sau đó mới có metrics development; không coi chúng là test cuối.
Dense trên cùng dataset/chunk_id/text_for_search vẫn là bước tiếp theo,
chưa triển khai. Chưa có URL chia sẻ artifact.

## Development evaluation thực chạy

- `staging/bm25-evaluation-dev-001/`: 30 câu/10 intent, mỗi intent có
  direct/paraphrase/scenario; năm câu smoke nghiệp vụ giữ nguyên. Query
  cố định trước ranking, không sửa sau xem kết quả.
- Load index một lần, 30 query thành công, 300 kết quả Top-10, không lỗi.
  Load 1.658,79 ms; tổng search 100,82 ms, tuần tự, không warmup.
  Đây là số đo một lần trên máy hiện tại, không phải SLA.
- Phiếu chứa nguyên văn/context/source spans cho 300 cặp. Submission ở
  `staging/bm25-evaluation-review-001/` có 5 proposal agent, 295 pending,
  **0 accepted**. Không ghi người dùng đã duyệt.
- `staging/bm25-evaluation-labels-001/`: validate/score đạt về cấu trúc;
  0/30 query đủ điều kiện, 30 loại vì rà độ đầy đủ nhãn pending.
  **metrics=null**, chưa có corpus coverage gap được kết luận; cả 30 câu
  cần khảo sát độ đầy đủ. Không nhầm thiếu hit Top-10 với thiếu trong corpus.
- 18 fixture evaluation + 14 regression BM25 đạt (32 tổng). Kiểm công thức
  tính tay, graded/multiple positive, cutoff, nhãn thiếu, lỗi, trùng, binding.
  Không dùng số test làm kết luận pháp lý hoặc chất lượng retrieval.
- Báo cáo: [BM25 Development Evaluation Verification](../reviews/BM25_Development_Evaluation_Verification.md).

## Chín Điều lá — ứng viên phiên bản dữ liệu tiếp theo

Run đề nghị xem: `staging/leaf-articles-preview-002/`, policy
`leaf-article-title-context.v1`. Cả 9 Điều có preview kỹ thuật, 0 blocked,
0 quarantine; token 31–139, unknown=0, budget 256/preprocessing không đổi.
Title chính Điều là heading context; target giữ trọn nội dung riêng, không
lặp body thành context. Source spans và paragraph DOCX được đối chiếu.

Proposal scope hiện có: 7 excluded, 2 pending; không có quyết định mới.
Nguồn/extraction/cây/applicability vẫn pending, release_eligible=false.
9 preview **chưa nhập dataset 3.077 chunk**, chưa thay index hoặc query set.
Không xử lý 20 trường hợp dài hoặc 13 lỗi nguồn/context của tập bàn giao.
Bước evaluation/Dense của nhóm tiếp tục trên dataset đã bàn giao nguyên vẹn.

Chi tiết và kiểm chứng: [Stage6 Leaf Article Verification](../reviews/Stage6_Leaf_Article_Verification.md).

## 13 candidate source/context — đã đối chiếu, chưa cập nhật dataset

Run cuối đề nghị xem: `staging/blocked-source-repair-003/`.
13 candidate → 6 nhóm vùng nguồn; 10 issue parser tại 8 locator, thêm một
paragraph continuation cách ly không có issue riêng. Đã xem tám trang
ảnh từ hai PDF capture cũ; không tải thêm nguồn, không OCR.

- 10 candidate NĐ168: DOCX khác ký hiệu trên PDF scan, không phải parser
  cần nới để nhận literal sai. Giữ deferred; cần nguồn text hoặc cơ chế
  transcription/mapping scan có truy vết trước khi dựng extraction mới.
- 2 Khoản Luật35 có bảng sửa đổi: giữ deferred, chưa triển khai bảng tổng
  quát; scope một pending, một excluded proposal.
- 1 Khoản Luật35 Điều86K2: disposition graphic line rỗng sau thân luật vào
  layout trong projection mới, units/spans giữ nguyên. Preview 77 token,
  unknown=0. Scope excluded proposal giữ nguyên; nguồn/hiệu lực pending.

Kết quả: 1 preview kỹ thuật, 12 deferred trong run riêng. Tập bàn giao vẫn
3.077 chunk; danh sách deferred cũ không bị viết lại. Không tạo reviewer
quyết định, sửa raw/offset cũ hoặc nhập preview vào dữ liệu evaluation.
Chi tiết: [Blocked Source Context Verification](../reviews/Blocked_Source_Context_Verification.md).

## NĐ168 Điều16 Khoản2 — đã khôi phục experimental riêng

Run cuối: `staging/nd168-a16k2-preview-004/`. Đã capture text chính thức
trên Cổng Chính phủ và đối chiếu đủ title/lead/năm Điểm với ảnh scan40–41
đã lưu; không cần phiên âm/OCR. HTML tải 2026-10-22, bài hiển thị2025-04-03;
không coi đó là bản website lịch sử tại snapshot. Applicability vẫn pending.

10 units/10 spans trong cây chọn lọc, 5 Điểm a/b/c/d/đ có preview, 0 quarantine,
0 blocked; token101/143/187/121/212, unknown=0. Hai vùng d/đ trước không có
unit nay có extraction/spans mới; không sửa marker trên DOCX hoặc offsets cũ.
Bảng comparison/crosswalk giải thích đầy đủ ID đổi do identity của cha/field
biểu diễn mới, không do ép phiên bản/source ID vào unit identity.

Scope proposal mới: 5 included targets, title/lead supporting đúng dependency;
không có quyết định reviewer hoặc xác nhận hiệu lực. Chưa nhập dataset3.077,
chưa sửa index/query/evaluation/ZIP. Không mở rộng Điều39/40 hoặc bảng Luật35.
Chi tiết: [ND168 A16K2 Recovery Verification](../reviews/ND168_A16K2_Recovery_Verification.md).

## Bản draft tiếp theo — chưa chuyển bản cho nhóm

`staging/dataset-v2-draft-001/dataset_manifest.json`, version
**vtls-coverage-experimental.v2-draft.1**, policy
`coverage-source-branches-draft.v1`, status=draft:

- 3.082 chunk/5.381 context; **added5, unchanged3.077, replaced0, removed0,
  conflicted0**, duplicate0 sau đối chiếu toàn dataset theo vị trí/nội dung/ID.
- Dataset content SHA: `729bc28b63f773de9d4f5c35c8d77c5f53c5311fa64f7d9c49e8e69496b376be`.
- Manifest SHA: `42c59623d6d921429cd45f2bdfaab3deabab002efa4f13e8720b9645d8944237`.
- Hai component nguồn độc lập giữ nguyên cây/proofs. Cha DOCX (document
  NĐ168 có628 code points own text) không bị own text chưa chọn của HTML đè.
  Metadata graph/membership là sidecar pending, không sửa schema DDD/ID.
- a/b/c trước có unit deferred, chưa có chunk; d/đ chưa có unit/chunk.
  Ba hồ sơ deferred cũ có alternate-source targets trong draft;43 còn lại
  được giữ. Cả46 hồ sơ và issue DOCX gốc vẫn bất biến trong base component.
- Scope của năm target chỉ proposed included; source/edition/technical và
  applicability pending tại2025-01-01. Không reviewer events hoặc corpus
  verified. Không thêm chín Điều lá, L35 A86K2 hoặc20 trường hợp dài.

Build/validate và30 tests tập trung đạt; đối chiếu exact3077 chunk/5371
context/3077 metadata cũ đạt. Kiểm kỹ thuật không chứng minh chất lượng
pháp lý/retrieval. Bản đang dùng của nhóm vẫn **v1 3.077 chunk** cùng index,
query/evaluation và ZIP cũ; không build index draft hoặc chuyển qrels.
Evaluation/Dense tiếp tục trên cùng v1; nếu thử draft sau này, phải bind
version/hash mới và rà coverage/nhãn/ranking, không dùng index v1 cho draft.
Chi tiết: [Experimental Dataset Draft Verification](../reviews/Experimental_Dataset_Draft_Verification.md).

## PDF Thông tư35/38/51 — đã kiểm tra và đăng ký pending

Lượt kiểm tra bắt đầu tại commit `2aebab4e4cbc10c4b550a1571855c0fe3bd9d278`;
đầu lượt chỉ có5 PDF người dùng thêm chưa tracked. Config mới
`config/source_registration.circulars.v1.json` giữ Source Inventory IDs
SRC-005=TT38, SRC-006=TT51, SRC-007=TT35. Không lẫn với Luật35/QH15.

- 5 file local: TT35 chính69tr/phụ lục179tr; TT38 chính7tr; TT51 chính1tr/
  QCVN41:2024 kèm403tr. Tên/kích thước khớp attachments chính thức.
- TT38 local trống số/ngày, kể cả ảnh; GET attachment Chính phủ xác nhận
  byte-identical. Bổ sung riêng Công báo8tr trong staging có số/ngày đầy đủ,
  không ghi đè raw. Không tải lại bốn PDF35/51; remote full-hash còn chưa kiểm.
- QCVN có100 trang PDFium không lấy được text; ảnh trang214 không trắng.
  pdfplumber mẫu đầu có NUL. Cần xử lý reader/hình/bảng ở bước extraction,
  chưa OCR hoặc bỏ nội dung. Lời nói đầu QCVN còn trống số thông tư.
- Run `staging/circulars-registration-001/`:3 documents/6 files pending,
  SQLite FK/integrity/schema/ID/hash đạt; `content.sqlite` vẫn0 bản ghi.
- `staging/circulars-source-check-001/source_metadata.csv` và observed JSONL
  lưu hash/IDs/URL/relationships/capture facts riêng. Năm local không có log
  retrieved_at lịch sử; không hồi điền ngày hiện tại. Source/applicability
  và full-content review pending, origin=agent_review, không human approval.

Validate/register và18 tests Stage2 đạt; require-release-ready exit1 đúng
chính sách.10 raw giữ nguyên hash; dataset/index v1, draft3082 và ZIP giữ
nguyên inventory/hash. Không thay dataset nhóm dùng hoặc nạp nguồn mới vào
chunk/index. Chi tiết: [Circulars Source Registration Verification](../reviews/Circulars_Source_Registration_Verification.md).

## Đồng bộ7 nguồn và xử lý TT38 — chưa cập nhật dataset/index

HEAD đầu lượt `2aebab4e4cbc10c4b550a1571855c0fe3bd9d278`; bảo toàn config,
báo cáo, STATUS và5 PDF untracked có trước. Config tổng hợp mới là
`config/source_registration.seven.v1.json`; snapshot vẫn2025-01-01.

| Source | Law | Registered files | Extraction / parse | Dataset/index v1 |
|---|---|---:|---|---:|
| SRC-001 | 36/2024/QH15 | 1 | DOCX đã xử lý; PDF Điều22 riêng | 788 chunk |
| SRC-002 | 168/2024/NĐ-CP | 1 | DOCX đã xử lý; HTML A16K2 riêng | 1.018 chunk |
| SRC-003 | 35/2024/QH15 | 1 | DOCX đã xử lý, còn bảng/vùng deferred | 664 chunk |
| SRC-004 | 165/2024/NĐ-CP | 1 | DOCX đã xử lý | 607 chunk |
| SRC-005 | 38/2024/TT-BGTVT | 2 | Công báo8tr extraction/parse/preview riêng; PDF7tr đối chiếu | 0 |
| SRC-006 | 51/2024/TT-BGTVT | 2 | Đăng ký main/QCVN, chưa pipeline extraction | 0 |
| SRC-007 | 35/2024/TT-BGTVT | 2 | Đăng ký main/annex, chưa extraction/parse/chunk | 0 |

Đăng ký7/10 là manifest tổng hợp gồm4 DOCX và6 PDF; không tính mọi PDF/HTML
bằng chứng cũ là thêm nguồn pháp lý, không giả các nguồn đã verified. Tất
cả source/edition review và applicability pending;4 văn bản cũ và TT38 có
agent scope proposals, TT35/TT51 chưa assessment đơn vị.

Nguồn TT38 bền vững:
`data/raw/official/38-2024-TT-BGTVT/congbao-1355-1356.pdf`; capture/evidence
trong `data/source_evidence/circulars-2024/`. Copy giữ nguyên SHA/file_id,
không ghi đè bản7tr hoặc PDF trong staging cũ. Metadata mới:
`staging/seven-sources-export-003/source_metadata.csv` và progress/crosswalk
JSONL; CSV cũ giữ nguyên. Một alias SRC-004 ở nhánh HTML NĐ168 được map
vềSRC-002 theo law+artifact, không thay chunk/ID hoặc alias toàn cục.

TT38 run chính `staging/tt38-preview-003/`, Stage3
`staging/tt38-extraction-001/`:12.694 code points,8 page locators,0 lỗi/
warning extraction;59 units (1 document/3 chương/12 điều/32 khoản/11 điểm),
180 spans. Coverage: parsed10.058; supporting1.173; unprocessed bảng1.285;
source layout171; separator trang7, tổng đúng12.694.

42 leaf candidates →38 preview/56 context,4 blocked do bảng/cross-reference:
A6K1, A6K2, A11K2a vàA11K2b.0 over-budget,59–168 token gồm special, unknown0.
3 bảng/33 physical cells/9 rows dẫn xuất được giữ riêng trong quarantine,
có loại đường/xe, đơn vị/điều kiện và source slices/bbox. Chưa table chunk
policy; không truncate hoặc tạo chunk có vẻ đủ từ phần mất bảng.

BRD/SRS/SDD/DDD gốc giữ nguyên byte; chỉ thêm addendum/changelog vì bốn
nguồn là khởi đầu, không giới hạn đích. README/AGENTS/ingestion guide cập
nhật trạng thái thật.78 tests tập trung và9 tests Điều lá đạt; kiểm tra/tái lập/tampering và
giới hạn chi tiết trong [Seven Sources TT38 Verification](../reviews/Seven_Sources_TT38_Verification.md).
Dataset3077/index/evaluation/ZIP và draft3082 không được cập nhật. Chưa
chạy embedding/index, chưa OCR TT51 hoặc yêu cầu nhóm chuyển phiên bản.

## Hoàn thiện ingestion ba Thông tư — 2026-10-23

Mục này cập nhật trạng thái hiện tại; các mục phía trên là lịch sử.
HEAD kiểm tra `3faaf98946ac24ff5abbf2bdd38e53d1c8975ecb`, có thay đổi chưa
commit cho ingestion; không stage/commit/push. Snapshot giữ2025-01-01.
Contract [Circulars addendum v1.1](../design/Circulars_Ingestion_Addendum_v1.1.md),
[báo cáo và bằng chứng](../reviews/Circulars_Ingestion_Completion_Verification.md),
[lệnh tái chạy](../ingestion.md).

Metadata cuối: `staging/seven-sources-export-006/`, 7 văn bản/10 file.
URL Công báo TT38 đã sửa thành scalar252 ký tự bằng receipt/HTML/hash;
CSV đọc được bằng csv.DictReader mặc định và khớp JSONL. 6 download_url có
căn cứ,4 DOCX null;9 retrieved_at lịch sử null. Export lỗi được giữ nguyên.

| Nguồn | Extraction / preview hiện tại | Giới hạn | Dataset/index |
|---|---|---|---|
| SRC-001 Luật36 | DOCX; PDF Điều22 riêng | Pending pháp lý | v1:788 chunk, giữ nguyên |
| SRC-002 NĐ168 | DOCX; HTML A16K2 riêng | Nhánh khôi phục chỉ trong draft | v1:1.018 chunk, giữ nguyên |
| SRC-003 Luật35/QH15 | DOCX | Còn vùng chưa xử lý | v1:664 chunk, giữ nguyên |
| SRC-004 NĐ165 | DOCX | Pending pháp lý | v1:607 chunk, giữ nguyên |
| SRC-005 TT38 | Công báo8tr; tt38-tables-003:38 chunk cũ +9 preview hàng bảng | Điểm b A11K2:279 token; hàng bảng chưa biểu diễn chunk DDD | Chưa nhập |
| SRC-006 TT51 | tt51-extraction-005:1+403tr; tt51-preview-003:3 supporting chunk | QCVN partial:100 trang không text,302 trang U+FFFE,0 target QCVN | Chưa nhập |
| SRC-007 TT35/TT-BGTVT | tt35-extraction-001:69+179tr; tt35-preview-005:767 unit,572 chunk/1.070 context | Cây thưa Phần/Chương;13 source/context blocked,4 quá budget;179tr annex chưa grammar | Chưa nhập |

TT38 đã có kết luận cho cả4 đơn vị bị bảng chặn: A6K1→1 row, A6K2→4 rows,
A11K2a→4 rows; A11K2b giữ dependency đầy đủ và quarantine279. Chín preview
đạt137–168 token,unknown0, giữ33 cells/spans; ID tp_ riêng, chưa phải chunk DDD.

TT35 có133 unit scope proposal (25 included/27 supporting/81 excluded),634
pending. 572 preview kỹ thuật gồm25 included,15 supporting,69 excluded,
463 pending.11 unknown trong preview đạt budget; hai included A15K1b/A15K2b
mỗi target có1 unknown tokenizer, không sửa nguyên văn/preprocessing.
148 bảng/cụm ô đo được,5.541 cells,28 image objects/9 trang annex;
3 vùng annex proposed supporting,176 trang khác pending. Phần/Chương thật
giữ sidecar/dependencies; chưa đủ cây cha DDD chính thức.

TT51 main complete độc lập; QCVN reader hoàn tất nhưng extraction partial:
61.891 U+FFFE,402 issue, validate-reader trả1 đúng chính sách. Không xóa NUL/
noncharacter hoặc gọi text rỗng là trang trắng.403 trang bảng chưa đo layout;
root image inventory quan sát4.057 objects/254 trang,177 trang vector,
59 trang inventory chưa đầy đủ. Chưa OCR/hiểu hình; toàn QCVN giữ unprocessed.

98 tests liên quan đạt;11 focused tests chạy lại đạt sau bổ sung assertion.
7 tampering cases bị từ chối;5.541 cell bindings khớp;572 TT35 ID/content
không đổi khi thêm blocker cấu trúc.281 file baseline được bảo vệ giữ nguyên.
Các số này là kiểm chứng kỹ thuật, không kết luận pháp lý hoặc retrieval.
Chưa thử môi trường sạch/OS khác trong lượt này.

Nguồn/edition/applicability còn pending, scope chỉ agent proposal; ngày hiệu
lực chung có source spans nhưng chưa đánh giá ngoại lệ/sửa đổi cấp unit.
Không human reviewer event. Bản nhóm đang dùng vẫn dataset3077/index/evaluation/
ZIP v1; draft3082 riêng, cả ba Thông tư chưa nhập. Evaluation và Dense của nhóm
tiếp tục trên cùng dataset v1; lượt ingestion này không chạy chúng.

Ứng viên cho đợt dataset tiếp:25 TT35 proposed included (còn blocker cây cha/
review/token), TT38 text đã có và9 hàng bảng sau khi chốt biểu diễn; TT51
chỉ3 supporting khi có dependency cụ thể. Chưa tự ghép các preview vào dataset.
