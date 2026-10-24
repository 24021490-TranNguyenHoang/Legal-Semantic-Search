# Development relevance review composition — 2026-10-24

Đầu phiên HEAD `bc2b2b7181a8e3fcdd7559f17135fa2b09cc3796`, worktree có sẵn
3 file modified và9 untracked từ lượt BM25 composition. Đã đọc AGENTS,
STATUS, contract/report composition và contract/code evaluation thực tế.
Giữ các thay đổi đó; lượt này chỉ bổ sung review adapter/contract/tests/tài
liệu và phần hiện tại của STATUS. Không stage/commit/push.

## Kết quả thực tế

Input đúng `bm25-composition-001`, `composition-queries-001`,
`bm25-composition-evaluation-001`; index bind `dataset-v3-draft-005`:
dataset `vtls-coverage-experimental.v3-draft.1`, index
`vtls-bm25s-composition.v1`, 3.115 retrieval members. Đã kiểm manifest,
frozen query, source projection và từng detail bằng consumer thực; không
gọi build/reindex. Dataset/index manifest SHA lần lượt:

- `1a17bbd11bfa00329c83fc1c31f4dade255f75a97df713a7a09db43f256d70b4`
- `6d285b850a8839e69dc2ecdbfd82a6d884310fb112b968db922d9ebbec09993e`

Output `staging/composition-relevance-review-001/` đã seal, rubric v1.1 ghi
trước nhãn. Phiếu đọc ẩn rank/score, ID sắp ổn định. Đọc 313 target/context
độc lập, xét riêng500 cặp/50query (30cũ/15mới/5limit); đọc required-read khi
cần, kiểm9hàng bảng với header/cell/đơn vị/điều kiện và source slices.

| Hạng mục | Số thực tế |
|---|---:|
| Nhãn proposed trong Top10 | 497 |
| Pending/null vì câu chưa rõ loại xe | 3 |
| Relevance0 / 1 / 2 | 377 / 57 / 63 |
| Nhãn2 full / partial | 28 / 35 |
| Cặp positive ngoài pool cho45dev | 33, thuộc24query |
| Bổ sung limit L05 | 1 dependency-only, không rank source unit |
| Tổng ngoài pool / record duy nhất | 34 / 17 |
| Tìm sâu nguyên query | 45query × Top100 =4.500hits |
| Record đọc ở khảo sát citation | 101 |
| Proposal v1 binding riêng | 300 (290 đọc payload chung,10cặp bị thay đọc riêng) |
| Accepted / human events / qrels | 0 / 0 / rỗng |
| Metrics chính thức | null |

Ba cặp pending là D02 với ngoại lệ xe chở người/chở hàng bốn bánh và D03
với hàng xi téc/kéo xe. Không tự đoán loại xe. Không chấm toàn4.500hits,
không chứng minh đã tìm đủ positive của từng câu. Những record chưa chấm
không bị ghi0. Scope/source/edition/applicability vẫn pending/proposed.

Các ca quan trọng đã đọc:

- Bằng hết hạn: Top1 cũ về đơn vị vận tải hàng hóa, mới về thông tin GPLX PET,
  cả hai đề xuất0. TT35A34K2a có trong graph nhưng không retrieval member;
  A29K3a/c chỉ hỗ trợ hồ sơ. Không thêm source-only ID vào qrels.
- D05: V=60/35m, không dùng60<V≤80/55m; câu thiếu thời tiết nên partial.
- D07: cần hai hàng80/55m và81/70m, không lấy Top1 trả lời toàn câu.
- D10: TT35A32K5 nói rõ B tự động không lái số sàn; B1 cũ chỉ supporting.
- L05: hàng khô ráo supporting; Điểm b nói mưa phải lớn hơn trị số biển/bảnga
  trong dependency của A4K2, không có target riêng vì quarantine279token.
- Năm limit được khảo sát riêng: XI/XXVI withheld, QCVN/y tế chi tiết ngoài
  component retrieval, rain có dependency. Không kết luận cả5 đều không đáp án.

`review_report.md` có bảng12query thay Top10 và15ca phân tích cụ thể, ghi độ
chắc chắn high13/medium2. Phân bố lỗi chỉ trên15ca chọn có chủ đích, không là
tỷ lệ lỗi của500cặp. Chỉ một thay membership đem thêm target partial cho câu
điểm GPLX theo proposal; không kết luận chất lượng tổng thể v3 hơn v1.
Không thấy lỗi consumer/detail trong phạm vi kiểm. Tối đa3 hướng cải thiện
chỉ được đề xuất; chưa tuning hoặc sửa dữ liệu.

## Lệnh và kết quả đã chạy

```powershell
git status --short
git diff --stat
git diff -- AGENTS.md docs/ingestion.md
git diff -- docs/progress/STATUS.md
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_composition_review tests.test_evaluation -v
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.composition_review --manifest staging/composition-relevance-review-001/manifest.json
git diff --check
```

27tests đạt:9test mới về partial/dependency/null/accepted giả, binding,
evidence/cells, thiếu/trùng cặp, ngày và thiếu lý do;18hồi quy evaluation gồm
metric fixture/no-positive/missing/accepted gating. Fixture chỉ kiểm code.
Validator thực exit0:50query,500pairs,34outside positives,300v1proposals,
accepted0,metricsnull. Logs nguyên lệnh/stdout/stderr tại
`staging/composition-relevance-review-checks-001/command-1.log`,
`command-2.log`, thời điểm thật trong `executions.json`.

Các script thao tác hữu hạn được giữ trong run để audit:
`assemble_review.py` chỉ triển khai bảng phán đoán đã viết tay ở
`judgments.txt`, không phân loại bằng score/từ khóa; `prepare_pack.py` tạo
phiếu/báo cáo từ proposal. Tìm sâu gọi `search_loaded` với query gốc Top100,
không build. Binding/spans/details kiểm bằng adapter mới, nguồn không sửa.

Đối chiếu hash715file input của phiên:0thay đổi. Baseline trước962file gồm
raw/v1/draft3082/v3/index/evaluation/qrels/ZIP: chỉ3tài liệu đã sửa có sẵn
(AGENTS,ingestion,STATUS),0thay đổi ngoài dự kiến. Chi tiết
`staging/composition-relevance-review-checks-001/preservation.json`.

## Việc còn thiếu

Mở [hướng dẫn nhận phiếu](../handoff/Composition_Relevance_Review.md), bắt đầu
`calibration.md`:10query/19cặp, có bảng/text, đúng/sai/partial/uncertain,
dependency, đổiTop1 và limit. Template trống, chưa ghi reviewer/ngày/quyết
định. Cần người rà phản hồi đúng từng cặp đã xem; duyệt mẫu không duyệt500
nhãn hoặc coverage. Cần làm rõ loại xe ởD02/D03, điều kiện thời tiếtD05/D07,
ngữ nghĩa nhãnpartial/supporting/dependency và phạm vi đáp án bằng hết hạn.

Chưa có accepted labels/coverage approval nên chưa tính metrics, chưa có
CLI score accepted composition cho cả table type. Không rà pháp lý toàn văn,
không đánh giá test độc lập, không máy/OS khác hoặc Dense. Không đổi nhóm
sang phiên bản mới. Mọi con số review/test trên đây không xác minh pháp lý.
