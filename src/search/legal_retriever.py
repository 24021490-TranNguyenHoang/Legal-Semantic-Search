import re
import json
import torch
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from transformers import AutoTokenizer, AutoModel
from qdrant_client import QdrantClient
from rank_bm25 import BM25Okapi

from src.config import QDRANT_PATH, COLLECTION_NAME, CHUNKS_FILE, EMBEDDING_MODEL_NAME

def simple_tokenize(text: str) -> List[str]:
    """Tách từ đơn giản bằng regex chuẩn hóa."""
    return re.findall(r"\w+", text.lower())

def mean_pooling(model_output, attention_mask):
    """Mean pooling cho embedding Bi-Encoder."""
    token_embeddings = model_output[0]
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
    sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    return sum_embeddings / sum_mask

# Từ điển tri thức giao thông: Ánh xạ tiếng lóng / từ đời thường -> Thuật ngữ pháp lý chuẩn
TRAFFIC_KNOWLEDGE_BASE = [
    {
        "patterns": [r"vượt đèn (đỏ|vàng)", r"đèn đỏ", r"đèn vàng", r"chạy đèn đỏ", r"vượt đèn"],
        "violation_name": "Không chấp hành hiệu lệnh của đèn tín hiệu giao thông (Vượt đèn đỏ / vượt đèn vàng)",
        "exact_phrases": ["hiệu lệnh của đèn tín hiệu giao thông", "hiệu lệnh của đèn tín hiệu"],
        "expanded_terms": ["không chấp hành hiệu lệnh của đèn tín hiệu giao thông", "đèn tín hiệu giao thông"],
    },
    {
        "patterns": [r"ngược chiều", r"đi ngược chiều", r"chạy ngược chiều", r"đường một chiều"],
        "violation_name": "Đi ngược chiều",
        "exact_phrases": ["đi ngược chiều của đường một chiều", "biển “cấm đi ngược chiều”", "cấm đi ngược chiều"],
        "expanded_terms": ["đi ngược chiều của đường một chiều", "đường có biển cấm đi ngược chiều"],
    },
    {
        "patterns": [r"sai làn", r"lấn làn", r"đè vạch", r"không đúng làn", r"lộn làn"],
        "violation_name": "Đi không đúng phần đường hoặc làn đường",
        "exact_phrases": ["không đi đúng phần đường hoặc làn đường quy định"],
        "expanded_terms": ["không đi đúng phần đường", "làn đường quy định"],
    },
    {
        "patterns": [r"rượu bia", r"nồng độ cồn", r"uống rượu", r"uống bia", r"say xỉn", r"say rượu", r"thổi cồn"],
        "violation_name": "Vi phạm nồng độ cồn",
        "exact_phrases": ["nồng độ cồn vượt quá", "trong máu hoặc hơi thở có nồng độ cồn"],
        "expanded_terms": ["nồng độ cồn trong máu hoặc hơi thở", "miligam/100 mililít máu", "miligam/1 lít khí thở"],
    },
    {
        "patterns": [r"quá tốc độ", r"bắn tốc độ", r"chạy quá tốc độ", r"phóng nhanh"],
        "violation_name": "Chạy quá tốc độ quy định",
        "exact_phrases": ["chạy quá tốc độ quy định"],
        "expanded_terms": ["điều khiển xe chạy quá tốc độ quy định", "km/h"],
    },
    {
        "patterns": [r"mũ bảo hiểm", r"nón bảo hiểm", r"không đội mũ", r"không nón"],
        "violation_name": "Không đội mũ bảo hiểm",
        "exact_phrases": ["không đội “mũ bảo hiểm", "không đội mũ bảo hiểm", "cài quai không đúng quy cách"],
        "expanded_terms": ["không đội mũ bảo hiểm cho người đi mô tô, xe máy", "cài quai không đúng quy cách"],
    },
    {
        "patterns": [r"điện thoại", r"nghe điện thoại", r"lướt điện thoại"],
        "violation_name": "Sử dụng điện thoại di động khi đang lái xe",
        "exact_phrases": ["sử dụng điện thoại di động", "thiết bị điện tử"],
        "expanded_terms": ["dùng tay cầm và sử dụng điện thoại di động", "thiết bị điện tử khác"],
    },
    {
        "patterns": [r"xi nhan", r"bật xi nhan", r"quên xi nhan", r"chuyển hướng"],
        "violation_name": "Không bật tín hiệu báo hướng rẽ (xi-nhan)",
        "exact_phrases": ["không có tín hiệu báo hướng rẽ", "chuyển hướng không có tín hiệu báo trước"],
        "expanded_terms": ["tín hiệu báo hướng rẽ", "chuyển làn đường không có tín hiệu"],
    },
    {
        "patterns": [r"kẹp ba", r"kẹp 3", r"chở 3", r"chở ba", r"chở quá số người", r"kẹp 4"],
        "violation_name": "Chở quá số người quy định",
        "exact_phrases": ["chở từ 03 người trở lên", "chở theo từ 03 người trở lên"],
        "expanded_terms": ["chở từ 03 người trở lên trên xe", "chở người ngồi trên xe"],
    },
    {
        "patterns": [r"không mang bằng", r"quên bằng", r"không có bằng", r"không mang giấy tờ", r"quên đăng ký"],
        "violation_name": "Không mang hoặc không có giấy phép lái xe / đăng ký xe",
        "exact_phrases": ["giấy phép lái xe", "giấy đăng ký xe"],
        "expanded_terms": ["không mang theo giấy phép lái xe", "không có giấy phép lái xe", "đăng ký xe"],
    }
]

