# Báo cáo rà soát mã nguồn Legal Semantic Search

Ngày rà soát: 15/10/2026. Đối tượng: bản ZIP Legal Semantic Search.zip do người thực hiện cung cấp.

## 1. Kết luận

Dự án đã có prototype xuyên suốt: đọc DOCX/PDF, làm sạch, chia Khoản, sinh embedding, nạp Qdrant, truy hồi BM25 + Dense + RRF và giao diện Streamlit. Có thể giữ cấu trúc module và tái sử dụng nhiều hàm hiện có. Chưa đủ điều kiện coi corpus hiện tại là bản phát hành đã kiểm định hoặc dùng kết quả tìm kiếm để kết luận chất lượng bốn phương pháp theo SRS.

Ưu tiên sửa dữ liệu và tính đồng bộ chỉ mục trước khi tối ưu mô hình hoặc giao diện. Không cần thu thập lại tất cả nguồn nếu xác minh được nguồn gốc và tính đầy đủ của các tệp DOCX hiện có. Mô hình dữ liệu 12 bảng có thể triển khai theo từng phần; không cần chuyển đổi toàn bộ trong một lần.

Đây là báo cáo rà soát; chưa sửa mã nguồn người dùng.

## 2. Căn cứ và phạm vi kiểm tra

Đã đọc toàn bộ 10 module Python, schema JSON, manifest nguồn, requirements và hai tài liệu Markdown trong ZIP; kiểm tra bốn DOCX, bốn TXT sạch, hai JSONL và SQLite lưu trữ nội bộ Qdrant.

Đối chiếu với SRS v1.0, tài liệu kiến trúc v1.0 và thiết kế mô hình dữ liệu v1.0 đã lập trong phiên làm việc. Quyết định áp dụng: snapshot 2025-01-01; bốn mode bm25/dense/hybrid/hybrid_rerank; corpus bất biến có phiên bản; nguồn và ngữ cảnh truy vết được; không bộ lọc phương tiện hoặc time-travel ở v1.0; không sinh tư vấn pháp lý.

Các kiểm tra đã thực hiện:

- Kiểm tra cú pháp cả 10 module bằng AST: đạt.
- Chạy lại hàm extraction/cleaning trên bốn DOCX: khớp nguyên trạng bốn TXT trong ZIP.
- Chạy lại hàm chunking trên bốn TXT: khớp các chunk đã lưu theo từng văn bản.
- Kiểm tra toàn bộ JSONL: 1.457 chunk, ID duy nhất; 1.457 bản ghi embedding, mỗi vector 768 chiều; metadata của hai JSONL khớp nhau.
- Kiểm tra schema cũ bằng Draft7Validator: không có lỗi hình dạng. Điều này không chứng minh đúng hiệu lực, đúng nguồn hoặc đầy đủ nội dung.
- Đọc SQLite Qdrant ở chế độ chỉ đọc. Khi kiểm tra point đã tuần tự hóa, dùng bộ giải mã hạn chế chỉ chấp nhận lớp dữ liệu PointStruct thay thế; không chạy mã từ pickle.
- Tách và thử riêng logic analyze_query; không khởi tạo mô hình.

Chưa chạy ứng dụng Streamlit hoặc pipeline tìm kiếm end-to-end, chưa tải lại mô hình, chưa sinh lại embedding, chưa đo latency hay Recall/MRR/nDCG. Không xác nhận toàn bộ nội dung DOCX là bản chính thức đầy đủ chỉ từ tên tệp. Số từ phân cách bằng khoảng trắng không phải số token của tokenizer.

## 3. Những phần đã thực hiện được

| Hạng mục | Bằng chứng | Đánh giá |
|---|---|---|
| Nguồn dữ liệu ban đầu | Bốn DOCX và MANIFEST.csv | Có nền dữ liệu để tiếp tục |
| Extraction/cleaning | cleaner.py; NFC, khoảng trắng; DOCX và PDF reader | Tái tạo được kết quả DOCX hiện có |
| Structural chunking | chunker.py | Có Điều/Khoản, chưa đủ Chương/Mục/Điểm |
| Phân biệt text hiển thị và text truy hồi | original_text/enriched_text | Ý tưởng phù hợp; cần sửa hợp đồng và provenance |
| Dense embedding | embedder.py, JSONL 768 chiều | Có artifact thực tế; cần giải quyết độ dài và phiên bản |
| Qdrant | 1.457 point lưu cục bộ | Có database nhưng không đồng bộ vector hiện tại |
| BM25 và RRF | legal_retriever.py | Có triển khai thực; chưa tách mode chuẩn |
| Demo | frontend/app.py | Có giao diện; chưa xác nhận chạy trong môi trường sạch |
| Hợp đồng dữ liệu | chunk_schema.json | Có bước khởi đầu; thiếu các ràng buộc đã chốt |

