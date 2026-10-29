# README

## Playing Snake with Monte Carlo Tree Search

## Acknowledgements
This project uses the `snake-ai` environment for the snake game from [linyiLYi](https://github.com/linyiLYi/snake-ai). A big thank you to the original author for providing such a great resource.

Author : Po Kai Su

### Introduction
The snake is controlled by a Monte Carlo Tree Search (MCTS) agent. Before every move, the agent looks ahead by simulating many possible futures and picks the move that leads to the best outcomes on average.

An earlier version of this project controlled the snake with body posture captured by a webcam (Mediapipe + an MLP classifier). That camera and pose-detection code has been removed.

### How MCTS chooses a move
Each move, the agent ([mcts.py](期末報告/mcts.py)) repeats four phases (300 times by default, or until the time limit):

1. **Selection** – start at the current position and walk down the search tree, choosing moves with the UCT formula, which balances moves that have scored well (exploitation) against moves that have been tried rarely (exploration).
2. **Expansion** – add one move that has not been tried yet to the tree.
3. **Simulation (rollout)** – play ahead up to 30 steps with a fast policy: head toward the food while avoiding moves that die immediately, with some randomness.
4. **Backpropagation** – add the result to every node on the path.

The move whose node was visited most is played.

Rewards: +1 for eating food, −1 for dying, discounted by 0.97 per step. If a rollout ends with the snake still alive, the position is scored by how close the head is to the food, and penalised if a flood fill shows the snake has trapped itself in a space smaller than its own length.

Food appears at random, so the tree is *open-loop*: each node keeps statistics for a sequence of moves, and every iteration replays that sequence with newly sampled food.

### Installation
```bash
pip install -r requirements.txt
```

### Usage
Run from the `期末報告` folder.

Watch the agent play (click **START THE GAME**):
```bash
python snake_game.py
```

Run games without a window and print the scores:
```bash
python snake_game.py --headless --games 5
```

| Option | Default | Description |
| --- | --- | --- |
| `--iterations` | 300 | MCTS iterations per move |
| `--time-limit` | 0.2 | Max thinking time per move in seconds (0 = no limit) |
| `--rollout-depth` | 30 | Steps simulated in each rollout |
| `--interval` | 0.1 | Minimum seconds between snake moves |
| `--board-size` | 15 | Board width and height |
| `--seed` | random | Random seed |

### Results
With the default settings on the 15×15 board, three headless games (seeds 1–3) scored 90, 77 and 70 (average 79), taking about 30 ms per move.
