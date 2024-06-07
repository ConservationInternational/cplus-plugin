import time
import json
import io
import requests
from qgis.PyQt import QtCore, QtWidgets, QtNetwork
from qgis.core import (
    QgsTask,
    QgsNetworkAccessManager,
    QgsApplication,
    QgsSettings,
    QgsNetworkReplyContent,
)


from .request import BaseApi, CplusApiRequest
from ..utils import log, todict, CustomJsonEncoder

# chunk_size must be greater than 5MB, for now use 100MB
CHUNK_SIZE = 100 * 1024 * 1024


def upload_part(signed_url: str, file_data: bytes, file_part_number: int, max_retries: int = 5) -> dict:
    """Upload filepart to presigned S3 URL.
    This function uses exponential backoff when retrying failed request, with maximum retries
    defined in `max_retries`.

    :param signed_url: Presigned S3 URL
    :type signed_url: str
    :param file_data: File like object, could be a chunk/part of large file, or whole file
    :type file_data: bytes
    :param file_part_number: The number/order of the file part, will be used when CPLUS API and S3
        finally merge the file part.
    :type file_part_number: int
    :param max_retries: Maximum retry attempts, defaults to 5
    :type max_retries: int
    :raises requests.exceptions.RequestException: Raised when error still occurs after
        retrying for `max_retries` times.

    :return: Dictionary containing part number and S3 etag
    :rtype: dict
    """

    retries = 0
    # while retries < max_retries:
    try:
        # ref: https://github.com/aws-samples/amazon-s3-multipart-upload-
        # transfer-acceleration/blob/main/frontendV2/src/utils/upload.js#L119
        if signed_url.startswith("http://"):
            # response = requests.put(
            #     signed_url, data=file_data, headers={"Host": "minio:9000"}
            # )
            resp = BaseApi(headers={"Host": "minio:9000"}).put(signed_url, file_data)

        else:
            # response = requests.put(signed_url, data=file_data)
            resp = BaseApi().put(signed_url, file_data)

        if resp is not None:
            status_code = resp.attribute(
                QtNetwork.QNetworkRequest.HttpStatusCodeAttribute
            )
            log(f"Status code: {str(status_code)}")
            log(f"headers: {str(json.dumps(todict(resp.rawHeaderList()), cls=CustomJsonEncoder))}")

            if status_code in [200, 201]:
                return {"part_number": file_part_number, "etag": resp.headers["ETag"]}
            else:
                log(f"Request failed")
                retries += 1
                # if retries < max_retries:
                #     # Calculate the exponential backoff delay
                #     delay = 2 ** retries
                #     log(f"Retrying in {delay} seconds...")
                #     time.sleep(delay)
                # else:
                #     log("Max retries exceeded.")
                #     raise
            return ret, status_code
    except requests.exceptions.RequestException as e:
        log(f"Request failed: {e}")
        retries += 1
        if retries < max_retries:
            # Calculate the exponential backoff delay
            delay = 2**retries
            log(f"Retrying in {delay} seconds...")
            time.sleep(delay)
        else:
            log("Max retries exceeded.")
            raise
