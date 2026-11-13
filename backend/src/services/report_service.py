import csv,io
from uuid import uuid4
from sqlalchemy import select
from fastapi import HTTPException
from ..models.review import BiasReview
from ..models.run import CalibrationRun
from ..models.report import Report

def create(db,body):
 review=db.get(BiasReview,body.review_id)
 if review is None or review.state!="approved":raise HTTPException(409,"报告必须关联已批准的偏倚复核")
 existing=db.scalar(select(Report).where(Report.review_id==body.review_id))
 if existing:return existing
 run=db.get(CalibrationRun,review.run_id);row=Report(id=str(uuid4()),review_id=review.id,title=body.title,snapshot={"result":run.result,"action":review.action,"reviewer":review.reviewer});db.add(row);db.commit();return row

def export(row):
 result=row.snapshot["result"];analysis_unit=result.get("unit")
 out=io.StringIO();writer=csv.writer(out)
 header=["pair_id","range_label","x_raw","y_raw","x_unit","y_unit","x_analysis","y_analysis","analysis_unit","mean","difference_y_minus_x","deming_fitted_y","residual_y","outside_loa","outside_tolerance"]
 writer.writerow(header)
 # Archived snapshots are immutable: old reports without conversion fields export stored values as-is.
 for p in result["points"]:
  x_raw=p.get("x_raw",p["x"]);y_raw=p.get("y_raw",p["y"])
  writer.writerow([p["pair_id"],p["range_label"],x_raw,y_raw,result.get("x_unit",analysis_unit),result.get("y_unit",analysis_unit),
                   p.get("x_analysis",p["x"]),p.get("y_analysis",p["y"]),analysis_unit,p["mean"],p["difference"],
                   p["fitted_y"],p["residual_y"],p["outside_loa"],p["outside_tolerance"]])
 basis=result.get("conversion")
 if basis:
  writer.writerow([])
  writer.writerow(["conversion_basis",basis["basis"]])
  writer.writerow(["variance_ratio_input",basis["variance_ratio_input"]])
  writer.writerow(["variance_ratio_analysis",basis["variance_ratio_analysis"]])
  writer.writerow(["variance_ratio_note",basis["variance_ratio_note"]])
  writer.writerow(["tolerance","±",result["tolerance"],analysis_unit,"(按分析单位解释)"])
 else:
  writer.writerow([])
  writer.writerow(["conversion_basis","归档快照创建时两侧同单位；未记录换算依据，原始值保持不变"])
  writer.writerow(["tolerance","±",result["tolerance"],analysis_unit])
 return "\ufeff"+out.getvalue()
