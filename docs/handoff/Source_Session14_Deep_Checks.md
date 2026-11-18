# Phiên14 — kiểm tra sâu bốn query
Origin=agent_review; snapshot2025-01-01; source/edition/applicability pending, scope proposal. Không dùng quan sát này đổi accepted labels hoặc tính metrics.
Binding: datasetv6 47b23b4…; indexv2 58c05ef…; frozen query manifest f8cc925… . Xem report phiên14 để lấy hash đầy đủ.

## dev-red_light-2
Query giữ nguyên: Lái xe ô tô vượt đèn đỏ bị xử lý ra sao?

Target: `c_fcaa52f3e09aa9b0719e84d05d9d13a9bd68343ff44f596fd379553ded82f4c6`
Rank v5→v6: None → 4; required own-unit reads None → 7

b) Không chấp hành hiệu lệnh của đèn tín hiệu giao thông;

### Context nguyên văn

u_a3b6d08589f5064fbe0ced8de1d9cc9256f8dde942b93100cfed7e5afb4a327d / title / field offsets [0,206)

Xử phạt, trừ điểm giấy phép lái xe của người điều khiển xe ô tô, xe chở người bốn bánh có gắn động cơ, xe chở hàng bốn bánh có gắn động cơ và các loại xe tương tự xe ô tô vi phạm quy tắc giao thông đường bộ

u_8c31b7b7220053d22f36f067635755013d4c5f9bb8e22c003011392d0709df29 / text_original / field offsets [0,128)

9. Phạt tiền từ 18.000.000 đồng đến 20.000.000 đồng đối với người điều khiển xe thực hiện một trong các hành vi vi phạm sau đây:

### Required-read nguyên văn

168/2024/NĐ-CP > Chương II > Mục 1 > Điều 6 > Khoản 16


16. Ngoài việc bị áp dụng hình thức xử phạt, người điều khiển xe thực hiện hành vi vi phạm còn bị trừ điểm giấy phép lái xe như sau:

168/2024/NĐ-CP > Chương II > Mục 1 > Điều 6 > Khoản 16 > Điểm b


b) Thực hiện hành vi quy định tại điểm h khoản 5; khoản 6; điểm b khoản 7; điểm b, điểm c, điểm d khoản 9 Điều này bị trừ điểm giấy phép lái xe 04 điểm;

168/2024/NĐ-CP > Chương II > Mục 1 > Điều 6 > Khoản 10 > Điểm b


b) Vi phạm quy định tại một trong các điểm, khoản sau của Điều này mà gây tai nạn giao thông: điểm a, điểm b, điểm c, điểm d, điểm đ khoản 1; điểm c khoản 2; điểm b, điểm g, điểm h, điểm n, điểm o, điểm p, khoản 3; điểm a, điểm c, điểm d khoản 4; điểm c, điểm d, điểm e, điểm h, điểm n, điểm o, điểm q khoản 5; điểm b khoản 7; điểm b, điểm c, điểm d khoản 9 Điều này.

168/2024/NĐ-CP > Chương II > Mục 1 > Điều 6 > Khoản 9


9. Phạt tiền từ 18.000.000 đồng đến 20.000.000 đồng đối với người điều khiển xe thực hiện một trong các hành vi vi phạm sau đây:

168/2024/NĐ-CP > Chương II > Mục 1 > Điều 6 > Khoản 16 > Điểm d


d) Thực hiện hành vi quy định tại điểm a khoản 9, khoản 10, điểm đ khoản 11 Điều này bị trừ điểm giấy phép lái xe 10 điểm.

168/2024/NĐ-CP > Chương II > Mục 1 > Điều 6

Xử phạt, trừ điểm giấy phép lái xe của người điều khiển xe ô tô, xe chở người bốn bánh có gắn động cơ, xe chở hàng bốn bánh có gắn động cơ và các loại xe tương tự xe ô tô vi phạm quy tắc giao thông đường bộ


168/2024/NĐ-CP > Chương II > Mục 1 > Điều 6 > Khoản 10


