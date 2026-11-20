# Phiên 15 — binding v5/v6 và gói review năm query

Ngày thực thi 2026-11-18; snapshot2025-01-01. Origin=agent_review. **PREPARED / NOT ACCEPTED / NO NEW METRICS**.

HEAD đầu/cuối phiên `b19452367cbea036d3949e0cdb05b35ff14a7115`, Git đầu phiên sạch. Khác HEAD phiên14; đã đọc trạng thái thực tế. Bảo toàn worktree Hùng và các input đã seal. Đọc AGENTS, contract/handoff labels/aggregate/five-query evaluation và báo cáo10–11, candidate13, BM2514/quickstart/deepchecks cùng code/config/manifest thật.

## Đầu vào được ghim

| Input | SHA256 |
|---|---|
| dataset — staging/dataset-v6-gap-002/dataset_manifest.json | 47b23b4f8742a308f32b4c1efd0d7749a81a8aae792459b95e7035490802bdfc |
| index — staging/bm25-subset-v6-001/index_manifest.json | 58c05ef0f6c2bb39d4a6af8d62d5520843c028e538a0b5d8abeb2ce5d3589c5f |
| batch — staging/bm25-subset-v6-batch-001/manifest.json | 43cda4d3c35b416c56d8c7da1bdefbec2e2ab1a8910b04c574d54a75d649bef2 |
| comparison — staging/bm25-v5-v6-comparison-001/manifest.json | 67f9fc847bf6e19c023d1d3bd3e53d81f7b4761d8f26ce0d3cfbdfda4c4cdfda |
| aggregate — staging/subset-v5-label-aggregate-001/manifest.json | 7c4dbee482e5bc7d38e96b12e4a75684b3756a47b48d4385c713e2fd846cd56e |
| v5_review — staging/subset-v5-query-review-002/manifest.json | 04ad32955c1443aedcc7b6f6f82e4e63e1bcd9a8adfe903159ff93463444b2f2 |
| evaluation — staging/subset-v5-five-query-evaluation-001/manifest.json | 71b249f6626120cf2137ab86675874f6e6131438758df8ca64e9faa0dbbff4d1 |
| evaluation_config — config/subset_five_query_evaluation.v1.json | 2479c09fc22b497bb9a17eb4da8dbb3efe7721645ba6dbee610b1742a78d91ed |
| v14_config — config/source_session14.v1.json | c962d0e4ebabd6787cef09384e84f64cdc42c55099c5e0247fbfdb77f268204e |



Dùng consumer v6 cấp gốc; kiểm139target/250supporting/1form/6views theo schema đã chốt. Validator aggregate v5 được tái sử dụng qua subset_evaluation.inputs; chỉ gọi input/evidence validation, không gọi metric functions. Giữ59accepted duy nhất/2pending, toàn receipt/metadata/reason/evidence/provenance;53 thuộc pool5query,6ngoài scope chỉ inventory. Pending CAL-a46415f601/CAL-b69c61257d vẫnV3-D02/null, không nằm trong template.

Không gọi ranking hoặc build index. Query/rank/score lấy từ frozen batch, comparison phiên14 kiểm lại bằng top_delta từ payload có seal; toàn50 vẫn1Top1/13Top10đổi theo dữ liệu ghim. Trong5query: 0 Top1 đổi và 2 danh sáchTop10 đổi. Không dùng Markdown làm bằng chứng hoặc đánh giá chất lượng.

## Kết quả pool và disposition

Hợp Top10 v6 + accepted v5 còn target + known positive ngoàiTop10, khử trùng query–record. **54cặp /42record duy nhất**, không ép bằng53. Giữ target tuổi ngoàiTop10; chỉ thêm cặp đèn đỏ đúngquery. Không đưa diagnostic139, supporting unit/form/view thành cặp target.

| Query | Pool | A | B | C | D | Quyết định cũ | Accepted v6 |
|---|---:|---:|---:|---:|---:|---:|---:|
| dev-night_horn-3 | 10 | 10 | 0 | 0 | 0 | 10 | 0 |
| dev-driving_age-2 | 12 | 11 | 1 | 0 | 0 | 12 | 0 |
| dev-red_light-2 | 12 | 11 | 0 | 1 | 0 | 11 | 0 |
| V3-D05 | 10 | 10 | 0 | 0 | 0 | 10 | 0 |
| V3-D07 | 10 | 10 | 0 | 0 | 0 | 10 | 0 |



