#!/bin/bash
# Startup script that runs as root to modify /etc/hosts for IPv4 resolution

set -e

echo "Starting Neon Local as root to configure networking..."

# Function to resolve hostname to IPv4 and add to /etc/hosts
add_ipv4_host() {
    local hostname=$1
    echo "Resolving $hostname to IPv4..."
    
    # Use getent to get IPv4 address specifically
    local ipv4_addr=$(python3 -c "
import socket
try:
    result = socket.getaddrinfo('$hostname', 5432, socket.AF_INET)
    print(result[0][4][0])
except Exception as e:
    print('FAILED')
    exit(1)
")
    
    if [ "$ipv4_addr" != "FAILED" ] && [ -n "$ipv4_addr" ]; then
        echo "Adding to /etc/hosts: $ipv4_addr $hostname"
        # Remove any existing entries for this hostname
        sed -i "/$hostname/d" /etc/hosts
        # Add the IPv4 entry
        echo "$ipv4_addr $hostname" >> /etc/hosts
    else
        echo "Failed to resolve $hostname to IPv4"
    fi
}

# Get the Neon database info from environment or API
echo "Getting database configuration..."
cd /scripts

# Create a temporary Python script to get database info and update hosts
python3 -c "
import sys
sys.path.append('/scripts')
from app.neon import NeonAPI
import socket

try:
    import os
    api = NeonAPI()
    project_id = os.environ.get('NEON_PROJECT_ID', '')
    branch_id = os.environ.get('BRANCH_ID', '')
    
    params = None
    if project_id and branch_id:
        try:
            params = api.get_branch_connection_info(project_id, branch_id)
        except Exception as e:
            print(f'Error with specific branch: {e}')
    
    # If that fails, try the fetch_or_create_branch method like unified_manager does
    if not params:
        try:
            # Simulate what unified_manager does
            state = {}  # Empty state for now
            current_branch = 'main'  # Default branch
            params, updated_state = api.fetch_or_create_branch(state, current_branch, vscode=False)
        except Exception as e:
            print(f'Error with fetch_or_create_branch: {e}')
    
    if params:
        print('Found database parameters, updating /etc/hosts...')
        hosts_entries = []
        
        for db in params:
            hostname = db['host']
            try:
                # Get IPv4 addresses for the hostname
                ipv4_info = socket.getaddrinfo(hostname, 5432, socket.AF_INET)
                ipv4_addr = ipv4_info[0][4][0]  # Get first IPv4 address
                hosts_entries.append(f'{ipv4_addr} {hostname}')
                print(f'Resolved {hostname} to IPv4: {ipv4_addr}')
            except Exception as e:
                print(f'Failed to resolve {hostname}: {e}')
        
        # Write entries to /etc/hosts
        if hosts_entries:
            with open('/etc/hosts', 'a') as f:
                f.write('\n# Neon IPv4 entries added by startup script\n')
                for entry in hosts_entries:
                    f.write(f'{entry}\n')
            print('Successfully updated /etc/hosts with IPv4 entries')
        else:
            print('No IPv4 entries to add')
    else:
        print('No database parameters found')
except Exception as e:
    print(f'Error getting database parameters: {e}')
"

echo "Displaying updated /etc/hosts:"
cat /etc/hosts

echo "Switching to postgres user and starting application..."

# Switch to postgres user and run the Python application
exec su postgres -c "cd /scripts && python3 -m app.entrypoint"
