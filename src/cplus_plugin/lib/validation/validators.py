# -*- coding: utf-8 -*-
"""
Aggregated and individual rule validators.
"""

import traceback
import typing

from qgis.PyQt import QtCore

from qgis.core import QgsRasterLayer, QgsTask

from ...definitions.constants import NO_DATA_VALUE

from .configs import (
    crs_validation_config,
    no_data_validation_config,
    raster_validation_config,
    resolution_validation_config,
)
from ...models.base import LayerModelComponent, ModelComponentType, NcsPathway
from ...models.validation import (
    RuleConfiguration,
    RuleResult,
    RuleType,
    ValidationResult,
)
from ...utils import log, tr


class BaseRuleValidator(QtCore.QObject):
    """Validator for an individual rule.

    This is an abstract class that needs to be subclassed with the
    specific validation implementation by overriding the `validate`
    protected function.
    """

    validation_started = QtCore.pyqtSignal()
    validation_progress_changed = QtCore.pyqtSignal(float)
    validation_completed = QtCore.pyqtSignal()

    def __init__(self, configuration: RuleConfiguration, parent=None):
        super().__init__(parent)

        self._config = configuration
        self._result: RuleResult = None
        self.model_components: typing.List[LayerModelComponent] = list()
        self._progress = 0.0

    @property
    def rule_configuration(self) -> RuleConfiguration:
        """Returns the rule configuration use in the validator.

        :returns: Rule configuration used in the validator.
        :rtype: RuleConfiguration
        """
        return self._config

    @property
    def result(self) -> RuleResult:
        """Returns the result of the validation process.

        :returns: Result of the validation process.
        :rtype: RuleResult
        """
        return self._result

    @property
    def rule_type(self) -> RuleType:
        """Returns the type identified of the rule validator.

        :returns: Type identified of the rule validator.
        :rtype: RuleType
        """
        raise NotImplementedError

    @property
    def progress(self) -> float:
        """Returns the validator's progress.

        :returns: Progress of the validator between 0.0 and 100.0.
        :rtype: float
        """
        return self._progress

    def _validate(self) -> bool:
        """Initiates the validation process.

        Subclasses need to override this method with the specific
        validation implementation and set the 'result' attribute
        value.

        :returns: True if the validation process succeeded
        or False if it failed.
        :rtype: bool
        """
        raise NotImplementedError

    def log(self, message: str, info: bool = True):
        """Convenience function that logs the given messages by appending
        the information in the rule configuration.

        :param message: Message to be logged.
        :type message: str

        :param info: False if the message should be logged as a warning
        else True if information.
        :type info: bool
        """
        msg = f"{self._config.rule_name} - {message}"
        log(message=msg, info=info)

    def _set_progress(self, progress: float):
        """Set the current progress of the validator.

        The 'validation_progress_changed' signal will be emitted.

        :param progress: Progress of validation as a percentage
        value i.e. between 0.0 and 100.0.
        :type progress: float
        """
        if progress < 0.0 or progress > 100.0:
            return

        self._progress = progress
        self.validation_progress_changed.emit(progress)

    def run(self) -> bool:
        """Initiates the rule validation process and returns
        a result indicating whether the process succeeded or
        failed.

        A fail result would, for instance, be due to no layers,
        or only one layer, defined for validation.

        :returns: True if the validation process succeeded
        or False if it failed.
        :rtype: bool
        """
        if len(self.model_components) < 2:
            msg = tr("At least two layers are required for the validation process.")
            self.log(msg, False)

            return False

        self.validation_started.emit()
        status = self._validate()
        self.validation_completed.emit()

        return status


BaseRuleValidatorType = typing.TypeVar("BaseRuleValidatorType", bound=BaseRuleValidator)


