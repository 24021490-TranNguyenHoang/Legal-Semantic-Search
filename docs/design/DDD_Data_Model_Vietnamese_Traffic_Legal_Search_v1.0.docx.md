# Thiết kế mô hình dữ liệu pháp luật giao thông Việt Nam

Vietnamese Traffic Legal Semantic Search

Phiên bản 1.0  |  Mã DDD MODEL VTLS 1.0  |  Ngày 15/10/2026

Tài liệu xác định mô hình dữ liệu logic và vật lý cho hệ thống tìm kiếm pháp luật giao thông tiếng Việt. Thiết kế bảo toàn nguồn, cấu trúc pháp lý, bằng chứng hiệu lực và tư cách thành viên của từng chunk trong corpus tại ngày 01/01/2025. Đây là cơ sở triển khai parser, chuẩn hóa, chunking và bàn giao dữ liệu cho bốn phương pháp truy hồi.

| Thuộc tính | Đặc tả |
| :---- | :---- |
| Cơ sở | SRS VTLS v1.0; SDD kiến trúc v1.0; danh mục nguồn v0.1; snapshot đã thống nhất. |
| Mốc dữ liệu | 2025-01-01, cố định cho phiên bản sản phẩm đầu. |
| Kho phục vụ | SQLite chỉ đọc; JSONL trao đổi; BM25S và Qdrant là chỉ mục dẫn xuất. |
| Phạm vi thiết kế | 12 bảng lõi, view phục vụ, ERD, từ điển dữ liệu, định danh, manifest và hợp đồng đánh giá. |
| Trạng thái | Thiết kế v1.0 để triển khai; corpus pháp luật thực tế chưa được phát hành. |

## **Nguyên tắc thiết kế**

* Văn bản pháp luật không đồng nhất với một tệp PDF; một văn bản có thể có nhiều phần và bản đối chiếu.  
* Đơn vị pháp lý không đồng nhất với chunk. Một đơn vị dài có thể tạo nhiều segment cùng unit\_id.  
* Trạng thái hiệu lực được xác minh ở cấp đơn vị tại snapshot, kể cả các đơn vị dùng làm ngữ cảnh.  
* Thay corpus tạo phiên bản mới; nội dung hiển thị và hai chỉ mục phải cùng tập chunk.  
* Không bổ sung tài khoản, dữ liệu cá nhân người tìm kiếm hoặc chức năng time travel vào v1.0.

## **Quy ước đọc**

PK là khóa chính; FK là khóa ngoại; UK là duy nhất; R là bắt buộc; O là cho phép null. Khóa chính ghép và ràng buộc liên bảng được mô tả riêng. Kiểu DATE/TIMESTAMP logic được lưu bằng TEXT trong SQLite và kiểm tra bằng validator.

# **1 Phạm vi và danh mục thực thể**

| Nhóm | Thực thể | Trách nhiệm |
| :---- | :---- | :---- |
| Nguồn | legal\_document, source\_file | Số hiệu, tên văn bản, bản gốc và thông tin thu thập. |
| Trích xuất | extraction, source\_span | Text bất biến và vị trí đối chiếu từ đơn vị về từng tệp/trang. |
| Pháp lý | legal\_unit, legal\_reference | Cây pháp lý và các dẫn chiếu có trạng thái phân giải. |
| Snapshot | corpus, corpus\_document, unit\_assessment | Phiên bản, nguồn thành viên, phạm vi và hiệu lực từng đơn vị. |
| Truy hồi | chunk, chunk\_context | Đoạn mục tiêu, mảnh ngữ cảnh và text chung cho mọi mode. |
| Kiểm định | quality\_issue | Lỗi và quyết định sửa/cách ly trước phát hành. |

## **1 1 Các quan hệ cốt lõi**

* legal\_document 1–N source\_file; source\_file 1–N extraction.  
* legal\_document 1–N legal\_unit; legal\_unit có tối đa một cha cùng văn bản và có thể có nhiều con.  
* legal\_unit N–N extraction thông qua source\_span; đơn vị qua ranh giới hai tệp vẫn truy vết được.  
* corpus N–N legal\_document qua corpus\_document; corpus N–N legal\_unit qua unit\_assessment.  
* unit\_assessment 1–N chunk; chunk N–N đơn vị ngữ cảnh qua chunk\_context.

## **1 2 Quan hệ với triển khai**

12 bảng là mô hình lưu trữ nội dung và provenance. Không cần 12 dịch vụ hay 12 cơ sở dữ liệu. CLI xây một SQLite ở vùng staging; sau kiểm định đóng gói bản chỉ đọc cho release. Dữ liệu đánh giá dùng kho ngoại tuyến riêng. Vector và chỉ mục BM25 không phải nguồn nội dung chuẩn.

## **1 3 Giới hạn đã xác định**

Chưa chốt ngân sách token, quy tắc tách câu theo từng nguồn hoặc cấu hình OCR. Các thông số này thuộc bước thiết kế chuẩn hóa và chunking tiếp theo; schema đã có segment, offsets, phiên bản cấu hình và nhánh cách ly để tiếp nhận kết quả.

