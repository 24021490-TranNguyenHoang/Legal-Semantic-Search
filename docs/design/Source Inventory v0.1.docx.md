# Danh mục nguồn dữ liệu pháp luật

# **Corpus giao thông tại ngày 01 tháng 01 năm 2025**

Phiên bản 0.1  |  Ngày lập 15/10/2026

Tài liệu ghi nhận mốc pháp lý đã chọn, danh mục nguồn khởi đầu và kế hoạch kiểm định phục vụ bước thiết kế dữ liệu chi tiết. Danh mục gồm bốn nguồn ban đầu và ba nguồn bổ sung theo chủ đề; phạm vi điều khoản sẽ được xác định sau đối chiếu bản gốc.

| Thuộc tính | Giá trị |
| :---- | :---- |
| Mã tài liệu | DATA-SOURCES-VTLS-0.1 |
| snapshot\_date | 2025-01-01 |
| Ngày rà soát nguồn | 2026-10-15; khác mốc pháp lý của corpus. |
| Mức hoàn thành | Đã xác định trang công bố chính thức cho 7 nguồn; chưa hoàn thành kiểm định từng điều khoản. |
| Trạng thái corpus | Chưa phát hành; chưa có checksum và thống kê chunk. |
| Nhãn trên demo | Tra cứu trong corpus pháp luật giao thông tại ngày 01/01/2025. |

## **1 Quyết định về mốc dữ liệu**

* Mốc 01/01/2025 là ngày áp dụng của dữ liệu tra cứu, không phải ngày tải file hay ngày tạo hệ thống.  
* Lưu bản nguồn nguyên gốc đầy đủ. Chỉ đưa đơn vị pháp lý đã xác minh áp dụng tại mốc này và thuộc phạm vi vào tập phục vụ.  
* Không dùng trạng thái còn hiệu lực hoặc hết hiệu lực tại thời điểm hiện tại để thay thế đánh giá lịch sử tại snapshot.  
* Văn bản sửa đổi sau mốc có thể được lưu làm tài liệu đối chiếu; không áp dụng nội dung sửa đổi chưa có hiệu lực tại snapshot. Nếu có quy định hồi tố liên quan, phải rà soát riêng và ghi bằng chứng.  
* Danh mục 7 nguồn là danh mục khảo sát v0.1, không phải khẳng định đã bao phủ toàn bộ pháp luật giao thông.

## **1.1 Liên kết với tài liệu dự án**

Quyết định này xác định giá trị snapshot\_date cho phần thông số dữ liệu còn mở trong SRS và thiết kế kiến trúc. Bộ tài liệu này ghi nhận quyết định; các bản BRD, SRS và kiến trúc đã phát hành chưa được sửa trực tiếp.

# **2 Danh mục nguồn khởi đầu**

## **SRC-001  36/2024/QH15**

Luật Trật tự, an toàn giao thông đường bộ

Ngày ban hành: 27/06/2024. Nguồn: Cổng thông tin điện tử Chính phủ.