**52 A:** payload/text_for_search/context/membership/closure/supporting/sourceproof facets bằng nhau sau khi consumer đã resolve và kiểm bytes. Chỉ bỏ package_locator khi so proof; không bỏ original raw/extraction IDs/hash, offsets, quote, cells/header/điều kiện. Response hash đổi do dataset/adapter/package wrapper không bị coi là nội dung đổi. Proposal giữ exact label/relation/completeness/reason cũ trên binding mới để người dùng xác nhận, không accepted tự động.

**1 B — tuổi:** payload/ID/context không đổi nhưng membership required IDs và proof/closure2→16 đổi. Proposal tạm giữ2/direct_target/partial, có evidence mới16reads; không sửa lý do lịch sử hoặc tự nâng full. Phân biệt A1/A/B1, mô tô/xe gắn máy, điều kiệnGPLX. B cần người dùng rà riêng, không nằm trong danh sách xác nhận A.

**1 C — đèn đỏ:** A6K9b có own target mới, unit trước đó chỉ là dependency v5. Prototype proposal2/direct_target/partial dựa nguyên văn hành vi, title đúng ô tô, leadKhoản9 và7reads về trừ điểm/gây tai nạn; không dùng rank4 suy nhãn/full. Không tạo oldchunk giả cho unit trước kia unranked.

**0 D:** chưa có blocker thiếu bằng chứng tương đương trong pool đã chọn. Không đồng nghĩa toàn nguồn/edition/applicability verified hoặc pool bao phủ mọi positive.

Tất cả53oldpair còn target v6 và có disposition, không có target cũ bị mất. Các pair rờiTop10 vẫn giữ trongpool qua accepted; pool.old_top10/v6_top10 tách trạng thái ranking khỏi membership. member_role kiểm target theorecord_id, dependency theounit_id. Chín hàng bảng/whole-source giữ đúngtype; encoder views không được rank nhưtarget.

Khoảng cách giữ V=60/35m,60<V≤80/55m,80<V≤100/70m cùng header/điều kiện. Hai hàng2/partial cũ không tự đủ so80/81; whole-source dependency-only1 không nângdirect. Không thay accepted completeness hoặc applicability bằng dữ liệu mới.

## Gói người dùng rà