class RasterValidator(BaseRuleValidator):
    """Checks if the input datasets are raster layers."""

    def _validate(self) -> bool:
        """Checks whether all input datasets are raster layers.

        If a layer is not valid, it will also be included in the list
        of non-raster datasets.

        :returns: True if the validation process succeeded
        or False if it failed.
        :rtype: bool
        """
        status = True
        non_raster_model_components = []

        progress = 0.0
        progress_increment = 100.0 / len(self.model_components)

        for model_component in self.model_components:
            is_valid = model_component.is_valid()
            if not is_valid:
                if status:
                    status = False
                non_raster_model_components.append(model_component.name)
            else:
                layer = model_component.to_map_layer()
                if not isinstance(layer, QgsRasterLayer):
                    non_raster_model_components.append(model_component.name)

            progress += progress_increment
            self._set_progress(progress)

        summary = ""
        validate_info = []
        if not status:
            summary = tr("There are invalid non-raster datasets")
            invalid_layer_names = ", ".join(non_raster_model_components)
            validate_info = [(tr("Non-raster datasets"), invalid_layer_names)]
        else:
            summary = tr("All datasets are rasters")

        self._result = RuleResult(
            self._config, self._config.recommendation, summary, validate_info
        )

        self._set_progress(100.0)

        return status

    def rule_type(self) -> RuleType:
        """Returns the raster type rule validator.

        :returns: Raster type rule validator.
        :rtype: RuleType
        """
        return RuleType.DATA_TYPE


class CrsValidator(BaseRuleValidator):
    """Checks if the input datasets have the same CRS."""

    def _validate(self) -> bool:
        """Checks whether all input datasets have the same CRS.

        :returns: True if the validation process succeeded
        or False if it failed.
        :rtype: bool
        """
        status = True

        # key: CRS name or 'undefined', value: list of model/layer names
        crs_definitions = {}
        undefined_msg = tr("Undefined")
        invalid_msg = tr("Invalid datasets")
        has_undefined = False

        progress = 0.0
        progress_increment = 100.0 / len(self.model_components)

        for model_component in self.model_components:
            is_valid = model_component.is_valid()
            if not is_valid:
                if status:
                    status = False

                # Add invalid datasets to the validation messages to make it explicit
                if invalid_msg in crs_definitions:
                    layers = crs_definitions.get(invalid_msg)
                    layers.append(model_component.name)
                else:
                    crs_definitions[invalid_msg] = [model_component.name]

            else:
                layer = model_component.to_map_layer()
                crs = layer.crs()
                if crs is None:
                    # Flag that there is at least one dataset with an undefined CRS
                    if not has_undefined:
                        has_undefined = True

                    if status:
                        status = False

                    if undefined_msg in crs_definitions:
                        layers = crs_definitions.get(undefined_msg)
                        layers.append(model_component.name)
                    else:
                        crs_definitions[undefined_msg] = [model_component.name]
                else:
                    crs_id = crs.authid()
                    if crs_id in crs_definitions:
                        layers = crs_definitions.get(crs_id)
                        layers.append(model_component.name)
                    else:
                        crs_definitions[crs_id] = [model_component.name]

            progress += progress_increment
            self._set_progress(progress)

        if len(crs_definitions) > 1 and status:
            status = False

        summary = ""
        validate_info = []
        if not status:
            summary = tr("Datasets have different CRS definitions")
            for crs_str, layers in crs_definitions.items():
                validate_info.append((crs_str, ", ".join(layers)))
        else:
            summary_tr = tr("All datasets have the same CRS")
            summary = f"{summary_tr} - {list(crs_definitions.keys())[0]}"

        self._result = RuleResult(
            self._config, self._config.recommendation, summary, validate_info
        )

        self._set_progress(100.0)

        return status

    def rule_type(self) -> RuleType:
        """Returns the CRS rule validator.

        :returns: CRS rule validator.
        :rtype: RuleType
        """
        return RuleType.CRS


