# Kiểm tra và đăng ký PDF Thông tư 35, 38, 51/2024/TT-BGTVT

Commit đầu lượt `2aebab4e4cbc10c4b550a1571855c0fe3bd9d278`. Git chỉ có
năm PDF mới untracked do người dùng thêm; không thay đổi/xóa chúng hoặc
`data/raw/MANIFEST.csv`. Đã đọc AGENTS, Source Inventory, contract và code
Stage2 cùng schema đăng ký. Tái sử dụng `src.source_registry`, không sửa
schema/validator/parser hoặc tạo framework nguồn mới. Snapshot 2025-01-01.

## Kết quả theo file

| File | Trang | Byte | Đối chiếu / lưu ý |
|---|---:|---:|---|
| `35-bgtvt.pdf` | 69 | 1.443.001 | Số35, ngày15/11/2024, tên văn bản trên ảnh trang1 khớp metadata chính thức |
| `35-bgtvt-kem.pdf` | 179 | 5.936.066 | Ảnh trang1 ghi rõ phụ lục ban hành kèm TT35 ngày15/11/2024 |
| `38-bgtvt.pdf` | 7 | 676.782 | Trống số/ngày ngay trên ảnh trang1; **byte-identical với attachment Chính phủ hiện tại**, không tự điền |
| `51-bgtvt.pdf` | 1 | 566.925 | Số51, ngày15/11/2024; Điều1 ban hành QCVN41:2024/BGTVT |
| `51-bgtvt-kem.pdf` | 403 | 25.535.085 | Bìa QCVN41:2024 khớp Điều1 TT51; lời nói đầu trang2 trống số thông tư |
| `official/tt38-congbao-valid.pdf` trong run kiểm tra | 8 | 463.837 | **Bổ sung riêng** Công báo1355+1356 ngày18/12/2024, trang in21–28; ảnh trang1 có số38 và ngày15/11/2024 |

Trang chính thức đã capture HTML và thời điểm truy cập thực, không chỉ ghi
URL từ kết quả tìm kiếm:

