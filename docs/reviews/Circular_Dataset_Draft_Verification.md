# Draft experimental mở rộng ba nguồn thành phần — 2026-10-23

Snapshot **2025-01-01**, HEAD kiểm tra cuối phiên
`f04f3482ca26a303ad0b47487eddd3f2056bc8f7`. Đầu phiên git status/diff rỗng:
công việc ingestion/priority trước phiên đã được commit trong repository.
Đã lưu status/diff/hash ở `staging/circular-draft-audit-001/`, không nhận
công việc trước là thay đổi mới. Phiên này
triển khai adapter composition và **build draft thật**, không chỉ thêm preview.

## Bản hiện hành

- Run: `staging/dataset-v3-draft-005/`.
- Dataset: `vtls-coverage-experimental.v3-draft.1`, policy `circular-composition.v1`.
- Base khóa SHA manifest trong config: `dataset-v2-draft-001`,3082 chunk,
  có đủ năm Điểm NĐ168 khôi phục. Priority khóa manifest circular-priority-006.
- `status=draft`, experimental=true, corpus_version=null, release_eligible=false.
  Scope chỉ proposed, source/edition/applicability pending,0humanreviewerevent.

| Loại | Số thực đo | Delta |
|---|---:|---|
| Text chunk.v1 | 3.106 | Giữ nguyên3.082, thêm24 =8TT38+16TT35 |
| Table retrieval records | 9 | Thêm9 tr_, không giả chunk.v1 |
| Tổng retrieval records | 3.115 | Định nghĩa:3.106 text +9 table |
| Encoder contexts | 5.413 | Base5.381 +32 mới |
| Required-read dependency bindings | 23 | Tách khỏi encoder context, có subtree IDs và spans |
| Candidate withheld | 13 | 9TT35 +1TT38 quarantine +3TT51 conditional |

`selection.jsonl`/`review.md` có46 disposition, `dependencies.jsonl` có các
dependency bắt buộc được bind. Toàn bộ text/cells/graph/source cần validate/read
được đóng gói. TT35 graph783 nodes vẫn là source component, chỉ16 leaf target
được chọn, không nhập572 preview. TT51/QCVN pilot không có trong package.

## Rà dependency: nguyên văn, không dùng extractor làm resolver

Đã đọc toàn33 target văn bản ưu tiên cùng context và bảng, bốn phụ lục được
dẫn chiếu và các subtree Luật36 thực trong base. Config selection ghi unit_id,
scope proposal, disposition/reason và dependency unit_ids chính xác, không
đoán bằng từ khóa rồi truyền nhãn cho con.

Phân loại áp dụng trong lượt:

1. **Bắt buộc và đã bind để đọc:** TT35 A14K2a/b→Luật36 A60K4 (căn cứ nằm
   trong lead Khoản, đã đọc, dù extractor target-only trước đó có thể bỏ sót);
   A28K1→A59K1 cùng sáu Điểm độ tuổi và A59K2; A29K3a→TT35 A15K1b;
   A67→Luật36 A89K3 và toàn bộ các Điểm đổi hạng a…n. Không chỉ bind đoạn
   dẫn rỗng con. Tuổi/sức khỏe giữ điều kiện trong quy phạm, không đòi biết
   người dùng cụ thể để đóng gói. Các tiêu chuẩn y tế chi tiết ngoài Luật59
   chưa được đưa vào; không tuyên bố hỗ trợ câu hỏi ngưỡng sức khỏe cụ thể.
2. **TT38 bắt buộc và đã bind:** A4K1→Luật36 A12; A4K2→A6/A7/A8/A11
   toàn subtree, kèm tables/cells cần thiết; A9K2/K3→A9K1 để giữ điều kiện
   tổ chức giao thông/biển báo; các hàng A6→A7/A8 để rõ nhóm xe ngoại lệ.
   Required-read có thể chứa nguyên văn b tại source graph, nhưng candidate
   encoder279 token của b vẫn quarantine, không nhập làm target/context encoder.
3. **Bổ sung hoặc nguyên tắc tự đủ:** TT35 A32K6b là quy tắc điều kiện
   “trường hợp điều ước…có quy định khác”, giữ nguyên điều kiện và context
   Khoản6, không tuyên bố nội dung một điều ước cụ thể. A32K6a yêu cầu đổi
   GPLX là nghĩa vụ đọc được; chi tiết thủ tục A36 là hướng dẫn bổ sung,
   không tự ghép toàn thủ tục vào encoder. Không trả lời thay các chi tiết ấy.
