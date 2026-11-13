from uuid import uuid4
from fastapi import HTTPException
from ..models.run import CalibrationRun
from ..models.study import CalibrationStudy
from ..models.dataset import PairedDataset
from ..models.instrument import InstrumentPair
from ..utils.queue import enqueue
from .paired_data import validate_pairs,validate_dataset_units,converted_readings
from .deming import regress
from .agreement import analyze
from .units import build_conversion

def create(db,body):
 if not db.get(CalibrationStudy,body.study_id):raise HTTPException(422,"校准研究不存在")
 row=CalibrationRun(id=str(uuid4()),study_id=body.study_id,status="queued",result={},error="");db.add(row);db.commit()
 try:enqueue(row.id)
 except Exception:
  row.status="failed";row.error="Redis队列不可用，请稍后重试";db.commit();raise HTTPException(503,row.error)
 return row

def compute(db,run_id):
 row=db.get(CalibrationRun,run_id)
 if row is None or row.status not in ["queued","running"]:return
 row.status="running";db.commit()
 try:
  study=db.get(CalibrationStudy,row.study_id);dataset=db.get(PairedDataset,study.dataset_id);pair=db.get(InstrumentPair,study.instrument_id)
  if dataset is None or pair is None:raise ValueError("校准研究对应的批次或探头组合不存在")
  validate_dataset_units(dataset.x_unit,dataset.y_unit)
  # Analysis unit is the probe combination's unit; raw readings keep their own units.
  conversion=build_conversion(dataset.x_unit,dataset.y_unit,pair.unit,study.variance_ratio)
  x_raw,y_raw=validate_pairs(dataset.pairs)
  x_an,y_an=converted_readings(dataset.pairs,conversion["x"]["factor"],conversion["y"]["factor"])
  deming=regress(x_an,y_an,conversion["variance_ratio_analysis"]);ba=analyze(x_an,y_an)
  points=[]
  for p,xa,ya in zip(dataset.pairs,x_an,y_an):
   fitted=deming["intercept"]+deming["slope"]*xa;difference=ya-xa
   points.append({"pair_id":p["pair_id"],"range_label":p["range_label"],"x":p["x"],"y":p["y"],"x_raw":p["x"],"y_raw":p["y"],"x_analysis":xa,"y_analysis":ya,"fitted_y":fitted,"residual_y":ya-fitted,"mean":(xa+ya)/2,"difference":difference,"outside_loa":difference<ba["loa_low"] or difference>ba["loa_high"],"outside_tolerance":abs(difference)>study.tolerance})
  row.result={"dataset_name":dataset.name,"instrument_name":pair.name,"x_serial":pair.x_serial,"y_serial":pair.y_serial,"unit":conversion["analysis_unit"],"x_unit":dataset.x_unit,"y_unit":dataset.y_unit,"analysis_unit":conversion["analysis_unit"],"tolerance_unit":conversion["analysis_unit"],"conversion":conversion,"variance_ratio_input":conversion["variance_ratio_input"],"variance_ratio_analysis":conversion["variance_ratio_analysis"],"n":len(points),"deming":deming,"agreement":ba,"points":points,"tolerance":study.tolerance,"outside_tolerance":sum(p["outside_tolerance"] for p in points)};row.status="completed"
 except Exception as e:row.status="failed";row.error=str(e)[:1000]
 db.commit()
