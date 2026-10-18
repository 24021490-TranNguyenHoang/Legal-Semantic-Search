# Agent review và ba chunk/context PREVIEW Điều 22

## Kết quả và phạm vi

Đã tạo `staging/article22-preview-001/` từ mapping PDF
`staging/article22-pdf-004/`, snapshot **2025-01-01**. Có ba chunk nguyên vẹn
cho Khoản 1–3, mỗi chunk có hai context rows: title và đoạn dẫn Điều 22.
Không tạo corpus, assessment, submission hoặc human reviewer event; không
chạy admit, embedding, index hoặc kích hoạt ứng dụng. Không tự commit.

Kết quả đối chiếu mang **origin=agent_review**, không phải quyết định reviewer
theo contract assessment v1.1/draft hiện hành. Nguồn, extraction và các
quyết định còn pending giữ nguyên. Không gặp mâu thuẫn cụ thể trong vùng đã
đối chiếu cần người dùng giải quyết.

Manifest preview SHA-256:
`f57afc1167e29cde01e0a5c372b9deaee678b4ef07c17a7c4efd601f6ea54141`.

## Đối chiếu nguồn của agent

Các đường dẫn dưới đây tương đối với `staging/article22-preview-001/`.
Số trang là trang PDF tính từ 1, khác số in trên Công báo.

| Nội dung | Bằng chứng đã xem | Kết quả và giới hạn |
|---|---|---|
| Nhận diện văn bản | `mapping_snapshot/inputs/evidence/01/snapshot.html`: bảng metadata và hai liên kết đính kèm; PDF `02/snapshot.pdf` p1; `03/snapshot.pdf` p1/p61 | Cùng số 36/2024/QH15, tên Luật Trật tự, an toàn giao thông đường bộ, ngày ban hành 27-06-2024. URL và byte/hash hai PDF khớp hồ sơ capture. |
| Quan hệ hai phần | PDF đầu p20, PDF tiếp p1 | Cuối phần đầu ghi xem tiếp Công báo 979+980; đầu phần tiếp ghi tiếp theo 977+978, cùng luật/ngày và tiếp từ Điều 24 sau Điều 23. |
| Nút cha | PDF đầu p1/p10, spans mapping | Document và Chương II có nguồn thực; chỉ giữ quan hệ/citation. Không đưa preamble/document/Chương vào context. |
| Nội dung chọn | PDF đầu p19, trang in 94; normalized.txt/trace và tám spans của mapping | Title, đoạn dẫn Điều 22 và Khoản 1–3 khớp vùng đã quan sát. Không đưa nội dung Điều 21 phía trên vào context. Replay kiểm lại hash/slice và đơn vị cha. |
| Warning p21 | PDF đầu p21 và ảnh `agent_inspection/part02-page021.png` | Có thông tin Văn phòng Chính phủ xuất bản, không phải trang trắng. Không trích được chữ; nằm ngoài spans chọn và chưa thấy ảnh hưởng trực tiếp tới Điều 22. Giữ nguyên PDF_PAGE_NO_TEXT; không OCR/resolve issue. |
| Hiệu lực | PDF tiếp p58–61; Điều 88/89 và căn cứ đã lưu trong mapping | Điều 88 nêu mốc chung 01-01-2025, ngoại lệ Khoản 3 Điều 10 từ 01-01-2026. Không thấy ngoại lệ riêng Điều 22 trong phần chuyển tiếp đã xem. Đây là đề xuất có căn cứ, chưa thành quyết định hiệu lực. |

Agent đã xem ảnh của mười trang: phần đầu p1/10/19/20/21, phần tiếp
p1/58/59/60/61. Hồ sơ quan sát ở `agent_inspection/observations.json`, có
thời điểm thực tế của agent, hash ảnh/PDF và nội dung quan sát. Các phép
đối chiếu text/metadata, quote, page locator, hash và giới hạn ở
`agent_review.json`; bản ngắn ở `agent_review.md`.

Tận dụng capture có sẵn; không tải thêm nguồn trong bước này. Thời điểm tải
thật vẫn là các trường source_accessed_at của capture ngày 2026-10-17 UTC,
không thay ngày ban hành hoặc ngày hiệu lực lịch sử. Chưa tra cứu lịch sử
sửa đổi toàn diện hoặc xác minh toàn văn hai PDF. Validator tái kiểm tra
binding/hash và nội dung text; không tuyên bố tự tái thực hiện quan sát ảnh.

