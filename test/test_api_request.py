import unittest
import datetime
from functools import partial
from unittest.mock import patch, MagicMock
from PyQt5 import QtCore
from qgis.core import QgsNetworkAccessManager, QgsFileDownloader
from qgis.PyQt.QtNetwork import QNetworkRequest, QNetworkReply
from cplus_plugin.api.request import (
    CplusApiRequestError,
    CplusApiPooling,
    JOB_COMPLETED_STATUS,
    CplusApiUrl,
    CplusApiRequest,
)
from cplus_plugin.conf import Settings
from cplus_plugin.definitions.defaults import BASE_API_URL


def mocked_exec_loop():
    pass


class TestCplusApiPooling(unittest.TestCase):
    @patch("cplus_plugin.api.request.CplusApiRequest")
    def setUp(self, mock_base_api_client):
        self.mock_context = mock_base_api_client.return_value
        self.url = "http://example.com"
        self.pooling = CplusApiPooling(
            context=self.mock_context,
            url=self.url,
            method="GET",
        )

    def test_call_api_get(self):
        self.mock_context.get.return_value = ({"status": JOB_COMPLETED_STATUS}, 200)
        response, status_code = self.pooling._CplusApiPooling__call_api()
        self.assertEqual(response, {"status": "Completed"})
        self.assertEqual(status_code, 200)

    @patch("time.sleep", return_value=None)
    def test_results_completed(self, mock_sleep):
        self.pooling.limit = 2
        self.mock_context.get.return_value = ({"status": JOB_COMPLETED_STATUS}, 200)
        response = self.pooling.results()
        self.assertEqual(response, {"status": JOB_COMPLETED_STATUS})

    @patch("time.sleep", return_value=None)
    def test_results_retry(self, mock_sleep):
        self.pooling.limit = 3
        self.mock_context.get.side_effect = [
            ({"status": "JOB_RUNNING"}, 200),
            ({"status": "JOB_RUNNING"}, 200),
            ({"status": JOB_COMPLETED_STATUS}, 200),
        ]
        response = self.pooling.results()
        self.assertEqual(response, {"status": JOB_COMPLETED_STATUS})

    @patch("time.sleep", return_value=None)
    def test_results_timeout(self, mock_sleep):
        self.pooling.limit = 2
        self.mock_context.get.return_value = ({"status": "JOB_RUNNING"}, 200)
        with self.assertRaises(CplusApiRequestError):
            self.pooling.results()


class TestCplusApiUrl(unittest.TestCase):
    @patch("cplus_plugin.conf.settings_manager.get_value")
    def setUp(self, mock_get_value):
        mock_get_value.side_effect = lambda key, default=None, type_=str: {
            Settings.DEBUG: False,
            Settings.BASE_API_URL: "https://api.test.com",
        }.get(key, default)
        self.cplus_api_url = CplusApiUrl()

    @patch("cplus_plugin.conf.settings_manager.get_value")
    def test_get_base_api_url_debug_false(self, mock_get_value):
        mock_get_value.side_effect = lambda key, default=None, type_=str: {
            Settings.DEBUG: False,
            Settings.BASE_API_URL: "https://api.test.com",
        }.get(key, default)
        base_url = self.cplus_api_url.get_base_api_url()
        self.assertEqual(base_url, BASE_API_URL)

    @patch("cplus_plugin.conf.settings_manager.get_value")
    def test_get_base_api_url_debug_true(self, mock_get_value):
        mock_get_value.side_effect = lambda key, default=None, type_=str: {
            Settings.DEBUG: True,
            Settings.BASE_API_URL: "https://api.test.com",
        }.get(key, default)
        base_url = self.cplus_api_url.get_base_api_url()
        self.assertEqual(base_url, "https://api.test.com")

    def test_layer_detail(self):
        url = self.cplus_api_url.layer_detail("test-layer-uuid")
        self.assertEqual(url, f"{self.cplus_api_url.base_url}/layer/test-layer-uuid/")

    def test_layer_check(self):
        url = self.cplus_api_url.layer_check()
        self.assertEqual(
            url, f"{self.cplus_api_url.base_url}/layer/check/?id_type=layer_uuid"
        )

    def test_layer_upload_start(self):
        url = self.cplus_api_url.layer_upload_start()
        self.assertEqual(url, f"{self.cplus_api_url.base_url}/layer/upload/start/")

    def test_layer_upload_finish(self):
        url = self.cplus_api_url.layer_upload_finish("test-layer-uuid")
        self.assertEqual(
            url, f"{self.cplus_api_url.base_url}/layer/upload/test-layer-uuid/finish/"
        )

    def test_layer_upload_abort(self):
        url = self.cplus_api_url.layer_upload_abort("test-layer-uuid")
        self.assertEqual(
            url, f"{self.cplus_api_url.base_url}/layer/upload/test-layer-uuid/abort/"
        )

    def test_scenario_submit(self):
        url = self.cplus_api_url.scenario_submit()
        self.assertEqual(url, f"{self.cplus_api_url.base_url}/scenario/submit/")

        url_with_version = self.cplus_api_url.scenario_submit("1.0.0")
        self.assertEqual(
            url_with_version,
            f"{self.cplus_api_url.base_url}/scenario/submit/?plugin_version=1.0.0",
        )

    def test_scenario_execute(self):
        url = self.cplus_api_url.scenario_execute("test-scenario-uuid")
        self.assertEqual(
            url, f"{self.cplus_api_url.base_url}/scenario/test-scenario-uuid/execute/"
        )

    def test_scenario_status(self):
        url = self.cplus_api_url.scenario_status("test-scenario-uuid")
        self.assertEqual(
            url, f"{self.cplus_api_url.base_url}/scenario/test-scenario-uuid/status/"
        )

    def test_scenario_cancel(self):
        url = self.cplus_api_url.scenario_cancel("test-scenario-uuid")
        self.assertEqual(
            url, f"{self.cplus_api_url.base_url}/scenario/test-scenario-uuid/cancel/"
        )

    def test_scenario_detail(self):
        url = self.cplus_api_url.scenario_detail("test-scenario-uuid")
        self.assertEqual(
            url, f"{self.cplus_api_url.base_url}/scenario/test-scenario-uuid/detail/"
        )

    def test_scenario_output_list(self):
        url = self.cplus_api_url.scenario_output_list("test-scenario-uuid")
        self.assertEqual(
            url,
            f"{self.cplus_api_url.base_url}/scenario_output/test-scenario-uuid/list/?page=1&page_size=100",
        )


