FROM python:3.13-alpine

RUN adduser -D user
USER user

WORKDIR /opt/rdgen

COPY . .
RUN pip install --no-cache-dir -r requirements.txt \
 && python manage.py migrate \
 && mkdir -p exe png temp_zips
# As pastas acima ja existem na imagem com dono "user": assim volumes nomeados
# montados nelas herdam a permissao de escrita (sem isso o gerador da erro 500).

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD wget --spider 0.0.0.0:8000

CMD ["/home/user/.local/bin/gunicorn", "-c", "gunicorn.conf.py", "rdgen.wsgi:application"]
