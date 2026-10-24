# Consumer/index BM25 composition — verification

2026-10-23, snapshot2025-01-01. HEAD đầu phiên
`bc2b2b7181a8e3fcdd7559f17135fa2b09cc3796`, worktree đầu phiên sạch.
Đã đọc AGENTS/STATUS, dataset contract/report, BM25 code/config/tokenizer và
evaluation thực tế. Contract trước build:
[Composition BM25 v1](../design/Composition_BM25_Contract_v1.0.md).
Không sửa corpus/index v1, draft v3, query cũ hoặc code validator/ranking cũ.

## Artifact và binding

| Artifact | Đường dẫn/version |
|---|---|
| Dataset input | staging/dataset-v3-draft-005/dataset_manifest.json |
| Dataset version | vtls-coverage-experimental.v3-draft.1 |
| Dataset manifest SHA | 1a17bbd11bfa00329c83fc1c31f4dade255f75a97df713a7a09db43f256d70b4 |
| Dataset content SHA | c20c30a7091cffb53090b704d3ab4414b0ebb250b7eb72c6bc21064882036bd2 |
| Index | staging/bm25-composition-001/index_manifest.json |
| Index version | vtls-bm25s-composition.v1 |
| Index manifest SHA | 6d285b850a8839e69dc2ecdbfd82a6d884310fb112b968db922d9ebbec09993e |
| Index content SHA | 60462a45b51b26d9e87eeff8e1ec91e81e5de0f59f5652b8dac73ea2f9d25d8a |
| Frozen queries | staging/composition-queries-001/manifest.json |
| Retrieval/review | staging/bm25-composition-evaluation-001/ |

Đã chạy validator dataset thực qua Consumer và frozen validate_read.py.
3.106 chunk.v1 +9 table-retrieval.v1 = **3.115 document BM25**. Mapping
internal_doc_id tăng liên tục theo record_id; record_type/ID/content/tokenhash
khớp toàn retrieval membership. Không lọc scope, không thêm 23 required-read
bindings hoặc candidate279 token thành document. Không merge9 rows theo owner.

Consumer dùng portable.resolve/descriptor/mounts đã đóng gói; validate một
lần rồi cache snapshot. bound_read cho kết quả bằng portable.read gốc ở các
ca kiểm thực, không resolve reference lại. Detail gồm nguyên văn, derived
table riêng, contexts, source spans/cells/header/conditions và mọi dependency
units/spans theo ID. Phần/Chương lặp của TT35 giữ riêng theo graph. Không
flatten nguồn DOCX/HTML hoặc suy unit trong dependency thành target đã rank.

## Projection, engine và tính độc lập

Text và table đều index đúng text_for_search hash-bound. Source_original của
bảng không bị thay bằng derived_text. Không ghép thêm subtree vào BM25 text.
Tái dùng baseline.engine/rank/runtime/tokenizer, BM25S0.3.13 Lucene k1=1.2/
b=.75, float32/int32, numpy backend. Query lexical Unicode giữ nguyên, không
PyVi/BPE/stopword/stem/expansion/boost. Adapter mapping truyền record_id vào
khóa tie của rank cũ trong bộ nhớ; không lưu tr_ thành chunk_id trong payload.
Tie score giảm/record_id tăng; score0 không trả, không đệm.

Index package127.594.824bytes inventory gồm dataset, engine, mapping/runtime/
config và src tối thiểu; không venv/weights/staging history. Đã copy sang
staging/composition-bm25-independent-001/bundle, tạo venv sạch rồi pip install
offline ba wheel đúng pins lấy từ pip HTTP cache. Không tải mạng hoặc đổi
model để chạy được. Packages chỉ bm25s/numpy/scipy cùng pip/setuptools.

Python3.11.9 Windows; standalone isolated/audit hook chặn open workspace bên
ngoài folder thử. Validate rebuild sparse arrays đạt, search đạt, read đạt cho
table, TT35 có dependency và TT38 A4K2 chứa source Điểm b trong subtree.
Không đọc ngầm staging gốc; engine source hashes/config/runtime được kiểm.
Đây không phải kiểm chứng máy/OS khác. Validate/read dataset riêng stdlib;
search/validate index cần sparse dependencies như Quickstart.

## Queries, review và metrics

Trước build/ranking mới đã seal30query cũ nguyên byte theo manifest evaluation
cũ,15query development mới và5case giới hạn; files config không sửa sau ranking.
15mới có direct/paraphrase/scenario về xe/đường, tốc độ/khoảng cách/boundaries,
GPLX và dependency, là corpus-derived development, không phải test độc lập.

