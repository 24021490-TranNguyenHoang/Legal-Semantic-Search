# Khôi phục NĐ168 Điều16 Khoản2 — experimental preview riêng

Commit đầu lượt `aee22f0173affc406cfccc443a9132c43c1c98fb`, Git sạch.
Đã đọc AGENTS/STATUS, báo cáo và run `blocked-source-repair-003`, contract
nguồn/extraction/parser/mapping/chunking và mã thực tế. Không stage/commit/push.

**Đã khôi phục đủ năm Điểm a,b,c,d,đ; 5 preview, 0 blocked/quarantine.**
Run cuối: `staging/nd168-a16k2-preview-004/`. Mở `review.md` để xem cây,
nguyên văn DOCX→nguồn chính thức→khôi phục, từng diff, spans và context.

## Chọn nguồn: đã tìm được text chính thức tương ứng vùng cần dùng

[Bản toàn văn trên Cổng Chính phủ](https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-dinh-168-2024-nd-cp-quy-dinh-xu-phat-vi-pham-hanh-chinh-ve-trat-tu-atgt-duong-bo-119241231164556785.htm)
được capture vào `staging/nd168-a16k2-source-check-001/`:

- accessed_at thực: **2026-10-22T09:42:43.614242Z**; HTTP200, 1.036.103 byte.
- HTML SHA: `e3803dd1ddd2a770e5f61a95e54111308c4d7b08c2196fa792ae5fdeeb4a5171`.
- Website metadata published03/04/2025 05:59 +07, modified cùng ngày10:59.
  Capture hôm nay không chứng minh website lịch sử tại2025-01-01.

Đã tái sử dụng [PDF scan Chính phủ](https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/01/168-nd-cp.signed.pdf),
SHA `7bb11b939d162499ab404aa41a940cce05dbf071d9cbae7a8898b00d4b4a48bd`,
accessed_at gốc **2026-10-16T14:33:07.439116Z**. Không tải lại PDF. Đã xem
ảnh trang40–41 để đối chiếu trọn title, lead và từng Điểm; c) tiếp từ cuối
trang40 sang đầu41, d)/đ) nằm trang41. Xem thêm ảnh trang1 để xác định số
168/2024/NĐ-CP, ngày26/12/2024 và tên nghị định; không map Điều khác.
Evidence nhận diện riêng: `staging/nd168-a16k2-source-identity-001/`.

HTML là nguồn text mới; scan là bằng chứng đối chiếu. Không cần phiên âm
hoặc OCR. Đã đọc từng ký hiệu/dấu câu/toàn nội dung trong vùng này; chưa
thấy ký tự không đọc chắc trong title/lead/năm Điểm. Đây là quan sát agent,
không human-reviewed/verified, không xác nhận toàn file hay applicability.
Không lấy ngày tải/bài đăng thay ngày ban hành/hiệu lực. Lần tải sandbox
ban đầu bị chặn socket; lần capture được phép sau đó thành công, có log
URL/time/hash thật, không tạo ngày tải giả.

## Bảng nội dung cũ → chính thức → khôi phục

| Thành phần | DOCX cũ | Text HTML đã đối chiếu scan | Khôi phục / token gồm special |
|---|---|---|---|
| Title Điều16 | Đúng tiêu đề về người điều khiển xe máy chuyên dùng, kể cả rơ moóc | Khớp nguyên văn | Giữ title làm context |
| Lead Khoản2 | Phạt1.000.000–2.000.000 đồng, một trong các hành vi | Khớp nguyên văn | Giữ toàn lead làm context |
| a | Có unit; hoạt động không đúng phạm vi | Khớp nguyên văn | Đủ text/spans, **101 token**, unknown0 |
| b | Có unit; giấy chứng nhận/tem kiểm định | Khớp nguyên văn | Đủ text/spans, **143 token**, unknown0 |
| c | Có unit; chứng nhận đăng ký xe, cả đoạn dài | Khớp nguyên văn | Đủ text/spans, **187 token**, unknown0 |
| d | Paragraphp[518] bị cách ly, marker sai đ); chưa có unit | Marker d) đúng; nguồn HTML có một trailing space | Khôi phục unit từ vùng cách ly, **121 token**, unknown0 |
| đ | Paragraphp[519] bị cách ly, có `ngán hàng`; chưa có unit | `ngân hàng`, marker đ) | Khôi phục đủ đoạn, **212 token**, unknown0 |

