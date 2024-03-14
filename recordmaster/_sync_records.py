# SPDX-FileCopyrightText: 2024 Max Mehl <https://mehl.mx>
#
# SPDX-License-Identifier: GPL-3.0-only

"""DNS record sync operations between local and remote"""

import logging

from INWX.Domrobot import ApiClient  # type: ignore

from . import RECORD_KEYS
from ._api import inwx_api
from ._data import Domain, Record


def sync_existing_local_to_remote(
    api: ApiClient, domain: Domain, dry: bool, interactive: bool
) -> None:
    """Compare previously matched local records to remote ones. If differences, update remote"""
    # pylint: disable=too-many-nested-blocks
    # Loop over local records which have an ID, so matched to a remote entry
    for loc_rec in [loc_rec for loc_rec in domain.local_records if loc_rec.id]:
        # For each ID, compare content, ttl and prio
        for key in ("content", "ttl", "prio"):
            # Get local and corresponding remote attribute
            loc_val = getattr(loc_rec, key)
            rem_val = next(
                getattr(rem_rec, key)
                for rem_rec in domain.remote_records
                if rem_rec.id == loc_rec.id
            )
            # Update attribute at remote if values differ
            if loc_val and (loc_val != rem_val):
                # Log and update record
                logging.info(
                    "[%s] Updating '%s' record of '%s': '%s' from '%s' to '%s'",
                    domain.name,
                    loc_rec.type,
                    loc_rec.name,
                    key,
                    rem_val,
                    loc_val,
                )

                # Update record via API call
                inwx_api(
                    api,
                    "nameserver.updateRecord",
                    interactive=interactive,
                    dry=dry,
                    id=loc_rec.id,
                    **{key: loc_val},
                )
            else:
                # No action needed as records are equal or undefined
                logging.debug(
                    "[%s] (%s) %s equal: %s = %s", loc_rec.name, loc_rec.id, key, rem_val, loc_val
                )


def create_missing_at_remote(
    api: ApiClient, domain: Domain, records: list[Record], dry: bool, interactive: bool
):
    """Create records that only exist locally but not remotely"""
    for rec in records:
        # Only add record parameter to API call that are set locally
        newrecord = {}
        for key in RECORD_KEYS:
            if value := getattr(rec, key):
                newrecord[key] = value

        logging.info("[%s] Creating new record: %s", domain.name, newrecord)

        # Run the creation of the new nameserver record with API
        inwx_api(
            api,
            "nameserver.createRecord",
            interactive=interactive,
            dry=dry,
            domain=domain.name,
            **newrecord,
        )


def delete_unconfigured_at_remote(
    # pylint: disable=too-many-arguments
    api: ApiClient,
    domain: Domain,
    records: list[Record],
    dry: bool,
    interactive: bool,
    ignore_types: list,
):
    """Delete records that only exist remotely but not locally, except some types"""
    for rec in records:
        if rec.type not in ignore_types:
            logging.info(
                "[%s] Deleting record at remote as it is not configured locally: %s",
                domain.name,
                rec,
            )

            # Run the deletion of the nameserver record with API
            inwx_api(api, "nameserver.deleteRecord", interactive=interactive, dry=dry, id=rec.id)
        else:
            logging.info(
                "[%s] This remote record is not configured locally, but you "
                "requested to not delete remote records of this type: %s",
                domain.name,
                rec,
            )
