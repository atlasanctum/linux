FROM python:3.12-slim

WORKDIR /app

COPY atlas/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY atlas/ ./atlas/

ENV PYTHONPATH=/app

ENTRYPOINT ["python", "-m", "atlas.node.node"]
CMD ["--name", "atlas-node-01", "--role", "edge"]