Bản giao **staging/subset-v6-binding-review-008/**;009 là replay. Các run001–007 giữ lịch sử, không dùng làm đầu vào latest.002 bị chặn bởi giả định sai rằng mọi record phải có source_proofs ngoài cùng. Bốn hàng bảng khoảng cách dùng cells/source_slices/context; đã bổ sung kiểm hash/offset/quote từng ô theo extraction gốc, không tạo proof giả hoặc bỏ kiểm tra.004/005 là checkpoint trước khi làm rõ namespace membership;006/007 trước sửa định dạng bảng Markdown;008/009 là bản cuối.

- review/OVERVIEW.md: tiến độ và liên kết năm phiếu; review/sheets/: câu hỏi nguyên văn, target/context/cells, quyết định/lý do cũ, proposal và EV6 IDs, required-read đầy đủ và chỗ để người dùng trả lời.

- review/pool.jsonl, disposition.jsonl, retrieval_deltas.five.jsonl: từng pair/nhóm, facets và nguồn pool, before/afterTop10. Không chỉ so payload hash để bỏ qua closure.

- review/history/:53historical annotations nguyên object và rowhash,6outside inventory,2pending inventory/receipt/provenance giữbindingv5. Không tạo event nhận lại.

- review/details/ và evidence/:42typed full responses và nội dung đọc đầy đủ; source_assets.json/proof_assets giữ20mounts raw/extraction/trace cần dùng. Bản raw đầy đủ chỉ là chứng cứ cho selected slices, không là review toànfile.

- review/equivalence_list.jsonl: danh sách exact52cặp A + quyết định cũ + evidence. templates/submission.template.json:54item, reviewer_ref/reviewed_at/outcome/labels/reason/evidence-used đều trống; group confirmation cũng chưa có.

Đây là proposal-visible/AI-assisted, không independent/blind. Khi người dùng phản hồi, chỉ điền metadata/sự kiện thật và EV6refs đã dùng, bản sao ngoài bundle seal. NhómA có thể confirm exactlist; B/C rà riêng. validate-response chỉ kiểm draft, accepted_created=0/import_supported=false; chưa có admitv6 hoặc qrels/metricsv6.

## Manifest, ZIP và replay

| Thành phần | Giá trị |
|---|---|
| Review core manifest SHA | 343956e65fd82a3834ecb3059833ad3b31b7575486fc6d5eb3749c791c8af53a |
| Packet manifest SHA | 4b00216317afe4ee1532b867105f969e09988d0ab8e46a13dca80566dfbf7857 |
| ZIP | staging/subset-v6-binding-review-008.zip |
| ZIP SHA | 3f1c975ab6758474e01487824f440f4ed01b68488e2ad4646b1cbfec28192cd5 |
| ZIP bytes | 11344945 |

Template pin coremanifestSHA và pool/query/record/full-read/proposal hashes; manifest cấp gốc seal cả core+template+validator. Cấu trúc hai tầng tránh vòng tự hash. ZIP SHA bảo vệ toàn gói; chưa có URL chia sẻ.

Replay008→009: **134files**, tất cả manifests/sidecars giống byte, ZIP giốngSHA. agent_recorded_at lấy thời điểm kỹ thuật capture trongconfig, không ngày tải nguồn hoặc thời gian reviewer. Không lựa run latest hoặc sửa seal cũ.

## Kiểm chứng và lệnh thực thi

- Build008/009 và CLI validate-delivery đều exit0, khởi tạo lại từ pinned inputs/consumer; không lấy file report cũ làm bằng chứng thay validator. Validate so bytes toàn output tái dựng, gồm proposal/MD/template/evidence/historical rows.

- Tests lần đầu32:25pass/7skip; hồi quy fixtures pool/template/acceptance. Suite mới cuối **11pass/0skip** trên008. Không cộng các ca chạy lặp; phạm vi hồi quy lịch sử có16pass/7skip (1query-review artifact opt-in và6acceptance real opt-in không bật vì không làm phiên nhậpnhãn). Aggregate59/2 vẫn được validate thực trongbuild/validate.

- **13resealed mutations** bị từ chối: duplicatepair, wrongdataset/index, mấtolddisposition, bỏquaclosuretuổi, fakehuman/accepted, kếthừareviewed_at, thiếuevidence/Top10, supportingthànhtarget, thiếudependency và sai celloffset. Fixtures kiểm package locator-only=A, rawhashđổi≠A, cùngpayload nhưngclosuređổi=B, pointer remap theounitID và namespacechunk/unit.

- Feedback fixture kiểm metadata thiếu, confirm_list chỉ gồmA, pendingnull không thành0, saiIDs/binding/duplicate/unknownacceptedfields. Fixture metadata FIXTURE-ONLY ởtemp, không ghi artifact accepted/human event thật.

- ZIP giải nén thư mục mới, chạy integrity và blank-response bằng Python -I -S -B chỉstdlib. HaiCLI exit0, 54unconfirmed/0decision/0accepted. Cùng Windows/CPython3.11.9; chưa máy/OS khác và không auditgate riêng ởphiên15. Portablevalidator không thay consumer semantic replay hoặc legalreview.

```powershell

.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.binding_review build --config config/subset_v6_binding_review.v1.json --run-dir staging/subset-v6-binding-review-NEW

.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.binding_review validate --packet staging/subset-v6-binding-review-008

.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.binding_review zip --packet staging/subset-v6-binding-review-008 --output staging/subset-v6-binding-review-NEW.zip

$env:VTLS_V6_REVIEW_PACKET='staging/subset-v6-binding-review-008'

.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest -v tests.test_binding_review

```

NEW phải chưa tồn tại. [Handoff](../handoff/Subset_V6_Binding_Review.md) có hướng dẫn điền bản sao/validate-response và portablecommands. Không chạy admitv5 cho dữ liệu v6.

## File thay đổi, preservation và giới hạn

Thêm src/binding_review.py (adapter hữu hạn), src/binding_review_packet.py (stdlib validator cho ZIP), config ghim, tests và contract/handoff/report. Tái sử dụng validators/renderer/pool/rubric, không thay framework hoặc DDD schema. STATUS prepend trạng thái hiện tại, lịch sử giữ byte.

Baseline **8709file** gồm raw, v5/v6dataset/index/query/labels/qrels/ZIP, code/tài liệu có trước và worktreeHùng. Preservation.final.json/git.final.json kiểm cuối; chỉ STATUS được phép prepend, HEAD/staged giữ nguyên. Không reset/clean/stash/stage/commit/push/merge.

Không metrics mới, acceptedv6, chuyển59labels/qrels, sửareason/completenessv5, tuning/retrieval/rebuild/model/UI/API hoặc thay ứng dụng Hùng. Snapshot2025-01-01, source/edition/applicability pending, scopeproposal. Technicalequivalence không legalverified và không bảo đảm toànpositive corpus. Phần còn thiếu là **phản hồi thực tế** cho54cặp (hoặc exactlistA và riêngB/C) cùng metadata/evidence đã dùng; sau đó mới chuẩn bị phiên nhậpv6 được yêu cầu riêng.
