from uuid import uuid4
from sqlalchemy import select
from fastapi import HTTPException
from ..models.study import CalibrationStudy
from ..models.dataset import PairedDataset
from ..models.instrument import InstrumentPair
from .units import ensure_compatible

def create(db,body):
 dataset=db.get(PairedDataset,body.dataset_id);pair=db.get(InstrumentPair,body.instrument_id)
 if not dataset or not pair:raise HTTPException(422,"配对批次或探头组合不存在")
 try:
  ensure_compatible(dataset.x_unit,dataset.y_unit,pair.unit)
 except ValueError as error:raise HTTPException(422,str(error))
 if db.scalar(select(CalibrationStudy).where(CalibrationStudy.name==body.name)):raise HTTPException(409,"校准研究名称已存在")
 row=CalibrationStudy(id=str(uuid4()),**body.model_dump());db.add(row);db.commit();return row
