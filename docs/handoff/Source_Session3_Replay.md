# Replay phiên 3 — source selection / membership proposal

Snapshot2025-01-01. Đây là proposal pending/experimental, không dataset build,
không serving hoặc legal verification. [Báo cáo](../reviews/Source_Session3_Verification.md),
[contract](../design/Source_Session3_Membership_Contract_v1.0.md).

Run bàn giao `staging/source-session3-proposal-009/`; replay010. Config
`config/source_session3.v1.json` chứa đúng input refs/hash và128scope reviews
với unit SHA; không tìm run mới nhất. User instruction nguyên byte được giữ ở
`staging/source-session3-001/user_instruction.txt`; đó là căn cứ lựa chọn source,
không human review từng unit. Đã kiểm HEAD2afb65c, Git sạch đầu phiên.

## Mở dữ liệu

- `source_selection.jsonl`:7nguồn,12file đã chọn, SHA/file_id/part_order và extraction.
- `membership.proposals.csv/.jsonl`:5375node, từng chiều trạng thái/lý do/proof.
  JSONL có nguyên văn và candidate refs; `membership_review.md` tập trung phần đã rà.
- `table_row.membership.proposals.csv/.jsonl`:9typed table row TT38, không duplicate owner.
- `nonunit.membership.proposals.jsonl`:forms/annex/source regions riêng, không text targets.
- `tt35_owner.decisions.csv/.jsonl`:8ca; A7đổiAnnexIII→II có sourceproof,6bảng
  supporting choA28K2,2bảng excluded. TargetA28K2vẫn pending formXXIII/PDF127.
- `table_owner_reads/*.json`:toàn record, nguồn, cells và mọi required dependency.
- `nd168.phase1_to_phase2.jsonl`, `nd168.legacy_branch_mapping.jsonl`,
  `nd168.span_crosswalk.jsonl`:phân biệt nguồn/định danh; không copy qrels/assessment.
- `dependencies.jsonl`, `v3.comparison.jsonl`, `v4.comparison.jsonl`,
  `law36.lead_checks.jsonl`, `law35.table_checks.jsonl`, `qcvn.remaining.jsonl`.

## Chạy từ thư mục repository

Windows/Python3.11.9, môi trường `.venv-stage1` đã cài theo README. Không yêu cầu
weights, inference hoặc OCR. Dùng caches/artifacts đúng config; clone code không
tự có staging. Cần các nhánh Stage4DOCX, ND168 phiên1/2, HTML/v3/v4, priority006,
TT38preview003/tables003/views001, TT35preview005/full-layout001/source-regions001/
owner-tables002, QCVNgazette/native/graph003/recovery004, ledger009 và scope/pilot
cũ. Config/input manifests ghi hash cụ thể, thiếu dependency phải fail.

Các lệnh build dưới đây đã chạy; khi tái chạy **đổi output sang tên chưa có**
như `source-session3-proposal-user-001`, không ghi đè009/010.

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.membership_proposal build --config config/source_session3.v1.json --run-dir staging/source-session3-proposal-009
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.membership_proposal build --config config/source_session3.v1.json --run-dir staging/source-session3-proposal-010
```

Validate run đã seal, không ghi vào run:

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m src.membership_proposal validate --config config/source_session3.v1.json --run-dir staging/source-session3-proposal-009
```

Checker thực/negative/replay/preservation (output mới nếu chạy lại):

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m tests.check_session3_artifacts `
  --config config/source_session3.v1.json `
  --proposal staging/source-session3-proposal-009 --replay staging/source-session3-proposal-010 `
  --output staging/source-session3-checks-003
```

Tests đã chạy:

```powershell
.\.venv-stage1\Scripts\python.exe -X utf8 -B -m unittest tests.test_session3_membership tests.test_session2_sources tests.test_source_revision tests.test_full_ingestion tests.test_circular_dataset -v
git diff --check
```

41tests pass; không lấy fixture/số test làm chứng minh pháp lý. Negative cases
bao gồm source/proof/version/dependency/old-ID/duplicate DOCX–HTML/capability/
encoder-view/QCVN-conflict và table header/cell/proof. Replay so payload, không
so thời điểm build manifest. Bản kiểm cuối sau cập nhật docs ghi output riêng.

## Consumer table-owner preview

```python
from src.experimental_dataset import load
from src.ingestion.table_owner_adapter import TableOwnerConsumer
consumer = TableOwnerConsumer(load('config/source_session3.v1.json')['table_owner'])
record = next(r for r in consumer.records if '/article:7/' in r['owner_path'])
full = consumer.read(record['record_id'])
# full giữ required_dependencies và loaded_required_dependencies, gồm đúng AnnexII.
```

Không gửi riêng encoder view cho người dùng như target. Consumer composition v1
khóa hash giữ nguyên; adapter này chưa được tích hợp dataset/index/app. RecordID
A7vàwrapperviewID đổi vì required_dependencies/source SHA đổi, không đổi unit ID,
nguyên văn/search text/token IDs. Không tự bỏ source fields để vừa budget.

## Word và giới hạn

Đã tìm Word trong HKLM AppPaths và thử DispatchEx riêng/ẩn, mở copy read-only,
macro disabled. COM báo `-2147023584` do logon session; không có PDF render mới.
Receipt `staging/source-session3-word-001/render_probe.json`, nguồn DOCX nguyên
hash. Có thể render **bản copy** bằng Word/LibreOffice trên môi trường phù hợp
để rà bố cục; đây là kiểm tra còn thiếu, không tự coi là verified khi render được.

Không tải lại nguồn/extraction PDF, áp lại corrections, OCR toànQCVN hoặc đổi
dataset3077/draft3082/v3/v4/index/evaluation/qrels/ZIP. Chưa thử máy/OS khác.
Nguồn/edition/applicability pending được giữ riêng với technical/scope proposal.