4. **Bắt buộc nhưng chưa có biểu diễn đủ:** XI/XII/XXIII/XXVI có text/ảnh
   nguồn đã đọc, nhưng policy chưa biểu diễn biểu mẫu hoàn chỉnh. Giữ ngoài
   A14K3,A15K1a,A15K2a,A15K2c,A28K2,A29K3b,A32K2. Không coi có page text
   là đã có biểu diễn form đầy đủ. A32K2 còn dẫn thủ tục A36.
5. **Chưa xác định đủ:** A28K3 thiếu binding “báo cáo1”; A45 là pointer tới
   điều ước áp dụng chưa xác định. Cả hai withheld, không chỉ gắn warning rồi nhập.

Không mở rộng reference đệ quy toàn corpus; không chunk biểu mẫu. Required-read
là contract bắt buộc cho consumer: phải có khả năng đọc/bảo toàn các dependency
này, không dùng text_for_search một mình để trình bày câu trả lời thiếu nghĩa.
Không thêm chúng vào encoder; do đó input/token/IDs đã đo giữ nguyên.

## Biểu diễn và resolver

Contract trước triển khai: [composition v1](../design/Circular_Dataset_Composition_v1.0.md).
Base copy bằng `experimental_draft.copy_component`, kiểm bằng validator cũ;
root chunks/context giữ nguyên object cũ. Không flatten cây DOCX/HTML hoặc
graph TT35 mới vào một cây law_id chung.

`memberships.jsonl` có record_type/record_id/graph_id/proof_base:

- Base DOCX/HTML resolve trong hai graph con của `components/base/`.
- TT35 proof giữ prefix tt35/ nguyên payload, resolve tại `components/tt35/`.
- TT38 text proof resolve tại `components/tt38/base/`.
- Table source_proof_base_ref vẫn chuỗi logical gốc staging/tt38-tables-003;
  manifest.mounts ánh xạ tới `components/tt38/`. Không mở đường dẫn gốc trong repo.

ID TT38 giữ nguyên; TT35 giữ ID graph revision và chunk policy đã tạo ởpriority.
unit/chunk crosswalk được bảo toàn, kiểm own content/type/designation trước/sau
và graph/chunk membership. Bảng giữ source_original/cells/header/rows tách
derived_text. Cờ downstream_blocker trong payload lịch sử không bị sửa hash:
manifest ghi adapter/capability đã thay thế blocker đó; release vẫnfalse.

Dependency validate/read đóng gói: source normalized/raw, graph/spans, cells,
trace, crosswalk, token evidence, selection và portable validator. HTML chính
thức TT35/TT38/Công báo và metadata observed được lưu làm evidence pending.
Các ref lịch sử trong metadata là quan sát provenance, không phải đường dẫn
resolver runtime; legacy PowerShell receipt/observed wrappers không được chép
vào bundle hoặc mở ngầm. Chúng và manifests/tokenizer/repository validators
là dependency rebuild riêng, ghi trong evidence/dependency_roles.json và
source_binding.json. Không giả source provenance đã đầy đủ.

Consumer phải hỗ trợ chunk.v1, graph-part.v1.2, table-retrieval.v1 và
required-read-dependency.v1. Thiếu capability hoặc record type lạ bị từ chối;
không dùng loader/index v1 cho bản này. Portable validation dùng stdlib,
full build vẫn cần môi trường repo cùng dependencies/assets hiện có.

## Diff, kiểm chứng và portability

Delta thêm24 text +9 table, unchanged3082, replaced/removed/conflicted=0.
Không trùng ID/vị trí target; kiểm row-table-owner riêng để không gộp các hàng
của cùng Khoản. `candidate_comparison.jsonl` giữ match exact vị trí và nội dung
NFC/whitespace với toànbase; nội dung giống ở luật khác không tự nhập chung.
Không sửa qrels hoặc áp nhãn cũ sang record mới.

Build chạy đầy đủ validator draft cũ và priority trước composition; portable
check inventory/hash, graph/field spans/parent/crosswalk, chunk.v1 identities,
context/source roundtrip, source proof roots, table/cell/header bindings,
dependency subtree completeness, token budget và pending/status.

39 tests phù hợp trên bản cuối đạt20,840s, gồm ca reseal rồi sửa dependency, record type,
cells/header, cha, crosswalk và snapshot bị từ chối. Unit test chặn vượt256,
truncation và path escape. Không dùng tests để kết luận pháp lý/retrieval.

