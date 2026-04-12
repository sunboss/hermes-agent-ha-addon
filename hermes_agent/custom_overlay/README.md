Place files here to override or add files inside the upstream Hermes source tree during image build.

Examples:
- custom_overlay/skills/my_skill/SKILL.md
- custom_overlay/docker/SOUL.md
- custom_overlay/plugins/my_plugin/...

At build time, this folder is copied over `/opt/hermes` after the upstream ref is checked out.
