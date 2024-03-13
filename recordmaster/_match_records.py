# SPDX-FileCopyrightText: 2024 Max Mehl <https://mehl.mx>
#
# SPDX-License-Identifier: GPL-3.0-only

"""Functions for matching local and remote nameserver entries"""

import logging
from difflib import get_close_matches

from ._data import Domain, Record


def _find_partial_matches(domain: Domain, rem_rec: Record) -> list[Record]:
    """Find partial matches for a remote record amongst local records."""
    return [
        loc_rec
        for loc_rec in domain.local_records
        if not loc_rec.id and loc_rec.name == rem_rec.name and loc_rec.type == rem_rec.type
    ]


def _assign_remote_id(domain: Domain, loc_rec: Record, rem_rec: Record, similar: int = 0) -> None:
    """Assign remote ID to the local record."""
    # Log, and display whether there was a choice
    if not similar:
        msg = "the only yet unassigned one"
    else:
        msg = f"the closest among {similar} similar unmatched ones"
    logging.debug(
        "[%s] Found this local record to be %s for the remote record: %s",
        domain.name,
        msg,
        loc_rec,
    )

    loc_rec.id = rem_rec.id


def _find_closest_matches(partial_matches: list[Record], rem_rec_content: str) -> list[Record]:
    """Find the max. 10 closest partial matches based on content."""
    close_content_matches = get_close_matches(
        rem_rec_content, [loc_rec.content for loc_rec in partial_matches], n=10, cutoff=0.6
    )
    # Similar local records found
    close_records = []
    # Get the corresponding full records
    for matched_content in close_content_matches:
        close_records.append(
            next(loc_rec for loc_rec in partial_matches if loc_rec.content == matched_content)
        )

    return close_records


def _process_multiple_matches(
    domain: Domain, partial_matches: list[Record], rem_rec: Record, unmatched_remote: list[Record]
) -> None:
    """Process multiple partial matches."""
    closest_matches = _find_closest_matches(partial_matches, rem_rec.content)
    if closest_matches:
        # Assign the one closest match, but provide amount of potential other
        # candidates
        _assign_remote_id(domain, closest_matches[0], rem_rec, similar=len(closest_matches))
    else:
        logging.debug(
            "[%s] No close-enough local match for the remote record. Will rather delete it",
            domain.name,
        )
        unmatched_remote.append(rem_rec)


def match_remote_to_local_records(domain: Domain) -> list[Record]:
    """Matching of all remote records against local records, based on similarity."""
    unmatched_remote: list = []

    for rem_rec in domain.remote_records:
        logging.debug(
            "[%s] Trying to find matches with local records for this remote record: %s",
            domain.name,
            rem_rec,
        )
        partial_matches = _find_partial_matches(domain, rem_rec)
        if len(partial_matches) == 1:
            _assign_remote_id(domain, partial_matches[0], rem_rec)
        elif len(partial_matches) > 1:
            _process_multiple_matches(domain, partial_matches, rem_rec, unmatched_remote)
        else:
            logging.debug(
                "[%s] No matching local record with at least the same name and "
                "type found for the remote record",
                domain.name,
            )
            unmatched_remote.append(rem_rec)

    return unmatched_remote
