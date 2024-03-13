# SPDX-FileCopyrightText: 2024 Max Mehl <https://mehl.mx>
#
# SPDX-License-Identifier: GPL-3.0-only

"""Dataclasses for domains and their records"""

from __future__ import annotations  # support "int | None"

import json
import logging
from dataclasses import asdict, dataclass, field
from os.path import join
from time import time

from platformdirs import user_cache_dir

from . import RECORD_KEYS


@dataclass
class Record:
    """Dataclass holding a nameserver record, be it remote or local"""

    # nameserver details
    id: int | None = None
    name: str = ""
    type: str = ""
    content: str = ""
    ttl: int = 3600
    prio: int = 0

    def import_records(self, data: dict, domain: str = "", root: str = ""):
        """Update records by providing a dict"""

        # If handling a subdomain record, prepend the root domain, if given
        if domain and root:
            self.name = f"{domain}.{root}"
        # If handling root records
        elif domain and not root:
            self.name = domain
        # There is a name already provided in 'data'
        else:
            pass

        for key, val in data.items():
            if key in RECORD_KEYS:
                setattr(self, key, val)
            else:
                logging.warning(
                    "Ignored importing record data for domain '%s'. Key: '%s', Value: '%s'",
                    domain,
                    key,
                    val,
                )


@dataclass
class Domain:
    """Dataclass holding general domain information"""

    id: int | None = None
    name: str = ""
    # Lists of Record elements
    remote_records: list[Record] = field(default_factory=list)
    local_records: list[Record] = field(default_factory=list)


def dc2json(domain: Domain) -> str:
    """return a dataclass as JSON"""
    return json.dumps(asdict(domain), indent=2)


def cache_data(domain: Domain, debug: bool):
    """Cache the current state of data before running any syncs"""

    # ~/.cache/inwx-dns-recordmaster/example.com-1521462189.json
    cache_file = join(
        user_cache_dir("inwx-dns-recordmaster", ensure_exists=True),
        f"{domain.name}-{int(time())}.json",
    )

    # Convert dataclass to JSON, write in cache file
    jsondc = dc2json(domain)
    logging.debug("[%s] Writing current data of the domain to '%s'", domain.name, cache_file)
    with open(cache_file, mode="w", encoding="UTF-8") as cachefile:
        cachefile.write(jsondc)

    # If --debug, also print current dataclass
    if debug:
        logging.debug("[%s] Current data of the domain after matching:", domain.name)
        print(jsondc)
