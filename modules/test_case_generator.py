"""Rule-based C++ test generation for supported numeric member functions.

Version 1 supports two numeric parameters (a basic/base amount and a bonus)
with explicit HRA and DA percentage requirements. It deliberately refuses
unsupported signatures instead of inventing expected results.
"""

import ast
import re


_NUMERIC_PARAMETER = re.compile(
    r"^(?:const\s+)?(?:unsigned\s+)?(?:long\s+long|long|short|double|float|int)"
    r"\s*(?:[&*]\s*)?(\w+)\s*$"
)


def _parse_member_signature(code, expected_function):
    pattern = re.compile(
        r"\b(?P<return_type>double|float|int|long|short)\s+"
        r"(?P<class_name>[A-Za-z_]\w*)::"
        r"(?P<function_name>[A-Za-z_]\w*)\s*\((?P<params>[^()]*)\)",
        re.MULTILINE,
    )
    match = pattern.search(code or "")

    if not match:
        raise ValueError(
            "Could not identify a supported numeric C++ member-function signature."
        )

    if match.group("function_name") != expected_function:
        raise ValueError(
            "The function name in the code does not match the selected function."
        )

    raw_params = match.group("params").strip()
    if not raw_params or raw_params == "void":
        raise ValueError("The selected function must have two numeric parameters.")

    parameters = []
    for raw_param in raw_params.split(","):
        param_match = _NUMERIC_PARAMETER.match(raw_param.strip())
        if not param_match:
            raise ValueError(
                "Only simple numeric parameters (int, long, float, double) "
                "are supported in this first version."
            )
        parameters.append(param_match.group(1))

    if len(parameters) != 2:
        raise ValueError("The first version supports exactly two numeric parameters.")

    base_index = next(
        (i for i, name in enumerate(parameters)
         if "basic" in name.lower() or "base" in name.lower()),
        None,
    )
    bonus_index = next(
        (i for i, name in enumerate(parameters)
         if "bonus" in name.lower()),
        None,
    )

    if base_index is None or bonus_index is None or base_index == bonus_index:
        raise ValueError(
            "Could not identify basic/base salary and bonus parameters. "
            "Use parameter names such as basicSalary and bonus."
        )

    return {
        "return_type": match.group("return_type"),
        "class_name": match.group("class_name"),
        "function_name": match.group("function_name"),
        "parameters": parameters,
        "base_index": base_index,
        "bonus_index": bonus_index,
    }


def _parse_percentage(requirements, label):
    match = re.search(
        rf"\b{label}\b\s*(?:=|:|is|of)?\s*(\d+(?:\.\d+)?)\s*%",
        requirements or "",
        re.IGNORECASE,
    )
    if not match:
        raise ValueError(
            f"Please specify {label} as a percentage, for example {label} = 20%."
        )
    value = float(match.group(1))
    if value < 0 or value > 100:
        raise ValueError(f"{label} percentage must be between 0 and 100.")
    return value / 100.0


def _safe_evaluate(node, values):
    """Evaluate a small arithmetic AST without executing arbitrary Python."""
    if isinstance(node, ast.Expression):
        return _safe_evaluate(node.body, values)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.Name) and node.id in values:
        return float(values[node.id])
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
        return +_safe_evaluate(node.operand, values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_safe_evaluate(node.operand, values)
    if isinstance(node, ast.BinOp):
        left = _safe_evaluate(node.left, values)
        right = _safe_evaluate(node.right, values)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Mod):
            return left % right
        if isinstance(node.op, ast.Pow) and abs(right) <= 8:
            return left ** right
    raise ValueError("Original return expression is not a supported arithmetic expression.")


def _baseline_value(original_code, parameter_values):
    returns = re.findall(r"\breturn\s+(.+?)\s*;", original_code or "", re.DOTALL)
    if not returns:
        return None
    expression = returns[-1].strip()
    try:
        tree = ast.parse(expression, mode="eval")
        return _safe_evaluate(tree, parameter_values)
    except Exception:
        return None