# **2 ERD nguồn và cấu trúc pháp lý**

![][image1]

Hình 1 Quan hệ nguồn và provenance. 1 : N cho biết một bản ghi cha có thể có nhiều bản ghi con; ở giai đoạn khảo sát có thể chưa có con. source\_span cần đồng thời một legal\_unit và một extraction.

## **2 1 Cây pháp lý và dẫn chiếu**

parent\_unit\_id tạo cây trong cùng law\_id. Mỗi cây có một nút document; validator kiểm tra chu trình, cha sai văn bản và cấp giả. legal\_reference nối nút chứa dẫn chiếu với đích đã xác định; đích có thể null. Không có quy tắc tự động coi mọi dẫn chiếu là ngữ cảnh cần ghép.

# **3 ERD corpus và chunk**

![][image2]

Hình 2 Quan hệ snapshot và truy hồi. chunk\_context phải có unit\_assessment cùng corpus cho đơn vị nguồn ngữ cảnh, ngoài khóa ngoại tới chunk. Các FK ghép được thể hiện đầy đủ trong schema.sql.

## **3 1 Khóa của tập phục vụ**

Khóa đọc là (corpus\_version, chunk\_id). Một corpus có một snapshot\_date. Không đọc chunk từ một corpus và assessment hoặc ngữ cảnh từ corpus khác. corpus\_document là bảng thành viên bổ sung giữa corpus và văn bản; không thay thế assessment từng đơn vị.

# **4 Từ điển dữ liệu nguồn**

## **legal\_document**

Một văn bản pháp luật có số hiệu, dùng chung cho các tệp và đơn vị pháp lý.

| Trường | Kiểu và mức | Ý nghĩa và ràng buộc |
| :---- | :---- | :---- |
| law\_id | TEXT / PK | Số hiệu chuẩn hóa NFC, trim; ví dụ 36/2024/QH15. |
| source\_id | TEXT / R | Mã danh mục nguồn ổn định, ví dụ SRC-001. |
| law\_title | TEXT / R | Tên đầy đủ, không rỗng; không dùng tên tệp thay tên văn bản. |
| document\_type | TEXT / R | law, decree, circular hoặc regulation. |
| issued\_date | TEXT / R | Ngày ban hành YYYY-MM-DD, kiểm tra lịch thực. |
| document\_effective\_from | TEXT / O | Ngày hiệu lực chung nếu đã xác minh; không kế thừa máy móc xuống đơn vị. |
| source\_url | TEXT / R | Trang công bố chính thức đã rà soát, http/https. |
| scope\_note | TEXT / R | Phạm vi khảo sát; có thể ghi nội dung loại trừ. |

## **source\_file**

Mỗi bản chụp tệp nguồn bất biến. Một văn bản có nhiều tệp, nhiều lần thu thập.

| Trường | Kiểu và mức | Ý nghĩa và ràng buộc |
| :---- | :---- | :---- |
| file\_id | TEXT / PK | UUID hoặc ID điều phối sinh một lần; không dùng tên tệp làm khóa. |
| law\_id | TEXT / R | Văn bản mà tệp thuộc về. |
| source\_set\_id | TEXT / R | Nhóm tệp tạo một bản biểu diễn đầy đủ; PDF Công báo và HTML dùng nhóm riêng. |
| file\_role | TEXT / R | Vai trò tệp; HTML đối chiếu có thể là alternate. |
| part\_order | INTEGER / R | Thứ tự trong nhóm nguồn cùng bản; không suy ra từ tên. |
| filename | TEXT / R | Tên tệp đã lưu, giữ phần mở rộng. |
| raw\_file\_ref | TEXT / R | Đường dẫn tương đối trong kho raw; không ghi URL tải tạm. |
| download\_url | TEXT / R | URL tệp thực tế, tách với trang công bố. |
| mime\_type | TEXT / R | Loại nội dung xác minh từ tệp. |
| size\_bytes | INTEGER / R | Kích thước thực sau tải, đơn vị byte. |
| sha256 | TEXT / R | SHA-256 của byte tệp được lưu, không phải checksum văn bản đã làm sạch. |
| retrieved\_at | TEXT / R | Thời điểm thu thập ISO 8601 UTC kết thúc bằng Z. |

UNIQUE(law\_id, sha256) loại bản byte trùng; UNIQUE(law\_id, source\_set\_id, part\_order) khóa thứ tự trong một bộ nguồn. source\_set\_id phân biệt bộ PDF nhiều phần với HTML đối chiếu. Tệp khác byte nhưng gần giống vẫn cần kiểm tra bản ban hành.

# **5 Từ điển dữ liệu trích xuất và đơn vị**

## **extraction**

Kết quả trích xuất có phiên bản trên một tệp nguồn; dùng để định vị ký tự.

