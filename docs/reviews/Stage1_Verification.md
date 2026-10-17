# Đợt 1 — Đường chạy và môi trường

Ngày kiểm tra: 2026-10-16. Môi trường: Windows x64, CPython 3.11.9,
venv sạch `.venv-stage1`. Đây là báo cáo kiểm tra kỹ thuật, không xác minh pháp lý.

## Đầu vào và giới hạn

Đã đọc lại các phần liên quan trong BRD/SRS, SDD/DDD, Source Inventory,
`Code_Review_Legal_Semantic_Search_v1.0.md` và bộ mẫu ZIP tại
`docs/design/data_model_v1/`. Các thành phần mẫu đã được đọc trong bộ nhớ;
chưa chạy validator thiết kế hoặc nhập fixture vào corpus.

Snapshot được người dùng xác nhận là 2025-01-01; SRS/SDD còn để mục này mở,
Source Inventory/DDD đã ghi mốc cụ thể. `docs/architecture.md` và `docs/scope.md`
còn mô tả/tiêu chí prototype. Chênh lệch được ghi rõ trong AGENTS và README.
Thiếu kế hoạch đánh giá chi tiết, PDF đề bài và bằng chứng hiệu lực/thu thập
nguồn trong repo; không tự tạo các tài liệu hay bằng chứng thay thế.

Trước sửa, Git chỉ có ZIP mẫu chưa được theo dõi. Không reset, clean, stage
hoặc commit; giữ nguyên ZIP. Các thay đổi prototype từ phiên trước đã nằm trong
HEAD và được bảo toàn về thuật toán; không thay parser/chunker hoặc model.

## Lệnh và kết quả đã chạy

Các lệnh chạy ở thư mục gốc; tiền tố Python thực tế là
`.\.venv-stage1\Scripts\python.exe`.

| Lệnh/nhóm kiểm tra | Kết quả |
| --- | --- |
| `python -m venv .venv-stage1` | Tạo môi trường mới, không sửa venv cũ. |
| `python -m pip install -r requirements.txt` | Lần trong sandbox lỗi mạng; lần được cấp quyền mạng cài thành công. |
| `python -m pip check` | Đạt: No broken requirements found. |
| `python -m pip install -r requirements.txt -c requirements-win-py311.lock.txt --no-index` | Đạt trên môi trường vừa cài; xác nhận constraints khớp bản đã cài, không phải lần cài fresh thứ hai. |
| Smoke import từng dependency ở tiến trình riêng | 12/14 thành công; `torch` và `sentence_transformers` lỗi DLL do Windows Application Control, WinError 4551. |
| Thử import `torch`, `transformers`, `sentence_transformers` ngoài sandbox | Dừng tại torch với cùng lỗi chính sách DLL; không thay đổi chính sách Windows. |
| `python -X utf8 -B -m unittest discover -s tests -v` | 13 test đạt ở lần chạy cuối; không model, không Qdrant build. |
| `python -X utf8 -B -m src.ingestion.cleaner --input-dir data/raw --run-dir staging/stage1-clean-smoke` | 4 DOCX thành công, ghi cleaned/report vào staging. |
| `python -X utf8 -B -m src.ingestion.chunker --input-dir staging/stage1-clean-smoke/cleaned --run-dir staging/stage1-chunk-smoke` | 1.457 chunk, khớp corpus cũ theo ID và nội dung JSON. |
| `python -X utf8 -B -m src.ingestion.embedder --input data/processed/corpus_chunks.jsonl --run-dir staging/check-embed --check-only` | Đạt: 1.457 bản ghi; không tạo run/output/model. |
| `python -X utf8 -B -m src.database.bm25_store --input data/processed/corpus_chunks.jsonl --run-dir staging/check-bm25 --check-only` | Đạt: 1.457 bản ghi; không build corpus index. |
| `python -X utf8 -B -m src.database.qdrant_setup --input data/processed/corpus_embedded.jsonl --run-dir staging/check-qdrant --check-only` | Đạt: 1.457 bản ghi, vector hợp kiểm tra kỹ thuật; không mở database. |
| `git diff --check` | Đạt sau sửa whitespace; Git còn thông báo LF/CRLF theo cấu hình máy. |

12 dependency import thành công: docx, pdfplumber, numpy, transformers,
rank_bm25, qdrant_client, streamlit, jsonschema, fastapi, uvicorn, pydantic, dotenv.
Import transformers thành công không chứng minh AutoModel hoạt động khi torch bị chặn.

13 test bao gồm: import toàn bộ 11 module dự án với audit hook chặn ghi/xóa,
kết nối mạng và dependency nặng; help/thiếu tham số; input thiếu/rỗng/lỗi;
JSON sai/ID trùng/vector sai; run ngoài staging hoặc đã tồn tại; check-only không
khởi tạo engine; parser tạo staging khớp corpus; AST thuật toán cleaning/parser
không đổi so với HEAD (chỉ chuyển import reader vào hàm); cleaner đọc fixture
DOCX và từ chối batch hỏng; BM25 fixture thành công; BM25 lỗi giả lập có failed
report và mã thoát khác 0; CLI search kiểm tra input trước model.

Test symlink nằm trong ca bảo vệ đường dẫn: chạy nhánh symlink nếu Windows cho
phép tạo link; các phép thử đường dẫn ngoài staging và tái dùng run luôn chạy.

## Bảo toàn dữ liệu

Đã chụp SHA-256 trước sửa và đối chiếu sau smoke tests: **14/14 tệp không đổi**,
gồm 4 raw DOCX, manifest, 4 cleaned TXT cũ, 2 JSONL cũ và 3 tệp Qdrant cũ.
Test suite cũng so hash trước/sau từng lần chạy toàn suite.

Bốn TXT staging khớp nội dung TXT cũ khi đọc text; byte khác do ghi LF thay vì
CRLF. Đây không phải thay thuật toán cleaning. Không ghi lại TXT cũ.
Không dùng số lượng 1.457 làm tiêu chí corpus pháp lý tương lai.

## Chưa kiểm tra

- Không tải model weights, tạo embedding, build Qdrant hoặc chạy retrieval/UI
  end-to-end: ngoài phạm vi đợt này; thêm giới hạn DLL PyTorch trên máy hiện tại.
- Chưa kiểm tra pipeline PDF thật, OCR hoặc bảng: reader giữ hành vi prototype;
  đợt extraction tiếp theo sẽ xử lý mất bảng/locator.
- Chưa kiểm tra đầy đủ schema DDD, hiệu lực/scope, corpus/index consistency,
  activation/rollback, bốn mode và metrics: thuộc các đợt sau.
- Chưa xác nhận môi trường Python/OS/GPU khác hoặc model revision. Lock này chỉ
  ghi phiên bản package cài trên Windows/Python 3.11; không phải model release.

Đợt 1 dừng để người dùng xem diff. Tài liệu README có lệnh cài đặt, preflight,
staging và tự chạy lại test; không chuyển tiếp sang đợt 2.
