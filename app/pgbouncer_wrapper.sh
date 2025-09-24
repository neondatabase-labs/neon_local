#!/bin/bash
# Wrapper script to run PgBouncer with IPv4-only DNS resolution

# Set environment to force IPv4
export RES_OPTIONS="inet"
export RESOLVE_SINGLE_REQUEST_REOPEN=1

# Run PgBouncer as postgres user for security
exec sudo -u postgres pgbouncer "$@"
