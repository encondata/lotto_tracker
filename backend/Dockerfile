FROM python:3.12-slim
WORKDIR /app
# Copy the full project first so the editable install can find the `app` package.
COPY . .
RUN pip install --no-cache-dir -e ".[dev]"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
