# Tài liệu yêu cầu nghiệp vụ

# **Hệ thống tra cứu pháp luật giao thông Việt Nam**

Vietnamese Traffic Legal Semantic Search

BRD phiên bản 1.0 • Ngày 4 tháng 10 năm 2026

Tài liệu xác định bài toán, phạm vi, yêu cầu nghiệp vụ và bằng chứng nghiệm thu cho bài tập nhóm Legal AI. Đây là cơ sở để nhóm xây dựng SRS, thiết kế hệ thống, thiết kế dữ liệu và kế hoạch đánh giá.

Hệ thống thực hiện tra cứu tại một mốc dữ liệu xác định. Corpus được mở rộng ngoài bốn văn bản khởi đầu theo phạm vi pháp luật áp dụng trực tiếp cho người tham gia giao thông. Tra cứu lịch sử hiệu lực thuộc phạm vi mở rộng.

| Thuộc tính | Thông tin |
| :---- | :---- |
| Mã tài liệu | BRD-VTLS-1.0 |
| Trạng thái | Báo cáo yêu cầu nghiệp vụ phiên bản 1.0 |
| Chủ trì rà soát | Hoàng — Trưởng nhóm |
| Đầu mối dữ liệu | Dữ liệu & Sparse/Hybrid |
| Căn cứ | Đề bài Project 2 và đặc tả phạm vi dự án. |
| Thông tin còn mở | Mốc dữ liệu, danh mục corpus cuối cùng, ngưỡng quy mô, hạn nộp, phần cứng và ngưỡng hiệu năng. |

## **Cấu trúc tài liệu**

1 Bối cảnh và mục tiêu 

• 2 Các bên liên quan • 3 Phạm vi và tình huống sử dụng • 4 Yêu cầu nghiệp vụ • 5 Yêu cầu dữ liệu • 6 Tiêu chí thành công • 7 Rủi ro và quyết định • 8 Rà soát và truy vết

## **Lịch sử phiên bản**

1.0 — 14/10/2026: ban hành tài liệu yêu cầu nghiệp vụ, xác định phạm vi một mốc dữ liệu, yêu cầu mở rộng corpus và tiêu chí nghiệm thu.

# **1 Bối cảnh và mục tiêu**

## **1 1 Vấn đề cần giải quyết**

Người tham gia giao thông thường mô tả hành vi hoặc tình huống bằng tiếng Việt đời thường, trong khi văn bản pháp luật sử dụng thuật ngữ và cấu trúc pháp lý. Người dùng có thể không biết số hiệu văn bản hoặc vị trí điều khoản cần tìm. Dự án giải quyết khoảng cách giữa cách đặt câu hỏi và cách diễn đạt trong nguồn pháp luật.

Dự án đánh giá khả năng cải thiện truy hồi của Dense, Hybrid và Hybrid kết hợp Reranker so với BM25 trên cùng corpus. Kết quả được xác định bằng thực nghiệm, chỉ số định lượng và phân tích trường hợp lỗi.

Việc đánh giá nhu cầu tra cứu được thực hiện thông qua các tình huống sử dụng và bộ truy vấn đại diện. Các lợi ích về chất lượng truy hồi được kiểm chứng trong giai đoạn đánh giá hệ thống.

## **1 2 Mục tiêu và giá trị**

| Mã | Mục tiêu | Bằng chứng dự kiến |
| :---- | :---- | :---- |
| OBJ-01 | Tìm được điều khoản liên quan từ câu hỏi tự nhiên. | Bộ truy vấn trực tiếp, diễn đạt lại và tình huống; Recall@10. |
| OBJ-02 | Cho phép người dùng đối chiếu căn cứ gốc. | Kết quả có nguyên văn, vị trí trích dẫn và nguồn. |
| OBJ-03 | Chứng minh hiệu quả của các phương pháp truy hồi. | So sánh bốn cấu hình trên cùng corpus và test set. |
| OBJ-04 | Xây dựng sản phẩm có thể chạy và trình diễn. | Demo tìm kiếm, ca lỗi, báo cáo chất lượng và độ trễ. |
| OBJ-05 | Bảo đảm corpus đủ bao phủ và đủ thách thức để đánh giá. | Thống kê corpus, ma trận bao phủ và biên bản chốt quy mô. |

## **1 3 Câu hỏi thực nghiệm**

