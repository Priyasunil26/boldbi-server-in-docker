# Upgrade Center for Bold BI in Docker

## Overview

The Upgrade Center is a **dedicated upgrade management** service that allows administrators to upgrade an existing Bold BI Docker deployment directly from the application interface without manually downloading or managing Docker images.

With Upgrade Center, administrators can:

- Check for available Bold BI updates.
- Perform upgrades directly from the administration portal.
- Validate the environment before and after upgrades.
- Automatically back up required database objects when schema updates are involved.
- Automatically roll back to the previous version if an upgrade fails.

> **Note:** Only users with **Bold BI Administrator** privileges can access and perform upgrades through the Upgrade Center.

---

## How Upgrade Center Works

When an upgrade is initiated, Upgrade Center automatically performs the following steps:

1. Detects the currently installed Bold BI version.
2. Checks for available versions from the release service.
3. Creates database backups when database script changes are required.
4. Runs pre-upgrade validation tests using Playwright.
5. Upgrades the Bold BI container to the selected version.
6. Performs application health checks.
7. Executes post-upgrade validation tests.
8. Cleans up temporary validation data.
9. Automatically rolls back to the previous version if validation fails.

---

## Prerequisites

Before deploying Upgrade Center, ensure the following requirements are met:

### Required Components

- An existing and running **Bold BI Docker deployment**.
- The Bold BI container must use the following container name:

```yaml
container_name: boldbi
```

- Docker Engine must be accessible through:

```text
/var/run/docker.sock
```

- Internet access must be available to retrieve release information.
- The Upgrade Center and Bold BI containers must share the same Docker network.

### Security Notice

> Mounting the Docker socket (`/var/run/docker.sock`) grants administrative access to Docker on the host machine. Restrict access to Upgrade Center and allow only trusted administrators.

---

## Deployment Architecture

The deployment consists of the following containers:

| Container | Purpose |
|------------|------------|
| **boldbi** | Main Bold BI application |
| **bold-upgrade-center** | Handles upgrade operations |
| **proxy (Traefik)** | Routes requests to Bold BI and Upgrade Center |

---

## Docker Compose Configuration

Add the following services to your existing `docker-compose.yml` file.

### Upgrade Center Service

```yaml
bold-upgrade-center:
  image: docker.io/syncfusion/dev-boldbi-upgrade-center:<version>
  container_name: bold-upgrade-center
  user: "0:0"
  restart: unless-stopped

  depends_on:
    - boldbi

  environment:
    UpgradeCenter__ExecutionEnvironment: "Docker"
    UpgradeCenter__IntegrationMode: "Standalone"
    UpgradeCenter__DeploymentMode: "BoldBI"

    BOLD_ADMIN_USERNAME: "<admin-user>"
    BOLD_ADMIN_PASSWORD: "<admin-password>"

  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
    - boldbi_data:/application/app_data:ro
    - uc-dataprotection:/app/App_Data/DataProtectionKeys
    - uc-reports:/app/App_Data/PlaywrightReports
    - bold-upgrade-center-playwright-state:/app/playwright-shared-state

  networks:
    - boldbi
```

### Traefik Proxy Service

```yaml
proxy:
  image: traefik:v2.11
  container_name: bold-proxy
  restart: unless-stopped

  ports:
    - "8090:80"

  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro

  networks:
    - boldbi

  depends_on:
    - boldbi
    - bold-upgrade-center
```

### Networks and Volumes

```yaml
networks:
  boldbi:

volumes:
  boldbi_data:
  uc-dataprotection:
  uc-reports:
  bold-upgrade-center-playwright-state:
```

---

## Important Configuration Settings

### Runtime Configuration

| Setting | Description |
|----------|-------------|
| `UpgradeCenter__ExecutionEnvironment` | Specifies the deployment environment. Use `Docker`. |
| `UpgradeCenter__IntegrationMode` | Use `Standalone` for standard Docker deployments. |
| `UpgradeCenter__DeploymentMode` | Specifies the product being upgraded (`BoldBI`). |

---

### Docker Configuration

| Setting | Description |
|----------|-------------|
| `UpgradeCenter__Docker__DockerHost` | Docker API endpoint used by Upgrade Center. |
| `UpgradeCenter__Docker__ContainerName` | Name of the Bold BI container to upgrade. |
| `UpgradeCenter__Docker__ImageRepository` | Docker image repository used during upgrades. |
| `UpgradeCenter__Docker__ComponentName` | Component name displayed in logs and UI. |
| `UpgradeCenter__Docker__MaintenanceWindowConfirmed` | Confirms downtime is acceptable during upgrade execution. |
| `UpgradeCenter__Docker__PlaywrightSharedStateVolumeName` | Shared Playwright state volume. |
| `UpgradeCenter__Docker__StopTimeoutSeconds` | Optional timeout before forcefully stopping containers. |

---

### Administrator Credentials

Upgrade validation requires a valid Bold BI administrator account.

```yaml
BOLD_ADMIN_USERNAME: "<admin-user>"
BOLD_ADMIN_PASSWORD: "<admin-password>"
```

> Store administrator credentials securely and avoid committing them to source control repositories.

---

### Release Feed Configuration