10. Phạt tiền từ 20.000.000 đồng đến 22.000.000 đồng đối với người điều khiển xe thực hiện một trong các hành vi vi phạm sau đây:

Source spans/proofs nguyên envelope: [deep_checks.json](../../staging/bm25-v5-v6-comparison-001/deep_checks.json). Read slice/hash đã qua consumer; không chuyển offsets từ nhánh nguồn khác.

## dev-driving_age-2
Query giữ nguyên: Bao nhiêu tuổi mới được điều khiển xe mô tô?

Target: `c_30a64fc1bea93d7860d4f3821af382006956ca7dcbdc7770e636782e97fb1d9e`
Rank v5→v6: 15 → 15; required own-unit reads 2 → 16

b) Người đủ 18 tuổi trở lên được cấp giấy phép lái xe hạng A1, A, B1, B, C1, được cấp chứng chỉ bồi dưỡng kiến thức pháp luật về giao thông đường bộ để điều khiển xe máy chuyên dùng tham gia giao thông đường bộ;

### Context nguyên văn

u_3fdd29d7059276581549e78f2fe31f20803297608be9e55f0d1c218034174fb9 / title / field offsets [0,76)

Tuổi, sức khỏe của người điều khiển phương tiện tham gia giao thông đường bộ

u_97509a7f35446b3a6e332fa668cb8bca569884af4a4871003e6050dcb2a769f4 / text_original / field offsets [0,87)

1. Độ tuổi của người lái xe, người điều khiển xe máy chuyên dùng được quy định như sau:

### Required-read nguyên văn

36/2024/QH15 > Chương III > Điều 34 > Khoản 1 > Điểm e


e) Xe mô tô gồm: xe có hai hoặc ba bánh chạy bằng động cơ, được thiết kế, sản xuất để hoạt động trên đường bộ, trừ xe gắn máy; đối với xe ba bánh thì khối lượng bản thân không lớn hơn 400 kg;

36/2024/QH15 > Chương IV > Điều 57 > Khoản 1 > Điểm c


c) Hạng B1 cấp cho người lái xe mô tô ba bánh và các loại xe quy định cho giấy phép lái xe hạng A1;

36/2024/QH15 > Chương IV > Điều 59

Tuổi, sức khỏe của người điều khiển phương tiện tham gia giao thông đường bộ


36/2024/QH15 > Chương IV > Điều 56 > Khoản 1 > Điểm b


b) Giấy phép lái xe phù hợp với loại xe đang điều khiển;

36/2024/QH15 > Chương IV > Điều 57 > Khoản 1


1. Giấy phép lái xe bao gồm các hạng sau đây:

36/2024/QH15 > Chương III > Điều 34

Phân loại phương tiện giao thông đường bộ


36/2024/QH15 > Chương IV > Điều 57 > Khoản 1 > Điểm b


b) Hạng A cấp cho người lái xe mô tô hai bánh có dung tích xi-lanh  trên 125 cm3 hoặc có công suất động cơ điện trên 11 kW và các loại xe quy định cho giấy phép lái xe hạng A1;

36/2024/QH15 > Chương IV > Điều 57 > Khoản 1 > Điểm a


a) Hạng A1 cấp cho người lái xe mô tô hai bánh có dung tích xi-lanh đến 125 cm3 hoặc có công suất động cơ điện đến 11 kW;

36/2024/QH15 > Chương IV > Điều 59 > Khoản 1


1. Độ tuổi của người lái xe, người điều khiển xe máy chuyên dùng được quy định như sau:

36/2024/QH15 > Chương IV > Điều 56

Điều kiện của người điều khiển phương tiện tham gia giao thông đường bộ


36/2024/QH15 > Chương IV > Điều 57

Giấy phép lái xe


36/2024/QH15 > Chương III > Điều 34 > Khoản 1


1. Xe cơ giới bao gồm:

36/2024/QH15 > Chương III > Điều 34 > Khoản 1 > Điểm g