| Trường | Kiểu và mức | Ý nghĩa và ràng buộc |
| :---- | :---- | :---- |
| extraction\_id | TEXT / PK | ID của một artifact trích xuất bất biến. |
| file\_id | TEXT / R | Tệp đầu vào; các phần PDF có extraction riêng. |
| method | TEXT / R | pdf\_text, html\_text, doc\_text hoặc ocr. |
| tool\_version | TEXT / R | Tên công cụ, phiên bản và revision/config có thể tái tạo. |
| text\_ref | TEXT / R | Đường dẫn UTF-8 của bản text đã đóng băng. |
| text\_sha256 | TEXT / R | Hash byte UTF-8 của extraction artifact. |
| char\_count | INTEGER / R | Số Unicode code point của text sau NFC và LF. |
| review\_status | TEXT / R | verified yêu cầu kiểm tra chất lượng và nguồn; OCR không tự đạt. |
| created\_at | TEXT / R | Thời điểm chạy thực tế, UTC. |

## **legal\_unit**

Một nút trong cây pháp lý; chứa phần chữ riêng của nút, không lặp toàn bộ con.

| Trường | Kiểu và mức | Ý nghĩa và ràng buộc |
| :---- | :---- | :---- |
| unit\_id | TEXT / PK | u\_ \+ SHA-256 theo quy tắc tại mục định danh. |
| law\_id | TEXT / R | Văn bản sở hữu nút. |
| parent\_unit\_id | TEXT / O | Nút cha trực tiếp; null chỉ cho gốc văn bản. |
| unit\_type | TEXT / R | Cấp thực có trong nguồn; không tạo Khoản/Điểm giả. |
| designation | TEXT / R | Ký hiệu gốc như II, 10, 3, đ; gốc dùng số hiệu văn bản. |
| canonical\_path | TEXT / R | Đường dẫn máy đọc, gồm cấp và ký hiệu gốc theo đúng cha. |
| citation\_path | TEXT / R | Đường dẫn hiển thị tiếng Việt, chỉ gồm các cấp thực có. |
| ordinal | INTEGER / R | Thứ tự trong các nút cùng cha, không sắp theo chuỗi số. |
| title | TEXT / R | Tiêu đề riêng, rỗng nếu nguồn không có; không sinh tiêu đề tóm tắt. |
| text\_original | TEXT / R | Phần nội dung trực tiếp của nút, NFC/LF; không chứa lặp văn bản các con. |
| text\_sha256 | TEXT / R | SHA-256 của text\_original UTF-8. |

Khóa UNIQUE(unit\_id, law\_id) hỗ trợ FK ghép (parent\_unit\_id, law\_id), bảo đảm cha cùng văn bản. Không áp UNIQUE(law\_id, canonical\_path) vì cùng vị trí có thể có bản chỉnh sửa extraction; mỗi bản có unit\_id mới và corpus chọn đúng bản.

# **6 Từ điển dữ liệu truy vết và dẫn chiếu**

## **source\_span**

Liên kết một đơn vị với các vùng trong extraction đã kiểm tra; cho phép nhiều tệp/trang.

| Trường | Kiểu và mức | Ý nghĩa và ràng buộc |
| :---- | :---- | :---- |
| span\_id | TEXT / PK | ID bằng chứng vị trí nguồn. |
| unit\_id | TEXT / R | Nút được chứng minh, kể cả tiêu đề hoặc phần chữ riêng. |
| extraction\_id | TEXT / R | Bản text nguồn có hash và phương pháp trích xuất. |
| field\_name | TEXT / R | Trường của nút được đối chiếu. |
| span\_order | INTEGER / R | Thứ tự ghép các vùng của một trường. |
| char\_start | INTEGER / R | Vị trí code point bắt đầu trong extraction, tính từ 0\. |
| char\_end | INTEGER / R | Vị trí kết thúc không bao gồm; phải \<= char\_count. |
| locator\_json | TEXT / R | PDF: page\_start/page\_end 1-based của từng tệp; HTML: id/selector và heading\_path; không bịa số trang. |
| quote\_sha256 | TEXT / R | Hash chuỗi extraction\[char\_start:char\_end\]; dùng phát hiện lệch offset. |

## **legal\_reference**

Dẫn chiếu pháp lý được phát hiện trong nguyên văn, có thể chưa có đích trong corpus.

| Trường | Kiểu và mức | Ý nghĩa và ràng buộc |
| :---- | :---- | :---- |
| reference\_id | TEXT / PK | ID dẫn chiếu. |
| from\_unit\_id | TEXT / R | Nút chứa dẫn chiếu. |
| target\_citation | TEXT / R | Nội dung dẫn chiếu như xuất hiện trong nguồn. |
| to\_unit\_id | TEXT / O | Đích đã phân giải; null khi ở ngoài tập hoặc chưa xác định. |
| resolution\_status | TEXT / R | resolved phải có đích; external/unresolved không tự ghép nội dung. |
| relation\_type | TEXT / R | Ví dụ refers\_to, exception, sanction\_link; không suy ra chế tài bằng từ khóa đơn thuần. |

Vị trí ký tự dùng quy ước \[start, end). Offsets extraction trỏ text NFC/LF đã đóng băng; offsets chunk/context trỏ trường legal\_unit. Trường nút được dựng bằng LF nối các span\_order. Không sửa OCR âm thầm: tạo extraction đã hiệu đính có phiên bản và rà soát lại spans.

# **7 Từ điển dữ liệu corpus**

## **corpus**

