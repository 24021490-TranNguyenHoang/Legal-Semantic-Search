# BM25 composition experimental — chạy độc lập

Snapshot2025-01-01. Bản nhóm đang dùng vẫn BM25/dataset v1. Bản mới ở
`staging/bm25-composition-001/`, index `vtls-bm25s-composition.v1`, gắn
dataset `vtls-coverage-experimental.v3-draft.1`. Chưa có URL chia sẻ; nhận
nguyên folder artifact, không chỉ engine. **Không dùng index v1 cho dataset v3.**

## Từ clone tới build

Clone repository bằng URL thực của nhóm, cd tới gốc repo. Build cần đúng
dataset-v3-draft-005 và các module/config trong commit làm việc này. Cài sparse
runtime Python3.11 (đã thử3.11.9 Windows), không cần PyTorch/model/PyVi:

```powershell
python -m venv .venv-bm25-composition
.\.venv-bm25-composition\Scripts\python.exe -m pip install -r requirements-bm25.txt
.\.venv-bm25-composition\Scripts\python.exe -X utf8 -B -m src.composition_bm25 build --dataset-manifest staging/dataset-v3-draft-005/dataset_manifest.json --run-dir staging/bm25-composition-NEW
```

NEW phải chưa tồn tại; không overwrite các index cũ. Build validate dataset,
projection đúng retrieval membership, save/load và rebuild kiểm sparse arrays.
Giữ raw/source/cells/IDs/search text, không thêm supporting thành document.

## Validate/search/read folder artifact độc lập

Copy nguyên folder index thành `bundle` trong một thư mục riêng rồi cd vào
`bundle`. Folder đã có src/, config/, requirements-bm25.txt, dataset/, engine/.
Tạo venv ở **thư mục cha** hoặc vị trí khác, tránh thêm file vào inventory index:

```powershell
python -m venv ../venv
../venv/Scripts/python.exe -m pip install -r requirements-bm25.txt
Get-FileHash index_manifest.json -Algorithm SHA256
../venv/Scripts/python.exe -X utf8 -B -m src.composition_bm25 validate --index-manifest index_manifest.json
../venv/Scripts/python.exe -X utf8 -B -m src.composition_bm25 search --index-manifest index_manifest.json --query "Ở tốc độ đúng 60 km/h cần cách xe trước ít nhất bao nhiêu mét?" --top-k 10
$sampleRecord = Get-Content dataset/table_records.jsonl -Encoding utf8 -TotalCount 1 | ConvertFrom-Json
../venv/Scripts/python.exe -X utf8 -B -m src.composition_bm25 read --index-manifest index_manifest.json --record-id $sampleRecord.retrieval_id
```

Manifest SHA-256 phải bằng:
`6d285b850a8839e69dc2ecdbfd82a6d884310fb112b968db922d9ebbec09993e`.
Version/hash dataset bind trong index manifest, không chọn bằng tên latest.
Consumer detail giữ nguyên text_original, đánh dấu derived_text nếu là bảng,
trả context/source spans/cells/rows/proof_base và toàn required-read units/spans.
Các source path resolve từ dataset root + membership.proof_base/mounts,
không từ thư mục chứa evaluation details hoặc repo cũ.

Validate/read **dataset riêng** chỉ cần stdlib:

```powershell
python -X utf8 -I -B dataset/validate_read.py validate --root dataset
python -X utf8 -I -B dataset/validate_read.py read --root dataset --record-id $sampleRecord.retrieval_id
```

Search/validate **index** cần bm25s0.3.13/numpy2.4.6/scipy1.17.1, không phải
stdlib-only. Runtime kiểm cùng CPython major/minor, Unicode và dependency/
engine-source hashes; Python patch khác có policy compatibility đã ghi.
`load_ms` gồm integrity/consumer validation, lexical mapping và load engine;
`search_ms` là query preprocessing/score/rank; batch còn tách `detail_ms`.
Đừng lấy tổng thời gian CLI search làm latency BM25 thuần.

## Development run và review

Từ gốc repo, dùng query freeze đã seal (30cũ+15mới+5giới hạn), không sửa query
sau khi xem ranking:

```powershell
.\.venv-bm25-composition\Scripts\python.exe -X utf8 -B -m src.composition_evaluation --index-manifest staging/bm25-composition-001/index_manifest.json --queries-manifest staging/composition-queries-001/manifest.json --old-index staging/bm25-baseline-v1-001/index_manifest.json --old-evaluation staging/bm25-evaluation-dev-001 --run-dir staging/bm25-composition-evaluation-NEW
.\.venv-bm25-composition\Scripts\python.exe -X utf8 -B -m unittest tests.test_composition_bm25 tests.test_evaluation
```

Batch load mỗi index một lần. Mở `annotation_sheet.md`, `run.jsonl`,
`details/<record_id>.json`, `annotations.jsonl`, `ranking_comparison.jsonl`,
`coverage_limits.jsonl`. Label/reviewer/time/reason để null khi chưa có review.
Phân biệt direct_target và dependency_only; unit trong dependency không có
rank riêng. Chưa có scoring submission CLI v3/accepted labels; metrics=null.
Không đổi record_id thành chunk_id để mang qrels v1 sang, không coi unjudged=0.

## Lỗi và giới hạn thực tế

- Sai hash/thiếu source/mount/dependency: phục hồi đúng bundle, không bỏ validator.
- Engine/dependency khác pin: cài requirements-bm25; không tự thay ranking/tokenizer.
- Thiếu capability/record type lạ: consumer phải fail; loader v1 không nhận composition.
- Windows stdout charmap: dùng `-X utf8`; giữ `-B` để tránh sinh cache trong artifact.
- Không đặt venv, log hoặc output mới trong folder index đã seal.
- QCVN/biểu mẫu withheld chưa phải retrieval target; Top10 có reference không
  chứng minh đã có toàn nội dung, Top10 thiếu cũng không tự chứng minh corpus gap.

Đã thử folder độc lập và venv mới cài ba packages từ wheels cache offline,
audit hook chặn đọc ngầm workspace bên ngoài. Cùng máy Windows, chưa thử OS/
máy khác. Bằng chứng trong staging/composition-bm25-audit-001/portability.json.
Không thêm API/UI hoặc sinh câu trả lời. Scope/source/applicability vẫn pending.
