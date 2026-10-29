# Phiên 4 — rebuild NĐ168, mẫu XXIII và packaging plan

Snapshot **2025-01-01**. Trạng thái **PREVIEW_AND_PLAN_ONLY**. Không tạo dataset,
index, embedding, assessment, nhãn accepted hay human reviewer event.

Đầu phiên Git sạch, HEAD `f63d4b629f4b5e44e46f8200a52986cada59cfc4`.
Nguồn/proposal ghim **source-session3-proposal-009**, không chọn latest. Đã đọc
source_selection, 5.375 membership proposals, 9 table-row proposals, 12 nonunit
proposals, 3.224 dependency records và cả hai comparison v3/v4. Config mới ghim
20 input/hash, dùng DOCX session2 đã sửa; không áp lại corrections/parser.

Run chính: `staging/source-session4-preview-007/`; replay `…preview-008/`.
Bộ đọc dễ xem và checks: `staging/source-session4-checks-002/`.
Run development 001–006 giữ nguyên; không dùng chúng thay run chính.

## NĐ168: 27 record cũ không đồng nghĩa 27 target mới

| Nhóm nguồn mới | Unit pháp lý | Record mới | Kết quả |
|---|---:|---:|---|
| A6K1 a,b,c,d,đ | 5 | 5 chunk.v1 | Ready kỹ thuật |
| A7K1 a,b,c,d,đ,e,g,h,i,k | 10 | 10 chunk.v1 | Ready kỹ thuật |
| A10K1 a,b,c; A10K2 a,b,c | 6 | 6 chunk.v1 | Ready kỹ thuật |
| A18K1 | 1 | 1 chunk.v1 | Ready kỹ thuật |
| A16K2 a,b,c,d,đ | 5 | 0 | Scope unresolved trên nhánh DOCX run009 |
| Tổng | **27** | **22** | **5 blocked**, không chuyển nhãn từ HTML |

Danh sách đủ 27 old record ID → old unit → lineage → selected unit → new record,
hai nội dung/nguồn và disposition có trong
`source-session4-checks-002/nd168.disposition.expanded.{jsonl,csv}` và
`ND168_Disposition.md`. Nguyên văn/context của 22 record ở
`source-session4-preview-007/nd168_preview.md`; native proof và toàn nội dung
required-read ở `nd168.reads.jsonl`. Không chỉ đổi ID trong payload cũ.

22 record mới giữ nguyên own text, search text và công thức identity chunk.v1.
So payload identity thực tế: **unit_id và contexts đổi ở cả 22**; các trường
identity còn lại không đổi. Context dùng ancestor IDs/ranges của graph mới.
Nguồn mới: file `d191d948-dfd7-5a1f-b38f-34c7eb2fe7d4`, SHA
`e31ebb1464cb0a5d56ec0b7e2237cf08b667247d8d9786bd1a872e76bd24bd41`,
extraction `e_1d98dab5400c9b8c91ca524c10668d2ca5b211daadf94199e34c9c75d207ad90`.
Offsets/proofs dựng từ extraction này; không mang assessment/qrels/offsets cũ.

Builder `leaf-clause-point-context.v1`, PyVi/PhoBERT và budget **256** không đổi.
Đo được **88–239 token**, **unknown=0**, không truncate; 22 chunk, không cần
encoder views mới. Còn nguyên dữ liệu quarantine và dependency checks của builder.

Required-read hữu hạn giữ các ngoại lệ được nêu ở A6K1a/A7K1a, các dẫn chiếu
A6K1c→A6K7c, A7K1đ→A7K6c/d, A10K1b→A10K2a, chế tài bổ sung/trừ điểm
A6K15–16/A7K12–13. Điểm còi/ngoại lệ xe ưu tiên có Luật36 A27. Mỗi dependency
trả đủ own title/text/spans, cha của Điểm được dẫn chiếu giữ đoạn dẫn mức phạt;
không suy tiền phạt bằng từ khóa hoặc lấy các anh em không liên quan.

Nhánh NĐ165/Luật36 cho **NĐ168 A12K12** đã kiểm binding riêng tại
`nd168.cross_source_probe.json`; **không thuộc 27 seed**, nên không tự thêm target
hay cả nguồn NĐ165 vào plan. Vẫn giữ dependency điều khoản chuyển tiếp từ run009.