Phân bố chunk: Luật 36: 441; Luật 35: 390; NĐ 168: 334; NĐ 165: 292. Không dùng con số 1.457 làm chỉ tiêu nghiệm thu cố định; sửa phạm vi và tách Điểm sẽ thay đổi số lượng hợp lệ.

## 4. Các lỗi cần sửa trước khi phát hành dữ liệu

### F01 — Qdrant và file embedding không đồng bộ — P0

Vị trí: src/database/qdrant_setup.py:13–20, 49–51; src/search/legal_retriever.py:245–262.

Database có 1.457 point; chunk_id tại mỗi vị trí khớp corpus JSONL. Tuy nhiên original_text và enriched_text trong tất cả payload đều null. So sánh vector theo ID với corpus_embedded.jsonl: cosine nằm trong khoảng 0,589402–0,981532; toàn bộ 1.457 cặp dưới 0,99999. Khác biệt không thể giải thích đơn thuần bằng chuẩn hóa độ dài vector.

Retriever sử dụng vector trong Qdrant để chọn ứng viên rồi lấy text từ self.chunks[doc_id]. Vì vậy không đủ căn cứ bảo đảm vector đại diện cho chính text đang trả về. Chưa xác định được nguyên nhân lịch sử tạo database.

Cần tạo lại chỉ mục từ corpus đã xác minh; lưu model revision, cấu hình, corpus_version và checksum. Dùng chunk_id làm khóa kết nối và UUID point xác định theo corpus_version + chunk_id, không dùng vị trí JSONL như định danh nghiệp vụ. Bổ sung kiểm tra tính tương thích trước khi nhận truy vấn.

Không chạy qdrant_setup.py hiện tại trên bản duy nhất cần giữ: module xóa collection ngay khi import/chạy. Thay bằng CLI có main guard, tạo collection mới theo build, kiểm định rồi kích hoạt.

### F02 — Gán hiệu lực mặc định cho mọi chunk — P0

Vị trí: src/ingestion/chunker.py:16–31 và hai nhánh tạo chunk; data/raw/MANIFEST.csv.

Ngày và trạng thái suy từ tên file, mặc định 2025-01-01/active. Không có xác minh ở cấp đơn vị, snapshot manifest hoặc quarantine.

Ví dụ đã thấy: chunk 36_2024_qh15_điều_10_k3 được gán active từ 2025-01-01. Trong bản luật ban hành, Điều 88 khoản 2 quy định khoản này hiệu lực từ 2026-01-01. NĐ 168 Điều 53 khoản 2 cũng nêu các ngoại lệ cho điểm m khoản 3 Điều 6; điểm e khoản 4 Điều 26; điểm b khoản 1 Điều 27; và mốc phụ thuộc quy định môi trường của điểm b khoản 1 Điều 32.

Cần unit_assessment gồm effective_from/effective_to, applicability_status, bằng chứng, người và ngày xác minh. Chỉ xuất đơn vị và context đủ điều kiện tại snapshot 2025-01-01. Chưa rõ mốc phải pending_review; không tự coi là active. Điều khoản hiệu lực vẫn có thể lưu làm bằng chứng; không loại toàn bộ Điều 53 chỉ vì nó nói đến 2026. Với một Khoản chứa các Điểm khác mốc, cần tách đơn vị trước khi chọn.

Nguồn kiểm tra bản ban hành:

- https://xaydungchinhsach.chinhphu.vn/toan-van-luat-trat-tu-an-toan-giao-thong-duong-bo-119240909105718285.htm — Điều 88.
- https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-dinh-168-2024-nd-cp-quy-dinh-xu-phat-vi-pham-hanh-chinh-ve-trat-tu-atgt-duong-bo-119241231164556785.htm — Điều 53.

Các nhận xét này phục vụ snapshot lịch sử, không khẳng định luật đang áp dụng tại ngày rà soát.

