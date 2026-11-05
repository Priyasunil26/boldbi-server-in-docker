# Upgrade Center for Bold BI and Bold Reports in Docker

## Overview

The Upgrade Center is a dedicated upgrade management service that lets administrators upgrade an existing Bold BI or Bold Reports Docker deployment from a web interface, without manually downloading or managing Docker images.

With Upgrade Center, administrators can:

- Check for available updates.
- Perform upgrades from the administration portal.
- Validate the environment before and after upgrades.
- Automatically back up required database objects when schema updates are involved.
- Automatically roll back to the previous version if an upgrade fails.

> **Note:** Only users with **Administrator** privileges can access and perform upgrades through the Upgrade Center.

---

## How Upgrade Center Works

1. Detects the currently installed version.
2. Checks for available versions from the release service.
3. Creates database backups when database script changes are required.
4. Runs pre-upgrade validation tests using Playwright (Bold BI).
5. Upgrades the product container to the selected version.
6. Performs application health checks.
7. Executes post-upgrade validation tests.
8. Cleans up temporary validation data.
9. Automatically rolls back to the previous version if validation fails.

---

## Prerequisites

- An existing and running **Bold BI** or **Bold Reports** Docker deployment.
- The product container must be named `boldbi` (Bold BI) or `boldreports` (Bold Reports).
- Docker Engine must be accessible through `/var/run/docker.sock`.
- Internet access to retrieve release information.
- The Upgrade Center, product, and proxy containers must share the same Docker network.

### Security Notice

> Mounting the Docker socket (`/var/run/docker.sock`) grants administrative access to Docker on the host machine. Restrict access to Upgrade Center and allow only trusted administrators.

---

## Deployment Architecture

| Container | Purpose |
|---|---|
| **boldbi** / **boldreports** | The product application |
| **postgres** | Product database (when deployed with the sample compose files) |
| **bold-upgrade-center** | Handles upgrade operations |
| **nginx-proxy** | Routes requests to the product and Upgrade Center |

---

## Configuration Model

Internal settings are **not** passed as environment variables in the compose file. They are shipped inside the Upgrade Center image as environment-specific settings files, selected by `UPGRADE_CENTER_DEPLOYMENT_ENV`:

| Product | `UPGRADE_CENTER_DEPLOYMENT_ENV` | Settings file |
|---|---|---|
| Bold BI | `Docker` | `appsettings.Docker.json` |
| Bold Reports | `DockerReports` | `appsettings.DockerReports.json` |

These files configure: Docker execution, Standalone mode, deployment mode, Docker socket, configuration/private-key paths (`/application/app_data/configuration/`), the allowed image registry/repository, release feed URL, Playwright shared-state volume, Playwright report/result upload URLs, and health-check timing.

The customer supplies the environment name, the product container name (`UpgradeCenter__Docker__ContainerName`, `boldbi` or `boldreports`) and the administrator credentials.

---

## Docker Compose Configuration

Add the following to your existing `docker-compose.yml`. Complete samples are provided in `docker-compose.yml` (Bold BI) and `docker-compose.reports.yml` (Bold Reports).

### Upgrade Center Service (Bold BI)

```yaml
bold-upgrade-center:
  image: syncfusion/bold-upgrade-center-dev:<version>
  container_name: bold-upgrade-center
  user: "0:0"
  restart: unless-stopped
  depends_on:
    - boldbi
  environment:
    UPGRADE_CENTER_DEPLOYMENT_ENV: "Docker"
    BOLD_ADMIN_USERNAME: "<admin-user>"
    BOLD_ADMIN_PASSWORD: "<admin-password>"
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
    - boldbi_data:/application/app_data:ro
    - uc_data:/app/App_Data
    - bold-upgrade-center-playwright-state:/app/playwright-shared-state
  networks:
    - boldbi
```

### Upgrade Center Service (Bold Reports)

Same as above with `depends_on: boldreports`, `UPGRADE_CENTER_DEPLOYMENT_ENV: "DockerReports"`, the `boldreports_data` volume, and the `boldreports` network.

### Nginx Proxy Service

```yaml
nginx-proxy:
  image: nginx:alpine
  container_name: nginx-proxy
  restart: unless-stopped
  ports:
    - "8085:80"
  networks:
    - boldbi
  depends_on:
    - boldbi
    - bold-upgrade-center
  volumes:
    - ./boldbi-nginx-config.conf:/etc/nginx/conf.d/default.conf:ro
```

