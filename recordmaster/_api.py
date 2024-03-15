# SPDX-FileCopyrightText: 2024 Max Mehl <https://mehl.mx>
#
# SPDX-License-Identifier: GPL-3.0-only

"""Generic INWX API functions"""

import logging
import sys

from INWX.Domrobot import ApiClient, ApiType  # type: ignore

from ._config import get_app_config


def _ask_confirmation(question, default="yes") -> bool:
    """Ask a question and allow to set a default"""
    valid = {"yes": True, "y": True, "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError(f"invalid default answer: '{default}'")

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == "":
            return valid[default]
        if choice in valid:
            return valid[choice]

        print("Please respond with 'yes' or 'no' (or 'y' or 'n').")


def api_login(api_response_file: str = "", debug: bool = False) -> ApiClient:
    """Login to INWX API"""
    if not api_response_file:
        # Set API URL depending on app config
        login_data = get_app_config("inwx_account")
        api_url = (
            ApiClient.API_OTE_URL
            if login_data.get("test_instance", False)
            else ApiClient.API_LIVE_URL
        )
        api_client = ApiClient(api_url=api_url, api_type=ApiType.JSON_RPC, debug_mode=debug)

        # Get login data from app config
        login_data = {
            "username": login_data.get("username"),
            "password": login_data.get("password"),
            "shared_secret": login_data.get("secret"),
        }

        # Error when no username and/or password set
        if not login_data["username"] or not login_data["password"]:
            logging.error("No username and/or password set to authenticate with the INWX API!")
            sys.exit(1)

        logging.info("Logging in as %s", login_data["username"])
        login_result = api_client.login(**login_data)
        if login_result["code"] != 1000:  # type: ignore
            raise RuntimeError(f"API Login error: {login_result}")

    # Do not login when using the remote API response file
    else:
        api_client = ApiClient(debug_mode=debug)

    return api_client


def inwx_api(
    api: ApiClient, method: str, interactive: bool = False, dry: bool = False, **params
) -> dict:
    """Wrapper for INWX API call that also checks the output for errors"""
    if interactive:
        if _ask_confirmation("Do you want to execute the above change?"):
            pass
        else:
            logging.info("The API call for '%s' has not been made as you have requested.", method)
            return {}

    if dry:
        logging.info("API call for '%s' has not been executed in dry-run mode", method)
        return {}

    api_result = api.call_api(api_method=method, method_params=params)

    # Handle return codes
    if api_result["code"] == 1000:
        pass
    elif api_result["code"] == 2303:
        logging.error(
            "The domain '%s' does not exist at INWX. Aborting program", params.get("domain")
        )
        sys.exit(1)
    else:
        logging.error("API call error for '%s' with params '%s': %s", method, params, api_result)
        sys.exit(1)

    return api_result
