# Snake MC

## Playing Snake with Monte Carlo Tree Search and A*

![Comparison](compare.png)

## Acknowledgements
This project uses the `snake-ai` environment for the snake game from [linyiLYi](https://github.com/linyiLYi/snake-ai). A big thank you to the original author for providing such a great resource.

Author : Po Kai Su

### Introduction
The snake is controlled by a search algorithm instead of a human, and we compare two of them:

- **Monte Carlo Tree Search (MCTS)** – before every move, simulate many possible futures (including where food might appear) and pick the move that leads to the best outcomes on average.
- **A\* search** – plan the shortest path to the food and follow it, in a plain and a "safe" variant.

This project grew out of our earlier final project, where the snake was controlled by body posture captured with a webcam (Mediapipe + an MLP classifier). Here the webcam is replaced by search algorithms.

### Project structure
| File | Description |
| --- | --- |
| [snake_game.py](snake_game.py) | The game (pygame) and the entry point for watching an agent play |
| [mcts.py](mcts.py) | Monte Carlo Tree Search agent, plus the fast game simulator it uses |
| [astar.py](astar.py) | A\* agent, plain and safe variants |
| [compare.py](compare.py) | Runs every agent on the same games and prints a results table |
| `image/`, `sound/` | Game graphics and sound effects |

### How MCTS chooses a move
Each move, the agent ([mcts.py](mcts.py)) repeats four phases (300 times by default, or until the time limit):

1. **Selection** – start at the current position and walk down the search tree, choosing moves with the UCT formula, which balances moves that have scored well (exploitation) against moves that have been tried rarely (exploration).
2. **Expansion** – add one move that has not been tried yet to the tree.
3. **Simulation (rollout)** – play ahead up to 30 steps with a fast policy: head toward the food while avoiding moves that die immediately, with some randomness.
4. **Backpropagation** – add the result to every node on the path.

The move whose node was visited most is played.

Rewards: +1 for eating food, −1 for dying, discounted by 0.97 per step. If a rollout ends with the snake still alive, the position is scored by how close the head is to the food, and penalised if a flood fill shows the snake has trapped itself in a space smaller than its own length.

Food appears at random, so the tree is *open-loop*: each node keeps statistics for a sequence of moves, and every iteration replays that sequence with newly sampled food.

### How A* chooses a move
The A\* agent ([astar.py](astar.py)) finds the shortest path from the head to the food, with cost = steps taken and heuristic = Manhattan distance. The search is time-aware: the body segment `k` cells behind the head leaves its cell after `len(snake) - k` steps, so a path may go through cells the tail will have vacated by the time the head gets there.

- **A\* (plain)** follows that path. If there is no path, it moves to the neighbouring cell with the most free space reachable from it.
- **A\* (safe)** first imagines the snake after following the path and eating. It follows the path only if, from there, the head can still reach the tail, because a snake that can reach its tail can always escape by following it. Otherwise it stalls: it takes a move that keeps the tail reachable, as far from the food as possible, until eating becomes safe.

### Installation
Requires Python 3.10 or newer.
```bash
git clone https://github.com/winston98321/snake_MC.git
```
```bash
cd snake_MC
```
```bash
pip install -r requirements.txt
```

### Usage
Watch an agent play (click **START THE GAME**):
```bash
python snake_game.py --agent mcts
```
```bash
python snake_game.py --agent astar-safe
```

Run games without a window and print the scores:
```bash
python snake_game.py --headless --games 5
```

Compare the agents on the same games (game `i` uses seed `i` for every agent):
```bash
python compare.py --games 20 --csv results.csv --plot compare.png
```

| Option | Default | Description |
| --- | --- | --- |
| `--agent` | mcts | `mcts`, `astar` or `astar-safe` |
| `--iterations` | 300 | MCTS iterations per move |
| `--time-limit` | 0.2 | Max thinking time per move in seconds (0 = no limit) |
| `--rollout-depth` | 30 | Steps simulated in each rollout |
| `--interval` | 0.1 | Minimum seconds between snake moves |
| `--board-size` | 15 | Board width and height |
| `--seed` | random | Random seed |

### Results
20 games per agent on the 15×15 board, seeds 0–19 (`python compare.py --games 20`). MCTS used 300 iterations per move with no time limit. The highest possible score is 222: the board has 225 cells and the snake starts 3 long.

| Agent | Avg score | Std | Min | Max | Avg steps | ms/move | Died | Stopped (looping) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MCTS | 74.9 | 17.1 | 40 | 121 | 1318 | 75.65 | 20 | 0 |
| A\* (plain) | 55.5 | 15.3 | 24 | 79 | 694 | 0.13 | 20 | 0 |
| A\* (safe) | 201.4 | 49.7 | 36 | 221 | 8444 | 0.40 | 2 | 18 |

"Stopped (looping)" means the snake was still alive but went 900 steps without eating, so the game was ended. For A\* (safe), this happened at scores of 211–221, with the board almost full. Times per move were measured with games running in parallel; a single MCTS game on its own takes about 30 ms per move.

**What we found**
- **Plain A\* is fast but short-sighted.** It always takes the shortest path, so it soon closes off parts of the board with its own body and traps itself.
- **MCTS beats plain A\*** (75 vs 56 on average) because its simulations can see some traps coming. But it looks only about 30 steps ahead and only gets 300 simulations per move, so once the snake is long, a trap often closes beyond that horizon. It is also about 500× slower per move.
- **Safe A\* scores best by far.** The "can I still reach my tail?" check is an exact safety rule for this game, and it is much stronger than what a rollout can estimate. It only failed when random food appeared inside a one-cell-wide corridor the snake was already in: the snake had to eat it, grew by one and hit a dead end. A\* plans only for the food that is already on the board, while MCTS also samples where new food may appear.
- **Takeaway:** a good hand-written rule (tail reachability) beats general-purpose search here. MCTS is the more general method: it needs no rules specific to the game, only a simulator, and it improves with more iterations or a better rollout policy. One idea is to use the safe-A\* rule as the MCTS rollout policy.
