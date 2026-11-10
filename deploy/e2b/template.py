from e2b import Template

# Ubuntu 22.04 with Docker Engine preinstalled.
template = (
    Template()
    .from_ubuntu_image("22.04")
    .run_cmd(
        "apt-get update && apt-get install -y ca-certificates curl iptables procps "
        "&& curl -fsSL https://get.docker.com | sh",
        user="root",
    )
)
