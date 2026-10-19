# BM25 experimental baseline — kiểm chứng

Ngày hoàn tất báo cáo: 2026-10-19 (Asia/Saigon). Snapshot tham chiếu **2025-01-01**.

Đã hoàn thành **build → save → load → search** trên BM25S 0.3.13 công thức Lucene (không phải Apache Lucene), k1=1.2, b=0.75, idf_method=lucene. Source/technical/applicability vẫn pending, experimental=true, release_eligible=false; không có reviewer event hoặc corpus verified.

## Đầu vào và số liệu thực

| Phân loại | Số lượng |
|---|---:|
| Unit của bốn cây DOCX | 4000 |
| Context-only | 877 |
| Preview upstream thành công | 3081 |
| Chunk được index | 3077 |
| Context được giữ | 5371 |
| Deferred | 46 |

| Văn bản | Chunk trong index |
|---|---:|
| 165/2024/NĐ-CP | 607 |
| 168/2024/NĐ-CP | 1018 |
| 35/2024/QH15 | 664 |
| 36/2024/QH15 | 788 |

Deferred: 4 ngoại lệ có bằng chứng snapshot; 20 vượt budget encoder; 13 lỗi source/context; 9 cấu trúc chưa hỗ trợ. 33 source-gap records được giữ riêng, có thể chồng lấn; không tạo unit giả hoặc cộng vào 46 như các target riêng.

Scope proposal trong index: included 94, excluded 64, pending 2.919. **Không lọc excluded/pending** khỏi tập kỹ thuật. 94 chunk pilot cũ là tập con khớp toàn bộ payload, ID/hash/source proof; không dùng chunk prototype hoặc PDF Điều 22 trộn vào cây DOCX.

Ngoại lệ: L36 Điều 10 khoản 3 có quote/rule bắt đầu 2026-01-01; NĐ168 A6K3m, A26K4e, A27K1b có ảnh đã capture trang 110/Điều 53 khoản 2. Liên kết unit/hash/ảnh/finding lưu config và deferred.jsonl/CSV; đây chỉ là selection origin=agent_review, không tạo ngày hiệu lực verified hoặc reviewer decision. Ngoại lệ A32K1b theo luật môi trường chưa có ngày đủ rõ nên vẫn pending. Không kết luận các đơn vị khác đều áp dụng tại snapshot.

## Artifact và binding

- Dataset: `staging/retrieval-dataset-v1-001/` — chunks.jsonl, contexts.jsonl, metadata.jsonl, deferred.csv/JSONL, dataset_statistics.json, manifest/version/content hash; support giữ bằng chứng token đo được, cây và cảnh báo để replay.
- Index: `staging/bm25-baseline-v1-001/` — engine CSC arrays/vocab/params native, document_mapping.jsonl, config/runtime, manifest và snapshot đúng dataset mới; không copy đệ quy lịch sử staging.
- Smoke: `staging/bm25-search-examples-001/search_examples.md` — Top-5 đầy đủ từng query, text/context/citation/score/tokens; JSON cùng tên chứa IDs và proofs.
- Log/bằng chứng kỹ thuật: `staging/bm25-baseline-verification-001/`.

Dataset version: `vtls-coverage-experimental.v1`. Content SHA-256: `2534731881e493a9b1b47b07470cc5d7f4fabbd9553d4e4d6c59e27359b313b5`.
Index version: `vtls-bm25s-lucene.v1`. Content SHA-256: `629f0214096d7ea013039af9253a5ed8f10f273f89da16f8cd56c69ff7130d18`.
Vocabulary 1630 token; CSC 207024 nonzero entries. Mapping kiểm internal_doc_id, chunk_id, unit_id, content hash, token count/hash; không dựa vị trí dòng ở file khác.

Bundle giữ payload text_original/context/search/citation/spans upstream nguyên vẹn. Source proofs relative với dataset root; trong index/result là base `dataset/`. URL DOCX chỉ là candidate, không xác minh nguồn gốc lịch sử toàn file. Schema DDD không đổi.