RQ1: Dense cải thiện hoặc suy giảm so với BM25 ra sao, đặc biệt với truy vấn diễn đạt lại và tình huống? RQ2: Hybrid có cải thiện Recall@10 và thứ hạng so với từng phương pháp riêng? RQ3: Hybrid kết hợp Reranker cải thiện thứ hạng bao nhiêu và làm thay đổi độ trễ thế nào?

## **1 4 Ranh giới của kết quả**

Kết quả là danh sách điều khoản được xếp hạng cùng nội dung gốc và căn cứ. Điểm xếp hạng không được trình bày như xác suất đúng pháp lý. Hệ thống không tự sinh tư vấn, kết luận mức phạt tổng hợp hoặc thay thế việc đối chiếu đầy đủ quy định.

# **2 Các bên liên quan và trách nhiệm**

## **2 1 Người sử dụng và bên đánh giá**

Người dùng chính là người tham gia giao thông muốn tìm căn cứ cho một hành vi hoặc tình huống. Sinh viên luật và chuyên viên pháp lý là người dùng phụ, sử dụng kết quả để tham khảo và đối chiếu nguồn. Giảng viên đánh giá mức độ đáp ứng đề bài và bằng chứng thực nghiệm.

## **2 2 Phân công trách nhiệm**

| Thành viên | Vai trò | Trách nhiệm liên quan đến BRD |
| :---- | :---- | :---- |
| Hoàng | Trưởng nhóm & Mô hình truy hồi | Điều phối phạm vi; phụ trách phần mô hình; tổng hợp các quyết định và rà soát tính khả thi. |
| Dữ liệu | Dữ liệu & Sparse/Hybrid | Nguồn và corpus; kiểm soát dữ liệu; phần Sparse/Hybrid; cung cấp thống kê và đánh giá độ bao phủ. |
| Long | Đánh giá & Phân tích | Kế hoạch đánh giá; điều phối nhãn; metrics; phân tích kết quả và failure cases. |
| Hùng | Hạ tầng & Ứng dụng | Môi trường chạy; tích hợp ứng dụng; trải nghiệm tìm kiếm; đo vận hành phối hợp với Long. |

Bộ phận Dữ liệu & Sparse/Hybrid phối hợp với Hoàng trong thiết kế và tích hợp truy hồi lai. Long điều phối đánh giá và rà soát chéo nhãn liên quan pháp lý. Hùng phụ trách tích hợp các thành phần vào ứng dụng và môi trường vận hành.

## **2 3 Đầu mối các quyết định**

| Quyết định | Chủ trì | Người phối hợp |
| :---- | :---- | :---- |
| Phạm vi nghiệp vụ và thay đổi lớn | Hoàng | Cả nhóm |
| Danh mục nguồn và mốc corpus | Phụ trách dữ liệu | Hoàng, Long |
| Độ bao phủ và mức đủ lớn của dữ liệu | Phụ trách dữ liệu và Long | Hoàng tổng hợp; xin ý kiến giảng viên |
| Quy tắc relevance và dev/test | Long | Phụ trách dữ liệu, Hoàng |
| Khả năng triển khai và benchmark | Hùng | Hoàng, Phụ trách dữ liệu, Long |

## **2 4 Cách ghi nhận thống nhất**

Các quyết định về phạm vi, dữ liệu và tiêu chí nghiệm thu được ghi trong nhật ký thay đổi. Tài liệu được rà soát bởi các đầu mối phụ trách trước khi sử dụng làm cơ sở cho SRS và thiết kế.

# **3 Phạm vi và tình huống sử dụng**

## **3 1 Phạm vi bản đầu**

Hệ thống hỗ trợ tìm kiếm tiếng Việt trong corpus pháp luật giao thông đường bộ được lựa chọn và xác minh tại một mốc dữ liệu. Chủ đề tập trung vào quy tắc giao thông, giấy phép lái xe và điểm GPLX, hành vi vi phạm và xử phạt áp dụng trực tiếp cho người tham gia giao thông.

Điều kiện phương tiện, kiểm định, đăng ký hoặc nội dung liên quan chỉ được đưa thành use case cam kết khi có nguồn đủ bao phủ và được nhóm chốt. Giao diện công bố mốc corpus; bản đầu không cung cấp bộ lọc ngày lịch sử cho người dùng.

## **3 2 Tình huống sử dụng ở mức nghiệp vụ**