For Bold Reports use `./boldreports-nginx-config.conf` and the `boldreports` network/dependency.

### Nginx Configuration

`boldbi-nginx-config.conf` (for Bold Reports, `boldreports-nginx-config.conf` is identical except `proxy_pass http://boldreports:80;`):

```nginx
server {
    listen 80;

    location /upgrade-center {
        proxy_pass http://bold-upgrade-center:80;
        proxy_set_header Host $http_host;
        proxy_set_header X-Forwarded-Host $http_host;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location / {
        proxy_pass http://boldbi:80;
        proxy_set_header Host $http_host;
        proxy_set_header X-Forwarded-Host $http_host;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_redirect off;
    }
}
```

### Networks and Volumes

```yaml
networks:
  boldbi:

volumes:
  boldbi_data:
  db_data:
  uc_data:
  bold-upgrade-center-playwright-state:
```

---

## Volume Configuration

| Volume | Mount | Purpose |
|---|---|---|
| `boldbi_data` / `boldreports_data` | `/application/app_data` (read-only) | Product configuration and encryption files. |
| `uc_data` | `/app/App_Data` | Upgrade Center data: data protection keys and Playwright reports. |
| `bold-upgrade-center-playwright-state` | `/app/playwright-shared-state` | Playwright session/state shared between Upgrade Center and the runner containers. Kept separate because it is also mounted into runner containers and its ownership is managed for GID 1001. |

### Docker Socket Mount

`/var/run/docker.sock:/var/run/docker.sock` allows Upgrade Center to pull new images, stop running containers, create replacement containers, run Playwright validation containers, and perform rollback.

---

## Playwright Validation

Upgrade Center uses Playwright runner containers for pre-upgrade validation, post-upgrade validation, and cleanup. The runner image is chosen from the release metadata for the target version, pulled automatically, and attached to the product container's Docker network. Test reports and results are uploaded back to Upgrade Center (`http://bold-upgrade-center/upgrade-center/api/playwright-reports` and `.../playwright-results`) and stored under `uc_data`.

| Product | Playwright validation | Notes |
|---|---|---|
| Bold BI | Enabled (`UsePlaywrightJob: true`) | Runner containers perform validation. |
| Bold Reports | Disabled (`UsePlaywrightJob: false`) | Validation checks only the container running state and Docker `HEALTHCHECK`; cleanup is skipped. |

Defaults (in the settings files): job timeout 9000 s, cleanup timeout 900 s, pass-rate threshold 100, health check enabled with a 300 s timeout and 10 s poll.

To tune behaviour, an operator may still override any setting with an environment variable of the form `UpgradeCenter__Section__Key`, for example `UpgradeCenter__Playwright__UsePlaywrightJob` or `BOLDBI_PLAYWRIGHT_WORKERS` (parallel workers, default 1).

> The allowed image registry/repository lists are under `UpgradeCenter:Docker:AllowedImageRegistryHosts` / `AllowedImageRepositories`.

---

## URL Routing

Nginx exposes both the product and Upgrade Center on one endpoint.

| URL | Service |
|---|---|
| `http://<host>:8085` | Bold BI / Bold Reports |
| `http://<host>:8085/upgrade-center` | Upgrade Center |

---

## Deployment Steps

1. **Verify the existing deployment**: `docker ps --filter name=boldbi` (or `boldreports`), `docker volume ls`, `docker network ls`.
2. **Update Docker Compose**: add the `bold-upgrade-center` and `nginx-proxy` services, the required volumes and network, and the Nginx config file next to the compose file. Keep the product container name and its data volume unchanged.
3. **Remove the product's direct port mapping** (for example `8080:80`); Nginx handles incoming requests.
4. **Start the services**: `docker compose up -d`, then `docker compose logs -f bold-upgrade-center`.
5. **Open Upgrade Center**: `http://<server-host>:8085/upgrade-center` and sign in with your administrator credentials.
6. **Upgrade**: review available versions, select the target version, start the upgrade, and monitor progress and validation results.

If any validation step fails, Upgrade Center restores the previous Docker image and database state and returns the environment to its original working condition.

> Store administrator credentials securely and avoid committing them to source control.
