FROM python:3.12-slim

# Datasette와 플러그인 설치
RUN pip install --no-cache-dir \
    setuptools \
    datasette \
    datasette-write \
    datasette-auth-passwords

WORKDIR /app

# DB 파일과 설정 파일 복사
COPY kugak.db .
COPY metadata.yml .

# 8080 포트 사용 (Fly.io 기본)
EXPOSE 8080

# Datasette 실행
CMD ["datasette", "serve", "kugak.db", \
     "--host", "0.0.0.0", \
     "--port", "8080", \
     "--metadata", "metadata.yml", \
     "--cors"]