Một snapshot dữ liệu đã lựa chọn và chuẩn hóa; đóng băng sau kiểm định.

| Trường | Kiểu và mức | Ý nghĩa và ràng buộc |
| :---- | :---- | :---- |
| corpus\_version | TEXT / PK | Tên phiên bản bất biến, ví dụ traffic-20250101-v1.0.0. |
| snapshot\_date | TEXT / R | Mốc áp dụng của v1.0; đổi mốc cần sửa thiết kế có phiên bản. |
| schema\_version | TEXT / R | 1.0.0 cho hợp đồng này. |
| status | TEXT / R | frozen là trạng thái phát hành, không được sửa tại chỗ. |
| built\_at | TEXT / R | Ngày tạo corpus thực tế, UTC. |
| processing\_config\_ref | TEXT / R | Artifact khóa parser, chuẩn hóa, chunker và quy tắc context. |
| manifest\_ref | TEXT / R | Đường dẫn corpus manifest; checksum của manifest lưu ở sidecar/release. |
| supported\_topics\_json | TEXT / R | Mảng chủ đề được xác minh; không dùng như bộ lọc API. |
| exclusions\_json | TEXT / R | Mảng giới hạn và khoảng trống công bố. |
| coverage\_report\_ref | TEXT / R | Báo cáo độ bao phủ và thống kê thực tế. |

## **corpus\_document**

Quan hệ thành viên giữa corpus và văn bản; hỗ trợ nguồn chỉ dùng đối chiếu.

| Trường | Kiểu và mức | Ý nghĩa và ràng buộc |
| :---- | :---- | :---- |
| corpus\_version | TEXT / R | Corpus sở hữu quan hệ. |
| law\_id | TEXT / R | Văn bản có hồ sơ nguồn. |
| usage\_role | TEXT / R | retrieval có nội dung được đưa vào truy hồi; supporting chỉ hỗ trợ xác minh. |

## **7 1 Thống kê và checksum**

document\_count, unit\_count và chunk\_count được tính từ dữ liệu đã kiểm định và ghi trong corpus manifest. document\_count chỉ đếm văn bản có chunk mục tiêu; supporting\_document\_count đếm riêng. Hash từng artifact tính từ byte tệp; manifest có sidecar SHA-256 để tránh checksum tự tham chiếu.

# **8 Từ điển dữ liệu quyết định hiệu lực**

## **unit\_assessment**

Quyết định phạm vi và hiệu lực của từng đơn vị tại một corpus; lưu cả đơn vị bị loại.

| Trường | Kiểu và mức | Ý nghĩa và ràng buộc |
| :---- | :---- | :---- |
| corpus\_version | TEXT / R | Mốc đối chiếu lấy từ corpus. |
| unit\_id | TEXT / R | Nút được kiểm tra. |
| scope\_status | TEXT / R | included có thể là mục tiêu; supporting có thể là context; excluded không được phục vụ. |
| applicability\_status | TEXT / R | Tách biệt hiệu lực pháp lý với tiến độ xử lý nguồn. |
| effective\_from | TEXT / O | Ngày bắt đầu của nội dung này; bắt buộc nếu verified\_at\_snapshot. |
| effective\_to | TEXT / O | Ngày kết thúc không bao gồm; null chỉ khi chưa có mốc kết thúc được xác minh. |
| verification\_ref | TEXT / O | Artifact bằng chứng có số hiệu, Điều/Khoản, locator và hash nguồn; bắt buộc khi xác minh. |
| verified\_at | TEXT / O | Thời điểm rà soát thực tế, UTC; bắt buộc khi xác minh. |
| reviewer\_ref | TEXT / O | Mã người/nhóm rà soát nội bộ; không bắt buộc tên cá nhân trong báo cáo. |
| decision\_note | TEXT / R | Lý do chọn/loại, điều kiện áp dụng và chuyển tiếp cần giữ. |

## **8 1 Phạm vi và hiệu lực là hai chiều riêng**

| Trạng thái | Ý nghĩa | Được phục vụ |
| :---- | :---- | :---- |
| included \+ verified\_at\_snapshot | Đơn vị thuộc phạm vi và đã có bằng chứng áp dụng. | Có thể tạo chunk. |
| supporting \+ verified\_at\_snapshot | Tiêu đề, lời dẫn hoặc điều kiện cần cho đoạn khác. | Chỉ làm context đã chọn. |
| excluded | Ngoài phạm vi hoặc đã bị loại theo quyết định. | Không. |
| pending\_review | Chưa đủ bằng chứng hoặc còn lỗi trích xuất. | Không. |
| not\_yet\_effective / expired\_at\_snapshot | Nằm ngoài khoảng hiệu lực tại snapshot. | Không. |
| not\_applicable | Không phải quy tắc pháp lý để truy hồi hoặc không áp dụng theo hồ sơ. | Không. |

effective\_to là cận trên không bao gồm. Điều kiện chọn là effective\_from \<= snapshot\_date \< effective\_to, hoặc không có cận trên đã xác minh. null không có nghĩa đã chứng minh hiệu lực vĩnh viễn. Quy định chuyển tiếp cần giữ điều kiện trong nguyên văn/context và decision\_note; một ngày không đủ xác định mọi tình huống áp dụng.

