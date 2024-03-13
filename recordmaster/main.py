# SPDX-FileCopyrightText: 2024 Max Mehl <https://mehl.mx>
#
# SPDX-License-Identifier: GPL-3.0-only

"""Sync INWX nameserver entries with local state"""

import argparse
import logging
import sys

from . import __version__, configure_logger
from ._api import api_login
from ._data import Domain, cache_data
from ._get_records import (
    check_local_records_config,
    combine_local_records,
    convert_local_records_to_data,
    convert_remote_records_to_data,
    find_valid_local_records_files,
)
from ._match_records import match_remote_to_local_records
from ._sync_records import (
    create_missing_at_remote,
    delete_unconfigured_at_remote,
    sync_existing_local_to_remote,
)

parser = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
)
parser.add_argument(
    "-c",
    "--dns-config",
    required=True,
    help="The directory where the DNS configuration files for each domain reside",
)
parser.add_argument(
    "-d",
    "--domain",
    help="Only run the program for the given domain",
)
parser.add_argument(
    "-i",
    "--ignore-types",
    # action="extend",
    nargs="*",
    default="SOA",
    help=(
        "Do not delete these types of records when they are only found remotely "
        "but not locally. Leave empty do consider all types. Example: -i SOA NS."
    ),
)
parser.add_argument(
    "-p",
    "--preserve-remote",
    action="store_true",
    help="Preserve remote records that are not configured locally.",
)
parser.add_argument(
    "-a",
    "--api-response",
    default="",
    help=(
        "Read local file that simulates the API response of INWX. Makes it work offline. "
        "However, this only works with one local domain configuration file, so use -d as well!. "
        "Implies --dry"
    ),
)
parser.add_argument(
    "--debug",
    action="store_true",
    help="Read local file for remote nameserver configuration. Make it work offline.",
)
parser.add_argument(
    "--dry",
    action="store_true",
    help="Dry run, do not change anything at remote",
)
parser.add_argument("--version", action="version", version="%(prog)s " + __version__)


def main():
    "Main function"
    # Process arguments
    args = parser.parse_args()
    # --api-response implies --dry
    if args.api_response:
        args.dry = True

        if not args.domain:
            print(
                "ERROR: When using the -a/--api-response option you must also provide "
                "the corresponding --domain"
            )
            sys.exit(1)

    # Convert --ignore-types to list if
    if not isinstance(args.ignore_types, list):
        args.ignore_types = [args.ignore_types]

    # Set logger
    configure_logger(args=args)

    if args.dry:
        logging.info("Dry-run mode activated. No changes on remote DNS entries will be executed.")

    # Load domain records configuration files
    records_files = find_valid_local_records_files(args.dns_config)

    # Login to API
    api = api_login(args.api_response, args.debug)

    # for domain_config_file in find_valid_local_records_files(args.dns_config):
    for domainname, records in combine_local_records(records_files).items():
        # If `-d`/`--domain` given, skip all other domains
        if args.domain and domainname != args.domain:
            logging.info("[%s] Skipping the handling of this domain as requested by -d", domainname)
            continue

        # Initialise a new domain dataclass to hold the different local and
        # remote records
        domain = Domain()

        domain.name = domainname

        # Read local configuration into domain dataclass
        convert_local_records_to_data(domain, records)

        # Sanitize local configuration
        check_local_records_config(domain=domain.name, records=domain.local_records)

        # Read remote configuration into domain dataclass
        convert_remote_records_to_data(api, domain, args.api_response)

        # Compare remote records with the local ones. The general idea is to
        # make a multi-step sync:
        # 1. Identify nameserver entries where name+type are equal. Apply some
        #    matching logic, if necessary based on similarity, so that ideally
        #    the desired remote DNS entry just changes content-wise (and ttl and
        #    prio if wished for)
        # 2. Update matched records from local -> remote
        # 3. Whatever remains unmatched on the local side will be created on the
        #    remote
        # 4. Whatever remains unmatched on the remote side will be deleted,
        #    except a few "standard" ones like NS or SOA.
        #
        # In the data model, we will mark matched nameserver entries with adding
        # the remote entry ID to the local record.
        #
        # As a result, we have remote <-> local matches, and two lists of
        # unmatched local and remote records.

        # 1. Matching of remote -> local records
        unmatched_remote = match_remote_to_local_records(domain)

        unmatched_local = [loc_rec for loc_rec in domain.local_records if not loc_rec.id]

        # Write current data to cache file in order to ease recoveries
        cache_data(domain, args.debug)

        # 2. Sync local to existing remote records
        sync_existing_local_to_remote(api, domain=domain, dry=args.dry)

        # 3. Create records that only exist locally at remote
        create_missing_at_remote(api, domain=domain, records=unmatched_local, dry=args.dry)

        # 4. Delete records that only exist remotely, unless their types are ignored
        if not args.preserve_remote:
            delete_unconfigured_at_remote(
                api,
                domain=domain,
                records=unmatched_remote,
                dry=args.dry,
                ignore_types=args.ignore_types,
            )
        else:
            logging.info(
                "[%s] Skipping the deletion of %s unconfigured records at remote, "
                "as requested by the -p flag",
                domainname,
                len(unmatched_remote),
            )