def generate_cpp_test_suite(
    original_code,
    modified_code,
    function_name,
    requirements,
):
    """Generate requirement-based tests and static original-behavior references."""
    try:
        signature = _parse_member_signature(modified_code, function_name)
        # Ensure the original signature is compatible with the proposed one.
        original_signature = _parse_member_signature(original_code, function_name)
        if (
            signature["class_name"] != original_signature["class_name"]
            or signature["parameters"] != original_signature["parameters"]
        ):
            raise ValueError(
                "Original and modified function class/parameter names must match "
                "to generate comparable tests."
            )

        if not re.search(r"\b(basic|base)\b", requirements or "", re.IGNORECASE):
            raise ValueError(
                "Requirements must describe the basic/base salary amount."
            )
        if not re.search(r"\bbonus\b", requirements or "", re.IGNORECASE):
            raise ValueError(
                "Requirements must explain how the bonus is included."
            )

        hra_rate = _parse_percentage(requirements, "HRA")
        da_rate = _parse_percentage(requirements, "DA")

        base_name = signature["parameters"][signature["base_index"]]
        bonus_name = signature["parameters"][signature["bonus_index"]]

        samples = [
            (30000.0, 5000.0, "normal salary and bonus"),
            (0.0, 5000.0, "zero basic salary"),
            (30000.0, 0.0, "zero bonus"),
            (1000000.0, 100000.0, "large salary values"),
        ]

        test_cases = []
        baseline_comparisons = []
        for base_value, bonus_value, label in samples:
            values = {base_name: base_value, bonus_name: bonus_value}
            expected = base_value + (base_value * hra_rate) + (base_value * da_rate) + bonus_value
            old_value = _baseline_value(original_code, values)
            test_cases.append({
                "name": label,
                "basic_salary": base_value,
                "bonus": bonus_value,
                "expected": expected,
            })
            if old_value is not None:
                baseline_comparisons.append({
                    "name": label,
                    "original_reference": old_value,
                    "requirement_expected": expected,
                    "behavior_differs": abs(old_value - expected) > 1e-9,
                })

        class_name = signature["class_name"]
        method_name = signature["function_name"]
        include_match = re.search(
            r"^\s*#include\s*[<\"]([^>\"]+)[>\"]",
            modified_code or "",
            re.MULTILINE,
        )
        header_name = include_match.group(1) if include_match else f"{class_name}.h"
        test_lines = [
            f'#include "{header_name}"',
            "#include <cmath>",
            "#include <iostream>",
            "",
            "int main() {",
            f"    {class_name} instance;",
            "    const double tolerance = 1e-6;",
            "",
        ]

        for index, case in enumerate(test_cases, start=1):
            args = [0.0, 0.0]
            args[signature["base_index"]] = case["basic_salary"]
            args[signature["bonus_index"]] = case["bonus"]
            arg_text = ", ".join(f"{value:.10g}" for value in args)
            test_lines.extend([
                f"    // Generated case {index}: {case['name']}",
                f"    const double actual_{index} = instance.{method_name}({arg_text});",
                f"    const double expected_{index} = {case['expected']:.10g};",
                f"    if (std::fabs(actual_{index} - expected_{index}) > tolerance) {{",
                f"        std::cerr << \"GENERATED_TEST_FAILURE: {case['name']} expected=\" << expected_{index} << \" actual=\" << actual_{index} << std::endl;",
                "        return 1;",
                "    }",
                f"    std::cout << \"GENERATED_TEST_PASSED: {case['name']}\" << std::endl;",
            ])
            baseline = next(
                (item for item in baseline_comparisons if item["name"] == case["name"]),
                None,
            )
            if baseline:
                test_lines.append(
                    f"    std::cout << \"BASELINE_REFERENCE: {case['name']} original={baseline['original_reference']:.10g} requirement_expected={baseline['requirement_expected']:.10g}\" << std::endl;"
                )
            test_lines.append("")

        test_lines.extend(["    return 0;", "}"])

        return {
            "supported": True,
            "reason": "Generated requirement-based C++ tests successfully.",
            "code": "\n".join(test_lines),
            "test_cases": test_cases,
            "baseline_comparisons": baseline_comparisons,
            "hra_percentage": hra_rate * 100,
            "da_percentage": da_rate * 100,
        }

    except Exception as error:
        return {
            "supported": False,
            "reason": str(error),
            "code": "",
            "test_cases": [],
            "baseline_comparisons": [],
        }
