
"""Genetic algorithm and baseline implemented from scratch."""

from __future__ import annotations

import random
from typing import List, Tuple, Dict, Any

from models import Bus, ChargingProblem
from fuzzy import slot_attractiveness


Genome = List[List[int]]  # One list of charging slots per bus


def energy_per_slot(bus: Bus, problem: ChargingProblem) -> float:
    """Calculate the maximum energy delivered in one time slot."""
    return bus.charger_kw * problem.slot_hours


def build_fuzzy_scores(problem: ChargingProblem) -> List[float]:
    """Calculate fuzzy attractiveness scores for every time slot."""
    low = min(problem.prices)
    high = max(problem.prices)
    scores = []

    for slot, price in enumerate(problem.prices):
        slots_left = max(1, problem.slots - slot)

        score = slot_attractiveness(
            price,
            slots_left,
            problem.slots,
            low,
            high
        )

        scores.append(score)

    return scores


def decode_genome(
    genome: Genome,
    problem: ChargingProblem
) -> List[List[int]]:
    """Convert a genome into a bus-by-slot binary matrix."""
    matrix = [
        [0 for _ in range(problem.slots)]
        for _ in problem.buses
    ]

    for b_idx, chosen_slots in enumerate(genome):
        for slot in chosen_slots:
            if (
                0 <= slot < problem.slots
                and slot < problem.buses[b_idx].departure_slot
            ):
                matrix[b_idx][slot] = 1

    return matrix



def evaluate(
    genome: Genome,
    problem: ChargingProblem,
    fuzzy_scores: List[float]
) -> Tuple[float, Dict[str, Any]]:
    """Evaluate charging cost, energy needs, and constraints."""

    slot_power = [0.0] * problem.slots
    slot_count = [0] * problem.slots
    bus_energy = [0.0] * len(problem.buses)

    energy_cost = 0.0
    fuzzy_adjustment = 0.0
    invalid = 0

    # Check each bus's selected charging slots.
    for b_idx, bus in enumerate(problem.buses):
        max_energy = energy_per_slot(bus, problem)
        seen = set()

        for slot in genome[b_idx]:
            if slot == -1:
                continue

            if (
                slot in seen
                or slot < 0
                or slot >= problem.slots
                or slot >= bus.departure_slot
            ):
                invalid += 1
                continue

            seen.add(slot)

            # Conservatively count full rated power for the slot.
            slot_power[slot] += bus.charger_kw
            slot_count[slot] += 1

            # Deliver no more energy than the bus requires.
            remaining = max(
                0.0,
                bus.energy_needed_kwh - bus_energy[b_idx]
            )
            charged_energy = min(max_energy, remaining)

            bus_energy[b_idx] += charged_energy
            energy_cost += charged_energy * problem.prices[slot]

            # Keep the fuzzy preference separate from electricity cost.
            fuzzy_adjustment += (
                (1.0 - fuzzy_scores[slot]) * 0.001
            )

    # Check transformer and charger limits.
    capacity_violation = 0.0
    charger_violation = 0

    for slot in range(problem.slots):
        if slot_power[slot] > problem.transformer_limit_kw:
            capacity_violation += (
                slot_power[slot] - problem.transformer_limit_kw
            )

        if slot_count[slot] > problem.available_chargers:
            charger_violation += (
                slot_count[slot] - problem.available_chargers
            )

    # Calculate unmet energy for every bus.
    unmet = 0.0
    per_bus = []

    for idx, bus in enumerate(problem.buses):
        required = bus.energy_needed_kwh
        delivered = min(bus_energy[idx], required)
        shortfall = max(0.0, required - delivered)
        unmet += shortfall

        per_bus.append({
            "bus_id": bus.bus_id,
            "required_kwh": round(required, 3),
            "scheduled_kwh": round(delivered, 3),
            "shortfall_kwh": round(shortfall, 3),
            "ready": shortfall <= 1e-9,
        })

    # Penalize schedules that violate constraints.
    penalty = (
        unmet * 10000.0
        + capacity_violation * 10000.0
        + charger_violation * 10000.0
        + invalid * 10000.0
    )

    # Fitness guides the GA; energy_cost remains the actual energy cost.
    fitness = energy_cost + fuzzy_adjustment + penalty

    metrics = {
        "fitness": fitness,
        "energy_cost": energy_cost,
        "unmet_energy_kwh": unmet,
        "transformer_overload_kw_slots": capacity_violation,
        "charger_overflow_slots": charger_violation,
        "invalid_gene_count": invalid,
        "bus_results": per_bus,
        "slot_power_kw": [
            round(value, 3) for value in slot_power
        ],
        "slot_chargers_used": slot_count,
        "feasible": (
            unmet <= 1e-9
            and capacity_violation <= 1e-9
            and charger_violation == 0
            and invalid == 0
        ),
    }

    return fitness, metrics