### F03 — Parser làm mất Chương và đoạn dẫn — P0

Vị trí: src/ingestion/chunker.py:55–66, 74–116.

Tất cả 1.457 chunk có chapter=null dù TXT có các dòng Chương I, Chương II… Regex yêu cầu ký tự phân cách sau số Chương nên không nhận dòng chỉ có Chương I sau strip(). Cần nhận tiêu đề một dòng hoặc hai dòng, lưu số và tên riêng.

Khi Điều có Khoản, intro_lines được đọc nhưng không lưu. Đã tìm 17 đoạn dẫn bị bỏ: 8 ở NĐ165, 6 ở Luật35, 3 ở Luật36. Ví dụ Điều22 Luật36 mất đoạn dẫn quy định việc quan sát, giảm tốc độ trước khi nhường đường; Điều26 mất phần xác định ngữ cảnh trong hầm. Đây là mất nội dung chứ không chỉ thiếu metadata.

Cần parser tạo cây Chương/Mục/Điều/Khoản/Điểm trước. Giữ nội dung riêng của cha và gắn đoạn dẫn vào context của con với nguồn/offset. Không tự viết lại phần điều kiện bị thiếu.

### F04 — Chưa tách Điểm; embedding cắt ở 256 token — P0

Vị trí: src/ingestion/chunker.py:118–171; src/ingestion/embedder.py:36–43.

point_id=null ở tất cả chunk. Mã hiện tại gộp mọi Điểm trong Khoản vào một chuỗi. 147 enriched_text có trên 256 đơn vị phân cách bằng khoảng trắng; dài nhất 8.318 ký tự, 1.864 đơn vị. Đây là thống kê độ dài, chưa phải phép đo tokenizer.

Embedding bật truncation=True,max_length=256 nhưng không ghi nhận phần bị cắt. BM25 đọc toàn bộ text trong khi Dense chỉ mã hóa tiền tố nếu quá giới hạn. Điều này có thể bỏ hành vi nằm ở cuối Khoản và làm sai lệch so sánh phương pháp.

Cần ưu tiên đơn vị Điểm/Khoản độc lập về nghĩa; khi tách Điểm giữ lead-in của Khoản, đối tượng áp dụng và khung phạt dưới dạng context có nguồn. Đếm token bằng tokenizer đã khóa phiên bản; đơn vị dài cần segment có offsets và kiểm tra phủ đủ nội dung. Không chỉ tăng max_length tùy ý.

### F05 — Extraction bỏ bảng và không giữ vị trí nguồn — P1

Vị trí: src/ingestion/cleaner.py:43–57.

read_docx chỉ đọc doc.paragraphs. Trong Luật35 có bảng nội dung về phí sử dụng đường bộ bị bỏ, không chỉ bảng quốc hiệu/chữ ký. Bảng có thể được đánh giá ngoài phạm vi ở bước scope, nhưng extraction cần ghi nhận trước khi có quyết định loại bỏ có lý do.

PDF reader bỏ qua trang không có text, không báo cần OCR; chưa chứng minh lỗi này xuất hiện trên bốn DOCX hiện có. Không lưu page/paragraph/table/cell locator. Regex cleanup chạy trên toàn văn cũng cần giới hạn vùng để tránh xóa nội dung giống chữ ký/tiêu đề.

Cần đọc paragraph và table theo thứ tự tài liệu, lưu extraction chuẩn hóa cùng locator/offset, báo trang rỗng và cách ly nguồn cần OCR. Giữ raw bất biến và nhật ký biến đổi; chưa cần xây OCR nếu tập nguồn đã có text đầy đủ và được kiểm chứng.

### F06 — Thiếu provenance và hợp đồng dữ liệu mới — P1

Vị trí: MANIFEST.csv; schemas/chunk_schema.json; đối tượng tạo trong chunker.py.

Manifest chỉ có tên file, mã/tên luật, ngày, trạng thái; chưa có source_url, retrieved_at, checksum, file_id/source_set_id. Chưa có corpus_version, nguồn chunk, source_locator, parent_unit_id, offsets, context có nguồn, hash nội dung hoặc bằng chứng hiệu lực.

original_text đang được dựng lại bằng tiêu đề Điều và chuỗi Khoản N:, không còn là một lát cắt nguyên văn. enriched_text thêm câu Theo…quy định; cần chuyển sang text_for_search theo công thức đã chốt, giữ text_original và context_text riêng.

