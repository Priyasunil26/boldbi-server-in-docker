"""Create an E2B sandbox and run Bold BI (single-container eval image) in Docker.

Usage:
    pip install e2b
    export E2B_API_KEY=...
    python deploy_boldbi.py
"""
import time
import urllib.request

from e2b import Sandbox

IMAGE = "syncfusion/boldbi:17.1.30-eval"
PORT = 8085  # host port mapped to container port 80
TIMEOUT = 3600  # sandbox lifetime in seconds


def sh(sbx, cmd, **kw):
    r = sbx.commands.run(cmd, user="root", timeout=kw.pop("timeout", 600), **kw)
    return r.stdout


def main():
    # Use a template with 8+ GB RAM (Bold BI needs it) and Docker preinstalled if you have one;
    # otherwise Docker is installed below on the default template.
    sbx = Sandbox.create(timeout=TIMEOUT)
    print("Sandbox:", sbx.sandbox_id)

    if "Docker version" not in sbx.commands.run("docker --version || true", user="root").stdout:
        print("Installing Docker...")
        sh(sbx, "curl -fsSL https://get.docker.com | sh", timeout=600)
    sh(sbx, "(pgrep dockerd || nohup dockerd >/var/log/dockerd.log 2>&1 &) ; sleep 8; docker info >/dev/null")

    print("Starting Bold BI...")
    sh(sbx, "docker rm -f boldbi 2>/dev/null || true")
    sh(
        sbx,
        f"docker run -d --name boldbi --restart always -p {PORT}:80 "
        "-e BOLD_SERVICES_DB_TYPE=postgresql -e BOLD_SERVICES_DB_HOST=localhost "
        "-e BOLD_SERVICES_POSTGRESQL_MAINTENANCE_DB=postgres "
        "-e BOLD_SERVICES_DB_USER=postgres -e BOLD_SERVICES_DB_PASSWORD='Admin@123' "
        "-e BOLD_SERVICES_USER_EMAIL=testuser@boldbi.com "
        "-e BOLD_SERVICES_USER_PASSWORD='Admin@123' "
        "-v boldbi_data:/application/app_data -v db_data:/var/lib/postgresql "
        f"{IMAGE}",
        timeout=1200,
    )

    url = "https://" + sbx.get_host(PORT)
    print("Waiting for", url)
    for _ in range(60):
        try:
            urllib.request.urlopen(url, timeout=10)
            break
        except Exception as e:
            code = getattr(e, "code", None)
            if code and code < 500:
                break
            time.sleep(10)
    print("Bold BI URL:", url)
    print("Logs: docker logs -f boldbi (inside sandbox", sbx.sandbox_id + ")")


if __name__ == "__main__":
    main()
