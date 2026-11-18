
"""Rule-based C++ test generation for numeric and Employee-based member functions."""

import ast
import re
from pathlib import Path


_NUMERIC_PARAMETER = re.compile(
    r"^(?:const\s+)?(?:unsigned\s+)?(?:long\s+long|long|short|double|float|int)"
    r"\s*(?:[&*]\s*)?(\w+)\s*$"
)



def _parse_method(code, expected_function):
    """Parse a supported C++ member function, including const getters."""

    pattern = re.compile(
        r"\b(?P<return_type>"
        r"(?:std::)?(?:unsigned\s+)?"
        r"(?:long\s+long|long|short|int|double|float|bool|char|string|void)"
        r")\s+"
        r"(?P<class_name>[A-Za-z_]\w*)::"
        r"(?P<function_name>[A-Za-z_]\w*)\s*"
        r"\((?P<params>[^()]*)\)\s*"
        r"(?:const\s*)?"
        r"\{",
        re.MULTILINE,
    )

    match = pattern.search(code or "")

    if not match:
        raise ValueError(
            "Could not identify the selected C++ member function."
        )

    if match.group("function_name") != expected_function:
        raise ValueError(
            "The function name does not match the selected function."
        )

    parameters = [
        item.strip()
        for item in match.group("params").split(",")
        if item.strip()
    ]

    return {
        "return_type": match.group("return_type"),
        "class_name": match.group("class_name"),
        "function_name": match.group("function_name"),
        "parameters": parameters,
    }


def _parse_numeric_signature(code, expected_function):
    signature = _parse_method(code, expected_function)
    names = []

    for parameter in signature["parameters"]:
        match = _NUMERIC_PARAMETER.match(parameter)
        if not match:
            raise ValueError("This function does not have two supported numeric parameters.")
        names.append(match.group(1))

    base_index = next(
        (i for i, name in enumerate(names)
         if "basic" in name.lower() or "base" in name.lower()),
        None,
    )
    bonus_index = next(
        (i for i, name in enumerate(names)
         if "bonus" in name.lower()),
        None,
    )

    if base_index is None or bonus_index is None or base_index == bonus_index:
        raise ValueError("Could not identify basic salary and bonus parameters.")

    signature.update({
        "parameter_names": names,
        "base_index": base_index,
        "bonus_index": bonus_index,
    })
    return signature


def _parse_employee_signature(code, expected_function):
    signature = _parse_method(code, expected_function)
    params = signature["parameters"]

    object_match = re.match(
        r"^\s*const\s+(?P<type>[A-Za-z_]\w*)\s*&\s*(?P<name>\w+)\s*$",
        params[0],
    )
    bonus_match = _NUMERIC_PARAMETER.match(params[1])

    if not object_match or not bonus_match:
        raise ValueError(
            "Object-based generation currently supports "
            "const Employee& employee followed by a numeric bonus."
        )

    if object_match.group("type") != "Employee":
        raise ValueError("Only the Employee object parameter is supported currently.")

    if "bonus" not in bonus_match.group(1).lower():
        raise ValueError("The second parameter must be named bonus.")

    signature.update({
        "employee_name": object_match.group("name"),
        "bonus_name": bonus_match.group(1),
    })
    return signature


def _parse_percentage(text, label):
    match = re.search(
        rf"\b{label}\b\s*(?:=|:|is|of)?\s*(\d+(?:\.\d+)?)\s*%",
        text or "",
        re.IGNORECASE,
    )
    if not match:
        raise ValueError(
            f"Could not determine {label} percentage. "
            f"Expected a value such as {label} = 20%."
        )

    value = float(match.group(1))
    if not 0 <= value <= 100:
        raise ValueError(f"{label} percentage must be between 0 and 100.")

    return value / 100.0


def _parse_fixed_allowance(requirements):
    patterns = [
        r"transport\s+allowance\s*(?:=|:|of|is)?\s*(?:₹|rs\.?\s*)?(\d+(?:\.\d+)?)",
        r"(?:₹|rs\.?\s*)(\d+(?:\.\d+)?)\s*transport\s+allowance",
        r"allowance\s+of\s*(?:₹|rs\.?\s*)?(\d+(?:\.\d+)?)",
    ]

    for pattern in patterns:
        match = re.search(pattern, requirements or "", re.IGNORECASE)
        if match:
            return float(match.group(1))

    raise ValueError(
        "Could not determine the transport allowance amount. "
        "Specify it clearly, for example: Transport Allowance = 2000."
    )


