# Phiên 17 · Chẩn đoán BM25 v6 và đối chiếu v5

Đánh giá đúng năm query thuộc phạm vi đã chấm, với snapshot sản phẩm 2025-01-01. Cả v5 và v6 có 50 vị trí Top‑10, tất cả đều nối được đúng một nhãn accepted theo cặp query–record. Pool dùng cho IDCG gồm 53 cặp v5 và 54 cặp v6. Tập chỉ mục tương ứng có 138 và 139 target.

| Chỉ số macro | v5 | v6 | Δ v6 − v5 |
|---|---:|---:|---:|
| Direct Precision@10 | 0,100 | 0,120 | +0,020 |
| Direct Hit@10 | 0,600 | 0,800 | +0,200 |
| Direct MRR@10 | 0,400 | 0,450 | +0,050 |
| Useful Precision@10 | 0,220 | 0,240 | +0,020 |
| Useful Hit@10 | 1,000 | 1,000 | 0,000 |
| Useful MRR@10 | 0,900 | 0,900 | 0,000 |
| nDCG@10_pool | 0,642149 | 0,657879 | +0,015730 |

Chỉ query đèn đỏ đổi điểm. Target A6K9b được thêm riêng trong v6, nằm ở hạng 4 và mang nhãn `2/direct_target/partial`. DCG@10 của query này tăng từ 0,630930 lên 1,922959 vì gain 3 ở hạng 4. IDCG tăng từ 1,630930 lên 4,130930 vì pool có thêm một cặp relevance 2. nDCG tăng từ 0,386853 lên 0,465503. Mức tăng nằm trong phép so sánh có thay đổi tập target, với cùng thiết lập BM25. Useful RR@10 giữ 0,5 vì hit Useful đầu tiên vẫn ở hạng 2.

Target tuổi lái mô tô giữ hạng 15 ở cả hai run sâu đã lưu. Required-read tăng từ 2 lên 16, bổ sung căn cứ về hạng GPLX và loại phương tiện. Vị trí ngoài Top‑10 làm Direct RR@10 của query này giữ 0.

V3-D05 giữ hàng V = 60 ứng với 35 m ở hạng 2. V3-D07 giữ hai hàng 60 < V ≤ 80 ứng với 55 m và 80 < V ≤ 100 ứng với 70 m ở hạng 2 và 3. Căn cứ trên từng hàng giữ điều kiện mặt đường khô ráo, tầm nhìn bảo đảm và nhãn `partial`. Hit hạng 1 của hai query đi qua dependency. Query còi ban đêm giữ nguyên thứ tự record ID và chuỗi nhãn Top‑10, với hai Direct ở hạng 1 và 2.

Provenance v5 ghi người dùng rà có AI hỗ trợ. V6 ghi người dùng tiếp nhận đề xuất AI, với `independent=false` và `blind=false`. Hai pending V3-D02 và sáu accepted v5 ngoài pool nằm ngoài phép tính. Recall, AP, MAP toàn corpus và metrics chính thức 50 query giữ `null`. Kết quả chỉ hỗ trợ chẩn đoán năm query, với trạng thái xác minh pháp lý của nguồn tiếp tục pending.

## Artifacts và bằng chứng

Đầu ra nằm tại `staging/subset-v6-five-query-evaluation-001/`. `results.md` có bảng đầy đủ Precision@1/3/5/10, Hit@10, RR@10, macro MRR@10, DCG, IDCG, nDCG và delta. Hai tệp Top‑10 giữ rank, record type, nhãn, lý do và evidence. Các bảng máy đọc gồm `metrics.per_query.jsonl`, `macro.delta.json`, `case_checks.json` và `report.json`. Manifest SHA-256 là `8ee65e51040e0ca2100b085346254801d243d6d9009e82327b7d15a7978114ae`.

Manifest ghim bảy artifact đầu vào, review core, dataset, index và bộ query. Adapter kiểm cùng query ID, payload và SHA-256 giữa hai phiên bản. Với v6, nó đối chiếu thêm hash của từng full-read và record payload giữa bảng batch, chi tiết trong packet và nhãn accepted. Tính lại các kết quả v5 và so với payload phiên 11.

- Validator gốc của evaluation phiên 11, aggregate v5 và accepted v6 đều exit 0.
- CLI phiên 17 build và validate exit 0. Replay khớp SHA-256 cho cả 11 tệp, gồm manifest và sidecar.
- Validator phiên 17 chạy thành công khi sáu hàm nạp index, tìm kiếm, xếp hạng và tạo engine bị gắn chốt báo lỗi nếu được gọi.
- Kiểm tra độc lập bằng phân số cho P/Hit/RR và `math.fsum` cho DCG/IDCG/nDCG đạt trên 10 dòng phiên bản–query, cùng hai bộ macro.
- 40 tests đạt, 0 skip và 0 lỗi. Có test trên artifact phiên 11 và các ca nhãn thiếu, nhãn trùng, binding/hash sai, dependency-only và IDCG bằng 0.
- Kiểm tra bảo toàn đối chiếu SHA-256 của file có sẵn, gồm nhãn, qrels, raw, dataset, index và worktree Hùng. Kiểm `git diff --check` và đầu/cuối Git ở receipt.

Receipts, kết quả kiểm độc lập và bảng hash chạy lại nằm trong `staging/source-session17-checks-001/`. HEAD đầu phiên là `b24ee8f23b0485810c1134858f451c045fc6ecfa`. Git đầu phiên sạch trên nhánh `feature/data-pipeline-huy`.

## Tái chạy từ thư mục gốc

```powershell
$py = '.\.venv-stage1\Scripts\python.exe'
& $py -X utf8 -B -m src.subset_evaluation validate --manifest staging/subset-v5-five-query-evaluation-001/manifest.json
& $py -X utf8 -B -m src.query_labels validate-aggregate --manifest staging/subset-v5-label-aggregate-001/manifest.json
& $py -X utf8 -B -m src.v6_acceptance validate --packet staging/subset-v6-binding-review-008 --capture staging/subset-v6-response-capture-001 --accepted staging/subset-v6-accepted-labels-001
& $py -X utf8 -B -m src.subset_v6_evaluation build --run-dir staging/subset-v6-five-query-evaluation-NEW
& $py -X utf8 -B -m src.subset_v6_evaluation validate --manifest staging/subset-v6-five-query-evaluation-001/manifest.json
$env:VTLS_FIVE_QUERY_EVAL_MANIFEST = 'staging/subset-v5-five-query-evaluation-001/manifest.json'
$env:VTLS_FIVE_QUERY_EVAL_CHECKS = 'staging/source-session17-tests-NEW'
& $py -X utf8 -B -m unittest -v tests.test_subset_v6_evaluation tests.test_subset_evaluation tests.test_evaluation
```

Chọn đường dẫn `NEW` chưa tồn tại. Lệnh `build` ở đây tạo artifact đánh giá từ rank đã lưu.
