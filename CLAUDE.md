# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Szymon is a personal assistant - a gateway for personal APIs and tools, designed for AI, MCP, and API integrations.

## Commands

```bash
# Install dependencies
pip install -e .

# Run the server
szymon
# or
python -m szymon.main

# Run with uvicorn directly (with hot reload)
uvicorn szymon.main:app --reload
```

## Architecture

- `szymon/main.py` - FastAPI application with settings (loads from `.env` via pydantic-settings)

## API Documentation

Swagger UI available at `/docs` when server is running.