## Ba preview dễ đọc

Context chung, giữ đúng LF của extraction:

```text
Nhường đường tại nơi đường giao nhau
Khi đến gần đường giao nhau, người điều khiển phương tiện tham gia giao thông
đường bộ phải quan sát, giảm tốc độ và nhường đường theo quy định sau đây:
```

**Khoản 1**:

```text
1. Tại nơi đường giao nhau giữa đường không ưu tiên với đường ưu tiên hoặc
giữa đường nhánh với đường chính thì xe đi từ đường không ưu tiên hoặc đường
nhánh phải nhường đường cho xe đi trên đường ưu tiên hoặc đường chính từ bất kỳ
hướng nào tới;
```

**Khoản 2**:

```text
2. Tại nơi đường giao nhau không có báo hiệu đi theo vòng xuyến, phải
nhường đường cho xe đi đến từ bên phải;
```

**Khoản 3**:

```text
3. Tại nơi đường giao nhau có báo hiệu đi theo vòng xuyến, phải nhường
đường cho xe đi đến từ bên trái.
```

| Field nguồn | Offsets trong normalized.txt | Số code point | Token target | Token context | Token text_for_search | Unknown trong text_for_search |
|---|---|---:|---:|---:|---:|---:|
| Title Điều 22 | [36927,36963) | 36 | — | — | — | — |
| Đoạn dẫn Điều 22 | [36964,37116) | 152 | — | — | — | — |
| Khoản 1 | [37117,37363) | 246 | 63 | 50 | 140/256 | 8 |
| Khoản 2 | [37364,37473) | 109 | 33 | 50 | 110/256 | 6 |
| Khoản 3 | [37474,37577) | 103 | 32 | 50 | 109/256 | 6 |

Tất cả các source slices trên thuộc extraction PDF đầu, p19. Offsets là
Unicode code point, đầu bao gồm/cuối loại trừ. Context có offsets tương đối
trong từng field: title [0,36), lead [0,152); chunk target [0,len(Khoản)).
Không dùng offsets của DOCX hoặc captured-page text thay extraction offsets.
Mỗi source_locator giữ file/extraction/span ID, locator, hash và đường dẫn
thực. Các snapshot input là bản sao nguyên byte của bundle mapping.

`text_for_search` nối law_title, citation_path, context_text và text_original
bằng hai LF giữa các khối; context_text nối title/lead bằng một LF. ID dùng
đúng payload chunk.v1 trong ZIP thiết kế; content hash trên UTF-8 của
text_for_search. ID/hash đầy đủ ở JSONL, không rút gọn trong dữ liệu.

Token đếm thật bằng tokenizer của model hiện có, revision/5 asset hashes
được khóa; Transformers 5.20.0, PhobertTokenizer, có hai special tokens,
không truncation hoặc thêm word segmentation. Worker chỉ chạy tokenizer
offline, không nạp PyTorch/DLL/model weights hoặc inference. Ngưỡng 256 chỉ
là ngưỡng preview theo prototype, chưa chốt chính sách phát hành. Unknown
tokens được giữ trong báo cáo; kết quả dưới ngưỡng không chứng minh chất
lượng biểu diễn hoặc truy hồi. Chưa kiểm tra embedding/reranker/query pair.

## File thay đổi trong bước này

| File | Mục đích |
|---|---|
| `src/article22_preview.py` | CLI build/validate; agent-only evidence, chunk/context, source proofs, replay và pending gates. |
| `src/preview_tokens.py` | Tokenizer-only worker offline, kiểm pin/hash và chặn inference/network/write trong worker. |
| `config/article22_preview.v1.json` | Policy preview, snapshot, token budget/model revision/asset hashes, trạng thái pending/null. |
| `schemas/chunk_preview_v1/preview.schema.json` | Contract preview riêng, cố ý không đạt schema chunk phục vụ. Không đổi schema DDD. |
| `tests/test_article22_preview.py` | 15 kiểm thử mới, gồm năm kiểm thử trên bản sao artifact thật khi bật biến môi trường. |
| `docs/design/data_model_v1/Article22_Chunk_Preview_Contract.md` | Quy tắc context/ID/hash/offset/token và tách agent review khỏi reviewer. |
| `README.md`, `AGENTS.md` | Bổ sung phạm vi được phép và lệnh chạy thực tế; giữ các nội dung/thay đổi có sẵn. |
| Báo cáo này | Kết quả, bằng chứng, giới hạn và lệnh kiểm tra lại. |

