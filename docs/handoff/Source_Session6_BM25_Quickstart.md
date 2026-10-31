# BM25 subset v5 — chạy lại và tích hợp search → read

Snapshot **2025-01-01**, experimental/release=false; không là corpus verified
hoặc câu trả lời pháp lý. Dataset `vtls-subset-experimental.v5-candidate.1`,
index `vtls-bm25s-subset.v1`,138target (125chunk/9table/4whole).
Chưa có URL chia sẻ. Lấy ZIP và SHA từ báo cáo
[phiên6](../reviews/Source_Session6_BM25_Verification.md), không thay bằng ZIP v5
chỉ chứa dataset hoặc index composition cũ.

## Từ ZIP, không cần repository

Ví dụ PowerShell, đang ở thư mục chứa ZIP. Thay tên biến bằng đúng artifact giao;
thư mục giải nén/venv/output phải mới. Dùng SHA đã nhận qua kênh bàn giao để so
với sidecar, không chỉ tin hai file không rõ nguồn cùng tải được.

```powershell
$zip = 'vtls-bm25s-subset-v1-002.zip'
$expected = (Get-Content "$zip.sha256").Split(' ')[0]
if ((Get-FileHash $zip -Algorithm SHA256).Hash.ToLower() -ne $expected) { throw 'ZIP SHA mismatch' }
Expand-Archive -LiteralPath $zip -DestinationPath unpacked
py -3.11 -m venv .venv-bm25
.\.venv-bm25\Scripts\python.exe -m pip install -r unpacked/bm25/requirements-bm25.txt
.\.venv-bm25\Scripts\python.exe -I -B unpacked/bm25/search.py validate --index unpacked/bm25
.\.venv-bm25\Scripts\python.exe -I -B unpacked/bm25/search.py search --index unpacked/bm25 --query 'Trời mưa cần giữ khoảng cách an toàn thế nào?' --top-k 10
.\.venv-bm25\Scripts\python.exe -I -B unpacked/bm25/search.py search --index unpacked/bm25 --query 'tốc độ' --source-id SRC-005 --record-type table-retrieval.v1 --top-k 3
.\.venv-bm25\Scripts\python.exe -I -B unpacked/bm25/search.py read --index unpacked/bm25 --record-id c_f40b4dc8a194af86f8c532e89b170ee49c88d9024b32fd5576431c13776c1dec
.\.venv-bm25\Scripts\python.exe -I -B unpacked/bm25/search.py batch --index unpacked/bm25 --output batch-NEW
.\.venv-bm25\Scripts\python.exe -I -B unpacked/bm25/dataset/consumer.py full-read --dataset unpacked/bm25/dataset --output all-records-NEW.jsonl
```

Windows CPython3.11.9 đã được thử. Pin bắt buộc cho runtime search/index validate:
**bm25s0.3.13/numpy2.4.6/scipy1.17.1**; không cài requirements toàn repo,
PyTorch/model/PyVi. Offline: có đúng wheel tương ứng Python/OS thì thêm
`--no-index --find-links wheels` vào pip install. Không copy venv từ máy tạo.
Runtime chỉ cho cùng CPython minor/Unicode/engine source/pins, patch khác cảnh
báo. Chưa kiểm máy/OS khác. Dataset consumer đơn lẻ chỉ stdlib; BM25 cần ba libs.

`-I -B` tránh sys.path ngoài và bytecode; search.py thêm chính package root vào
sys.path. Không ghi output/cache vào bm25/ hoặc dataset/. Load kiểm checksum/
mapping/consumer full validate trước search; validate CLI còn rebuild matrix so
sánh trong RAM. Đây không là rebuild index trên disk. Thiếu input/hash sai trả
exit1; không fallback corpus mẫu. Lấy lại đúng ZIP/path, không sửa manifest để pass.

Query rỗng/chỉ punctuation/invalid top_k/filter trả lỗi. OOV/no lexical match
trả[]; không pad. Source/law/type filter là exact AND, trước Top-k, score vẫn theo
toàn corpus. SRC-004 hợp lệ nhưng không có target, trả[]. Không có legal threshold.

## Contract dùng cho Hùng/nhóm

Search hit giữ record_id/type/rank/score/source_id/law_id/citation và versions.
Lấy **record_id** gọi read trên cùng index; không join/dedup theo title, không đổi
type sang chunk. Read envelope có index binding và dataset_response nguyên trạng:
record, contexts, source_proofs, required_read.bindings/unit_reads/supporting_records,
membership/proposal/pending. Không chỉ hiển thị snippet/view rồi coi đã trả đủ luật.

Table: giữ source_original khác derived_text, cells/headers/conditions. Whole:
trả đủ record/search input cùng mọi encoder view; view không là target. FormXXVI
chỉ nằm trong supporting. Structural nodes không tự thành nội dung bắt buộc.
Proof dùng package_locator (dưới dataset/); original_locator là nhãn lịch sử,
không dùng để mở workspace cũ. Các object không có đuôi, không đổi tên bên trong gói.
Consumer không hỗ trợ capability thì phải báo lỗi, không âm thầm mất dependency.

Batch chứa raw_results/run/details.jsonl + details/*.json, signatures và pending
annotations.50query giữ nguyên30old/15new/5limit; metrics=null vì chưa có accepted
v5 labels. Không suy relevance từ score hoặc chuyển qrels cũ. Thời gian load
(integrity+consumer+engine) tách ranking và detail hydration, batch tuần tự không
warmup không là benchmark/p95/SLA.

## Build/replay tại repository

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_bm25 build --config config/source_session6.v1.json --run-dir staging/bm25-subset-v5-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_bm25 validate --index staging/bm25-subset-v5-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_bm25 batch --index staging/bm25-subset-v5-NEW --output staging/bm25-subset-v5-batch-NEW
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.subset_bm25 zip --index staging/bm25-subset-v5-NEW --output staging/vtls-bm25s-subset-NEW.zip
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_subset_bm25 tests.test_bm25_baseline tests.test_composition_bm25 tests.test_subset_candidate -v
```

Không build vào run đã tồn tại. Build ghim candidate006/ZIP-002/composition-queries-001
bằng config/hash; không chọn latest. Runtime ZIP mang dataset nguyên trạng,
không cần staging upstream. Chưa tích hợp UI/API hoặc yêu cầu nhóm đổi bản.