# Từ khóa chỉ ý định hỏi chế tài xử phạt
PENALTY_INDICATORS = [
    r"phạt", r"bị phạt", r"mức phạt", r"tiền phạt", r"phạt tiền", r"bao nhiêu tiền",
    r"mấy tiền", r"trừ điểm", r"tước bằng", r"giam xe", r"tạm giữ", r"như nào", r"thế nào",
    r"bị xử lý", r"hình phạt", r"chế tài"
]

# Phân loại phương tiện
VEHICLE_PATTERNS = {
    "oto": {
        "pattern": r"ô tô|oto|xe hơi|xe tải|bốn bánh",
        "label": "🚗 Xe ô tô",
        "terms": ["ô tô", "xe chở người bốn bánh", "xe chở hàng bốn bánh"],
        "article_hint": "Điều 6"
    },
    "xe_may": {
        "pattern": r"xe máy|mô tô|xe gắn máy|hai bánh",
        "label": "🏍️ Xe mô tô, xe gắn máy",
        "terms": ["xe mô tô", "xe gắn máy"],
        "article_hint": "Điều 7"
    },
    "chuyen_dung": {
        "pattern": r"chuyên dùng|xe lu|xe ủi|máy kéo",
        "label": "🚜 Xe máy chuyên dùng",
        "terms": ["xe máy chuyên dùng"],
        "article_hint": "Điều 8"
    },
    "xe_dap": {
        "pattern": r"xe đạp|xe thô sơ|xe điện",
        "label": "🚲 Xe đạp, xe thô sơ",
        "terms": ["xe đạp", "xe thô sơ"],
        "article_hint": "Điều 9"
    },
    "di_bo": {
        "pattern": r"đi bộ|người đi bộ",
        "label": "🚶 Người đi bộ",
        "terms": ["người đi bộ"],
        "article_hint": "Điều 10"
    }
}

