# SPDX-FileCopyrightText: 2024 Max Mehl <https://mehl.mx>
#
# SPDX-License-Identifier: GPL-3.0-only

"""Sync INWX nameserver entries with local state"""

import argparse
import logging
import sys

from INWX.Domrobot import ApiClient  # type: ignore

from . import __version__, configure_logger
from ._api import api_login
from ._data import Domain, cache_data
from ._get_records import (
    check_local_records_config,
    combine_local_records,
    convert_dict_to_yaml,
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
subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

# Sync command
parser_sync = subparsers.add_parser(
    "sync",
    help="Synchronise DNS records from local configuration to productive INWX nameserver entries",
)
parser_sync.add_argument(
    "-c",
    "--dns-config",
    required=True,
    help="The directory where the DNS configuration files for each domain reside",
)
parser_sync.add_argument(
    "-d",
    "--domain",
    help="Only run the program for the given domain",
)
parser_sync.add_argument(
    "-p",
    "--preserve-remote",
    action="store_true",
    help="Preserve remote records that are not configured locally.",
)
parser_sync.add_argument(
    "--dry",
    action="store_true",
    help="Dry run, do not change anything at remote",
)
parser_sync.add_argument(
    "--interactive",
    action="store_true",
    help="Ask to confirm each change at INWX before executing it",
)

# Convert command
parser_convert = subparsers.add_parser(
    "convert",
    help="Convert existing INWX domain records to the local configuration's YAML file format",
)
parser_convert.add_argument(
    "-d",
    "--domain",
    required=True,
    help=(
        "The domain whose records want to convert. "
        "It respects the values for --ignore-types, so SOA records by default. "
        "Will not make any modifications at the remote."
    ),
)

# General flags
parser.add_argument(
    "-i",
    "--ignore-types",
    default="SOA",
    help=(
        "A comma-separated list of record types which will be ignored when "
        "considering remote records. Leave empty do consider all types. Example: -i SOA,NS."
    ),
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
parser.add_argument("--version", action="version", version="%(prog)s " + __version__)


def sync(
    # pylint: disable=too-many-arguments, dangerous-default-value
    api: ApiClient,
    dns_config: str,
    only_domain: str = "",
    preserve_remote: bool = False,
    ignore_types: list = ["SOA"],
    dry: bool = False,
    debug: bool = False,
    interactive: bool = False,
    api_response: str = "",
):
    """The sync command"""
    # --api-response implies --dry
    if api_response:
        dry = True

        if not only_domain:
            print(
                "ERROR: When using the -a/--api-response option you must also provide "
                "the corresponding --domain"
            )
            sys.exit(1)

    if dry:
        logging.info("Dry-run mode activated. No changes on remote DNS entries will be executed.")

    # Load domain records configuration files
    records_files = find_valid_local_records_files(dns_config)

    # Normal procedure
    for domainname, records in combine_local_records(records_files).items():
        # If `-d`/`--domain` given, skip all other domains
        if only_domain and domainname != only_domain:
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
        convert_remote_records_to_data(api, domain, api_response)

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
        cache_data(domain, debug)

        # 2. Sync local to existing remote records
        sync_existing_local_to_remote(api, domain=domain, dry=dry, interactive=interactive)

        # 3. Create records that only exist locally at remote
        create_missing_at_remote(
            api, domain=domain, records=unmatched_local, dry=dry, interactive=interactive
        )

        # 4. Delete records that only exist remotely, unless their types are ignored
        if not preserve_remote:
            delete_unconfigured_at_remote(
                api,
                domain=domain,
                records=unmatched_remote,
                dry=dry,
                interactive=interactive,
                ignore_types=ignore_types,
            )
        else:
            logging.info(
                "[%s] Skipping the deletion of %s unconfigured records at remote, "
                "as requested by the -p flag",
                domainname,
                len(unmatched_remote),
            )


def convert(
    # pylint: disable=dangerous-default-value
    api: ApiClient,
    converted_domain: str,
    ignore_types: list = ["SOA"],
    api_response: str = "",
):
    """The convert command"""
    # Create and initiate domain dataclass
    domain = Domain()
    domain.name = converted_domain

    # Read remote configuration into domain dataclass
    convert_remote_records_to_data(api, domain, api_response)

    # Convert to YAML
    yml_dict = domain.to_local_conf_format(domain.remote_records, ignore_types)
    logging.info(
        "[%s] Remote records at INWX convert to local YAML configuration format:\n",
        domain.name,
    )
    print(convert_dict_to_yaml(yml_dict))


def main():
    "Main function"
    # Process arguments
    args = parser.parse_args()

    # Convert --ignore-types to list if it's just a string (the default)
    args.ignore_types = args.ignore_types.split(",")

    # Set logger
    configure_logger(args=args)

    # Login to API
    api = api_login(args.api_response, args.debug)

    # Figure out which command to run
    if args.command == "sync":
        sync(
            api=api,
            dns_config=args.dns_config,
            only_domain=args.domain,
            preserve_remote=args.preserve_remote,
            ignore_types=args.ignore_types,
            dry=args.dry,
            debug=args.debug,
            interactive=args.interactive,
            api_response=args.api_response,
        )
    elif args.command == "convert":
        convert(
            api=api,
            converted_domain=args.domain,
            ignore_types=args.ignore_types,
            api_response=args.api_response,
        )
    else:
        logging.error("No valid command provided!")
        sys.exit(1)
