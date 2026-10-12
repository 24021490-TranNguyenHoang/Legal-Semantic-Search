import json
import torch
from transformers import AutoTokenizer, AutoModel
from src.config import CHUNKS_FILE, EMBEDDED_FILE, EMBEDDING_MODEL_NAME

# Hàm gộp vector (Mean Pooling) chuẩn cho mô hình Bi-Encoder
def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0] 
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
    sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    return sum_embeddings / sum_mask

def embed_and_save():
    print(f"[*] Đang tải mô hình NLP: {EMBEDDING_MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL_NAME)
    model = AutoModel.from_pretrained(EMBEDDING_MODEL_NAME)
    
    if not CHUNKS_FILE.exists():
        print(f"[!] Lỗi: Không tìm thấy file {CHUNKS_FILE} tại {CHUNKS_FILE.absolute()}")
        return
        
    print(f"[*] Đang đọc dữ liệu từ {CHUNKS_FILE}...")
    processed_data = []
    with open(CHUNKS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                processed_data.append(json.loads(line))
                
    print(f"[*] Đang mã hóa vector cho {len(processed_data)} chunks...")
    EMBEDDED_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(EMBEDDED_FILE, 'w', encoding='utf-8') as f_out:
        for item in processed_data:
            # Ưu tiên lấy enriched_text, sau đó đến original_text
            text = item.get("enriched_text") or item.get("original_text") or ""
            
            # Mã hóa văn bản sang tensor
            encoded_input = tokenizer(text, padding=True, truncation=True, max_length=256, return_tensors='pt')
            with torch.no_grad():
                model_output = model(**encoded_input)
            
            # Tính toán vector trung bình
            sentence_embedding = mean_pooling(model_output, encoded_input['attention_mask'])
            vector = sentence_embedding[0].tolist()
            
            item['vector'] = vector
            f_out.write(json.dumps(item, ensure_ascii=False) + '\n')
            
    print(f"[+] Hoàn tất! Đã lưu file vector tại: {EMBEDDED_FILE}")

if __name__ == "__main__":
    embed_and_save()