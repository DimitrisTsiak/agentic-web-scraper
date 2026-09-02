import pytest
from pydantic import BaseModel
from src.extractor.schemas import (
    ProductItem,
    ArticleItem,
    JobPostingItem,
    PRESET_SCHEMAS,
    create_dynamic_schema,
    resolve_schema,
)

def test_preset_schemas():
    prod = ProductItem(title="Test Product", price=29.99, rating=4.5)
    assert prod.title == "Test Product"
    assert prod.price == 29.99
    assert prod.in_stock is True

    art = ArticleItem(headline="Breaking News", summary="Something happened.")
    assert art.headline == "Breaking News"
    assert art.author is None

    job = JobPostingItem(job_title="Software Engineer", company="TechCorp", location="Remote", remote=True)
    assert job.remote is True


def test_create_dynamic_schema_from_string():
    Model = create_dynamic_schema("title:str,price:float,in_stock:bool,rating:float?")
    assert issubclass(Model, BaseModel)

    item = Model(title="Book", price=12.5, in_stock=True)
    assert item.title == "Book"
    assert item.price == 12.5
    assert item.in_stock is True
    assert item.rating is None


def test_create_dynamic_schema_from_dict():
    Model = create_dynamic_schema({"name": "string", "quantity": "int", "available": "bool"})
    assert issubclass(Model, BaseModel)

    item = Model(name="Gadget", quantity=5, available=False)
    assert item.name == "Gadget"
    assert item.quantity == 5
    assert item.available is False


def test_resolve_schema():
    # 1. By preset name
    assert resolve_schema("product") == ProductItem
    assert resolve_schema("article") == ArticleItem
    assert resolve_schema("job") == JobPostingItem

    # 2. Directly by class
    assert resolve_schema(ProductItem) == ProductItem

    # 3. By field spec string
    dynamic_model = resolve_schema("title:str,price:float")
    assert issubclass(dynamic_model, BaseModel)
    assert "title" in dynamic_model.model_fields
    assert "price" in dynamic_model.model_fields

    # 4. By dictionary
    dict_model = resolve_schema({"headline": "str", "views": "int"})
    assert issubclass(dict_model, BaseModel)
    assert "headline" in dict_model.model_fields
    assert "views" in dict_model.model_fields

    # 5. Invalid
    with pytest.raises(ValueError):
        resolve_schema("nonexistent_preset_xyz")

def test_resolve_schema_file_lookup_security(tmp_path):
    # Create temporary json schema file
    schema_file = tmp_path / "custom_schema.json"
    schema_file.write_text('{"item": "str", "cost": "float"}', encoding="utf-8")

    # Disallowed by default (security protection for API)
    with pytest.raises(ValueError) as exc:
        resolve_schema(str(schema_file), allow_file_lookup=False)
    assert "Unrecognized schema" in str(exc.value)

    # Allowed when explicitly enabled (CLI usage)
    model = resolve_schema(str(schema_file), allow_file_lookup=True)
    assert issubclass(model, BaseModel)
    assert "item" in model.model_fields
    assert "cost" in model.model_fields
