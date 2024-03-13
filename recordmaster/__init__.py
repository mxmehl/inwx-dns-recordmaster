# SPDX-FileCopyrightText: 2024 Max Mehl <https://mehl.mx>
#
# SPDX-License-Identifier: GPL-3.0-only

"""Global init file"""

import logging
from importlib.metadata import version

__version__ = version("inwx-dns-recordmaster")

RECORD_KEYS = ("id", "name", "type", "content", "ttl", "prio")

DEFAULT_APP_CONFIG = """# App configuration for INWX DNS Recordmaster.
# This is not the place for domain records, these can be anywhere and used with the -c flag

# Login data for the INWX API. Can also be a sub-account
[inwx_account]
# Username and password are both required
username = ""
password = ""

# In case your account is 2FA-protected, you can add the TOTP shared secret here
# The program will automatically create a TOTP token for you.
# Note that this may reduce the account's security drastically. It may be better
# to create a sub-account with restricted access. You may also ask the INWX
# support to limit access to this account to certain IP addresses.
shared_secret = ""

# Whether to use the INWX test instance at https://www.ote.inwx.de. Default: false
test_instance = false
"""


def configure_logger(args) -> logging.Logger:
    """Set logging options"""
    log = logging.getLogger()
    logging.basicConfig(
        encoding="utf-8",
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Set loglevel based on args
    if args.debug:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)

    return log