g) Xe gắn máy là xe có hai hoặc ba bánh chạy bằng động cơ, được thiết kế, sản xuất để hoạt động trên đường bộ, có vận tốc thiết kế không lớn hơn 50 km/h; nếu động cơ dẫn động là động cơ nhiệt thì dung tích làm việc hoặc dung tích tương đương không lớn hơn 50 cm3; nếu động cơ dẫn động là động cơ điện thì công suất của động cơ không lớn hơn 04 kW; xe gắn máy không bao gồm xe đạp máy;

36/2024/QH15 > Chương IV > Điều 56 > Khoản 4


4. Người lái xe gắn máy tham gia giao thông đường bộ phải hiểu biết quy tắc giao thông đường bộ, có kỹ năng điều khiển phương tiện; đủ điều kiện về độ tuổi, sức khỏe theo quy định tại điểm a khoản 1 và khoản 2 Điều 59 của Luật này.

36/2024/QH15 > Chương IV > Điều 56 > Khoản 1


1. Người lái xe tham gia giao thông đường bộ phải đủ tuổi, sức khỏe theo quy định của pháp luật; có giấy phép lái xe đang còn điểm, còn hiệu lực phù hợp với loại xe đang điều khiển do cơ quan có thẩm quyền cấp, trừ người lái xe gắn máy quy định tại khoản 4 Điều này. Khi tham gia giao thông đường bộ, người lái xe phải mang theo các giấy tờ sau đây:

36/2024/QH15 > Chương IV > Điều 59 > Khoản 1 > Điểm a


a) Người đủ 16 tuổi trở lên được điều khiển xe gắn máy;

Source spans/proofs nguyên envelope: [deep_checks.json](../../staging/bm25-v5-v6-comparison-001/deep_checks.json). Read slice/hash đã qua consumer; không chuyển offsets từ nhánh nguồn khác.

## V3-D05
Query: Ở tốc độ đúng 60 km/h cần cách xe trước ít nhất bao nhiêu mét?

| Rank | Record ID | Type | Citation |
|---|---|---|---|
| 1 | rv_0916941b9b7db992fc538429b284e82378867ea9f955c146dfd3cad46fedb6f9 | source-retrieval.v1 | 38/2024/TT-BGTVT > Chương II > Điều 11 > Khoản 2 > Điểm b |
| 2 | tr_824017275f85f56315730a69283f12135b509778b1c64c9655d38392ecc83beb | table-retrieval.v1 | 38/2024/TT-BGTVT > Chương II > Điều 11 > Khoản 2 > Điểm a |
| 3 | tr_7d96624a118ba37e1ec17a7d886fe612582b69cccbf29fe261e13a0e0d2ad64d | table-retrieval.v1 | 38/2024/TT-BGTVT > Chương II > Điều 11 > Khoản 2 > Điểm a |
| 4 | c_94e9af6a8818fd0df403046d9a7468fc2d785608e9711e4e7192f5b43f4e4c32 | chunk.v1 | 38/2024/TT-BGTVT > Chương II > Điều 9 > Khoản 3 |
| 5 | tr_48dd2c5f29cc0f090f1f8a3a0ed9d37e3a56b637804beb2331d0355d6fad40be | table-retrieval.v1 | 38/2024/TT-BGTVT > Chương II > Điều 11 > Khoản 2 > Điểm a |
| 6 | tr_ac4f3afd92e8ae309f157b9f601c5d3d69adf93094bc9e29e2780c321e91e021 | table-retrieval.v1 | 38/2024/TT-BGTVT > Chương II > Điều 11 > Khoản 2 > Điểm a |
| 7 | tr_03f3ae425e4a1930d6081703c72e22aba780a4cdfd1402625e9ce8081e6308e6 | table-retrieval.v1 | 38/2024/TT-BGTVT > Chương II > Điều 6 > Khoản 1 |
| 8 | tr_090bd1839f3130d3e8d67a5956fa3bf91e3f658f53ee632a62138f9cdf6dfa8f | table-retrieval.v1 | 38/2024/TT-BGTVT > Chương II > Điều 6 > Khoản 2 |
| 9 | tr_268d7ec2a87e5f4f716c80b84a79e3e2a9600de6b8d4d437fbc1577b0a0808ec | table-retrieval.v1 | 38/2024/TT-BGTVT > Chương II > Điều 6 > Khoản 2 |
| 10 | c_ab92855d2e304336e166c7cb67d4fb72e57c0a8b9c9d2a01d4d283df02133364 | chunk.v1 | 38/2024/TT-BGTVT > Chương II > Điều 11 > Khoản 1 |

