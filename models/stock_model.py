# models/stock_model.py
from dataclasses import dataclass, asdict


@dataclass
class StockModel:
    item_id: str = ""
    item_name: str = ""
    category: str = ""
    purity: str = ""
    gross_weight: float = 0.0
    net_weight: float = 0.0
    quantity: int = 0
    purchase_price: float = 0.0
    selling_price: float = 0.0
    vendor_name: str = ""
    remarks: str = ""

    def to_dict(self): return asdict(self)

    @classmethod
    def from_dict(cls, d: dict):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
