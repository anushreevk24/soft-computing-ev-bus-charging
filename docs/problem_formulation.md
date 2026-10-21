# Problem Formulation — EV Bus Overnight Charging

## Source problem statement

Problem Statement 20 on page 2 of the supplied AAT PDF asks teams to schedule overnight charging of an electric bus fleet under charger and transformer limits so every bus is ready for morning service at minimum energy cost. The suggested technique is **Fuzzy Logic + Evolutionary Algorithm**, Units **2 and 3**, mapped to **SDG 11**.

## Sets and parameters

- \(B\): set of buses.
- \(T\): set of charging time slots.
- \(p_t\): electricity price per kWh in slot \(t\).
- \(P_b\): charging power for bus \(b\), in kW.
- \(\Delta h\): slot duration in hours.
- \(E_b\): energy still required by bus \(b\), in kWh.
- \(d_b\): last slot index allowed for bus \(b\).
- \(P_{max}\): transformer power limit.
- \(C\): number of available chargers.

## Decision variable

\(x_{b,t}\in\{0,1\}\): 1 if bus \(b\) charges in slot \(t\), otherwise 0.

## Objective

Minimise the energy cost:

\[
\min \sum_{b\in B}\sum_{t\in T} p_t P_b\Delta h\,x_{b,t}
\]

A small fuzzy-score tie-break term is used in the implementation to prefer slots the fuzzy rule system considers attractive when energy costs are almost equal.

## Constraints

1. **Energy requirement:** \(\sum_{t<d_b}P_b\Delta h\,x_{b,t}\ge E_b\) for every bus.
2. **Transformer capacity:** \(\sum_b P_bx_{b,t}\le P_{max}\) for every slot.
3. **Charger capacity:** \(\sum_b x_{b,t}\le C\) for every slot.
4. **Deadline:** \(x_{b,t}=0\) for slots \(t\ge d_b\).
5. **Binary decision:** \(x_{b,t}\in\{0,1\}\).

## Soft-computing approach

The fuzzy module calculates low/medium/high memberships for price and urgency. A compact rule base produces a slot attractiveness score. The genetic algorithm represents each bus's selected slot indices as genes and implements tournament selection, one-point crossover, mutation, elitism, and repair. Fitness is energy cost plus large penalties for unmet energy, transformer overload, charger overflow, and invalid assignments.

## Assumptions and limitations

The supplied sample is synthetic. Each bus uses a fixed charging power and charges in 30-minute on/off blocks. The implementation uses a simple fixed power per bus rather than modelling charging taper, battery efficiency, demand charges, charger compatibility, or uncertain departure times. The genetic algorithm is stochastic; use multiple seeds for robust evaluation. A schedule should be treated as feasible only when the feasibility flag is true and every bus's readiness check passes.
