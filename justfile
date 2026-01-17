set shell := ["bash", "-uc"]

# Install all dependencies
install:
    pip install -e .
    cd web && npm install

# Build the React app
build:
    cd web && npm run build

# Run the server
run:
    szymon

# Install, build, and run
all: install build run

# Run React dev server (hot reload)
dev-web:
    cd web && npm run dev

# Clean build artifacts
clean:
    rm -rf web/dist web/node_modules certs __pycache__ *.egg-info