# **9 Từ điển dữ liệu chunk**

## **chunk**

Đơn vị truy hồi của một corpus; mục tiêu lấy từ phần chữ của một legal\_unit đã xác minh.

| Trường | Kiểu và mức | Ý nghĩa và ràng buộc |
| :---- | :---- | :---- |
| corpus\_version | TEXT / R | Một phần khóa chính, luôn khớp manifest. |
| chunk\_id | TEXT / R | c\_ \+ SHA-256 nội dung ngữ nghĩa và provenance theo mục định danh. |
| unit\_id | TEXT / R | Đơn vị mục tiêu; liên kết assessment cùng corpus. |
| segment\_no | INTEGER / R | Số đoạn trong cùng đơn vị, liên tục từ 1\. |
| unit\_char\_start | INTEGER / R | Offset code point trong legal\_unit.text\_original. |
| unit\_char\_end | INTEGER / R | Kết thúc không bao gồm; text\_original phải là đúng lát cắt. |
| text\_original | TEXT / R | Nguyên văn đoạn mục tiêu sau chuẩn hóa được phép. |
| context\_text | TEXT / O | Chuỗi ghép theo chunk\_context.context\_order; null khi không cần. |
| text\_for\_search | TEXT / R | Chuỗi chung cho bốn mode; gồm tên văn bản, citation, context và đoạn gốc. |
| content\_sha256 | TEXT / R | SHA-256 của text\_for\_search UTF-8, dùng đối chiếu chỉ mục. |
| chunk\_policy\_version | TEXT / R | Phiên bản quy tắc chia đoạn và ngữ cảnh. |

## **9 1 Đơn vị mục tiêu**

Ưu tiên nút Điểm, Khoản không có Điểm hoặc Điều không có cấp đánh số con. Phần dẫn nhập của Khoản/Điều có các con thường làm context, không tự biến thành đoạn mục tiêu đứng riêng. Nếu một điều khoản chỉ đọc đúng khi ghép điều kiện ở cha, chunk\_context phải chỉ rõ vùng nguồn này. Trường hợp bảng/hình cần quy tắc kiểm tra riêng ở bước chunking.

## **9 2 Bảo toàn nguyên văn**

chunk.text\_original phải bằng legal\_unit.text\_original\[start:end\]. Các segment mục tiêu của một đơn vị phủ kín phần chữ riêng, liên tục, không chồng lấn; ngữ cảnh được quản lý riêng. Không cắt mất phủ định, số liệu hoặc điều kiện, không diễn giải hay tự ghép kết luận pháp lý. Ranh giới và ngân sách token sẽ được thực nghiệm trước khi đóng băng cấu hình.

# **10 Từ điển dữ liệu ngữ cảnh và lỗi**

## **chunk\_context**

Các mảnh nguồn được ghép thành context, mỗi mảnh có đơn vị và khoảng ký tự riêng.

| Trường | Kiểu và mức | Ý nghĩa và ràng buộc |
| :---- | :---- | :---- |
| corpus\_version | TEXT / R | Khớp chunk và assessment của context. |
| chunk\_id | TEXT / R | Chunk được hỗ trợ. |
| context\_order | INTEGER / R | Thứ tự ghép xác định, liên tục từ 0\. |
| unit\_id | TEXT / R | Nút nguồn ngữ cảnh; có thể là cha, tiêu đề hoặc dẫn chiếu đã xác minh. |
| field\_name | TEXT / R | Trường nguồn được lấy nguyên văn. |
| char\_start | INTEGER / R | Offset code point trong trường nguồn. |
| char\_end | INTEGER / R | Kết thúc không bao gồm; không cắt mất điều kiện cần thiết. |
| context\_role | TEXT / R | Mục đích sử dụng; không phải nhãn suy luận pháp lý. |

## **quality\_issue**

Lỗi dữ liệu và hồ sơ xử lý, dùng ở offline; không trả ra giao diện tìm kiếm.

| Trường | Kiểu và mức | Ý nghĩa và ràng buộc |
| :---- | :---- | :---- |
| issue\_id | TEXT / PK | ID lỗi duy nhất. |
| corpus\_version | TEXT / R | Bản corpus bị ảnh hưởng. |
| unit\_id | TEXT / O | Nút liên quan nếu đã xác định. |
| rule\_id | TEXT / R | Mã DQ trong mục kiểm định. |
| severity | TEXT / R | error chặn phát hành nếu ảnh hưởng tập được phục vụ. |
| status | TEXT / R | excluded cần xác minh đối tượng lỗi không xuất hiện trong mục tiêu hoặc context. |
| detail | TEXT / R | Vị trí, mô tả và bằng chứng xử lý. |
| created\_at | TEXT / R | Thời điểm ghi lỗi UTC. |

# **11 Hợp đồng nội dung và xuất dữ liệu**

## **11 1 Ba trường văn bản**

