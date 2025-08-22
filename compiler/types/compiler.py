import json
import pathlib
import re
import textwrap

from black import format_str, Mode

from model import TypesModel, FieldModel

LINE_LENGTH = 79

NO_INDENT = ""
FOUR_SPACE_INDENT = " " * 4
EIGHT_SPACE_INDENT = " " * 8
TWELVE_SPACE_INDENT = " " * 12

NEW_LINE = "\n"
DOUBLE_NEW_LINE = "\n\n"

HEADER_IMPORT_TYPING = "import typing"
HEADER_TYPING_CHECKING = "if typing.TYPE_CHECKING:"

PYBOTGRAM_TYPES_IMPORT = "from pybotgram.types import "

BLACK_MODE = Mode(line_length=LINE_LENGTH)

WARNING = """
# # # # # # # # # # # # # # # # # # # # # # # #
#               !!! WARNING !!!               #
#          This is a generated file!          #
# All changes made in this file will be lost! #
# # # # # # # # # # # # # # # # # # # # # # # #
""".strip()

TYPES_MAP = {
    "String": "str",
    "Integer": "int",
    "Boolean": "bool",
    "Float": "float",
}


# Converts CamelCase to snake_case
def camel_to_snake(name):
    # https://stackoverflow.com/a/1176023
    name = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()


# Generates the docstring type for a field (for documentation only)
def generate_field_type_docstring(field: FieldModel) -> str:
    def _get_type(t: str) -> str:
        if t in TYPES_MAP:
            return f"``{TYPES_MAP[t]}``"
        elif t.startswith("Array of"):
            new_type = _get_type(t[len("Array of ") :])
            return f"List of {new_type}"
        else:
            return f":obj:`~pybotgram.types.{t}`"

    is_required = lambda x: ", *optional*" if not x else ""

    return " | ".join(map(_get_type, field.types)) + is_required(
        field.required
    )


# Generates actual type hints for a field (used in class definition)
def generate_field_type(field: FieldModel) -> str:
    def _gen_type(t: str) -> str:
        if t in TYPES_MAP:
            return TYPES_MAP[t]
        elif t.startswith("Array of"):
            new_type = _gen_type(t[len("Array of ") :])
            return f"list[{new_type}]"
        else:
            return t

    field_types = list(field.types)

    if not field.required:
        field_types.append("None")

    return " | ".join(map(_gen_type, field_types))


# Generates required imports based on types
def generate_imports(fields: list[FieldModel]) -> tuple[str, str]:
    def is_custom_type(type_n: str) -> bool:
        return type_n not in TYPES_MAP and not type_n.startswith("Array of ")

    result = set()

    for field in fields:
        for type_name in field.types:
            if type_name.startswith("Array of "):
                type_name = type_name.replace("Array of ", "")

            if is_custom_type(type_name):
                result.add(type_name)

    if not result:
        return "", ""

    types_import_line = (
        FOUR_SPACE_INDENT + PYBOTGRAM_TYPES_IMPORT + ", ".join(sorted(result))
    )
    types_import_line = (
        "\n" + HEADER_TYPING_CHECKING + "\n" + types_import_line + "\n"
    )

    return "\n" + HEADER_IMPORT_TYPING + "\n", types_import_line


# Generates the docstring section of the class
def generate_docstring(
    description: list[str], fields: list[FieldModel]
) -> str:
    result = ""

    for i, x in enumerate(description):
        if x.endswith("of"):
            x += ":"

        result += textwrap.fill(
            x,
            initial_indent=NO_INDENT if i == 0 else FOUR_SPACE_INDENT,
            subsequent_indent=FOUR_SPACE_INDENT,
            break_long_words=False,
            break_on_hyphens=False,
        )

        # Skip last iteration
        if i == len(description) - 1:
            continue

        if x.startswith("-"):
            result += NEW_LINE
        else:
            result += DOUBLE_NEW_LINE

    if len(fields) > 0:
        result += f"\n\n{FOUR_SPACE_INDENT}Parameters:\n"

    for i, field in enumerate(fields):
        field_name = field.name

        if field_name == "from":
            field_name = "from_user"

        field_type = generate_field_type_docstring(field)
        field_header = f"{field_name} ({field_type}):"

        field_description = field.description
        if field_description.startswith("Optional."):
            field_description = field_description.replace("Optional. ", "", 1)

        result += textwrap.fill(
            field_header,
            initial_indent=EIGHT_SPACE_INDENT,
            subsequent_indent=EIGHT_SPACE_INDENT,
            break_long_words=False,
            break_on_hyphens=False,
        )
        result += "\n"
        result += textwrap.fill(
            field_description,
            initial_indent=TWELVE_SPACE_INDENT,
            subsequent_indent=TWELVE_SPACE_INDENT,
            break_long_words=False,
            break_on_hyphens=False,
        )

        # Skip last iteration
        if i == len(fields) - 1:
            continue

        result += "\n\n"

    return result


