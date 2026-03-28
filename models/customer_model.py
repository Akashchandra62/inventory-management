# models/customer_model.py
from dataclasses import dataclass, asdict


@dataclass
class CustomerModel:
    customer_id: str = ""
    customer_name: str = ""
    mobile: str = ""
    address: str = ""
    email: str = ""
    notes: str = ""

    def to_dict(self): return asdict(self)

    @classmethod
    def from_dict(cls, d: dict):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