Không chỉ đổi tên original_text thành text_original: phải sửa nội dung và khả năng đối chiếu với nguồn. Dùng mô hình legal_document/source_file/extraction/legal_unit/source_span/unit_assessment/chunk/chunk_context rồi xuất JSONL thống nhất. Schema và validator liên bảng bổ sung dần nhưng phải hoàn thành các cổng kiểm định trước release.

### F07 — Corpus truy hồi chứa phần ngoài phạm vi — P1

Vị trí: chunker.py và corpus_chunks.jsonl; docs/scope.md.

Hiện nạp toàn bộ nội dung parser nhận được. Ví dụ NĐ165 Điều3 về quy hoạch kết cấu hạ tầng, Điều29 về đấu nối trong quy hoạch đang là chunk truy hồi. Chưa có phân biệt included/supporting/excluded.

Cần ma trận coverage theo chủ đề/đối tượng và đánh giá phạm vi từng đơn vị. Lưu đầy đủ nguồn, nhưng chỉ đưa các đơn vị phù hợp vào index; các định nghĩa/dẫn chiếu hỗ trợ được giữ có kiểm soát. Bảy nguồn trong inventory là danh mục khảo sát, không phải yêu cầu lập tức thêm cả bảy vào corpus.

## 5. Các khác biệt ở truy hồi, ứng dụng và đánh giá

### F08 — Chưa có bốn pipeline thực nghiệm độc lập — P1

Vị trí: src/search/legal_retriever.py:227–335.

search luôn chạy query expansion, Dense, BM25, RRF rồi nhân trọng số thủ công theo hành vi, ý định và phương tiện. RRF đang có công thức hai danh sách đúng về hình thức, nhưng kết quả cuối không còn là Hybrid RRF thuần. Không có Cross-Encoder reranker.

Cần mode bm25, dense, hybrid, hybrid_rerank tách rõ, dùng cùng corpus/text_for_search; bật/tắt expansion/heuristic bằng cấu hình. Bốn baseline chính nên tắt heuristic để trả lời RQ1–RQ3; nếu giữ thì báo cáo như thí nghiệm bổ sung, tune chỉ trên dev. Không gọi heuristic rescoring là Cross-Encoder.

### F09 — Heuristic nhận diện và gán phương tiện sai — P1

Vị trí: legal_retriever.py:25–126,147–190,285–325.

Các ca thử tái hiện:

- Quy tắc nhường đường thế nào? → is_penalty=True vì chứa thế nào.
- xe máy chuyên dùng đi đường thế nào? → vehicle_key=xe_may do xét pattern chung trước.
- Tôi có đội mũ bảo hiểm đúng quy cách → nhận diện Không đội mũ bảo hiểm.
- đèn vàng nhấp nháy có được đi không? → gán nhãn vi phạm đèn tín hiệu.

Nhãn phương tiện dùng phép chứa Điều 6/7/8… mà không kiểm tra law_id và không so khớp số Điều chính xác. Điều60 Luật35 cũng khớp Điều6 và có thể bị gắn Xe ô tô. Logic tăng điểm theo article_hint còn tìm cả trong nội dung dẫn chiếu.

V1.0 đã loại bộ lọc phương tiện: bỏ UI và logic ép ưu tiên khỏi baseline. Nếu nghiên cứu heuristic riêng, cần xử lý phủ định, loại phương tiện cụ thể, câu hỏi quy tắc và nhãn có căn cứ. Không trình bày nhận diện bằng regex như kết luận pháp lý chắc chắn.

### F10 — Hai triển khai BM25 không thống nhất — P1

Vị trí: database/bm25_store.py:27–30; search/legal_retriever.py:12–14,136–145.

Builder dùng lower().split(), đọc EMBEDDED_FILE; retriever dùng regex \w+, đọc CHUNKS_FILE và dựng BM25 khi khởi tạo. File bm25_index.pkl không có trong ZIP và retriever cũng không load nó. Vì vậy code builder hiện không phải đường phục vụ thật.

Cần một tokenizer có phiên bản dùng nhất quán lúc build/query; index xây từ corpus chuẩn không phụ thuộc file vector. Theo kiến trúc đã chốt, chuyển sang BM25S Lucene và lưu row_index→chunk_id. rank_bm25 có thể giữ làm prototype đối chiếu nếu ghi rõ khác biệt. Việc đổi thư viện là căn chỉnh thiết kế; không tự bảo đảm Recall tốt hơn.