def _safe_evaluate(node, values):
    """Evaluate a restricted arithmetic AST without executing arbitrary code."""
    if isinstance(node, ast.Expression):
        return _safe_evaluate(node.body, values)

    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)

    if isinstance(node, ast.Name) and node.id in values:
        return float(values[node.id])

    if isinstance(node, ast.UnaryOp):
        value = _safe_evaluate(node.operand, values)
        if isinstance(node.op, ast.UAdd):
            return value
        if isinstance(node.op, ast.USub):
            return -value

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

    raise ValueError("Unsupported arithmetic expression.")


def _baseline_value(original_code, parameter_values):
    returns = re.findall(
        r"\breturn\s+(.+?)\s*;",
        original_code or "",
        re.DOTALL,
    )
    if not returns:
        return None

    try:
        tree = ast.parse(returns[-1].strip(), mode="eval")
        return _safe_evaluate(tree, parameter_values)
    except Exception:
        return None


def _find_project_file(project_path, filename):
    root = Path(project_path).resolve()

    candidates = [
        root / "include" / filename,
        root / filename,
        root / "src" / filename,
    ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    matches = list(root.rglob(filename))
    if matches:
        return matches[0]

    raise ValueError(f"Could not find {filename} in the selected project.")


def _read_employee_constructor(project_path):
    header = _find_project_file(project_path, "Employee.h")
    content = header.read_text(encoding="utf-8", errors="ignore")

    constructor = re.search(
        r"\bEmployee\s*\(\s*int\s+\w+\s*,\s*"
        r"std::string\s+\w+\s*,\s*double\s+\w+\s*\)\s*;",
        content,
    )

    if not constructor:
        raise ValueError(
            "Employee.h does not contain the supported constructor: "
            "Employee(int, std::string, double)."
        )

    return header.name


def _read_salary_rates(project_path):
    salary_file = _find_project_file(project_path, "Salary.cpp")
    content = salary_file.read_text(encoding="utf-8", errors="ignore")

    hra_match = re.search(
        r"\bhra\s*=\s*\w+\s*\*\s*(\d+(?:\.\d+)?)",
        content,
        re.IGNORECASE,
    )
    da_match = re.search(
        r"\bda\s*=\s*\w+\s*\*\s*(\d+(?:\.\d+)?)",
        content,
        re.IGNORECASE,
    )

    if not hra_match or not da_match:
        raise ValueError(
            "Could not safely read HRA and DA calculation rates from Salary.cpp."
        )

    hra_rate = float(hra_match.group(1))
    da_rate = float(da_match.group(1))

    if hra_rate > 1:
        hra_rate /= 100.0
    if da_rate > 1:
        da_rate /= 100.0

    if not 0 <= hra_rate <= 1 or not 0 <= da_rate <= 1:
        raise ValueError("The HRA or DA rate in Salary.cpp is outside the supported range.")

    return hra_rate, da_rate


def _generate_numeric_tests(
    original_code, modified_code, function_name, requirements
):
    signature = _parse_numeric_signature(modified_code, function_name)
    original_signature = _parse_numeric_signature(original_code, function_name)

    if (
        signature["class_name"] != original_signature["class_name"]
        or signature["parameter_names"] != original_signature["parameter_names"]
    ):
        raise ValueError("Original and modified function signatures must match.")

    if not re.search(r"\b(basic|base)\b", requirements or "", re.IGNORECASE):
        raise ValueError("Requirements must describe the basic/base salary amount.")

    if not re.search(r"\bbonus\b", requirements or "", re.IGNORECASE):
        raise ValueError("Requirements must explain how the bonus is included.")

    hra_rate = _parse_percentage(requirements, "HRA")
    da_rate = _parse_percentage(requirements, "DA")

    base_name = signature["parameter_names"][signature["base_index"]]
    bonus_name = signature["parameter_names"][signature["bonus_index"]]

    samples = [
        (30000.0, 5000.0, "normal salary and bonus"),
        (0.0, 5000.0, "zero basic salary"),
        (30000.0, 0.0, "zero bonus"),
        (1000000.0, 100000.0, "large salary values"),
    ]

    cases = []
    baselines = []

    for base, bonus, label in samples:
        expected = base + base * hra_rate + base * da_rate + bonus
        old_value = _baseline_value(
            original_code,
            {base_name: base, bonus_name: bonus},
        )

        cases.append({
            "name": label,
            "basic_salary": base,
            "bonus": bonus,
            "expected": expected,
        })

        if old_value is not None:
            baselines.append({
                "name": label,
                "original_reference": old_value,
                "requirement_expected": expected,
                "behavior_differs": abs(old_value - expected) > 1e-9,
            })

    include_match = re.search(
        r'^\s*#include\s*[<"]([^>"]+)[>"]',
        modified_code or "",
        re.MULTILINE,
    )
    header = include_match.group(1) if include_match else f"{signature['class_name']}.h"

    lines = [
        f'#include "{header}"',
        "#include <cmath>",
        "#include <iostream>",
        "",
        "int main() {",
        f"    {signature['class_name']} instance;",
        "    const double tolerance = 1e-6;",
        "",
    ]

    for index, case in enumerate(cases, start=1):
        args = [0.0, 0.0]
        args[signature["base_index"]] = case["basic_salary"]
        args[signature["bonus_index"]] = case["bonus"]
        arg_text = ", ".join(f"{value:.10g}" for value in args)

        lines.extend([
            f"    // Generated case {index}: {case['name']}",
            f"    const double actual_{index} = instance.{function_name}({arg_text});",
            f"    const double expected_{index} = {case['expected']:.10g};",
            f"    if (std::fabs(actual_{index} - expected_{index}) > tolerance) {{",
            f'        std::cerr << "GENERATED_TEST_FAILURE: {case["name"]}" << std::endl;',
            "        return 1;",
            "    }",
            f'    std::cout << "GENERATED_TEST_PASSED: {case["name"]}" << std::endl;',
            "",
        ])

    lines.extend(["    return 0;", "}"])

    return {
        "supported": True,
        "reason": "Generated requirement-based C++ tests successfully.",
        "code": "\n".join(lines),
        "test_cases": cases,
        "baseline_comparisons": baselines,
        "hra_percentage": hra_rate * 100,
        "da_percentage": da_rate * 100,
    }


def _generate_employee_tests(
    original_code,
    modified_code,
    function_name,
    requirements,
    project_path,
):
    signature = _parse_employee_signature(modified_code, function_name)
    original_signature = _parse_employee_signature(original_code, function_name)

    if (
        signature["class_name"] != original_signature["class_name"]
        or signature["parameters"] != original_signature["parameters"]
    ):
        raise ValueError("Original and modified EmployeeService signatures must match.")

    if not re.search(r"\bbonus\b", requirements or "", re.IGNORECASE):
        raise ValueError("Requirements must explain how the bonus is included.")

    if not re.search(r"\b(basic|base)\b", requirements or "", re.IGNORECASE):
        raise ValueError("Requirements must mention basic/base salary.")

    employee_header = _read_employee_constructor(project_path)
    hra_rate, da_rate = _read_salary_rates(project_path)
    allowance = _parse_fixed_allowance(requirements)

    samples = [
        (30000.0, 5000.0, "normal salary and bonus"),
        (0.0, 5000.0, "zero basic salary"),
        (30000.0, 0.0, "zero bonus"),
        (1000000.0, 100000.0, "large salary values"),
    ]

    cases = []
    baselines = []

    for base, bonus, label in samples:
        expected = (
            base
            + base * hra_rate
            + base * da_rate
            + bonus
            + allowance
        )

        cases.append({
            "name": label,
            "basic_salary": base,
            "bonus": bonus,
            "transport_allowance": allowance,
            "expected": expected,
        })

    include_match = re.search(
        r'^\s*#include\s*[<"]([^>"]+)[>"]',
        modified_code or "",
        re.MULTILINE,
    )
    service_header = (
        include_match.group(1)
        if include_match
        else f"{signature['class_name']}.h"
    )

    employee_name = signature["employee_name"]
    bonus_name = signature["bonus_name"]

    lines = [
        f'#include "{service_header}"',
        "#include <cmath>",
        "#include <iostream>",
        "",
        "int main() {",
        f"    {signature['class_name']} service;",
        "    const double tolerance = 1e-6;",
        "",
    ]

    for index, case in enumerate(cases, start=1):
        lines.extend([
            f"    // Generated case {index}: {case['name']}",
            f'    Employee {employee_name}_{index}({index}, "Test Employee", {case["basic_salary"]:.10g});',
            f"    const double actual_{index} = service.{function_name}({employee_name}_{index}, {case['bonus']:.10g});",
            f"    const double expected_{index} = {case['expected']:.10g};",
            f"    if (std::fabs(actual_{index} - expected_{index}) > tolerance) {{",
            f'        std::cerr << "GENERATED_TEST_FAILURE: {case["name"]}"',
            f'                  << " expected=" << expected_{index}',
            f'                  << " actual=" << actual_{index} << std::endl;',
            "        return 1;",
            "    }",
            f'    std::cout << "GENERATED_TEST_PASSED: {case["name"]}" << std::endl;',
            "",
        ])

    lines.extend(["    return 0;", "}"])

    return {
        "supported": True,
        "reason": "Generated Employee-object requirement-based C++ tests successfully.",
        "code": "\n".join(lines),
        "test_cases": cases,
        "baseline_comparisons": baselines,
        "hra_percentage": hra_rate * 100,
        "da_percentage": da_rate * 100,
        "transport_allowance": allowance,
        "employee_header": employee_header,
    }


def _generate_getter_tests(
    original_code,
    modified_code,
    function_name,
    requirements,
    project_path=None,
):
    """Generate requirement-based tests for zero-parameter numeric getters."""

    signature = _parse_method(modified_code, function_name)
    original_signature = _parse_method(original_code, function_name)

    if signature["parameters"]:
        raise ValueError("Getter must have zero parameters.")

    if original_signature["parameters"]:
        raise ValueError("Original getter must have zero parameters.")

    if signature["class_name"] != original_signature["class_name"]:
        raise ValueError("Original and modified class names must match.")

    if signature["return_type"] != original_signature["return_type"]:
        raise ValueError("Original and modified return types must match.")

    if signature["return_type"] not in ("int", "long", "short"):
        raise ValueError(
            "Currently, getter generation supports integer return types."
        )

    if not project_path:
        raise ValueError("Project path is required for getter test generation.")

    if not re.search(r"\bexact\b", requirements or "", re.IGNORECASE):
        raise ValueError("Requirement must specify the exact stored value.")

    if not re.search(r"\b(id|identifier)\b", requirements or "", re.IGNORECASE):
        raise ValueError("Requirement must describe the employee ID.")

    if not re.search(r"\b(positive|negative)\b", requirements or "", re.IGNORECASE):
        raise ValueError("Requirement must cover positive and negative IDs.")

    header = _find_project_file(
        project_path,
        f"{signature['class_name']}.h"
    ).name

    samples = [
        (101, "positive employee ID"),
        (0, "zero employee ID"),
        (-10, "negative employee ID"),
    ]

    cases = []

    lines = [
        f'#include "{header}"',
        "#include <iostream>",
        "",
        "int main() {",
        "",
    ]

    for index, (employee_id, label) in enumerate(samples, start=1):
        cases.append({
            "name": label,
            "employee_id": employee_id,
            "expected": employee_id,
        })

        lines.extend([
            f"    // Test case {index}: {label}",
            (
                f'    {signature["class_name"]} employee_{index}'
                f'({employee_id}, "Test Employee", 50000.0);'
            ),
            (
                f"    int actual_{index} = "
                f"employee_{index}.{function_name}();"
            ),
            f"    int expected_{index} = {employee_id};",
            f"    if (actual_{index} != expected_{index}) {{",
            (
                f'        std::cerr << "GENERATED_TEST_FAILURE: {label}"'
                f' << std::endl;'
            ),
            "        return 1;",
            "    }",
            (
                f'    std::cout << "GENERATED_TEST_PASSED: {label}"'
                f' << std::endl;'
            ),
            "",
        ])

    lines.extend([
        "    return 0;",
        "}",
    ])

    return {
        "supported": True,
        "reason": "Generated zero-parameter getter tests successfully.",
        "code": "\n".join(lines),
        "test_cases": cases,
        "baseline_comparisons": [],
    }


def generate_cpp_test_suite(
    original_code,
    modified_code,
    function_name,
    requirements,
    project_path=None,
):
    """Generate C++ tests using the appropriate supported test strategy."""

    try:
        signature = _parse_method(modified_code, function_name)

        # Mode 1: Zero-parameter getter
        if not signature["parameters"]:
            return _generate_getter_tests(
                original_code,
                modified_code,
                function_name,
                requirements,
                project_path,
            )

        # Mode 2: Existing numeric salary generation
        try:
            _parse_numeric_signature(modified_code, function_name)

            return _generate_numeric_tests(
                original_code,
                modified_code,
                function_name,
                requirements,
            )

        except ValueError:
            pass

        # Mode 3: Existing Employee-object salary generation
        if not project_path:
            raise ValueError(
                "Project path is required for Employee-object test generation."
            )

        return _generate_employee_tests(
            original_code,
            modified_code,
            function_name,
            requirements,
            project_path,
        )

    except Exception as error:
        return {
            "supported": False,
            "reason": str(error),
            "code": "",
            "test_cases": [],
            "baseline_comparisons": [],
        }