class TestCplusApiRequest(unittest.TestCase):
    @patch("qgis.core.QgsNetworkAccessManager.instance")
    def setUp(self, mock_nam_instance):
        self.mock_nam = mock_nam_instance.return_value
        self.api_request = CplusApiRequest()
        self.api_request._api_token = "test_token"
        self.api_request.token_exp = datetime.datetime.now() + datetime.timedelta(
            days=1
        )

    def test_get_raw_header_value(self):
        result = self.api_request._get_raw_header_value("test-header")
        self.assertEqual(result, QtCore.QByteArray(b"test-header"))

    def test_default_headers(self):
        expected_headers = {
            "Authorization": "Bearer test_token",
            "Content-Type": "application/json",
        }
        self.assertEqual(self.api_request._default_headers(), expected_headers)

    def test_generate_request(self):
        url = "http://example.com"
        headers = {"Authorization": "Bearer token"}
        request = self.api_request._generate_request(url, headers)
        self.assertIsNotNone(request)
        self.assertEqual(request.url(), QtCore.QUrl(url))

    @patch("qgis.PyQt.QtNetwork.QNetworkReply")
    def test_read_json_response(self, mock_reply):
        mock_reply.readAll.return_value.data.return_value = b'{"key": "value"}'
        response = self.api_request._read_json_response(mock_reply)
        self.assertEqual(response, {"key": "value"})

    @patch("qgis.PyQt.QtNetwork.QNetworkReply")
    def test_handle_response(self, mock_reply):
        url = "http://example.com"
        mock_reply.error.return_value = QNetworkReply.NoError
        mock_reply.attribute.return_value = 200
        mock_reply.readAll.return_value.data.return_value = b'{"key": "value"}'
        response, status_code = self.api_request._handle_response(url, mock_reply)
        self.assertEqual(response, {"key": "value"})
        self.assertEqual(status_code, 200)
        mock_reply.error.return_value = QNetworkReply.ConnectionRefusedError
        with self.assertRaises(CplusApiRequestError):
            response, status_code = self.api_request._handle_response(url, mock_reply)

    @patch("qgis.PyQt.QtNetwork.QNetworkReply")
    @patch("PyQt5.QtCore.QEventLoop.exec_")
    def test_make_request(self, mock_event_loop, mock_reply):
        mock_event_loop.exec_.side_effect = mocked_exec_loop
        self.api_request._make_request(mock_reply)
        mock_event_loop.assert_called_once()

    @patch.object(CplusApiRequest, "post")
    @patch.object(CplusApiRequest, "_is_valid_token", return_value=True)
    def test_api_token(self, mock_is_valid_token, mock_post):
        self.assertEqual(self.api_request.api_token, "test_token")
        mock_is_valid_token.assert_called_once()

    @patch("cplus_plugin.trends_earth.auth.get_auth_config")
    @patch.object(CplusApiRequest, "post")
    def test_api_token_fetch_new_token(self, mock_post, mock_get_auth_config):
        self.api_request._api_token = None
        self.api_request.token_exp = datetime.datetime.now() - datetime.timedelta(
            days=1
        )

        mock_auth_config = MagicMock()
        mock_auth_config.config.side_effect = lambda key: {
            "username": "test_user",
            "password": "test_pass",
        }[key]
        mock_get_auth_config.return_value = mock_auth_config

        mock_post.return_value = ({"access_token": "new_token"}, 200)

        token = self.api_request.api_token
        self.assertEqual(token, "new_token")
        self.assertEqual(self.api_request._api_token, "new_token")
        self.assertIsNotNone(self.api_request.token_exp)

    @patch.object(CplusApiRequest, "get")
    def test_get_layer_detail(self, mock_get):
        mock_get.return_value = ({"key": "value"}, 200)
        result = self.api_request.get_layer_detail("test-layer-uuid")
        self.assertEqual(result, {"key": "value"})
        mock_get.assert_called_once_with(
            self.api_request.urls.layer_detail("test-layer-uuid")
        )

    @patch.object(CplusApiRequest, "post")
    def test_check_layer(self, mock_post):
        mock_post.return_value = ({"status": "valid"}, 200)
        result = self.api_request.check_layer(["uuid1", "uuid2"])
        self.assertEqual(result, {"status": "valid"})
        mock_post.assert_called_once_with(
            self.api_request.urls.layer_check(), ["uuid1", "uuid2"]
        )

    @patch("os.stat")
    @patch.object(CplusApiRequest, "post")
    @patch("cplus_plugin.utils.get_layer_type")
    def test_start_upload_layer(self, mock_get_layer_type, mock_post, mock_stat):
        mock_stat.return_value.st_size = 1024
        mock_get_layer_type.return_value = 0
        mock_post.return_value = ({"upload_id": "12345"}, 201)

        result = self.api_request.start_upload_layer("test_path", "ncs_pathway")
        self.assertEqual(result, {"upload_id": "12345"})
        mock_post.assert_called_once()

    @patch.object(CplusApiRequest, "post")
    def test_finish_upload_layer(self, mock_post):
        mock_post.return_value = ({"status": "completed"}, 200)
        result = self.api_request.finish_upload_layer(
            "test-layer-uuid", "upload_id", [{"part": 1}]
        )
        self.assertEqual(result, {"status": "completed"})
        mock_post.assert_called_once_with(
            self.api_request.urls.layer_upload_finish("test-layer-uuid"),
            {"multipart_upload_id": "upload_id", "items": [{"part": 1}]},
        )

    @patch.object(CplusApiRequest, "post")
    def test_abort_upload_layer(self, mock_post):
        mock_post.return_value = ({}, 204)
        result = self.api_request.abort_upload_layer("test-layer-uuid", "upload_id")
        self.assertTrue(result)
        mock_post.assert_called_once_with(
            self.api_request.urls.layer_upload_abort("test-layer-uuid"),
            {"multipart_upload_id": "upload_id", "items": []},
        )

    @patch.object(CplusApiRequest, "post")
    def test_submit_scenario_detail(self, mock_post):
        mock_post.return_value = ({"uuid": "scenario-uuid"}, 201)
        result = self.api_request.submit_scenario_detail({"key": "value"})
        self.assertEqual(result, "scenario-uuid")
        mock_post.assert_called_once_with(
            self.api_request.urls.scenario_submit(), {"key": "value"}
        )

    @patch.object(CplusApiRequest, "get")
    def test_execute_scenario(self, mock_get):
        mock_get.return_value = ({}, 201)
        result = self.api_request.execute_scenario("test-scenario-uuid")
        self.assertTrue(result)
        mock_get.assert_called_once_with(
            self.api_request.urls.scenario_execute("test-scenario-uuid")
        )

    @patch.object(CplusApiRequest, "get")
    def test_fetch_scenario_status(self, mock_get):
        mock_get.return_value = ({"status": "running"}, 200)
        result = self.api_request.fetch_scenario_status("test-scenario-uuid")
        self.assertIsInstance(result, CplusApiPooling)

    @patch.object(CplusApiRequest, "get")
    def test_cancel_scenario(self, mock_get):
        mock_get.return_value = ({}, 200)
        result = self.api_request.cancel_scenario("test-scenario-uuid")
        self.assertTrue(result)
        mock_get.assert_called_once_with(
            self.api_request.urls.scenario_cancel("test-scenario-uuid")
        )

    @patch.object(CplusApiRequest, "get")
    def test_fetch_scenario_output_list(self, mock_get):
        mock_get.return_value = ({"output": "list"}, 200)
        result = self.api_request.fetch_scenario_output_list("test-scenario-uuid")
        self.assertEqual(result, {"output": "list"})
        mock_get.assert_called_once_with(
            self.api_request.urls.scenario_output_list("test-scenario-uuid")
        )

    @patch.object(CplusApiRequest, "get")
    def test_fetch_scenario_detail(self, mock_get):
        mock_get.return_value = ({"detail": "info"}, 200)
        result = self.api_request.fetch_scenario_detail("test-scenario-uuid")
        self.assertEqual(result, {"detail": "info"})
        mock_get.assert_called_once_with(
            self.api_request.urls.scenario_detail("test-scenario-uuid")
        )
