# Stage 6 — encoder input và builder chunk/context PREVIEW

Snapshot **2025-01-01**. Contract bổ sung cho preview Điều 22, không sửa DDD,
schema phục vụ, parser, corpus hoặc review decisions. Kết quả nguồn kế thừa
origin=agent_review của preview-001; các trạng thái và blocker giữ nguyên.

## Đường đi dữ liệu và ba biểu diễn

```text
legal units + quan hệ + source spans/extraction/raw
  -> chunk_preview.build_chunks: nguyên văn Khoản + context riêng của Điều
  -> text_for_search theo DDD + content hash + chunk.v1 ID
  -> encoder_input.encode_inputs: bản sao NFC/whitespace/PyVi
  -> encoder_text + tokenizer IDs/counts (không embedding)
```

| Biểu diễn | Quy tắc | Offset/hash |
|---|---|---|
| text_original | Toàn bộ chữ riêng của Khoản không có con; không viết lại | Offsets legal_unit; source spans tuyệt đối trong extraction |
| context_text | Title/đoạn dẫn thực có của Điều cha, theo thứ tự field, nối LF | Context offsets tương đối trong từng field; source_locator riêng |
| text_for_search | law_title, citation_path, context nếu có, text_original; các khối nối 2LF | content_sha256 SHA-256 UTF-8; giữ nguyên để so sánh các mode |
| encoder_text | Bản sao search hoặc query qua cùng hàm/cấu hình tiền xử lý | encoder_text_sha256 riêng; không phải nguyên văn hoặc extraction offsets |

Tiền xử lý không bổ sung context riêng cho dense/reranker và không sửa text
tìm kiếm chung. Prototype đang chạy chưa được nối với hàm mới; không tuyên
bố query của ứng dụng đã dùng segmentation. Khi tích hợp retrieval phải
dùng cùng preprocessing_version/config/hash cho document và query; không
được chỉ đổi một phía.

## Căn cứ model và cấu hình

