# Stage 6 — encoder input và chunk/context PREVIEW

## Kết quả thực tế

Run thành công: **`staging/article22-stage6-002/`**, từ baseline
`staging/article22-preview-001/`. Đã đọc code CLI/worker/builder prototype,
DDD/SDD/SRS và contract/báo cáo trước; không dùng kết luận báo cáo thay
việc replay code và dữ liệu thật. Snapshot vẫn **2025-01-01**.

Ba chunk mục tiêu là nguyên văn Khoản 1–3, có sáu context rows từ title và
đoạn dẫn Điều 22. Nguồn PDF, units/spans và context không thay đổi. Tất cả
identity payload, chunk ID và content hash trùng baseline. Kết quả kế thừa
**origin=agent_review**, không tạo human reviewer event, assessment verified
hoặc corpus. Các trạng thái và chín blocker cũ được giữ nguyên.

Manifest SHA-256:
`c70a3dec68ce17c9b0b75921d9b4248324b6e8143643c68667f526f15df4838d`.

## Unknown token: nguyên nhân đã kiểm chứng

| Khoản | Trước: token / unknown | Chỉ gom whitespace: token / unknown | Sau PyVi: token / unknown | Special tokens |
|---|---|---|---|---:|
| 1 | 140 / 8 | 127 / 0 | 106 / 0 | 2 |
| 2 | 110 / 6 | 101 / 0 | 83 / 0 | 2 |
| 3 | 109 / 6 | 99 / 0 | 82 / 0 | 2 |

Các con số đếm trên **toàn text_for_search/encoder_text**, không chỉ target
hoặc context. Không truncation/padding, special tokens đã nằm trong số đếm.

**Toàn bộ 20 unknown trước là literal LF (`\n`)**. Regex local của PhoBERT
là `\S+\n?`, giữ một LF sau lexeme; BPE sinh mảnh LF không có trong vocab.
Đã dựng lại khớp toàn chuỗi tokens/IDs và từng literal lexeme, rồi xác nhận
slice của text_for_search; không suy từ chuỗi decode `<unk>`. Phép chỉ gom
whitespace đã đưa unknown về 0 trước khi thêm segmentation. Không có bằng
chứng lỗi encoding; cũng không gán nguyên nhân các unknown LF cho việc
thiếu word segmentation.

| Khoản | Vị trí unknown trong token sequence, tính từ 0 và gồm BOS/EOS |
|---|---|
| 1 | 12, 28, 37, 56, 77, 96, 114, 132 |
| 2 | 12, 28, 37, 56, 77, 97 |
| 3 | 12, 28, 37, 56, 77, 98 |

Phân loại: mỗi chunk có ba unknown ở separator ghép các khối, hai ở
context (LF giữa title/lead và LF trong lead); target có lần lượt 3/1/1.
Không có unknown bên trong law_title hoặc citation_path. LF ghép khối
được ghi là separator, không gán giả vào field nguồn. Ví dụ Khoản 1 token
96 là LF tại text_for_search[354:355], sau `hoặc`; token 114 tại [431:432]
sau `đường`, token 132 tại [511:512] sau `kỳ`.

Phép thử tokenizer không cung cấp native offset_mapping: bản cài hiện tại
không ném lỗi nhưng cũng không trả trường offset_mapping. Code kiểm cả
kết quả thực, không coi việc lời gọi không báo lỗi là có offsets. Fallback
chỉ ghi range khi regex/BPE roundtrip chứng minh được, nếu không thì null.
Các ranges trên thuộc **text_for_search**, không phải normalized.txt.

`unknown_diagnostics.md` trong run có đủ từng vị trí, component, literal và
snippet; `encoder_inputs.preview.jsonl` giữ token IDs/pieces, lexeme/ranges,
phép đối chứng trước/whitespace-only/sau. Offsets sau segmentation chỉ có
ý nghĩa trên encoder_text, chưa có inverse map về extraction.

## Cấu hình encoder đã triển khai

Model vẫn `bkai-foundation-models/vietnamese-bi-encoder`, revision
`84f9d9ada0d1a3c37557398b9ae9fcedcdf40be0`. Model card đúng revision và
sentence_bert_config.json đã được capture, cùng tài liệu PhoBERT/PyVi,
URL/hash/thời điểm truy cập thực ngày **2026-10-18 UTC**, trong
`model_evidence/`. Đây là ngày tra cứu kỹ thuật, không phải ngày hiệu lực.

