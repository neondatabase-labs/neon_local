FROM haproxy:3.1-alpine

USER root

RUN apk add --no-cache python3 py3-requests

COPY haproxy.cfg.tmpl /scripts/haproxy.cfg.tmpl
COPY entrypoint.py /scripts/entrypoint.py

USER haproxy

ENTRYPOINT [ "python3", "/scripts/entrypoint.py" ]

CMD [ "/bin/bash" ]
