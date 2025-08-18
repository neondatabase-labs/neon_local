# Start with official Envoy image (Debian-based with glibc)
FROM envoyproxy/envoy:v1.28-latest

USER root

# Install PgBouncer and PostgreSQL from the working version
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    python3 \
    python3-pip \
    python3-requests \
    python3-yaml \
    openssl \
    postgresql-client \
    wget \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Build PgBouncer from source to get latest version with SNI support
RUN apt-get update && apt-get install -y \
    build-essential \
    libevent-dev \
    libssl-dev \
    pkg-config \
    libc-ares-dev \
    && wget https://pgbouncer.github.io/downloads/files/1.24.1/pgbouncer-1.24.1.tar.gz -O /tmp/pgbouncer.tar.gz \
    && cd /tmp && tar -xzf pgbouncer.tar.gz \
    && cd pgbouncer-1.24.1 \
    && ./configure --prefix=/usr/local \
    && make && make install \
    && rm -rf /tmp/* \
    && apt-get remove -y build-essential pkg-config \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Force IPv4-only DNS resolution
RUN echo 'precedence ::ffff:0:0/96  100' >> /etc/gai.conf

# Create postgres user and set up directories
RUN groupadd -f postgres || true \
    && useradd -g postgres postgres || true \
    && mkdir -p /etc/pgbouncer /var/log /scripts/app \
    && chown postgres:postgres /var/log /etc/pgbouncer \
    && echo "postgres ALL=(root) NOPASSWD: /bin/sed, /bin/sh" >> /etc/sudoers

# PgBouncer config
COPY /pgbouncer/userlist.txt /etc/pgbouncer/userlist.txt
COPY /pgbouncer/pgbouncer.ini.tmpl /scripts/app/pgbouncer.ini.tmpl

# Envoy config template
COPY /envoy/envoy.yaml.tmpl /scripts/app/envoy/envoy.yaml.tmpl

# Application code
COPY entrypoint.py /scripts/app/entrypoint.py
COPY process_manager.py /scripts/app/process_manager.py
COPY neon.py /scripts/app/neon.py
COPY unified_manager.py /scripts/app/unified_manager.py
COPY /pgbouncer/pgbouncer_manager.py /scripts/app/pgbouncer_manager.py
COPY /envoy/envoy_manager.py /scripts/app/envoy_manager.py
COPY pgbouncer_wrapper.sh /usr/local/bin/pgbouncer_wrapper.sh
RUN chmod +x /usr/local/bin/pgbouncer_wrapper.sh
RUN touch /scripts/app/__init__.py

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/scripts
ENV NEON_PROJECT_ID=""
ENV BRANCH_ID=""
ENV DELETE_BRANCH=true

# Create a startup script that runs as root to modify /etc/hosts
COPY startup.sh /usr/local/bin/startup.sh
RUN chmod +x /usr/local/bin/startup.sh

# Create and set permissions for logs
RUN touch /var/log/pgbouncer.log \
    && touch /var/log/envoy.log \
    && chown postgres:postgres /var/log/pgbouncer.log /var/log/envoy.log \
    && chmod 644 /var/log/pgbouncer.log /var/log/envoy.log

# Stay as root for startup script, then switch to postgres in the script
USER root

WORKDIR /scripts

# Expose the main proxy port
EXPOSE 5432

ENTRYPOINT []
CMD ["/usr/local/bin/startup.sh"]
