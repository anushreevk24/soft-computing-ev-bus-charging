# Soft Computing AAT — EV Bus Overnight Charging Optimizer

**Chosen problem:** Problem Statement 20 from the supplied Soft Computing AAT PDF: schedule overnight charging of an electric bus fleet under charger and transformer limits so every bus is ready for morning service at minimum energy cost.

**Suggested technique in the PDF:** Fuzzy Logic + Evolutionary Algorithm (Units 2 and 3), aligned with SDG 11 — Sustainable Cities and Communities.

## What this project does

- Builds an overnight charging schedule for a small example fleet.
- Uses a hand-written fuzzy inference system to estimate a relative cost/priority score for each time slot.
- Uses a genetic algorithm implemented from scratch to search for low-cost schedules.
- Checks charger availability, transformer capacity, bus energy requirements, and morning-readiness.
- Includes a deterministic baseline schedule for comparison.
- Prints metrics and writes a CSV schedule plus a JSON summary.
- Uses only Python's standard library. No NumPy, pandas, scikit-learn, DEAP, or other optimization libraries are used.

> This is an educational simulation, not a production charging controller. Input data and electricity prices are illustrative. Confirm constraints and price tariffs before real-world use.

## Requirements

- Python 3.10 or newer
- No third-party packages required

## Run

From this folder:

```bash
python main.py
```

Run tests:

```bash
python -m unittest discover -s tests -v
```

Use custom input data:

```bash
python main.py --data data/buses.json --output output
```

Generated files:
- `output/schedule.csv` — slot-by-slot charging plan
- `output/summary.json` — metrics, constraints, baseline comparison, and algorithm settings

## Project structure

```text
soft_computing_bus_charging/
├── main.py
├── optimizer.py
├── fuzzy.py
├── models.py
├── reporting.py
├── data/
│   └── buses.json
├── tests/
│   └── test_optimizer.py
├── docs/
│   └── problem_formulation.md
├── .gitignore
└── README.md
```

## Model and assumptions

- Time horizon: 22:00–06:00, divided into 30-minute slots (16 slots).
- Each bus can charge at most one slot's energy per slot; a bus is either off or charging at its configured power.
- Charging energy per slot = charger power (kW) × slot duration (hours).
- Slot energy cost = energy (kWh) × illustrative price (currency units/kWh).
- The transformer has a hard aggregate kW limit per slot.
- Each bus has a target energy requirement in kWh and a departure deadline.
- A feasible schedule must meet each bus's energy requirement by its deadline, respect the number of available chargers, and respect transformer capacity.
- The fuzzy controller converts price and remaining time-to-deadline into a relative slot attractiveness score. It is deliberately transparent and rule-based.
- The genetic algorithm encodes each bus's charging decisions as slot indices. It uses tournament selection, one-point crossover, mutation, and elitism. Infeasible schedules receive penalties.

## Important implementation note

The AAT PDF says to implement the chosen soft-computing technique **without library functions**. This project implements fuzzy membership functions, fuzzy rules, the genetic algorithm operators, fitness evaluation, schedule checks, and baseline logic directly in Python. Standard-library utilities are used for file I/O, CSV/JSON, argument parsing, and reproducible random numbers—not for the optimization technique itself.

## GitHub

Create a new repository, then from this folder run:

```bash
git init
git add .
git commit -m "Implement fuzzy and evolutionary EV bus charging optimizer"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```

Replace the remote URL with your own GitHub repository URL.