Không chỉ phục hồi ba candidate a/b/c. Năm Điểm đầy đủ, thứ tự0..4, giữ
toàn bộ số tiền/đơn vị/ngoặc/rơ moóc/dấu câu. Bảng chi tiết và full diff
trong `comparison.jsonl`/`review.md` phân biệt content_difference với
format_whitespace; không che khác biệt bằng folding. c) không bị cắt tại
ranh giới trang scan. Không tạo thêm target từ lead mức phạt.

## Provenance, extraction và cây

JSONL source_files.prepared có hai hồ sơ dữ liệu thật, qua schema DDD:

- HTML file_id `a8ccc14a-e7ea-59ef-b86e-32f956b3699e`, source_set riêng
  `SRC-004-html-a16k2`; PDF file_id `0498a83b-38a4-502e-b32e-b3922bad3fbf`,
  source_set `SRC-004-signed-pdf`. Cùng namespace/quy tắc UUIDv5 source-file.v1
  hiện có, không dùng file_id DOCX cho HTML/PDF.
- `source_facts.pending.json` tách capture facts và review/edition/hiệu lực
  pending. Không giả làm bundle Stage2 chính thức hoặc tạo corpus/FK giả.

Extraction hẹp method=html_text (DDD đã hỗ trợ), dùng lại normalizer Stage3
NFC/LF và định danh extraction.v1, không sửa pipeline DOCX/PDF cũ. Artifact
mới có **2.436 Unicode code points**, UTF-8 không BOM, trace fragments/
separators và XPath DOM thật. Tool/version/code/Python/Unicode/lxml/config
được khóa; thời điểm chạy ở created_at, không thay retrieved_at.

Cây chọn lọc có **10 units/10 spans**:

```text
document 168/2024/NĐ-CP
  Chương II                      ordinal1
    Mục 2                        ordinal1
      Điều 16                    ordinal3
        Khoản 2                  ordinal1 — toàn lead mức phạt
          Điểm a                 ordinal0
          Điểm b                 ordinal1
          Điểm c                 ordinal2
          Điểm d                 ordinal3 — khôi phục mới
          Điểm đ                 ordinal4 — khôi phục mới
```

Document/Chương/Mục chỉ là dependencies cấu trúc thật, title lấy HTML;
own text chưa chọn, không khẳng định toàn cha rỗng/đã rà. Không tạo Khoản1
hoặc Điều13–15 giả để lấp ordinal. Thứ tự đã kiểm trên heading/marker thật
của HTML. Điều16 không có đoạn dẫn riêng trước Khoản1, nên context lead
Điều vắng hợp lệ. Context mỗi Điểm = title Điều16 → lead Khoản2; không
lấy nội dung anh em, Khoản1 hoặc ghép căn cứ dẫn chiếu ngoài cây.

Source spans dùng offsets tuyệt đối trên **normalized.txt HTML mới**.
Locator HTML/XPath, không bịa DOCX locator, PDF text offsets hoặc pixel
tọa độ. Scan alignment nằm riêng: PDF/image hash, page40/41 và phạm vi
mô tả. Bản sao nguồn/extraction cũ chỉ dùng comparison, không sửa marker
hoặc sinh span cho vùng cách ly trên extraction cũ.

## Mapping IDs và scope

`id_crosswalk.jsonl` có 10 hàng, bao gồm hai hàng old_unit_id=null cho
d/đ; chỉ giữ raw locator/quote/offset của vùng cách ly làm bằng chứng cũ.
Không tạo old ID giả. Các unit ID cũ có thật được đối chiếu toàn bộ
UNIT_FIELDS với payload mới:

- Document đổi title do biểu diễn line break/NBSP của HTML, own text
  không được chọn trong sparse projection; Chương/Mục cũng khác title
  line break và parent ID. Những khác biệt này được ghi rõ.
- Điều/Khoản/a,b,c giữ nguyên nội dung own field, nhưng parent_unit_id
  đổi dây chuyền nên ID đổi đúng unit.v1.
