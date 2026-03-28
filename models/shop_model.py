# models/shop_model.py
from dataclasses import dataclass, asdict


@dataclass
class ShopModel:
    shop_name: str = ""
    owner_name: str = ""
    address: str = ""
    mobile: str = ""
    gst_number: str = ""
    email: str = ""
    invoice_prefix: str = "JB"
    default_tax: float = 3.0
    printer: str = ""

    def to_dict(self): return asdict(self)

    @classmethod
    def from_dict(cls, d: dict):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
