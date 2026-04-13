#!/usr/bin/env python3
"""
METRICS AGENT 4: Phase 4 Timeline Forecast
Monte Carlo Simulation - 10 paths, Critical Path Analysis
WBS: HALE_IMPLEMENTATION_WBS.md (Phase 4: Days 22-30 - Integration/Maturation)
"""

import json
import random
import statistics
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple

@dataclass
class Task:
    name: str
    task_id: str
    min_days: float
    mode_days: float
    max_days: float
    priority: str
    owner: str
    due_day: int
    dependencies: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

# Phase 4 Tasks from WBS
PHASE4_TASKS = [
    Task(
        name="Trust Compounding System",
        task_id="4.1",
        min_days=2.5,
        mode_days=3.5,
        max_days=5.0,
        priority="P2",
        owner="Claude Sonnet",
        due_day=22,
        dependencies=[]
    ),
    Task(
        name="Commander Preference Modeling",
        task_id="4.2",
        min_days=4.0,
        mode_days=5.0,
        max_days=6.5,
        priority="P2",
        owner="DeepSeek V3.1",
        due_day=25,
        dependencies=["4.1"]  # Sequential: needs trust metrics from 4.1
    ),
    Task(
        name="Performance Optimization",
        task_id="4.3",
        min_days=3.0,
        mode_days=3.5,
        max_days=4.5,
        priority="P1",
        owner="DeepSeek V3.1",
        due_day=28,
        dependencies=["4.2"]  # Sequential: optimization after preference modeling
    ),
]

def triangular_sample(min_val: float, mode_val: float, max_val: float) -> float:
    """Generate sample from triangular distribution."""
    u = random.random()
    c = (mode_val - min_val) / (max_val - min_val)

    if u <= c:
        return min_val + (u * c) ** 0.5 * (max_val - min_val)
    else:
        return max_val - ((1 - u) * (1 - c)) ** 0.5 * (max_val - min_val)