def create_individual(
    problem: ChargingProblem,
    rng: random.Random
) -> Genome:
    """Create a random charging schedule."""
    genome = []

    for bus in problem.buses:
        per_slot = energy_per_slot(bus, problem)

        if per_slot <= 0:
            slots_needed = 0
        else:
            slots_needed = int(
                bus.energy_needed_kwh / per_slot + 0.999999
            )

        allowed = list(
            range(max(0, min(problem.slots, bus.departure_slot)))
        )

        rng.shuffle(allowed)

        genome.append(sorted(allowed[:slots_needed]))

    return genome


def repair(
    genome: Genome,
    problem: ChargingProblem,
    rng: random.Random
) -> Genome:
    """Repair a schedule while respecting shared capacity limits."""

    fixed = [[] for _ in problem.buses]
    slot_power = [0.0] * problem.slots
    slot_count = [0] * problem.slots

    fuzzy_scores = build_fuzzy_scores(problem)

    # Prioritize buses that must leave earlier.
    bus_order = sorted(
        range(len(problem.buses)),
        key=lambda i: problem.buses[i].departure_slot
    )

    for i in bus_order:
        bus = problem.buses[i]
        per_slot = energy_per_slot(bus, problem)

        if per_slot <= 0:
            slots_needed = 0
        else:
            slots_needed = int(
                bus.energy_needed_kwh / per_slot + 0.999999
            )

        allowed = list(
            range(max(0, min(problem.slots, bus.departure_slot)))
        )

        # Keep valid inherited slots where possible.
        preferred = [
            slot for slot in genome[i]
            if slot in allowed
        ]

        preferred = list(dict.fromkeys(preferred))

        # Consider remaining slots by price and fuzzy score.
        remaining = [
            slot for slot in allowed
            if slot not in preferred
        ]

        remaining.sort(
            key=lambda slot: (
                problem.prices[slot]
                - 0.01 * fuzzy_scores[slot],
                slot
            )
        )

        candidates = preferred + remaining

        for slot in candidates:
            if len(fixed[i]) >= slots_needed:
                break

            transformer_ok = (
                slot_power[slot] + bus.charger_kw
                <= problem.transformer_limit_kw + 1e-9
            )

            chargers_ok = (
                slot_count[slot] < problem.available_chargers
            )

            if transformer_ok and chargers_ok:
                fixed[i].append(slot)

                slot_power[slot] += bus.charger_kw
                slot_count[slot] += 1

        fixed[i].sort()

    return fixed


def tournament(
    population: List[Genome],
    scores: List[float],
    rng: random.Random,
    size: int = 3
) -> Genome:
    """Select a parent using tournament selection."""

    indices = [
        rng.randrange(len(population))
        for _ in range(size)
    ]

    winner = min(indices, key=lambda idx: scores[idx])

    return [
        gene[:] for gene in population[winner]
    ]


def crossover(
    parent_a: Genome,
    parent_b: Genome,
    rng: random.Random
) -> Tuple[Genome, Genome]:
    """Combine two parent schedules to create offspring."""

    if len(parent_a) < 2:
        return (
            [gene[:] for gene in parent_a],
            [gene[:] for gene in parent_b]
        )

    cut = rng.randrange(1, len(parent_a))

    child_a = (
        [gene[:] for gene in parent_a[:cut]]
        + [gene[:] for gene in parent_b[cut:]]
    )

    child_b = (
        [gene[:] for gene in parent_b[:cut]]
        + [gene[:] for gene in parent_a[cut:]]
    )

    return child_a, child_b


