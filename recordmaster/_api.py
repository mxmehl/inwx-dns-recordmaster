# SPDX-FileCopyrightText: 2024 Max Mehl <https://mehl.mx>
#
# SPDX-License-Identifier: GPL-3.0-only

"""Generic INWX API functions"""

import logging
import sys

from INWX.Domrobot import ApiClient, ApiType  # type: ignore

from ._config import get_app_config


def api_login(api_response_file: str, debug: bool) -> ApiClient:
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


def inwx_api(api: ApiClient, method: str, **params) -> dict:
    """Wrapper for INWX API call that also checks the output for errors"""
    api_result = api.call_api(api_method=method, method_params=params)

    if api_result["code"] != 1000:  # type: ignore
        raise RuntimeError(f"API call error: {api_result}")

    return api_result  # type: ignore
