
def build_dependency_map(results):

    function_to_files = {}

    for function in results["functions"]:

        name = function["name"]
        file = function["file"]

        function_to_files.setdefault(name, set()).add(file)

    dependencies = []

    for call in results["function_calls"]:

        function_name = call["name"]
        caller_file = call["file"]

        target_files = function_to_files.get(
            function_name, set()
        )

        for target_file in target_files:

            # Ignore same-file calls
            if caller_file == target_file:
                continue

            # Avoid matching main() across unrelated files
            if function_name == "main":
                continue

            # Avoid treating header declarations as callers
            if caller_file.endswith((".h", ".hpp")):
                continue

            dependency = {
                "source": caller_file,
                "target": target_file,
                "function": function_name
            }

            if dependency not in dependencies:
                dependencies.append(dependency)

    return dependencies
