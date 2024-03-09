"""Dataclasses for domains and their records"""

import json
import logging
from dataclasses import asdict, dataclass, field

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


def print_dc(domain: Domain):
    """Print a dataclass as JSON"""
    print(json.dumps(asdict(domain), indent=2))
