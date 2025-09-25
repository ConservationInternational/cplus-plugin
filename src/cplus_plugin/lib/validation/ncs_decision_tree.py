"""Decision tree processing algorithm for Nature-based Solutions (NCS)."""
import os
import tempfile
import typing

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterString,
    QgsProcessingParameterCrs,
    QgsProcessingParameterExtent,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterEnum,
    QgsProcessingException,
    QgsCoordinateReferenceSystem,
    QgsRectangle,
    QgsRasterLayer,
)
from qgis import processing

from ...conf import settings_manager
from ...utils import tr, log
from ...models.base import NcsPathway, NcsPathwayType


# helpers

def _tmp_tif() -> str:
    """Get a temporary filepath for a GTiff."""
    f = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    f.close()
    return f.name


def _calc(
    expr: str,
    a: QgsRasterLayer,
    out_path: str,
    b: typing.Optional[QgsRasterLayer] = None,
    extent: typing.Optional[QgsRectangle] = None,
) -> str:
    """Thin wrapper around gdal:rastercalculator using refs a@1 and optional b@1."""
    params = {
        "EXPRESSION": expr,
        "LAYERS": [a] if b is None else [a, b],
        "CRS": a.crs().authid(),
        "EXTENT": extent.toString() if extent else a.extent().toString(),
        "OUTPUT": out_path,
        "CELLSIZE": a.rasterUnitsPerPixelX(),  # assume square pixels post-warp
    }
    processing.run("gdal:rastercalculator", params)
    return out_path


def _warp_clip(
    src: str,
    crs: QgsCoordinateReferenceSystem,
    extent: QgsRectangle,
    pixel_size: float,
    nodata: int,
) -> str:
    """
    Warp/clip a raster (file or URL) to the target CRS, extent, and pixel size.
    """
    out = _tmp_tif()
    processing.run(
        "gdal:warpreproject",
        {
            "INPUT": src,
            "SOURCE_CRS": None,
            "TARGET_CRS": crs,
            "RESAMPLING": 0,  # nearest
            "NODATA": nodata,
            "TARGET_RESOLUTION": pixel_size,
            "TARGET_EXTENT": extent.toString(),
            "DATA_TYPE": 6,  # Float32
            "OUTPUT": out,
            "MULTITHREADING": True,
        },
    )
    return out


def _materialize(
    mc,
    extent: QgsRectangle,
    crs: QgsCoordinateReferenceSystem,
    pixel_size: float,
    nodata: int,
) -> typing.Optional[QgsRasterLayer]:
    """
    Turn a default/online pathway into a local clipped/warped GTiff.
    Cache once per run to avoid repeated downloads.
    """
    cache_attr = "_tmp_local_raster"
    cached = getattr(mc, cache_attr, None)
    if cached and os.path.exists(cached):
        lyr = QgsRasterLayer(cached, f"tmp_{getattr(mc, 'name', 'layer')}")
        return lyr if lyr.isValid() else None

    # Try to resolve a file/URL
    src = getattr(mc, "source", None) or getattr(mc, "path", None)
    if not src and hasattr(mc, "to_map_layer"):
        lyr0 = mc.to_map_layer()
        if isinstance(lyr0, QgsRasterLayer) and lyr0.isValid():
            src = lyr0.source()
    if not src:
        log(f"DecisionTree: no source for '{getattr(mc,'name','?')}'")
        return None
    if src.startswith("http"):
        src = f"/vsicurl/{src}"

    try:
        out = _warp_clip(src, crs, extent, pixel_size, nodata)
    except Exception as ex:
        log(f"DecisionTree: warp failed for '{getattr(mc,'name','?')}': {ex}", info=False)
        return None

    lyr = QgsRasterLayer(out, f"tmp_{getattr(mc, 'name', 'layer')}")
    if not lyr.isValid():
        log(f"DecisionTree: invalid warped raster for '{getattr(mc,'name','?')}'", info=False)
        try:
            os.remove(out)
        except Exception:
            pass
        return None

    setattr(mc, cache_attr, out)
    return lyr