## Mẫu XXIII và A28K2: mẫu hoàn thành, closure còn blocked

Đã xem ảnh **126/127/128** của `data/raw/35-bgtvt-kem.pdf` và ảnh trang32 bản
chính. SHA phụ lục `a79fd735777e6948bb9cfc8aa4ec556641a616d4bfc2ee0d00e8c26d7e559a94`.
Trang **PDF127** thật có heading “Phụ lục XXIII / MẪU GIẤY XÁC NHẬN HOÀN THÀNH
KHOÁ HỌC”, phần “XÁC NHẬN HOÀN THÀNH KHÓA ĐÀO TẠO LÁI XE”, dòng điền thông tin,
người ký và hai hướng dẫn. Trang126 thuộc XXII; trang128 sang XXIV. Không quan sát
được số trang in trên mẫu127; không gán số trang PDF thành số trang in.

**18 dòng nguồn, 0 bảng vật lý**, đủ nhãn/trường trống/dấu chấm/hướng dẫn/ký.
Giữ bbox từng dòng và whole-page proof, không tạo cell grid hoặc điền giá trị giả.
`form-retrieval.v1` dùng identity recipe hiện có, record ID
`fr_d8ab773ccbab4a2dd33b4c4e4ae374eaaee93e782ef4fe27a87f1361a953cba0`.
Đây là biểu diễn layout có truy vết, không phải chunk.v1 hay legal verified.

A28K2 có technical chunk preview và source proof. Bản in trang32 cũng ghi
“được cơ đào tạo”; giữ đúng nguồn, không tự thêm chữ “sở”. Điều28 không có own
lead trước Khoản1: vắng hợp lệ. Sáu owner **A6K1/A7K1/A8K1a–d** được đọc bằng
adapter phiên3; **A7 dùng Phụ lục II**. Bảng chương trình là supporting có điều
kiện theo hạng GPLX, không thành target độc lập. Đã đưa **18 completion units**
thuộc A6K4, A7K4–5, A8K4–5 và spans vào hồ sơ A28.

Chưa đề xuất nhận A28K2 vì A7K4d/A8K4d trực tiếp yêu cầu tiêu chí chấm thi ở:

| Phụ lục | Trang PDF phụ lục | Native lines | Native tables | Còn thiếu |
|---|---|---:|---:|---|
| XV | 48–72 | 1.001 | 31 | Kiểm layout/nội dung/whole-read chấm điểm |
| XVI | 73–84 | 357 | 8 | Như trên |
| XVII | 85–96 | 367 | 8 | Như trên |

49 trang này **đã có native inventory, chưa được rà đủ** trong phiên này. Không
mở đệ quy mọi dẫn chiếu. A21K4c/A46K2 vẫn ngoài target. Hồ sơ biểu mẫu, completion
text/proof và sáu whole table reads đã bàn giao để tiếp tục; mẫu ready không làm
closure ready. Xem `TT35_XXIII_A28_Review.md` và `a28.closure.json`.

## Tập dự kiến đóng gói — chưa tạo dataset

Kiểm từng record trong **116** đề xuất phiên3: **103 chunk + 9 table-row TT38 +
4 whole-source**, đủ ID/type/payload hash/native proof/context/required read.
Kết quả kỹ thuật 116 ready, 0 blocked. Thêm đúng 22 ND168 mới:

| Thành phần | Số record |
|---|---:|
| chunk.v1 | **125** |
| table-retrieval.v1 | **9** |
| source-retrieval.v1 | **4** |
| Tổng target proposal | **138** |
| Supporting unit reads (không phải target record mới) | **238** |
| Supporting form XXVI | **1** |

138 target thuộc **132 unit pháp lý** vì nhiều hàng bảng dùng chung owner. 238
supporting units là union required-read, **35 unit cũng là target của record
khác**; không cộng thành 376 đơn vị pháp lý. Không có old ND record ID trong
tập target mới; không split/merge 22 record đã dựng. Năm A16 và A28 không vào plan.

