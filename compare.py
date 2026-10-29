"""
Compare the MCTS and A* snake agents.

Every agent plays the same games (same seeds, so the same food sequence as long
as the snakes make the same moves), and the script prints a summary table:

    python compare.py --games 10
    python compare.py --games 10 --plot compare.png   # also save a chart (needs matplotlib)
"""

import argparse
import csv
import statistics
from concurrent.futures import ProcessPoolExecutor

from snake_game import make_agent, play_game

AGENT_LABELS = {"mcts": "MCTS", "mcts-safe": "MCTS (safe)", "astar": "A* (plain)", "astar-safe": "A* (safe)"}


def run_one(job):
    name, seed, board_size, iterations, rollout_depth = job
    agent = make_agent(name, seed=seed, iterations=iterations, rollout_depth=rollout_depth)
    return name, seed, play_game(agent, seed, board_size)


def summarize(name, games):
    scores = [g["score"] for g in games]
    results = [g["result"] for g in games]
    return {
        "agent": AGENT_LABELS[name],
        "avg_score": statistics.mean(scores),
        "std_score": statistics.stdev(scores) if len(scores) > 1 else 0.0,
        "min_score": min(scores),
        "max_score": max(scores),
        "avg_steps": statistics.mean(g["steps"] for g in games),
        "ms_per_move": statistics.mean(g["ms_per_move"] for g in games),
        "died": results.count("died"),
        "looping": results.count("looping"),
        "won": results.count("won"),
    }


def print_table(rows, games):
    print(f"\nResults over {games} games per agent\n")
    print("| Agent | Avg score | Std | Min | Max | Avg steps | ms/move | Died | Looping | Won |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in rows:
        print(f"| {r['agent']} | {r['avg_score']:.1f} | {r['std_score']:.1f} | {r['min_score']} | {r['max_score']} "
              f"| {r['avg_steps']:.0f} | {r['ms_per_move']:.2f} | {r['died']} | {r['looping']} | {r['won']} |")


def plot(results, agents, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [AGENT_LABELS[a] for a in agents]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    ax1.boxplot([[g["score"] for g in results[a]] for a in agents])
    ax1.set_xticks(range(1, len(agents) + 1), labels)
    ax1.set_title("Score per game")
    ax1.set_ylabel("Food eaten")

    ax2.bar(labels, [statistics.mean(g["ms_per_move"] for g in results[a]) for a in agents])
    ax2.set_title("Thinking time")
    ax2.set_ylabel("ms per move")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"\nSaved chart to {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare MCTS and A* on the same games.")
    parser.add_argument("--agents", nargs="+", choices=list(AGENT_LABELS), default=list(AGENT_LABELS))
    parser.add_argument("--games", type=int, default=10)
    parser.add_argument("--seed", type=int, default=0, help="Seed of the first game; game i uses seed + i.")
    parser.add_argument("--board-size", type=int, default=15)
    parser.add_argument("--iterations", type=int, default=300, help="MCTS iterations per move.")
    parser.add_argument("--rollout-depth", type=int, default=30, help="MCTS rollout depth.")
    parser.add_argument("--jobs", type=int, default=None, help="Games to run in parallel (default: CPU count).")
    parser.add_argument("--csv", help="Save every game's result to this CSV file.")
    parser.add_argument("--plot", help="Save a comparison chart to this image file (needs matplotlib).")
    args = parser.parse_args()

    jobs = [(name, args.seed + i, args.board_size, args.iterations, args.rollout_depth)
            for name in args.agents for i in range(args.games)]
    results = {name: [] for name in args.agents}
    rows_out = []
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        for name, seed, stats in pool.map(run_one, jobs):
            results[name].append(stats)
            rows_out.append({"agent": name, "seed": seed, **stats})
            print(f"{AGENT_LABELS[name]:<11} seed={seed:<4} score={stats['score']:<4} "
                  f"steps={stats['steps']:<5} {stats['result']:<8} {stats['ms_per_move']:.2f} ms/move")

    print_table([summarize(name, results[name]) for name in args.agents], args.games)

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["agent", "seed", "score", "steps", "result", "ms_per_move"])
            writer.writeheader()
            writer.writerows(rows_out)
        print(f"\nSaved per-game results to {args.csv}")

    if args.plot:
        plot(results, args.agents, args.plot)