def _calcN(expr: str,
           layers: typing.List[QgsRasterLayer],
           out_path: str,
           extent: QgsRectangle,
           crs: QgsCoordinateReferenceSystem,
           pixel_size: float) -> str:
    """
    N-ary raster calculator using a@1, b@1, c@1... variable refs.
    Layers must already be aligned (our _materialize does that).
    """
    if not layers:
        raise QgsProcessingException("No layers provided to raster calculator.")
    params = {
        "EXPRESSION": expr,
        "LAYERS": layers,
        "CRS": crs.authid(),
        "EXTENT": extent.toString(),
        "CELLSIZE": pixel_size,
        "OUTPUT": out_path,
    }
    processing.run("gdal:rastercalculator", params)
    return out_path


def _mosaic_sum(layers: typing.List[QgsRasterLayer],
                crs: QgsCoordinateReferenceSystem,
                extent: QgsRectangle,
                pixel: float) -> typing.Optional[QgsRasterLayer]:
    """
    Sum all input rasters, preserving magnitude (Float32).
    If only one layer, just return it.
    """
    if not layers:
        return None
    if len(layers) == 1:
        return layers[0]

    # Build "a@1 + b@1 + c@1 + ..."
    letters = "abcdefghijklmnopqrstuvwxyz"
    if len(layers) > len(letters):
        raise QgsProcessingException("Too many layers to sum at once.")
    expr = " + ".join([f"{letters[i]}@1" for i in range(len(layers))])

    out_path = _tmp_tif()
    _calcN(expr, layers, out_path, extent, crs, pixel)
    lyr = QgsRasterLayer(out_path, "sum")
    return lyr if lyr.isValid() else None


def _presence_mask(layer: QgsRasterLayer,
                   extent: QgsRectangle,
                   crs: QgsCoordinateReferenceSystem,
                   pixel: float) -> QgsRasterLayer:
    """
    1 where layer > 0, else 0
    """
    out_path = _tmp_tif()
    _calcN("(a@1) > 0", [layer], out_path, extent, crs, pixel)
    return QgsRasterLayer(out_path, "presence")


# processing algo

