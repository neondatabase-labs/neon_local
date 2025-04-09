FROM edoburu/pgbouncer:latest

USER root
COPY server.crt /etc/pgbouncer/server.crt
COPY server.key /etc/pgbouncer/server.key
COPY userlist.txt /etc/pgbouncer/userlist.txt
COPY pgbouncer.ini.tmpl /scripts/pgbouncer.ini.tmpl
COPY entrypoint.py /scripts/entrypoint.py

ENV PYTHONUNBUFFERED=1

RUN apk add --no-cache python3 py3-requests

USER postgres

ENTRYPOINT [ "python3", "/scripts/entrypoint.py" ]
CMD [ "/bin/sh" ]