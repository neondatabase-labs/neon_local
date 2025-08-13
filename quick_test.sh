#!/bin/bash

echo "=== Quick HAProxy & PgBouncer Test ==="
echo ""

# Set test environment variables
export NEON_API_KEY="test_key"
export NEON_PROJECT_ID="test_project_id"  
export PARENT_BRANCH_ID="test_branch_id"

echo "1. Starting container with test environment..."
docker-compose up -d

echo ""
echo "2. Waiting 5 seconds for services to start..."
sleep 5

echo ""
echo "3. Checking if container is running..."
docker-compose ps

echo ""
echo "4. Checking container logs..."
docker-compose logs --tail=20

echo ""
echo "5. Testing if we can connect to container shell..."
echo "   (If this works, you can run the commands below manually)"
echo ""
echo "Commands to run inside container:"
echo "docker-compose exec neon_local sh"
echo "# Then inside container:"
echo "ps aux | grep -E '(haproxy|pgbouncer)'"
echo "netstat -tlnp | grep -E '(5432|6432)'"
echo "ls -la /tmp/haproxy.cfg /etc/pgbouncer/pgbouncer.ini"

echo ""
echo "6. Testing external port accessibility..."
nc -zv localhost 5432 2>&1 || echo "Port 5432 not accessible from host"

echo ""
echo "=== Test Complete ==="