class LegalRetriever:
    def __init__(self):
        self.client = QdrantClient(path=QDRANT_PATH)
        self.tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL_NAME)
        self.model = AutoModel.from_pretrained(EMBEDDING_MODEL_NAME)
        self.model.eval()
        
        # Tải chunks
        self.chunks = []
        if CHUNKS_FILE.exists():
            with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        self.chunks.append(json.loads(line))
                        
        tokenized_corpus = [simple_tokenize(c.get("enriched_text") or c.get("text", "")) for c in self.chunks]
        self.bm25 = BM25Okapi(tokenized_corpus) if tokenized_corpus else None

    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Phân tích ý định người dùng và ngữ cảnh pháp lý."""
        q_low = query.lower()
        matched_violations = []
        exact_phrases = []
        expanded_terms = []
        
        # 1. Phát hiện hành vi vi phạm
        for item in TRAFFIC_KNOWLEDGE_BASE:
            for p in item["patterns"]:
                if re.search(p, q_low):
                    matched_violations.append(item["violation_name"])
                    exact_phrases.extend(item["exact_phrases"])
                    expanded_terms.extend(item["expanded_terms"])
                    break
                    
        # 2. Phát hiện ý định xử phạt
        is_penalty = any(re.search(p, q_low) for p in PENALTY_INDICATORS)
        if is_penalty:
            expanded_terms.extend(["xử phạt", "phạt tiền", "trừ điểm", "giấy phép lái xe"])
            
        # 3. Phát hiện phương tiện
        detected_vehicle = None
        vehicle_label = None
        for v_key, v_info in VEHICLE_PATTERNS.items():
            if re.search(v_info["pattern"], q_low):
                detected_vehicle = v_key
                vehicle_label = v_info["label"]
                expanded_terms.extend(v_info["terms"])
                break
                
        # 4. Tạo câu truy vấn mở rộng
        expanded_query = query
        if expanded_terms:
            expanded_query = f"{query} {' '.join(expanded_terms)}"
            
        return {
            "original_query": query,
            "expanded_query": expanded_query,
            "is_penalty": is_penalty,
            "matched_violations": matched_violations,
            "exact_phrases": exact_phrases,
            "vehicle_key": detected_vehicle,
            "vehicle_label": vehicle_label
        }

    def encode_query(self, query_text: str) -> List[float]:
        """Mã hóa truy vấn sang vector chuẩn hóa."""
        encoded_input = self.tokenizer(query_text, padding=True, truncation=True, max_length=256, return_tensors='pt')
        with torch.no_grad():
            model_output = self.model(**encoded_input)
        embedding = mean_pooling(model_output, encoded_input['attention_mask'])
        vector = embedding[0] / embedding[0].norm(p=2)
        return vector.tolist()

    @staticmethod
    def extract_fine_amount(text: str) -> Optional[str]:
        """Trích xuất khoảng mức phạt tiền từ nội dung điều khoản."""
        # Tìm regex dạng: Phạt tiền từ X đồng đến Y đồng
        m = re.search(r'Phạt (?:tiền|liền)\s+từ\s+([\d\.]+)\s*đồng\s+đến\s+([\d\.]+)\s*đồng', text, re.IGNORECASE)
        if m:
            return f"{m.group(1)}đ - {m.group(2)}đ"
        m2 = re.search(r'Phạt (?:tiền|liền)\s+([\d\.]+)\s*đồng', text, re.IGNORECASE)
        if m2:
            return f"{m2.group(1)}đ"
        return None

    @staticmethod
    def highlight_exact_violation(text: str, exact_phrases: List[str]) -> str:
        """Đánh dấu (highlight) điểm vi phạm cụ thể trong điều luật."""
        if not exact_phrases:
            return text
            
        # Tìm xem câu hoặc điểm nào trong text chứa phrase
        highlighted = text
        for p in exact_phrases:
            pattern = re.compile(re.escape(p), re.IGNORECASE)
            highlighted = pattern.sub(f"<mark style='background-color: #ffeb3b; padding: 2px 4px; border-radius: 3px;'>{p}</mark>", highlighted)
        return highlighted

    def search(self, query: str, top_k: int = 3, vehicle_override: Optional[str] = None) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Thực hiện tìm kiếm ngữ nghĩa kết hợp (Hybrid Retrieval + Legal Domain Rescoring).
        """
        analysis = self.analyze_query(query)
        expanded_q = analysis["expanded_query"]
        is_penalty = analysis["is_penalty"]
        exact_phrases = analysis["exact_phrases"]
        
        target_vehicle = vehicle_override if vehicle_override else analysis["vehicle_key"]
        
        # 1. Dense Retrieval (Qdrant)
        query_vector = self.encode_query(expanded_q)
        dense_response = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=50
        )
        dense_ids = [hit.id for hit in dense_response.points]
        
        # 2. Sparse Retrieval (BM25)
        tokenized_query = simple_tokenize(expanded_q)
        bm25_scores = self.bm25.get_scores(tokenized_query) if self.bm25 else []
        sparse_ids = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:50] if len(bm25_scores) > 0 else []
        
        # 3. Reciprocal Rank Fusion (RRF)
        rrf_scores = {}
        for rank, doc_id in enumerate(dense_ids, start=1):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (60 + rank)
        for rank, doc_id in enumerate(sparse_ids, start=1):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (60 + rank)
            
        # 4. Legal Domain-Specific Rescoring
        rescored = []
        for doc_id, rrf_score in rrf_scores.items():
            item = self.chunks[doc_id]
            text_content = (item.get("citation_path", "") + " " + item.get("original_text", "")).lower()
            score = rrf_score
            
            # --- Tiêu chí 1: Khớp chính xác hành vi vi phạm vi mô (Exact Phrase) ---
            exact_match = any(p.lower() in text_content for p in exact_phrases) if exact_phrases else False
            if exact_match:
                score *= 3.0
                
            # --- Tiêu chí 2: Khớp ý định tra cứu Mức phạt (Penalty) ---
            if is_penalty:
                is_sanction_chunk = "xử phạt" in text_content or "phạt tiền" in text_content or "168/2024" in item.get("law_id", "")
                if is_sanction_chunk:
                    score *= 1.5
                else:
                    # Giảm mạnh các điều khoản thuần quy tắc khi người dùng hỏi mức phạt
                    score *= 0.1
            else:
                # Nếu không phải hỏi phạt (VD: hỏi đèn đỏ là gì, xe ưu tiên gồm xe gì)
                # Ưu tiên các điều khoản Luật trật tự ATGT (36/2024) và Luật Đường bộ (35/2024)
                if "36/2024" in item.get("law_id", "") or "35/2024" in item.get("law_id", ""):
                    score *= 1.4
                    
            # --- Tiêu chí 3: Bộ lọc / Ưu tiên phương tiện ---
            if target_vehicle:
                v_info = VEHICLE_PATTERNS.get(target_vehicle)
                if v_info:
                    hint = v_info["article_hint"].lower()
                    terms = v_info["terms"]
                    has_vehicle = any(t in text_content for t in terms) or (hint in text_content)
                    if has_vehicle:
                        score *= 2.5
                    else:
                        score *= 0.2
            else:
                # Nếu người dùng không chỉ định phương tiện, nhưng có khớp vi phạm chính xác:
                # Ưu tiên các phương tiện phổ biến nhất: Xe máy (Điều 7) và Ô tô (Điều 6)
                if exact_match and ("điều 7" in text_content or "điều 6" in text_content):
                    score *= 1.5
                    
            rescored.append((doc_id, score, exact_match))
            
        rescored.sort(key=lambda x: x[1], reverse=True)
        
        # Chuẩn bị danh sách kết quả trả về
        results = []
        for doc_id, final_score, is_exact in rescored[:top_k]:
            item = dict(self.chunks[doc_id])
            item["score"] = final_score
            item["exact_match"] = is_exact
            item["fine_amount"] = self.extract_fine_amount(item.get("original_text", ""))
            
            # Gợi ý loại phương tiện của điều luật
            art_id = item.get("article_id", "")
            if "Điều 6" in art_id:
                item["vehicle_type"] = "🚗 Xe ô tô"
            elif "Điều 7" in art_id:
                item["vehicle_type"] = "🏍️ Xe mô tô, xe gắn máy"
            elif "Điều 8" in art_id:
                item["vehicle_type"] = "🚜 Xe máy chuyên dùng"
            elif "Điều 9" in art_id:
                item["vehicle_type"] = "🚲 Xe đạp, xe thô sơ"
            elif "Điều 10" in art_id:
                item["vehicle_type"] = "🚶 Người đi bộ"
            else:
                item["vehicle_type"] = "⚖️ Quy định chung"
                
            item["highlighted_text"] = self.highlight_exact_violation(
                item.get("original_text", ""),
                exact_phrases
            )
            results.append(item)
            
        return analysis, results
