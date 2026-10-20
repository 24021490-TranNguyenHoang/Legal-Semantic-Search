# BM25 development evaluation — kiểm chứng

Source đầu lượt `1e39d16e0ec776a400474182f907aa2d8d4cba04`, Git sạch.
Đọc AGENTS, STATUS, Quickstart, contract BM25, BRD §3, SRS phần evaluation,
DDD §14 và mã loader/search thực tế. Không tìm thấy qrels/query set
evaluation của nhóm trong repository/data; có smoke config gồm sáu câu.
Tái sử dụng năm câu nghiệp vụ nguyên văn, câu OOV giữ riêng ở smoke.
Không phải xác nhận nhóm không có tài liệu ngoài repository.

## Kết quả thực

| Mục | Kết quả |
|---|---|
| Dataset | vtls-coverage-experimental.v1 — 3.077 chunk |
| Dataset content SHA-256 | 2534731881e493a9b1b47b07470cc5d7f4fabbd9553d4e4d6c59e27359b313b5 |
| Index | vtls-bm25s-lucene.v1 |
| Index content SHA-256 | 629f0214096d7ea013039af9253a5ed8f10f273f89da16f8cd56c69ff7130d18 |
| Query | 30 dev, 10 intent × direct/paraphrase/scenario |
| Batch | load một lần, 30 success, 0 error, 300 kết quả |
| Timing | load 1.658,79 ms; tổng search 100,82 ms; tuần tự, không warmup |
| Annotation hiện tại | 5 proposed agent, 295 pending, 0 accepted |
| Qrels được chấp nhận | 0 |
| Query đủ điều kiện metrics | 0/30; tất cả chưa rà độ đầy đủ nhãn |
| Metrics | null — không báo Recall/MRR/nDCG chính thức |
| Corpus coverage gap | chưa có kết luận; 30 câu coverage pending |

Ba chủ đề nghiệp vụ chính BRD có mặt: quy tắc giao thông, hành vi/xử phạt,
GPLX/điểm GPLX. Đây là coverage của bản dự thảo, không chứng minh mẫu đại
diện toàn bộ nhu cầu. Câu hỏi đổi GPLX cần kiểm độ đầy đủ nguồn.

Năm proposal đọc nội dung thực gồm: vòng xuyến direct=2, đèn tín hiệu
ô tô direct=2, còi ban đêm direct=0, mũ bảo hiểm direct=1, đổi GPLX direct=1.
Mỗi proposal chỉ cho một cặp query/chunk, không khẳng định qrels câu đó đủ.
Top đầu “Dùng còi ban đêm” nói về báo hiệu hàng hóa, không về còi;
query giữ nguyên. Nhóm đổi GPLX có top đầu về GPLX hết hạn không có hiệu
lực, chưa trả lời điều kiện đổi; không suy toàn dataset thiếu căn cứ.

## Artifact và đường chạy

- `staging/bm25-evaluation-dev-001/`: queries, run, outcomes, timings,
  300 phiếu pending có nguyên văn/context/citation/source spans; manifest
  binding dataset/index và hash từng file.
- `staging/bm25-evaluation-review-001/submission.json`: mẫu tiếp nhận
  nhãn, có năm proposal thực của agent. `proposals.md` dễ đọc;
  `coverage_status.md` liệt kê từng câu và điểm ưu tiên rà.
- `staging/bm25-evaluation-labels-001/`: score từ submission chỉ-proposal,
  giữ bản submission và hash parent; trạng thái PENDING_LABELS.
- `staging/bm25-evaluation-verification-001/verification.json`:
  command/exit/stdout/stderr thực, hash source evaluation, preservation.
  Có fixture submission sai binding để thử từ chối; không dùng làm nhãn.

Các lệnh đã chạy từ root repository bằng `.venv-stage1\Scripts\python.exe`:

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.evaluation batch --index-manifest staging/bm25-baseline-v1-001/index_manifest.json --queries config/evaluation_dev.v1.jsonl --run-dir staging/bm25-evaluation-dev-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.evaluation validate --index-manifest staging/bm25-baseline-v1-001/index_manifest.json --bundle staging/bm25-evaluation-dev-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.evaluation score --index-manifest staging/bm25-baseline-v1-001/index_manifest.json --bundle staging/bm25-evaluation-dev-001 --submission staging/bm25-evaluation-review-001/submission.json --run-dir staging/bm25-evaluation-labels-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.evaluation validate --index-manifest staging/bm25-baseline-v1-001/index_manifest.json --bundle staging/bm25-evaluation-labels-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_evaluation tests.test_bm25_baseline.RuntimeCompatibilityTests tests.test_bm25_baseline.LexicalTests tests.test_bm25_baseline.SelectionTests
```

Tất cả exit 0. 18 test evaluation và 14 test regression BM25 đạt, gồm
graded/multiple positives, tính tay nDCG, khác cutoff 5/10, hit sau 10,
không hit, danh sách ngắn, duplicate, thiếu judgment, no-positive,
query error đóng góp 0, nhãn agent không được accepted, evidence sai,
intent leakage, manifest hash/binding sai.

CLI score với `staging/bm25-evaluation-verification-001/invalid_binding.json`
trả exit 1: `Submission binding mismatch`; thư mục `must-not-exist` không
được tạo. Hash toàn inventory index và standalone dataset khớp. Queries
trong run bằng đúng bản config đã chốt. Loader, tokenizer, config BM25 và
builder Điểm bằng byte HEAD. Không build lại index, thay preprocessing
hay sửa nguồn. Không chạy lại suite pipeline toàn bộ vì không thay các
thành phần đó. Không kiểm máy/OS khác, Dense/Hybrid/Reranker.

## Thay đổi và việc người phụ trách cần xem

Thêm `src/evaluation.py` (batch/validate/score và metrics), fixture tests,
config 30 câu, contract và Quickstart; cập nhật README/STATUS. Không thêm
dependency hay framework. Đầu ra chỉ trong các run staging mới.

Long/nhóm cần:

1. Rà độ rõ và phạm vi 30 câu; bộ này là dev đã xem kết quả, không đưa
   intent/paraphrase sang test cuối. Nếu cần sửa câu, tạo phiên bản mới và
   ghi lý do, không ghi đè bản đã chạy.
2. Rà 300 cặp, bác/sửa/nhận năm proposal theo nội dung; bổ sung positive
   ngoài BM25 pool. Chú ý đối tượng xe, ngưỡng, mức phạt và context.
3. Ghi đủ căn cứ/người/thời gian thực trong submission mới; ghi độ đầy đủ
   qrels và coverage gap nếu có bằng chứng. Phần chưa đọc giữ pending.
4. Chạy score vào run mới; xem số câu bị loại trước khi đọc macro metrics.

Development relevance review không thay source/applicability verification.
Nguồn legacy và corpus tiếp tục pending; các test không xác nhận chất
lượng pháp lý. Chưa có metrics thực để báo chất lượng retrieval.
