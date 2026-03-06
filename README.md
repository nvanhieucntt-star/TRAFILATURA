# Search Service (Python)

Web search API tương thích SearXNG — dùng DuckDuckGo, không cần API key.

## API

```
GET /search?q=query&format=json
```

Trả về JSON với mảng `results`, mỗi item có `url`, `title`, `content`. Chatbot dùng trực tiếp thay SearXNG.

## Chạy local

```bash
# Cách 1: Python thuần
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8080

# Cách 2: Docker
docker build -t search-service .
docker run -p 8080:8080 -e PORT=8080 search-service
```

## Deploy Render

1. Connect repo, Root Directory: `searxng-service`
2. Runtime: **Docker** hoặc **Python** (có `requirements.txt` là đủ)
3. Build: auto (Dockerfile) hoặc `pip install -r requirements.txt`
4. Start: `uvicorn app:app --host 0.0.0.0 --port $PORT`
5. Lấy URL → thêm vào chatbot `.env`: `SEARXNG_URL=https://xxx.onrender.com`

## Environment (tùy chọn)

| Biến | Mặc định | Mô tả |
|------|----------|-------|
| `SEARCH_MAX_RESULTS` | 10 | Số kết quả tối đa |
| `SEARCH_TIMEOUT_SECONDS` | 15 | Timeout tìm kiếm |
