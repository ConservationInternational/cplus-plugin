import concurrent.futures
import json
import os
import traceback

import requests

from .multipart_upload import upload_part
from .request import CplusApiRequest, JOB_COMPLETED_STATUS, JOB_STOPPED_STATUS, CHUNK_SIZE
from ..conf import settings_manager, Settings
from ..models.base import Activity, NcsPathway
from ..models.base import ScenarioResult
from ..tasks import ScenarioAnalysisTask
from ..utils import FileUtils, CustomJsonEncoder, todict, md5


def download_file(url, local_filename):
    parent_dir = os.path.dirname(local_filename)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)


def clean_filename(filename):
    """Creates a safe filename by removing operating system
    invalid filename characters.

    :param filename: File name
    :type filename: str

    :returns A clean file name
    :rtype str
    """
    characters = " %:/,\[]<>*?"

    for character in characters:
        if character in filename:
            filename = filename.replace(character, "_")

    return filename

class ScenarioAnalysisTaskApiClient(ScenarioAnalysisTask):
    def __init__(
        self,
        analysis_scenario_name,
        analysis_scenario_description,
        analysis_activities,
        analysis_priority_layers_groups,
        analysis_extent,
        scenario
    ):
        super().__init__(
            analysis_scenario_name,
            analysis_scenario_description,
            analysis_activities,
            analysis_priority_layers_groups,
            analysis_extent,
            scenario
        )
        self.total_file_upload_size = 0
        self.total_file_upload_chunks = 0
        self.uploaded_chunks = 0
        self.checksum_to_uuid_mapping = {}
        self.path_to_checksum_mapping = {}

    def cancel_task(self, exception=None):
        self.log_message('CANCELLED')
        super().cancel_task(exception)
        self.request.cancel_scenario(self.scenario.uuid)

    def run(self):
        """Run scenario analysis using API."""
        self.request = CplusApiRequest()
        self.scenario_directory = self.get_scenario_directory()
        FileUtils.create_new_dir(self.scenario_directory)

        try:
            self.upload_layers()
        except Exception as e:
            self.log_message(str(e))

        self.build_scenario_detail_json()

        try:
            self.__execute_scenario_analysis()
        except Exception as ex:
            self.log_message(traceback.format_exc(), info=False)
            err = f"Problem executing scenario analysis in the server side: {ex}\n"
            self.log_message(err, info=False)
            self.set_info_message(err, level=Qgis.Critical)
            self.error = ex
            self.cancel_task()
            return False
        return True

    def run_upload(self, file_path, component_type):
        # start upload
        self.log_message(f"Uploading {file_path} as {component_type}")
        upload_params = self.request.start_upload_layer(file_path, component_type)
        upload_id = upload_params['multipart_upload_id']
        layer_uuid = upload_params['uuid']
        upload_urls = upload_params['upload_urls']
        # do upload by chunks
        items = []
        idx = 0
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                url_item = upload_urls[idx]
                self.log_message(f"starting upload part {url_item['part_number']}")
                part_item = upload_part(
                    url_item['url'], chunk, url_item['part_number'])
                items.append(part_item)
                self.log_message(f"finished upload part {url_item['part_number']}")
                self.uploaded_chunks += 1
                self.__update_scenario_status({
                    'progress_text': f'Uploading layers with concurrent request',
                    'progress': int((self.uploaded_chunks / self.total_file_upload_chunks) * 100)
                })
                idx += 1
        self.log_message(f'***Total upload_urls: {len(upload_urls)}')
        self.log_message(f'***Total chunks: {idx}')
        # finish upload

        if upload_id:
            result = self.request.finish_upload_layer(layer_uuid, upload_id, items)
        else:
            layer_detail = self.request.get_layer_detail(layer_uuid)
            result = {
                "name": layer_detail['filename'],
                "size": layer_detail['size'],
                "uuid": layer_detail['uuid']
            }
        return result

    def run_parallel_upload(self, upload_dict):
        file_paths = list(upload_dict.keys())
        component_types = list(upload_dict.values())

        final_result = []
        with concurrent.futures.ThreadPoolExecutor(
                max_workers=3 if os.cpu_count() > 3 else 1
        ) as executor:
            final_result.extend(list(executor.map(
                self.run_upload,
                file_paths,
                component_types
            )))
        return list(final_result)

    def upload_layers(self):
        files_to_upload = {}

        for activity in self.analysis_activities:
            for pathway in activity.pathways:
                if pathway:
                    if pathway.path and os.path.exists(pathway.path):
                        is_uploaded = self.__is_layer_uploaded(pathway.path)
                        if not is_uploaded:
                            files_to_upload[pathway.path] = 'ncs_pathway'

                    for carbon_path in pathway.carbon_paths:
                        if os.path.exists(carbon_path):
                            is_uploaded = self.__is_layer_uploaded(carbon_path)
                            if not is_uploaded:
                                files_to_upload[carbon_path] = 'ncs_carbon'

            for priority_layer in activity.priority_layers:
                if priority_layer:
                    if priority_layer['path'] and os.path.exists(priority_layer['path']):
                        is_uploaded = self.__is_layer_uploaded(priority_layer['path'])
                        if not is_uploaded:
                            files_to_upload[priority_layer['path']] = 'priority_layer'

        sieve_enabled = self.get_settings_value(
            Settings.SIEVE_ENABLED, default=False, setting_type=bool
        )

        if sieve_enabled:
            sieve_mask_layer = self.get_settings_value(
                Settings.SIEVE_MASK_PATH, default=""
            )

            if sieve_mask_layer:
                is_uploaded = self.__is_layer_uploaded(sieve_mask_layer)
                if not is_uploaded:
                    files_to_upload[sieve_mask_layer] = 'sieve_mask_layer'

            snapping_enabled = self.get_settings_value(
                Settings.SNAPPING_ENABLED, default=False, setting_type=bool
            )
            if snapping_enabled:
                reference_layer = self.get_settings_value(Settings.SNAP_LAYER, default="")
                if reference_layer:
                    is_uploaded = self.__is_layer_uploaded(reference_layer)
                    if not is_uploaded:
                        files_to_upload[reference_layer] = 'snap_layer'

        masking_layers = self.get_masking_layers()
        for masking_layer in masking_layers:
            is_uploaded = self.__is_layer_uploaded(masking_layer)
            if not is_uploaded:
                files_to_upload[masking_layer] = 'mask_layer'

        self.total_file_upload_size = sum(os.stat(fp).st_size for fp in files_to_upload)
        self.total_file_upload_chunks = self.total_file_upload_size / CHUNK_SIZE
        final_results = self.run_parallel_upload(files_to_upload)

        new_uploaded_layer = {}
        for file_path in files_to_upload:
            filename_without_ext = '.'.join(os.path.basename(file_path).split('.')[0:-1])
            for res in final_results:
                if res['name'].startswith(filename_without_ext):
                    res['path'] = file_path
                    new_uploaded_layer[file_path] = res
                    break

        for uploaded_layer in new_uploaded_layer.values():
            settings_manager.save_layer_mapping(uploaded_layer)

    def __is_layer_uploaded(self, layer_path: str):
        # TODO: Check uploaded layer value from QGIS settings
        identifier = md5(layer_path)
        uploaded_layer_dict = settings_manager.get_layer_mapping(identifier)
        if uploaded_layer_dict:
            if layer_path == uploaded_layer_dict['path']:
                is_uploaded = 'uuid' in self.request.get_layer_detail(uploaded_layer_dict['uuid'])
                self.checksum_to_uuid_mapping[identifier] = uploaded_layer_dict
                self.path_to_checksum_mapping[layer_path] = identifier
                return is_uploaded
        return False

    def build_scenario_detail_json(self):
        # TODO: Get layer UUID from QGIS settings
        old_scenario_dict = json.loads(json.dumps(todict(self.scenario), cls=CustomJsonEncoder))
        uploaded_layer_dict = {
            fp: self.checksum_to_uuid_mapping[checksum] for fp, checksum in self.path_to_checksum_mapping.items()
        }
        sieve_enabled = json.loads(self.get_settings_value(Settings.SIEVE_ENABLED, default=False))
        sieve_threshold =float(
            self.get_settings_value(Settings.SIEVE_THRESHOLD, default=10.0)
        )
        sieve_mask_path = self.get_settings_value(
            Settings.SIEVE_MASK_PATH, default=""
        ) if sieve_enabled else ""
        snapping_enabled = json.loads(self.get_settings_value(
            Settings.SNAPPING_ENABLED, default=False, setting_type=bool
        )) if sieve_enabled else False
        snap_layer_path = self.get_settings_value(
            Settings.SNAP_LAYER, default="", setting_type=str
        ) if snapping_enabled else ""
        suitability_index = float(
            self.get_settings_value(Settings.PATHWAY_SUITABILITY_INDEX, default=0)
        )
        carbon_coefficient = float(
            self.get_settings_value(Settings.CARBON_COEFFICIENT, default=0.0)
        )
        snap_rescale = self.get_settings_value(
            Settings.RESCALE_VALUES, default=False, setting_type=bool
        )
        resampling_method = self.get_settings_value(
            Settings.RESAMPLING_METHOD, default=0
        )

        masking_layers = self.get_masking_layers()
        mask_layer_uuids = [
            obj['uuid'] for fp, obj in uploaded_layer_dict.items() if fp in masking_layers
        ]

        sieve_mask_uuid = uploaded_layer_dict.get(sieve_mask_path, "")['uuid'] if sieve_mask_path else ""
        snap_layer_uuid = uploaded_layer_dict.get(snap_layer_path, "")['uuid'] if snap_layer_path else ""

        for activity in old_scenario_dict['activities']:
            activity['layer_type'] = 0
            for pathway in activity['pathways']:
                if pathway:
                    if pathway['path'] and os.path.exists(pathway['path']):
                        if uploaded_layer_dict.get(pathway['path'], None):
                            pathway['uuid'] = uploaded_layer_dict.get(pathway['path'])['uuid']
                            pathway['layer_uuid'] = pathway['uuid']
                            pathway['layer_type'] = 0

                    carbon_uuids = []
                    for carbon_path in pathway['carbon_paths']:
                        if os.path.exists(carbon_path):
                            if uploaded_layer_dict(carbon_path, None):
                                carbon_uuids.append(uploaded_layer_dict(carbon_path))
                    pathway['carbon_uuids'] = carbon_uuids

            new_priority_layers = []
            for priority_layer in activity['priority_layers']:
                if priority_layer:
                    if priority_layer['path'] and os.path.exists(priority_layer['path']):
                        if uploaded_layer_dict.get(priority_layer['path'], None):
                            priority_layer['uuid'] = uploaded_layer_dict.get(priority_layer['path'])['uuid']
                            priority_layer['layer_uuid'] = priority_layer['uuid']
                            new_priority_layers.append(priority_layer)
            activity['priority_layers'] = new_priority_layers

        self.scenario_detail = {
            'scenario_name': old_scenario_dict['name'],
            'scenario_desc': old_scenario_dict['description'],
            'snapping_enabled': snapping_enabled if sieve_enabled else False,
            'snap_layer': snap_layer_path,
            'snap_layer_uuid': snap_layer_uuid,
            'pathway_suitability_index': suitability_index,
            'carbon_coefficient': carbon_coefficient,
            'snap_rescale': snap_rescale,
            'snap_method': resampling_method,
            'sieve_enabled': sieve_enabled,
            'sieve_threshold': sieve_threshold,
            'sieve_mask_path': sieve_mask_path,
            'sieve_mask_uuid': sieve_mask_uuid,
            'mask_path': ', '.join(masking_layers),
            'mask_layer_uuids': mask_layer_uuids,
            'extent': old_scenario_dict['extent']['bbox'],
            'priority_layer_groups': old_scenario_dict.get('priority_layer_groups', []),
            'priority_layers': old_scenario_dict['activities'][0]['priority_layers'],
            'activities': old_scenario_dict['activities']
        }

    def __execute_scenario_analysis(self):
        # submit scenario detail to the API
        scenario_uuid = self.request.submit_scenario_detail(self.scenario_detail)
        self.scenario.uuid = scenario_uuid

        # execute scenario detail
        self.request.execute_scenario(scenario_uuid)
        # scenario_uuid = '8271bcd7-9161-4941-87e2-caae3f7df0b9'


        # fetch status by interval
        status_pooling = self.request.fetch_scenario_status(scenario_uuid)
        status_pooling.on_response_fetched = self.__update_scenario_status
        status_response = status_pooling.results()
        # if success, fetch output list
        scenario_status = status_response.get("status", "")
        self.new_scenario_detail = self.request.fetch_scenario_detail(scenario_uuid)

        if scenario_status == JOB_COMPLETED_STATUS:
            self.__retrieve_scenario_outputs(scenario_uuid)
        elif scenario_status == JOB_STOPPED_STATUS:
            scenario_error = status_response.get("errors", "Unknown error")
            raise Exception(scenario_error)

    def __update_scenario_status(self, response):
        self.set_status_message(response.get("progress_text", ""))
        self.update_progress(response.get("progress", 0))

    def create_activity(self, activity: dict, download_dict: list):
        ncs_pathways = []
        for pathway in activity['pathways']:
            if 'layer_uuid' in pathway:
                del pathway['layer_uuid']
            if 'carbon_uuids' in pathway:
                del pathway['carbon_uuids']
            pathway['path'] = download_dict[os.path.basename(pathway['path'])]
            ncs_pathways.append(NcsPathway(**pathway))
        activity['pathways'] = ncs_pathways
        activity['path'] = download_dict[os.path.basename(activity['path'])]
        activity_obj = Activity(**activity)
        return activity_obj

    def set_scenario(self, output_list, download_paths):
        output_fnames = []
        for output in output_list['results']:
            if '_cleaned' in output['filename']:
                output_fnames.append(output['filename'])

        from ..utils import log
        weighted_activities = []
        activities = []

        download_dict = {
            os.path.basename(d): d for d in download_paths
        }

        for activity in self.new_scenario_detail['updated_detail']['activities']:
            activities.append(self.create_activity(activity, download_dict))
        for activity in self.new_scenario_detail['updated_detail']['weighted_activities']:
            weighted_activities.append(self.create_activity(activity, download_dict))

        self.analysis_weighted_activities = weighted_activities
        self.analysis_activities = activities
        self.scenario.activities = activities
        self.scenario.weighted_activities = weighted_activities
        self.scenario.priority_layer_groups = self.new_scenario_detail['updated_detail']['priority_layer_groups']

    def __retrieve_scenario_outputs(self, scenario_uuid):
        output_list = self.request.fetch_scenario_output_list(scenario_uuid)
        urls_to_download = []
        download_paths = []
        for output in output_list['results']:
            urls_to_download.append(
                output['url'].replace('https://0.0.0.0:8888', 'http://0.0.0.0:9010')
            )
            if output['is_final_output']:
                download_path = os.path.join(
                    self.scenario_directory,
                    output['filename']
                )
                final_output_path = download_path
                self.output = output['output_meta']
                self.output['OUTPUT'] = final_output_path
            else:
                download_path = os.path.join(
                    self.scenario_directory,
                    output['group'],
                    output['filename']
                )
            download_paths.append(download_path)

        with concurrent.futures.ThreadPoolExecutor(
                max_workers=3 if os.cpu_count() > 3 else 1
        ) as executor:
            executor.map(
                download_file,
                urls_to_download,
                download_paths
            )
        # for idx, download_path in enumerate(download_paths):
        #     download_file(urls_to_download[idx], download_path)

        self.set_scenario(output_list, download_paths)

        self.scenario_result = ScenarioResult(
            scenario=self.scenario,
            scenario_directory=self.scenario_directory,
            analysis_output=self.output,
        )

        self.analysis_priority_layers_groups