class NoDataValueValidator(BaseRuleValidator):
    """Checks if applicable input datasets have the same no data value."""

    # Default band in raster layer.
    BAND_NUMBER = 0

    def _validate(self) -> bool:
        """Checks whether applicable input datasets have the same no data value.

        :returns: True if the validation process succeeded
        or False if it failed.
        :rtype: bool
        """
        status = True

        no_data_definitions = {}
        invalid_msg = tr("Invalid datasets")
        has_undefined = False

        progress = 0.0
        progress_increment = 100.0 / len(self.model_components)

        for model_component in self.model_components:
            is_valid = model_component.is_valid()
            if not is_valid:
                if status:
                    status = False

                # Add invalid datasets to the validation messages to
                # make it explicit
                if invalid_msg in no_data_definitions:
                    layers = no_data_definitions.get(invalid_msg)
                    layers.append(model_component.name)
                else:
                    no_data_definitions[invalid_msg] = [model_component.name]

            else:
                layer = model_component.to_map_layer()
                if not isinstance(layer, QgsRasterLayer):
                    continue

                # If band does not have NoData value then exclude from validation
                raster_provider = layer.dataProvider()
                if not raster_provider.sourceHasNoDataValue(self.BAND_NUMBER):
                    continue

                no_data_value = raster_provider.sourceNoDataValue(self.BAND_NUMBER)
                if no_data_value != NO_DATA_VALUE:
                    if no_data_value in no_data_definitions:
                        layers = no_data_definitions.get(no_data_value)
                        layers.append(model_component.name)
                    else:
                        no_data_definitions[no_data_value] = [model_component.name]

            progress += progress_increment
            self._set_progress(progress)

        if len(no_data_definitions) > 1 and status:
            status = False

        summary = ""
        validate_info = []
        if not status:
            summary_tr = tr("Datasets have a NoData value different from")
            summary = f"{summary_tr} {str(NO_DATA_VALUE)}"
            for no_data, layers in no_data_definitions.items():
                validate_info.append((str(no_data), ", ".join(layers)))
        else:
            summary_tr = tr("Datasets have the same NoData value")
            summary = f"{summary_tr} - {str(NO_DATA_VALUE)}"

        self._result = RuleResult(
            self._config, self._config.recommendation, summary, validate_info
        )

        self._set_progress(100.0)

        return status

    def rule_type(self) -> RuleType:
        """Returns the no data value rule validator.

        :returns: No data value rule validator.
        :rtype: RuleType
        """
        return RuleType.NO_DATA_VALUE


