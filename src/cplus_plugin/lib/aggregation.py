# utils.py
from typing import Dict, List, Union, Tuple
from qgis.core import QgsRasterLayer
from qgis import processing

NODATA_VAL = -9999.0


# --------- helpers ---------------------------------------------------------


def _normalize_inputs(
    rasters_by_key: Union[Dict[str, QgsRasterLayer], List[QgsRasterLayer]],
    weights: Union[Dict[str, float], List[float], None],
) -> Tuple[Dict[str, QgsRasterLayer], Union[Dict[str, float], None]]:
    """
    Coerce inputs to dicts keyed consistently;
    coerce weights to dict or None.
    """
    if isinstance(rasters_by_key, list):
        layers_dict = {f"R{i}": r for i, r in enumerate(rasters_by_key)}
        if isinstance(weights, list):
            weights_dict = {f"R{i}": float(w) for i, w in enumerate(weights)}
        elif isinstance(weights, dict):
            weights_dict = {str(k): float(v) for k, v in weights.items()}
        else:
            weights_dict = None
    else:
        layers_dict = dict(rasters_by_key)
        if isinstance(weights, list):
            # Map list weights in raster order into the dict's key order
            keys = list(layers_dict.keys())
            if len(weights) != len(keys):
                raise ValueError("weights length does not match rasters count")
            weights_dict = {k: float(w) for k, w in zip(keys, weights)}
        elif isinstance(weights, dict):
            weights_dict = {str(k): float(v) for k, v in weights.items()}
        else:
            weights_dict = None

    return layers_dict, weights_dict


def _normalize_weights(w: Dict[str, float], allowed: set) -> Dict[str, float]:
    """Drop non-positive/missing,
    restrict to allowed keys, renormalize to sum=1.
    """
    filt = {
        k: float(v) for k, v in w.items() if k in allowed and v is not None and v > 0
    }
    s = sum(filt.values())
    if s <= 0:
        return {}
    return {k: v / s for k, v in filt.items()}


def _cellstats(
    rasters: List[QgsRasterLayer],
    statistic: str,
    ignore_nodata: bool,
    nodata_value: float,
) -> QgsRasterLayer:
    """Thin wrapper for qgis:cellstatistics with sane defaults."""
    stat_map = {
        "SUM": 0,
        "MEAN": 1,
        "MIN": 2,
        "MAX": 3,
        "STD_DEV": 4,
        "VARIANCE": 5,
        "COUNT": 6,
        "MEDIAN": 7,
    }
    if statistic not in stat_map:
        raise ValueError(f"Unsupported statistic: {statistic}")
    params = {
        "INPUT": rasters,
        "STATISTIC": stat_map[statistic],
        "IGNORE_NODATA": bool(ignore_nodata),
        "REFERENCE_LAYER": rasters[0],  # align to first raster
        "OUTPUT": "TEMPORARY_OUTPUT",
    }
    out = processing.run("qgis:cellstatistics", params)["OUTPUT"]
    # Ensure the output advertises a proper NoData value
    out = _set_nodata(out, nodata_value)
    return out


def _set_nodata(r: QgsRasterLayer, nodata_value: float) -> QgsRasterLayer:
    """Ensure raster has the desired band NoData value
    (metadata only; does not zero valid pixels).
    """
    params = {
        "INPUT": r,
        "NODATA": nodata_value,
        "OPTIONS": "",
        "EXTRA": "",
        "DATA_TYPE": 0,  # Use input type
        "OUTPUT": "TEMPORARY_OUTPUT",
    }
    return processing.run("gdal:translate", params)["OUTPUT"]


def _calc(
    refs: Dict[str, QgsRasterLayer], formula: str, nodata_value: float
) -> QgsRasterLayer:
    """
    gdal:rastercalculator wrapper.
    - refs uses keys among A..F; you may pass fewer than 6.
    - 'formula' is a gdal_calc-style expression; supports where(), comparisons
    - preserves real NoData (nodata_value), so 0 remains a valid class.
    """
    # Map first six refs into A..F slots
    slot_keys = ["A", "B", "C", "D", "E", "F"]
    params = {
        "INPUT_A": refs.get("A"),
        "BAND_A": 1,
        "INPUT_B": refs.get("B"),
        "BAND_B": 1,
        "INPUT_C": refs.get("C"),
        "BAND_C": 1,
        "INPUT_D": refs.get("D"),
        "BAND_D": 1,
        "INPUT_E": refs.get("E"),
        "BAND_E": 1,
        "INPUT_F": refs.get("F"),
        "BAND_F": 1,
        "FORMULA": formula,
        "NO_DATA": nodata_value,
        "RTYPE": 5,  # Float32
        "OPTIONS": f"-a_nodata {nodata_value} -co COMPRESS=DEFLATE",
        "EXTRA": "",
        "OUTPUT": "TEMPORARY_OUTPUT",
    }
    params = params.copy()
    for sk in slot_keys:
        inp = params.get(f"INPUT_{sk}")
        if inp is not None:
            params[f"INPUT_{sk}"] = _set_nodata(inp, nodata_value)

    return processing.run("gdal:rastercalculator", params)["OUTPUT"]


