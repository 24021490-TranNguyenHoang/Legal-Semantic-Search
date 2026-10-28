# Chạy lại phiên1 — NĐ168 và đánh giá DOC QCVN

Ngày28/10/2026; đọc [contract](../design/Source_Revision_DOC_Assessment_v1.0.md)
và [kết quả/giới hạn](../reviews/Source_Revision_Session1_Verification.md).
Đứng tại root repo, Python3.11.9 trong `.venv-stage1` hiện có.

## Input thực tế cần giữ

- Raw NĐ168; config `config/nd168_docx_revision.v1.json` bind PDF/ảnh41/85/86 và
  graph cũ `stage4-docx-005`. File config có các đường dẫn tương đối thật.
- `staging/source-revision-session1-001/`: HTML/receipt/links Công báo mới,
  `doc-captures/` chứa5DOC và receipt thật; `antiword/` chứa tool/mapping/license
  metadata từ MSYS2; `antiword.receipt.json` giữ URL/SHA/thời điểm tải tool.
- `staging/qcvn-gazette-extraction-001/`: inventory/manifest của5PDF đã có.
  Các local_ref trỏ `staging/seven-source-completion-001/evidence/` và receipt24/10.
  Giữ các dependency này khi chuyển máy; Git không chứa artifact staging.
- Kiểm bảo toàn cần baseline trong coordinator001; replay artifact cần thêm
  nd168-docx-corrected-002 và qcvn-doc-assessment-003.

Chưa có URL chia sẻ archive phiên này. Không chỉ clone repo rồi giả định đã có
raw/evidence/tool. DOC lấy từ [trang Công báo chính thức](https://congbao.chinhphu.vn/van-ban/thong-tu-so-51-2024-tt-bgtvt-43387/53152.htm);
năm PDF đã có nên không tải lại. URL download đầy đủ và SHA nằm trong receipt,
không đoán URL theo tên file hoặc lấy ngày copy làm ngày tải.

## Chạy pipeline hiện có qua adapter hẹp

Thay NEW bằng tên chưa tồn tại; không chạy lại vào run đã có.

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.source_revision --config config/nd168_docx_revision.v1.json --run-dir staging/nd168-docx-corrected-NEW

.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.qcvn_doc_assessment --capture-dir staging/source-revision-session1-001/doc-captures --pdf-source-run staging/qcvn-gazette-extraction-001 --antiword staging/source-revision-session1-001/antiword/mingw64/bin/antiword.exe --mapping-dir staging/source-revision-session1-001/antiword/mingw64/share/antiword --run-dir staging/qcvn-doc-assessment-NEW

.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.qcvn_doc_assessment validate --run-dir staging/qcvn-doc-assessment-NEW

.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.legal_parser validate --manifest staging/nd168-docx-corrected-NEW/graph/manifest.json
```

Adapter NĐ168 gọi registration→extraction→legal_parser hiện có, không có builder
mới. CLI DOC gọi Antiword `-m UTF-8.txt -w 0` và `-m UTF-8.txt -x db` trên toàn
từng file, giữ stderr/exit/config trong report. ANTIWORDHOME do module đặt theo
mapping-dir; thiếu executable hoặc UTF-8 mapping bị từ chối trước output.

Tool bổ sung không cài toàn hệ thống: gói
`https://repo.msys2.org/mingw/mingw64/mingw-w64-x86_64-antiword-0.37-3-any.pkg.tar.zst`
148.613byte, receipt thật trong coordinator001. Không phải model hoặc service.
`olefile==0.47`, `zstandard==0.25.0` đã cài bằng pip `--target` vào
`staging/source-revision-session1-001/tool-python` để khảo sát OLE/giải nén tool.
Hai thư viện đó **không bắt buộc** cho CLI DOC/validator ở trên; Antiword executable
và mapping thì bắt buộc. Thư viện dự án dùng môi trường ingestion hiện có
(lxml, jsonschema, PDF/DOCX readers); không import encoder hoặc tải weights.

## Kiểm thử và kiểm chứng artifact

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_stage2 tests.test_stage3 tests.test_stage4 tests.test_source_revision tests.test_qcvn_doc_assessment -v

.\.venv-stage1\Scripts\python.exe -X utf8 -B -m tests.check_source_revision_artifacts --nd168-run staging/nd168-docx-corrected-002 --doc-run staging/qcvn-doc-assessment-003 --baseline staging/source-revision-session1-001/preservation.baseline.json --replay-nd168 staging/nd168-docx-corrected-003 --replay-doc staging/qcvn-doc-assessment-004 --run-dir staging/source-revision-checks-NEW

git diff --check
```

Muốn kiểm replay mới, truyền các run vừa tạo vào hai tham số --replay tương ứng.
File/cây/spans/text diagnostic phải giữ hash; manifest có created_at mới nên
không đòi manifest byte-identical. Baseline kiểm2.226file ở workspace này; chỉ
STATUS và ingestion guide được thay trong các file baseline. Không stage/commit.

## Giới hạn môi trường

Antiword đọc DOC nhị phân, không render được bố cục Word hoặc phục hồi đầy đủ
hình/bảng. Word/LibreOffice thực thi không có; registry Word.Application cũ còn
nhưng không có LocalServer32, không coi đó là Word hoạt động. Không render DOCX
hiệu chỉnh, không convert DOC→DOCX. Chỉ chạy trên Windows/Python này; chưa máy/OS
khác, chưa clean install toàn bộ dependency. Không dùng kết quả kỹ thuật thay
quyết định pháp lý hoặc full visual review.