class DataValidator(QgsTask):
    """Abstract runner for checking a set of datasets against specific
    validation rules.

    Rule validators need to be added manually in this default
    implementation and set the model component type of the result.
    """

    NAME = "Default Data Validator"
    MODEL_COMPONENT_TYPE = ModelComponentType.UNKNOWN

    rule_validation_started = QtCore.pyqtSignal(RuleType)
    rule_validation_finished = QtCore.pyqtSignal(RuleType, RuleResult)
    validation_completed = QtCore.pyqtSignal()

    def __init__(self, model_components=None):
        super().__init__(tr(self.NAME))

        self.model_components = []
        if model_components is not None:
            self.model_components = model_components

        self._result: ValidationResult = None
        self._rule_validators = []
        self._rule_results = []

    def _validate(self) -> bool:
        """Initiates the validation process based on the specified
        rule validators.

        :returns: True if the validation process succeeded
        or False if it failed ro cancelled.
        :rtype: bool
        """
        status = True
        for rule_validator in self._rule_validators:
            if self.isCanceled():
                status = False
                break

            rule_validator.model_components = self.model_components
            rule_validator.run()
            if rule_validator.result is not None:
                self.rule_validation_finished.emit(
                    rule_validator.rule_type(), rule_validator.result
                )

        return status

    def log(self, message: str, info: bool = True):
        """Convenience function that logs the given messages by appending
        the information for the validator.

        :param message: Message to be logged.
        :type message: str

        :param info: False if the message should be logged as a warning
        else True if information.
        :type info: bool
        """
        msg = f"{self.NAME} - {message}"
        log(message=msg, info=info)

    @property
    def result(self) -> ValidationResult:
        """Returns the result of the validation process.

        :returns: Result of the validation process.
        :rtype: ValidationResult
        """
        return self._result

    def cancel(self):
        """Cancel the validation process."""
        self.log(tr("Validation process has been cancelled."))

        super().cancel()

    def run(self) -> bool:
        """Initiates the validation process based on the
        specified validators and returns a result indicating
        whether the process succeeded or failed.

        :returns: True if the validation process succeeded
        or False if it failed.
        :rtype: bool
        """
        if len(self._rule_validators) == 0:
            msg = tr("No rule validators specified.")
            self.log(msg, False)

            return False

        if len(self.model_components) < 2:
            msg = tr("At least two datasets are required for the validation process.")
            self.log(msg, False)

            return False

        status = True

        try:
            status = self._validate()
        except Exception as ex:
            exc_info = "".join(traceback.TracebackException.from_exception(ex).format())
            self.log(exc_info, False)
            status = False

        return status

    @staticmethod
    def rule_validators() -> dict[RuleType, typing.Type[BaseRuleValidator]]:
        """Returns all the rule validator classes, any new validator
        type needs to be added here.

        The validator classes are indexed by their corresponding rule
        type enum.

        :returns: Collection containing rule validator classes indexed
        by their corresponding rule types.
        :rtype: dict
        """
        return {
            RuleType.DATA_TYPE: RasterValidator,
            RuleType.CRS: CrsValidator,
            RuleType.NO_DATA_VALUE: NoDataValueValidator,
        }

    @staticmethod
    def validator_cls_by_type(rule_type: RuleType) -> typing.Type[BaseRuleValidator]:
        """Gets the rule validator class based on the corresponding rule type.

        :param rule_type: The type of the validator rule.
        :type rule_type: RuleType

        :returns: The rule validator class corresponding to the
        given rule type.
        :rtype: BaseRuleValidator
        """
        return DataValidator.rule_validators()[rule_type]

    @staticmethod
    def create_rule_validator(
        rule_type: RuleType, config: RuleConfiguration
    ) -> BaseRuleValidator:
        """Factory method for creating a rule validator object.

        :param rule_type: The type of the validator rule.
        :type rule_type: RuleType

        :param config: The context information for configuring
        the rule validator.
        :type rule_type: RuleConfiguration

        :returns: An instance of the specific rule validator.
        :rtype: BaseRuleValidator
        """
        validator_cls = DataValidator.validator_cls_by_type(rule_type)

        return validator_cls(config)

    def add_rule_validator(self, rule_validator: BaseRuleValidator):
        """Add a rule validator for validating the input model components.

        :param rule_validator: Validator for checking the input model
        components based on the specific validation rule.
        :type rule_validator: BaseRuleValidator
        """
        self._rule_validators.append(rule_validator)

    def finished(self, result: bool):
        """Depending on the outcome of the validation process,
        `validation_completed` signal will be emitted only if the
        validation was successful. The `result` attribute will also contain the
        validation result object. If an error occurred during the validation
        process, the validation result object will be None.

        :param result: True if the validation process was successful, else False.
        :type result: bool
        """
        if result:
            rule_results = [
                rule_validator.result for rule_validator in self._rule_validators
            ]
            self._result = ValidationResult(rule_results, self.MODEL_COMPONENT_TYPE)
            self.validation_completed.emit()
            self.log("Validation complete.")


class NcsDataValidator(DataValidator):
    """Validates both NCS pathway and carbon layer datasets. The resolution
    check for carbon layers is tagged as a warning rather than an error.
    """

    MODEL_COMPONENT_TYPE = ModelComponentType.NCS_PATHWAY
    NAME = "NCS Data Validator"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_components = kwargs.pop("ncs_pathways", list)
        self._initialize_rule_validators()

    def _initialize_rule_validators(self):
        """Add rule validators."""
        # Raster data type validator
        self._raster_type_validator = DataValidator.create_rule_validator(
            RuleType.DATA_TYPE, raster_validation_config
        )
        self.add_rule_validator(self._raster_type_validator)

        # CRS validator
        self._crs_validator = DataValidator.create_rule_validator(
            RuleType.CRS, crs_validation_config
        )
        self.add_rule_validator(self._crs_validator)

        # NoData value validator
        self._no_data_validator = DataValidator.create_rule_validator(
            RuleType.NO_DATA_VALUE, no_data_validation_config
        )
        self.add_rule_validator(self._no_data_validator)
