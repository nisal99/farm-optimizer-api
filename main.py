"""
Farm Optimizer API
Solves crop planning LP based on the Group 5 Excel model logic.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import pulp
import json

app = FastAPI(title="Farm Optimizer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CropParams(BaseModel):
    name: str
    enabled: bool = True
    demand_wholesale: float
    demand_d2c: float
    demand_b2b: float
    yield_per_acre: float
    crop_size_m3_per_lb: float
    months_planting: int = 1
    months_growing: int = 1
    months_harvesting: int = 1
    labor_planting: float
    labor_growing: float
    labor_harvesting: float
    water_planting: float
    water_growing: float
    water_harvesting: float
    price_wholesale: float
    price_d2c: float
    price_b2b: float
    seed_required: float
    seed_cost: float
    fertilizer_planting: float
    fertilizer_growing: float
    fertilizer_harvesting: float
    packaging_wholesale: float
    packaging_d2c: float
    packaging_b2b: float
    fuel_planting: float
    fuel_growing: float
    fuel_harvesting: float
    max_land_fraction: float = 0.8
    planting_months: list[int]
    max_successions: int = 1

class FarmParams(BaseModel):
    total_acres: float = 175
    total_budget: float = 3_500_000
    harvest_storage_m3: float = 30_000
    water_storage_l: float = 180_000
    equipment_storage_m3: float = 24_000
    fuel_storage_l: float = 1_500
    harvest_storage_cost: float = 2
    water_storage_cost: float = 0.002
    water_supply_cost: float = 0.002
    irrigation_cost: float = 175
    equipment_storage_cost: float = 2
    fuel_storage_cost: float = 0.01
    machinery_cost: float = 2_600
    fertilizer_cost: float = 2
    labor_cost: float = 20
    fuel_cost: float = 1
    monthly_water_supply: list[float] = [
        90000, 90000, 157500, 180000, 225000, 225000,
        225000, 225000, 202500, 157500, 112500, 90000
    ]
    monthly_labor_available: list[float] = [
        1280, 1280, 1280, 3840, 3840, 3840,
        7680, 7680, 7680, 7680, 3840, 1280
    ]
    crops: list[CropParams]

class ScenarioRequest(BaseModel):
    name: str = "My Farm Plan"
    farm: FarmParams

DEFAULT_CROPS = [
    {
        "name": "Spinach",
        "enabled": True,
        "demand_wholesale": 45000, "demand_d2c": 14062.5, "demand_b2b": 21093.75,
        "yield_per_acre": 13000,
        "crop_size_m3_per_lb": 0.075,
        "months_planting": 1, "months_growing": 1, "months_harvesting": 1,
        "labor_planting": 15, "labor_growing": 12, "labor_harvesting": 100,
        "water_planting": 1250, "water_growing": 1000, "water_harvesting": 1125,
        "price_wholesale": 2.5, "price_d2c": 5.0, "price_b2b": 3.5,
        "seed_required": 10, "seed_cost": 20,
        "fertilizer_planting": 15, "fertilizer_growing": 10, "fertilizer_harvesting": 5,
        "packaging_wholesale": 0.04, "packaging_d2c": 0.125, "packaging_b2b": 0.075,
        "fuel_planting": 8, "fuel_growing": 3, "fuel_harvesting": 6,
        "max_land_fraction": 0.8,
        "planting_months": [2, 3, 4, 8, 9],
        "max_successions": 5,
    },
    {
        "name": "Cucumbers",
        "enabled": True,
        "demand_wholesale": 42187.5, "demand_d2c": 16875, "demand_b2b": 22500,
        "yield_per_acre": 16000,
        "crop_size_m3_per_lb": 0.015,
        "months_planting": 1, "months_growing": 1, "months_harvesting": 1,
        "labor_planting": 15, "labor_growing": 12, "labor_harvesting": 130,
        "water_planting": 1750, "water_growing": 250, "water_harvesting": 750,
        "price_wholesale": 0.6, "price_d2c": 1.5, "price_b2b": 1.0,
        "seed_required": 2.5, "seed_cost": 45,
        "fertilizer_planting": 12, "fertilizer_growing": 8, "fertilizer_harvesting": 5,
        "packaging_wholesale": 0.025, "packaging_d2c": 0.075, "packaging_b2b": 0.05,
        "fuel_planting": 8, "fuel_growing": 2, "fuel_harvesting": 5,
        "max_land_fraction": 0.5,
        "planting_months": [5, 6, 7],
        "max_successions": 3,
    },
    {
        "name": "Sweet Corn",
        "enabled": True,
        "demand_wholesale": 28125, "demand_d2c": 28125, "demand_b2b": 19687.5,
        "yield_per_acre": 10000,
        "crop_size_m3_per_lb": 0.015,
        "months_planting": 1, "months_growing": 2, "months_harvesting": 1,
        "labor_planting": 10, "labor_growing": 6, "labor_harvesting": 200,
        "water_planting": 1000, "water_growing": 750, "water_harvesting": 875,
        "price_wholesale": 1.75, "price_d2c": 2.75, "price_b2b": 2.0,
        "seed_required": 12, "seed_cost": 5,
        "fertilizer_planting": 20, "fertilizer_growing": 15, "fertilizer_harvesting": 8,
        "packaging_wholesale": 0.02, "packaging_d2c": 0.06, "packaging_b2b": 0.04,
        "fuel_planting": 10, "fuel_growing": 4, "fuel_harvesting": 8,
        "max_land_fraction": 0.8,
        "planting_months": [5, 6],
        "max_successions": 2,
    },
    {
        "name": "Napa Cabbage",
        "enabled": True,
        "demand_wholesale": 67500, "demand_d2c": 28125, "demand_b2b": 35156.25,
        "yield_per_acre": 45000,
        "crop_size_m3_per_lb": 0.02,
        "months_planting": 1, "months_growing": 2, "months_harvesting": 1,
        "labor_planting": 10, "labor_growing": 6, "labor_harvesting": 80,
        "water_planting": 2000, "water_growing": 1000, "water_harvesting": 1250,
        "price_wholesale": 0.5, "price_d2c": 1.75, "price_b2b": 1.0,
        "seed_required": 0.75, "seed_cost": 60,
        "fertilizer_planting": 15, "fertilizer_growing": 10, "fertilizer_harvesting": 5,
        "packaging_wholesale": 0.03, "packaging_d2c": 0.1, "packaging_b2b": 0.06,
        "fuel_planting": 8, "fuel_growing": 3, "fuel_harvesting": 5,
        "max_land_fraction": 0.5,
        "planting_months": [3, 8],
        "max_successions": 2,
    },
    {
        "name": "Hot Peppers",
        "enabled": True,
        "demand_wholesale": 36562.5, "demand_d2c": 7031.25, "demand_b2b": 14062.5,
        "yield_per_acre": 5000,
        "crop_size_m3_per_lb": 0.035,
        "months_planting": 1, "months_growing": 3, "months_harvesting": 3,
        "labor_planting": 20, "labor_growing": 15, "labor_harvesting": 80,
        "water_planting": 2000, "water_growing": 1250, "water_harvesting": 625,
        "price_wholesale": 3.0, "price_d2c": 8.0, "price_b2b": 5.0,
        "seed_required": 0.35, "seed_cost": 120,
        "fertilizer_planting": 10, "fertilizer_growing": 12, "fertilizer_harvesting": 6,
        "packaging_wholesale": 0.04, "packaging_d2c": 0.125, "packaging_b2b": 0.075,
        "fuel_planting": 7, "fuel_growing": 3, "fuel_harvesting": 4,
        "max_land_fraction": 0.5,
        "planting_months": [4],
        "max_successions": 1,
    },
    {
        "name": "Garlic",
        "enabled": True,
        "demand_wholesale": 84375, "demand_d2c": 8437.5, "demand_b2b": 10125,
        "yield_per_acre": 11000,
        "crop_size_m3_per_lb": 0.025,
        "months_planting": 1, "months_growing": 5, "months_harvesting": 1,
        "labor_planting": 20, "labor_growing": 8, "labor_harvesting": 75,
        "water_planting": 1500, "water_growing": 500, "water_harvesting": 1000,
        "price_wholesale": 2.0, "price_d2c": 4.5, "price_b2b": 3.0,
        "seed_required": 1000, "seed_cost": 5,
        "fertilizer_planting": 8, "fertilizer_growing": 5, "fertilizer_harvesting": 3,
        "packaging_wholesale": 0.03, "packaging_d2c": 0.1, "packaging_b2b": 0.06,
        "fuel_planting": 10, "fuel_growing": 2, "fuel_harvesting": 5,
        "max_land_fraction": 0.8,
        "planting_months": [1],
        "max_successions": 1,
    },
]

def solve_farm(farm: FarmParams):
    MONTHS = list(range(1, 13))
    MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    A = farm.total_acres
    crops = [c for c in farm.crops if c.enabled]
    if not crops:
        raise HTTPException(400, "No crops enabled")

    prob = pulp.LpProblem("FarmOptimizer", pulp.LpMaximize)

    x = {}
    b = {}
    successions = {}

    for ci, crop in enumerate(crops):
        successions[ci] = []
        si = 0
        for pm in crop.planting_months:
            if si >= crop.max_successions:
                break
            total_months = crop.months_planting + crop.months_growing + crop.months_harvesting
            active = []
            for i in range(total_months):
                m = ((pm - 1 + i) % 12) + 1
                active.append(m)
            successions[ci].append((pm, active))
            x[ci, si] = pulp.LpVariable(f"x_{ci}_{si}", lowBound=0, upBound=1)
            b[ci, si] = pulp.LpVariable(f"b_{ci}_{si}", cat="Binary")
            si += 1

    def get_phase(ci, si, month):
        crop = crops[ci]
        pm, active = successions[ci][si]
        if month not in active:
            return None
        idx = active.index(month)
        if idx < crop.months_planting:
            return "planting"
        elif idx < crop.months_planting + crop.months_growing:
            return "growing"
        else:
            return "harvesting"

    def weighted_avg_price(crop):
        total_d = crop.demand_wholesale + crop.demand_d2c + crop.demand_b2b
        if total_d == 0:
            return 0
        return (crop.price_wholesale * crop.demand_wholesale +
                crop.price_d2c * crop.demand_d2c +
                crop.price_b2b * crop.demand_b2b) / total_d

    def weighted_avg_packaging(crop):
        total_d = crop.demand_wholesale + crop.demand_d2c + crop.demand_b2b
        if total_d == 0:
            return 0
        return (crop.packaging_wholesale * crop.demand_wholesale +
                crop.packaging_d2c * crop.demand_d2c +
                crop.packaging_b2b * crop.demand_b2b) / total_d

    revenue_expr = []
    var_cost_expr = []

    for ci, crop in enumerate(crops):
        wavg_price = weighted_avg_price(crop)
        wavg_pkg = weighted_avg_packaging(crop)
        for si in range(len(successions[ci])):
            pm, active = successions[ci][si]
            harvest_months = [m for m in active if get_phase(ci, si, m) == "harvesting"]
            for m in harvest_months:
                rev = crop.yield_per_acre * A * wavg_price
                revenue_expr.append(rev * x[ci, si])
            for m in active:
                phase = get_phase(ci, si, m)
                if phase == "planting":
                    vc = (crop.seed_required * crop.seed_cost +
                          crop.fertilizer_planting * farm.fertilizer_cost +
                          crop.fuel_planting * farm.fuel_cost) * A
                elif phase == "growing":
                    vc = (crop.fertilizer_growing * farm.fertilizer_cost +
                          crop.fuel_growing * farm.fuel_cost) * A
                else:
                    vc = (crop.fertilizer_harvesting * farm.fertilizer_cost +
                          crop.fuel_harvesting * farm.fuel_cost) * A + \
                         wavg_pkg * crop.yield_per_acre * A
                var_cost_expr.append(vc * x[ci, si])

    for ci, crop in enumerate(crops):
        for si in range(len(successions[ci])):
            pm, active = successions[ci][si]
            for m in active:
                phase = get_phase(ci, si, m)
                if phase == "planting":
                    lc = crop.labor_planting
                elif phase == "growing":
                    lc = crop.labor_growing
                else:
                    lc = crop.labor_harvesting
                var_cost_expr.append(lc * farm.labor_cost * A * x[ci, si])

    fixed_cost = (farm.machinery_cost * 12 +
                  farm.irrigation_cost * A * 12 +
                  farm.harvest_storage_cost * farm.harvest_storage_m3 * 12 +
                  farm.water_storage_cost * farm.water_storage_l * 12 +
                  farm.equipment_storage_cost * farm.equipment_storage_m3 * 12 +
                  farm.fuel_storage_cost * farm.fuel_storage_l * 12)

    total_revenue = pulp.lpSum(revenue_expr)
    total_var_cost = pulp.lpSum(var_cost_expr)
    prob += total_revenue - total_var_cost - fixed_cost, "Total_Profit"

    for m in MONTHS:
        land_use = []
        for ci, crop in enumerate(crops):
            for si in range(len(successions[ci])):
                pm, active = successions[ci][si]
                if m in active:
                    land_use.append(x[ci, si])
        if land_use:
            prob += pulp.lpSum(land_use) <= 1, f"Land_Month_{m}"

    for ci in range(len(crops)):
        for si in range(len(successions[ci])):
            prob += x[ci, si] <= b[ci, si], f"Binary_link_{ci}_{si}"

    for ci, crop in enumerate(crops):
        total_plant = pulp.lpSum(b[ci, si] for si in range(len(successions[ci])))
        max_s = max(1, int(crop.max_land_fraction * len(crops)))
        prob += total_plant <= max_s, f"Diversity_{ci}"

    for m_idx, m in enumerate(MONTHS):
        labor_use = []
        for ci, crop in enumerate(crops):
            for si in range(len(successions[ci])):
                pm, active = successions[ci][si]
                if m in active:
                    phase = get_phase(ci, si, m)
                    if phase == "planting":
                        lc = crop.labor_planting
                    elif phase == "growing":
                        lc = crop.labor_growing
                    else:
                        lc = crop.labor_harvesting
                    labor_use.append(lc * A * x[ci, si])
        if labor_use:
            prob += pulp.lpSum(labor_use) <= farm.monthly_labor_available[m_idx], \
                   f"Labor_Month_{m}"

    for m_idx, m in enumerate(MONTHS):
        water_use = []
        for ci, crop in enumerate(crops):
            for si in range(len(successions[ci])):
                pm, active = successions[ci][si]
                if m in active:
                    phase = get_phase(ci, si, m)
                    if phase == "planting":
                        wc = crop.water_planting
                    elif phase == "growing":
                        wc = crop.water_growing
                    else:
                        wc = crop.water_harvesting
                    water_use.append(wc * A * x[ci, si])
        if water_use:
            max_water = min(farm.monthly_water_supply[m_idx], farm.water_storage_l)
            prob += pulp.lpSum(water_use) <= max_water, f"Water_Month_{m}"

    for m in MONTHS:
        storage_use = []
        for ci, crop in enumerate(crops):
            for si in range(len(successions[ci])):
                pm, active = successions[ci][si]
                if m in active and get_phase(ci, si, m) == "harvesting":
                    storage_use.append(crop.yield_per_acre * crop.crop_size_m3_per_lb * A * x[ci, si])
        if storage_use:
            prob += pulp.lpSum(storage_use) <= farm.harvest_storage_m3, \
                   f"HarvestStorage_Month_{m}"

    for ci, crop in enumerate(crops):
        total_demand = crop.demand_wholesale + crop.demand_d2c + crop.demand_b2b
        harvest_yield = []
        for si in range(len(successions[ci])):
            pm, active = successions[ci][si]
            h_months = [m for m in active if get_phase(ci, si, m) == "harvesting"]
            for _ in h_months:
                harvest_yield.append(crop.yield_per_acre * A * x[ci, si])
        if harvest_yield:
            prob += pulp.lpSum(harvest_yield) <= total_demand * 12, \
                   f"Demand_{ci}"

    prob += total_var_cost + fixed_cost <= farm.total_budget, "Budget"

    solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=30)
    prob.solve(solver)

    status = pulp.LpStatus[prob.status]
    if prob.status not in [1]:
        return {"status": status, "feasible": False, "message": f"Solver status: {status}"}

    total_profit = pulp.value(prob.objective)
    total_rev = sum(pulp.value(e) or 0 for e in revenue_expr)
    total_vc = sum(pulp.value(e) or 0 for e in var_cost_expr)

    crop_results = []
    for ci, crop in enumerate(crops):
        cr = {"name": crop.name, "successions": [], "annual_yield_lbs": 0,
              "annual_revenue": 0, "planted": False}
        wavg_price = weighted_avg_price(crop)
        for si in range(len(successions[ci])):
            xval = pulp.value(x[ci, si]) or 0
            bval = pulp.value(b[ci, si]) or 0
            pm, active = successions[ci][si]
            if xval > 0.001:
                cr["planted"] = True
                acres_used = xval * A
                harvest_months_s = [m for m in active if get_phase(ci, si, m) == "harvesting"]
                yield_lbs = crop.yield_per_acre * acres_used * len(harvest_months_s)
                rev = yield_lbs * wavg_price
                cr["annual_yield_lbs"] += yield_lbs
                cr["annual_revenue"] += rev
                cr["successions"].append({
                    "succession_num": si + 1,
                    "plant_month": pm,
                    "plant_month_name": MONTH_NAMES[pm - 1],
                    "active_months": active,
                    "acres_used": round(acres_used, 2),
                    "fraction_of_farm": round(xval, 4),
                    "yield_lbs": round(yield_lbs, 0),
                    "revenue": round(rev, 2),
                })
        cr["annual_yield_lbs"] = round(cr["annual_yield_lbs"], 0)
        cr["annual_revenue"] = round(cr["annual_revenue"], 2)
        crop_results.append(cr)

    monthly_land = {}
    for m in MONTHS:
        mname = MONTH_NAMES[m - 1]
        used = 0
        breakdown = {}
        for ci, crop in enumerate(crops):
            for si in range(len(successions[ci])):
                xval = pulp.value(x[ci, si]) or 0
                pm, active = successions[ci][si]
                if m in active and xval > 0.001:
                    used += xval
                    breakdown[crop.name] = breakdown.get(crop.name, 0) + round(xval * A, 2)
        monthly_land[mname] = {
            "total_acres_used": round(used * A, 2),
            "fraction_used": round(used, 4),
            "crop_breakdown": breakdown
        }

    monthly_revenue = {mn: 0 for mn in MONTH_NAMES}
    for ci, crop in enumerate(crops):
        wavg_price = weighted_avg_price(crop)
        for si in range(len(successions[ci])):
            xval = pulp.value(x[ci, si]) or 0
            if xval < 0.001:
                continue
            pm, active = successions[ci][si]
            for m in active:
                if get_phase(ci, si, m) == "harvesting":
                    rev = crop.yield_per_acre * xval * A * wavg_price
                    monthly_revenue[MONTH_NAMES[m - 1]] += round(rev, 2)

    return {
        "status": "Optimal",
        "feasible": True,
        "summary": {
            "total_profit": round(total_profit, 2),
            "total_revenue": round(total_rev, 2),
            "total_variable_cost": round(total_vc, 2),
            "total_fixed_cost": round(fixed_cost, 2),
            "total_cost": round(total_vc + fixed_cost, 2),
            "crops_planted": sum(1 for c in crop_results if c["planted"]),
            "total_acres": A,
        },
        "crops": crop_results,
        "monthly_land_use": monthly_land,
        "monthly_revenue": monthly_revenue,
    }

@app.get("/")
def root():
    return {"message": "Farm Optimizer API", "version": "1.0.0", "status": "running"}

@app.get("/defaults")
def get_defaults():
    return {
        "farm": {
            "total_acres": 175,
            "total_budget": 3500000,
            "harvest_storage_m3": 30000,
            "water_storage_l": 180000,
            "equipment_storage_m3": 24000,
            "fuel_storage_l": 1500,
            "harvest_storage_cost": 2,
            "water_storage_cost": 0.002,
            "water_supply_cost": 0.002,
            "irrigation_cost": 175,
            "equipment_storage_cost": 2,
            "fuel_storage_cost": 0.01,
            "machinery_cost": 2600,
            "fertilizer_cost": 2,
            "labor_cost": 20,
            "fuel_cost": 1,
            "monthly_water_supply": [90000,90000,157500,180000,225000,225000,225000,225000,202500,157500,112500,90000],
            "monthly_labor_available": [1280,1280,1280,3840,3840,3840,7680,7680,7680,7680,3840,1280],
        },
        "crops": DEFAULT_CROPS,
    }

@app.post("/optimize")
def optimize(req: ScenarioRequest):
    try:
        result = solve_farm(req.farm)
        result["scenario_name"] = req.name
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Solver error: {str(e)}")

@app.post("/optimize/quick")
def optimize_quick(acres: float = 175, budget: float = 3500000):
    from copy import deepcopy
    crops = [CropParams(**c) for c in DEFAULT_CROPS]
    farm = FarmParams(total_acres=acres, total_budget=budget, crops=crops)
    result = solve_farm(farm)
    result["scenario_name"] = f"{acres} acres / ${budget:,.0f} budget"
    return result
