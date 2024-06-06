import json
import math
import os
import time
import typing

import requests

from ..utils import log, get_layer_type
from ..conf import settings_manager, Settings
from ..trends_earth import auth
from ..trends_earth.constants import API_URL as TRENDS_EARTH_API_URL
from ..definitions.defaults import BASE_API_URL

JOB_COMPLETED_STATUS = "Completed"
JOB_CANCELLED_STATUS = "Cancelled"
JOB_STOPPED_STATUS = "Stopped"
CHUNK_SIZE = 100 * 1024 * 1024


def log_response(response: typing.Union[dict, str], request_name: str) -> None:
    """Log response to QGIS console.
    :param response: Response from CPLUS API
    :type response: dict
    :param request_name: Name of the request
    :type request_name: str
    """

    if not settings_manager.get_value(Settings.DEBUG):
        return
    log(f"****Request - {request_name} *****")
    if isinstance(response, dict):
        log(json.dumps(response))
    else:
        log(response)


class CplusApiRequestError(Exception):
    """Error class for Cplus API Request.
    :param message: Error message
    :type message: str
    """

    def __init__(self, message):
        """Constructor for CplusApiRequestError"""
        if isinstance(message, dict):
            message = json.dumps(message)
        elif isinstance(message, list):
            message = ", ".join(message)
        log(message, info=False)
        self.message = message
        super().__init__(self.message)


class CplusApiPooling:
    """Fetch/Post url with pooling.

    :param url: URL to send request
    :type url: str
    :param headers: Headers to send request, optional, default to None
    :type headers: dict
    :param method: Method to send request, defaults to "GET"
    :type method: str
    :param data: Data to send request, optional, default to None
    :type data: dict
    :param max_limit: Number of maximum retry attempts, optional, defaults to 3600
    :type max_limit: int
    :param interval: Interval in seconds, optional, defaults to 1
    :type interval: int
    :param on_response_fetched: Callback function when response is fetched successfully
    :type on_response_fetched: typing.Callable
    """

    DEFAULT_LIMIT = 3600  # Check result maximum 3600 times
    DEFAULT_INTERVAL = 1  # Interval of check results
    FINAL_STATUS_LIST = [JOB_COMPLETED_STATUS, JOB_CANCELLED_STATUS, JOB_STOPPED_STATUS]

    def __init__(
        self,
        url: str,
        headers: typing.Union[dict, None] = None,
        method: str = "GET",
        data: dict = None,
        max_limit: int = None,
        interval: int = None,
        on_response_fetched: typing.Callable = None,
    ):
        """init."""
        self.url = url
        self.headers = headers or {}
        self.current_repeat = 0
        self.method = method
        self.data = data
        self.limit = max_limit or self.DEFAULT_LIMIT
        self.interval = interval or self.DEFAULT_INTERVAL
        self.on_response_fetched = on_response_fetched
        self.cancelled = False

    def __call_api(self):
        """Call CPLUS API URL"""
        if self.method == "GET":
            return requests.get(self.url, headers=self.headers)
        return requests.post(self.url, self.data, headers=self.headers)

    def results(self):
        """Return results of data.

        :raises requests.exceptions.Timeout: Raised when getting request timeout

        :return: CPLUS API response result
        :rtype: dict
        """
        if self.cancelled:
            return {"status": JOB_CANCELLED_STATUS}
        self.current_repeat += 1
        if self.limit != -1 and self.current_repeat >= self.limit:
            raise requests.exceptions.Timeout()
        try:
            response = self.__call_api()
            if response.status_code != 200:
                raise CplusApiRequestError(f"{response.status_code} - {response.text}")
            result = response.json()
            if self.on_response_fetched:
                self.on_response_fetched(result)
            if result["status"] in self.FINAL_STATUS_LIST:
                return result
            else:
                time.sleep(self.interval)
                return self.results()
        except requests.exceptions.Timeout:
            time.sleep(self.interval)
            return self.results()


class TrendsApiUrl:
    """Trends API Urls."""

    def __init__(self) -> None:
        self.base_url = TRENDS_EARTH_API_URL

    @property
    def auth(self):
        return f"{self.base_url}/auth"


