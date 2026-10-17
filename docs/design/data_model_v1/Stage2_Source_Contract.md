# Stage 2 — Hồ sơ nguồn và contract nền

Snapshot: **2025-01-01**. Stage này không xác minh pháp lý, không trích xuất text,
không thay parser/chunker, không chạy mô hình hoặc xây index. Giới hạn inference
WinError 4551 của Stage 1 vẫn còn, không cần giải quyết để chạy Stage 2.

## Schema chính thức và lớp pending

`schemas/data_model_v1/schema.sql` là bản byte nguyên vẹn của `schema.sql` trong
`Data_Model_Schema_Examples_v1.0.zip`. `provenance.json` lưu hash ZIP/member.
Không đổi NOT NULL, enum, khóa hoặc view của mẫu. JSON Schema Draft 2020-12 cho
legal_document/source_file/extraction được triển khai từ từ điển DDD và mẫu;
validator bật FormatChecker và kiểm tra thêm kiểu số nguyên, NFC/LF, URL.

Run tạo hai SQLite:

- `content.sqlite`: đủ 12 bảng lõi/view thiết kế, **0 bản ghi**. Đây là nền staging,
  chưa phải serving corpus. Mỗi kết nối ghi bật `PRAGMA foreign_keys=ON` trước
  transaction. Validator mở `mode=ro`, bật `query_only` và kiểm tra FK/integrity.
- `pending.sqlite`: schema staging riêng `pending_schema.sql`, có
  pending_document, pending_file, pending_quality_issue và FK/UNIQUE tương ứng.
  Hồ sơ JSON trong các bảng phải khớp export JSONL và cấu hình đăng ký.

DDD quality_issue yêu cầu corpus_version tham chiếu corpus. Stage 2 chưa có
corpus/đơn vị pháp lý hợp lệ nên không tạo corpus giả để điền FK; quality issue
nguồn nằm ở lớp pending riêng. Không coi schema pending là schema DDD thay thế.

## Đo được, khai báo và bằng chứng

`config/source_registration.v1.json` là cấu hình khai báo có phiên bản, không phải
hồ sơ thu thập chính thức. source_id/law_id/tên/URL ứng viên/ngày ban hành ứng
viên lấy từ Source Inventory. Những dữ kiện đó chưa chứng minh DOCX hiện tại là
bản ban hành đầy đủ tương ứng. Không tải lại nguồn trong Stage 2.

| Nhóm | Trường | Trạng thái |
| --- | --- | --- |
| Đo từ byte tệp | size_bytes, sha256, mime_type | Đo trực tiếp; MIME dựa vào cấu trúc gói DOCX, không chỉ đuôi tệp. Không kiểm chứng nội dung pháp lý. |
| Vị trí quan sát | filename, raw_file_ref | Đường dẫn tương đối với `--raw-root`; giữ layout raw hiện có, không di chuyển/ghi lại raw. |
| Khai báo điều phối | law_id, source_id, source_set_id, file_role, part_order | Khai báo tường minh trong config; không suy thứ tự phần từ tên tệp. Mỗi nhóm hiện chỉ có một tệp quan sát, chưa chứng minh đầy đủ phần/phụ lục. |
| Gợi ý từ tài liệu | declared.source_url_candidate, issued_date_candidate, inventory_ref, tên và loại văn bản | Giữ riêng trong declared, không dùng trực tiếp thay trường chính thức. |
| Cần bằng chứng | evidence.source_url, issued_date, edition, verification_ref, reviewer_ref, verified_at | null và pending trên bốn hồ sơ document. |
| Cần bằng chứng tệp | evidence.download_url, retrieved_at, edition, verification_ref, source_set_complete | null và pending trên bốn hồ sơ file. |

Mỗi trường evidence chưa có tạo một quality issue error/pending: 6 trường × 4
document + 5 trường × 4 file = **44 issue**. Đây là số cổng bằng chứng còn thiếu
của profile đăng ký này, không phải 44 kết luận rằng nội dung luật sai.

`expected_sha256` trong config được đo từ raw hiện tại để phát hiện byte đổi;
không phải chữ ký xác nhận nguồn chính thức. Không lấy mtime/ctime, ngày inventory
hoặc ngày chạy làm retrieved_at. `built_at` ở manifest chỉ là thời điểm chạy kỹ thuật.
Không tạo extraction placeholder, ngày trích xuất hoặc cờ verified cho text cũ.

## Quy tắc định danh ổn định

DDD cho phép file_id là UUID/ID điều phối cấp một lần, chưa quy định công thức
UUID của source_file. Stage 2 cụ thể hóa chính sách cấp UUID của dự án, không
gọi đây là công thức bắt buộc sẵn có trong DDD:

```text
file_id = UUIDv5(file_id_namespace,
    canonical_json({identity_schema: "source-file.v1", law_id, sha256}))
```

