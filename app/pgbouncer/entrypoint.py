#!/usr/bin/env python

import json
import hashlib
import os
import time
import subprocess
import threading
import requests


API_URL = "https://console.neon.tech/api/v2"


def _prepare_config() -> None:
    # Get environment variables
    api_key = os.getenv("NEON_API_KEY")
    project_id = os.getenv("NEON_PROJECT_ID")

    # Check for required environment variables
    if not api_key or not project_id:
        raise ValueError("NEON_API_KEY or NEON_PROJECT_ID not set in environment variables.")

    # Load the state file
    try:
        with open("/scripts/.neon.local", "r") as file:
            state = json.load(file)
            print(f"State: {state}")
    except:
        print("No state file found.")
        state = {}

    # Get the current branch
    try:
        with open("/scripts/.git/HEAD", "r") as file:
            current_branch = file.read().split(":", 1)[1].split("/", 2)[-1].strip()
            print(f"Current branch: {current_branch}")
    except:
        print("No branch found from git file.")
        current_branch = None

    # Prepare headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    params = None
    if current_branch is not None and (params := state.get(current_branch)) is not None:
        # Ensure that branch still exists
        try:
            requests.get(f"{API_URL}/projects/{project_id}/branches/{params['branch_id']}", headers=headers).raise_for_status()
        except:
            print("No branch found at Neon.")
            params = None

    if params is None:
        # Prepare the JSON payload
        payload = {
            "endpoints": [{
                "type": "read_write",
            }],
        }

        # Make the POST request
        response = requests.post(f"{API_URL}/projects/{project_id}/branches", headers=headers, json=payload)

        # Check that branch is created. If it's not, just abort the process
        response.raise_for_status()

        # Parse the response as JSON
        json_response = response.json()

        # Extract connection parameters
        params = json_response["connection_uris"][0]["connection_parameters"]
        params["branch_id"] = json_response["branch"]["id"]

        if current_branch is not None:
            state[current_branch] = params

    # Read the template and replace placeholders
    with open("/scripts/pgbouncer.ini.tmpl", "r") as file:
        pgbouncer_template = file.read()

    print(f"Params: {params}")
    # Generate pgbouncer configuration
    pgbouncer_config = pgbouncer_template.format(**params)

    # Print the generated configuration
    with open ("/etc/pgbouncer/pgbouncer.ini", "w") as file:
        file.write(pgbouncer_config)

    # Preserve the state
    try:
        with open("/scripts/.neon.local", "w") as file:
            json.dump(state, file)
            print(f"New state: {state}")
    except:
        print("Failed to write state file.")


def _start_pgbouncer() -> subprocess.Popen:
    _prepare_config()
    return subprocess.Popen(["/usr/bin/pgbouncer", "/etc/pgbouncer/pgbouncer.ini"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _pgbouncer_thread(cv: threading.Condition) -> None:
    pgbouncer_process = _start_pgbouncer()
    
    while True:
        with cv:
            cv.wait()
            print("reloading pgbouncer")
            pgbouncer_process.kill()
            pgbouncer_process.wait()
            pgbouncer_process = _start_pgbouncer()


def _calculate_file_hash(file_path: str) -> str:
    with open(file_path, "rb") as file:
        return hashlib.sha256(file.read()).hexdigest()


def _inner_main() -> None:
    cv = threading.Condition()

    pgbouncer_thread = threading.Thread(target=_pgbouncer_thread, args=(cv,))
    pgbouncer_thread.start()

    file_path = "/scripts/.git/HEAD"
    last_hash = _calculate_file_hash(file_path)

    print("Watching for file changes...")

    try:
        while True:
            time.sleep(1)  # Check every second
            current_hash = _calculate_file_hash(file_path)
            if current_hash != last_hash:
                print("File has changed!")
                last_hash = current_hash
                with cv:
                    cv.notify()
    except KeyboardInterrupt:
        print("Terminating")
        pgbouncer_thread.kill()
        pgbouncer_thread.join()


def main() -> None:
    try: 
        _inner_main()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
