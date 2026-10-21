import json
import tempfile
import unittest
from pathlib import Path
from main import load_problem
from optimizer import optimize, evaluate, build_fuzzy_scores, baseline_schedule
from fuzzy import triangular, slot_attractiveness


class FuzzyTests(unittest.TestCase):
    def test_triangular_peak(self):
        self.assertEqual(triangular(0.5, 0.0, 0.5, 1.0), 1.0)

    def test_fuzzy_score_is_bounded(self):
        score = slot_attractiveness(7.0, 4, 16, 6.0, 10.0)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)


class OptimizerTests(unittest.TestCase):
    def setUp(self):
        self.problem = load_problem("data/buses.json")

    def test_schedule_shape(self):
        genome, metrics, history = optimize(self.problem, population_size=20, generations=20, seed=2)
        self.assertEqual(len(genome), len(self.problem.buses))
        self.assertEqual(len(history), 20)
        self.assertIn("feasible", metrics)

    def test_fitness_penalizes_unmet_energy(self):
        empty = [[] for _ in self.problem.buses]
        scores = build_fuzzy_scores(self.problem)
        _, metrics = evaluate(empty, self.problem, scores)
        self.assertGreater(metrics["unmet_energy_kwh"], 0)
        self.assertFalse(metrics["feasible"])

    def test_baseline_evaluates(self):
        scores = build_fuzzy_scores(self.problem)
        _, metrics = evaluate(baseline_schedule(self.problem), self.problem, scores)
        self.assertIn("energy_cost", metrics)


if __name__ == "__main__":
    unittest.main()
