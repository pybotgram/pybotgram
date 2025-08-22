from pydantic import BaseModel


class FieldModel(BaseModel):
    """
    Represents a single field within a complex type definition.

    Each field includes its name, type(s), whether it's required, and a description.
    """

    name: str
    types: list[str]
    required: bool
    description: str


class TypeDefinition(BaseModel):
    """
    Represents a detailed definition of a complex type, such as 'Update' in the Telegram Bot API.

    Includes the type name, reference URL to official documentation, a description,
    and a list of fields describing the structure of the type.
    """

    name: str
    href: str
    description: list[str]
    fields: list[FieldModel] = []
    subtypes: list[str] = []
    subtype_of: list[str] = []


class TypesModel(BaseModel):
    """
    Represents a collection of type definitions.

    The 'types' dictionary maps type names (as strings) to their corresponding
    full TypeDefinition objects, which include metadata and fields for each type.
    """

    types: dict[str, TypeDefinition]