- File/extraction ID hoặc timestamp không được chèn vào unit identity.
  Fixture kiểm đổi nguồn/extraction mà giữ toàn payload thì unit IDs giữ
  nguyên. Không ép ID đổi bằng version/salt.
- Chunk dùng nguyên chunk.v1/leaf-clause-point-context.v1; source_url,
  unit ID/context identity theo binding mới được ghi đầy đủ. Không mang
  quyết định/proposal DOCX sang như quyết định của nguồn HTML.

Proposal scope riêng: năm Điểm included vì chế tài trực tiếp người điều
khiển xe tham gia giao thông theo BRD3.1, khác chế tài cơ sở/trung tâm.
Điều/Khoản supporting đúng title/lead dependency; ba cha cấu trúc scope
null. Mỗi proposal có unit/hash/spans/extraction/HTML/PDF/snapshot binding,
origin agent_review, reviewer_ref=null. **Applicability pending**, ngày
hiệu lực/corpus null, release_eligible=false.

## Lệnh đã chạy và kết quả

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.nd168_a16k2 build --run-dir staging/nd168-a16k2-preview-004
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.nd168_a16k2 validate --manifest staging/nd168-a16k2-preview-004/manifest.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_nd168_a16k2 tests.test_stage6_points.PointBuilderTests
git diff --check
```

- Build/validate exit0: 5 points/5 preview, không blocked/quarantine,
  replay source/capture/metadata/DOM/trace/units/spans/context/token/ID đạt.
- **20 tests đạt**: 7 fixture HTML/mapping và 13 builder regression. Gồm
  đủ thứ tự năm Điểm, sparse ordinals, thiếu/trùng/sai marker phải fail,
  unsupported content, entities/LF, roundtrip/ID/quan hệ sai, unit ID ổn
  định khi chỉ đổi nguồn, context không lẫn anh em; fixture257 token giữ
  toàn candidate ở quarantine và fixture uncertainty chặn preview.
- Trên bản copy kiểm thử: sửa normalized text rồi reseal → exit1; đổi
  source facts thành human_reviewed rồi reseal → exit1. Không sửa run thật.
- Audit hash/index inventory và byte source xác nhận raw, dataset
  **3.077 chunk/5.371 context**, index, query/evaluation, ZIP và review003
  cũ giữ nguyên. Không cần build lại hoặc chạy toàn suite pipeline.
- Evidence thực thi: `staging/nd168-a16k2-verification-001/` chứa tests,
  validate, tampering tests và preservation JSON.

Các run001–003 là bước chẩn đoán/hoàn thiện, giữ nguyên; dùng004 để replay
với source hiện tại. Lỗi thiếu normalized trước source-proof ở lần đầu
đã sửa bằng ghi artifact extraction trước builder và so lại nó khi replay;
không nới source proof. Các fixture ban đầu cần khai báo charset và marker
lead đúng contract; không dùng lỗi fixture làm lý do nới reader thật.

Để tự chạy lại, thay run-dir bằng tên mới. Giữ coverage/tokenizer assets
referenced và source capture001 cho build; validate dùng bản sources đã
chụp trong run. Gói không được quảng bá là portable độc lập. Không kiểm
máy/OS khác, chưa xác minh pháp lý/source edition, không OCR/encoder
inference/embedding/index hoặc nhập vào dataset nhóm.

## File thay đổi và phần còn pending

Thêm `src/nd168_a16k2.py`, config source/review, tests, contract hẹp và
báo cáo này; cập nhật README/STATUS. Không sửa schema hoặc module cũ đã
khóa hash. Blocker ký hiệu/nội dung của **riêng Khoản2** đã có nguồn thay
thế và preview kỹ thuật; không tuyên bố DOCX/toàn NĐ168 được sửa/verified.

Chưa có quyết định reviewer về nguồn/extraction/scope/applicability, chưa
đối chiếu toàn lịch sử hiệu lực tại snapshot. Website hiện tại sau snapshot
chỉ được dùng với đối chiếu vùng scan, không mặc định là bản lịch sử.
Không mở rộng Điều39, Điều40 hoặc hai bảng Luật35; không nhập preview vào
dataset/index/evaluation đang dùng và không tự commit.
