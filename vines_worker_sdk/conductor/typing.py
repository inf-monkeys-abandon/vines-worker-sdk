from typing import List, Dict, Any


class BlockInputOption:
    def __init__(self, name: str, value: Any):
        self.name = name
        self.value = value


class BlockInputDef:
    def __init__(self, display_name: str, name: str, type: str, default: Any = None, required: bool = False,
                 description: str = None, type_options: Dict[str, Any] = None, options: List[BlockInputOption] = None,
                 display_options: Dict = None):
        self.displayName = display_name
        self.name = name
        self.type = type
        self.default = default
        self.required = required
        self.description = description
        self.type_options = type_options
        self.options = options
        self.display_options = display_options


class BlockOutputDef:
    def __init__(self, display_name: str, name: str, type: str, default: Any = None, required: bool = False,
                 description: str = None, type_options: Dict[str, Any] = None, options: List[BlockInputOption] = None,
                 display_options: Dict = None, properties: List[Any] = None):
        self.displayName = display_name
        self.name = name
        self.type = type
        self.default = default
        self.required = required
        self.description = description
        self.type_options = type_options
        self.options = options
        self.display_options = display_options
        self.properties = properties


class BlockDef:
    def __init__(
            self,
            name: str,
            categories: List[str],
            display_name: str,
            description: str,
            icon: str,
            input: List[BlockInputDef],
            output: List[BlockOutputDef],
            extra: Dict[str, Any] = None,
    ):
        self.type = type
        self.name = name
        self.categories = categories
        self.display_name = display_name
        self.description = description
        self.icon = icon
        self.extra = extra
        self.input = input
        self.output = output


class CredentialDef:
    def __init__(self, name: str, display_name: str, input: List[BlockInputDef], logo: str, type: str):
        self.displayName = display_name
        self.name = name
        self.input = input
        self.logo = logo
        self.type = type
