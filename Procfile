# Forcing new build at {datetime.datetime.utcnow().isoformat()}
# Zeabur release command to install Playwright browser dependencies
release: python -m playwright install --with-deps chromium
# Web process to run the FastAPI application
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
