# VLADO — hosted pilot image (modo piloto, behind an HTTPS reverse proxy).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN useradd --create-home --uid 10001 vlado

COPY requirements.txt requirements-opcional.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-opcional.txt

COPY . .
# Data folders are Docker volumes (see docker-compose.yml). Only they are writable by the
# app user; the code stays read-only for it.
RUN mkdir -p casos conversas execucoes lixeira entrada segredos ajustes acesso \
    && chown -R vlado:vlado casos conversas execucoes lixeira entrada segredos ajustes acesso
USER vlado

EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8765/saude', timeout=4).status == 200 else 1)"

CMD ["sh", "-c", "exec python scripts/interface_pesquisa.py --modo piloto --host 0.0.0.0 --porta 8765 --sem-abrir --origem \"https://${VLADO_DOMINIO:?defina VLADO_DOMINIO}\""]
