"""Functions for handling local configuration files"""

import json
import logging
import sys
from os import listdir, path

import yaml
from INWX.Domrobot import ApiClient  # type: ignore

from ._api import inwx_api
from ._data import Domain, Record


def find_valid_local_records_files(configdir: str):
    """Get all local domain configuration files"""
    logging.debug("Gather locally configured domains from configuration directory '%s'", configdir)

    dcfg_files_abs = []

    for file in listdir(configdir):
        file = path.abspath(path.join(configdir, file))
        if file.endswith((".yaml", ".yml")):
            dcfg_files_abs.append(file)
        else:
            logging.warning(
                "File %s does not match naming convention and will be ignored",
                file,
            )

    return dcfg_files_abs


def _read_local_records_from_file(cfg_file):
    """Read configuration file for a specific domain"""
    domain = path.splitext(path.basename(cfg_file))[0]

    with open(cfg_file, mode="r", encoding="UTF-8") as ymlfile:
        ymldocs = yaml.safe_load_all(ymlfile)

        root = next(ymldocs)
        records = next(ymldocs)

    return domain, root, records


def convert_local_records_to_data(domain: Domain, configfile: str) -> None:
    """Read domain configuration with records from local file and put into dataclass"""
    # Read local domain config
    domain.name, root_records, sub_records = _read_local_records_from_file(configfile)

    logging.debug("[%s] Reading local domain config", domain.name)

    # Adding root records
    for rec in root_records:
        record = Record()

        record.import_records(domain=domain.name, data=rec)

        domain.local_records.append(record)

    # Adding subdomain records
    for subdomain, recs in sub_records.items():
        # The local configuration layout is a bit different from the internal
        # data model, to make configuration files a bit shorter. We convert this
        # here.
        for rec in recs:
            record = Record()

            record.import_records(root=domain.name, domain=subdomain, data=rec)

            domain.local_records.append(record)


def check_local_records_config(domain: str, records: list[Record]):
    """Find common errors in local records confiuration files"""
    # Find records with IDs
    local_ids = [rec for rec in records if rec.id is not None]
    if local_ids:
        logging.error(
            "[%s] You set IDs in your local configuration for the following "
            "records. This is forbidden. %s",
            domain,
            local_ids,
        )
        sys.exit(1)

    # Find local records whose name+type+content is equal
    duplicates = []
    seen = set()
    for rec in records:
        # Create a "signature" for each local record
        signature = (rec.type, rec.name, rec.content)
        # Signature has already been seen before -> duplicate
        if signature in seen:
            duplicates.append(rec)
        # Otherwise, note as "seen" for the first time
        else:
            seen.add(signature)

    if duplicates:
        logging.error(
            "[%s] These locally defined records carry the same type, name, and "
            "content as an earlier one. This is forbidden and would lead to "
            "strange results: %s",
            domain,
            duplicates,
        )
        sys.exit(1)

    # TTL and Prio no ints
    no_ints = [
        rec for rec in records if not isinstance(rec.ttl, int) or not isinstance(rec.prio, int)
    ]
    if no_ints:
        logging.error(
            "[%s] These locally defined records contain 'ttl' and/or 'prio' "
            "values that are not integers: %s",
            domain,
            no_ints,
        )
        sys.exit(1)


def convert_remote_records_to_data(api: ApiClient, domain: Domain, local: str):
    """Request domain configuration with records from the remote (INWX) and put into dataclass"""

    # Load remote configuration from remote via API call, or from local file
    if not local:
        domain_remote = inwx_api(api, "nameserver.info", domain=domain.name)["resData"]
    else:
        with open(local, mode="r", encoding="UTF-8") as jsonfile:
            domain_remote = json.load(jsonfile)

    domain.id = domain_remote["roId"]

    for rec in domain_remote["record"]:
        record = Record()

        record.import_records(data=rec)

        domain.remote_records.append(record)
