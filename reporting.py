"""CSV and JSON output helpers using only Python standard library."""
import csv
import json
from pathlib import Path
from typing import Any, Dict, List
from models import ChargingProblem
from optimizer import Genome, decode_genome


def write_outputs(problem: ChargingProblem, genome: Genome, metrics: Dict[str, Any],
                  baseline_metrics: Dict[str, Any], history: List[float],
                  fuzzy_scores: List[float], output_dir: str) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    matrix = decode_genome(genome, problem)
    with (out / "schedule.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["slot", "time", "price_per_kwh", "transformer_limit_kw",
                         "total_power_kw", "chargers_used", "fuzzy_attractiveness", "charging_buses"])
        for slot in range(problem.slots):
            bus_ids = [problem.buses[i].bus_id for i in range(len(problem.buses)) if matrix[i][slot]]
            minutes = (22 * 60 + slot * problem.slot_minutes) % (24 * 60)
            time_label = f"{minutes // 60:02d}:{minutes % 60:02d}"
            writer.writerow([slot, time_label, problem.prices[slot], problem.transformer_limit_kw,
                             metrics["slot_power_kw"][slot], metrics["slot_chargers_used"][slot],
                             round(fuzzy_scores[slot], 4), ";".join(bus_ids)])
    summary = {
        "problem": "Overnight EV bus charging schedule",
        "units": {"energy": "kWh", "power": "kW", "cost": "illustrative cost units"},
        "algorithm": {"name": "Genetic Algorithm + hand-coded fuzzy inference",
                      "population_size": 100, "generations": 250, "mutation_rate": 0.18, "seed": 7},
        "optimized": metrics,
        "baseline": baseline_metrics,
        "cost_savings_vs_baseline": round(baseline_metrics["energy_cost"] - metrics["energy_cost"], 3),
        "best_fitness_by_generation": [round(v, 4) for v in history],
        "fuzzy_slot_scores": [round(v, 4) for v in fuzzy_scores],
        "disclaimer": "Illustrative educational simulation; validate tariffs and constraints before real deployment."
    }
    with (out / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
