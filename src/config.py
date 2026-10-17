from pathlib import Path

# Thư mục gốc dự án
BASE_DIR = Path(__file__).resolve().parent.parent

# Đường dẫn dữ liệu
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

CLEANED_DIR = PROCESSED_DIR / "cleaned"
CHUNKS_FILE = PROCESSED_DIR / "corpus_chunks.jsonl"
EMBEDDED_FILE = PROCESSED_DIR / "corpus_embedded.jsonl"

# Cấu hình Vector DB & Model
QDRANT_PATH = str(BASE_DIR / "qdrant_db")
COLLECTION_NAME = "legal_vn_traffic"
EMBEDDING_MODEL_NAME = "bkai-foundation-models/vietnamese-bi-encoder"

# Prototype parameters retained in stage 1; these are not a validated model release.
EMBEDDING_MAX_LENGTH = 256
EMBEDDING_DIMENSION = 768
SNAPSHOT_DATE = "2025-01-01"
STAGING_DIR = BASE_DIR / "staging"
