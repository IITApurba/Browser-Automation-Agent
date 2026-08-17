from pydantic import BaseModel


class ExtractionField(BaseModel):
    selector: str
    attr: str = "text"
    multiple: bool = False


class ExtractionSchema(BaseModel):
    name: str
    fields: dict[str, ExtractionField]

    def to_toolkit_dict(self) -> dict:
        return {
            field_name: {"selector": f.selector, "attr": f.attr, "multiple": f.multiple}
            for field_name, f in self.fields.items()
        }

    @classmethod
    def from_dict(cls, name: str, raw: dict) -> "ExtractionSchema":
        fields = {k: ExtractionField(**v) for k, v in raw.items()}
        return cls(name=name, fields=fields)
