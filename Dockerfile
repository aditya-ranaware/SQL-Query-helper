# ---------- Stage 1: build the React app ----------
FROM node:22-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- Stage 2: Python backend + the built frontend ----------
FROM python:3.12-slim
WORKDIR /app/backend
ENV PYTHONUNBUFFERED=1

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/make_sample_db.py .
RUN mkdir -p data && python make_sample_db.py
COPY --from=frontend-build /frontend/dist ./static

EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860} --proxy-headers --forwarded-allow-ips='*'"]