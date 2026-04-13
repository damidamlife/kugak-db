FROM python:3.12-slim

# setuptools 먼저 설치 (pkg_resources 오류 방지)
RUN pip install --no-cache-dir setuptools

# Datasette 최신 버전 + 플러그인
RUN pip install --no-cache-dir \
    datasette \
    datasette-write \
    datasette-auth-passwords

WORKDIR /app

COPY kugak.db .
COPY metadata.yml .

EXPOSE 8080

# --cors 반드시 포함 — 없으면 외부 페이지에서 "fail to fetch" 발생
CMD ["datasette", "serve", "kugak.db", \
     "--host", "0.0.0.0", \
     "--port", "8080", \
     "--metadata", "metadata.yml", \
     "--cors"]