Các file draft/assessment/mapping đã thay đổi hoặc untracked từ trước được
giữ nguyên, không stage/commit. Output mới chỉ nằm trong ba run mới:
`article22-preview-inspection-001`, `article22-preview-001`,
`article22-preview-verification-001` dưới staging.

## Lệnh đã chạy và kết quả

Từ thư mục gốc dự án, trong PowerShell:

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.article22_preview build --mapping-manifest staging/article22-pdf-004/manifest.json --agent-review staging/article22-preview-inspection-001/observations.json --run-dir staging/article22-preview-001
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.article22_preview validate --manifest staging/article22-preview-001/manifest.json
$env:VTLS_ARTICLE22_MANIFEST = 'staging/article22-pdf-004/manifest.json'
$env:VTLS_ARTICLE22_PREVIEW_MANIFEST = 'staging/article22-preview-001/manifest.json'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
git diff --check
git diff --cached --stat
```

Build và validate **exit 0**: 3 chunk/6 context, technical_valid=true,
token_limit_passed=true, origin=agent_review, human_reviewer_event_count=0,
corpus_created=false, release_eligible=false. Validate replay đầy đủ mapping
đầu vào, không mock upstream trong lần CLI này.

Toàn bộ **136 tests đạt, không skipped**, 69,162 giây (121 hồi quy + 15 mới).
Log thực tế và mã trả về ở
`staging/article22-preview-verification-001/unittest.log`,
`unittest_result.json`, `validate.log`, `validate_result.json`.

Các kiểm thử mới bao gồm: nguyên văn/spans/context; công thức ID đối chiếu
hàm ZIP; preview bị schema serving từ chối; determinism; thiếu lead/sai
offset/bổ sung unit bị từ chối; import không tác dụng phụ; token dài hơn
256 không bị cắt; context/status/token giả sau reseal vẫn bị phát hiện;
agent_review không thể nạp như phiếu human. Các test tamper dùng bản sao
cô lập và chỉ mock upstream để tập trung downstream; tokenizer thật vẫn
chạy, ngoài lần CLI full replay độc lập nêu trên.

Hai lần tái tính chunk/context từ input thật cho kết quả trùng nhau và
trùng JSONL đã lưu; `determinism.json` ghi ID và manifest hash. Đối chiếu
SHA-256 **7.167 file cũ** trong raw, processed, Qdrant và staging trước bước
này: không file thay đổi/mất. `preservation.json` ghi kết quả. SQL chính
thức khớp nguyên byte ZIP mẫu. AST/JSON parse và whitespace trên source,
test/config/schema/contract mới đạt. `git diff --check` đạt; không có file
được stage.

## Cách mở và tái chạy

- Đọc ngắn: `staging/article22-preview-001/agent_review.md`.
- Xem ba chunk, context, text_for_search và proofs:
  `staging/article22-preview-001/chunks_preview.md`.
- Dữ liệu: `chunks.preview.jsonl`, `contexts.preview.jsonl`,
  `token_report.json`, `validation_report.json` trong cùng run.
- Kiểm lại run đã seal bằng lệnh validate trên; không ghi lại output vào run đó.
- Tái build dùng lệnh trên nhưng đổi run-dir thành đường dẫn **chưa tồn tại**,
  có thể thêm `--tokenizer-dir staging/article22-preview-001/tokenizer_assets`.
  Input staging không nằm trong Git; giữ chúng để tái chạy. Không tự tạo
  observations.json giả nếu thiếu bằng chứng quan sát.

## Trạng thái còn lại

Giữ sáu blocker nguồn/extraction/mapping/scope/applicability/corpus từ bundle
cũ và ba cờ PREVIEW_NOT_A_CORPUS, AGENT_REVIEW_NOT_REVIEWER_DECISION,
TOKEN_BUDGET_NOT_RELEASE_POLICY. corpus_version/effective dates=null,
applicability_status=pending_review. Không chép đề xuất hoặc nhận định của
agent thành quyết định. Trang 21 chưa OCR; chưa chứng minh toàn file, lịch
sử sửa đổi đầy đủ, chất lượng embedding hoặc tìm kiếm. Đây là các giới hạn
còn nguyên, không bổ sung yêu cầu chữ ký số hoặc hệ thống phân quyền.