| Mã | Nhu cầu | Kết quả mong đợi |
| :---- | :---- | :---- |
| UC-01 | Tìm căn cứ liên quan đến hành vi vi phạm. | Các điều khoản phù hợp với hành vi và đối tượng được mô tả. |
| UC-02 | Tìm quy tắc tham gia giao thông. | Nội dung quy tắc và thông tin trích dẫn để đối chiếu. |
| UC-03 | Tra cứu GPLX và điểm GPLX trong corpus. | Điều khoản liên quan; không suy luận thay người dùng. |
| UC-04 | Kiểm tra nguồn của một kết quả. | Xem nguyên văn, văn bản, vị trí và nguồn tương ứng. |
| UC-05 | So sánh các cấu hình của nhóm. | Kết quả chất lượng và độ trễ trên cùng dữ liệu kiểm thử. |

## **3 3 Ngoài phạm vi và mở rộng**

Ngoài phạm vi: sinh câu trả lời bằng LLM/RAG; nhận diện biển báo hoặc camera; dữ liệu bản án; ngành luật khác; quy hoạch, xây dựng hạ tầng và quản lý vĩ mô. Không cam kết bao phủ toàn bộ pháp luật giao thông Việt Nam.

Mở rộng sau bản đầu: time-travel có dữ liệu phiên bản; cập nhật nguồn tự động; phạm vi chủ đề mới. Mỗi mở rộng phải đánh giá tác động đến dữ liệu, nhãn, hiệu năng và thời gian.

## **3 4 Luồng nghiệp vụ tổng quát**

Người dùng kiểm tra phạm vi dữ liệu, nhập tình huống, nhận danh sách kết quả và mở căn cứ nguồn. Nếu câu hỏi thiếu thông tin, kết quả có thể bao gồm nhiều trường hợp; hệ thống không tự khẳng định một đối tượng áp dụng mà người dùng chưa nêu. Khi không có kết quả hoặc truy vấn ngoài phạm vi, không diễn giải điều đó thành kết luận rằng pháp luật không có quy định.

# **4 Danh mục yêu cầu nghiệp vụ**

Mức M là yêu cầu cốt lõi của bản đầu; mức E là mở rộng. Các yêu cầu dưới đây được chuyển thành chức năng, tiêu chí kiểm thử và thiết kế trong tài liệu tiếp theo.

| Mã | Yêu cầu nghiệp vụ | Mức | Kiểm chứng |
| :---- | :---- | :---- | :---- |
| BR-01 | Tra cứu bằng câu hỏi tiếng Việt tự nhiên trong miền hỗ trợ. | M | Demo và test set |
| BR-02 | Trả danh sách điều khoản được xếp hạng, giới hạn số kết quả theo lựa chọn hợp lệ. | M | Kiểm thử luồng tìm kiếm |
| BR-03 | Hiển thị nguyên văn, văn bản và vị trí Điều/Khoản/Điểm phù hợp. | M | Đối chiếu nguồn |
| BR-04 | Truy ngược được kết quả về nguồn và phiên bản corpus sử dụng. | M | Kiểm tra truy vết |
| BR-05 | Công bố phạm vi và mốc dữ liệu; không tự nhận là dữ liệu mới nhất. | M | Rà soát giao diện |
| BR-06 | So sánh BM25, Dense, Hybrid và Hybrid \+ Reranker trên cùng dữ liệu. | M | Báo cáo thực nghiệm |
| BR-07 | Có bộ đánh giá riêng và tách dữ liệu tinh chỉnh khỏi test cuối. | M | Kiểm tra bộ đánh giá |
| BR-08 | Có báo cáo độ trễ và ít nhất một failure case trong demo. | M | Benchmark và demo |
| BR-09 | Mở rộng corpus theo độ bao phủ; báo cáo quy mô sau làm sạch và loại trùng. | M | Báo cáo corpus |
| BR-10 | Duy trì bản nguồn, nhật ký xử lý và phiên bản để tái tạo dữ liệu. | M | Chạy lại quy trình |
| BR-11 | Thể hiện rõ đầu vào không hợp lệ, lỗi hệ thống và trạng thái không có kết quả. | M | Kiểm thử ngoại lệ |
| BR-12 | Tra cứu theo ngày trong lịch sử đã được xác minh. | E | Đặc tả giai đoạn sau |

## **4 1 Quy tắc nghiệp vụ đi kèm**

