# SPDX-FileCopyrightText: 2024 Max Mehl <https://mehl.mx>
#
# SPDX-License-Identifier: GPL-3.0-only

"""App configuration functions"""

import logging
import sys
from os import makedirs
from os.path import dirname, join

import toml
from platformdirs import user_config_dir

from . import DEFAULT_APP_CONFIG


def _initialize_config_file(configfile: str) -> dict:
    """Create a new app configuration file with default values"""

    # Create directory in case it does not exist
    makedirs(dirname(configfile), exist_ok=True)

    # Write the default config in TOML format to a new file
    with open(configfile, mode="w", encoding="UTF-8") as tomlfile:
        tomlfile.write(DEFAULT_APP_CONFIG)

    return toml.loads(DEFAULT_APP_CONFIG)


def _read_app_config_file() -> dict:
    """Read full app configuration"""
    config_file = join(user_config_dir("inwx-dns-recordmaster", ensure_exists=True), "config.toml")
    try:
        with open(config_file, mode="r", encoding="UTF-8") as tomlfile:
            app_config = toml.load(tomlfile)

    except FileNotFoundError:
        logging.warning(
            "App configuration file '%s' has not been found. Initializing a new empty one.",
            config_file,
        )
        app_config = _initialize_config_file(config_file)

    except toml.decoder.TomlDecodeError:
        logging.error("Error reading configuration file '%s'. Check the syntax!", config_file)
        sys.exit(1)

    return app_config


def get_app_config(key: str = ""):
    """Return a specific section from the app configuration, or the whole config"""

    if key:
        return _read_app_config_file()[key]

    return _read_app_config_file