### Hàng bảng / điều kiện từ record đọc thật

`tr_824017275f85f56315730a69283f12135b509778b1c64c9655d38392ecc83beb`

a) Trong điều kiện mặt đường khô ráo, không có sương mù, mặt đường không
trơn trượt, địa hình bằng phẳng, đường thẳng, tầm nhìn bảo đảm, khoảng cách an
toàn ứng với mỗi tốc độ được quy định như sau:
Khi điều khiển xe chạy với tốc độ dưới 60 km/h, người lái xe, người điều
khiển xe máy chuyên dùng phải chủ động giữ khoảng cách an toàn phù hợp với xe
chạy liền trước xe của mình; khoảng cách này tùy thuộc vào mật độ phương tiện,
tình hình giao thông thực tế để đảm bảo an toàn giao thông.

Tốc độ lưu hành (V km/h): V = 60
Khoảng cách an toàn (m): 35

`tr_7d96624a118ba37e1ec17a7d886fe612582b69cccbf29fe261e13a0e0d2ad64d`

a) Trong điều kiện mặt đường khô ráo, không có sương mù, mặt đường không
trơn trượt, địa hình bằng phẳng, đường thẳng, tầm nhìn bảo đảm, khoảng cách an
toàn ứng với mỗi tốc độ được quy định như sau:
Khi điều khiển xe chạy với tốc độ dưới 60 km/h, người lái xe, người điều
khiển xe máy chuyên dùng phải chủ động giữ khoảng cách an toàn phù hợp với xe
chạy liền trước xe của mình; khoảng cách này tùy thuộc vào mật độ phương tiện,
tình hình giao thông thực tế để đảm bảo an toàn giao thông.

Tốc độ lưu hành (V km/h): 60 < V ≤ 80
Khoảng cách an toàn (m): 55

`tr_48dd2c5f29cc0f090f1f8a3a0ed9d37e3a56b637804beb2331d0355d6fad40be`

a) Trong điều kiện mặt đường khô ráo, không có sương mù, mặt đường không
trơn trượt, địa hình bằng phẳng, đường thẳng, tầm nhìn bảo đảm, khoảng cách an
toàn ứng với mỗi tốc độ được quy định như sau:
Khi điều khiển xe chạy với tốc độ dưới 60 km/h, người lái xe, người điều
khiển xe máy chuyên dùng phải chủ động giữ khoảng cách an toàn phù hợp với xe
chạy liền trước xe của mình; khoảng cách này tùy thuộc vào mật độ phương tiện,
tình hình giao thông thực tế để đảm bảo an toàn giao thông.

Tốc độ lưu hành (V km/h): 100 < V ≤ 120
Khoảng cách an toàn (m): 100

`tr_ac4f3afd92e8ae309f157b9f601c5d3d69adf93094bc9e29e2780c321e91e021`

a) Trong điều kiện mặt đường khô ráo, không có sương mù, mặt đường không
trơn trượt, địa hình bằng phẳng, đường thẳng, tầm nhìn bảo đảm, khoảng cách an
toàn ứng với mỗi tốc độ được quy định như sau:
Khi điều khiển xe chạy với tốc độ dưới 60 km/h, người lái xe, người điều
khiển xe máy chuyên dùng phải chủ động giữ khoảng cách an toàn phù hợp với xe
chạy liền trước xe của mình; khoảng cách này tùy thuộc vào mật độ phương tiện,
tình hình giao thông thực tế để đảm bảo an toàn giao thông.