| Trường | Nội dung | Nguồn chuẩn |
| :---- | :---- | :---- |
| text\_original | Nguyên văn segment mục tiêu. | Lát cắt của legal\_unit.text\_original. |
| context\_text | Ghép các mảnh đã chọn bằng LF; không có mảnh thì null. | chunk\_context theo context\_order, lấy đúng field và offsets. |
| text\_for\_search | Tên văn bản, citation\_path, context nếu có, text\_original; ghép các khối bằng hai LF. | Dữ liệu nguồn và mẫu ghép cố định, dùng chung bốn mode. |

Không lowercase hoặc bỏ dấu trên nội dung chuẩn. Tokenizer BM25 xử lý bản sao phục vụ thuật toán; tokenizer của model xử lý cùng text\_for\_search. Không âm thầm thêm ngữ cảnh chỉ cho Dense hoặc Reranker trong thực nghiệm so sánh.

## **11 2 View serving\_chunks và JSONL**

View nối chunk, legal\_unit, legal\_document và unit\_assessment để tạo đủ trường của DR-02. source\_locator là chuỗi JSON gồm file\_id, span\_id và locator của đơn vị mục tiêu; ngữ cảnh có bảng riêng để truy vết. JSONL xuất thêm snapshot\_date, segment, offsets và chunk\_policy\_version theo chunk.schema.json. View chỉ hỗ trợ đọc; corpus phải vượt validator đầy đủ trước khi phục vụ.

## **11 3 Quy ước tuần tự hóa**

* UTF-8 không BOM; Unicode NFC; xuống dòng LF; một JSON object trên một dòng; null là JSON null.  
* Ngày YYYY-MM-DD; timestamp UTC ISO 8601 có Z. Số nguyên không nhận boolean hoặc số thực.  
* Khi tính hash đối tượng: json.dumps(sort\_keys=True, ensure\_ascii=False, separators=(",", ":")), rồi mã hóa UTF-8. Không hash JSON có khoảng trắng tùy ý.  
* chunks.jsonl sắp chunk\_id tăng dần; danh sách ID có LF cuối, mỗi ID đúng một dòng; lưu SHA-256 riêng.  
* JSON Schema kiểm tra hình dạng; bật FormatChecker cho date/uri và chạy kiểm tra tham chiếu, offset, snapshot ở validator.

# **12 Định danh và quản lý phiên bản**

| Định danh | Quy tắc | Khi thay đổi |
| :---- | :---- | :---- |
| source\_id | Mã inventory cấp một lần. | Không đổi vì tên tệp hoặc lần tải mới. |
| law\_id | Số hiệu chuẩn hóa, vẫn giữ dấu và ký tự gốc. | Văn bản pháp luật khác có ID khác. |
| unit\_id | u\_ \+ SHA-256 đối tượng unit.v1. | Đổi text, title, path hoặc cha tạo ID mới. |
| chunk\_id | c\_ \+ SHA-256 đối tượng chunk.v1. | Đổi mục tiêu, ngữ cảnh, metadata áp dụng hoặc policy tạo ID mới. |
| corpus\_version | traffic-20250101-vMAJOR.MINOR.PATCH. | Bất kỳ thay đổi nội dung, phạm vi, ngữ cảnh hoặc metadata pháp lý. |
| index\_build\_id | ID build cụ thể trên một corpus. | Đổi model, tokenizer, index hoặc cấu hình indexing. |
| release\_id | ID gói vận hành khóa corpus và build. | Đổi gói ứng dụng hoặc tham số truy hồi cũng tạo release mới. |

## **12 1 Đối tượng hash định danh**

unit.v1 gồm identity\_schema, law\_id, parent\_unit\_id, unit\_type, designation, canonical\_path, citation\_path, ordinal, title và text\_original. Xây cha trước con. Sửa cha có thể làm đổi ID các con. Trong một corpus, mỗi law\_id và canonical\_path đang dùng chỉ được chọn một bản unit; bản cũ giữ ở kho nguồn hoặc corpus trước.

chunk.v1 gồm identity\_schema, unit\_id, segment\_no, unit\_char\_start, unit\_char\_end, text\_original, danh sách context gồm unit\_id/field/offset/role/order, law\_id, law\_title, citation\_path, source\_url, effective\_from, effective\_to, applicability\_status và chunk\_policy\_version. Không gồm corpus\_version, chunk\_id hoặc thời điểm build. Cùng nội dung và provenance có thể dùng cùng chunk\_id ở nhiều corpus; khóa vật lý vẫn có corpus\_version.

## **12 2 ID trong chỉ mục**

BM25 lưu row\_index liên tục từ 0 và chunk\_id theo thứ tự ổn định. Qdrant point\_id là UUIDv5(namespace cố định ghi trong config, tên corpus\_version \+ LF \+ chunk\_id). Payload lưu chunk\_id, corpus\_version, content\_sha256. Tên collection cụ thể thuộc index\_build\_id; không dùng alias thay đổi giữa các bước của một truy vấn.

# **13 Ánh xạ lưu trữ và manifest**

