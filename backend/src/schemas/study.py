from pydantic import BaseModel,Field,model_validator
from ..constants.enums import UNITS
from ..services.units import ensure_compatible

class StudyCreate(BaseModel):
 name:str=Field(min_length=2,max_length=180)
 dataset_id:str
 instrument_id:str
 variance_ratio:float=Field(default=2.25,gt=0,le=1000000,allow_inf_nan=False)
 tolerance:float=Field(default=2,gt=0,le=1000000,allow_inf_nan=False)

class StudyUnits(BaseModel):
 x_unit:str
 y_unit:str
 analysis_unit:str
 @model_validator(mode="after")
 def compatibility(self):
  for unit in (self.x_unit,self.y_unit,self.analysis_unit):
   if unit not in UNITS:raise ValueError(f"单位不支持：{unit}；仅支持kPa/bar/degC/mg/L")
  ensure_compatible(self.x_unit,self.y_unit,self.analysis_unit)
  return self