Tốc độ lưu hành (V km/h): 80 < V ≤ 100
Khoảng cách an toàn (m): 70

Whole-source ở rank1 giữ source_record và table_rows/cells, encoder views chỉ là projection. Full response có required-read, source proofs và điều kiện bất lợi. Text bảng là dẫn xuất, tách nguyên văn owner; không thay nguyên văn bằng diễn giải.

## V3-D07
Query: Chạy 81 km/h thì khoảng cách an toàn khác lúc chạy 80 thế nào?

| Rank | Record ID | Type | Citation |
|---|---|---|---|
| 1 | rv_0916941b9b7db992fc538429b284e82378867ea9f955c146dfd3cad46fedb6f9 | source-retrieval.v1 | 38/2024/TT-BGTVT > Chương II > Điều 11 > Khoản 2 > Điểm b |
| 2 | tr_7d96624a118ba37e1ec17a7d886fe612582b69cccbf29fe261e13a0e0d2ad64d | table-retrieval.v1 | 38/2024/TT-BGTVT > Chương II > Điều 11 > Khoản 2 > Điểm a |
| 3 | tr_ac4f3afd92e8ae309f157b9f601c5d3d69adf93094bc9e29e2780c321e91e021 | table-retrieval.v1 | 38/2024/TT-BGTVT > Chương II > Điều 11 > Khoản 2 > Điểm a |
| 4 | rv_073f041e0382ecd951764ed2e4de64e9d301875f78fddaf33d28d8e57d8da2f1 | source-retrieval.v1 | QCVN/rule:6.4 |
| 5 | tr_824017275f85f56315730a69283f12135b509778b1c64c9655d38392ecc83beb | table-retrieval.v1 | 38/2024/TT-BGTVT > Chương II > Điều 11 > Khoản 2 > Điểm a |
| 6 | tr_48dd2c5f29cc0f090f1f8a3a0ed9d37e3a56b637804beb2331d0355d6fad40be | table-retrieval.v1 | 38/2024/TT-BGTVT > Chương II > Điều 11 > Khoản 2 > Điểm a |
| 7 | c_ab92855d2e304336e166c7cb67d4fb72e57c0a8b9c9d2a01d4d283df02133364 | chunk.v1 | 38/2024/TT-BGTVT > Chương II > Điều 11 > Khoản 1 |
| 8 | c_106d4f03daf7303e0d866aa313d7714d5ae03b21b364a38057ba181f0a43c8cc | chunk.v1 | 36/2024/QH15 > Chương II > Điều 12 > Khoản 3 > Điểm c |
| 9 | c_94e9af6a8818fd0df403046d9a7468fc2d785608e9711e4e7192f5b43f4e4c32 | chunk.v1 | 38/2024/TT-BGTVT > Chương II > Điều 9 > Khoản 3 |
| 10 | tr_19906379710bf99bdcdbbccecfe41baea5354436a130b8e811920c3d82e34c12 | table-retrieval.v1 | 38/2024/TT-BGTVT > Chương II > Điều 6 > Khoản 2 |

### Hàng bảng / điều kiện từ record đọc thật

`tr_7d96624a118ba37e1ec17a7d886fe612582b69cccbf29fe261e13a0e0d2ad64d`

a) Trong điều kiện mặt đường khô ráo, không có sương mù, mặt đường không
trơn trượt, địa hình bằng phẳng, đường thẳng, tầm nhìn bảo đảm, khoảng cách an
toàn ứng với mỗi tốc độ được quy định như sau:
Khi điều khiển xe chạy với tốc độ dưới 60 km/h, người lái xe, người điều
khiển xe máy chuyên dùng phải chủ động giữ khoảng cách an toàn phù hợp với xe
chạy liền trước xe của mình; khoảng cách này tùy thuộc vào mật độ phương tiện,
tình hình giao thông thực tế để đảm bảo an toàn giao thông.

