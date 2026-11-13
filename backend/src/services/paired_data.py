import csv,io,math
from .units import ensure_compatible

def parse_csv(text,x_unit=None,y_unit=None):
 rows=list(csv.DictReader(io.StringIO(text)));required={"pair_id","range_label","x","y"}
 if not rows or len(rows)>5000 or not required.issubset(rows[0]):raise ValueError("CSV需1至5000行并包含pair_id,range_label,x,y")
 # Units are declared on the paired-observation page. Legacy CSVs may repeat them;
 # they are accepted only when they agree with the declaration, never used to override it.
 for column,declared in (("x_unit",x_unit),("y_unit",y_unit)):
  if column in rows[0]:
   stated=(rows[0].get(column) or "").strip()
   if declared is not None and stated.casefold()!=declared.casefold():raise ValueError(f"CSV列{column}={stated}与页面声明{declared}不一致；单位由配对观测页两侧分别声明")
 seen=set();result=[]
 for index,row in enumerate(rows,2):
  ident=(row.get("pair_id") or "").strip();band=(row.get("range_label") or "").strip()
  if not ident or len(ident)>80 or ident in seen:raise ValueError(f"第{index}行配对ID为空、过长或重复")
  if band not in ["low","middle","high"]:raise ValueError(f"第{index}行量程应为low/middle/high")
  seen.add(ident);values={}
  for key in ["x","y"]:
   try:value=float(row.get(key))
   except Exception:raise ValueError(f"第{index}行{key}需要有效数值")
   if not math.isfinite(value) or abs(value)>1e9:raise ValueError(f"第{index}行{key}必须有限且绝对值不超过1e9")
   values[key]=value
  result.append({"pair_id":ident,"range_label":band,**values})
 return result

def validate_pairs(pairs):
 if len(pairs)<4:raise ValueError("至少需要4组成对读数")
 x=[r["x"] for r in pairs];y=[r["y"] for r in pairs]
 if not all(math.isfinite(v) for v in x+y):raise ValueError("读数必须有限")
 return x,y

def validate_dataset_units(x_unit,y_unit):
 if x_unit is None or y_unit is None:raise ValueError("配对批次缺少两侧单位声明")
 return ensure_compatible(x_unit,y_unit)

def converted_readings(pairs,x_factor,y_factor):
 """Raw readings stay untouched; analysis uses the converted copies."""
 return ([p["x"]*x_factor for p in pairs],[p["y"]*y_factor for p in pairs])