| Vùng hoặc artifact | Nội dung | Quy tắc |
| :---- | :---- | :---- |
| data/raw/source\_id/ | Tệp nguồn nguyên byte và hồ sơ tải. | Bất biến; không ghi kết quả làm sạch tại đây. |
| staging/run\_id/ | Extraction, cây pháp lý, assessment dự thảo, lỗi. | Có thể tái tạo; không đưa trực tiếp vào truy hồi. |
| corpora/corpus\_version/ | sources.jsonl, units.jsonl, assessments.jsonl, chunks.jsonl, context/spans và corpus manifest. | Đóng băng cùng báo cáo chất lượng và checksum. |
| releases/release\_id/ | content.sqlite, BM25 artifacts, index/release manifest. | Ứng dụng chỉ đọc, giữ release trước để khôi phục. |
| Qdrant collection | Vector và payload của đúng build. | Tập ID phải khớp SQLite và BM25. |
| eval/dataset\_version/ | Queries, qrels, hướng dẫn nhãn và split. | Tách test khỏi tinh chỉnh; không đưa vào kho phục vụ. |

## **13 1 Corpus manifest bắt buộc**

corpus\_version, snapshot\_date, schema\_version, built\_at, source\_manifest\_ref, processing\_config\_ref, parser\_revision, chunker\_revision, source/unit/chunk counts, coverage\_report\_ref, validation\_report\_ref, files\[\] với path/size\_bytes/sha256. Manifest và mọi artifact được hash từ byte thực; checksum manifest ở sidecar hoặc release manifest.

## **13 2 Index và release manifest**

Index manifest khóa corpus\_version, chunk\_id\_list\_sha256, BM25 row mapping, tokenizer/config, embedding model ID và revision, dimension, distance, dtype và collection. Release manifest khóa release\_id, index\_build\_id, corpus manifest checksum, SQLite/BM25 paths và hashes, model reranker/revision, tham số retrieval, mã nguồn commit, lockfile và validation report. Đây là hồ sơ triển khai, không phải bảng giao dịch online.

# **14 Hợp đồng dữ liệu đánh giá**

Dữ liệu đánh giá thuộc trách nhiệm phối hợp với nhóm đánh giá. Mô hình bên dưới cụ thể hóa DR-03 để tránh nhãn trỏ sang chunk hoặc corpus không tương thích; không tự chốt số lượng truy vấn hay hướng dẫn chuyên môn relevance.

| Artifact hoặc bảng | Khóa và trường | Ràng buộc |
| :---- | :---- | :---- |
| eval\_dataset | PK dataset\_version; corpus\_version; annotation\_version; guideline\_version; reviewer\_ref; review\_status; manifest\_ref. | Khóa corpus trước test; phiên bản dataset bất biến sau đóng băng. |
| eval\_query | PK dataset\_version \+ query\_id; query; query\_type; topic; intent\_group\_id; split. | direct/paraphrase/scenario; dev/test; cùng nhóm ý định chỉ thuộc một split. |
| eval\_qrel | PK dataset\_version \+ query\_id \+ chunk\_id; corpus\_version; relevance. | relevance 0/1/2; corpus phải khớp dataset; chunk tồn tại trong corpus đã khóa. |
| run manifest và rankings.jsonl | run\_id, dataset\_version, release\_id, corpus\_version, mode, query\_id, ranked\_chunk\_ids, scores, latency\_ms, outcome. | Không ghi đè run; outcome phân biệt success/error/timeout; điểm hữu hạn và rank liên tục. |

## **14 1 Quan hệ và thay đổi chunk**

eval\_dataset 1–N eval\_query; eval\_query 1–N eval\_qrel; một qrel trỏ đúng một chunk của corpus đã khóa. Vì kho đánh giá tách SQLite nội dung, tương thích corpus được validator kiểm tra bằng export thay vì FK tới một database đang hoạt động. Không tự chuyển nhãn sang ID mới khi chia lại chunk; phải rà soát lại.

## **14 2 Quy ước relevance theo SRS**

0 không liên quan; 1 hỗ trợ; 2 trực tiếp phù hợp. Recall và MRR dùng relevance \>= 1; nDCG dùng gain \= 2^relevance − 1\. Không gán nhãn cho toàn bộ kết quả chưa được đánh giá là không liên quan trong quá trình xây golden set; cách xử lý kết quả chưa có nhãn phải được công bố trong kế hoạch đánh giá.

# **15 Kiểm định và điều kiện nghiệm thu**

| Mã | Nhóm kiểm tra | Điều kiện |
| :---- | :---- | :---- |
| DQ-01 | Nguồn và tệp | ID duy nhất, URL hợp lệ; raw tồn tại; checksum/kích thước khớp; đủ phần tiếp/phụ lục. |
| DQ-02 | Cây pháp lý | Không chu trình; cha cùng law\_id; root hợp lệ; đường dẫn và thứ tự đúng nguồn. |
| DQ-03 | Vị trí nguồn | Mỗi mục tiêu và mảnh context có span hợp lệ trong extraction verified; offset/hash không lệch. |
| DQ-04 | Hiệu lực | Mục tiêu included, context included/supporting; đều verified\_at\_snapshot và chứa snapshot trong khoảng ngày. |
| DQ-05 | Nguyên văn | Text mục tiêu/context bằng đúng lát cắt nguồn chuẩn; NFC/LF; giữ số liệu, phủ định và điều kiện. |
| DQ-06 | Định danh | Tái tính hash unit/chunk/content; không trùng ID, không thay nội dung dưới ID cũ. |
| DQ-07 | Nhất quán chỉ mục | Cùng corpus và tập chunk, content hashes; row mapping/UUID không va chạm; vector dimension hợp cấu hình. |
| DQ-08 | Đánh giá | Qrels hợp corpus/ID; relevance hợp lệ; nhóm ý định không rò dev/test. |
| DQ-09 | Đóng băng | Không có lỗi error chưa giải quyết trong mục tiêu/context; manifest đầy đủ và có checksum artifacts. |
| DQ-10 | Độ bao phủ | Đếm duy nhất; có báo cáo chủ đề/đối tượng và khoảng trống; không tăng quy mô bằng bản trùng. |

