FROM python:3.11-alpine

WORKDIR /app

# The server uses only Python standard library modules (no pip requirements needed)
COPY server.py index.html ./

ENV PORT=8088 \
    PYTHONUNBUFFERED=1

EXPOSE 8088

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8088/api/health')" || exit 1

CMD ["python3", "server.py"]
