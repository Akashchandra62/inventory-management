# models/invoice_model.py
from dataclasses import dataclass, field, asdict
from typing import List


@dataclass
class InvoiceItem:
    name: str = ""
    category: str = ""
    quantity: int = 1
    weight: float = 0.0
    rate: float = 0.0
    making_charge: float = 0.0
    stone_charge: float = 0.0
    tax_percent: float = 0.0
    discount: float = 0.0
    total: float = 0.0

    def to_dict(self): return asdict(self)

    @classmethod
    def from_dict(cls, d: dict):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def calculate_total(self):
        base = (self.rate * self.weight) + self.making_charge + self.stone_charge
        tax_amt = base * (self.tax_percent / 100)
        self.total = round(base + tax_amt - self.discount, 2)
        return self.total


@dataclass
class InvoiceModel:
    invoice_id: str = ""
    invoice_number: str = ""
    date: str = ""
    time: str = ""
    customer_name: str = ""
    customer_mobile: str = ""
    customer_address: str = ""
    items: List[dict] = field(default_factory=list)
    subtotal: float = 0.0
    tax_percent: float = 0.0
    tax_amount: float = 0.0
    grand_total: float = 0.0
    notes: str = ""

    def to_dict(self): return asdict(self)

    @classmethod
    def from_dict(cls, d: dict):
        obj = cls()
        for k, v in d.items():
            if hasattr(obj, k):
                setattr(obj, k, v)
        return obj
