"""
Model exported as python.
Name : cplus_model
Group : CPLUS
With QGIS : 33000
"""

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterRasterDestination
import processing


class CPLUSModel(QgsProcessingAlgorithm):
    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "alien_plant_removal_apr",
                "Alien plant removal (APR)",
                optional=True,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "anr_carbon_impact",
                "ANR: Carbon impact",
                optional=True,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "anr_mtrends", "ANR: mtrends", optional=True, defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "anr_nvp", "ANR: NVP", optional=True, defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "anr_years", "ANR: Years", optional=True, defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "apc_carbon_impact",
                "APC: Carbon impact",
                optional=True,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "apr_mtrends", "APR: mtrends", optional=True, defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "apr_years", "APR: Years", optional=True, defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "assisted_natural_regeneration_anr",
                "Assisted natural regeneration (ANR)",
                optional=True,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "biocombine_normalized",
                "Biocombine normalized",
                optional=True,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "bt_carbon_impact",
                "BT: Carbon impact",
                optional=True,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "bt_mtrends", "BT: mtrends", optional=True, defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "bt_nvp", "BT: NVP", optional=True, defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "bt_years", "BT: Years", optional=True, defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "bush_thinning_bt",
                "Bush thinning (BT)",
                optional=True,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "cccombo_normalized",
                "Cccombo normalized",
                optional=True,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "cccombo_normalized_inverse",
                "Cccombo normalized (inverse)",
                optional=True,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "eat_fresh_ef", "Eat fresh (EF)", optional=True, defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "ef_carbon_impact",
                "EF: Carbon impact",
                optional=True,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "ef_mtrends", "EF: mtrends", optional=True, defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "ef_nvp", "EF: NVP", optional=True, defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "ef_years", "EF: Years", optional=True, defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "ei_all_gknp_normalized",
                "ei all gknp normalized",
                optional=True,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "herding_health_hh",
                "Herding health (HH)",
                optional=True,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "hh_carbon_impact",
                "HH: Carbon impact",
                optional=True,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "hh_mtrends", "HH: mtrends", optional=True, defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "hh_nvp", "HH: NVP", optional=True, defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "hh_years", "HH: Years", optional=True, defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "policy", "Policy", optional=True, defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "social_normalized",
                "Social normalized",
                optional=True,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "social_normalized_inverse",
                "Social normalized (inverse)",
                optional=True,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "wattle_naturally_wn",
                "Wattle naturally (WN)",
                optional=True,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "wn_carbon_impact",
                "WN: Carbon impact",
                optional=True,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "wn_mtrends", "WN: mtrends", optional=True, defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "wn_nvp", "WN: NVP", optional=True, defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                "wn_years", "WN: Years", optional=True, defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterDestination(
                "cplus_qgis_model_output",
                "cplus_qgis_model_output.tif",
                createByDefault=True,
                defaultValue=None,
            )
        )

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(7, model_feedback)
        results = {}
        outputs = {}

        wattle_naturally_expression = (
            '"Wattle naturally (WN)@1" + "Biocombine normalized@1" + (10 * "Social normalized@1")'
            ' + "Cccombo normalized (inverse)@1" + "Policy@1" + "WN: Years@1" + "WN: mtrends@1" '
            '+ "WN: NVP@1" + "WN: Carbon impact@1"'
        )

        eat_fresh_expression = (
            '"Eat fresh (EF)@1" + "Biocombine normalized@1" + "Cccombo normalized@1" +'
            ' (10 * "Social normalized (inverse)@1") + "Policy@1" + "EF: Years@1" +'
            ' "EF: mtrends@1" + "EF: NVP@1" + "EF: Carbon impact@1"'
        )

        assisted_natural_regeneration_expression = (
            '"Assisted natural regeneration (ANR)@1" + "Biocombine normalized@1" + '
            '"Cccombo normalized@1" + (10 * "Social normalized@1") + "Policy@1" + '
            '"ANR: Years@1" + "ANR: mtrends@1" + "ANR: NVP@1" + "ANR: Carbon impact@1"'
        )

        hearding_health_expression = (
            '"Herding health (HH)@1" + "Biocombine normalized@1" + '
            '"ei all gknp normalized@1" + (10 * "Social normalized@1") + '
            '"Policy@1" + "HH: Years@1" + "HH: mtrends@1" + "HH: NVP@1" + '
            '"HH: Carbon impact@1"'
        )

        alien_plant_removal_expression = (
            '"Alien plant removal (APR)@1"  + "Biocombine normalized@1"  +  '
            '"ei all gknp normalized@1"  + (10 * "Social normalized@1")  + '
            '"Policy@1" + "APR: Years@1" + "APR: mtrends@1" +  '
            '"APC: Carbon impact@1"'
        )

        bush_thinning_expression = (
            '"Bush thinning (BT)@1" + "Biocombine normalized@1" + '
            '"Cccombo normalized (inverse)@1" + (10 * "Social normalized@1") + '
            '"Policy@1" + "BT: Years@1" + "BT: mtrends@1" + "BT: NVP@1" + '
            '"BT: Carbon impact@1"'
        )

        models_expressions = {
            "wattle_naturally_wn": wattle_naturally_expression,
            "eat_fresh": eat_fresh_expression,
            "assisted_natural_regeneration": assisted_natural_regeneration_expression,
            "hearding_health": hearding_health_expression,
            "alien_plant_removal": alien_plant_removal_expression,
            "bush_thinning": bush_thinning_expression,
        }

        step = 1
        for model in parameters["models"]:
            alg_params = {
                "CELLSIZE": 0,
                "CRS": None,
                "EXPRESSION": models_expressions[model],
                "EXTENT": None,
                "LAYERS": parameters[model],
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            }
            outputs[model] = processing.run(
                "qgis:rastercalculator",
                alg_params,
                context=context,
                feedback=feedback,
                is_child_algorithm=True,
            )
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}
            step += 1

        input_rasters = [output["OUTPUT"] for output in outputs if True]

        # Highest position in raster stack
        alg_params = {
            "IGNORE_NODATA": True,
            "INPUT_RASTERS": input_rasters,
            "OUTPUT_NODATA_VALUE": -9999,
            "REFERENCE_LAYER": outputs["AlienPlantRemovalCalculation"]["OUTPUT"],
            "OUTPUT": parameters["cplus_qgis_model_output"],
        }
        outputs["HighestPositionInRasterStack"] = processing.run(
            "native:highestpositioninrasterstack",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )
        results["cplus_qgis_model_output"] = outputs["HighestPositionInRasterStack"][
            "OUTPUT"
        ]
        return results

    def name(self):
        return "cplus_model"

    def displayName(self):
        return "cplus_model"

    def group(self):
        return "CPLUS"

    def groupId(self):
        return "CPLUS"

    def createInstance(self):
        return CPLUSModel()
