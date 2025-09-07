# Multi-stage: Extract Envoy, then use minimal Ubuntu base (half the size of full Envoy image)
FROM envoyproxy/envoy:v1.28-latest AS envoy-source

# Minimal Ubuntu 20.04 base (same version as Envoy, but without all the extras)
FROM ubuntu:20.04
ARG TARGETARCH

USER root

# Install only essential packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Runtime dependencies
    python3 \
    python3-requests \
    python3-yaml \
    openssl \
    postgresql-client \
    sudo \
    libevent-2.1-7 \
    libc-ares2 \
    libssl1.1 \
    ca-certificates \
    # Build dependencies (will be removed)
    build-essential \
    libevent-dev \
    libssl-dev \
    pkg-config \
    libc-ares-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

# get Go and build wsproxy
RUN wget https://go.dev/dl/go1.25.1.linux-${TARGETARCH}.tar.gz -O /tmp/go.tar.gz \
  && cd /tmp && tar -C /usr/local -xzf go.tar.gz \
  && GOBIN=/usr/local/bin /usr/local/go/bin/go install github.com/neondatabase/wsproxy@latest

# Copy Envoy binary from official image (avoid downloading/extracting)
COPY --from=envoy-source /usr/local/bin/envoy /usr/local/bin/envoy
COPY --from=envoy-source /usr/local/bin/su-exec /usr/local/bin/su-exec

# Build PgBouncer from source and aggressively clean up
RUN wget https://pgbouncer.github.io/downloads/files/1.24.1/pgbouncer-1.24.1.tar.gz -O /tmp/pgbouncer.tar.gz \
    && cd /tmp && tar -xzf pgbouncer.tar.gz \
    && cd pgbouncer-1.24.1 \
    && ./configure --prefix=/usr/local \
    && make && make install \
    && cd / \
    && rm -rf /tmp/* \
    # Remove ALL build dependencies and related packages
    && apt-get remove --purge -y \
        build-essential \
        gcc \
        gcc-* \
        g++ \
        g++-* \
        cpp \
        cpp-* \
        libc6-dev \
        linux-libc-dev \
        pkg-config \
        libevent-dev \
        libssl-dev \
        libc-ares-dev \
        wget \
        dpkg-dev \
        binutils \
        binutils-* \
        make \
        patch \
        perl \
        perl-* \
    && apt-get autoremove --purge -y \
    && apt-get clean \
    # Aggressive cleanup of caches, docs, and unused files
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/* \
    && rm -rf /var/cache/debconf/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/* \
    && rm -rf /usr/share/doc/* \
    && rm -rf /usr/share/man/* \
    && rm -rf /usr/share/info/* \
    && rm -rf /usr/share/locale/* \
    && rm -rf /usr/lib/python*/test \
    && rm -rf /usr/lib/python*/unittest \
    && rm -rf /usr/lib/python*/distutils \
    && rm -rf /usr/lib/python*/lib2to3 \
    && rm -rf /usr/lib/python*/ensurepip \
    && find /usr/lib/python* -name "*.pyc" -delete \
    && find /usr/lib/python* -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true \
    # Remove any leftover .a static libraries
    && find /usr -name "*.a" -delete 2>/dev/null || true

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

USER root
WORKDIR /scripts
EXPOSE 5432

ENTRYPOINT []
CMD ["/usr/local/bin/startup.sh"]