def monte_carlo_simulation(tasks: List[Task], num_paths: int = 10) -> Dict:
    """Run Monte Carlo simulation for task durations."""

    paths = []
    all_durations = {task.task_id: [] for task in tasks}
    completion_days = []

    for path_num in range(num_paths):
        path_data = {"path": path_num + 1, "tasks": {}}
        current_day = 22  # Phase 4 starts on day 22

        # Task 4.1: Independent, starts day 22
        duration_4_1 = triangular_sample(PHASE4_TASKS[0].min_days, PHASE4_TASKS[0].mode_days, PHASE4_TASKS[0].max_days)
        completion_4_1 = current_day + duration_4_1
        path_data["tasks"]["4.1"] = {"duration": round(duration_4_1, 2), "completion_day": round(completion_4_1, 2)}
        all_durations["4.1"].append(duration_4_1)

        # Task 4.2: Depends on 4.1, starts after 4.1 completes
        start_4_2 = completion_4_1
        duration_4_2 = triangular_sample(PHASE4_TASKS[1].min_days, PHASE4_TASKS[1].mode_days, PHASE4_TASKS[1].max_days)
        completion_4_2 = start_4_2 + duration_4_2
        path_data["tasks"]["4.2"] = {"duration": round(duration_4_2, 2), "start_day": round(start_4_2, 2), "completion_day": round(completion_4_2, 2)}
        all_durations["4.2"].append(duration_4_2)

        # Task 4.3: Depends on 4.2, starts after 4.2 completes
        start_4_3 = completion_4_2
        duration_4_3 = triangular_sample(PHASE4_TASKS[2].min_days, PHASE4_TASKS[2].mode_days, PHASE4_TASKS[2].max_days)
        completion_4_3 = start_4_3 + duration_4_3
        path_data["tasks"]["4.3"] = {"duration": round(duration_4_3, 2), "start_day": round(start_4_3, 2), "completion_day": round(completion_4_3, 2)}
        all_durations["4.3"].append(duration_4_3)

        # Critical path is completion of 4.3
        phase4_total_days = completion_4_3 - 22
        completion_days.append(phase4_total_days)
        path_data["phase4_total_days"] = round(phase4_total_days, 2)
        path_data["calendar_day"] = round(22 + phase4_total_days, 1)

        paths.append(path_data)

    # Calculate statistics
    mean_days = statistics.mean(completion_days)
    median_days = statistics.median(completion_days)
    stdev_days = statistics.stdev(completion_days) if len(completion_days) > 1 else 0
    min_days = min(completion_days)
    max_days = max(completion_days)

    # Percentiles
    sorted_days = sorted(completion_days)
    p90_days = sorted_days[int(len(sorted_days) * 0.9) - 1] if len(sorted_days) >= 1 else sorted_days[-1]
    p75_days = sorted_days[int(len(sorted_days) * 0.75) - 1] if len(sorted_days) >= 1 else sorted_days[-1]

    # Variance analysis
    task_variances = {}
    for task_id in all_durations:
        task_durations = all_durations[task_id]
        task_mean = statistics.mean(task_durations)
        task_stdev = statistics.stdev(task_durations) if len(task_durations) > 1 else 0
        task_variances[task_id] = {
            "mean_days": round(task_mean, 2),
            "stdev": round(task_stdev, 2),
            "cv": round(task_stdev / task_mean, 3) if task_mean > 0 else 0,  # Coefficient of variation
            "min": round(min(task_durations), 2),
            "max": round(max(task_durations), 2)
        }

    # Risk identification
    risks = []

    # Risk 1: High variance in critical path (4.2)
    if task_variances["4.2"]["stdev"] > 0.8:
        risks.append({
            "id": "R1_HIGH_VARIANCE_4_2",
            "severity": "HIGH",
            "description": "Task 4.2 (Commander Preference Modeling) has high variance (σ={:.2f}d)".format(task_variances["4.2"]["stdev"]),
            "impact": "Phase 4 completion highly sensitive to 4.2 delays",
            "mitigation": "Break 4.2 into smaller milestones; increase daily sync frequency with DeepSeek owner"
        })

    # Risk 2: P90 exceeds original target (30 days from day 1 = day 30, so Phase 4 should end ~day 30)
    if p90_days > 8:
        risks.append({
            "id": "R2_P90_DELAY",
            "severity": "MEDIUM",
            "description": "P90 completion is {:.1f} days (calendar day ~{:.0f})".format(p90_days, 22 + p90_days),
            "impact": "10% of scenarios overrun original 8-day Phase 4 window",
            "mitigation": "Defer non-critical Phase 4.3 optimization tasks; focus on 4.1 and 4.2 as priorities"
        })

    # Risk 3: Sequential dependency chain vulnerability
    total_mean_chain = sum([task_variances[tid]["mean_days"] for tid in ["4.1", "4.2", "4.3"]])
    if mean_days > 8:
        risks.append({
            "id": "R3_SEQUENTIAL_CHAIN",
            "severity": "MEDIUM",
            "description": "Sequential dependency chain (4.1→4.2→4.3) means {:.1f} days avg".format(total_mean_chain),
            "impact": "Delays in early tasks cascade to Phase 4 completion",
            "mitigation": "Parallelize 4.3 with 4.2; identify fast-track 4.1 deliverables for parallel work"
        })

    # Risk 4: Owner conflict (DeepSeek owns both 4.2 and 4.3)
    risks.append({
        "id": "R4_OWNER_CONTENTION",
        "severity": "MEDIUM",
        "description": "DeepSeek V3.1 is primary owner for both 4.2 and 4.3",
        "impact": "Sequential tasks cannot be parallelized; shared resource bottleneck",
        "mitigation": "Assign 4.3 to Claude Sonnet as parallel optimization effort; document hand-off protocol"
    })

    # Risk 5: P90 > mean by significant margin
    p90_excess = p90_days - mean_days
    if p90_excess > 1.5:
        risks.append({
            "id": "R5_TAIL_RISK",
            "severity": "LOW",
            "description": "P90 exceeds mean by {:.1f} days (distribution right-skewed)".format(p90_excess),
            "impact": "90% confidence requires {:.1f}d buffer beyond mean estimate".format(p90_excess),
            "mitigation": "Budget 8.5 days for Phase 4; schedule parallel work for margin"
        })

    return {
        "simulation": {
            "num_paths": num_paths,
            "start_day": 22,
            "phase": "Phase 4 (Integration/Maturation)",
            "tasks": [
                {"id": t.task_id, "name": t.name, "priority": t.priority, "owner": t.owner}
                for t in PHASE4_TASKS
            ]
        },
        "summary": {
            "mean_days": round(mean_days, 2),
            "median_days": round(median_days, 2),
            "stdev_days": round(stdev_days, 2),
            "p75_days": round(p75_days, 2),
            "p90_days": round(p90_days, 2),
            "min_days": round(min_days, 2),
            "max_days": round(max_days, 2),
            "calendar_day_mean": round(22 + mean_days, 1),
            "calendar_day_p90": round(22 + p90_days, 1),
            "critical_path": ["4.1 → 4.2 → 4.3"],
            "variance_ratio": round(stdev_days / mean_days, 3) if mean_days > 0 else 0
        },
        "task_variance": task_variances,
        "risks": [
            {
                "id": r["id"],
                "severity": r["severity"],
                "description": r["description"],
                "impact": r["impact"],
                "mitigation": r["mitigation"]
            }
            for r in risks
        ],
        "paths": paths
    }

