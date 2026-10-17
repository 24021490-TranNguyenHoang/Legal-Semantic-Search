# Stage 2 — Bằng chứng kiểm tra hồ sơ nguồn và contract nền

Ngày ghi báo cáo: 2026-10-16. Snapshot sản phẩm: 2025-01-01.
Môi trường dùng lại: Windows x64, CPython 3.11.9, `.venv-stage1`.
Inference vẫn được ghi nhận bị Windows Application Control chặn (WinError 4551).
Stage này không tải/chạy model hoặc thử sửa chính sách Windows.

## Phạm vi và Git

Đã đọc AGENTS, DDD, các phần source/extraction của data_dictionary, README/SQL/
validator và cấu trúc fixture trong ZIP mẫu. Không chạy báo cáo fixture có sẵn
như bằng chứng kiểm định corpus thật. Source Inventory dùng làm khai báo ứng viên.

Toàn bộ thay đổi chưa commit của Stage 1 được giữ nguyên. Stage 2 chỉ bổ sung
source registry/contracts/tests/tài liệu và cập nhật AGENTS/README. Không sửa
cleaner, parser/chunker, embedder, retrieval hay các builder của Stage 1.
Không stage hoặc commit. SQLite và output mới vẫn dưới staging, bị Git ignore.

## File triển khai Stage 2

| File/nhóm | Vai trò |
| --- | --- |
| `config/source_registration.v1.json` | Khai báo bốn nguồn/tệp, source set/phần, expected SHA-256 đo từ raw và namespace file UUID cố định. |
| `schemas/data_model_v1/schema.sql`, `provenance.json` | Schema chính thức nguyên byte từ ZIP và thông tin hash đối chiếu. |
| `schemas/data_model_v1/{legal_document,source_file,extraction}.schema.json` | Contract DDD chính thức, không chấp nhận trường bắt buộc null chỉ để pass. |
| `schemas/data_model_v1/{registration,pending_document,pending_file}.schema.json`, `pending_schema.sql` | Contract/lưu trữ staging riêng, không thay schema chính thức. |
| `src/source_contracts.py` | Format/schema validator, UUID, path/hash và kết nối SQLite bật FK; validator cho extraction artifact đã có. |
| `src/source_registry.py` | CLI register/validate, kiểm tra manifest/DB/raw, tạo run pending và chặn release. |
| `tests/test_stage2.py` | 18 ca test mới; fixture synthetic riêng. |
| `docs/design/data_model_v1/Stage2_Source_Contract.md` | Phân tách measured/declared/evidence, chính sách cấp ID và quy trình chuyển pending khi có bằng chứng. |
| `AGENTS.md`, `README.md` | Cập nhật phạm vi được cho phép, hướng dẫn CLI/tái tạo và giới hạn. |

## Artifact thực tế

Hai run đã tạo:

- `staging/stage2-sources-001/`
- `staging/stage2-sources-002/`

Mỗi run có `content.sqlite` nguyên 12 bảng/view nhưng 0 bản ghi chính thức;
`pending.sqlite` có 4 document, 4 file và 44 quality issue; ba JSONL tương ứng;
schema/contract/config đã chụp, validation_report.json, manifest.json,
manifest.sha256 và run_report.json. Không có extraction, unit, chunk hoặc corpus
mới. `source_set_complete`, `retrieved_at` và các bằng chứng chưa có đều null.

| Tệp raw hiện có | file_id ổn định | Kích thước byte |
| --- | --- | ---: |
| 36.2024.QH15.docx | 963d53d4-d8a4-5074-aa49-2343f914fc80 | 92219 |
| 168.2024.NĐ-CP.docx | 06431cc5-ad00-5024-bbc2-5b2d45fb8336 | 100455 |
| 35.2024.QH15.docx | fdcffbfc-4a2c-5872-b652-97444919e740 | 160981 |
| 165.2024.NĐ-CP.docx | 6b9f0cd9-a8dc-50e1-ac01-025c74fb9d89 | 132788 |

SHA-256 đầy đủ, MIME và ref nằm trong files.pending.jsonl và config. Kiểm tra
gói DOCX không phải extraction nội dung hoặc chứng nhận bản ban hành chính thức.

## Lệnh đã chạy và kết quả

Tiền tố Python thực tế: `.\.venv-stage1\Scripts\python.exe -X utf8 -B`.

