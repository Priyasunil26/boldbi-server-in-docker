from e2b import Template, default_build_logger

from template import template

# Memory is fixed at template build time. Bold BI needs ~8 GB.
Template.build(
    template,
    "boldbi-docker",
    cpu_count=4,
    memory_mb=8192,
    min_free_disk_mb=30720,  # Bold BI image is large; default leaves ~10 GB
    on_build_logs=default_build_logger(),
)