def main():
    random.seed(2026)  # Fixed seed for reproducibility

    results = monte_carlo_simulation(PHASE4_TASKS, num_paths=10)

    # Write to output file
    output_path = Path("/home/john/Thunderbird/output/metrics_forecast.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    # Print summary
    print("\n" + "="*70)
    print("METRICS AGENT 4: PHASE 4 TIMELINE FORECAST")
    print("="*70)
    print(f"\nMonte Carlo Simulation (10 paths)")
    print(f"Phase 4 (Integration/Maturation): Days 22-30")
    print(f"\n📊 RESULTS:")
    print(f"  Mean completion:     {results['summary']['mean_days']:>6.2f} days → Calendar day {results['summary']['calendar_day_mean']}")
    print(f"  P90 completion:      {results['summary']['p90_days']:>6.2f} days → Calendar day {results['summary']['calendar_day_p90']}")
    print(f"  Median completion:   {results['summary']['median_days']:>6.2f} days")
    print(f"  Std Deviation:       {results['summary']['stdev_days']:>6.2f} days")
    print(f"  Range:               {results['summary']['min_days']:.2f}–{results['summary']['max_days']:.2f} days")
    print(f"  Variance ratio:      {results['summary']['variance_ratio']:.3f} (CV = σ/μ)")

    print(f"\n🔗 CRITICAL PATH: {' → '.join(results['summary']['critical_path'])}")
    print(f"\n📈 TASK VARIANCE ANALYSIS:")
    for task_id in ["4.1", "4.2", "4.3"]:
        tv = results['task_variance'][task_id]
        print(f"  {task_id}: {tv['mean_days']}±{tv['stdev']}d (CV={tv['cv']}, range {tv['min']}-{tv['max']})")

    print(f"\n⚠️  RISKS IDENTIFIED ({len(results['risks'])})")
    for risk in results['risks']:
        print(f"  [{risk['severity']}] {risk['id']}: {risk['description']}")
        print(f"        → {risk['mitigation']}")

    print(f"\n✅ Output written to: {output_path}")
    print("="*70 + "\n")

    return results

if __name__ == "__main__":
    main()