[Model card BKAI](https://huggingface.co/bkai-foundation-models/vietnamese-bi-encoder)
yêu cầu word segmentation trước khi gọi SentenceTransformer/Transformers;
PyVi là một lựa chọn được tác giả nêu. Widget hosted có segmenter riêng,
khác lời gọi tokenizer local. Không tự thay model/tokenizer trong Stage 6.
[Tài liệu PhoBERT](https://huggingface.co/docs/transformers/model_doc/phobert)
cũng yêu cầu đầu vào đã word-segmented và mô tả `<s> X </s>` cho một chuỗi.

Model ID vẫn `bkai-foundation-models/vietnamese-bi-encoder`, revision
`84f9d9ada0d1a3c37557398b9ae9fcedcdf40be0`. Đã capture model card và
sentence_bert_config.json **đúng revision**, tài liệu PhoBERT và PyVi cùng
URL, hash, thời điểm truy cập thật trong model_evidence của run mới.
Các bằng chứng này là tài liệu kỹ thuật, không phải căn cứ hiệu lực luật.

- `model_max_tokens=256` lấy từ cấu hình SentenceTransformer của revision
  này. Một đầu vào single sequence có 2 special tokens, tức tối đa 254 body
  tokens khi dùng giới hạn đó; pair có 4 special tokens, chưa chạy reranker.
- `preview token_limit=256` là quyết định thử nghiệm riêng, có thể hạ xuống;
  ngưỡng thực thi là min(preview budget, model limit). Hai số bằng nhau ở
  run này không làm token budget toàn dự án trở thành đã chốt.
- tokenizer.model_max_length tại máy là sentinel rất lớn, không dùng nó để
  cho phép đầu vào dài. config.max_position_embeddings=258 là kích thước
  bảng vị trí, không coi đó là ngưỡng search input 258 token.

`config/stage6_preview.v1.json` khóa model/revision, năm tokenizer assets,
PyVi/model CRF/word list/source hashes và phiên bản package. Policy tiền xử
lý `phobert-pyvi-input.v1`: NFC trên bản sao, gom Unicode whitespace thành
space, `ViTokenizer.tokenize`, gom whitespace kết quả; không lowercase,
bỏ dấu hoặc cắt nội dung. Kiểm từng ký tự không phải whitespace còn nguyên
theo thứ tự, chỉ cho phép thêm underscore nối từ; sai thì thất bại rõ ràng.

PyVi 0.1.1 dùng CRF CPU và model được đóng gói cùng package; các asset này
được pin/hash, không tải thêm encoder weights. Worker tách process, chặn
import PyTorch/TensorFlow/JAX, network/database/subprocess, chỉ cho CRF tạo
file tạm trong thư mục staging mới riêng rồi dọn file tạm do chính nó tạo.
Không sửa backend ứng dụng hay nạp DLL PyTorch bị Windows chặn. Dependency
thử nghiệm ở requirements-stage6.txt; không cần tải model encoder.

## Chẩn đoán unknown và offsets

Tokenizer local không trả native offset_mapping trong phép thử thực tế.
Không tìm ký tự bằng cách decode `<unk>` hoặc đoán offset. Chẩn đoán:

1. Lấy IDs, token pieces, special mask trên toàn input không truncation.
2. Replay regex `\S+\n?` và BPE của đúng tokenizer/implementation được hash.
3. Chỉ công bố offset khi các pieces/IDs khớp toàn chuỗi và literal nối từ
   BPE khớp chính xác lexeme nguồn. Khi không khớp, chỉ giữ token position,
   char ranges=null và ghi phương pháp mapping unavailable.
4. Gán range vào law_title/citation_path/context/text_original theo phép
   ghép search đã kiểm chứng. Các LF giữa khối là separator do thiết kế,
   không giả là ký tự của field nguồn. LF giữa title và lead là context.

Vị trí token tính từ 0, gồm BOS/EOS. Offsets chẩn đoán trước là trên
text_for_search, không phải extraction. Sau segmentation, offsets nếu có
chỉ thuộc encoder_text; chưa có inverse map về source. Giữ các namespace
này riêng. `encoder_inputs.preview.jsonl` chứa đầy đủ IDs/pieces, vị trí
unknown, literal/range/lexeme/snippet, component và các phép đối chứng.

Ba chunk cũ có toàn bộ unknown là LF. Đối chứng chỉ gom whitespace đã về
0 unknown; segmentation được thêm vì yêu cầu model, không gán nhầm nguyên
nhân LF cho encoding hoặc thiếu segmentation. Việc hết unknown không chứng
minh chất lượng biểu diễn hoặc tìm kiếm.

## Builder dùng chung

`src/chunk_preview.py` không có mã luật, số Điều hoặc đường dẫn run cố định.
Nhận data gồm document/units/files/extractions/spans, root đọc artifact,
config target IDs/chunk policy/required context fields/budget, blocker và
callback đo encoder input. Builder không tự tải tokenizer hoặc mở database.

- Hỗ trợ Khoản không có con, có Điều cha thật. Kiểm ID đơn vị/spans, quan hệ,
  cha khác văn bản/chu trình/ID trùng, file/extraction/quote hashes và field
  roundtrip. Source nhiều spans dựng lại bằng LF theo DDD.
- Context chỉ là chữ riêng title/lead của Điều cha thực có; không sao text
  Khoản hoặc Điểm con vào cha. Thứ tự title rồi lead, context_order liên tục.
- Không có lead vẫn hợp lệ nếu config không đòi lead. Field không rỗng thì
  bắt buộc có source proof; không được âm thầm bỏ field thiếu bằng chứng.
  Nếu policy cho phép không có context, context_text=null và bỏ khối đó
  khỏi phép ghép search đúng DDD.
- Phạm vi này không xử lý Khoản có Điểm hoặc loại target khác. Trả issue
  UNSUPPORTED_STRUCTURE kèm unit và source spans; không dùng riêng câu dẫn
  mức phạt như target đại diện cho các hành vi chưa xử lý.
- Thiếu cha/nguồn, context bắt buộc, ID sai hoặc cấu trúc không rõ: issue và
  unit_results blocked_preview; không tạo legal unit hoặc quan hệ giả.
- Đầu vào encoder vượt ngưỡng: issue TOKEN_BUDGET_EXCEEDED, giữ toàn candidate
  và contexts trong quarantined; không nằm trong chunks/contexts sẵn sàng.
  Không cắt chữ, đổi budget hoặc bỏ nội dung để pass.

Kết quả luôn preview_only=true, corpus/effective dates=null,
applicability_status=pending_review, release_eligible=false. Chỉ dùng schema
PREVIEW có sẵn; không nới schema DDD hoặc tự tạo unit_assessment verified.

## IDs, CLI ví dụ và replay

Chunk ID dùng đúng chunk.v1 DDD; content_sha256 vẫn trên text_for_search,
không hash encoder_text thay nó. Encoder config/implementation/runtime có
binding riêng ở manifest/sidecar. Thay encoder preprocessing không đổi ID
chunk khi identity payload không đổi; đổi policy/context/metadata luật phải
tính ID theo payload mới và liệt kê trường thay đổi.

CLI `src.article22_stage6` là ví dụ gọi builder/encoder dùng chung; chỉ chọn
ba targets và dependencies từ baseline preview-001. Config giữ
chunk_policy_version=article22-context-preview.v1 vì cách chia/ghép cho ba
Khoản này không đổi. Không đổi thành version mới chỉ do tách module.
Source references của run mới thêm prefix baseline_snapshot; đường dẫn lưu
không thuộc chunk.v1, unit/spans/file hashes không đổi.

CLI v1 `src.article22_preview` và worker v1 giữ nguyên byte: manifest cũ có
code hashes nên sửa trực tiếp sẽ làm run đã seal không kiểm lại được.
Đây là đường tương thích để đối chiếu, không phải hai builder mới song song.
Logic dùng chung hiện hành nằm trong chunk_preview; CLI Stage 6 không tự
viết lại logic tạo target/context.

Build/validate kiểm lại toàn baseline/mapping, pins/assets, kết quả builder,
spans/search/hash/IDs, diagnostics/token counts và báo cáo đọc được. Manifest
khóa code/config/schema, toàn input/output. Thay nội dung rồi reseal vẫn bị
replay phát hiện. 0=preview đạt, 2=đã xử lý nhưng có issue/quarantine,
1=lỗi input/binding/runtime. Run phải mới dưới staging, không ghi đè.

Chưa tích hợp query/document vào ứng dụng, chưa embedding/reranker hoặc
đánh giá retrieval. Không phát sinh quyết định reviewer/source approval,
corpus frozen/active, BM25 hay Qdrant. Lệnh thực tế ở README và báo cáo
Stage6_Encoder_Chunk_Preview_Verification.md.
