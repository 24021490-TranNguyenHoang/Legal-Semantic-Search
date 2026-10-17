# Đề xuất xử lý DOCX legacy thiếu log tải — chưa được chấp thuận cho corpus

Snapshot 2025-01-01. Đây là đề xuất thiết kế để lựa chọn sau đối chiếu Điều 22,
không phải quyết định người dùng đã duyệt dữ liệu hoặc cho phép phát hành.

## Chính sách đang giữ nguyên

DOCX raw, file_id, hash, extraction, cây và các run cũ không đổi. download_url,
retrieved_at, edition/source_set evidence chưa biết vẫn pending. Không dùng
mtime/ctime hoặc thời điểm tải PDF mới thay ngày thu thập DOCX. Không gán URL
PDF cho DOCX để vượt NOT NULL source_file. Schema DDD giữ nguyên byte.

Phân biệt ba kết luận:

| Kết luận | Có thể chứng minh bằng gì? | Không suy ra |
|---|---|---|
| Byte DOCX không đổi | SHA-256/size so baseline | Nguồn gốc tải chính thức hoặc bản đầy đủ |
| Một vùng nội dung khớp | Unit/span/hash + PDF Công báo/page/quote/hash + toàn bộ diff và quy tắc so | Toàn DOCX/extraction/tree verified hoặc đủ điều kiện serving |
| Đơn vị đủ điều kiện corpus | Nguồn có hồ sơ thật, extraction/spans hợp lệ, quyết định phù hợp từng chiều, corpus/FK/manifest | Không có lối tắt bằng cờ content_match |

## Sử dụng ngay trong phạm vi được phép

Các đoạn đã đối chiếu chỉ dùng để rà soát, kiểm hồi quy và đề xuất phạm vi/hiệu
lực trong staging. comparison.jsonl khóa unit_id, text/span hash, extraction
locator/offset, PDF hash/page/text slice, raw differences và whitespace rule.
agent_findings.json ghi origin=agent_analysis_not_reviewer_decision và mức tin
cậy có giới hạn. Không ghi verified hoặc tự tạo event external_review_submission.
Reviewer có thể ghi riêng từng chiều sau khi thực tế kiểm tra; upstream vẫn
chặn corpus/serving. Không đồng nhất content match với provenance toàn file.

## Hai đường đề xuất để chọn trước khi chuyển DDD

1. **Bổ sung hồ sơ gốc đúng DOCX.** Cần bằng chứng tải/thu thập của đúng byte
   file, URL/edition/đủ phần. Thông tin không khôi phục được tiếp tục để trống,
   không tạo lịch sử giả. Khi đủ bằng chứng vẫn cần công đoạn tiếp nhận nguồn
   và promotion staging sang schema DDD có kiểm tra, hiện chưa có.
2. **Dùng nguồn chính thức mới làm nguồn corpus cho vùng được rà.** PDF Công
   báo mới tải có byte/hash/URL/time thật, tách khỏi source_file legacy. Có thể
   đề xuất extraction PDF Stage 3 (đã hỗ trợ đọc text) và ánh xạ spans hẹp cho
   nội dung Điều 22 đã đối chiếu bằng hồ sơ rà soát thực tế. Việc này cần contract
   ánh xạ, kiểm title/text/cha và locator trên extraction mới trước khi nhập;
   chưa được triển khai/chấp thuận trong lượt này. Không cần suy cây toàn PDF
   hoặc triển khai parser PDF chỉ để giải quyết log tải legacy. unit_id chỉ giữ
   nếu identity payload DDD thực sự không đổi; extraction/span IDs phải theo
   provenance/offset mới, không sao offsets DOCX sang PDF.

Đường 2 không nới schema DDD, nhưng bổ sung phương thức tiếp nhận/mapping nguồn
cho vùng được rà ngoài đường parser DOCX Stage 4 hiện hành. Vì thế đây là quyết
định thiết kế **đề xuất**, cần người dùng chọn trước bước triển khai riêng.
Trong cả hai đường, các nút cha thật cần cho FK phải có hồ sơ, các phần dùng làm
context phải được rà đúng phạm vi. Không buộc mở rộng đánh giá 4.000 unit.

## Kiểm tra cần thiết và giới hạn không phải điều kiện mới

Cần cho bài tập: nguồn/byte/URL/time trung thực; đúng bản/hiệu lực tại snapshot;
đối chiếu nội dung/spans/cha/context; bằng chứng và người/thời điểm quyết định
thật; IDs/FK/schema/manifest đúng; hồ sơ còn thiếu không được serving.

Chưa kiểm chữ ký số và chưa xây hệ thống phân quyền là giới hạn, không phải
cổng mới. Không yêu cầu người dùng hoàn thành hai việc đó để ghi quyết định
scope, applicability hoặc technical. Không tuyên bố kiểm kỹ thuật thay rà pháp lý.
