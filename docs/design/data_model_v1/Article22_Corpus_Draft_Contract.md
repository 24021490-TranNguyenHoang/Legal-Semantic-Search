# Review có phạm vi và nhập corpus draft Điều 22 — article22-draft.v1

Snapshot **2025-01-01**. Đọc DDD §4–8, §12, §15; assessment-pilot.v1.1;
Article22 PDF mapping v1 và bundle `staging/article22-pdf-004/`. Không sửa
schema DDD hoặc các bundle/đường chạy Stage 1–5A đã có. Giới hạn không promote
trong các contract cũ là lịch sử; yêu cầu mới cho phép **draft**, chưa release.

## Quyết định triển khai về review có phạm vi

DDD `extraction.review_status` thuộc cả artifact của file, chưa có enum/trường
để mô tả review một phần. DQ-03 đòi extraction verified cho target/context
được phục vụ. Schema đồng thời có corpus.status=draft và extraction pending.
Do đó giữ nguyên schema và mọi extraction **pending**, lưu review theo spans
ở sidecar. Có thể nạp draft cùng unit_assessment có quyết định thật; không
coi quyết định hiệu lực của unit là xác minh toàn artifact extraction.

Không thêm verified_scoped vào enum, không gán verified toàn file, không tạo
extraction cắt đoạn giả để né nghĩa cấp file. DQ-03 vẫn chưa đạt để phát hành.
Sau này muốn phục vụ phải giải quyết biểu diễn/phạm vi verification bằng một
quyết định thiết kế được công bố hoặc review extraction phù hợp; bước này chỉ
nhập draft và không bắt người rà xác nhận toàn file từ vùng nhỏ.

## Hồ sơ review

CLI `src.article22_draft review-pack` replay/check mapping-004 và sao nguyên
input thành mapping_snapshot trong run mới. Context chứa sáu nút/8 spans,
hai PDF và capture thật; bộ này khóa binding riêng gồm mapping manifest/hash,
mapping binding, units/spans, catalog và code/schema. DOCX chỉ ở snapshot
đối chiếu, không làm nguồn corpus draft. Không mang quyết định DOCX sang PDF.

Catalog gắn mọi evidence với artifact/hash và thời điểm capture khi có:

`accessed_at` của span/ảnh dẫn xuất là thời điểm capture **PDF nguồn** được
liên kết, không phải thời điểm tải ảnh từ mạng hoặc ngày review. Ảnh trang 21
được render kỹ thuật trong run mới, không tạo sự kiện thu thập nguồn lịch sử.

- Hai file PDF, metadata công bố có liên kết nguồn và thứ tự phần.
- Tám source_span; ba spans cha document/Chương II chỉ chứng minh cấu trúc.
- Bốn lát căn cứ Điều 88/89 trên PDF phần tiếp trang 58–61.
- BRD §3.1/§3.3 cho scope.
- Ảnh trang 21 của PDF phần đầu. Mapping-004 chưa chứa ảnh được khóa cho
  warning này: render một ảnh vào run review mới là bổ sung cụ thể duy nhất.
  Không tải thêm nguồn. Agent quan sát thông tin xuất bản dạng nét, nằm ngoài
  tám spans, chưa OCR hoặc resolve warning. Reviewer ghi ảnh hưởng thực tế.

Review.md trình bày nguyên văn, spans/locator/hash, phần đã kiểm kỹ thuật và
chưa kiểm, căn cứ hiệu lực và giới hạn tra cứu. Đã kiểm 832 code point ở
trang 1/10/19 bằng mapping; chưa đối chiếu toàn bộ 21/61 trang. Bốn unit dùng
title/đoạn dẫn Điều 22 và Khoản 1–3; không biến cha thành target/context.
Lịch sử tra cứu cũ chưa toàn diện; bản hợp nhất 2026 chỉ là đầu mối sau snapshot.
Không suy không có sửa đổi từ việc chưa thấy trong nguồn đã lưu.

## Mẫu và quyết định thật

`decision_template.md` là phiếu đọc/ghi nháp; `decision_template.json` là tệp
CLI nhập. Sao mẫu ra ngoài bundle trước khi điền để giữ checksum input.
Mẫu giữ reviewer_ref/reviewed_at và mọi status/note là null;
record_status=unfilled_no_decision; không có quyết định mặc định.

Reviewer điền reviewer_ref và thời gian rà thực tế UTC (Z); nguồn/phạm vi
đã xem; các ô kết luận và bằng chứng đã thực tế xem. Suggested refs/proposals
không phải evidence đã xem hoặc quyết định. Đổi record_status=submitted khi
gửi hồ sơ thật; các ô vẫn null thì tiếp tục thiếu. Không cần tự tính ID/hash.

Source review: accepted/needs_fix, note và evidence_refs. Accepted đòi hai
PDF/metadata, các spans cha và ảnh warning; chỉ xác nhận đúng nguồn/phần và
vùng đã xem, không toàn nội dung file. Needs_fix có thể chỉ trích bằng chứng
vấn đề, không bắt đã xem hết các mục còn lại. Lịch sử source có chuỗi riêng.

Mỗi unit có ba chiều độc lập:

| Chiều | Kết quả | Nội dung cần ghi |
|---|---|---|
| technical | accepted/needs_fix | Own fields/spans đã rà và vấn đề nếu có. Accepted cần đủ own spans; needs_fix có thể chỉ trích span gặp vấn đề. |
| scope | supporting/included/excluded | Lý do, own fields và BRD. Đề xuất supporting Điều 22, included ba Khoản; reviewer được chọn khác. |
| applicability | Các enum DDD | Ngày, quote/căn cứ, historical_basis/history_note/content_note thực tế. Khác pending_review cần căn cứ chính thức và giải thích lịch sử/ngoại lệ trong phạm vi đã rà. |