### F11 — Chưa có corpus/index/release manifest và rollback — P1

Vị trí: config.py:12–18; qdrant_setup.py; chunker.py và embedder.py khi ghi đầu ra.

Tên corpus và collection cố định, output ghi đè; chưa có staging, checksum, khóa phiên bản mô hình/config hoặc cơ chế kích hoạt/khôi phục. chunk_id dựa số Điều/Khoản vẫn giữ nguyên khi text thay đổi, không đáp ứng quy tắc định danh đã chốt.

Cần tách corpus_version, index_build_id, release_id; content hash và ID xác định; ghi staging rồi kiểm định. SQLite nội bộ của Qdrant trong ZIP không thay thế kho SQLite canonical theo thiết kế. Tạo kho nội dung phục vụ chỉ đọc, để retriever trả ID và ResultAssembler đọc nội dung cùng release.

### F12 — Giao diện/API khác SRS — P2

Vị trí: src/frontend/app.py.

Có Streamlit gọi trực tiếp retriever, không có FastAPI routes dù requirements có fastapi/uvicorn. Thiếu chọn mode, snapshot/corpus info, source_url, score_type và trạng thái khả dụng. Có bộ lọc phương tiện đã loại khỏi v1.0. Lời giới thiệu mới nhất không phù hợp corpus snapshot cố định.

Giữ Streamlit để debug trong quá trình sửa dữ liệu. Bản bàn giao theo kiến trúc cần FastAPI + frontend đã chốt, contract request/response, readiness/version checks, worker/queue/timeout và log từng chặng. Nếu muốn tiếp tục dùng Streamlit làm sản phẩm cuối, cần cập nhật SDD bằng quyết định thay đổi rõ ràng.

Score hiện tại là điểm RRF sau heuristic, không phải xác suất hay độ tin cậy pháp lý. Nhãn mức phạt trích bằng regex chỉ phản ánh chuỗi đầu tiên tìm thấy, không chứng minh trả lời đủ điều kiện tình huống. Ưu tiên hiển thị nguyên văn, context và nguồn.

### F13 — Chưa có bộ đánh giá định lượng — P1 trước báo cáo nghiên cứu

Vị trí: src/search/test_search.py:15,46; src/search/search_db.py.

test_search.py là script thử một câu, đọc corpus_embedded.jsonl ở đường dẫn gốc không khớp cấu trúc hiện tại và dùng item.get('text') trong khi dữ liệu có original_text. Nếu sửa đường dẫn mà giữ truy cập text, lát cắt trên None có thể gây lỗi. Script này cũng dùng SentenceTransformer, khác đường AutoModel/mean pooling đang phục vụ; cần thống nhất encoder trước so sánh.

Không thấy queries/qrels, split dev/test theo intent_group_id, evaluator, metric report hay benchmark latency trong ZIP. Cần xây sau khi chốt corpus; nhãn phải gắn corpus_version/chunk_id. Đo Recall@5/10, MRR@10, nDCG@10, latency từng chặng và p95 với cấu hình máy, warmup, số lượt chạy. Không lấy các câu demo làm bằng chứng cải thiện chất lượng.

### F14 — Chạy lại dự án chưa có cấu hình môi trường đầy đủ — P1

Vị trí: cleaner.py:70–72; requirements.txt; config.py.

CLI cleaner đọc raw_data và ghi cleaned_data, trong khi dự án dùng data/raw và data/processed/cleaned. requirements chưa khai báo python-docx/pdfplumber dùng trực tiếp; các dependency khác chưa khóa phiên bản. ZIP kèm venv Windows nhưng không thay thế hướng dẫn cài đặt đa máy.

Cần dùng chung config hoặc CLI flags, môi trường sạch, lockfile và README có lệnh theo thứ tự. Ghi cấu hình model/tokenizer revision, max_length, dimension thay vì hard-code 768 tại nhiều nơi. Mô hình BKAI hiện tại là prototype có thể tái dùng cho thí nghiệm; BGE-M3 trong SDD là ứng viên pilot, không phải lý do duy nhất buộc bỏ mô hình hiện tại. Quyết định mô hình bằng thử nghiệm dev và tài nguyên thực tế.