RULE-01: chỉ cam kết khả năng tra cứu trong corpus đã công bố. RULE-02: không làm thay đổi nội dung pháp lý gốc khi chuẩn hóa. RULE-03: ngữ cảnh bổ sung phải truy về nguồn. RULE-04: điểm xếp hạng không phải độ tin cậy pháp lý. RULE-05: các kết luận cải thiện chất lượng chỉ dựa trên test set đã đóng băng.

RULE-06: nội dung chưa xác minh nguồn hoặc hiệu lực không được đưa vào corpus tra cứu chính của mốc đã chốt. RULE-07: không tăng quy mô bằng bản trùng hoặc chia vụn làm mất nghĩa. RULE-08: không coi kết quả rỗng là bằng chứng không tồn tại quy định.

# **5 Yêu cầu về dữ liệu và quy mô corpus**

## **5 1 Corpus khởi đầu và hướng mở rộng**

Corpus khởi đầu gồm các văn bản có số hiệu 36/2024/QH15, 35/2024/QH15, 168/2024/NĐ-CP và 165/2024/NĐ-CP. Danh mục nguồn chính thức phải ghi tên văn bản, nguồn công bố, nội dung được sử dụng và tình trạng áp dụng tại mốc dữ liệu. Việc kiểm tra nguồn và hiệu lực là điều kiện trước khi phát hành corpus.

Corpus được mở rộng theo độ bao phủ chủ đề và đối tượng tra cứu. Các nhóm nguồn khảo sát gồm văn bản sửa đổi hoặc thay thế; quy tắc và báo hiệu đường bộ; GPLX và điểm GPLX; xử phạt; điều kiện phương tiện thuộc phạm vi dự án. Danh mục đưa vào corpus được xác định sau bước rà soát nguồn.

## **5 2 Tiêu chí lựa chọn và loại trừ**

Một nguồn được chọn khi có xuất xứ kiểm chứng được, liên quan trực tiếp đến chủ đề, xác định được khả năng áp dụng tại mốc corpus và có thể trích xuất hoặc rà soát nội dung. Nguồn dùng để xác minh lịch sử có thể được lưu ở tầng dữ liệu thô nhưng không tự động trở thành kết quả tra cứu.

Loại khỏi tập truy hồi chính: bản trùng, nội dung ngoài phạm vi, đoạn thiếu nguồn, dữ liệu lỗi chưa sửa và phiên bản không áp dụng tại mốc đã chọn. Nếu sử dụng văn bản hợp nhất để hỗ trợ đọc, phải lưu rõ loại tài liệu và quan hệ nguồn; không tính nội dung lặp thành dữ liệu mới.

## **5 3 Cách xác định dữ liệu đủ lớn**

| Chiều đo | Bằng chứng cần có |
| :---- | :---- |
| Độ bao phủ | Ma trận chủ đề × loại phương tiện/đối tượng × nguồn; chỉ ra ô có dữ liệu và khoảng trống. |
| Quy mô thực | Số văn bản/phiên bản, số Điều/Khoản/Điểm, số chunk duy nhất, dung lượng và phân bố độ dài sau xử lý. |
| Độ thách thức | Có các điều khoản gần nghĩa nhưng khác đối tượng, điều kiện hoặc hành vi để đánh giá khả năng phân biệt. |
| Chất lượng | Thống kê trùng, thiếu nguồn, lỗi trích xuất, đoạn quá dài và kết quả rà soát thủ công. |

Ngưỡng quy mô corpus được xác định từ kết quả khảo sát dữ liệu và báo cáo thử nghiệm ban đầu. Bộ phận Dữ liệu & Sparse/Hybrid phối hợp với Long xây dựng đề xuất về số văn bản, số chunk duy nhất và mức bao phủ. Hoàng tổng hợp để thống nhất trước khi đóng băng corpus. Số lượng được tính sau chuẩn hóa và loại trùng.

## **5 4 Ranh giới bàn giao dữ liệu**

Đầu ra dữ liệu gồm danh mục nguồn, bản gốc, dữ liệu sạch có cấu trúc, chunk có ngữ cảnh và metadata, báo cáo chất lượng và phiên bản có thể tái tạo. Schema, quy tắc chunking và công cụ lưu trữ được đặc tả trong tài liệu thiết kế dữ liệu.

# **6 Tiêu chí thành công và nghiệm thu**

Recall@10 là chỉ số đánh giá chính. Recall@5, MRR@10, nDCG@10 và độ trễ là các chỉ số bổ trợ. Mục tiêu là Hybrid cải thiện Recall@10 so với BM25. Báo cáo phải thể hiện kết quả thực tế và mức chênh lệch giữa các cấu hình.

