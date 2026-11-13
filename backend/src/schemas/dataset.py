from pydantic import BaseModel,Field,model_validator
from ..constants.enums import UNITS
from ..services.units import ensure_compatible

class DatasetCreate(BaseModel):
 name:str=Field(min_length=2,max_length=180)
 x_unit:str
 y_unit:str
 csv_text:str=Field(min_length=20,max_length=2000000)
 description:str=Field(default="",max_length=2000)
 @model_validator(mode="after")
 def unit_check(self):
  for unit in (self.x_unit,self.y_unit):
   if unit not in UNITS:raise ValueError(f"单位不支持：{unit}；仅支持kPa/bar/degC/mg/L")
  ensure_compatible(self.x_unit,self.y_unit)
  return self

class DatasetEdit(BaseModel):
 description:str=Field(max_length=2000)
