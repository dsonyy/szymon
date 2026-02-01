set shell := ["bash", "-uc"]

# Run backend and frontend with hot reload
dev:
    uvicorn szymon.main:app --reload & cd web && npm run dev

# Build the project
build:
    pip install -e .
    cd web && npm install && npm run build

# Run the built project
start:
    szymon
