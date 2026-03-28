# models/vendor_model.py
from dataclasses import dataclass, asdict


@dataclass
class VendorModel:
    vendor_id: str = ""
    vendor_name: str = ""
    phone: str = ""
    address: str = ""
    gst_number: str = ""
    email: str = ""
    notes: str = ""

    def to_dict(self): return asdict(self)

    @classmethod
    def from_dict(cls, d: dict):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