[Model card](https://huggingface.co/bkai-foundation-models/vietnamese-bi-encoder)
yêu cầu word segmentation trước encode local và nêu PyVi là một lựa chọn;
[tài liệu PhoBERT](https://huggingface.co/docs/transformers/model_doc/phobert)
mô tả đầu vào word-segmented, single sequence `<s> X </s>`.

Policy **phobert-pyvi-input.v1** đã triển khai trong encoder_input: tạo bản
sao NFC, gom whitespace, PyVi tokenize, gom whitespace đầu ra; kiểm giữ đủ
mọi ký tự không phải whitespace theo thứ tự, chỉ thêm underscore nối từ.
Không lowercase/bỏ dấu. Document/query gọi **cùng hàm/cấu hình**; test với
cùng input cho cùng encoder_text và token IDs. Chưa nối vào ứng dụng.

- PyVi 0.1.1, sklearn-crfsuite 0.5.0, python-crfsuite 0.9.12. Package/model
  CRF/word-list/source hashes và dependency versions được khóa trong config.
  Segmenter dùng CPU CRF đóng gói trong PyVi; không tải encoder weights.
- PhobertTokenizer, Transformers 5.20.0; hash implementation và năm assets
  tokenizer giữ trùng baseline. Worker không import encoder/PyTorch, không
  network/database; CRF chỉ ghi file tạm trong scratch staging mới riêng.
- Giới hạn model theo SentenceTransformer của revision này là **256 tổng
  token**, single sequence có 2 special tokens. Preview budget cũng 256
  ở run này nhưng là tham số thử nghiệm riêng, chưa chốt budget toàn dự án.
- tokenizer.model_max_length hiện là sentinel rất lớn; không dùng nó làm
  giới hạn thực. max_position_embeddings=258 không được dùng để nâng budget.
- Không tạo prefix task/query/document hoặc context riêng cho encoder.
  text_original/context/text_for_search giữ nguyên, encoder_text/hash riêng.

## Builder dùng chung và tính tương thích

`src/chunk_preview.py` nhận units/quan hệ/spans/files/extractions, config và
callback chuẩn bị/đếm encoder input. Không có số Điều, mã luật hoặc run
hardcode. Hỗ trợ Khoản không có con, context riêng của Điều cha theo thứ tự
title/lead. Lead vắng có thể hợp lệ; thiếu field bắt buộc hoặc nguồn của
field thực có phải phát issue, không đoán/bỏ qua. Bảng/Điểm hoặc các loại
target khác chưa hỗ trợ. Khoản có con không được biến câu dẫn mức phạt
thành target thay cho hành vi.

Vượt budget được đo trên encoder_text: giữ candidate/context đầy đủ ở
quarantined, có issue và trạng thái blocked_preview, không nằm trong
chunks/contexts sẵn sàng. Không truncate hoặc tự nâng ngưỡng. Fixture gồm
câu dẫn mức phạt và Điểm đ hành vi chỉ là synthetic, không dữ liệu NĐ168.

`src.article22_stage6` là CLI ví dụ gọi builder, giới hạn đúng ba target
cũ. CLI v1/worker v1 được giữ **nguyên byte** để validator của preview-001
vẫn kiểm được code hashes đã seal; không sửa lịch sử run cũ.

`comparison.json` xác nhận mỗi identity_payload_equal=true,
changed_identity_fields=[], original_equal/context_equal/content_hash_equal=true.
Giữ chunk_policy_version cũ vì cách chia/ghép ba Khoản không đổi. Prefix
source_locator mới là baseline_snapshot/mapping_snapshot, không thuộc
payload chunk.v1; file/unit/span/extraction IDs và hash không đổi. Encoder
preprocessing có version/hash riêng, không đổi nghĩa content_sha256 DDD.

## Kiểm tra đã chạy

```powershell
.\.venv-stage1\Scripts\python.exe -m pip install pyvi==0.1.1 --disable-pip-version-check --report staging/stage6-verification-001/pyvi_install.json
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.article22_stage6 build --baseline-manifest staging/article22-preview-001/manifest.json --model-evidence staging/stage6-verification-001/model_evidence_retry --run-dir staging/article22-stage6-002
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.article22_stage6 validate --manifest staging/article22-stage6-002/manifest.json
$env:VTLS_ARTICLE22_MANIFEST = 'staging/article22-pdf-004/manifest.json'
$env:VTLS_ARTICLE22_PREVIEW_MANIFEST = 'staging/article22-preview-001/manifest.json'
$env:VTLS_STAGE6_MANIFEST = 'staging/article22-stage6-002/manifest.json'
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
.\.venv-stage1\Scripts\python.exe -m pip check
git diff --check
git diff --cached --stat
```

Kết quả cuối: build/validate **exit 0**, 3 chunk/6 context, 0 issue, mọi
blocker giữ nguyên. Validator CLI full replay baseline/mapping/source và
tokenizer/segmentation thật, không mock. **155/155 tests đạt, không skipped**,
57,136 giây: 136 hồi quy và 19 Stage 6. pip check không có dependency hỏng.
Diff check đạt; index Git rỗng, không stage/commit/push.
Sau khi hoàn chỉnh citation/path của fixture Điểm, chạy riêng lần cuối
**19/19 test Stage 6 đạt**, không skipped, 17,550 giây; log ở
`focused_final.log`, mã trả về 0 ở `focused_final_result.json`.

Test mới bao phủ đủ Khoản đơn/context, không lead, thiếu cha/nguồn/context
bắt buộc, budget/quarantine, Khoản có Điểm, nguyên văn/spans không bị sửa,
query/document chung config, import không tác dụng phụ, input encoder dài
hơn 256 giữ nguyên không truncation. Các test artifact thật kiểm IDs/pending,
encoder text/diagnostic offsets giả sau reseal và evidence thiếu. Test tamper
dùng bản sao cô lập, mock upstream để tập trung downstream; đã có lần CLI
full replay độc lập nêu trên.

Log và kết quả thật: `staging/stage6-verification-001/unittest.log`,
`unittest_result.json`, `validate.log`, `validate_result.json`,
`preservation.json`. SHA-256 của **7.520 file cũ** trong raw/processed/Qdrant
và staging không đổi; không thêm file vào các vị trí cũ. SQL chính thức
khớp nguyên byte ZIP. Trong các source/docs/config có từ trước chỉ append
AGENTS.md/README.md; mọi sửa đổi chưa commit khác giữ nguyên byte.

Các lần thử chưa đạt được giữ trung thực: mạng trong sandbox ban đầu báo
WinError 10051; lần chạy được cấp quyền tải/cài sau đó thành công. Focused
test đầu phát hiện fixture Windows CRLF và phép probe offsets chưa xét
trường trả về; đã sửa fixture mới/kiểm capability trước run thành công.
`staging/article22-stage6-001/` là run thử thất bại ở capability probe, có
run_report status=failed, không seal thành output hợp lệ; không dùng làm
preview kết quả và không ghi đè/xóa run đó. Focused test sau sửa đạt trước
khi chạy toàn bộ suite.

## Mở và chạy lại

Trong `staging/article22-stage6-002/`:

- `chunks_preview.md`: ba nguyên văn, context, text_for_search, encoder_text.
- `chunks.preview.jsonl`, `contexts.preview.jsonl`: chunk/context có source.
- `unknown_diagnostics.md`, `encoder_inputs.preview.jsonl`, `runtime.json`:
  chẩn đoán, tokens, cấu hình thực và giới hạn offsets.
- `comparison.json`, `validation_report.json`, `manifest.json`: ID/hash và
  kiểm định. `baseline_snapshot/` giữ bản sao input đã seal.

Validate lại bằng lệnh trên. Muốn build lại chọn run-dir chưa tồn tại,
dùng `--model-evidence staging/article22-stage6-002/model_evidence` để tận
dụng capture cũ. README có lệnh đầy đủ và requirements-stage6.txt đã pin.
Input staging không có trong Git; nếu thiếu phải khôi phục bundle thật,
không tạo quan sát hoặc hash giả.

## Giới hạn và bước tiếp theo đề xuất

Đã chạy CPU segmentation/tokenizer, chưa chạy encoder inference, embedding,
reranker hoặc retrieval. Không thử lại tải encoder/PyTorch trong lượt này;
WinError 4551 là hạn chế đã ghi nhận trước, không tuyên bố vừa kiểm lại.
Hết unknown và dưới budget không chứng minh chất lượng semantic search.

Builder chưa hỗ trợ Điểm, Điều làm target, bảng, tách đoạn dài hoặc context
dẫn chiếu. Chưa có inverse character map cho text đã segmentation. Những
trường hợp này phải có issue/quarantine, không đại diện bằng một chunk giả.
Chưa triển khai query integration; việc dùng cùng config hai phía đã được
kiểm ở API/test, việc chạy trong ứng dụng mới là bước tiếp theo đề xuất.

Nguồn/extraction/applicability vẫn pending; agent review không thay hồ sơ
reviewer. Chưa tạo corpus verified/frozen, BM25/Qdrant index hoặc kích hoạt
ứng dụng. Bước tiếp theo có thể chọn: rà chính sách context cho Khoản có
Điểm bằng fixture, hoặc tích hợp preprocessing query/document khi môi trường
encoder sẵn sàng; cả hai chưa được thực hiện trong lượt này.

## Diff summary của riêng lượt Stage 6

| File | Thay đổi |
|---|---|
| `src/chunk_preview.py` | Mới: builder dùng lại, source proofs/IDs/context/budget và quarantine. |
| `src/encoder_input.py` | Mới: tiền xử lý chung hai role, chẩn đoán BPE, worker CPU cô lập. |
| `src/article22_stage6.py` | Mới: CLI ví dụ hẹp, replay/manifest/comparison và báo cáo. |
| `config/stage6_preview.v1.json` | Mới: binding/pins/preprocessing/context/budget/ba target. |
| `requirements-stage6.txt` | Mới: dependencies segmentation/runtime đã pin. |
| `tests/test_stage6.py` | Mới: 19 kiểm thử Stage 6, fixture tách dữ liệu thật. |
| `Stage6_Encoder_Chunk_Preview_Contract.md`, báo cáo này | Hai tài liệu mới: contract và bằng chứng kiểm tra. |
| `AGENTS.md`, `README.md` | Append phạm vi và lệnh thực tế, giữ nội dung cũ. |

Tổng: **8 file mới, 2 file có trước được append**. Các diff/untracked có
trước lượt này giữ nguyên, không gộp chúng thành kết quả phát triển Stage 6.