| Lệnh/kiểm tra | Kết quả |
| --- | --- |
| `-m src.source_registry register --run-dir staging/stage2-sources-001` | Exit 0; technical_valid=true; 4 pending file/44 issue; release_eligible=false. |
| `-m src.source_registry register --run-dir staging/stage2-sources-002` | Exit 0; tái tạo được cùng hồ sơ và định danh. |
| `-m src.source_registry validate --manifest staging/stage2-sources-001/manifest.json` | Exit 0; kiểm tra kỹ thuật không có lỗi. |
| Cùng lệnh validate, thêm `--require-release-ready` | Exit 1 như mong đợi; bị chặn bởi pending source evidence và các cổng release chưa chạy. |
| Read-only inspect cả hai manifest | Cả hai technical_valid=true, release_eligible=false. |
| So byte documents/files/issues JSONL giữa hai run | Cả ba giống nhau. |
| So byte content.sqlite/pending.sqlite giữa hai run | Cả hai giống nhau trên máy/phiên bản SQLite hiện tại; không cam kết byte SQLite giữa mọi phiên bản khác. |
| `-m unittest discover -s tests -v` | Lần chạy cuối 31/31 đạt: 13 hồi quy Stage 1 + 18 Stage 2. |
| `git diff --check` | Đạt; chỉ còn cảnh báo LF/CRLF từ cấu hình Git. |
| `git check-ignore` cho hai SQLite staging | Cả hai được ignore; không đưa DB vào commit mới. |

Test Stage 2 phát hiện raw thiếu/hash đổi, sai MIME, path traversal, ID trùng,
quan hệ sai, số nguyên bị thay boolean/float, thiếu bằng chứng chính thức,
extraction ref/hash/code point/encoding sai, SQLite vi phạm FK, schema bị sửa,
manifest/artifact/report bị thay, giả trạng thái verified/retrieved_at hoặc flag
release. Một số ca cố ý tính lại checksum để xác nhận validator còn đối chiếu
ngữ nghĩa, không chỉ tin hash/flag.

Test register chặn import torch/transformers/sentence_transformers/rank_bm25/
qdrant_client mà vẫn hoàn tất đăng ký synthetic. Test FK xác nhận NOT NULL và
quan hệ chính thức không bị nới; test schema đối chiếu byte với ZIP mẫu.

Hồi quy Stage 1 có ca BM25 trên fixture tạm nhỏ, tách khỏi corpus thật và được
dọn sau test; Stage 2 không gọi builder trên corpus hoặc tạo index phục vụ.
Không có embedding hay Qdrant build.

## Bảo toàn dữ liệu

Hash chụp trước Stage 2 được so sau toàn bộ test/smoke:

- **14/14** tệp trong raw/processed/Qdrant cũ không đổi (kể cả manifest cũ).
- **7/7** artifact staging có trước Stage 2 không đổi.
- Raw không bị di chuyển/ghi lại; ZIP mẫu không bị sửa/giải nén vào dữ liệu thật.

## Giới hạn và phần chưa đạt điều kiện phát hành

- Bốn tệp vẫn pending: chưa có log retrieved_at lịch sử, download URL gắn với
  đúng byte, bằng chứng bản ban hành/đủ phần, nguồn và quyết định xác minh.
- URL/ngày ban hành có trong inventory chỉ nằm ở declared/candidate. Thời gian
  built_at của run không được hồi điền thành retrieved_at.
- Schema nguồn/extraction và nền SQLite đã triển khai, nhưng chưa có công cụ
  tự phê duyệt evidence hoặc promote. Quy trình chuyển khi có bằng chứng nằm
  trong Stage2_Source_Contract.md; không tạo corpus giả để chứa quality issue.
- Chưa xác minh hiệu lực/scope, chạy extraction thật, OCR, parser mới, chunking,
  index, release/rollback hoặc retrieval. Các cổng đó thuộc các stage sau.
- Thiếu hồ sơ thu thập/đối chiếu thực tế không được thay bằng yêu cầu tự tạo.
  Chính sách UUID file là cụ thể hóa cách cấp UUID mà DDD cho phép; công thức và
  namespace được ghi công khai, không đổi định danh Qdrant/unit/chunk của DDD.

Stage 2 dừng để người dùng xem diff; chưa chuyển Stage 3.
