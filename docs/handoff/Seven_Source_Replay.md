# Chạy lại đợt hoàn thiện bảy nguồn

Trạng thái 2026-10-25: candidate kỹ thuật đã kiểm chứng; **chưa hoàn tất nội dung
toàn bảy nguồn**. Snapshot 2025-01-01. Không chuyển bản cho nhóm hoặc tạo index.
Xem [báo cáo](../reviews/Seven_Source_Completion_Verification.md),
[contract](../design/Seven_Source_Completion_v1.0.md) và [STATUS](../progress/STATUS.md).

## Đọc candidate, không cần repository hoặc thư viện ML

Bản hiện hành: `staging/dataset-v4-candidate-006/`, version
`vtls-seven-source-experimental.v4-candidate.5`, adapter `seven-source-candidate.v1.3`.
Copy **cả thư mục**, gồm `components/v3`, `objects`, `additions` và manifest.
Component v3 là nguồn/proof lưu trữ; chỉ `memberships.jsonl` là danh sách target.
Không lấy cả 3.115 payload lưu trữ làm membership của candidate.

Từ thư mục bản sao, dùng Python 3.11+ và standard library:

```powershell
python -X utf8 -B validate_read.py validate --root .
python -X utf8 -B validate_read.py read --root . --record-id c_ce3b071b3f447c01b7e7b5af133a5af6c3e2d342c00fc6a396c4ed88a59cdd57
```

Lệnh đọc trên là Điều34K2a TT35. Kết quả có nguyên văn, context Điều/Khoản,
các subtree hồ sơ/sát hạch, mẫu XXVI, nguồn và căn cứ chuyển tiếp để đọc.
`text_refs_root`, `component_root` và `proof_mounts` xác định root của từng ref;
không fallback sang đường dẫn staging nguyên thủy.

Candidate có 131 text chunk, 9 table record, 4 whole-source record và 2 form.
Form hỗ trợ đọc layout/fields; **chưa có projection encoder/search cho form**.
Whole-source record giữ toàn bộ nội dung; encoder views không phải target độc lập.
Consumer cũ không được nhận rằng nó hỗ trợ các capability mới chỉ để chạy qua gate.

Chưa có URL chia sẻ bundle/ZIP mới. Hai lần copy độc lập đã chạy trên cùng
Windows/Python, có audit gate chặn đọc workspace ngoài bundle; chưa thử máy/OS khác.

## Môi trường rebuild

Đứng ở root repository. Môi trường đang dùng là `.venv-stage1` (Python 3.11.9).
Máy mới có thể tạo venv rồi cài `requirements-ingestion.txt`; lượt này chỉ kiểm
dry-run offline trong venv hiện hữu, không tuyên bố đã cài sạch lại.

```powershell
py -3.11 -m venv .venv-ingestion
.\.venv-ingestion\Scripts\python.exe -m pip install -r requirements-ingestion.txt
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.full_ingestion --help
```

Rebuild cần tokenizer assets và PyVi đã bind trong `tt35-preview-005`; không
tải/chạy encoder hoặc weights. Đọc/validate candidate không cần các dependency này.
Không dùng constraints prototype cũ thay pins encoder hiện hành.
`.gitattributes` giữ LF riêng cho các module mới có byte hash, để checkout không
tự đổi code checksum. Không chạy renormalize mã/artifact lịch sử.

Các upstream được chọn tường minh trong `config/seven_source_completion.v1.json`
và manifest đầu ra. Giữ các run: seven-sources-export-006, stage4-docx-005,
stage6-coverage-001, circular-priority-006, tt35-preview-005, tt38-preview-003,
tt38-tables-003, dataset-v3-draft-005, blocked-source-repair-003,
nd168-a16k2-preview-004 và composition-relevance-review-001. Đây là dependency
**build**; chúng đã được đóng gói/mount cho đường **read** độc lập.

Giữ thêm năm PDF/receipt Công báo TT51 trong
`staging/seven-source-completion-001/evidence/`. Source set Công báo 425 trang
khác bản 403 trang; không cộng nối hai edition hoặc sao offsets giữa chúng.
URL/hash/thời điểm capture thật có trong receipt và inventory. Copy không tạo
retrieved_at mới; nếu tải lại phải tạo receipt của sự kiện tải mới. Không dọn
staging này khi chưa lưu archive nguồn. Không có URL tải archive dự án được công bố.

## Lệnh đã dùng, đổi NEW thành run chưa tồn tại

Các lệnh dưới đọc upstream đã seal; không chọn run theo thời gian sửa file.