Đã copy bản cuối sang `staging/circular-draft-independent-002/bundle/`, tạo
venv mới **không pip/dependency ngoài stdlib**, chạy Python isolated mode và
audit hook từ chối đọc workspace ngoài thư mục độc lập. Validate đạt, read
đạt cho table/TT35 có dependency/TT38/NĐ168 khôi phục. Không phát hiện chuỗi
đường dẫn C:/Users trong các file văn bản bundle. Đây là cùng máy Windows,
không gọi là kiểm chứng máy/OS khác. Phải dùng `-X utf8` khi xuất nguyên văn
tiếng Việt trên Windows; thử thiếu cờ gặp lỗi charmap, đã sửa lệnh.

Portable check là integrity/semantic read validation, không tuyên bố replay
reader PDF hoặc tokenization mới trong môi trường stdlib. Full replay/rebuild
được thực hiện bằng repo và upstream validators trước đóng gói.

Các run001–004 là quá trình triển khai, giữ nguyên lịch sử;005 là bản cuối.
Lần001 thiếu tạo thư mục graphs, đã sửa exporter trước build002. Không reset,
clean hoặc sửa bundle cũ để chạy lại.

Manifest SHA-256 cuối:
`1a17bbd11bfa00329c83fc1c31f4dade255f75a97df713a7a09db43f256d70b4`.
Dataset content SHA-256:
`c20c30a7091cffb53090b704d3ab4414b0ebb250b7eb72c6bc21064882036bd2`.
Inventory payload124.730.684bytes, không gồm venv hoặc lịch sử staging.
23 dependency bindings tham chiếu55 graph units duy nhất; không phải55target
mới.24 text additions có tổng2unknown giữ nguyên. Không phát hiện trùng
vị trí/ID hoặc nội dung NFC-whitespace với base trong candidate comparison.

File thêm phiên này: src/circular_dataset.py, src/circular_dataset_portable.py,
config/circular_dataset.v1.json, tests/test_circular_dataset.py, contract và
báo cáo này. Bổ sung routes CLI cũ và AGENTS/STATUS/ingestion guide; các code/
config/docs ingestion/priority có trước vẫn giữ nguyên. Không đổi
schema DDD hoặc validator/adapter draft v2 cũ.

Kiểm preservation cuối:629 file baseline,625 nguyên hash;4 file được bổ sung
có chủ đích là CLI/AGENTS/STATUS/ingestion guide,0 thay đổi bất ngờ. Bao gồm
raw/evidence sealed, draft3082, dataset/index3077, evaluation/qrels/ZIP và
priority006. Git diff --check đạt, Git index rỗng. Bằng chứng thực thi trong
staging/circular-draft-audit-001/manifest.json; không coi baseline hữu hạn này
là kiểm hash mọi file trong toàn bộ staging.

## Lệnh thực tế và bước tiếp

```powershell
# Rebuild từ gốc repo, thư mục NEW chưa tồn tại
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.tt38_preview dataset-draft --config config/circular_dataset.v1.json --run-dir staging/dataset-v3-draft-NEW

# Validate/read sau khi copy riêng folder bundle; không cần repository/venv cũ
python -X utf8 -I bundle/validate_read.py validate --root bundle
$sampleRecord = Get-Content bundle/table_records.jsonl -Encoding utf8 -TotalCount 1 | ConvertFrom-Json
python -X utf8 -I bundle/validate_read.py read --root bundle --record-id $sampleRecord.retrieval_id

# Consumer cũ cố tình không hỗ trợ table/Part: phải exit1
python -X utf8 -I bundle/validate_read.py validate --root bundle --capabilities chunk.v1

.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_circular_dataset tests.test_circular_priority tests.test_circular_completion tests.test_stage6_points.PointBuilderTests tests.test_leaf_articles.LeafArticleTests
git diff --check
```

Đủ điều kiện kỹ thuật tạo draft experimental đã được thực hiện. Chưa nghiệm
thu pháp lý: nguồn/edition/applicability vẫn pending, scope proposed. Ngày hiệu
lực chung/điều kiện chuyển tiếp giữ bằng chứng cũ, không dùng ngày tải thay
ngày hiệu lực và không cần biết hoàn cảnh cá nhân để đóng gói. Không tra cứu
nguồn mới khi các subtree nguồn hiện có đã đủ cho các binding được chọn.

Phiên tới nếu được phép: consumer/index revision phải xử lý hai record types,
resolver/membership và required-read dependency; quyết định cách đưa derived
table text vào index, giữ source nguyên văn, bind version/hash và đánh giá lại.
Chưa build index/BM25/Dense/embedding, sửa app hoặc chuyển phiên bản cho nhóm.