## **15 1 Phân chia kiểm tra tự động và rà soát**

SQL kiểm tra khóa, null, enum và một số ràng buộc miền. validate\_design.py kiểm tra thêm cây, offsets, hash, hiệu lực và provenance trên fixture cấu trúc. Chất lượng OCR, đúng nội dung nguồn, căn cứ hiệu lực, tính đầy đủ của điều kiện và độ bao phủ vẫn cần rà soát dữ liệu thực tế. Chạy fixture thành công không xác nhận corpus pháp luật đã đúng.

# **16 Bàn giao và trình tự triển khai**

| Đầu ra | Nội dung | Sử dụng |
| :---- | :---- | :---- |
| Tài liệu thiết kế | ERD và từ điển 12 bảng, hợp đồng xuất, quy tắc định danh và phiên bản. | Thống nhất giữa dữ liệu, truy hồi, ứng dụng và đánh giá. |
| schema.sql | DDL SQLite và view serving\_chunks. | Khởi tạo kho staging; chưa phải pipeline nạp luật. |
| chunk.schema.json | JSON Schema 2020-12 của chunks.jsonl. | Kiểm tra trường, kiểu và giá trị. |
| eval\_schema.sql | DDL tùy chọn cho bộ đánh giá offline. | Cơ sở bàn giao queries/qrels. |
| data\_dictionary.json và ERD mmd | Nguồn máy đọc của từ điển và sơ đồ. | Đồng bộ tài liệu khi thay đổi schema. |
| fixture và validator | Dữ liệu giả lập có ghi nhãn, script kiểm tra và báo cáo kết quả. | Thử các ràng buộc; không nhập fixture vào corpus thật. |

## **16 1 Bước tiếp theo**

* Thiết kế quy tắc trích xuất và chuẩn hóa cho từng dạng PDF có text, PDF ảnh, HTML và bảng/phụ lục.  
* Chọn mẫu Điều/Khoản/Điểm có dẫn nhập, mức phạt, trừ điểm, dẫn chiếu và ngoại lệ hiệu lực.  
* Định nghĩa quy tắc tạo legal\_unit, source\_span và assessment trên mẫu nguồn đã rà soát.  
* Thiết kế chunking/context và đo token bằng model dự kiến; khóa chunk\_policy\_version sau pilot.  
* Sau đó triển khai ingestion CLI, kiểm định toàn corpus, xây chỉ mục và thực nghiệm.

## **16 2 Truy vết yêu cầu**

DR-01 → legal\_document/source\_file/corpus. DR-02 → legal\_unit/source\_span/assessment/chunk/context/view. DR-03 → hợp đồng đánh giá. DR-04 → DQ-01 đến DQ-10 và quality\_issue. DR-05 → hash, corpus/index/release manifest, nguyên tắc bất biến. Kiến trúc mục 7–8 → SQLite chỉ đọc, JSONL, Qdrant collection cụ thể và gói phát hành đồng nhất.

# **17 Tài liệu tham chiếu**

## **SRS v1.0**

https\://docs.google.com/document/d/1vGVHThtWevrpAaZ1R8iheY3iC3pUPo5l-hnN-oLYY7s

## **Thiết kế kiến trúc v1.0**

https\://docs.google.com/document/d/1BB8aiPDQmpcdBBdyDDvYEAo0S4Fzu-77JRnaM72sj8s

## **Danh mục nguồn v0.1**

https\://docs.google.com/document/d/1zwigO2YbDfZxIHXyUyen8r740w6m4eXz6CioYAUAztA

## **SQLite Foreign Key Support**

https\://www\.sqlite.org/foreignkeys.html

## **Qdrant Points**

https\://qdrant.tech/documentation/manage-data/points/

## **JSON Schema Draft 2020 12**

https\://json-schema.org/draft/2020-12

## **Luật 36 nguồn chính thức**

https\://vanban.chinhphu.vn/?pageid=27160\&docid=211194

## **Nghị định 168 nguồn chính thức**

https\://vanban.chinhphu.vn/?pageid=27160\&docid=212167

Các tài liệu kỹ thuật được đối chiếu ngày 15/10/2026. Nguồn luật ở đây là tham chiếu provenance; tài liệu thiết kế không xác nhận hoàn thành rà soát hiệu lực của toàn bộ corpus.

[image1]: <data:image/png;base64,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>

[image2]: <data:image/png;base64,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>