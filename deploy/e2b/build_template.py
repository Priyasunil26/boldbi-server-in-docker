from e2b import Template, default_build_logger

from template import template

# Memory is fixed at template build time. Bold BI needs ~8 GB.
Template.build(
    template,
    "boldbi-docker",
    cpu_count=4,
    memory_mb=8192,
    on_build_logs=default_build_logger(),
)
