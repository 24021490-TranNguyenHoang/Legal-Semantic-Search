# BM25 v6 experimental — contract phiên 14 v1.0

Kế thừa contract BM25 phiên6 về engine/tokenizer/query/filter/tie/projection/read. Adapter mới `src/subset_bm25_v6.py`, index vtls-bm25s-subset.v2; datasetv6 root consumer,139targets (126/9/4), supporting250/form1/views6. Không sửa v1 runtime hoặc dùng base/consumer.py giả đọc v6. Config ghim manifest47b23b4… và ZIP8c9f3a5…, consumer/content/query/frozen algorithms; preflight validate trước tạo output.

Version adapter mới cần vì membership và consumer/root bindings thay đổi. Các hàm projection/mapping/query/search/read và algorithm giữ semanticsv1, recipe vẫn subset-text-for-search.v1. Không thêm closure vào encoder/search text, không chuyển views thành target. Inventory index sort theo relative POSIX string rõ ràng để Windows/POSIX nhất quán, khác sort Path phụ thuộc platform của v1. Không sửa v1 artifact.

Batch50query ghim30+15+5, nguyên IDs/text/thứ tự/top_k10; diagnostic139 riêng. Kết quả so sánh là hành vi retrieval, score có thể đổi do corpus stats, không metrics relevance. Age target giữ payload/ID nhưng closure2→16; red target thêm closure7. v5 frozenrun/hash giữ nguyên, replayv5 dùng v1 riêng. Accepted59/pending2 không transfer.

Manifest pins runtime/dependency/algorithm/source/dataset/query/inventory. Load kiểm integrity+projection và engine; validate replay matrix; fullread bằng rootconsumerv6. Read envelope giữ type/source/proof/context/closure và response hash; foreign/missingID/capability/dependency bị từ chối. No fallback/resealinput. Replay so payload/matrix/rank/score/readsignature, loại timestamp/timing khỏi signature. ZIP chứa mọi dependency nội dung, runtime source/config/query và lockdependency; không model/cache/venv. Audit gate chỉ cho bundle/stdlib/venv/output/harness, chặn repo/cache/network. Kiểm thực Windows/Python ghi receipt; không suy Linux từ POSIX sort hoặc kiểm consumer cũ.

Experimental/releasefalse/corpusnull/source-edition-applicabilitypending/scopeproposal, originagent_review, human events0. Không indexactivation/UIintegration/labels/metrics/tuning.
