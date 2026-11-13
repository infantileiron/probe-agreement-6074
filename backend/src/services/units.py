import math

# Unit metadata is shared by dataset import, study creation and run computation.
# Pressure units convert linearly; temperature and concentration currently have
# a single supported unit each, so their factors are the identity.
UNIT_DIMENSIONS = {"kPa": "pressure", "bar": "pressure", "degC": "temperature", "mg/L": "concentration"}
DIMENSION_LABELS = {"pressure": "压力", "temperature": "温度", "concentration": "浓度"}
CANONICAL_UNITS = {"pressure": "kPa", "temperature": "degC", "concentration": "mg/L"}
UNIT_TO_CANONICAL = {"kPa": 1.0, "bar": 100.0, "degC": 1.0, "mg/L": 1.0}
DIMENSION_BASIS = {
    "pressure": "1 bar = 100 kPa",
    "temperature": "degC 为摄氏温度读数，仅在温度单位内使用",
    "concentration": "mg/L 为浓度读数，仅在浓度单位内使用",
}


def dimension(unit):
    try:
        return UNIT_DIMENSIONS[unit]
    except KeyError:
        raise ValueError(f"单位不支持：{unit!r}；仅支持 kPa/bar/degC/mg/L")


def dimension_label(unit):
    return DIMENSION_LABELS[dimension(unit)]


def mixing_error(first, second):
    """Explicit rejection text for units of different physical dimensions."""
    first_label, second_label = dimension_label(first), dimension_label(second)
    return (f"单位不能混配：{first}（{first_label}）与 {second}（{second_label}）"
            f"属于不同物理量；{first_label}与{second_label}不得混配，"
            "压力与温度严禁混用，请统一到同一物理量的单位")


def ensure_compatible(*units):
    """Return the shared dimension or reject cross-dimension mixing."""
    if not units:
        raise ValueError("至少需要一个单位")
    for unit in units:
        dimension(unit)
    for unit in units[1:]:
        if dimension(unit) != dimension(units[0]):
            raise ValueError(mixing_error(units[0], unit))
    return dimension(units[0])


def conversion_factor(source, target):
    """Multiplicative factor such that value_target = value_source * factor."""
    if source == target:
        return 1.0
    if dimension(source) != dimension(target):
        raise ValueError(mixing_error(source, target))
    return UNIT_TO_CANONICAL[source] / UNIT_TO_CANONICAL[target]


def format_factor(value):
    return f"{value:.12g}"


def _formula(name, factor):
    return f"{name}_analysis = {name}" if factor == 1.0 else f"{name}_analysis = {name} × {format_factor(factor)}"


def build_conversion(x_unit, y_unit, analysis_unit, variance_ratio):
    """Describe conversion to the analysis unit and adjust lambda.

    Raw readings stay in the dataset's own units. The variance ratio is supplied
    in those raw units, so it must follow the same linear conversion:
    lambda_analysis = lambda_input * (y_factor / x_factor)^2.
    """
    shared = ensure_compatible(x_unit, y_unit, analysis_unit)
    x_factor = conversion_factor(x_unit, analysis_unit)
    y_factor = conversion_factor(y_unit, analysis_unit)
    if not math.isfinite(variance_ratio) or variance_ratio <= 0:
        raise ValueError("lambda=var(y误差)/var(x误差)须正且有限")
    ratio_analysis = variance_ratio * (y_factor / x_factor) ** 2
    if not math.isfinite(ratio_analysis) or ratio_analysis <= 0:
        raise ValueError("换算后的误差方差比须正且有限")
    x_note = "同单位，无需换算" if x_factor == 1.0 else f"{x_unit}→{analysis_unit} × {format_factor(x_factor)}"
    y_note = "同单位，无需换算" if y_factor == 1.0 else f"{y_unit}→{analysis_unit} × {format_factor(y_factor)}"
    basis = (f"分析单位 {analysis_unit}（{dimension_label(analysis_unit)}）："
             f"X侧 {x_note}；Y侧 {y_note}；{DIMENSION_BASIS[shared]}")
    ratio_note = (f"输入λ（原单位）={format_factor(variance_ratio)}；"
                  f"换算后λ={format_factor(ratio_analysis)}"
                  f"（λ分析 = λ输入 × (y_factor/x_factor)²）")
    return {
        "basis": basis,
        "dimension": shared,
        "dimension_label": dimension_label(analysis_unit),
        "analysis_unit": analysis_unit,
        "x": {"from": x_unit, "to": analysis_unit, "factor": x_factor, "formula": _formula("x", x_factor)},
        "y": {"from": y_unit, "to": analysis_unit, "factor": y_factor, "formula": _formula("y", y_factor)},
        "variance_ratio_input": variance_ratio,
        "variance_ratio_analysis": ratio_analysis,
        "variance_ratio_note": ratio_note,
    }
