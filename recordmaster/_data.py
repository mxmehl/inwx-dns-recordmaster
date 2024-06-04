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
class Record:  # pylint: disable=too-many-instance-attributes
    """Dataclass holding a nameserver record, be it remote or local"""

    # nameserver details
    id: int | None = None
    name: str = ""
    type: str = ""
    content: str = ""
    ttl: int = 3600
    prio: int = 0
    # pylint: disable=invalid-name
    urlRedirectType: str = ""
    urlRedirectTitle: str = ""
    urlRedirectDescription: str = ""
    urlRedirectFavIcon: str = ""
    urlRedirectKeywords: str = ""
    urlAppend: bool = False

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
                    "Ignored importing record data for domain '%s.%s'. Key: '%s', Value: '%s'",
                    domain,
                    self.name,
                    key,
                    val,
                )


@dataclass
class DomainStats:
    """Dataclass holding general statistics about the handling of a domain"""

    total_remote: int = 0
    updated: int = 0
    added: int = 0
    deleted: int = 0
    ignored: int = 0
    unchanged: int = 0
    changed: int = 0

    def stats_calc(self, domainname: str) -> None:
        """Calculate the number of unchanged records based on updates and removals"""

        self.unchanged = self.total_remote - self.updated - self.deleted
        self.changed = self.updated + self.added + self.deleted

        logging.info(
            "[%s] Domain synchronised with %s changes: %s updated, %s added, %s deleted. "
            "%s ignored, %s unchanged",
            domainname,
            self.changed,
            self.updated,
            self.added,
            self.deleted,
            self.ignored,
            self.unchanged,
        )


@dataclass
class Domain:
    """Dataclass holding general domain information"""

    id: int | None = None
    name: str = ""
    # Lists of Record elements
    remote_records: list[Record] = field(default_factory=list)
    local_records: list[Record] = field(default_factory=list)
    # Stats
    stats: DomainStats = field(default_factory=DomainStats)
    # Domain-specific options, either global or local, if present
    options: dict = field(default_factory=dict)

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

            # All the other attributes unless they have the default value
            # This is, in RECORD_KEYS, all from the 5th element, ttl
            for attr in RECORD_KEYS[4:]:
                if getattr(rec, attr) != getattr(Record, attr):
                    rec_yaml[attr] = getattr(rec, attr)

            data[name].append(rec_yaml)

        return {convert_punycode(self.name, False): data}


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


def convert_punycode(domain: str, is_punycode: bool = True) -> str:
    """Convert a domain name from human-readable to punycode, or vice versa"""
    if is_punycode:
        return domain.encode("idna").decode()

    return domain.encode().decode("idna")
