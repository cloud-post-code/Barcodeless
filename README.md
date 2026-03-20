# Barcodeless

Image-based product identification without barcodes. Uses CLIP embeddings with multi-view vector search and re-ranking to identify items from photos.

## How It Works

1. **Register items** — upload a product image and name. The system generates 5 embedding variants (full, center crops, brightness adjustments) per image for robust matching.
2. **Scan to identify** — upload a photo and get the top 5 matches ranked by confidence.
3. **Duplicate detection** — automatically rejects duplicate items when adding (configurable similarity threshold).

### Accuracy Strategy

- **CLIP ViT-L/14** for zero-shot visual embeddings (no training data needed)
- **5 embeddings per reference image** covering crops, brightness, and framing variation
- **Max-similarity re-ranking** — the best-matching view determines the score, not the average
- **Add more reference images** per item to boost accuracy further

## API

| Method   | Path                          | Description                            |
|----------|-------------------------------|----------------------------------------|
| `POST`   | `/items`                      | Add item (multipart: `name`, `image`)  |
| `GET`    | `/items`                      | List all items                         |
| `GET`    | `/items/{id}`                 | Get item details                       |
| `DELETE` | `/items/{id}`                 | Delete item                            |
| `POST`   | `/items/{id}/images`          | Add reference image to existing item   |
| `GET`    | `/items/{id}/images/{img_id}` | Retrieve a reference image             |
| `POST`   | `/scan`                       | Scan image, get top 5 matches          |
| `GET`    | `/health`                     | Health check                           |

### Scan Example

```bash
curl -X POST https://your-app.railway.app/scan \
  -F "image=@photo.jpg" \
  -F "top_k=5"
```

Response:
```json
{
  "results": [
    {"rank": 1, "item_id": "...", "name": "Red Apple", "confidence": 94.52},
    {"rank": 2, "item_id": "...", "name": "Green Apple", "confidence": 87.10}
  ],
  "total_items_searched": 523,
  "scan_time_ms": 68.4
}
```

## Deploy to Railway

1. **Create a Railway project** at [railway.app](https://railway.app)
2. **Add a PostgreSQL plugin** — Railway will set `DATABASE_URL` automatically
3. **Enable pgvector** — run this in the Railway PostgreSQL console:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
4. **Connect this repo** — point Railway at `https://github.com/Blakem12345/Barcodeless`
5. **Deploy** — Railway reads `railway.toml` and builds the Dockerfile

The first deploy takes ~5 minutes (model download is cached in the Docker image).

### Environment Variables

| Variable              | Default       | Description                       |
|-----------------------|---------------|-----------------------------------|
| `DATABASE_URL`        | *(required)*  | PostgreSQL connection string      |
| `CLIP_MODEL`          | `ViT-L-14`   | CLIP model variant                |
| `CLIP_PRETRAINED`     | `openai`      | Pretrained weights                |
| `DUPLICATE_THRESHOLD` | `0.92`        | Similarity threshold for dedup    |
| `TOP_K_RECALL`        | `50`          | Candidates retrieved before rerank|

## Local Development

```bash
# Start PostgreSQL with pgvector
docker compose up db -d

# Install dependencies
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# Copy and edit env
cp .env.example .env

# Run
uvicorn app.main:app --reload
```

Or run everything in Docker:

```bash
docker compose up --build
```
