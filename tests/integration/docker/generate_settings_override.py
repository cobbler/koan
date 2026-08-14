#!/usr/bin/env python3
"""
Generate a docker-compose override that patches Cobbler's settings.yaml (embedded as a
string inside docker/compose/base.yml's "cobbler-settings" config) to enable
register_new_installs, so the integration suite's cobbler-register tests can run.

register_new_installs is gated behind allow_dynamic_settings, which the settings.yaml
comment itself says can only be changed by editing the file and restarting cobblerd -
it cannot be flipped live via the modify_setting() RPC. So this has to be baked into the
compose stack's config before startup, not toggled afterwards.

This reads the *current* base.yml from whatever Cobbler checkout the CI job just cloned,
rather than hand-maintaining a duplicated settings blob in the koan repo - the latter
would silently drift out of sync with Cobbler's actual defaults over time, which is
exactly the kind of problem this whole integration suite exists to catch.

Usage:
    generate_settings_override.py --base <cobbler-checkout>/docker/compose/base.yml \\
        --out <output-path>.yml
"""

import argparse
import sys

import yaml


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base", required=True, help="Path to Cobbler's docker/compose/base.yml"
    )
    parser.add_argument("--out", required=True, help="Path to write the override to")
    args = parser.parse_args()

    with open(args.base, encoding="utf-8") as handle:
        base = yaml.safe_load(handle)

    settings_text = base["configs"]["cobbler-settings"]["content"]
    settings = yaml.safe_load(settings_text)

    settings["allow_dynamic_settings"] = True
    settings["register_new_installs"] = True

    override = {
        "configs": {
            "cobbler-settings": {
                "content": yaml.safe_dump(settings, sort_keys=False),
            }
        }
    }

    with open(args.out, "w", encoding="utf-8") as handle:
        yaml.safe_dump(override, handle, sort_keys=False)

    return 0


if __name__ == "__main__":
    sys.exit(main())