class CplusApiUrl:
    """Class for Cplus API Urls."""

    def __init__(self):
        self.base_url = self.get_base_api_url()
        self.trends_urls = TrendsApiUrl()
        self._api_token = self.api_token

    def get_base_api_url(self) -> str:
        """Returns the base API URL.


        :return: Base API URL
        :rtype: str
        """

        debug = settings_manager.get_value(Settings.DEBUG, False, bool)
        if debug:
            return settings_manager.get_value(Settings.BASE_API_URL)
        else:
            return BASE_API_URL

    @property
    def api_token(self) -> str:
        """Fetch token from Trends.Earth API

        :raises CplusApiRequestError: If request is failing

        :return: Trends.Earth Access Token
        :rtype: str
        """
        auth_config = auth.get_auth_config(auth.TE_API_AUTH_SETUP, warn=None)

        if (
            not auth_config
            or not auth_config.config("username")
            or not auth_config.config("password")
        ):
            log("API unable to login - setup auth configuration before using")
            return

        username = auth_config.config("username")
        pw = auth_config.config("password")

        response = requests.post(
            self.trends_urls.auth, json={"email": username, "password": pw}
        )
        if response.status_code != 200:
            raise CplusApiRequestError(
                "Error authenticating to Trends Earth API: "
                f"{response.status_code} - {response.text}"
            )
        result = response.json()
        access_token = result.get("access_token", None)
        if access_token is None:
            raise CplusApiRequestError(
                "Error authenticating to Trends Earth API: missing access_token!"
            )
        self._api_token = access_token
        return access_token

    @property
    def headers(self) -> dict:
        """Return headers for Cplus API request


        :return: Headers for Cplus API request
        :rtype: dict
        """
        return {
            "Authorization": f"Bearer {self._api_token}",
        }

    def layer_detail(self, layer_uuid) -> str:
        """Cplus API URL to get layer detail

        :param layer_uuid: Layer UUID
        :type layer_uuid: str

        :return: Cplus API URL for layer detail
        :rtype: str
        """
        return f"{self.base_url}/layer/{layer_uuid}/"

    def layer_check(self) -> str:
        """Cplus API URL for checking layer validity


        :return: Cplus API URL for layer check
        :rtype: str
        """
        return f"{self.base_url}/layer/check/?id_type=layer_uuid"

    def layer_upload_start(self) -> str:
        """Cplus API URL for starting layer upload


        :return: Cplus API URL for layer upload start
        :rtype: str
        """
        return f"{self.base_url}/layer/upload/start/"

    def layer_upload_finish(self, layer_uuid) -> str:
        """Cplus API URL for finishing layer upload

        :param layer_uuid: Layer UUID
        :type layer_uuid: str

        :return: Cplus API URL for layer upload finish
        :rtype: str
        """
        return f"{self.base_url}/layer/upload/{layer_uuid}/finish/"

    def layer_upload_abort(self, layer_uuid) -> str:
        """Cplus API URL for aborting layer upload

        :param layer_uuid: Layer UUID
        :type layer_uuid: str

        :return: Cplus API URL for layer upload abort
        :rtype: str
        """
        return f"{self.base_url}/layer/upload/{layer_uuid}/abort/"

    def scenario_submit(self, plugin_version=None) -> str:
        """Cplus API URL for submitting scenario JSON

        :param plugin_version: Version of the Cplus Plugin
        :type plugin_version: str

        :return: Cplus API URL for scenario submission
        :rtype: str
        """
        url = f"{self.base_url}/scenario/submit/"
        if plugin_version:
            url += f"?plugin_version={plugin_version}"
        return url

    def scenario_execute(self, scenario_uuid) -> str:
        """Cplus API URL for executing scenario

        :param scenario_uuid: Scenario UUID
        :type scenario_uuid: str

        :return: Cplus API URL for scenario execution
        :rtype: str
        """
        return f"{self.base_url}/scenario/{scenario_uuid}/execute/"

    def scenario_status(self, scenario_uuid) -> str:
        """Cplus API URL for getting scenario status

        :param scenario_uuid: Scenario UUID
        :type scenario_uuid: str

        :return: Cplus API URL for scenario status
        :rtype: str
        """
        return f"{self.base_url}/scenario/{scenario_uuid}/status/"

    def scenario_cancel(self, scenario_uuid) -> str:
        """Cplus API URL for cancelling scenario execution

        :param scenario_uuid: Scenario UUID
        :type scenario_uuid: str

        :return: Cplus API URL for cancelling scenario execution
        :rtype: str
        """
        return f"{self.base_url}/scenario/{scenario_uuid}/cancel/"

    def scenario_detail(self, scenario_uuid) -> str:
        """Cplus API URL for getting scenario detal

        :param scenario_uuid: Scenario UUID
        :type scenario_uuid: str

        :return: Cplus API URL for getting scenario detail
        :rtype: str
        """
        return f"{self.base_url}/scenario/{scenario_uuid}/detail/"

    def scenario_output_list(self, scenario_uuid) -> str:
        """Cplus API URL for listing scenario output

        :param scenario_uuid: Scenario UUID
        :type scenario_uuid: str

        :return: Cplus API URL for scenario output list
        :rtype: str
        """
        return f"{self.base_url}/scenario_output/{scenario_uuid}/list/?download_all=true&page=1&page_size=100"