- [TT35 — docid211984](https://vanban.chinhphu.vn/?pageid=27160&docid=211984):
  hai attachments đúng tên35-bgtvt.pdf/35-bgtvt-kem.pdf.
- [TT38 — docid211873](https://vanban.chinhphu.vn/?pageid=27160&docid=211873):
  một attachment38-bgtvt.pdf.
- [TT51 — docid211908](https://vanban.chinhphu.vn/?pageid=27160&docid=211908):
  hai attachments51-bgtvt.pdf/51-bgtvt-kem.pdf.
- [Công báo TT38](https://congbao.chinhphu.vn/van-ban/thong-tu-so-38-2024-tt-bgtvt-43378/53130.htm):
  PDF lấy từ đúng liên kết CDN trên trang, không đoán tên file.

Cả5 tên và kích thước local khớp attachment listing/HTTP HEAD. Không tải lại
bốn PDF35/51 chỉ để tạo bản sao: đối chiếu số/tên/ngày, quan hệ phụ lục và
ảnh nhận diện; **chưa chứng minh byte-identical toàn file với remote**.
Không dùng Content-Length làm checksum. SHA-256 từng file và file_id đầy đủ
trong `source_metadata.csv`/`source_files.observed.jsonl`.

Riêng38 thiếu số/ngày nên đã GET attachment để xác định bản: SHA
`b0addaf053bd302cf17b9c07ebf5403e29a10f6164ab9112ef0e7c85190c37dc`,
trùng hoàn toàn local; không lưu thêm một PDF trùng. Vì publisher attachment
cũng thiếu nhận diện trên trang, thu thập thêm Công báo có số/ngày đầy đủ,
SHA `e27582e2bce4aee27ebc85ffc43731790f887782375ab76e52e2f61981603689`,
file_id `1e28277a-66b1-58c1-900b-360bc4c5ffd5`. Đề nghị ưu tiên bản Công báo
cho extraction sau; đây chưa phải quyết định xác minh toàn nội dung/hiệu lực.

Capture PDF Công báo thực **2026-10-22T10:43:08.5203746Z**; HTML Chính phủ
capture khoảng10:40:31–32 UTC cùng ngày, từng timestamp/hash/header lưu trong
run. Không lấy những ngày này làm retrieved_at lịch sử của năm file local.

## Khả năng đọc và giới hạn

Đã mở và kiểm toàn bộ659 trang local bằng PDFium; thêm8 trang Công báo bằng
pdfplumber. Không gặp lỗi mở PDF. Đây là kiểm cấu trúc/khả năng lấy text,
không phải đọc xác minh từng trang hoặc chứng minh không thiếu nội dung.

Ảnh thực đã xem: trang1 của cả5 PDF, trang2 QCVN, trang214 QCVN và trang1
Công báo mới. Các ảnh khác đầu/cuối đã render để mở lại nhưng không ghi là
đã được rà soát chỉ vì render thành công.

QCVN: PDFium lấy text rỗng ở100/403 trang; ảnh trang214 vẫn có biển báo,
nhãn chữ, số đo và bảng. Không coi chúng là trang trắng hoặc tự bỏ trang.
pdfplumber trích trang1–2 có nhiều NUL; PDFium có hành vi khác. Đây là vấn
đề của đầu ra reader cần khảo sát ở extraction, chưa kết luận file hỏng hay
lỗi encoding duy nhất. Danh sách trang cụ thể trong `pdf_inspection.json`,
text mẫu nguyên trạng trong `pdfplumber_samples.jsonl`; chưa OCR/nhận dạng
biển báo hoặc thay normalization. Không khẳng định QCVN đã sẵn sàng chunk.

Đã có đủ5 attachments theo listing của ba trang; chưa rà mọi phụ lục/bảng/
hình, lịch sử sửa đổi và hiệu lực từng đơn vị tại snapshot. Cả ba trang ghi
ngày hiệu lực chung01/01/2025, lưu là observed/candidate; không suy mọi đơn
vị active hoặc scope included. Không thêm yêu cầu xác minh chữ ký số.

## Metadata đã đăng ký

`config/source_registration.circulars.v1.json` dùng đúng Source Inventory:
SRC-005=TT38, SRC-006=TT51, SRC-007=TT35; không lẫn TT35 với Luật35/QH15.
Namespace UUIDv5/source-file.v1 giữ nguyên. Ba nhóm local: main part1, annex
part2 nếu có. Công báo38 là alternate trong source_set riêng, không giả làm
phần tiếp nối7 trang của PDF local.

- `staging/circulars-registration-001/`:3 pending documents/6 pending files,
  JSONL, pending.sqlite, content.sqlite rỗng, schema snapshot, manifest/hash.
- `staging/circulars-source-check-001/`: metadata đo được và observed riêng,
  URLs/captures/HEAD/hash, source relationships, CSV, ảnh/trang text bằng
  chứng, warning kỹ thuật, validation report và manifest đã seal.
- `staging/circulars-verification-001/`: logs validator/tests/preservation.

Stage2 profile hiện hành cố ý không tiếp nhận/phê duyệt evidence mới và
giữ evidence=null, tạo48 placeholder issues. **Không có nghĩa48 dữ kiện đều
chưa tìm thấy**: issued date/source URL/capture facts đã có trong sidecar
observed, nhưng chưa được promote bằng review/adapter chính thức. Giữ các
cổng/schema nguyên trạng; không âm thầm đổi pending thành verified để pass.

Năm file local có `historical_retrieved_at=null` do chưa có log tải; metadata
filesystem không được dùng thay. Công báo mới có new_capture_retrieved_at
thật riêng. Lần GET hiện tại trùng byte TT38 là sự kiện đối chiếu mới,
không chứng minh thời điểm hay đường tải ban đầu của file người dùng thêm.
Origin=agent_review; không human reviewer event/approved, corpus hay units.

## Lệnh và kiểm chứng

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_registry register --config config/source_registration.circulars.v1.json --run-dir staging/circulars-registration-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_registry validate --manifest staging/circulars-registration-001/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_registry validate --manifest staging/circulars-registration-001/manifest.json --require-release-ready
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_stage2
```

Thay NEW bằng run chưa tồn tại. Config tham chiếu5 raw và PDF Công báo trong
run kiểm tra, nên giữ các file đó để register lại. Không chạy script capture/
finalize trực tiếp lên run đã seal; chúng là script thực thi một lần, chưa
phải CLI pipeline mới. Không tự tải lại khi chỉ validate/register metadata.

Register và validate exit0: ID/hash/quan hệ/part order/JSONL/SQLite FK/
integrity/schema/manifest đạt. Require-release-ready **exit1 như mong đợi**.
18 tests Stage2 đạt. Kiểm manifest bằng chứng đạt;10 file raw (gồm manifest
và DOCX cũ) giữ nguyên hash. Inventory dataset/index v1 và draft3082 giữ
nguyên; ZIP bàn giao vẫn SHA
`8678cd66620cbacfae7443e9e0774ac36f8294aeb6edceebf1e06cfaa789d03e`.
Không sửa app/evaluation, chạy encoder, chunking hoặc build index.

Lỗi capture đã xử lý và lưu giới hạn: sandbox socket bị chặn; retry được
cấp quyền thành công. Endpoint download Công báo cũ trả HTML, không đăng
ký thành PDF; PDF thật lấy từ liên kết CDN. Python thiếu issuer certificate
cho CDN; dùng kho chứng chỉ Windows tải thành công, **không tắt TLS**.
Các phản hồi lỗi được giữ riêng, không dùng làm bằng chứng PDF hợp lệ.

Thay đổi Git mới chỉ config đăng ký, báo cáo này và STATUS; năm raw vẫn
untracked như đầu lượt. Không stage/commit/push. Chưa nhập nguồn mới vào
dataset/corpus; bước kế tiếp cần xử lý extraction có bảng/hình và review
phạm vi/hiệu lực theo đơn vị, tách khỏi đăng ký nguồn lần này.