| Setting | Description |
|----------|-------------|
| `UpgradeCenter__BiReleaseVersionsApiUrl` | Retrieves available Bold BI versions. |
| `UpgradeCenter__Kubernetes__AllowedImageRegistryHosts__0` | Allowed Docker registry host. |
| `UpgradeCenter__Kubernetes__AllowedImageRepositories__0` | Allowed Docker image repository. |

> Although the configuration names contain *Kubernetes*, these settings are also used in Docker deployments.

---

### Playwright Validation Settings

Upgrade Center uses Playwright-based automated testing to validate upgrades.

| Setting | Description |
|----------|-------------|
| `UpgradeCenter__Playwright__UsePlaywrightJob` | Enables Playwright validation. |
| `UpgradeCenter__Playwright__JobTimeoutSeconds` | Maximum duration for validation execution. |
| `UpgradeCenter__Playwright__CleanupJobTimeoutSeconds` | Maximum duration for cleanup activities. |
| `UpgradeCenter__Playwright__PassRateThreshold` | Required test pass percentage. |
| `BOLDBI_PLAYWRIGHT_WORKERS` | Number of parallel Playwright workers. |

## Volume Configuration

The following volumes are required for Upgrade Center.

| Volume | Purpose |
|----------|----------|
| `boldbi_data` | Provides access to Bold BI configuration and encryption files. |
| `uc-dataprotection` | Stores data protection keys across container restarts. |
| `uc-reports` | Stores Playwright validation reports. |
| `bold-upgrade-center-playwright-state` | Stores Playwright session and state information. |

### Docker Socket Mount

```yaml
/var/run/docker.sock:/var/run/docker.sock
```

This mount allows Upgrade Center to:

- Pull new images
- Stop running containers
- Create replacement containers
- Execute validation workloads
- Perform rollback operations

---

## URL Routing

Traefik exposes both Bold BI and Upgrade Center using a single endpoint.

| URL | Service |
|------|----------|
| `http://<host>:8090` | Bold BI |
| `http://<host>:8090/upgrade-center` | Upgrade Center |

This approach eliminates the need to expose additional ports.

---

## Deployment Steps

### Step 1: Verify Existing Deployment

Confirm the Bold BI container is running:

```bash
docker ps --filter name=boldbi
```

Verify available Docker volumes:

```bash
docker volume ls
```

Verify available Docker networks:

```bash
docker network ls
```

---

### Step 2: Update Docker Compose

Add the following components:

- `bold-upgrade-center` service
- `proxy` service
- Required Docker volumes
- Required Docker network configuration

Ensure:

- The Bold BI container name remains `boldbi`.
- The `boldbi_data` volume remains unchanged.

---

### Step 3: Remove Existing Port Mapping from Bold BI

If the Bold BI container already exposes a port directly, remove that mapping.

Example:

```yaml
ports:
  - "8080:80"
```

Traefik will handle incoming requests and route them appropriately.

---

### Step 4: Start the Services

Start all containers:

```bash
docker-compose up -d
```

Monitor Upgrade Center logs:

```bash
docker-compose logs -f bold-upgrade-center
```

---

### Step 5: Access Upgrade Center

Open the following URL in your browser:

```text
http://<server-host>:8090/upgrade-center
```

Sign in using your Bold BI administrator credentials.

---

### Step 6: Perform an Upgrade

1. Open the Upgrade Center dashboard.
2. Review available versions.
3. Select the target version.
4. Start the upgrade process.
5. Monitor upgrade progress and validation results.

If any validation step fails, Upgrade Center automatically:

- Restores the previous Docker image.
- Restores the previous database state.
- Returns the environment to its original working condition.

---

## Troubleshooting

### Container Exits with Status Code 137

**Cause**

The application did not stop within the expected timeout period.

**Resolution**

Increase the following setting:

```yaml
UpgradeCenter__Docker__StopTimeoutSeconds
```

---

### Application Health Check Fails

**Cause**

Bold BI requires additional startup time.

**Resolution**

Increase:

```yaml
UpgradeCenter__ProductHealthCheck__TimeoutSeconds
```

Review application logs:

```bash
docker logs boldbi
```

---

### Playwright Report Upload Failure

**Cause**

Playwright cannot communicate with Upgrade Center.

**Resolution**

Verify:

- Upload URLs reference `bold-upgrade-center`.
- Both containers are connected to the same network.
- Container-to-container DNS resolution is functioning correctly.

---

### Configuration File Not Found

**Cause**

Upgrade Center cannot access required configuration files.

**Resolution**

Verify that the following files exist:

```text
/application/app_data/configuration/config.json
```

```text
/application/app_data/configuration/privatekeys.dat
```

Also ensure the `boldbi_data` volume is mounted correctly.

---

### Administrator Login Failure

**Cause**

Invalid administrator credentials.

**Resolution**

Verify the following environment variables:

```yaml
BOLD_ADMIN_USERNAME
BOLD_ADMIN_PASSWORD
```

Ensure they contain valid Bold BI administrator account credentials.

---

### Unauthorized Access

**Cause**

The signed-in user does not have administrator privileges.

**Resolution**

Sign in using a Bold BI account with administrator permissions.

---

## Summary

The Upgrade Center simplifies the process of upgrading Bold BI Docker deployments by automating version discovery, validation, deployment, health checks, and rollback procedures. By deploying Upgrade Center alongside Bold BI and Traefik, administrators can perform upgrades directly from the application interface while minimizing operational effort and reducing upgrade risks.
