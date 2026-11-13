# 霁川观测 · 双探头读数校准

对同一对象的两侧探头读数，计算给定误差方差比的Deming回归、Bland–Altman偏倚与一致性界限，并保留量程、异常配对和人工复核依据。全部使用模拟数据。

## 工作场景

霁川观测技术组12人原来用 `jichuan_probe_pairs_202611.csv` 在Excel只比较差值均值。三个痛点是两侧均有测量误差、偏差随量级变化、异常配对被总体均值掩盖。上游为同一对象同时采集的配对读数与独立重复测量误差依据；本项目替代校准关系、差值图和复核底稿计算；下游由计量负责人对照现场校准标准讨论。

六个业务实体贯穿数据库、Python Model/Schema/Service/Controller/Route、前端API/Store/页面：PairedDataset、InstrumentPair、CalibrationStudy、CalibrationRun、BiasReview、Report。页面为总览、配对观测、探头组合、研究设定、运行底稿、复核归档，另有管理员审计。

## 启动与技术

```sh
cp .env.example .env
docker compose up -d --build --wait
docker compose exec -T backend python -m scripts.seed_demo
```

前端 http://localhost:18221 ，API文档 http://localhost:19221/docs ，MySQL宿主17721。Nginx把 `/api/` 去前缀转发Python，开发代理一致；`/health`实际检查数据库及Redis。

| 层 | 版本与实现 |
|---|---|
| 前端 | Vue3.5.13、TypeScript5.7.2、Vite6.0.5、vue-tsc2.2.0 |
| 锁定安装 | 复用已验Vue依赖锁，仅修改工程名；npm ci，构建含vue-tsc |
| 后端 | Python3.12、FastAPI0.115.6、SQLAlchemy2.0.36 |
| 存储 | MySQL8.4 LTS、Redis7.4；误差比和容差列明确DOUBLE |
| 后台 | Redis列表队列、独立Python worker，运行状态与结果写MySQL |
| 网关 | Nginx1.28、SPA回落；健康检查显式127.0.0.1 |

恰好frontend/backend/worker/db/redis五服务，均有healthcheck与healthy依赖；数据库、Redis和共享心跳产物具名卷。演示清理 `docker compose down -v --remove-orphans`，保留数据时省略 `-v`。

目录：`backend/src/{models,schemas,services,controllers,routes}`按六实体分层；`services/paired_data.py`校验CSV，`units.py`声明单位维度、换算与λ调整，`deming.py`与`agreement.py`计算；`config,utils,middlewares`包含数据库、JWT/口令摘要、队列、审计、错误。种子在 `backend/scripts/seed_demo.py`，`migrations/001_schema.sql`说明新库基线，实际启动用元数据建表。前端 `src/{api,stores,types,constants,hooks,utils,router,pages}`，共享AgreementPlot、CalibrationMetrics与ConversionBasis用于总览/结果/报告，PairTable用于观测/结果。

测试、截图和日志在批次外层 `test-artifacts/gb-2302`，不进入本源码目录。

本地开发：安装backend/requirements.txt，配置可用DATABASE_URL与REDIS_URL，从backend启动 `uvicorn src.main:app --reload`，另起 `python -m src.worker`。前端 `npm ci && npm run dev`，构建 `npm run build`。页面用轻量hash路由，无额外路由依赖。

环境变量COMPOSE_PROJECT_NAME、FRONTEND_PORT、BACKEND_PORT、DB_PORT、JWT_SECRET、SEED_DEMO；Compose内部提供DATABASE_URL/REDIS_URL。`.env`忽略，示例密码与密钥用于本地模拟，部署使用独立配置。

## 角色与账号

统一密码 `ProbeDemo2026!`，带独立salt的PBKDF2-SHA256口令摘要，JWT八小时有效。

| 账号 / 角色 | 页面与动作 | 后端权限 |
|---|---|---|
| admin@probe.demo / admin | 偏倚复核、归档、审计 | 全部分析写入与批准归档 |
| analyst@probe.demo / analyst | 配对导入、组合/研究、异步计算、提审 | 不能批准或归档 |
| viewer@probe.demo / viewer | 阅读原始配对、结果、下载批准CSV | 所有写入403 |

未登录401；错角色403；失败运行不能提审409；未批准复核不能归档409。同一批准复核重复生成报告返回同一快照，不覆盖原结果。审计记录账号/路径/状态码，不记录密码、Token或上传正文。

共享枚举：Role/RunStatus/RangeBand和UNITS在 `backend/src/constants/enums.py`；前端roles/runStatuses/rangeBands/units在 `frontend/src/constants/enums.ts`，Role类型在types/domain.ts。

## 输入与统计口径

CSV列 `pair_id,range_label,x,y`，量程为low/middle/high，每批最多5000组；配对ID必填、唯一，x/y必须有限且绝对值≤1e9，缺失值、NaN/Infinity和未知量程拒绝。最少4组才能计算。**两侧单位在配对观测页分别声明**（`x_unit`/`y_unit`），只接受kPa/bar/degC/mg/L。原始读数按各自单位原样保存；分析统一换算到探头组合（instrument）的分析单位：压力 `1 bar = 100 kPa`，温度degC与浓度mg/L各自只有一种支持单位。**压力、温度、浓度属于不同物理量，不得混配**（例如X侧kPa、Y侧degC在批次、研究或运行任一层都明确拒绝）。旧CSV若带 `x_unit`/`y_unit` 列，只有当其值与页面声明一致时才接受，单位仍以页面声明为准。用户仍需保证真实采集对象、时刻和测量条件一致。

