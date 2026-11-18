# Candidate phiên 13 — development-gap-candidate.v1

Snapshot 2025-01-01. Dataset mới `vtls-subset-experimental.v6-candidate.1`.
Đây là candidate experimental, release_eligible=false, corpus_version=null;
nguồn/edition/applicability pending, scope là proposal, không human approval.

## Phương án tối thiểu

Consumer v5 kiểm lineage riêng của tập phiên 4. Không sửa consumer hoặc seal
v5 và không bịa lineage thay thế cho target mới. Bundle mới chứa bản v5 nguyên
byte trong `base/`, preview phiên 12 nguyên byte trong `preview/`, consumer
delta stdlib kế thừa các kiểm tra graph/frame/proof/type/encoder của v5.
Validator v5 tiếp tục kiểm toàn bộ base và lineage cũ; adapter mới chỉ cho
delta đã ghim: thêm A6K9b và thay read closure A59K1b bằng preview.

Giữ nguyên 138 record ID/type/payload/context. Target tuổi không đổi identity;
dependencies/native proofs và read response binding thay đổi. Target mới có
identity do builder phiên 12 tạo, không tạo lại bằng thay ID payload cũ.
Không nhập assessment, accepted, pending, qrels hoặc evaluation vào dataset.
Các hash lineage evaluation trong preview chỉ là provenance, không nhãn kế thừa.

Graph là hợp của base và projection phiên 12; cùng ID phải cùng unit payload.
Span cùng ID phải cùng payload; cha phải đủ và cùng nguồn. Không mở subtree.
Supporting là hợp dependency thực tế của target, không mọi proposal supporting.
Nút mới có proposal supporting/structural theo vai trò sử dụng cụ thể, không
truyền scope xuống con. Bản proposal cũ được giữ nguyên khi unit đã tồn tại.

Các extraction đã có trong base được tái sử dụng. Alias mới chỉ được nhận khi
file thực tế cùng SHA với binding raw/text/trace/identity đã chọn. Assets là
file nội bộ bundle; đường dẫn workspace trong payload chỉ là provenance label.
Bằng chứng agent review phiên 12 được đóng gói kèm mount/hash; không chuyển
thành quyết định reviewer hoặc xác minh nguồn toàn file.

## Kiểm chứng và giao diện

`consumer.py validate/list/read/full-read --dataset candidate` dùng stdlib
Python >=3.11. Không cần repository, tokenizer, PyTorch, cache hay mạng.
Consumer tái tạo hợp xác định từ base+preview, so với plan/graph/spans/proposals
đã xuất; đọc và kiểm toàn bộ target, table, whole-source, form, encoder views.
Các kiểm tra v5 được tái dùng; lineage mới ghi added_target, không giả replaced.
Manifest ghim base, preview, runtime, contract; checksum là kiểm toàn vẹn,
không phải chữ ký số. Runtime không nạp label hoặc tính metrics.

Delta phân biệt: target payload, supporting membership, graph node, span,
frame và read-response hash. Toàn bộ response có dataset version/package
locator mới; không diễn giải mọi response hash đổi thành nội dung luật đổi.
Target tuổi thay closure nên tuyệt đối không tự chuyển nhãn dù ID giữ nguyên.

Replay đóng gói không chạy lại parser/correction/tokenizer. ZIP có timestamp
cố định cho khả năng tái tạo; thời điểm kiểm chứng thật ở báo cáo ngoài seal.
Audit thử consumer trong bản giải nén riêng, chặn đọc repository/cache gốc,
chặn mạng/subprocess sau khi khởi động. Không gọi đây là thử trên máy/OS khác.
