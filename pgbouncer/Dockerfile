FROM edoburu/pgbouncer:latest

USER root
COPY server.crt /etc/pgbouncer/server.crt
COPY server.key /etc/pgbouncer/server.key
COPY userlist.txt /etc/pgbouncer/userlist.txt
COPY pgbouncer.ini.tmpl /scripts/app/pgbouncer.ini.tmpl
COPY entrypoint.py /scripts/app/entrypoint.py
COPY process_manager.py /scripts/app/process_manager.py
COPY pgbouncer_manager.py /scripts/app/pgbouncer_manager.py
COPY neon.py /scripts/app/neon.py
RUN touch /scripts/app/__init__.py

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/scripts

RUN apk add --no-cache python3 py3-requests

RUN touch /var/log/pgbouncer.log
RUN chown postgres:postgres /var/log/pgbouncer.log
RUN chmod 644 /var/log/pgbouncer.log

USER postgres

ENTRYPOINT []
WORKDIR /scripts
CMD ["python", "-m", "app.entrypoint"]