**误差方差比按原单位输入**。λ定义在原始读数单位下，换算到分析单位时按线性比例调整：`λ_分析 = λ_输入 × (y_factor/x_factor)²`，其中factor是原单位→分析单位的乘数（例如kPa/bar批次、Y侧bar→kPa factor=100，则λ缩小为原来的1/10⁴）。运行结果同时保存 `variance_ratio_input` 与 `variance_ratio_analysis`，两者都进入底稿、图表、快照和CSV。**讨论容差按分析单位解释**：输入±t作用于换算后的差值，不随原单位另行换算。

Deming模型为 `y=intercept+slope*x`，**λ=var(y测量误差)/var(x测量误差)**，由外部重复测量或计量依据输入，不从本批读数方差自动估计。设Sxx/Syy/Sxy为样本中心二阶矩，Δ=Syy−λSxx，斜率为：

`(Δ + sqrt(Δ² + 4λSxy²)) / (2Sxy)`

实现先按方差尺度归一化，并在Δ<0时采用等价稳定根 `2λSxy/(sqrt(Δ²+4λSxy²)−Δ)` 避免相消，截距为mean(y)−slope×mean(x)。任一侧常量、少于4组、零/近零协方差、负/零/非有限λ明确失败。API中λ须正且≤1e6；容差须正且≤1e6。正λ不是设备误差模型成立的证明。假设包括给定误差方差比、两侧随机误差口径稳定及对应关系适用；异方差或相关误差需要另设模型。不同单位的等价样本（换算后读数一致、λ已按比例调整）应得到相同的斜率、截距、偏倚、SD、界限和逐点越界标记；seed中的kPa/kPa与kPa/bar两批即用于此对照。

Bland–Altman差值固定为 **d=y−x**，横轴m=(x+y)/2，偏倚=mean(d)，样本SD按ddof=1，界限为mean(d)±1.96×sample_sd。它描述在差值近似正态、观测独立且方差口径适用时的近似覆盖范围，**不是置信区间**，也不证明设备可互换。差值常量时SD=0、上下界相同是实际计算结果，不伪造不确定性。

比例偏倚另用OLS拟合 `d=alpha+beta*m`，报告系数与描述性R²，不输出未经检验的p值或因果判断。均值读数m常量时返回不可估计/null及原因；差值常量时R²不可定义返回null。讨论容差±t只是使用者输入的领域阈值，不改变BA界限，也不自动给出合格/互换结论。

结果保存原始读数（`x_raw`/`y_raw`及其原单位）、换算后的分析读数（`x_analysis`/`y_analysis`）、换算依据、λ的输入值与分析值、拟合值、y方向残差、均值、差值、界限外和讨论容差外标记；图表横轴/纵轴与单位标注均使用分析单位。y方向残差RMSE只作残差摘要，不称为Deming的唯一优化目标。旧运行结果若缺少换算字段，页面与CSV按当时保存的原值读取并标注“未记录换算依据”；已归档报告保持原值，不重新计算、不回写。

## 模拟工作日

Seed为固定20261112的240组、三量程、两探头JQ-P17/JQ-P18，单位kPa。模拟X误差SD0.2、Y误差SD0.3，故假设λ=2.25；包含4个刻意偏差点，默认讨论容差±2kPa。另有一批同一物理读数、Y侧以bar记录的混合单位样本：λ在原单位下为0.000225，换算后等于2.25，统计量与逐点越界标记应与kPa/kPa批次一致。

1. 09:00 导入 `jichuan_probe_pairs_202611.csv`，核对240组、唯一ID与量程，分别声明X侧kPa、Y侧单位。
2. 09:04 核对两探头序列号、X/Y方向及组合分析单位kPa。
3. 09:08 查阅独立重复测量依据，按原单位填写λ（kPa/kPa为2.25，kPa/bar为0.000225），不将读数方差比误当误差比。
4. 09:12 保存讨论容差±2kPa（按分析单位），送入Redis后台；核对换算依据与换算后λ。
5. 09:18 同时查看Deming校准线、y=x参考和BA差值图，两图均按分析单位。
6. 09:23 检查高量程比例偏倚及界限外配对，记录现场核查建议。
7. 09:30 分析师提交偏倚复核，管理员核准结论与限制。
8. 09:35 viewer下载批准快照CSV（含原单位原始读数、分析读数与换算依据）；已归档快照保持原值，不向真实设备写参数。

种子自然键幂等，重复运行不覆盖用户修改的批次说明。

## 已知差异

- 采用MySQL8.4 LTS而非8.0；同属MySQL8家族。
- Redis列表无worker崩溃租约及自动重投、无取消；新库自动建表没有存量库版本化迁移/回滚。列表最多200条实体。
- 不处理真实设备通信、加权/异方差Deming或重复个体的层次模型；无校准参数CI。比例偏倚仅描述，不自动断言显著性。
- 单位换算只覆盖线性压力单位kPa/bar；温度仅degC、浓度仅mg/L，不做温标转换或浓度稀释换算。不同物理量组合明确拒绝而非尝试换算。旧运行结果没有换算字段时按原值读取，不回溯重算。
- 模拟数据不能用于真实设备合格判定；Google Fonts需联网，断网回退字体。

MIT License。真实验收见批次 `test-artifacts/gb-2302/TESTING.md`。
