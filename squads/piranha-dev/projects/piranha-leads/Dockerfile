FROM node:20-bullseye AS frontend-build

WORKDIR /app/atlas

COPY atlas/package*.json ./
RUN npm ci

COPY atlas/ ./
RUN npm run build


FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./
COPY --from=frontend-build /app/atlas/dist /app/atlas/dist

EXPOSE 8000

CMD ["uvicorn", "atlas.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
