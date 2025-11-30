# All I Want For Christmas

***DISCLAIMER: This was completely vibe-coded.***

A tiny Flask web app you can open on your phone to track every time you hear  
**“All I Want For Christmas Is You”** by Mariah Carey out in the wild.  
Each tap logs the time and your location to a CSV file.

---

## Docker usage

This repo *does not* include the compose file, but here’s the example to use:

```yaml
services:
  all-i-want:
    build: .
    container_name: all-i-want
    restart: unless-stopped
    ports:
      - "2025:2025"
    volumes:
      - ./data:/app/data
    environment:
      - FLASK_ENV=production
```

Then run:

```bash
mkdir -p data
docker compose up --build -d
```

App becomes available at:

```
http://localhost:2025
```

