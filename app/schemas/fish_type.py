from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

FishTypeName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]

class FishTypeCreate(BaseModel):
    name:FishTypeName

class FishTypeUpdate(BaseModel):
    name:FishTypeName

class FishTypeRead(BaseModel):
    id:int
    name:str
    is_active:bool

    model_config=ConfigDict(from_attributes=True)