| Mã | Điều kiện và bằng chứng | Đầu mối |
| :---- | :---- | :---- |
| AC-01 | BR-01, BR-02, BR-11: demo tìm kiếm xuyên suốt, số kết quả hợp lệ và trạng thái lỗi rõ ràng. | Hùng |
| AC-02 | BR-03, BR-04: kiểm tra nội dung và trích dẫn với nguồn; lưu kết quả kiểm tra và lỗi đã sửa. | Phụ trách dữ liệu |
| AC-03 | BR-05, BR-09: công bố mốc corpus, inventory, thống kê duy nhất và ma trận bao phủ; chốt ngưỡng đủ lớn. | Phụ trách dữ liệu, Long |
| AC-04 | BR-06: bảng kết quả bốn cấu hình trên cùng corpus/test set; ghi mức chênh lệch và cấu hình chạy. | Hoàng, Long |
| AC-05 | BR-07: bộ truy vấn có nhãn, phương pháp gán nhãn, tách dev/test và nhật ký đóng băng. | Long |
| AC-06 | BR-08: báo cáo độ trễ có điều kiện đo và demo ít nhất một failure case được phân tích. | Long, Hùng |
| AC-07 | BR-10: có thể tái tạo corpus và thực nghiệm bằng tài liệu và cấu hình đã lưu. | Cả nhóm |

## **6 1 Nguyên tắc đánh giá**

Bộ đánh giá bao gồm truy vấn trực tiếp, diễn đạt lại và tình huống, đồng thời phân bổ theo chủ đề/đối tượng. Một truy vấn có thể có nhiều điều khoản liên quan. Long chủ trì hướng dẫn relevance; Phụ trách dữ liệu hỗ trợ liên kết nhãn với nguồn và rà soát độ đầy đủ.

Các biến thể cùng ý định phải được quản lý theo nhóm khi chia dev/test. Không dùng test cuối để chọn mô hình hoặc tinh chỉnh tham số. Bốn cấu hình dùng cùng phiên bản corpus và nội dung chuẩn hóa; mọi khác biệt cần được công bố. Chi tiết pooling, mức relevance, công thức và thủ tục đo thuộc kế hoạch đánh giá.

## **6 2 Hiệu năng và điều kiện nghiệm thu**

Độ trễ được báo cáo theo truy vấn, bao gồm p50 và p95 trên tập đo được xác định trong kế hoạch đánh giá. Điều kiện đo phải ghi phần cứng, mức đồng thời, trạng thái cache, độ dài dữ liệu và số ứng viên rerank. Ngưỡng hiệu năng nghiệm thu được xác định sau benchmark ban đầu.

Quy mô bộ đánh giá được xác định theo phạm vi chủ đề, cơ cấu truy vấn và nguồn lực gán nhãn. Kết quả hoàn thành các thực nghiệm và mức độ đạt mục tiêu chất lượng được báo cáo riêng.

# **7 Ràng buộc rủi ro và quyết định còn mở**

## **7 1 Ràng buộc và giả định**

Dự án được thực hiện bởi nhóm bốn thành viên theo phân công tại mục 2\. Kế hoạch triển khai phải xác định hạn nộp, phân bổ thời gian, tài nguyên CPU/GPU, kinh phí và môi trường vận hành. Khả năng thu thập và trích xuất nguồn được kiểm tra trong giai đoạn khảo sát dữ liệu.

| Mã | Rủi ro | Xử lý và đầu mối |
| :---- | :---- | :---- |
| R-01 | Corpus lớn về số lượng nhưng thiếu chủ đề hoặc nhiều bản trùng. | Ma trận bao phủ, loại trùng và thống kê duy nhất — Phụ trách dữ liệu. |
| R-02 | Nguồn hoặc hiệu lực tại mốc dữ liệu chưa chính xác. | Lưu bằng chứng nguồn, rà soát trước khi xuất bản corpus — Phụ trách dữ liệu phối hợp nhóm. |
| R-03 | Chunk mất ngữ cảnh, sai số liệu hoặc trích dẫn. | Kiểm tra cấu trúc và đối chiếu mẫu có trọng tâm — Phụ trách dữ liệu. |
| R-04 | Nhãn thiếu đáp án hoặc dev/test rò rỉ ý định. | Quy tắc gán nhãn, rà soát chéo và nhóm paraphrase — Long. |
| R-05 | Hybrid không cải thiện hoặc rerank quá chậm. | Phân tích lỗi trên dev, đo trade-off, báo cáo đúng test — Hoàng, Phụ trách dữ liệu, Long. |
| R-06 | Mở rộng corpus vượt khả năng triển khai. | Ưu tiên độ bao phủ cốt lõi và kiểm soát thay đổi — Hoàng, Hùng. |

