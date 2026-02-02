set shell := ["bash", "-uc"]

# Run backend and frontend with hot reload
dev:
    python -m szymon.main & cd web && npm run dev

# Build backend and frontend
build:
    pip install -e .
    cd web && npm install && npm run build

# Run backend and frontend (production)
start:
    szymon & cd web && npm run preview