def combine_layers(
    rasters_by_key: Union[Dict[str, QgsRasterLayer], List[QgsRasterLayer]],
    weights: Union[Dict[str, float], List[float], None] = None,
    scale_to_01: bool = False,
    nodata_value: float = NODATA_VAL,
) -> QgsRasterLayer:
    """
    Combine rasters by per-pixel mean (unweighted) or
    weight-normalized average (weighted),
    ignoring NoData. 0 is treated as a valid class (not NoData).

    Args
    ----
    rasters_by_key : Dict[str, QgsRasterLayer] | List[QgsRasterLayer]
        Either a dict keyed by variable name or a list of rasters.
    weights : Dict[str, float] | List[float] | None
        If provided, a weight per raster.
        Will be renormalized to sum=1 over positive weights.
        If None, a simple per-pixel mean is used.
    scale_to_01 : bool
        If True, each input is divided by 5.0 first (convert 0–5 -> 0–1).
        Leave False if your pipeline is already standardized or you want 0–5.
    nodata_value : float
        NoData sentinel to use for outputs and internal calcs.

    Returns
    -------
    QgsRasterLayer (TEMPORARY_OUTPUT)
    """
    layers_dict, weights_dict = _normalize_inputs(rasters_by_key, weights)
    if not layers_dict:
        raise ValueError("combine_layers: no rasters provided")

    # Optionally rescale 0–5 -> 0–1 per input (before any averaging)
    if scale_to_01:
        layers_dict = {
            k: _calc({"A": r}, "A/5.0", nodata_value) for k, r in layers_dict.items()
        }

    if weights_dict is None:
        # Unweighted per-pixel MEAN, ignoring NoData
        return _cellstats(
            list(layers_dict.values()),
            statistic="MEAN",
            ignore_nodata=True,
            nodata_value=nodata_value,
        )

    # Weighted average (Σ w_i * r_i) / (Σ w_i over valid pixels)
    weights_norm = _normalize_weights(weights_dict, set(layers_dict.keys()))
    if not weights_norm:
        # fall back to simple mean if all weights invalid/non-positive
        return _cellstats(
            list(layers_dict.values()),
            statistic="MEAN",
            ignore_nodata=True,
            nodata_value=nodata_value,
        )

    # 1) Build weighted layers: r_i * w_i  (NoData stays NoData)
    weighted_layers: List[QgsRasterLayer] = []
    # 2) Build per-layer weight masks: w_i where pixel is valid, else 0
    weight_masks: List[QgsRasterLayer] = []
    for k, r in layers_dict.items():
        if k not in weights_norm:
            continue
        w = float(weights_norm[k])

        # weighted value: A*w
        w_val = _calc({"A": r}, f"A*{w}", nodata_value)
        weighted_layers.append(w_val)

        # weight mask: w where A != nodata, else 0
        # Using gdal_calc semantics: (A != nodata) yields 1 where valid,
        # 0 where nodata
        w_mask = _calc({"A": r}, f"(A!={nodata_value})*{w}", nodata_value)
        weight_masks.append(w_mask)

    if not weighted_layers:
        raise ValueError(
            "combine_layers: no (positive-weight) rasters matched"
        )

    # 3) Sum of weighted values and sum of weight masks (ignoring NoData)
    sum_weighted = _cellstats(
        weighted_layers,
        statistic="SUM",
        ignore_nodata=True,
        nodata_value=nodata_value
    )
    sum_masks = _cellstats(
        weight_masks,
        statistic="SUM",
        ignore_nodata=True,
        nodata_value=nodata_value
    )

    # 4) Final = where(sum_masks > 0, sum_weighted / sum_masks, nodata)
    final = _calc(
        {"A": sum_weighted, "B": sum_masks},
        f"where(B>0, A/B, {nodata_value})",
        nodata_value,
    )
    return final