class ApplyNcsDecisionTreeAlgorithm(QgsProcessingAlgorithm):
    """
    Enforce NCS base rules on the selected Activity and produce a single
    binary raster for the user-selected action (Protect / Manage / Restore).
    """

    # Parameters
    P_ACTIVITY_ID = "ACTIVITY_ID"
    P_TARGET_CRS = "TARGET_CRS"
    P_EXTENT = "EXTENT"
    P_PIXEL = "PIXEL_SIZE"
    P_NODATA = "NODATA"
    P_SELECTED_ACTION = "SELECTED_ACTION"

    # Outputs
    O_SELECTED = "OUT_SELECTED"

    # Enum choices
    CHOICES_ACTION = ["Protect", "Manage", "Restore"]

    def name(self):
        return "apply_ncs_decision_tree"

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterString(self.P_ACTIVITY_ID, tr("Activity ID (UUID)"))
        )
        self.addParameter(QgsProcessingParameterCrs(self.P_TARGET_CRS, tr("Target CRS")))
        self.addParameter(QgsProcessingParameterExtent(self.P_EXTENT, tr("Target Extent")))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.P_PIXEL, tr("Pixel size (map units)"),
                QgsProcessingParameterNumber.Double, 30.0, minValue=1e-6
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.P_NODATA, tr("NoData value"),
                QgsProcessingParameterNumber.Integer, 0
            )
        )
        # User picks exactly one action to output
        self.addParameter(
            QgsProcessingParameterEnum(
                self.P_SELECTED_ACTION,
                tr("Selected action"),
                options=self.CHOICES_ACTION,
                defaultValue=0  # Protect by default
            )
        )
        # Single output
        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.O_SELECTED, tr("Selected action mask")
            )
        )

    def processAlgorithm(self, params, context, feedback):
        # Inputs
        act_id = self.parameterAsString(params, self.P_ACTIVITY_ID, context)
        tgt_crs = self.parameterAsCrs(params, self.P_TARGET_CRS, context)
        extent = self.parameterAsExtent(params, self.P_EXTENT, context)
        pixel = self.parameterAsDouble(params, self.P_PIXEL, context)
        nodata = int(self.parameterAsInt(params, self.P_NODATA, context))
        sel_idx = self.parameterAsEnum(params, self.P_SELECTED_ACTION, context)
        selected_name = self.CHOICES_ACTION[sel_idx]

        # Resolve activity + pathways
        activity = settings_manager.get_activity(act_id)
        if activity is None:
            raise QgsProcessingException(f"Activity not found: {act_id}")

        pathways: typing.List[NcsPathway] = activity.pathways or []
        if not pathways:
            raise QgsProcessingException("Activity has no pathways.")

        # Materialize + group masks
        cropland, wetlands, grass_sav_shrub = [], [], []

        P_crops, M_crops, R_crops = [], [], []
        P_wets,  M_wets,  R_wets  = [], [], []
        P_other, M_other, R_other = [], [], []

        R_forest, R_nonforest = [], []   # for biodiversity safeguard

        for p in pathways:
            if feedback.isCanceled():
                break

            lyr = _materialize(p, extent, tgt_crs, pixel, nodata)
            if not lyr:
                log(f"DecisionTree: skip '{p.name}' (no raster)")
                continue

            # Biome grouping (prefer metadata; fallback on names)
            biome = (getattr(p, "biome", None) or getattr(p, "name", "")).lower()
            is_crop = ("crop" in biome)
            is_wet  = ("wetland" in biome)
            is_grass_sav_shrub = any(k in biome for k in ("grass", "savanna", "shrub"))
            is_forest = ("forest" in biome)

            # populate biome lists (used to build presence masks C/W/G)
            if is_crop:
                cropland.append(lyr)
            elif is_wet:
                wetlands.append(lyr)
            elif is_grass_sav_shrub:
                grass_sav_shrub.append(lyr)

            ptype = getattr(p, "pathway_type", None)

            # action x biome grouping (keeps magnitudes)
            if ptype == NcsPathwayType.PROTECT:
                (P_crops if is_crop else P_wets if is_wet else P_other).append(lyr)
            elif ptype == NcsPathwayType.MANAGE:
                (M_crops if is_crop else M_wets if is_wet else M_other).append(lyr)
            elif ptype == NcsPathwayType.RESTORE:
                (R_crops if is_crop else R_wets if is_wet else R_other).append(lyr)
                # track forest restore specifically (for biodiversity rule)
                (R_forest if is_forest else R_nonforest).append(lyr)

        # Build presence masks C/W/G from populated biome lists
        C_sum = _mosaic_sum(cropland, tgt_crs, extent, pixel)
        W_sum = _mosaic_sum(wetlands, tgt_crs, extent, pixel)
        G_sum = _mosaic_sum(grass_sav_shrub, tgt_crs, extent, pixel)

        C = _presence_mask(C_sum, extent, tgt_crs, pixel) if C_sum else None
        W = _presence_mask(W_sum, extent, tgt_crs, pixel) if W_sum else None
        G = _presence_mask(G_sum, extent, tgt_crs, pixel) if G_sum else None

        P_c = _mosaic_sum(P_crops, tgt_crs, extent, pixel)
        P_w = _mosaic_sum(P_wets,  tgt_crs, extent, pixel)
        P_o = _mosaic_sum(P_other, tgt_crs, extent, pixel)

        M_c = _mosaic_sum(M_crops, tgt_crs, extent, pixel)
        M_w = _mosaic_sum(M_wets,  tgt_crs, extent, pixel)
        M_o = _mosaic_sum(M_other, tgt_crs, extent, pixel)

        R_c = _mosaic_sum(R_crops, tgt_crs, extent, pixel)
        R_w = _mosaic_sum(R_wets,  tgt_crs, extent, pixel)
        R_o = _mosaic_sum(R_other, tgt_crs, extent, pixel)

        R_for = _mosaic_sum(R_forest,     tgt_crs, extent, pixel)
        R_non = _mosaic_sum(R_nonforest,  tgt_crs, extent, pixel)


        # Short-circuit if nothing
        if not any([P_c, P_w, P_o, M_c, M_w, M_o, R_c, R_w, R_o]):
            raise QgsProcessingException(
                "No action masks could be built (check inputs and pathways)."
            )

        # ---------- ENFORCEMENT ORDER ----------
        # Helpers
        def _minus(
                mask: QgsRasterLayer,
                by: typing.Optional[QgsRasterLayer]
            ) -> typing.Optional[QgsRasterLayer]:
            """Subtract 'by' mask from 'mask' (1 - (b>0)),
            preserving magnitude of 'mask'.
            """
            if mask is None:
                return None
            if by is None:
                return mask
            out = _tmp_tif()
            _calc("(a@1) * (1 - (b@1 > 0))", mask, out, b=by, extent=extent)
            return QgsRasterLayer(out, "tmp")

        # Helper to sum a few aligned rasters
        def _sum_layers(*layers):
            L = [lyr for lyr in layers if lyr is not None]
            return _mosaic_sum(L, tgt_crs, extent, pixel) if L else None

        # 1) Cropland supersedes others:
        #    - keep cropland actions (P_c/M_c/R_c)
        #    - remove NON-cropland actions wherever C == 1
        P_after_crop = _sum_layers(P_c, _minus(P_w, C), _minus(P_o, C))
        M_after_crop = _sum_layers(M_c, _minus(M_w, C), _minus(M_o, C))
        R_after_crop = _sum_layers(R_c, _minus(R_w, C), _minus(R_o, C))

        # 2) Wetlands supersede remaining others, but NOT croplands
        P_after_wet = _sum_layers(
            P_c,                                      # keep cropland
            P_w,                                      # keep wetlands
            _minus(_minus(P_after_crop, P_c), W)      # from post-crop, remove cropland then wetlands
        )

        M_after_wet = _sum_layers(
            M_c,
            M_w,
            _minus(_minus(M_after_crop, M_c), W)
        )

        R_after_wet = _sum_layers(
            R_c,
            R_w,
            _minus(_minus(R_after_crop, R_c), W)
        )

        # 3) Biodiversity safeguard (forest restore cannot replace native grass/savanna/shrub)
        R_for_after_cropwet = _sum_layers(
            _minus(R_for, C),   # remove cropland
            None
        )
        R_for_after_cropwet = _minus(R_for_after_cropwet, W) if R_for_after_cropwet else None

        # Apply the G mask to that slice (removing any forest-restore on native G/S/S)
        R_for_after = _minus(R_for_after_cropwet, G) if R_for_after_cropwet else None

        # Recombine: takes R_after_wet, removes the pre-G forest slice
        # and adds the G-filtered slice back
        R_after_bio = _sum_layers(
            _minus(R_after_wet, R_for_after_cropwet),
            R_for_after
        )

        # 4) Action hierarchy: Protect > Manage > Restore
        P_final = P_after_wet
        M_final = _minus(M_after_wet, P_final) if M_after_wet else None
        R_tmp   = _minus(R_after_bio, P_final) if R_after_bio else None
        R_final = _minus(R_tmp, M_final) if (R_tmp and M_final) else R_tmp

        # Select the one action to output
        if sel_idx == 0:
            selected_layer = P_final
        elif sel_idx == 1:
            selected_layer = M_final
        else:
            selected_layer = R_final

        if selected_layer is None:
            raise QgsProcessingException(f"No data available for selected action: {selected_name}")

        # Single output path
        out_path = self.parameterAsOutputLayer(params, self.O_SELECTED, context)

        # Save the selected mask (Byte, with NoData)
        processing.run(
            "gdal:translate",
            {
                "INPUT": selected_layer,
                "TARGET_CRS": tgt_crs,
                "NODATA": nodata,
                "DATA_TYPE": 6,
                "COPY_SUBDATASETS": False,
                "OUTPUT": out_path,
            },
        )

        log(f"DecisionTree: wrote '{selected_name}' mask to {out_path}")
        return { self.O_SELECTED: out_path }
