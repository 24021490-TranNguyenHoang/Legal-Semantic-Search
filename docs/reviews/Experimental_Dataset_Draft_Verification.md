# Dataset experimental v2 draft — kết quả tích hợp A16K2

Commit đầu lượt `aee22f0173affc406cfccc443a9132c43c1c98fb`. Git đã có
README/STATUS cùng năm file recovery chưa commit; giữ nguyên chúng và bổ
sung phần draft. Đã đọc AGENTS, STATUS, DDD, contract dataset/BM25/recovery,
báo cáo khôi phục và actual manifests/crosswalk; đã đọc code packaging,
source proof, chunk identity và recovery trước sửa. Không stage/commit/push.

## Kết quả thực tế và phương án đã dùng

Run **`staging/dataset-v2-draft-001/`**, version
**`vtls-coverage-experimental.v2-draft.1`**, policy
`coverage-source-branches-draft.v1`, status=draft.

| Chỉ tiêu | V1 nhóm đang dùng | Draft riêng |
|---|---:|---:|
| Chunk | 3.077 | 3.082 |
| Context | 5.371 | 5.381 |
| Added / replaced / removed | — | 5 / 0 / 0 |
| Unchanged / conflicted / duplicate | — | 3.077 / 0 / 0 |
| Deferred projection | 46 | 43; giữ đủ 46 hồ sơ lịch sử |
| Scope proposed included / excluded / pending | 94 / 64 / 2.919 | 99 / 64 / 2.919 |

Đối chiếu **tất cả 3.077 chunk**, không chỉ unit ID trong recovery crosswalk:
law_id + canonical_path/citation, ID, exact và NFC/whitespace content.
Cả năm Điểm không có chunk cũ cùng vị trí, cùng ID hoặc trùng nguyên văn ở
vị trí khác. Không tự coi ID mới là căn cứ mới; fixture kiểm trường hợp ID
khác cùng vị trí/nội dung phải duplicate và nội dung/context khác là conflict.

| Điểm A16K2 | Cây DOCX cũ | Dataset v1 | Hành động draft | Token / unknown |
|---|---|---|---|---:|
| a | Có unit, own text khớp | Deferred, không chunk | Added từ nhánh HTML | 101 / 0 |
| b | Có unit, own text khớp | Deferred, không chunk | Added từ nhánh HTML | 143 / 0 |
| c | Có unit, own text khớp | Deferred, không chunk | Added từ nhánh HTML | 187 / 0 |
| d | Paragraph cách ly, marker DOCX đ) | Không unit/chunk | Added theo nguồn d) | 121 / 0 |
| đ | Paragraph cách ly, `ngán hàng` | Không unit/chunk | Added theo nguồn `ngân hàng` | 212 / 0 |

Nguồn khôi phục giữ nguyên từ run004: HTML Chính phủ SHA
`e3803dd1ddd2a770e5f61a95e54111308c4d7b08c2196fa792ae5fdeeb4a5171`,
capture thực2026-10-22T09:42:43.614242Z; đối chiếu PDF scan SHA
`7bb11b939d162499ab404aa41a940cce05dbf071d9cbae7a8898b00d4b4a48bd`,
trang40–41, capture2026-10-16T14:33:07.439116Z. Không tải thêm nguồn.

### Cây cha: không hợp nhất hai representation

Contract v1 không biểu diễn được cây DOCX đầy đủ cùng sparse HTML trong
một `laws[law_id]`. Đã ghi amendment trước khi đóng gói tại
[contract draft](../design/data_model_v1/Experimental_Dataset_Draft_Contract.md).
Giữ nguyên hai component, mỗi target có graph membership. FK cha/con và
context luôn resolve trong component tương ứng. Không sửa schema DDD.

Crosswalk có 10 hàng: tám unit có thật cũ→mới, hai unit d/đ old=null.
Document/chapter/section thay field biểu diễn/parent; Article16, Clause2,
a/b/c đổi parent_unit_id. Không thêm source ID hoặc salt vào identity.
Không reparent các con HTML về cha DOCX. Các vị trí cha trùng được ghi rõ
là representation thay thế, không nhân đôi căn cứ trong target list.

Document DOCX có **628 code points own text**, giữ nguyên hash và record.
Document/Chương/Mục HTML own text chưa chọn giữ phạm vi sparse, không ghi
đè cha cũ hoặc suy nguồn rỗng. Title Điều16 và lead Khoản2 là hai context
thực cho từng Điểm; không dùng anh em hoặc cha hỗn hợp từ nguồn khác.

Ba deferred a/b/c được ghi `alternate_source_target_available`, không ghi
resolved issue DOCX. Root deferred43 là projection cho draft, không xóa46
hồ sơ trong base. d/đ không có old unit/chunk giả. Không thêm chín Điều lá,
L35 A86K2, 20 trường hợp dài, Điều39/40 hoặc hai bảng Luật35.

## Artifact và binding

Input base: `staging/bm25-baseline-v1-001/dataset/dataset_manifest.json`,
version `vtls-coverage-experimental.v1`, manifest SHA
`2aa5dc595dab7614920ce94317b85c7b21e188cc35b16b54bef9e81f3ccf1b0a`.
Recovery: `staging/nd168-a16k2-preview-004/manifest.json`, SHA
`64d71247974bf8973684dabb91abeee4d76eaf34495bf44212c4cf4122a15770`.

Draft manifest SHA:
`42c59623d6d921429cd45f2bdfaab3deabab002efa4f13e8720b9645d8944237`.
Draft content SHA:
`729bc28b63f773de9d4f5c35c8d77c5f53c5311fa64f7d9c49e8e69496b376be`.
96 inventory files,95.365.087 byte (ngoài control manifests/execution).
Không tạo ZIP mới hoặc thay ZIP bàn giao.

