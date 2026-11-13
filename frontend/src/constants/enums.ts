export const roles=["admin","analyst","viewer"] as const;export const runStatuses=["queued","running","completed","failed"] as const;export const rangeBands=["low","middle","high"] as const;export const rangeLabels:Record<string,string>={low:"低量程",middle:"中量程",high:"高量程"};export const units=["kPa","bar","degC","mg/L"] as const;
export const unitGroups:Record<string,string[]>={pressure:["kPa","bar"],temperature:["degC"],concentration:["mg/L"]};
export const unitDimension:Record<string,string>={kPa:"pressure",bar:"pressure",degC:"temperature","mg/L":"concentration"};
export const dimensionLabels:Record<string,string>={pressure:"压力",temperature:"温度",concentration:"浓度"};
export const unitFactors:Record<string,number>={kPa:1,bar:100,degC:1,"mg/L":1};
export const analysisUnits:Record<string,string>={pressure:"kPa",temperature:"degC",concentration:"mg/L"};
export const unitNote="压力 kPa/bar 可换算；温度 degC 与浓度 mg/L 各自单独使用，压力、温度、浓度不得混配。";
export function dimensionOf(unit:string|undefined){return unit?unitDimension[unit]||"":""}
export function compatibleUnits(first:string|undefined,second:string|undefined){return !!first&&!!second&&!!dimensionOf(first)&&dimensionOf(first)===dimensionOf(second)}
export function conversionFactor(from:string|undefined,to:string|undefined){if(!compatibleUnits(from,to))return 1;return (unitFactors[from as string]||1)/(unitFactors[to as string]||1)}
export function unitError(first:string,second:string){const a=dimensionLabels[dimensionOf(first)]||first,b=dimensionLabels[dimensionOf(second)]||second;return `单位不能混配：${first}（${a}）与 ${second}（${b}）属于不同物理量；${a}与${b}不得混配，压力与温度严禁混用。`}
