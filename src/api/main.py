from typing import Optional
import os
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
)
from src.search.dense import DenseSearcher

app = FastAPI(
    title="Vietnamese Legal Semantic Search API",
    version="1.0",
    description=(
        "API tìm kiếm ngữ nghĩa văn bản pháp luật sử dụng FastAPI và Qdrant"
    ),
)

# Khởi tạo searcher
searcher = DenseSearcher()


class SearchRequest(BaseModel):
  query: str
  document_id: Optional[str] = None
  top_k: int = 3


@app.get("/")
def root():
  return {"message": "Legal Semantic Search API is running successfully!"}


@app.post("/api/v1/search")
def search_legal_docs(request: SearchRequest):
  try:
    results = searcher.search(
        query_text=request.query,
        document_id_filter=request.document_id,
        top_k=request.top_k,
    )
    return {"status": "success", "query": request.query, "results": results}
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
  import uvicorn

  uvicorn.run("src.api.main:app", host="127.0.0.1", port=8000, reload=True)