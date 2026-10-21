"""Run the Soft Computing AAT EV bus charging optimization project."""
import argparse
import json
from pathlib import Path
from models import Bus, ChargingProblem
from optimizer import optimize, evaluate, baseline_schedule, build_fuzzy_scores
from reporting import write_outputs


def load_problem(path: str) -> ChargingProblem:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    buses = [Bus(
        bus_id=item["bus_id"],
        required_kwh=float(item["required_kwh"]),
        charger_kw=float(item["charger_kw"]),
        departure_slot=int(item["departure_slot"]),
        initial_kwh=float(item.get("initial_kwh", 0.0)),
    ) for item in data["buses"]]
    problem = ChargingProblem(
        buses=buses,
        prices=[float(x) for x in data["prices_per_kwh"]],
        transformer_limit_kw=float(data["transformer_limit_kw"]),
        available_chargers=int(data["available_chargers"]),
        slot_minutes=int(data["slot_minutes"]),
        start_label=data.get("start_label", "22:00"),
    )
    if not problem.buses:
        raise ValueError("Input must contain at least one bus.")
    if not problem.prices:
        raise ValueError("Input must contain at least one time slot.")
    if problem.slot_minutes <= 0 or problem.transformer_limit_kw <= 0 or problem.available_chargers <= 0:
        raise ValueError("Slot length, transformer limit, and charger count must be positive.")
    if any(b.charger_kw <= 0 or b.required_kwh < 0 or b.initial_kwh < 0 for b in problem.buses):
        raise ValueError("Bus power must be positive and energy values cannot be negative.")
    if any(b.departure_slot < 0 or b.departure_slot > problem.slots for b in problem.buses):
        raise ValueError("Each departure_slot must be between 0 and number of slots.")
    return problem


def main():
    parser = argparse.ArgumentParser(description="Fuzzy + Genetic Algorithm EV bus charging optimizer")
    parser.add_argument("--data", default="data/buses.json", help="Input JSON file")
    parser.add_argument("--output", default="output", help="Output directory")
    parser.add_argument("--population", type=int, default=100)
    parser.add_argument("--generations", type=int, default=250)
    parser.add_argument("--mutation", type=float, default=0.18)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    problem = load_problem(args.data)
    if args.population < 4 or args.generations < 1 or not 0 <= args.mutation <= 1:
        raise ValueError("Population must be >= 4, generations >= 1, and mutation must be in [0, 1].")

    best, metrics, history = optimize(problem, args.population, args.generations, args.mutation, args.seed)
    fuzzy_scores = build_fuzzy_scores(problem)
    baseline = baseline_schedule(problem)
    _, baseline_metrics = evaluate(baseline, problem, fuzzy_scores)
    write_outputs(problem, best, metrics, baseline_metrics, history, fuzzy_scores, args.output)

    print("\\n=== EV BUS OVERNIGHT CHARGING OPTIMIZER ===")
    print(f"Slots: {problem.slots} | Slot duration: {problem.slot_minutes} minutes")
    print(f"Transformer limit: {problem.transformer_limit_kw:.1f} kW | Chargers: {problem.available_chargers}")
    print(f"Optimized energy cost: {metrics['energy_cost']:.2f}")
    print(f"Baseline energy cost:   {baseline_metrics['energy_cost']:.2f}")
    print(f"Cost savings:           {baseline_metrics['energy_cost'] - metrics['energy_cost']:.2f}")
    print(f"Feasible schedule:      {metrics['feasible']}")
    print(f"Unmet energy:           {metrics['unmet_energy_kwh']:.2f} kWh")
    print("\\nBus readiness:")
    for item in metrics["bus_results"]:
        status = "READY" if item["ready"] else "NOT READY"
        print(f"  {item['bus_id']}: {item['scheduled_kwh']:.1f}/{item['required_kwh']:.1f} kWh - {status}")
    print(f"\\nFiles written to: {Path(args.output).resolve()}")
    print("  schedule.csv")
    print("  summary.json")


if __name__ == "__main__":
    main()