Compiler chỉ biến ô đã điền trong submission thực tế thành event. Định danh
event canonical SHA-256; binding/unit_sha256/refs được kiểm, không lấy proposal
làm decision. Dùng lại decision_errors v1.1 cho unit events; dates chỉ phải
hợp lệ/khoảng ngày đúng snapshot, không ép theo ngày máy. Reviewer khác
proposal được ghi proposal_relation=override với lý do từ note và bằng chứng;
không đổi code/policy. Technical/applicability/scope không kế thừa nhau.

History nhập bằng `--history FILE.json` có source_events/unit_events. Bản
submission mới giữ nguyên byte; compiler ghi history mới ở run mới.
Supersedes theo (unit_id, dimension), source riêng. Một chiều mới không xóa
chiều khác. Kiểm thời gian UTC thật, không trước evidence/extraction đã trích;
không bịa danh tính, chữ ký, thời điểm tải hoặc ngày lịch sử.

## Điều kiện và dữ liệu nhập draft

Đây là nhập nguyên tử tập con bốn unit + dependencies. Chỉ tạo corpus khi:

1. Source review accepted theo đúng binding/phạm vi.
2. Có quyết định scope cho bốn unit; excluded cũng là quyết định hợp lệ.
3. Technical bốn unit accepted; needs_fix được lưu nhưng còn chặn nhập.
4. Có kết luận applicability khác pending_review cho bốn unit, bằng chứng và
   ngày hợp lệ. Không ép kết luận thành verified_at_snapshot; not_yet_effective,
   expired_at_snapshot hoặc not_applicable có căn cứ vẫn là dữ liệu draft.

Nếu chưa đủ, vẫn lưu history/tiến độ/các blocker cụ thể, không tạo content.sqlite,
corpus.jsonl hoặc các bảng DDD giả. Mẫu trống có đúng **13 ô còn thiếu**:
1 source + 4 unit × 3 chiều. Hoàn thành một chiều không tự hoàn thành chiều khác.
File thiếu/sai binding là lỗi input; ô null hợp lệ là thiếu quyết định.

Khi đủ, dùng schema.sql nguyên byte, FK ON, nạp:

- legal_document/source_file/extraction thật từ mapping; refs được chuyển
  sang review_pack/mapping_snapshot trong run draft mới, hash/ID không đổi.
- 6 legal_unit và 8 source_span; cha nạp trước con. Hai cha không có
  unit_assessment vì chỉ cấu trúc, không được chọn target/context.
- corpus version dạng traffic-20250101-vMAJOR.MINOR.PATCH do lệnh nhập chỉ rõ,
  status=draft, built_at là thời gian chạy thật, metadata/config/coverage/manifest.
- corpus_document chỉ Luật 36; usage_role phản ánh nội dung được chọn cho
  draft. Không đọc membership thành kích hoạt truy hồi.
- 4 unit_assessment từ quyết định thực tế. Verification_ref trỏ event trong
  decision_history.json, event liên kết catalog/quote/locator/hash. Reviewer_ref/
  verified_at lấy từ event applicability, decision_note giữ ID ba chiều/source.
- Không chunk, chunk_context hoặc index. document_count=0 theo DDD vì chưa
  có chunk mục tiêu; registered_document_count=1 ghi riêng số văn bản đã nạp.

scoped_review_uses.jsonl chỉ mô tả phạm vi review, không serving candidates.
Ba Khoản cần title/đoạn dẫn Điều 22 theo dependency cụ thể. Nếu reviewer loại
Điều 22 khỏi context, không sửa scope/hiệu lực các Khoản; đánh dấu phạm vi
dùng phụ thuộc này chưa đủ. Không dùng quy tắc kế thừa trạng thái chung.
Mọi serving_eligible/release_eligible đều false do file extraction pending
và chưa có bước release; thiếu chunk cũng không thể đọc serving_chunks.

## CLI, validator và fixture

- review-pack: tạo mẫu/hồ sơ mới, rc=0; chưa có quyết định.
- admit: nhận review manifest, decisions, corpus-version và run mới.
  rc=0 khi tạo draft; rc=2 khi thiếu/quyết định đang deferred/needs_fix;
  rc=1 khi input/binding/evidence/constraint lỗi, không tạo output cho input sai.
- validate: readonly, kiểm checksum/artifact set/code binding, replay mapping,
  catalog/template/events, policy/coverage, schema/FK/IDs/spans/SQL/JSONL;
  rc=0 cho draft hợp lệ, rc=2 cho run bị chặn hợp lệ, rc=1 cho artifact sai.

Không có lệnh freeze/activate/force-verified. Frozen DB, file extraction bị
gán verified, vùng cha bị thêm vào target/context, quyết định/hash sai và
manifest thay đổi sau reseal đều có kiểm replay. Manifest không phải chữ ký
mật mã hoặc bằng chứng xác thực người ký; không thêm yêu cầu phân quyền mới.

Fixture cô lập chỉ có law_id bắt đầu FIXTURE/, corpus version fixture-...,
và cần --allow-fixture. Không có nhánh CLI dùng fixture để chấp nhận luật thật.
Fixture mô phỏng provenance/extraction để thử adapter/DDD; không kiểm chất
lượng reader PDF và không chứng minh luật thực tế đã đúng. Output fixture
và source simulated luôn nằm trong staging riêng, không trộn corpus thật.