# Generates the actual class fields (attributes with type hints)
def generate_fields(fields: list[FieldModel]) -> str:
    result = ""

    for i, field in enumerate(fields):
        field_name = field.name

        if field_name == "from":
            field_name = "from_user"

        field_type = generate_field_type(field)
        field_value = " = None" if not field.required else ""

        result += NO_INDENT if i == 0 else FOUR_SPACE_INDENT
        result += f"{field_name}: {field_type}{field_value}"

        # Skip last iteration
        if i == len(fields) - 1:
            continue

        result += "\n"

    return result


# Generates he imports of __init__.py
def generate_init_imports(init_data: dict[str, str]) -> str:
    result = ""

    for file_name, class_name in init_data.items():
        result += f"from {file_name} import {class_name}\n"

    return result


# Saves the generated class to file
def save_types(
    types_generated_dir: pathlib.Path,
    file_name: str,
    std_imports: str,
    imports: str,
    class_name: str,
    docstring: str,
    fields: str,
    template_file: str,
) -> None:
    with open(types_generated_dir / f"{file_name}.py", "w") as f:
        f.write(
            format_str(
                template_file.format(
                    warning=WARNING,
                    std_imports=std_imports,
                    imports=imports,
                    class_name=class_name,
                    docstring=docstring,
                    fields=fields,
                ),
                mode=BLACK_MODE,
            )
        )


# Main function that drives generation of all type classes
def generate_types(
    types: TypesModel,
    template_dir: pathlib.Path,
    types_generated_dir: pathlib.Path,
) -> None:
    # Open the template file for types
    with open(template_dir / "types.txt", "r") as f:
        template_text = f.read()

    # Open the template file for __init__.py
    with open(template_dir / "init.txt", "r") as f:
        init_template_text = f.read()

    # Create directory if not exists
    types_generated_dir.mkdir(parents=True, exist_ok=True)

    # Dict file_name: class_name
    init_data = {}

    for class_name, v in types.types.items():
        description = v.description
        fields = v.fields

        file_name = camel_to_snake(class_name)
        init_data[file_name] = class_name

        typing_import, types_import = generate_imports(fields)

        save_types(
            types_generated_dir,
            file_name,
            typing_import,
            types_import,
            class_name,
            generate_docstring(description, fields),
            generate_fields(fields),
            template_text,
        )

    # Generate __init__.py
    with open(types_generated_dir / "__init__.py", "w") as f:
        f.write(
            format_str(
                init_template_text.format(
                    warning=WARNING,
                    classes=",\n".join(
                        map(lambda x: f'"{x}"', init_data.values())
                    ),
                    imports=generate_init_imports(init_data),
                ),
                mode=BLACK_MODE,
            )
        )


def _main():
    # Get current directory
    current_directory = pathlib.Path(__file__).parent

    # Path to the directory containing the Telegram Bot API specification
    root_directory = current_directory.parent.parent
    spec_dir = root_directory / "telegram-bot-api-spec"
    spec_file = spec_dir / "api.min.json"

    # Load the Telegram API specification JSON
    with open(spec_file, "r", encoding="utf-8") as file:
        api_spec_data = json.load(file)

    # Path for generator
    template_directory = current_directory / "template"
    types_generated_directory = root_directory / "pybotgram" / "types"

    # Validate the loaded specification using the TypesModel
    validated_model = TypesModel.model_validate(api_spec_data)
    generate_types(
        validated_model, template_directory, types_generated_directory
    )


if __name__ == "__main__":
    _main()
