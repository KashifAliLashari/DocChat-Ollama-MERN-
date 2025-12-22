Set-Location -LiteralPath "e:\Ollama offline chatbot"
$env:PYTHONPATH = "."
if (-not $env:OLLAMA_MODEL) { $env:OLLAMA_MODEL = "qwen2.5:0.5b" }
.\.venv\Scripts\python -m uvicorn backend.main:app --reload

