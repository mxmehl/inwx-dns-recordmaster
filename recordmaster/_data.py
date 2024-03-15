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

    def to_local_conf_format(self, records: list[Record], ignore_types: list) -> dict:
        """
        Convert the internal data format of records to a dict that matches the
        local YAML configuration
        """
        data: dict[str, list] = {}

        for rec in records:
            if rec.type in ignore_types:
                continue
            # Gather the "subdomain" as this is the format we're using
            name = rec.name.replace(self.name, "")
            name = "." if name == "" else name.rstrip(".")

            # Create key for subdomain if it doesn't exit yet
            if name not in data:
                data[name] = []

            # Type and content are straightforward, we don't need to convert it
            rec_yaml: dict[str, str | int] = {"type": rec.type, "content": rec.content}
            # TTL and prio will be set unless it's the default value
            if rec.ttl != Record.ttl:
                rec_yaml["ttl"] = rec.ttl
            if rec.prio != Record.prio:
                rec_yaml["prio"] = rec.prio

            data[name].append(rec_yaml)

        return {self.name: data}


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
