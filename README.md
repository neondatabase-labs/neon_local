# Neon Local

## What is Neon Local?

Neon Local is a proxy service that creates a local interface to your Neon cloud database. By default, it automatically creates a new database branch when your container starts and deletes it when the container stops.

Your application connects to a local Postgres endpoint, while Neon Local handles routing and authentication to the correct project and branch. This removes the need to update connection strings when working across database branches.

See our documentation for more configuration options: [Neon Local Documentation](https://neon.tech/docs/local/neon-local)

## Ephemeral database branches for development and testing

By default, the Neon Local container automatically creates a new ephemeral branch of your database when the container starts, and deletes it when the container stops. This ensures that each time you deploy your app via Docker Compose, you have a fresh copy of your database — without needing manual cleanup or orchestration scripts. Your database branch lifecycle is tied directly to your Docker environment.

## Persistent database per Git branch for development and testing

If you prefer to persist database branches across test runs, you can disable automatic branch deletion and mount your project's Git metadata into the container. Neon Local will automatically create a new Neon database branch corresponding to each Git branch you work on.

Using the Neon Local container in your CI pipeline allows you to instantly create and connect to fresh copies of your staging or test database with a simple `docker compose up` command — no additional automation (like GitHub Actions) required.

## Docker run instructions

Run the Neon Local container using the following `docker run` command:

```shell
docker run \
  --name db \
  -p 5432:5432 \
  -e NEON_API_KEY=<your_neon_api_key> \
  -e NEON_PROJECT_ID=<your_neon_project_id> \
  neondatabase/neon_local:latest
```

## Docker Compose instructions

Add Neon Local to your `docker-compose.yml`:

```yaml
db:
  image: neondatabase/neon_local:latest
  ports:
    - '5432:5432'
  environment:
    NEON_API_KEY: ${NEON_API_KEY}
    NEON_PROJECT_ID: ${NEON_PROJECT_ID}
```

## Multi-driver support

The Neon Local container supports both the `postgres` and Neon `serverless` drivers.  
If no driver is configured, `postgres` is used by default.

Set the driver using the `DRIVER` environment variable:

- `postgres`
- `serverless`

## Connecting your app (Postgres driver)

Connect to Neon Local using a standard Postgres connection string.

### Docker run

```shell
postgres://neon:npg@localhost:5432/<database_name>?sslmode=no-verify
```

### Docker compose

```shell
postgres://neon:npg@db:5432/<database_name>?sslmode=no-verify
```

## Connecting your app (Neon serverless driver)

Connect using the Neon [serverless driver](https://neon.tech/docs/serverless/serverless-driver).

### Docker run

```javascript
import { neon, neonConfig } from '@neondatabase/serverless';
neonConfig.fetchEndpoint = 'http://localhost:5432/sql';

const sql = neon('postgres://neon:npg@localhost:5432/<database_name>');
```

### Docker compose

```javascript
import { neon, neonConfig } from '@neondatabase/serverless';
neonConfig.fetchEndpoint = 'http://db:5432/sql';

const sql = neon('postgres://neon:npg@db:5432/<database_name>');
```

When using the serverless driver, set `DRIVER=serverless`:

```shell
docker run \
  --name db \
  -p 5432:5432 \
  -e NEON_API_KEY=<your_neon_api_key> \
  -e NEON_PROJECT_ID=<your_neon_project_id> \
  -e DRIVER=serverless \
  neondatabase/neon_local:latest

```

Or in Compose:

```yml
db:
  image: neondatabase/neon_local:latest
  ports:
    - '5432:5432'
  environment:
    NEON_API_KEY: ${NEON_API_KEY}
    NEON_PROJECT_ID: ${NEON_PROJECT_ID}
    DRIVER: serverless
```

## Environment variables and configuration options

| Variable           | Description                                                                       | Required | Default               |
| ------------------ | --------------------------------------------------------------------------------- | -------- | --------------------- |
| `NEON_API_KEY`     | Your Neon API key. [Manage API Keys](https://neon.tech/docs/manage/api-keys)      | Yes      | N/A                   |
| `NEON_PROJECT_ID`  | Your Neon project ID. Found under Project Settings → General in the Neon console. | Yes      | N/A                   |
| `DRIVER`           | Database driver to use. Options: `postgres`, `serverless`.                        | No       | `postgres`            |
| `PARENT_BRANCH_ID` | Specify a parent branch other than `main`, or `production`.                       | No       | `main` / `production` |
| `DELETE_BRANCH`    | Set to `false` to persist branches after container shutdown.                      | No       | `true`                |

## Persistent Neon branch per Git branch

To persist a branch per Git branch, add the following volume mounts:

```yaml
db:
  image: neondatabase/neon_local:latest
  ports:
    - '5432:5432'
  environment:
    NEON_API_KEY: ${NEON_API_KEY}
    NEON_PROJECT_ID: ${NEON_PROJECT_ID}
  volumes:
    - ./.neon_local/:/tmp/.neon_local
    - ./.git/HEAD:/tmp/.git/HEAD:ro,consistent
```

Note: This will create a `.neon_local` directory in your project to store metadata.
Be sure to add `.neon_local/` to your `.gitignore` to avoid committing database information.

## Git integration using Docker on Mac

If using Docker Desktop for Mac, ensure that your VM settings use **gRPC FUSE** instead of **VirtioFS**.  
There is currently a known bug with VirtioFS that prevents proper branch detection and live updates inside containers.

![How to change Docker Desktop settings](img/disc.png)