class CplusApiRequest:
    """Class to send request to Cplus API."""

    page_size = 50

    def __init__(self) -> None:
        self.urls = CplusApiUrl()

    def get(self, url) -> requests.Response:
        """GET requests.

        :param url: Cplus API URL
        :type url: str

        :return: Response from Cplus API
        :rtype: requests.Response
        """
        return requests.get(url, headers=self.urls.headers)

    def post(self, url: str, data: typing.Union[dict, list]) -> requests.Response:
        """POST requests.

        :param url: Cplus API URL
        :type url: typing.Union[dict, list]
        :param data: Cplus API payload
        :type data: dict

        :return: Response from Cplus API
        :rtype: requests.Response
        """
        return requests.post(url, json=data, headers=self.urls.headers)

    def get_layer_detail(self, layer_uuid) -> dict:
        """Request for getting layer detail

        :param layer_uuid: Layer UUID
        :type layer_uuid: str

        :return: Layer detail
        :rtype: dict
        """
        response = self.get(self.urls.layer_detail(layer_uuid))
        result = response.json()
        return result

    def check_layer(self, payload) -> dict:
        """Request for checking layer validity

        :param payload: List of Layer UUID
        :type payload: list

        :return: dict consisting of which Layer UUIDs are available, unavailable, or invalid
        :rtype: dict
        """
        response = self.post(self.urls.layer_check(), payload)
        result = response.json()
        return result

    def start_upload_layer(self, file_path: str, component_type: str) -> dict:
        """Request for starting layer upload

        :param file_path: Path of the file to be uploaded
        :type file_path: str
        :param component_type: Layer component type, e.g. "ncs_pathway"
        :type component_type: str
        :raises CplusApiRequestError: If the request is failing

        :return: Dictionary of the layer to be uploaded
        :rtype: dict
        """
        file_size = os.stat(file_path).st_size
        payload = {
            "layer_type": get_layer_type(file_path),
            "component_type": component_type,
            "privacy_type": "private",
            "name": os.path.basename(file_path),
            "size": file_size,
            "number_of_parts": math.ceil(file_size / CHUNK_SIZE),
        }
        response = self.post(self.urls.layer_upload_start(), payload)
        result = response.json()
        if response.status_code != 201:
            raise CplusApiRequestError(result.get("detail", ""))
        return result

    def finish_upload_layer(self, layer_uuid: str,
                            upload_id: typing.Union[str, None],
                            items: typing.Union[typing.List[dict], None]) -> dict:
        """Request for finishing layer upload

        :param layer_uuid: UUID of the uploaded layer
        :type layer_uuid: str
        :param upload_id: Upload ID of the multipart upload, optional, defaults to None
        :type upload_id: str
        :param items: List of uploaded items for multipart upload, optional, defaults to None
        :type items: typing.Union[typing.List[dict], None]

        :return: Dictionary containing the UUID, name, size of the upload file
        :rtype: dict
        """
        payload = {}
        if upload_id:
            payload["multipart_upload_id"] = upload_id
        if items:
            payload["items"] = items
        response = self.post(self.urls.layer_upload_finish(layer_uuid), payload)
        result = response.json()
        return result

    def abort_upload_layer(self, layer_uuid: str, upload_id: str) -> bool:
        """Aborting layer upload

        :param layer_uuid: UUID of a Layer that is currently being uploaded
        :type layer_uuid: str
        :param upload_id: Multipart Upload ID
        :type upload_id: str
        :raises CplusApiRequestError: If the abort is failed

        :return: True if upload is successfully aborted
        :rtype: bool
        """
        payload = {"multipart_upload_id": upload_id, "items": []}
        response = self.post(self.urls.layer_upload_abort(layer_uuid), payload)
        if response.status_code != 204:
            result = response.json()
            raise CplusApiRequestError(result.get("detail", ""))
        return True

    def submit_scenario_detail(self, scenario_detail: dict) -> bool:
        """Submitting scenario JSON to Cplus API

        :param scenario_detail: Scenario detail
        :type scenario_detail: dict
        :raises CplusApiRequestError: If the failed to submit scenario

        :return: Scenario UUID
        :rtype: bool
        """
        log_response(scenario_detail, "scenario_detail")
        response = self.post(self.urls.scenario_submit(), scenario_detail)
        result = response.json()
        if response.status_code != 201:
            raise CplusApiRequestError(result.get("detail", ""))
        return result["uuid"]

    def execute_scenario(self, scenario_uuid: str) -> bool:
        """Executing scenario in Cplus API

        :param scenario_uuid: Scenario UUID
        :type scenario_uuid: str
        :raises CplusApiRequestError: If the failed to execute scenario

        :return: True if the scenario was successfully executed
        :rtype: bool
        """
        response = self.get(self.urls.scenario_execute(scenario_uuid))
        result = response.json()
        if response.status_code != 201:
            raise CplusApiRequestError(result.get("detail", ""))
        return True

    def fetch_scenario_status(self, scenario_uuid) -> CplusApiPooling:
        """Fetching scenario status

        :param scenario_uuid: Scenario UUID
        :type scenario_uuid: str

        :return: CplusApiPooling object
        :rtype: CplusApiPooling
        """
        url = self.urls.scenario_status(scenario_uuid)
        return CplusApiPooling(url, self.urls.headers)

    def cancel_scenario(self, scenario_uuid: str) -> bool:
        """Cancel scenario execution

        :param scenario_uuid: Scenario UUID
        :type scenario_uuid: str
        :raises CplusApiRequestError: If the failed to cancel scenario

        :return: True if the scenario was successfully cancelled
        :rtype: bool
        """
        response = self.get(self.urls.scenario_cancel(scenario_uuid))
        result = response.json()
        if response.status_code != 200:
            raise CplusApiRequestError(result.get("detail", ""))
        return True

    def fetch_scenario_output_list(self, scenario_uuid) -> typing.List[dict]:
        """List scenario output

        :param scenario_uuid: Scenario UUID
        :type scenario_uuid: str
        :raises CplusApiRequestError: If the failed to list scenario output

        :return: List of scenario output:
        :rtype: typing.List[dict]
        """
        response = self.get(self.urls.scenario_output_list(scenario_uuid))
        result = response.json()
        if response.status_code != 200:
            raise CplusApiRequestError(result.get("detail", ""))
        return result

    def fetch_scenario_detail(self, scenario_uuid: str) -> dict:
        """Fetch scenario detail

        :param scenario_uuid: Scenario UUID
        :type scenario_uuid: str
        :raises CplusApiRequestError: If the failed to list scenario output

        :return: Scenario detail
        :rtype: dict
        """
        response = self.get(self.urls.scenario_detail(scenario_uuid))
        result = response.json()
        if response.status_code != 200:
            raise CplusApiRequestError(result.get("detail", ""))
        return result
