# Phiên 16 nhập nhãn relevance v6

Ngày thực thi 20/11/2026. Đã nhập 54 quyết định thuộc năm query, gồm 52 `confirm_previous` và 2 `change`. Snapshot sản phẩm là 2025-01-01. Nguồn, edition và applicability vẫn pending, scope ở mức proposal. Artifact là nhận xét relevance cho tập hữu hạn, chưa có metrics v6.

## Đầu vào và phép nhập

Tìm thấy phản hồi tại `staging/subset-v5-relevance-002/subset-v6-response-002/`. Ba tệp `submission.json`, `provenance.json` và `checks.json` được giữ nguyên byte trong `staging/subset-v6-response-capture-001/`. Các file đính kèm khác ở nguyên vị trí nguồn.

| Thành phần | SHA-256 |
|---|---|
| Packet manifest | `4b00216317afe4ee1532b867105f969e09988d0ab8e46a13dca80566dfbf7857` |
| Review core manifest | `343956e65fd82a3834ecb3059833ad3b31b7575486fc6d5eb3749c791c8af53a` |
| Dataset manifest | `47b23b4f8742a308f32b4c1efd0d7749a81a8aae792459b95e7035490802bdfc` |
| Index manifest | `58c05ef0f6c2bb39d4a6af8d62d5520843c028e538a0b5d8abeb2ce5d3589c5f` |
| Submission nhận được | `b5c50ba8bc1bb01b000b899a1c3e9c30f369c48ce88887c397b7debd4f1e32bf` |
| Capture manifest | `4ae8dcd15809f3fe266f009460c4eb942ac6749a33e1a7ca0a510eb38dbb4ea3` |
| Accepted manifest | `d5ab715923b05f05d037acbcfa7b06457a7082a90b586920c8c644143fcb473c` |
| ZIP accepted | `71c6000d986324d82cee98d0aa602568cd6b692f492aeba5c1298e968ed8e535` |

Validator nguyên bản phiên 15 trả 54 quyết định và 0 cặp chưa xác nhận. Adapter mới `src/v6_acceptance.py` kiểm hash của mã validator theo packet, chạy trên đúng byte đã capture rồi dựng nhãn v6 từ item được xác nhận. Mỗi dòng giữ query, record/type, payload/full-read/proposal hashes, 144 lượt tham chiếu EV6 trên toàn tập, relevance/relation/completeness/reason và lineage v5 khi có. Bản đọc lại kiểm lại evidence và dựng toàn bộ nhãn để so byte, kể cả khi manifest của bản sao đã được tạo lại.

| Query | Accepted |
|---|---:|
| dev-night_horn-3 | 10 |
| dev-driving_age-2 | 12 |
| dev-red_light-2 | 12 |
| V3-D05 | 10 |
| V3-D07 | 10 |

Phân bố relevance 2/1/0 là **7/8/39**. Cả tuổi và đèn đỏ có `2/direct_target/partial` với lý do v6 riêng theo submission. 53 cặp có lineage v5, trong đó nhóm A giữ nguyên quyết định và lý do cũ. Dòng đèn đỏ mới có lineage v5 rỗng.

Reviewer reference được giữ đúng `## CAL-039998018b`. Sự kiện xác nhận `2026-11-20T08:08:00+07:00` tương ứng `2026-11-20T01:08:00Z`. Capture và import diễn ra lần lượt tại `2026-11-20T13:18:55.345768+00:00` và `2026-11-20T13:18:57.203233+00:00`. Provenance ghi người dùng tiếp nhận đề xuất có AI hỗ trợ. Các EV6 refs thuộc quá trình trợ lý đọc bằng chứng. Trạng thái người dùng tự mở chi tiết để `null`.

## Kiểm chứng

- Chạy `packet_validator.py --packet ... --response ...` trên phản hồi gốc, thành công.
- Chạy `python -X utf8 -B -m src.v6_acceptance` với `capture`, `admit`, `validate` và `zip`. Mọi lệnh trả exit 0. Log và đối số thực tế ở `staging/source-session16-checks-001/`.
- Chạy `python -X utf8 -B -m unittest -v tests.test_v6_acceptance`. Bảy test đạt, không skip. Kiểm sai binding, thiếu metadata hoặc evidence, sai giờ, cặp trùng, sửa lý do đã xác nhận, nhập lặp và sửa quote trong artifact đã seal lại.
- Gọi lại `admit` trên bản chính trả 0 nhãn mới và giữ byte/mtime của tất cả file. Replay giữ import ID và byte nhãn. Thời điểm kỹ thuật của replay được ghi riêng.
- Giải nén ZIP vào thư mục sạch và chạy `python -X utf8 -I -S -B validate.py validate --packet packet --capture capture --accepted accepted`. Readback đủ 54 nhãn, exit 0. Kiểm trên Windows với CPython 3.11.9.

## Bảo toàn và giới hạn

Thư mục phản hồi do người dùng thêm nằm bên trong gói v5 `subset-v5-relevance-002`. Vì vậy `src.query_labels validate-aggregate` dừng ở kiểm inventory nghiêm ngặt. Đối chiếu riêng đủ 136 tệp được manifest v5 liệt kê cho thấy hash đều khớp. Seal của aggregate và các batch nhãn khớp. Đã so row hash của cả 59 accepted và 2 pending, gồm đúng hai mã V3-D02 rỗng. Sáu accepted ngoài năm query nằm trong lịch sử v5. Chi tiết sáu tệp thêm vào thư mục nguồn nằm ở `v5-inventory.json`. Giữ nguyên thư mục người dùng đã chuyển vào và validator cũ.

HEAD đầu phiên `b19452367cbea036d3949e0cdb05b35ff14a7115`. Giữ mọi thay đổi phiên 15, thêm adapter/tests và tài liệu phiên 16. STATUS thêm mục hiện tại và giữ byte phần lịch sử. Receipt kiểm bảo toàn và `git diff --check` ở `staging/source-session16-checks-001/preservation.final.json`. Các artifact v5, dataset/index/query và worktree Hùng được đối chiếu theo baseline.

[Hướng dẫn đọc và chạy lại](../handoff/Subset_V6_Accepted_Labels.md)
