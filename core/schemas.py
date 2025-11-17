from typing import Optional, List
from pydantic import BaseModel

class UserPreferences(BaseModel):
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    city: Optional[str] = None
    usage: Optional[str] = None  # city | highway | mixed
    daily_km: Optional[int] = None
    family_size: Optional[int] = None
    fuel_pref: Optional[List[str]] = None
    transmission: Optional[str] = None
    priorities: Optional[List[str]] = None
