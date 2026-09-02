import os
import json
from typing import Optional, List, Dict, Any, Type, Union
from pydantic import BaseModel, Field, create_model

# -----------------------------------------------------------------------------
# Built-in Preset Schemas
# -----------------------------------------------------------------------------

class ProductItem(BaseModel):
    """Structured record for an e-commerce product."""
    title: str = Field(description="Name or title of the product")
    price: float = Field(description="Numeric price of the product without currency symbols")
    currency: Optional[str] = Field(default="USD", description="Currency symbol or ISO code (e.g. USD, EUR, GBP)")
    rating: Optional[float] = Field(default=None, description="Star rating or review score (e.g. 4.5)")
    in_stock: bool = Field(default=True, description="Availability status (True if in stock, False otherwise)")
    description: Optional[str] = Field(default=None, description="Short product description or summary")
    url: Optional[str] = Field(default=None, description="Direct URL link to the product page")


class ArticleItem(BaseModel):
    """Structured record for a news article or blog post."""
    headline: str = Field(description="Article headline or title")
    author: Optional[str] = Field(default=None, description="Author name or publication byline")
    published_date: Optional[str] = Field(default=None, description="Publication date string")
    summary: str = Field(description="Summary or main excerpt of the article")
    category: Optional[str] = Field(default=None, description="Topic or category section")
    reading_time_min: Optional[int] = Field(default=None, description="Estimated reading time in minutes")


class JobPostingItem(BaseModel):
    """Structured record for an employment job posting."""
    job_title: str = Field(description="Title of the job position")
    company: str = Field(description="Hiring company or organization name")
    location: str = Field(description="Location (city, state, country, or Remote)")
    salary: Optional[str] = Field(default=None, description="Salary range or compensation details")
    remote: bool = Field(default=False, description="True if remote work is available")
    requirements: Optional[List[str]] = Field(default=None, description="Key qualifications or skills required")


PRESET_SCHEMAS: Dict[str, Type[BaseModel]] = {
    "product": ProductItem,
    "products": ProductItem,
    "article": ArticleItem,
    "articles": ArticleItem,
    "job": JobPostingItem,
    "jobs": JobPostingItem,
    "job_posting": JobPostingItem,
}

# -----------------------------------------------------------------------------
# Type Mapping & Dynamic Model Factory
# -----------------------------------------------------------------------------

TYPE_MAP: Dict[str, Any] = {
    "str": (str, ...),
    "string": (str, ...),
    "int": (int, ...),
    "integer": (int, ...),
    "float": (float, ...),
    "number": (float, ...),
    "bool": (bool, ...),
    "boolean": (bool, ...),
    "list[str]": (List[str], ...),
    "list": (List[str], ...),
    # Optional variations
    "str?": (Optional[str], None),
    "string?": (Optional[str], None),
    "int?": (Optional[int], None),
    "integer?": (Optional[int], None),
    "float?": (Optional[float], None),
    "number?": (Optional[float], None),
    "bool?": (Optional[bool], None),
    "boolean?": (Optional[bool], None),
    "list[str]?": (Optional[List[str]], None),
}

def parse_field_spec_string(spec: str) -> Dict[str, Any]:
    """
    Parses a string like 'title:str,price:float,rating:float?,in_stock:bool'
    into field definitions suitable for pydantic.create_model.
    """
    field_definitions = {}
    if not spec or not spec.strip():
        return field_definitions

    pairs = [p.strip() for p in spec.split(",") if p.strip()]
    for pair in pairs:
        if ":" in pair:
            name, type_str = pair.split(":", 1)
            name = name.strip()
            type_str = type_str.strip().lower()
            if type_str in TYPE_MAP:
                field_definitions[name] = TYPE_MAP[type_str]
            else:
                # Default to optional string if unknown
                field_definitions[name] = (Optional[str], None)
        else:
            # If no type specified, default to optional string
            field_definitions[pair.strip()] = (Optional[str], None)

    return field_definitions


def create_dynamic_schema(
    spec: Union[str, Dict[str, Any]], 
    model_name: str = "DynamicItem"
) -> Type[BaseModel]:
    """
    Dynamically creates a Pydantic model class from a string specification or dictionary.
    
    Examples:
        create_dynamic_schema("title:str,price:float,in_stock:bool")
        create_dynamic_schema({"title": "str", "price": "float"})
    """
    if isinstance(spec, str):
        field_definitions = parse_field_spec_string(spec)
    elif isinstance(spec, dict):
        field_definitions = {}
        for name, type_val in spec.items():
            type_str = str(type_val).strip().lower()
            if type_str in TYPE_MAP:
                field_definitions[name] = TYPE_MAP[type_str]
            else:
                field_definitions[name] = (Optional[str], None)
    else:
        raise ValueError(f"Unsupported schema spec type: {type(spec)}")

    if not field_definitions:
        raise ValueError("Cannot create dynamic schema with no fields.")

    return create_model(model_name, **field_definitions)


def resolve_schema(schema_input: Any) -> Type[BaseModel]:
    """
    Resolves a schema input into a Pydantic BaseModel class.
    
    Accepts:
      - A Pydantic BaseModel class
      - A preset name ('product', 'article', 'job')
      - A comma-separated type specification ('title:str,price:float')
      - A filepath to a JSON schema file (.json)
      - A dictionary mapping field names to types
    """
    if schema_input is None:
        raise ValueError("Schema input cannot be None.")

    # 1. Already a Pydantic model
    if isinstance(schema_input, type) and issubclass(schema_input, BaseModel):
        return schema_input

    # 2. String input
    if isinstance(schema_input, str):
        cleaned = schema_input.strip()

        # Check presets
        if cleaned.lower() in PRESET_SCHEMAS:
            return PRESET_SCHEMAS[cleaned.lower()]

        # Check if file path
        if (cleaned.endswith(".json") or os.path.exists(cleaned)) and os.path.isfile(cleaned):
            with open(cleaned, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    # Check if it's a mapping of {field: type}
                    return create_dynamic_schema(data)
                raise ValueError(f"JSON schema file '{cleaned}' must contain a JSON object.")

        # Check if JSON string
        if cleaned.startswith("{") and cleaned.endswith("}"):
            try:
                data = json.loads(cleaned)
                if isinstance(data, dict):
                    return create_dynamic_schema(data)
            except Exception:
                pass

        # Check if comma-separated field spec (e.g. 'title:str,price:float')
        if ":" in cleaned:
            return create_dynamic_schema(cleaned)

        raise ValueError(
            f"Unrecognized schema '{schema_input}'. Available presets: {list(PRESET_SCHEMAS.keys())}, "
            f"or specify fields as 'name:type,name2:type'."
        )

    # 3. Dictionary input
    if isinstance(schema_input, dict):
        return create_dynamic_schema(schema_input)

    raise ValueError(f"Unsupported schema type: {type(schema_input)}")