def mutate(
    genome: Genome,
    problem: ChargingProblem,
    rng: random.Random,
    rate: float = 0.15
) -> None:
    """Randomly change charging slots in a schedule."""

    for i, bus in enumerate(problem.buses):

        if rng.random() < rate:
            allowed = list(
                range(max(0, min(problem.slots, bus.departure_slot)))
            )

            if allowed and genome[i]:
                gene_index = rng.randrange(len(genome[i]))
                genome[i][gene_index] = rng.choice(allowed)

            elif allowed:
                genome[i].append(rng.choice(allowed))


def optimize(
    problem: ChargingProblem,
    population_size: int = 100,
    generations: int = 250,
    mutation_rate: float = 0.18,
    seed: int = 7
) -> Tuple[Genome, Dict[str, Any], List[float]]:
    """Run the genetic algorithm and return the best schedule."""

    rng = random.Random(seed)
    fuzzy_scores = build_fuzzy_scores(problem)

    population = [
        repair(create_individual(problem, rng), problem, rng)
        for _ in range(population_size)
    ]

    history = []
    best_genome = None
    best_metrics = None

    for _ in range(generations):
        evaluated = [
            evaluate(individual, problem, fuzzy_scores)
            for individual in population
        ]

        scores = [item[0] for item in evaluated]

        best_index = min(
            range(len(population)),
            key=lambda i: scores[i]
        )

        history.append(scores[best_index])

        if (
            best_metrics is None
            or scores[best_index] < best_metrics["fitness"]
        ):
            best_genome = [
                gene[:] for gene in population[best_index]
            ]

            best_metrics = evaluated[best_index][1]

        # Preserve the two best individuals (elitism).
        ranked = sorted(
            range(len(population)),
            key=lambda i: scores[i]
        )

        next_population = [
            [gene[:] for gene in population[ranked[0]]]
        ]

        if len(ranked) > 1:
            next_population.append(
                [gene[:] for gene in population[ranked[1]]]
            )

        # Create the next generation.
        while len(next_population) < population_size:
            parent1 = tournament(population, scores, rng)
            parent2 = tournament(population, scores, rng)

            child1, child2 = crossover(parent1, parent2, rng)

            mutate(child1, problem, rng, mutation_rate)
            mutate(child2, problem, rng, mutation_rate)

            next_population.append(
                repair(child1, problem, rng)
            )

            if len(next_population) < population_size:
                next_population.append(
                    repair(child2, problem, rng)
                )

        population = next_population

    # Return the best valid candidate found during the run.
    assert best_genome is not None
    assert best_metrics is not None

    return best_genome, best_metrics, history


def baseline_schedule(problem: ChargingProblem) -> Genome:
    """Build a low-cost baseline respecting shared capacity limits."""

    genome = [[] for _ in problem.buses]
    slot_power = [0.0] * problem.slots
    slot_count = [0] * problem.slots

    # Schedule buses with earlier departure deadlines first.
    bus_order = sorted(
        range(len(problem.buses)),
        key=lambda i: problem.buses[i].departure_slot
    )

    for i in bus_order:
        bus = problem.buses[i]
        per_slot = energy_per_slot(bus, problem)

        if per_slot <= 0:
            slots_needed = 0
        else:
            slots_needed = int(
                bus.energy_needed_kwh / per_slot + 0.999999
            )

        # Choose the cheapest available slots before departure.
        allowed_slots = sorted(
            range(max(0, min(problem.slots, bus.departure_slot))),
            key=lambda slot: (problem.prices[slot], slot)
        )

        for slot in allowed_slots:
            if len(genome[i]) >= slots_needed:
                break

            transformer_ok = (
                slot_power[slot] + bus.charger_kw
                <= problem.transformer_limit_kw + 1e-9
            )

            charger_ok = (
                slot_count[slot] < problem.available_chargers
            )

            if transformer_ok and charger_ok:
                genome[i].append(slot)

                slot_power[slot] += bus.charger_kw
                slot_count[slot] += 1

        genome[i].sort()

    return genome