canonical_json dùng sort_keys, UTF-8 giữ dấu, separators=(",", ":") theo DDD.
Namespace được cấp một lần và khóa trong config; không dùng namespace Qdrant
của fixture. Tên/đường dẫn tệp và built_at không tham gia file_id. Chạy lại cùng
config/raw giữ nguyên ID; đổi tên file giữ nguyên ID; byte hoặc law_id khác có
ID khác. Nếu phát hiện gán sai văn bản, giữ hồ sơ cũ để truy vết, tạo hồ sơ sửa
mới; không tái gán âm thầm một ID cũ. Namespace/config phải được lưu cùng code.

source_set_id cũng được khai báo và giữ ổn định trong config. Đây là nhóm local
DOCX ứng viên; issue `source_set_complete` chặn việc coi nhóm là bản đầy đủ trước
rà soát. Không tạo unit_id/chunk_id/corpus_version trong Stage 2.

## Artifact và validator

Run mới dưới staging có schema/contract/config chụp lại, hai SQLite, ba JSONL,
validation_report.json, manifest.json, manifest.sha256 và run_report.json.
Đây là **source registration manifest**, chưa phải corpus/index/release manifest
đầy đủ theo DDD §13. SHA-256 sidecar tránh checksum tự tham chiếu.

Manifest bao phủ byte/kích thước các artifact, kể cả SQLite và report kiểm tra;
run_report.json được ghi cuối bởi cơ chế Stage 1, không nằm trong checksum
manifest. Validator không dùng run_report làm bằng chứng sẵn sàng/phát hành.
Checksum phát hiện thay đổi, không thay thế chữ ký hoặc kiểm chứng nguồn.

Validator tái đo raw, tái tính UUID/issues từ config, kiểm tra JSON Schema,
ID/quan hệ/part order, SQLite FK/integrity/cấu trúc, export so với DB,
schema đích nguyên vẹn và manifest hashes/counts. Việc sửa flag hoặc tự tính lại
checksum không làm pending thành verified: nội dung còn bị đối chiếu lại với
config/DB/contract. Trong Stage 2, mọi evidence thực chưa có luôn là null;
profile này không phải công cụ tiếp nhận/phê duyệt evidence mới.

`validate` trả 0 nếu gói đăng ký **hợp lệ kỹ thuật**, vẫn in release_eligible=false.
`validate --require-release-ready` trả 1 cho các run Stage 2. Không có lệnh activate,
promote hoặc publish. Test dữ liệu giả dùng dataset_kind=synthetic_fixture và
namespace/thư mục tạm riêng; không chép fixture mẫu vào run legal_sources.

Contract extraction chỉ kiểm tra artifact đã có: khóa file_id, text hash, số
Unicode code point, UTF-8 không BOM/NFC/LF, method/tool/version và timestamp UTC.
Hàm `validate_extraction` không trích xuất text và không cấp trạng thái verified;
schema/kiểm tra byte không xác nhận nội dung hoặc hiệu lực pháp lý.

## Chuyển pending sang hồ sơ hợp lệ khi có bằng chứng

Quy trình này chưa được tự động hóa trong Stage 2:

1. Đối chiếu trang công bố và đúng byte/bản ban hành, đủ phần/phụ lục; lưu artifact
   bằng chứng có hash, locator, người rà soát và thời điểm rà soát thực tế.
2. Xác minh riêng source_url của document và download_url của file. Có URL ứng
   viên trong inventory không chứng minh file được tải từ đó.
3. Phục hồi retrieved_at lịch sử chỉ khi có log/hồ sơ đáng tin cậy. Nếu không có,
   giữ tệp legacy pending. Có thể thực hiện lần thu thập mới có ghi nhận thật,
   giữ raw cũ; không hồi điền ngày mới cho lần thu thập cũ. Cách biểu diễn lần
   thu thập lại byte trùng cần thiết kế riêng vì DDD có UNIQUE(law_id,sha256).
4. Tạo run mới, điền đủ trường DDD từ bằng chứng, chạy contract/FK validator và
   rà soát trước khi nạp legal_document/source_file chính thức. Không dùng chuỗi
   rỗng/"unknown"/ngày giả để vượt NOT NULL. Giữ provenance của quyết định chuyển.
5. Extraction review, legal units, hiệu lực/scope tại snapshot, chunk/context,
   corpus/index/release gates vẫn phải hoàn tất sau đó. Đủ hồ sơ nguồn chưa đủ
   để phát hành corpus; không đánh dấu các cổng chưa chạy là đạt.

Không có mâu thuẫn schema cần nới trong Stage 2: việc chưa đủ bằng chứng được
cách ly ở pending. Quy tắc cấp file UUID là quyết định triển khai bổ sung được
ghi công khai ở trên; không thay công thức UUID Qdrant hoặc hash unit/chunk của DDD.