## **7 2 Danh sách vấn đề cần chốt**

| Mã | Thông tin chưa chốt | Đầu mối và thời điểm |
| :---- | :---- | :---- |
| OPEN-01 | Ngày chốt dữ liệu và danh mục nguồn cuối. | Phụ trách dữ liệu; trước đóng băng corpus. |
| OPEN-02 | Ngưỡng số văn bản/chunk duy nhất và tiêu chí bao phủ. | Phụ trách dữ liệu, Long, Hoàng; sau pilot, trước mở rộng toàn bộ. |
| OPEN-03 | Số truy vấn, cơ cấu dev/test và quy trình gán nhãn. | Long; trước sản xuất bộ đánh giá chính. |
| OPEN-04 | Hạn nộp, nguồn lực và môi trường chạy. | Hoàng, Hùng; trước chốt kế hoạch triển khai. |
| OPEN-05 | Ngưỡng hiệu năng và chất lượng định lượng bổ sung. | Cả nhóm; sau baseline trên dev, trước test cuối. |

Các nội dung tại mục 7.2 phải được xác định trước mốc công việc phụ thuộc. Tiêu chí quy mô corpus chỉ được nghiệm thu khi ngưỡng định lượng và mức bao phủ đã được thống nhất.

# **8 Rà soát quản lý thay đổi và truy vết**

## **8 1 Cơ sở phạm vi dự án**

| Mã | Nội dung phạm vi |
| :---- | :---- |
| DEC-01 | Bản đầu sử dụng một mốc dữ liệu; time-travel là mở rộng. |
| DEC-02 | Nhóm gồm bốn thành viên, phụ trách quản lý và mô hình truy hồi; dữ liệu và Sparse/Hybrid; đánh giá và phân tích; hạ tầng và ứng dụng. |
| DEC-03 | Corpus được mở rộng ngoài bốn văn bản khởi đầu và phải đáp ứng tiêu chí về quy mô, độ bao phủ và chất lượng dữ liệu. |

## **8 2 Truy vết về đề bài và tài liệu đầu vào**

| Căn cứ | Yêu cầu liên quan |
| :---- | :---- |
| Project 2 | BR-01, BR-06, BR-08; bốn cấu hình; Hybrid \> BM25; metrics và latency. |
| Yêu cầu chung | BR-07, BR-09, BR-10; dữ liệu riêng, nguồn, quy mô, chất lượng, nhãn, không tune trên test. |
| Yêu cầu demo và nghiệm thu | BR-02 đến BR-05, BR-08, BR-11; sản phẩm chạy được, căn cứ, failure case và bằng chứng đánh giá. |
| Đặc tả phạm vi dự án | Miền giao thông, danh mục nguồn khởi đầu, giới hạn một mốc, corpus mở rộng và phân công nhóm. |

## **8 3 Quy trình thay đổi và bàn giao**

Thành viên đề xuất thay đổi ghi yêu cầu bị ảnh hưởng, lý do, tác động đến dữ liệu, đánh giá, tiến độ và ứng dụng. Hoàng điều phối rà soát; cập nhật phiên bản và quyết định trước khi áp dụng. Thay đổi nguồn/corpus sau khi đóng băng phải được ghi nhận và xác định có cần chạy lại toàn bộ so sánh hay không.

Tài liệu tiếp theo gồm SRS, thiết kế hệ thống, thiết kế dữ liệu và kế hoạch đánh giá. Bảng truy vết phải liên kết yêu cầu nghiệp vụ với chức năng, thành phần thiết kế và ca kiểm thử. Các lựa chọn mô hình, cơ sở dữ liệu và công cụ triển khai được quyết định trong giai đoạn thiết kế.

## **8 4 Ghi nhận rà soát**

| Người rà soát | Trạng thái | Ngày xác nhận |
| :---- | :---- | :---- |
| Hoàng | Chờ rà soát | Chưa ghi nhận |
| Dữ liệu | Chờ rà soát | Chưa ghi nhận |
| Long | Chờ rà soát | Chưa ghi nhận |
| Hùng | Chờ rà soát | Chưa ghi nhận |

