# Deploy Bold BI (single container) on an E2B sandbox

This guide builds a custom E2B template (Docker, 4 CPU, 8 GB RAM, ~25 GB free disk)
and runs the Bold BI evaluation image (`syncfusion/boldbi:17.1.30-eval`, PostgreSQL included)
inside a sandbox created from it.

> The eval image is for evaluation only, not production.

## Why a custom template?
The default E2B template has 512 MB RAM and no Docker. Bold BI needs about 8 GB RAM and
a large disk for its image. Memory and disk are fixed when a template is built.

## Prerequisites
- An E2B account and API key (E2B dashboard, Keys). Your plan must allow 8 GB RAM and a larger disk.
- Python 3.9+ and `python3-venv`.

## Files in this folder
| File | Purpose |
| --- | --- |
| `requirements.txt` | Python dependency (`e2b`) |
| `template.py` | Template definition: Ubuntu 22.04 + Docker Engine |
| `build_template.py` | Builds the template `boldbi-docker` (4 CPU, 8 GB RAM, 25 GB free disk) |
| `deploy_boldbi.py` | Creates a sandbox from the template, starts Bold BI, prints the public URL |

## Step 1: Set up Python
```bash
sudo apt install -y python3-venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Step 2: Set your API key
```bash
export E2B_API_KEY="<your E2B API key>"
```
No `e2b auth login` is needed. Do not commit the key.

## Step 3: Build the template (once)
```bash
python build_template.py
```
Takes about 2 minutes. In the log, check `resize-disk: free ... -> ...` shows about 25,000 MiB.
Key settings in `build_template.py`:
```python
cpu_count=4,
memory_mb=8192,
min_free_disk_mb=25600,
```
If your plan rejects these values, lower them, but keep disk above ~20 GB or the image
pull fails with `no space left on device`.

## Step 4: Deploy Bold BI
```bash
export E2B_TEMPLATE=boldbi-docker
python deploy_boldbi.py
```
The script:
1. Creates a sandbox from the template with public traffic allowed (otherwise E2B returns 403 without an `e2b-traffic-access-token` header).
2. Starts Docker if needed.
3. Runs the Bold BI container, mapping port 8085 to container port 80.
4. Waits for the app, then prints the public URL.

The first image pull takes several minutes. A 502 during first start is normal.

## Step 5: Use Bold BI
1. Open the printed URL, for example `https://8085-<sandbox-id>.e2b.app`.
2. Choose **Proceed with 30 Days Trial** (or activate a license).
3. Sign in with `testuser@boldbi.com` / `Admin@123`.

## Managing the sandbox
- Sandboxes last 1 hour by default (`TIMEOUT` in `deploy_boldbi.py`) and then stop. Data is lost with the sandbox.
- Delete unused sandboxes in the E2B dashboard to stay within your concurrency limit.
- Container logs: run `docker logs -f boldbi` inside the sandbox.

## Troubleshooting
| Symptom | Cause / fix |
| --- | --- |
| 403 `Token header 'e2b-traffic-access-token' is missing` | Sandbox was created without public traffic. Use the current `deploy_boldbi.py`. |
| Only 512 MB RAM in dashboard | `E2B_TEMPLATE` not set, so the `base` template was used. |
| `no space left on device` while pulling | Template disk too small. Rebuild with a larger `min_free_disk_mb`. |
| 502 for a few minutes | Bold BI is still starting. Wait. |
| Docker daemon not running | Check `/var/log/dockerd.log` inside the sandbox. |
