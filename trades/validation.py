from typing import Optional
from pydantic import BaseModel



class CreateMark(BaseModel):
    symbol: str
    expires: Optional[str] = ''