Mở các file dưới `staging/dataset-v2-draft-001/`:

- `review.md`: năm target/context và kết luận delta dễ đọc.
- `candidate_comparison.jsonl`: toàn bộ match/mismatch với dataset cũ.
- `delta.jsonl`: mapping chunk cũ→draft và hướng xử lý qrels,3.082 hàng.
- `unit_crosswalk.jsonl`:10 mapping units, identity fields, old/new chunk IDs.
- `parent_dependencies.jsonl`:5 cha, parent IDs, hash/độ dài/phạm vi own text.
- `memberships.jsonl`: chunk→graph; manifest.components cho root_ref.
- `chunks.jsonl`, `contexts.jsonl`, `metadata.jsonl`, `deferred_history.jsonl`,
  `deferred.jsonl`, statistics/report cùng hai bundle component bất biến.

Đọc source_locator: lookup membership theo chunk_id, lấy root_ref tương ứng
trong manifest, resolve proof từ đó. Không resolve ở root draft hoặc đoán
graph theo law_id. Mỗi component giữ source snapshot, extraction/trace,
units/spans và pending/proposal gốc; không ghi raw/spans lên extraction cũ.

## Lệnh và kết quả đã chạy

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_experimental_draft tests.test_nd168_a16k2 tests.test_stage6_points.PointBuilderTests
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.experimental_draft build --run-dir staging/dataset-v2-draft-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.experimental_draft validate --manifest staging/dataset-v2-draft-001/dataset_manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.experimental_draft validate --manifest staging/dataset-draft-verification-001/tamper-copy/dataset_manifest.json
git diff --check
```

- 30 tests đạt: 10 composition synthetic + 7 scoped recovery + 13 point builder.
  Kiểm duplicate/conflict khác ID, context thay đổi, content giống khác vị
  trí, wrong crosswalk/membership/parent, giữ bytes/proofs/config và hồi quy
  builder/nguồn. Fixture không nhập dataset.
- Build exit 0 chạy validator base và recovery hiện có trước tạo output.
  Recovery validator chạy tokenizer-only; không encoder inference.
- Validate exit 0: replay base bằng validator cũ; replay HTML/normalization/
  mapping/DDD IDs/parents/spans/trace và builder với token evidence bound.
  Validate không tokenize mới, không cần coverage/recovery gốc. Copy bundle
  sang thư mục khác rồi validate exit0; **cùng máy/môi trường**, chưa thử máy
  hoặc OS khác. Extraction identity còn khóa Python/lxml/Unicode/tool.
- Đối chiếu exact 3077 chunk + 5371 context + 3077 metadata cũ đều giống; 5
  chunk mới giữ nguyên IDs/hash/proofs/context từ preview004.
- Bốn fault probes trên bản copy: sai graph membership, sửa context proof,
  sai component binding hoặc source_status=verified đều bị từ chối, kể cả
  reseal manifest root. Chỉ trong probes, stub phần base replay đã được
  validate riêng để tránh lặp nặng; kiểm layer mới vẫn chạy. Sau phục hồi
  copy, lệnh validate đầy đủ phía trên đạt, không stub.
- Build vào run đã tồn tại và validate manifest thiếu đều exit1 rõ ràng.
- Audit 172 file từ baseline đầu lượt không đổi: raw, dataset độc lập/gắn
  index, index, evaluation/query, preview004 và ZIP. ZIP SHA vẫn
  `8678cd66620cbacfae7443e9e0774ac36f8294aeb6edceebf1e06cfaa789d03e`.
  Index binding dataset manifest đúng v1; không rebuild/search index draft.

Log kiểm chứng: `staging/dataset-draft-verification-001/` có baseline Git/diff,
tests_summary, delta_checks, tampering_tests, negative_cli và preservation
before/after. Tests_summary là tóm tắt command đã thực thi, không một lần
test mới. Không dùng số test kết luận chất lượng retrieval/pháp lý.

Tái tạo: dùng lệnh README, thay run001 bằng tên NEW chưa tồn tại, config
`config/experimental_dataset_draft.v1.json`. Dùng cùng inputs/code/tool để
giữ content/manifest identity; execution.json ghi sự kiện thực ngoài hash.

## Pending và tác động qrels/index

Chưa reviewer/source edition/technical/applicability verified, không có
human reviewer event. Scope chỉ proposed included cho năm target; không
suy hiệu lực từ sửa kỹ thuật hoặc ngày văn bản. HTML hiện tại đăng sau
snapshot và scan đối chiếu vùng hẹp không chứng minh lịch sử sửa đổi/hiệu
lực toàn văn tại2025-01-01. Các cổng phát hành giữ đóng; corpus_version=null.

Không đổi query set, qrels hoặc index đang dùng. 3.077 ID unchanged chỉ là
căn cứ xem xét carry-over judgments khi bind sang version/hash mới; năm ID
added vẫn unjudged. Nhóm evaluation phải xét coverage/positive mới và tập
nhãn; ngay cả khi chunk cũ giữ nguyên, BM25 IDF/ranking có thể đổi do thêm
document. Loader BM25 v1 hiện từ chối policy draft. Chưa triển khai consumer
membership cho index, chưa build index draft, Dense/embedding hoặc đo metric.
Không yêu cầu nhóm chuyển phiên bản ở lượt này.

File mới: `src/experimental_draft.py` (adapter, không builder mới), config,
10 fixture tests, contract và báo cáo này. README/STATUS bổ sung hướng dẫn
và phân biệt v1 đang dùng với draft. Giữ nguyên code recovery và mọi code
packaging/builder/parser/encoder/retrieval cũ. Dừng sau draft để xem diff.
