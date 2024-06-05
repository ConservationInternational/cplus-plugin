# -*- coding: utf-8 -*-
"""
Contains functions for financial computations.
"""

import datetime
from functools import partial
import pathlib
import typing

from qgis.core import (
    QgsFeedback,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingMultiStepFeedback,
)

from qgis import processing

from ..definitions.constants import NPV_PRIORITY_LAYERS_SEGMENT, PRIORITY_LAYERS_SEGMENT
from ..conf import settings_manager, Settings
from ..models.financial import ActivityNpvCollection
from ..utils import clean_filename, FileUtils, log, tr


def compute_discount_value(
    revenue: float, cost: float, year: int, discount: float
) -> float:
    """Calculates the discounted value for the given year.

    :param revenue: Projected total revenue.
    :type revenue: float

    :param cost: Projected total costs.
    :type cost: float

    :param year: Relative year i.e. between 1 and 99.
    :type year: int

    :param discount: Discount value as a percent i.e. between 0 and 100.
    :type discount: float

    :returns: The discounted value for the given year.
    :rtype: float
    """
    return (revenue - cost) / ((1 + discount / 100.0) ** (year - 1))


def create_npv_pwls(
    npv_collection: ActivityNpvCollection,
    context: QgsProcessingContext,
    multi_step_feedback: QgsProcessingMultiStepFeedback,
    feedback: QgsProcessingFeedback,
    target_crs_id: str,
    target_pixel_size: float,
    target_extent: str,
    on_finish_func: typing.Callable = None,
    on_removed_func: typing.Callable = None,
):
    """Creates constant raster layers based on the normalized NPV values for
    the specified activities.

    :param npv_collection: The Activity NPV collection containing the NPV
    parameters for activities.
    :type npv_collection: ActivityNpvCollection

    :param context: Context information for performing the processing.
    :type context: QgsProcessingContext

    :param multi_step_feedback: Feedback for updating the status of processing.
    :type multi_step_feedback: QgsProcessingMultiStepFeedback

    :param feedback: Underlying feedback object for communicating to the caller.
    :type feedback: QgsProcessingFeedback

    :param target_crs_id: CRS identifier of the target layers.
    :type target_crs_id: str

    :param target_pixel_size: Pixel size of the target layer:
    :type target_pixel_size: float

    :param target_extent: Extent of the output layer as xmin, xmax, ymin, ymax.
    :type target_extent: str

    :param on_finish_func: Function to be executed when a constant raster
    has been created.
    :type on_finish_func: Callable

    :param on_removed_func: Function to be executed when a disabled NPV PWL has
    been removed.
    :type on_finish_func: Callable
    """
    base_dir = settings_manager.get_value(Settings.BASE_DIR)
    if not base_dir:
        log(message=tr("No base directory for saving NPV PWLs."), info=False)
        return

    # Create NPV PWL subdirectory
    FileUtils.create_npv_pwls_dir(base_dir)

    # NPV PWL root directory
    npv_base_dir = f"{base_dir}/{PRIORITY_LAYERS_SEGMENT}/{NPV_PRIORITY_LAYERS_SEGMENT}"

    current_step = 0
    multi_step_feedback.setCurrentStep(current_step)

    for i, activity_npv in enumerate(npv_collection.mappings):
        if feedback.isCanceled():
            break

        if activity_npv.activity is None or activity_npv.params is None:
            log(
                tr(
                    "Could not create or update activity NPV as activity and NPV parameter information is missing."
                ),
                info=False,
            )

            current_step += 1
            multi_step_feedback.setCurrentStep(current_step)

            continue

        base_layer_name = clean_filename(
            activity_npv.base_name.replace(" ", "_").lower()
        )

        # Delete existing NPV PWLs. Relevant layers will be re-created
        # where applicable.
        for del_npv_path in pathlib.Path(npv_base_dir).glob(f"*{base_layer_name}*"):
            try:
                log(f"{tr('Deleting')} - NPV PWL {del_npv_path}")
                pathlib.Path(del_npv_path).unlink()
            except OSError as os_ex:
                base_msg_tr = tr("Unable to delete NPV PWL")
                conclusion_msg_tr = tr(
                    "File will be deleted in subsequent processes if not locked"
                )
                log(
                    f"{base_msg_tr}: {os_ex.strerror}. {conclusion_msg_tr}.", info=False
                )

        # Delete if PWL previously existed and is now disabled
        if not activity_npv.enabled:
            if npv_collection.remove_existing:
                # Delete corresponding PWL entry in the settings
                del_pwl = settings_manager.find_layer_by_name(activity_npv.base_name)
                if del_pwl is not None:
                    pwl_id = del_pwl.get("uuid", None)
                    if pwl_id is not None:
                        settings_manager.delete_priority_layer(pwl_id)
                        if on_removed_func is not None:
                            on_removed_func(str(del_pwl["uuid"]))

                current_step += 1
                multi_step_feedback.setCurrentStep(current_step)
                continue

        # Output layer name
        npv_pwl_path = f"{npv_base_dir}/{base_layer_name}_{datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}.tif"

        output_post_processing_func = None
        if on_finish_func is not None:
            output_post_processing_func = partial(
                on_finish_func, activity_npv, npv_pwl_path
            )

        try:
            alg_params = {
                "EXTENT": target_extent,
                "TARGET_CRS": target_crs_id,
                "PIXEL_SIZE": target_pixel_size,
                "NUMBER": activity_npv.params.normalized_npv,
                "OUTPUT": npv_pwl_path,
            }
            processing.run(
                "native:createconstantrasterlayer",
                alg_params,
                context=context,
                feedback=multi_step_feedback,
                onFinish=output_post_processing_func,
            )
        except QgsProcessingException as ex:
            err_tr = tr("Error creating NPV PWL")
            log(f"{err_tr} {npv_pwl_path}")

        current_step += 1
        multi_step_feedback.setCurrentStep(current_step)
