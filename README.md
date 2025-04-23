# Neon Local

## Whats Neon local?
Neon Local is a local proxy for your Neon database that allows you to easily connect and switch between Neon database branches as if it were a locally running postgres container. This means that you no longer need to manually update connection string environment variables and pass them to your app everytime you switch Neon branches. Your app can be configured as if it were communicating with a local postgres container, and the Neon Local container will handle all routing and authentication for you.  

## Ephemeral database branches for dev and test
By default, the Neon Local container will automatically create a new ephemeral branch of your database to develop and test against when the container starts that will persist until the container is stopped. This ensure that each time you deploy your app via Docker Compose, you have a clean copy of your database, without the need to manually clean up branches via the CLI or orchestrate anything via make or similar tools. Your database branch lifecycle is tied directly to the life of your compose app.

## Persistent database per Git branch for dev test
If you would prefer to have your Neon branches persist between test runs you can also disable the auto-deletion of branches on container stop, and provide a mount to your project's git file to ensure that the container will automatically create new Neon database branches for every new Git branch you work on. 

## Personal copies of your staging database for CI testing and Preview environments
Using the Neon Local container in your CI pipeline allows you to instantly create and connect to copies of your staging or test database with a simple compose up command. No need for additional automation like Github actions required. 

## Docker run instructions
You can run the Neon Local container with the following docker run command

``` 
    $ docker run \
        -name db
        -p 5432:5432
        -e NEON_API_KEY: <your_neon_api_key>
        -e NEON_PROJECT_ID: <your_neon_project_key>
        neondatabase/neon_local:latest
```

## Docker compose instructions
You can also add the Neon Local container directly to your compose app like this

``` 
    db:
        image: neondatabase/neon_local:latest
        ports:
            - "5432:5432"
        environment:
            NEON_API_KEY: ${NEON_API_KEY}
            NEON_PROJECT_ID: ${NEON_PROJECT_ID}
```

## Multi-Driver support
The Neon Local container supports communicating with your Neon database via both the postgres and Neon serverless driver. If no driver is configured, the postgres driver will be used by default. The container's driver can be set with the `DRIVER` environment variable and can be set to either `postgres` or `serverless`. 

## Connecting your app (postgres driver)
To connect your app to the Neon Local container via the postgres driver, you need to provide your app a connection sting pointing to the Neon Local container with the following credentials (role: neon, password: npg). That means for the docker run example above the app's connection string to connect would look like:

``` "postgres://neon:npg@localhost:5432/<database_name>?sslmode=require" ```

and in the docker compose example above, the app's connection string to connect would look like:

``` "postgres://neon:npg@db:5432/<database_name>?sslmode=require" ```

(as the containers service name in the compose file is `db`)

No other changes should be necessary to your app, except ensuring you currently do not have your `sslmode` is set to `disable` on your database connection as Neon databases require your app to use ssl to communicate.
 
## Connection your app (Neon serverless driver)
To connect your app to the Neon Local container via the Neon serverless driver you must provide the Neon Local connection string to your app in the same way as the postgres driver. You also need to ensure that the `NeonConfig.fetchEndpoint` is properly configured to also point to your Neon Local container. So with the docker run example above this would lokk like:

```
    import { neon, neonConfig } from "@neondatabase/serverless";
    const sql = neon("postgres://neon:npg@localhost:5432/<database_name>?sslmode=no-verify");
    neonConfig.fetchEndpoint = 'http://localhost:5432/sql'
```

And for the docker compose example it would look like:

```
    import { neon, neonConfig } from "@neondatabase/serverless";
    const sql = neon("postgres://neon:npg@db:5432/<database_name>")?sslmode=no-verify;
    neonConfig.fetchEndpoint = 'http://db:5432/sql'
```

You will also need to add the `DRIVER: serverless` environment variable to your Docker run command or compose command to allow your app to communicate with the the Neon Local container using the Neon serverless driver like this:

``` 
    $ docker run \
        -name db
        -p 5432:5432
        -e NEON_API_KEY: <your_neon_api_key>
        -e NEON_PROJECT_ID: <your_neon_project_key>
        -e DRIVER: serverless
        neondatabase/neon_local:latest
```

``` 
    db:
        image: neondatabase/neon_local:latest
        ports:
            - "5432:5432"
        environment:
            NEON_API_KEY: ${NEON_API_KEY}
            NEON_PROJECT_ID: ${NEON_PROJECT_ID}
            DRIVER: serverless
```


## Environment variables and additional settings

### NEON_API_KEY (required)
A Neon API key is required by the Neon Local container to enable the container to create and delete Neon branches and proxy your apps queries to your Neon database. Instructions to generate a Neon API key can be found at <https://neon.tech/docs/manage/api-keys>. Once you have created your API key, it can be configured with the `NEON_API_KEY` environment variable.

### NEON_PROJECT_ID (required)
The Neon Local container also requires you to define which Neon project you wish to connect to via the `NEON_PROJECT_ID` environment variable. Your project's id can be found by navigating to the Settings > General page of your project at <https://neon.tech>.

### DRIVER
The Neon Local container supports both the postgres driver and the Neon serverless driver and can be configured using the `DRIVER` environment variable. Valid values are `postgres` and `serverless`. By default if no driver is defined, the container will use the postges driver.

### PARENT_BRANCH_ID
By default the Neon Local container will create a child of your project's default branch. If you wish to set a different parent you can do so by setting the `PARENT_BRANCH_ID` environment variable on the container to the desired branches `branch_id`.

### DELETE_BRANCH
By default the Neon Local container will automatically delete any created branch when the container stops. If you wish to disable automatic branch deletion, you can configure it with the `DELETE_BRANCH` environment variable by setting it to `false`. 

### Persistent Neon branch per Git branch 
If you wish for the Neon Local container to create a single branch tied to your git branches, you can provide two volume mounts to your Neon local container to access your projects current git branch's name and to persist Neon branch metadata in your project. 

``` 
    db:
        image: neondatabase/neon_local:latest
        ports:
            - "5432:5432"
        environment:
            NEON_API_KEY: ${NEON_API_KEY}
            NEON_PROJECT_ID: ${NEON_PROJECT_ID}
        volumes:
            - ./.neon_local/:/tmp/.neon_local
            - ./.git/HEAD:/tmp/.git/HEAD:ro,consistent
```
Note: this will automatically create a .neon_local folder in your project to save branch metadata to. You will want to add this file to your .gitignore file to prevent database connection information from being saved in git. 

#### Git integration using docker on Mac
If using Docker Desktop for Mac, ensure that your Virtual Machine settings in Docker Desktop are set to gRPC FUSE, not VirtioFS to ensure that Neon Local can detect git branch changes. There is currently a bug with VirtioFS which can prevent containers from being properly updated when local files change while the container is running.  

![How to change the image](img/disc.png)