```powershell
# Reader/layout theo trang; mặc định là 5 PDF Công báo TT51 đã capture.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.full_ingestion source-scan --run-dir staging/qcvn-gazette-extraction-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.full_ingestion source-scan --law-id "35/2024/TT-BGTVT" --run-dir staging/tt35-full-layout-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.full_ingestion source-scan --law-id "38/2024/TT-BGTVT" --run-dir staging/tt38-full-layout-NEW

# Bản PDF đối chiếu đã có; không tải lại, không ghi đè raw.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.full_ingestion source-scan --comparison-inventory staging/seven-source-ledger-009/inventory.jsonl --law-id "168/2024/NĐ-CP" --run-dir staging/nd168-comparison-extraction-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.full_ingestion source-scan --comparison-inventory staging/seven-source-ledger-009/inventory.jsonl --law-id "35/2024/QH15" --run-dir staging/law35-comparison-extraction-NEW

# Graph HTML, regions, preview hữu hạn từ các upstream đã chọn.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.full_ingestion nd168-html --run-dir staging/nd168-html-full-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.full_ingestion regions --source-run staging/tt35-full-layout-001 --run-dir staging/tt35-source-regions-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.full_ingestion regions --source-run staging/qcvn-gazette-extraction-001 --run-dir staging/qcvn-source-regions-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.full_ingestion previews --run-dir staging/seven-source-previews-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.full_ingestion complete-records --run-dir staging/seven-source-complete-records-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.full_ingestion source-repairs --run-dir staging/seven-source-repairs-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.full_ingestion qcvn-graph --source-run staging/qcvn-gazette-extraction-001 --regions-run staging/qcvn-source-regions-001 --previous-graph-manifest staging/qcvn-rule-graph-002/manifest.json --parser-revision qcvn-reader-boundaries.v1.2 --run-dir staging/qcvn-rule-graph-NEW

# Packaging/ledger dùng đúng graph được bind; giữ profile mới riêng.
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.full_ingestion dataset --qcvn-graph-manifest staging/qcvn-rule-graph-003/manifest.json --run-dir staging/dataset-v4-candidate-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.full_ingestion ledger --candidate-manifest staging/dataset-v4-candidate-006/dataset_manifest.json --qcvn-graph-manifest staging/qcvn-rule-graph-003/manifest.json --run-dir staging/seven-source-ledger-NEW
```

Đây là replay từng bước với input đã chọn, không phải tự nối tất cả thư mục NEW
vào downstream. Muốn thay input phải truyền manifest/config tương ứng và kiểm
binding; một số bước preview vẫn dùng upstream cố định được ghi trong contract.
Manifest run mới có thời điểm kỹ thuật mới; content/IDs được đối chiếu, không hứa
manifest byte-identical do created_at/tool revision. Policy cũ vẫn đọc bằng
bundle/runtime cũ; riêng graph002 có replay `--parser-revision qcvn-reader-boundaries.v1.1`
để đối chiếu, kèm giới hạn ownership annex, không dùng làm trạng thái hiện hành.

## OCR local, checkpoint và resume

Tesseract portable `5.5.3.20260724`, vie tessdata_fast 531.275 byte. URL/hash/version
thực trong `staging/ocr-environment-001/downloads/receipts.json`; Apache-2.0 cho
Tesseract/tessdata, các dependency/7-Zip có license kèm. Không chạy installer hoặc
dịch vụ trả phí. Lệnh đã dùng để unpack hai lớp:

```powershell
& staging/ocr-environment-001/downloads/7zr.exe x staging/ocr-environment-001/downloads/7z2301-x64.exe -ostaging/ocr-environment-001/7zip -y
& staging/ocr-environment-001/7zip/7z.exe x staging/ocr-environment-001/downloads/tesseract-5.5.3.exe -ostaging/ocr-environment-001/tesseract -y
# Sau unpack, copy vie.traineddata đã kiểm SHA vào tessdata của môi trường mới.
& staging/ocr-environment-001/tesseract/tesseract.exe --version
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.full_ingestion ocr --extraction-manifest staging/qcvn-gazette-extraction-001/manifest.json --run-dir staging/qcvn-ocr-drafts-NEW --executable staging/ocr-environment-001/tesseract/tesseract.exe --tessdata staging/ocr-environment-001/tesseract/tessdata
```

Chỉ chọn trang image-dependent có reader text <500 ký tự và có image object;
không OCR mù toàn 403/425 trang. Scale3, vie, OEM1, PSM3, một CPU thread.
Mỗi trang có reader riêng, PNG, txt/TSV gốc, normalized OCR, bbox/confidence/offsets.
OCR chất lượng số/ký hiệu **chưa đạt gate target**; 203 draft không vào candidate.

Chỉ với run **chưa seal** bị gián đoạn: chạy lại cùng lệnh/tham số và thêm
`--resume`. Kiểm input bytes/config/tool/hash trước khi dùng checkpoint. Reader
resume được cả sau khi serialization viết một phần; phần có sẵn được so với
replay, không ghi đè. Khác hash/code/config thì dừng và giữ hiện trạng để điều tra.
Run đã seal hoặc output ngoài staging bị từ chối. Không dùng resume để sửa raw,
xóa warning, đổi edition hoặc đánh dấu verified.

## Kiểm chứng

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_full_ingestion -v
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m tests.check_seven_source_artifacts --dataset-manifest staging/dataset-v4-candidate-006/dataset_manifest.json --run-dir staging/seven-source-artifact-checks-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m tests.check_seven_source_negative --dataset-root staging/dataset-v4-candidate-006 --run-dir staging/seven-source-negative-checks-NEW
```

Negative checks chỉ sửa bản sao fixture, reseal checksum ngoài rồi kiểm lỗi logic;
không thay corpus thật. Bộ đọc portable dùng `-X utf8` trên Windows để tránh lỗi
stdout cp1258. Lỗi module helper Stage6 khi chạy `unittest tests.test_stage6` được
khắc phục bằng `unittest discover -s tests -p test_stage6.py`; không sửa test cũ.

Phần chưa hoàn thành và checkpoint để tiếp tục nằm ở đầu STATUS và trong
`staging/seven-source-completion-001/checkpoint.json`. Scope/applicability pending
không phải yêu cầu người dùng duyệt trước khi agent tiếp tục preview kỹ thuật.