[https\://vanban.chinhphu.vn/?pageid=27160\&docid=211194](https://vanban.chinhphu.vn/?pageid=27160&docid=211194)

Phạm vi khảo sát: Quy tắc giao thông, GPLX và điểm GPLX. Ưu tiên pilot.

Kiểm tra tiếp: Đọc Điều 88–89; tách Khoản 3 Điều 10 chưa áp dụng tại snapshot.

## **SRC-002  168/2024/NĐ-CP**

Quy định xử phạt vi phạm hành chính về trật tự, an toàn giao thông trong lĩnh vực giao thông đường bộ; trừ điểm, phục hồi điểm giấy phép lái xe

Ngày ban hành: 26/12/2024. Nguồn: Cổng thông tin điện tử Chính phủ.

[https\://vanban.chinhphu.vn/?pageid=27160\&docid=212167](https://vanban.chinhphu.vn/?pageid=27160&docid=212167)

Phạm vi khảo sát: Hành vi vi phạm, xử phạt và điểm GPLX. Ưu tiên pilot.

Kiểm tra tiếp: Đọc Điều 53–54; kiểm tra các ngoại lệ hiệu lực và chuyển tiếp.

## **SRC-003  35/2024/QH15**

Luật Đường bộ

Ngày ban hành: 27/06/2024. Nguồn: Cổng thông tin điện tử Chính phủ.

[https\://vanban.chinhphu.vn/?pageid=27160\&docid=211193](https://vanban.chinhphu.vn/?pageid=27160&docid=211193)

Phạm vi khảo sát: Chọn nội dung áp dụng trực tiếp cho người tham gia giao thông.

Kiểm tra tiếp: Rà soát điều khoản thi hành và phạm vi; không nạp toàn bộ phần quy hoạch, quản lý hạ tầng.

## **SRC-004  165/2024/NĐ-CP**

Quy định chi tiết, hướng dẫn thi hành một số điều của Luật Đường bộ và Điều 77 Luật Trật tự, an toàn giao thông đường bộ

Ngày ban hành: 26/12/2024. Nguồn: Cổng thông tin điện tử Chính phủ.

[https\://vanban.chinhphu.vn/?pageid=27160\&docid=212168](https://vanban.chinhphu.vn/?pageid=27160&docid=212168)

Phạm vi khảo sát: Nguồn khảo sát có chọn lọc theo phạm vi dự án.

Kiểm tra tiếp: Rà soát nội dung liên quan; tách thủ tục và quản lý hạ tầng ngoài phạm vi.

Trạng thái chung: official\_page\_found; điều khoản và bản tệp chờ kiểm định. Các ID SRC-001 đến SRC-004 giữ theo danh mục khởi đầu.

# **3 Nguồn bổ sung theo chủ đề**

## **SRC-005  38/2024/TT-BGTVT**

Quy định về tốc độ và khoảng cách an toàn của xe cơ giới, xe máy chuyên dùng tham gia giao thông trên đường bộ

Ngày ban hành: 15/11/2024. Ngày hiệu lực ghi trên trang công bố: 01/01/2025.

[https\://vanban.chinhphu.vn/?pageid=27160\&docid=211873](https://vanban.chinhphu.vn/?pageid=27160&docid=211873)

Phạm vi khảo sát: Bổ sung tốc độ và khoảng cách an toàn.

Kiểm tra tiếp: Giữ đầy đủ hàng/cột, đối tượng, loại đường và điều kiện của bảng.

## **SRC-006  51/2024/TT-BGTVT**

Ban hành Quy chuẩn kỹ thuật quốc gia về báo hiệu đường bộ

Ngày ban hành: 15/11/2024. Ngày hiệu lực ghi trên trang công bố: 01/01/2025.

[https\://vanban.chinhphu.vn/?pageid=27160\&docid=211908](https://vanban.chinhphu.vn/?pageid=27160&docid=211908)

Phạm vi khảo sát: Bổ sung nội dung quy chuẩn kèm theo về báo hiệu.

Kiểm tra tiếp: Thu thập cả văn bản ban hành và quy chuẩn; giữ mã biển, chú thích, liên kết hình.

## **SRC-007  35/2024/TT-BGTVT**

Quy định về đào tạo, sát hạch, cấp giấy phép lái xe; cấp, sử dụng giấy phép lái xe quốc tế; đào tạo, kiểm tra, cấp chứng chỉ bồi dưỡng kiến thức pháp luật về giao thông đường bộ

Ngày ban hành: 15/11/2024. Ngày hiệu lực ghi trên trang công bố: 01/01/2025.

[https\://vanban.chinhphu.vn/?pageid=27160\&docid=211984](https://vanban.chinhphu.vn/?pageid=27160&docid=211984)

Phạm vi khảo sát: Bổ sung nội dung trực tiếp liên quan người học, dự sát hạch và người có GPLX.

Kiểm tra tiếp: Chọn phần phù hợp; rà soát chuyển tiếp; không nạp toàn bộ quy trình quản lý cơ sở đào tạo.

## **3.1 Giới hạn của nguồn bổ sung**

Nguồn bổ sung được đề xuất theo các chủ đề đã có trong phạm vi dự án. Việc chọn vào tập phục vụ được thực hiện ở cấp điều khoản sau rà soát, không đồng nghĩa đưa toàn bộ văn bản vào corpus.

Đối với quy chuẩn báo hiệu, text không thể hiện hết ý nghĩa của mọi hình vẽ. Pilot ưu tiên các quy định đọc hiểu được bằng văn bản; đơn vị phụ thuộc hình được gắn cờ cần kiểm tra hoặc giữ làm tài liệu nguồn. Không triển khai nhận diện hình ảnh.

Các nội dung thủ tục phục hồi điểm, đăng ký hoặc kiểm định phương tiện cần khảo sát nguồn riêng nếu đưa thành phạm vi cam kết. Chưa coi danh mục hiện tại đã bao phủ các nội dung này.

# **4 Ngoại lệ hiệu lực cần đưa vào kiểm định**

Các điểm dưới đây được phát hiện từ toàn văn công bố trên chuyên trang Chính phủ. Trước phát hành corpus phải đối chiếu lại với bản gốc đính kèm. Đây là danh sách kiểm tra ban đầu, không phải toàn bộ ngoại lệ của 7 nguồn.

| Nguồn và vị trí | Nội dung kiểm tra | Xử lý tại 01/01/2025 |
| :---- | :---- | :---- |
| Luật 36; Điều 88 khoản 2 | Khoản 3 Điều 10 có mốc hiệu lực 01/01/2026 theo bản ban hành. | Không đưa Khoản 3 Điều 10 vào tập điều khoản áp dụng tại snapshot. |
| NĐ 168; Điều 53 khoản 2 | Điểm m khoản 3 Điều 6; điểm e khoản 4 Điều 26; điểm b khoản 1 Điều 27 có mốc 01/01/2026. | Đánh dấu chưa có hiệu lực tại snapshot; không lập chỉ mục phục vụ cho các đơn vị này. |
| NĐ 168; Điều 53 khoản 2 | Điểm b khoản 1 Điều 32 phụ thuộc quy định pháp luật bảo vệ môi trường về kiểm định khí thải mô tô, xe gắn máy. | Cách ly chờ căn cứ xác định mốc; không tự gán 01/01/2025. |
| Luật 36; Điều 89 và NĐ 168; Điều 54 | Có quy định chuyển tiếp. | Giữ điều kiện chuyển tiếp; kiểm tra dẫn chiếu trước khi chia chunk. |

## **4.1 Tác động tới schema và chunking**

* Ngày hiệu lực của văn bản và ngày hiệu lực của đơn vị pháp lý phải được phân biệt.  
* Tầng xử lý cần có trạng thái pending\_review, not\_yet\_effective, verified\_at\_snapshot và excluded\_scope; đây là trạng thái xử lý đề xuất, chưa thay schema SRS.  
* Tập phục vụ chỉ chứa đơn vị đạt kiểm định; không ghép một khoản chưa hiệu lực vào context\_text của chunk được phục vụ.  
* Khi trích một phần Điều, phải lưu citation\_path, vị trí nguồn và quy tắc chọn phần; không sửa bản raw để xóa điều khoản.

## **4.2 Nguồn đối chiếu ngoại lệ**

\[E1\] Luật 36, Điều 88–89: [https\://xaydungchinhsach.chinhphu.vn/toan-van-luat-trat-tu-an-toan-giao-thong-duong-bo-119240909105718285.htm](https://xaydungchinhsach.chinhphu.vn/toan-van-luat-trat-tu-an-toan-giao-thong-duong-bo-119240909105718285.htm)

\[E2\] Nghị định 168, Điều 53–54: [https\://xaydungchinhsach.chinhphu.vn/toan-van-nghi-dinh-168-2024-nd-cp-quy-dinh-xu-phat-vi-pham-hanh-chinh-ve-trat-tu-atgt-duong-bo-119241231164556785.htm](https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-dinh-168-2024-nd-cp-quy-dinh-xu-phat-vi-pham-hanh-chinh-ve-trat-tu-atgt-duong-bo-119241231164556785.htm)

# **5 Cấu trúc quản lý nguồn và công việc tiếp theo**

## **5.1 Bản ghi danh mục nguồn**

| Trường | Ý nghĩa và quy tắc |
| :---- | :---- |
| source\_id; law\_id; law\_title | ID danh mục; số hiệu; tên đầy đủ. |
| source\_url; issued\_date | Trang công bố chính thức và ngày ban hành. |
| scope\_note; related\_documents | Phạm vi dự kiến; văn bản liên quan hoặc dẫn chiếu cần kiểm tra. |
| snapshot\_date | 2025-01-01 cho đợt corpus này. |
| review\_status; verification\_note | Tiến độ công việc và bằng chứng; không dùng thay trạng thái hiệu lực pháp lý. |
| reviewed\_at | Ngày rà soát thực tế; lần rà soát này là 2026-10-15. |

## **5.2 Bản ghi tệp nguồn**

Một nguồn có thể có nhiều tệp: văn bản chính, phần tiếp và phụ lục. Mỗi tệp cần file\_id, source\_id, download\_url, filename, retrieved\_at, sha256, mime\_type và local\_ref. Các giá trị chỉ được ghi khi đã tải và kiểm tra; không dùng ngày snapshot làm retrieved\_at.

## **5.3 Trình tự thực hiện sau danh mục**

* Thu thập đầy đủ tệp của SRC-001 và SRC-002 trước để làm pilot; ghi checksum và kiểm tra trang thiếu.  
* Kiểm tra khả năng lấy text, phân biệt PDF có lớp text và bản scan; lưu bản raw nguyên vẹn.  
* Lập bảng hiệu lực ở cấp đơn vị và bảng chọn phạm vi; xử lý trước các ngoại lệ ở mục 4\.  
* Chọn mẫu đại diện: quy tắc ngắn, khoản có nhiều điểm, mức phạt kèm trừ điểm, dẫn chiếu và chuyển tiếp.  
* Thiết kế schema và chunking trên mẫu; sau đó áp dụng cho 5 nguồn còn lại và kiểm tra bảng/hình.

## **5.4 Đầu ra để chuyển sang thiết kế schema**

Danh mục nguồn có ID và URL; quyết định snapshot; danh sách tệp đầy đủ; báo cáo khả năng trích xuất; mẫu cấu trúc pháp lý và danh sách ngoại lệ. Ở bản 0.1 hiện đã có danh mục, snapshot và các ngoại lệ ban đầu; bước thu thập tệp và đối chiếu đầy đủ còn phải thực hiện.