### F15 — Tài liệu trong repo không phản ánh chính xác code — P2

Vị trí: docs/architecture.md:17–33; docs/scope.md:5–8,38–41.

Tài liệu nói chia Khoản/Điểm nhưng code chưa tách Điểm; nói load index lưu sẵn nhưng retriever dựng lại; coverage 100% chưa có kiểm chứng, thực tế mất bảng/đoạn dẫn. Mô tả NĐ165 và NĐ168 trong scope.md không khớp văn bản raw; cần thay tên/trích yếu từ nguồn đã xác minh. Thay tiêu chí cố định 1.457 chunk bằng kiểm định phạm vi, độ đầy đủ, nguồn, cấu trúc và snapshot.

## 6. Lộ trình sửa đề xuất

### Đợt 1 — Khôi phục tính đúng của dữ liệu

- Chuẩn hóa đường dẫn, dependency và nguồn manifest.
- Giữ extraction nguyên trạng có nguồn; đọc bảng theo thứ tự.
- Sửa nhận diện Chương/Mục, giữ đoạn dẫn, tạo cây đơn vị.
- Tách Điểm khi cần và giữ context có nguồn; kiểm soát độ dài.
- Đánh giá scope và hiệu lực snapshot; cách ly phần chưa xác minh.

Đầu ra: legal units, source spans, assessments, chunks draft và báo cáo lỗi. Chưa cần embedding toàn corpus.

### Đợt 2 — Đóng băng corpus và xây lại chỉ mục

- Căn chỉnh schema/ID/hash với DDD, xuất SQLite và JSONL.
- Kiểm định, tạo corpus manifest.
- Xây BM25 và vector từ đúng tập chunk, thống nhất model/tokenizer.
- Kiểm tra ID/content/version, tạo release có thể rollback.

Đầu ra: corpus đã kiểm định, hai chỉ mục và release manifest. Database cũ giữ để đối chiếu, không dùng làm bản chuẩn.

### Đợt 3 — Hoàn thiện thực nghiệm

- Tách bốn mode và bổ sung Cross-Encoder.
- Xây queries/qrels có dev/test, khóa corpus.
- Chạy metrics, latency và error analysis; heuristic là ablation riêng nếu giữ.

Đầu ra: bảng kết quả tái lập được và các ca lỗi có bằng chứng.

### Đợt 4 — Hoàn thiện sản phẩm và bàn giao

- FastAPI/frontend theo SDD; snapshot, nguồn, score_type, mode và thông báo lỗi.
- Worker/queue/timeout, readiness, log và quy trình release.
- README, tài liệu repo, cấu hình và hướng dẫn demo khớp triển khai.

## 7. Tiêu chí kiểm tra cho lần sửa đầu

- Dòng Chương I riêng được nhận đúng, số và tên Chương không mất.
- Đoạn dẫn Điều22 Luật36 được giữ làm nội dung/context và truy về nguồn.
- Điểm thuộc Khoản xử phạt giữ đúng lead-in và khung phạt.
- Bảng Luật35 được trích xuất hoặc ghi rõ quyết định loại ở bước scope.
- Khoản3 Điều10 Luật36 không nằm trong tập kết quả áp dụng tại snapshot2025-01-01.
- Không chunk hoặc context quá giới hạn encoder bị cắt âm thầm.
- Sửa text hoặc context làm thay đổi identity/hash theo DDD; chạy lại không thay đổi dữ liệu thì ổn định.
- Mismatch corpus/index làm hệ thống không sẵn sàng, không trả text ghép theo vị trí.
- Cài môi trường mới và chạy lệnh ingestion được từ README.

## 8. Phân công phù hợp vai trò Data Engineer

Ưu tiên trực tiếp: nguồn/provenance; extraction/parser/chunker; scope và assessment phối hợp người rà soát pháp lý; schema/validator; corpus version; SQLite/JSONL; BM25/vector build và tính nhất quán release.

Phối hợp thành viên phụ trách retrieval: text_for_search, encoder config, ID mapping, candidate format, bộ đánh giá và trường hợp lỗi. Phối hợp backend/frontend: contract kết quả, metadata snapshot, nguồn và trạng thái corpus. Không cần một thành viên tự hoàn thiện toàn bộ API, UI và mô hình để chứng minh phần Data Engineering đã đạt yêu cầu.
