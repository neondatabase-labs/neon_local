FROM edoburu/pgbouncer:latest

USER root

# Install HAProxy and Python
RUN apk add --no-cache haproxy python3 py3-requests

# Certificates and PgBouncer config
COPY /pgbouncer/server.crt /etc/pgbouncer/server.crt
COPY /pgbouncer/server.key /etc/pgbouncer/server.key
COPY /pgbouncer/userlist.txt /etc/pgbouncer/userlist.txt
COPY /pgbouncer/pgbouncer.ini.tmpl /scripts/app/pgbouncer.ini.tmpl

# HAProxy config template
COPY /haproxy/haproxy.cfg.tmpl /scripts/app/haproxy.cfg.tmpl

# Application code
COPY entrypoint.py /scripts/app/entrypoint.py
COPY process_manager.py /scripts/app/process_manager.py
COPY neon.py /scripts/app/neon.py
COPY /pgbouncer/pgbouncer_manager.py /scripts/app/pgbouncer_manager.py
COPY /haproxy/haproxy_manager.py /scripts/app/haproxy_manager.py
RUN touch /scripts/app/__init__.py

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/scripts

# Create and set permissions for logs
RUN touch /var/log/pgbouncer.log \
    && touch /var/log/haproxy.log \
    && chown postgres:postgres /var/log/pgbouncer.log /var/log/haproxy.log \
    && chmod 644 /var/log/pgbouncer.log /var/log/haproxy.log

USER postgres

WORKDIR /scripts
ENTRYPOINT []
CMD ["python", "-m", "app.entrypoint"]
