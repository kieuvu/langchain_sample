# Installation

```bash
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
cp .env.example .env
```

# Run the API

```bash
.venv/bin/uvicorn api:create_app --factory --host 127.0.0.1 --port 8000 --workers 1
```

# CLI

```bash
.venv/bin/chat-service "What's the weather in Hanoi today?"
```