Tốc độ lưu hành (V km/h): 60 < V ≤ 80
Khoảng cách an toàn (m): 55

`tr_ac4f3afd92e8ae309f157b9f601c5d3d69adf93094bc9e29e2780c321e91e021`

a) Trong điều kiện mặt đường khô ráo, không có sương mù, mặt đường không
trơn trượt, địa hình bằng phẳng, đường thẳng, tầm nhìn bảo đảm, khoảng cách an
toàn ứng với mỗi tốc độ được quy định như sau:
Khi điều khiển xe chạy với tốc độ dưới 60 km/h, người lái xe, người điều
khiển xe máy chuyên dùng phải chủ động giữ khoảng cách an toàn phù hợp với xe
chạy liền trước xe của mình; khoảng cách này tùy thuộc vào mật độ phương tiện,
tình hình giao thông thực tế để đảm bảo an toàn giao thông.

Tốc độ lưu hành (V km/h): 80 < V ≤ 100
Khoảng cách an toàn (m): 70

`tr_824017275f85f56315730a69283f12135b509778b1c64c9655d38392ecc83beb`

a) Trong điều kiện mặt đường khô ráo, không có sương mù, mặt đường không
trơn trượt, địa hình bằng phẳng, đường thẳng, tầm nhìn bảo đảm, khoảng cách an
toàn ứng với mỗi tốc độ được quy định như sau:
Khi điều khiển xe chạy với tốc độ dưới 60 km/h, người lái xe, người điều
khiển xe máy chuyên dùng phải chủ động giữ khoảng cách an toàn phù hợp với xe
chạy liền trước xe của mình; khoảng cách này tùy thuộc vào mật độ phương tiện,
tình hình giao thông thực tế để đảm bảo an toàn giao thông.

Tốc độ lưu hành (V km/h): V = 60
Khoảng cách an toàn (m): 35

`tr_48dd2c5f29cc0f090f1f8a3a0ed9d37e3a56b637804beb2331d0355d6fad40be`

a) Trong điều kiện mặt đường khô ráo, không có sương mù, mặt đường không
trơn trượt, địa hình bằng phẳng, đường thẳng, tầm nhìn bảo đảm, khoảng cách an
toàn ứng với mỗi tốc độ được quy định như sau:
Khi điều khiển xe chạy với tốc độ dưới 60 km/h, người lái xe, người điều
khiển xe máy chuyên dùng phải chủ động giữ khoảng cách an toàn phù hợp với xe
chạy liền trước xe của mình; khoảng cách này tùy thuộc vào mật độ phương tiện,
tình hình giao thông thực tế để đảm bảo an toàn giao thông.

Tốc độ lưu hành (V km/h): 100 < V ≤ 120
Khoảng cách an toàn (m): 100

Whole-source ở rank1 giữ source_record và table_rows/cells, encoder views chỉ là projection. Full response có required-read, source proofs và điều kiện bất lợi. Text bảng là dẫn xuất, tách nguyên văn owner; không thay nguyên văn bằng diễn giải.

## Kết luận có phạm vi
V=60 thuộc hàng35m; 60<V≤80 thuộc55m; 80<V≤100 thuộc70m trong đúng bảng/điều kiện đã lưu. V3-D05 hàng35m rank2; V3-D07 hai hàng55m/70m rank2/3. Một hit partial không đủ câu hỏi80/81; điều kiện và bất lợi phải đọc kèm. Checker evidence v1 được tái dùng ở validation run; kết quả không thay completeness accepted hoặc applicability pháp lý.
Target đèn đỏ mới rank4; age giữ15. Closure tuổi2→16 không làm thay đổi projection hoặc riêng nó cải thiện ranking. Không có target bị xóa/mappingID sang căn cứ khác.

Markdown bỏ khoảng trắng cuối dòng khi trình bày; nguyên văn hash-bound giữ đầy đủ trong deep_checks.json và bundle, không sửa text/spans nguồn.