50queries →500 Top10 results,313 unique detail records,0query error.
Các số này không phải Recall/MRR/nDCG. Batch load index mới một lần (run đo
khoảng5.042 ms, tức khoảng5,04giây gồm kiểm integrity/consumer), tách search và detail từng query.
Không lấy thời gian load này làm latency ranking hoặc SLA trên máy khác.

annotations.jsonl có500 phiếu pending/relevance=null, relation_to_query=null;
cho phép reviewer phân biệt direct_target/dependency_only/unrelated. Qrels
rỗng, không chuyển nhãn v1, không ghi human review. metrics chính thức **null**,
eligible_queries=0, PENDING_LABELS. Annotation sheet có nguyên văn/derived/
context và link detail đầy đủ; score không phải xác suất hoặc độ tin cậy pháp lý.

Các ví dụ quan sát, chưa phải judgment accepted:

- V3-D05 hỏi đúng60km/h: rank1 là row V=60/35m; row60<V≤80/55m rank2.
  Context điều kiện khô ráo vẫn ở detail, không phát biểu luật cho mọi thời tiết.
- V3-D07 hỏi so81với80: hai row60<V≤80/55m và80<V≤100/70m ở rank1/2.
  BM25 không suy luận bất đẳng thức; cần đọc hai vùng nguồn, không lấy Top1
  làm câu trả lời hoàn chỉnh.
- V3-D10 hỏi bằng số tự động lái số sàn: rank1 TT35 A32K5, nguyên văn/phạm vi
  đọc được. Đây là ví dụ retrieval, không test bắt buộc câu này phải Top1.
- V3-L05 mưa: Top đầu là các row bảng điều kiện khô ráo; Điểm b chỉ có trong
  source dependency của A4K2. Có thể read nguyên văn b đầy đủ, nhưng b không
  có document/rank riêng. Cần reviewer xác định direct hay dependency-only;
  không cộng source unit này vào recall denominator như một target rank.

Nhóm giới hạn được đối chiếu selection/graph/component, không suy từ miss:
formXI/XXVI withheld; QCVN không target; tiêu chuẩn y tế chi tiết không phải
component; Điểm b target quarantine nhưng source dependency có. Một số source
evidence/reference vẫn tồn tại, nên không gọi mọi câu này là toàn corpus thiếu
đáp án. coverage_status vẫn pending_review, chi tiết coverage_limits.jsonl.

## So sánh v1 và kiểm thử

Chạy30query trên chính v1 giữ đúng ID/score historical run với tolerance cũ.
Trên v3 có12/30 thay Top10 IDs,1/30 thay Top1. Query “Bằng lái hết hạn có được
đổi không?” đổi từ Luật35 A62K2b sang TT35 A32K7 (quy định nhận diện GPLX).
Kết quả này cần review relevance/coverage; không kết luận v3 tốt hơn. Các score
cũng có thể đổi khi IDs giữ nguyên do IDF/length statistics. Không chỉnh query.

25tests consumer/index + metric/evaluation fixtures đạt28,707s. Suite v1:
14unit tests đạt,4actual-index tests ban đầu skip do chưa set env; đã chạy riêng
cả4 actual tests với manifest v1 và đạt24,116s. Không cộng skip thành pass hoặc
fixture thành bằng chứng pháp lý. Actual tests gồm validate/save-load/search,
patch compatibility warning và resealed mapping/tokenizer lỗi.

Tests mới phủ projection cảhai types/membership, tie, Part lặp, tablecells,
frozen-reader parity, source b không target, capability/path containment;
reseal sai dataset hash/snapshot/path/rowID/dependency/type đều bị từ chối.
Các kiểm nội dung/binding độc lập ranking, không ép query nghiệp vụ Top1.

Audit run_consistency.json kiểm ranks liên tục, score hữu hạn/giảm, ID/type
đúngmapping, detail tồn tại, query bytes unchanged. Manifest/file inventory
được seal. Chưa có đánh giá relevance đã được chấp nhận cho v3.

## Thay đổi và bàn giao

Thêm composition_consumer.py, composition_bm25.py, composition_evaluation.py,
hai config query mới, tests, contract, Quickstart và báo cáo này; cập nhật
AGENTS/STATUS/ingestion guide. Không sửa BM25 v1/tokenizer/evaluation code,
dataset hoặc source/history để cải thiện query. Dataset/index nhóm dùng và
draft3082/3106+9, evaluation/qrels/ZIP cũ giữ nguyên.

Lệnh đầy đủ: [Composition BM25 Quickstart](../handoff/Composition_BM25_Quickstart.md).
Consumer/index mới sẵn cho review/evaluation; scope/nguồn/edition/applicability
còn pending/proposed. Chưa sinh câu trả lời, UI/API, Dense/embedding/Qdrant/
reranker, OCR hoặc chuyển phiên bản cho nhóm. Không stage/commit/push.