Target theo văn bản: Luật36 70; NĐ168 22; Luật35/QH15 2; TT38 18;
TT35/BGTVT 23; QCVN/TT51 3. Số này là proposal chọn lọc, không phải toàn nguồn.
Không tự lấy supporting_only từ inventory. XXVI được đọc đủ 23 dòng nguồn;
XXIII và sáu programme tables chỉ nằm trong hồ sơ A28 blocked, chưa thành closure
của tập138. Supporting units: NĐ168 99, Luật36 78, TT35 33, TT38 15, QCVN 11,
Luật35/QH15 2; NĐ165 chỉ có probe chưa chọn nên không được đóng gói ngầm.

Mỗi target có source artifact/payload hash/type/scope proposal/required units,
dependency IDs và capability. `base116.reads.jsonl`, `nd168.reads.jsonl` và
`supporting_records.reads.jsonl` trả typed record cùng nguồn và toàn nội dung
required-read, không chỉ projection encoder. `packaging_plan.jsonl/.csv` và
`Packaging_Plan.md` là kế hoạch, chưa phải dataset portable được phát hành.

Whole record TT38 A11K2b vẫn **279 token / 2 view 237+44**, không mất nội dung;
ba QCVN record giữ view cũ 137;70;234+20. View không là target độc lập. Không
chuẩn hóa gộp I.418/I.416 hoặc nhận sáu recovery regions thành target.

## Kiểm chứng thực thi và giới hạn

- Bộ test phiên4+phiên2/3: **27 pass**, gồm source/offset/old ID, dependency,
  context, form mất hướng dẫn dù rehash, capability, duplicate DOCX/HTML, views,
  budget/truncation và table-row token budget.
- Suite builder/encoder/circular: **46 collected, 39 pass, 7 skipped** vì chưa
  truyền manifest của các pilot cũ vào opt-in tests. Batch này không chạy model.
  Lần gọi đầu thiếu PYTHONPATH của tests nên import một test cũ lỗi; đã sửa lệnh,
  không sửa test cũ hoặc chỉ cập nhật expected để pass.
- Checker thật: **19 negative bị từ chối**, 138 target reads cùng form/support
  và table consumer được kiểm; **58 payload replay giống byte**. Không coi số
  test là chứng minh chất lượng pháp lý hoặc retrieval.
- Portable probe: sao độc lập 5 typed reads (ND chunk, XXIII form, A7 table owner
  với AnnexII, TT38 row, TT38 whole-source); chạy Python `-I -B -S`, audit hook
  **cấm đọc workspace gốc**, kể cả thử AGENTS.md. Đọc đủ nguồn/dependency đã copy.
  Chỉ trên **cùng máy Windows**, không phải kiểm máy/OS khác; chưa đóng gói toàn138.
- Baseline **3.488 file** kiểm hash; chỉ STATUS/ingestion được phép thêm trạng thái
  mới, lịch sử giữ nguyên bytes. Raw/run đã seal/dataset/index/evaluation/qrels/ZIP
  không đổi. Receipt cuối nằm trong coordinator `source-session4-001/`.
- Word retry bản copy read-only, private DispatchEx/ẩn, macro disabled: vẫn COM
  `-2147023584` logon session. Nguồn DOCX nguyên vẹn; **chưa kiểm bố cục render**.
  Không dùng ZIP/XML thay render hoặc dừng các phần độc lập vì lỗi này.

Không tải/extraction lại toàn nguồn, không OCR QCVN/khôi phục5013unresolved;
không legal verification, applicability decision, qrels transfer, dataset/index
build hoặc chuyển phiên bản cho nhóm. Source/edition/applicability tiếp tục
pending; proposal scope tách khỏi technical pass.

## Đủ điều kiện cho phiên tiếp theo

Có thể giao phiên đóng gói **subset138** cùng closure đã liệt kê, nếu giữ contract
experimental/pending và mang đủ typed consumer/source assets. Phiên này **chưa
tạo dataset** và không yêu cầu nhóm chuyển bản. Không coi subset này là hoàn thiện
bảy nguồn. A16K2 cần scope review trên nguồn DOCX; A28 cần required-read chấm điểm
XV/XVI/XVII; bố cục DOCX cần môi trường Word hoạt động. Các phần này không được
âm thầm nhận vào subset vì đã có preview hoặc ảnh.

Lệnh thực tế và vị trí artifact: [Source_Session4_Replay.md](../handoff/Source_Session4_Replay.md).