## Lệnh và kết quả đã chạy

Các lệnh dưới chạy từ root với `.venv-stage1/Scripts/python.exe -X utf8 -B`; log *_result.json giữ command argv, exit code và thời gian thực.

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.coverage_survey validate --manifest staging/stage6-coverage-001/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.retrieval_dataset build --coverage-manifest staging/stage6-coverage-001/manifest.json --scope-manifest staging/stage5-scope-survey-001/manifest.json --refinement-manifest staging/stage5-pilot-refinement-001/manifest.json --run-dir staging/retrieval-dataset-v1-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.bm25_baseline build --dataset-manifest staging/retrieval-dataset-v1-001/dataset_manifest.json --config config/bm25_baseline.v1.json --run-dir staging/bm25-baseline-v1-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.bm25_baseline validate --index-manifest staging/bm25-baseline-v1-001/index_manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.bm25_baseline search --index-manifest staging/bm25-baseline-v1-001/index_manifest.json --query "Nhường đường tại vòng xuyến" --top-k 5
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
```

Không chạy lại build vào các tên run đã tồn tại. README có lệnh tái tạo bằng tên local mới; chỉ search/validate có thể chạy lại ngay.

| Kiểm tra | Kết quả thực |
|---|---|
| Coverage validator toàn đầu vào | Exit 0, 227,09 s |
| Dataset build và validator replay | Exit 0, 359,82 s; giữ 3.077/3.081 |
| BM25 build/save/load/matrix replay | Exit 0, 133,16 s |
| CLI validate index/dataset riêng | Exit 0, 58,73 s |
| Suite hồi quy, đủ các VTLS_* | **245 test đạt**, không skip; 295,502 s |
| Test bổ sung mapping/tokenizer sau reseal | **1 test đạt**, 0,910 s |
| CLI negative | Query rỗng/chỉ dấu câu, top_k=0/2.5, thiếu index/dataset: exit 1/2 đúng; thiếu input không tạo output |
| Save/load fixture | Score float32 khớp rtol=1e-6, atol=1e-7; kết quả/tie ổn định |
| Mapping/content | Thứ tự input/mapping đổi vẫn liên kết đúng; trùng/thiếu/sai binding/hash/config bị từ chối |
| Search | Không gọi index(); chỉ score>0; OOV rỗng; top_k capped N; query 300 token lexical được chấp nhận |
| Import/search mới | Không import torch, SentenceTransformer, Qdrant, Transformers hoặc PyVi |
| Bảo toàn | **10.928 artifact cũ nguyên byte**, 125 file workspace cũ chỉ AGENTS/README đổi; HEAD không đổi; schema.sql khớp ZIP |
| Cú pháp/whitespace | AST/JSON parse đạt; git diff --check và --cached --check đạt; index Git không có file staged |

Suite lúc thu thập gồm 245 test; test mutation mới được thêm sau đó chạy riêng, không gọi cả suite cuối là đã chạy 246 trong một lượt. `regression_result.json` ghi đủ env VTLS_* cho các PDF/preview/Stage6/points/coverage/scope/refinement/pilot cũ và index mới.

Dependency: đã cài bm25s==0.3.13 vào venv hiện có (lần đầu network sandbox chặn, lần cài được phép thành công). NumPy 2.4.6, SciPy 1.17.1 sẵn có đúng pin; `pip check`: No broken requirements found. **Chưa thử venv sạch mới trong lượt này**. Source và METADATA thực cài/hash lưu engine_evidence; [tài liệu chính thức phiên bản 0.3.13](https://pypi.org/project/bm25s/0.3.13/). Không tải weights.

## Smoke và thời gian

Sáu query cố định `config/bm25_smoke.v1.json`, chọn sau khi đọc nội dung nguồn (`smoke_source_inspection.json`), trước khi xem ranking; mỗi query một process mới. Load gồm hash/read/JSON/mapping/import và saved arrays; search gồm tokenize/scoring/ranking/assembly; wall process tính riêng. Máy Windows 10.0.26200, Intel64 Family 6 Model 151, Python 3.11.9.

| Query | Load ms | Search ms | Hit |
|---|---:|---:|---:|
| roundabout | 1118.98 | 3.85 | 5 |
| motorcycle_stop | 1051.24 | 3.23 | 5 |
| night_horn | 1017.55 | 2.58 | 5 |
| driving_age | 1015.54 | 5.01 | 5 |
| licence_points | 972.91 | 4.32 | 5 |
| oov | 992.73 | 0.05 | 0 |

Vòng xuyến: Luật 36 Điều 22 khoản 3 hạng 1. Xe máy dừng/đỗ: nghĩa vụ báo tín hiệu chung hạng 1, xe máy chuyên dùng hạng 2; chưa phân biệt tốt đối tượng. Còi ban đêm: hạng 1 về đèn/báo hiệu hàng hóa; điều cấm còi L36 A21K2 hạng 4. Điểm GPLX: Top-5 là nội dung trừ điểm/giấy phép thật, chưa có L36 A58K1 tổng quan 12 điểm. Tuổi lái xe trộn điều kiện tuổi và chế tài chưa đủ tuổi. OOV trả rỗng. Đây là failure/giới hạn của lexical baseline, không sửa query/ranking để làm đẹp demo.

Không qrels, Recall/MRR/nDCG hoặc kết luận chất lượng toàn tập. Sáu smoke không chứng minh p95 hệ thống. Giới hạn tokenizer: không đồng nghĩa/cách viết GPLX/giấy phép, không hiểu phủ định hoặc quan hệ điều kiện chỉ từ giữ token; không phân biệt xe mô tô/xe máy chuyên dùng bằng mô hình ngữ nghĩa. Chưa tối ưu load: CLI kiểm full snapshot và token mapping mỗi process; đo hiện tại gồm các kiểm tra này.

## File thay đổi và giới hạn

| File | Mục đích |
|---|---|
| src/retrieval_dataset.py | Export/validate all-scope, reuse builder/proofs/evidence helpers; giữ cổng pending |
| src/bm25_tokenizer.py | Lexical tokenizer dùng chung, bản sao NFC/lowercase, giữ dấu/số/phủ định |
| src/bm25_baseline.py | BM25S build/save/load/search/validate, mapping tường minh và metadata |
| config/retrieval_dataset.v1.json | Chính sách tập mở rộng và ba ngoại lệ visual có binding |
| config/bm25_baseline.v1.json | Pin method/IDF/k1/b/tokenizer/tie |
| config/bm25_smoke.v1.json | Sáu query chức năng cố định |
| requirements-bm25.txt | Pin BM25S/NumPy/SciPy |
| tests/test_bm25_baseline.py | Fixtures synthetic và integration index thật; không trộn fixture vào dữ liệu thật |
| docs/design/data_model_v1/BM25_Experimental_Baseline_Contract.md | Contract thử nghiệm, semantics và giới hạn |
| docs/reviews/BM25_Experimental_Baseline_Verification.md | Báo cáo này |
| README.md, AGENTS.md | Lệnh PowerShell thực tế và phạm vi được phép |

Chưa chạy Dense/Hybrid/reranker/inference/embedding, xây Qdrant, tích hợp UI hoặc kích hoạt ứng dụng. Chưa sửa parser/nguồn/vùng thiếu/20 candidate dài và chưa xác minh hiệu lực toàn bộ. Bước tiếp theo chỉ là đề xuất: soạn bộ query có nhãn theo dataset hash để đánh giá ranking và failure cases trước khi đổi policy. Không tự triển khai bước tiếp hoặc thêm cổng duyệt thủ công.

Chưa stage/commit/push; Git HEAD giữ nguyên `2cef8e0`. Diff gồm 2 file có sẵn cập nhật và 10 file mới (source/tests/config/pin/contract/report); staging artifacts nằm ngoài Git.
