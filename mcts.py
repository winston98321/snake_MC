"""
Monte Carlo Tree Search (蒙地卡羅樹搜尋) controller for the snake game.

Each time the game asks for a move, the agent builds a search tree from the
current position and runs four phases many times:

    1. Selection     - walk down the tree, picking children with UCT
    2. Expansion     - add one untried move as a new child
    3. Simulation    - play the rest of the game with a fast rollout policy
    4. Backpropagation - add the rollout's return to every node on the path

Food appears at random, so the tree is "open loop": nodes store statistics
for a sequence of moves, and every iteration re-simulates that sequence from
the root with freshly sampled food positions.

Safe mode borrows the rule that makes safe A* strong: a snake whose head can
still reach its tail can always escape by following it. With safe=True the
agent only searches moves that keep the tail reachable (when any exist), and
rollouts that end with the tail unreachable are penalised.
"""

import math
import random
import time
from collections import deque

# 0: UP, 1: DOWN, 2: LEFT, 3: RIGHT (same encoding as SnakeGame.step)
MOVES = {0: (-1, 0), 1: (1, 0), 2: (0, -1), 3: (0, 1)}
OPPOSITE = {0: 1, 1: 0, 2: 3, 3: 2}
DIRECTION_TO_ACTION = {"UP": 0, "DOWN": 1, "LEFT": 2, "RIGHT": 3}


class SnakeState:
    """Lightweight copy of the game used for fast simulation."""

    __slots__ = ("board_size", "snake", "body", "direction", "food", "alive", "won", "rng")

    def __init__(self, board_size, snake, direction, food, rng):
        self.board_size = board_size
        self.snake = deque(snake)  # Head is snake[0], in (row, col) format.
        self.body = set(snake)
        self.direction = direction  # Action index of the current heading.
        self.food = food
        self.alive = True
        self.won = False
        self.rng = rng

    @classmethod
    def from_game(cls, game, rng):
        return cls(game.board_size, game.snake, DIRECTION_TO_ACTION[game.direction], game.food, rng)

    def copy(self):
        state = SnakeState.__new__(SnakeState)
        state.board_size = self.board_size
        state.snake = deque(self.snake)
        state.body = set(self.body)
        state.direction = self.direction
        state.food = self.food
        state.alive = self.alive
        state.won = self.won
        state.rng = self.rng
        return state

    def legal_actions(self):
        # Turning back onto the neck is ignored by the game, so it is never a real choice.
        return [a for a in range(4) if a != OPPOSITE[self.direction]]

    def next_head(self, action):
        dr, dc = MOVES[action]
        row, col = self.snake[0]
        return row + dr, col + dc

    def is_safe(self, action):
        """True if taking `action` does not kill the snake on the very next step."""
        row, col = self.next_head(action)
        if not (0 <= row < self.board_size and 0 <= col < self.board_size):
            return False
        if (row, col) not in self.body:
            return True
        # Moving into the tail is fine, because the tail moves away (unless we eat).
        return (row, col) == self.snake[-1] and (row, col) != self.food

    def step(self, action):
        """Advance one step with the same rules as SnakeGame.step. Returns True if food was eaten."""
        self.direction = action
        head = self.next_head(action)

        ate = head == self.food
        if not ate:
            self.body.discard(self.snake.pop())

        row, col = head
        if head in self.body or not (0 <= row < self.board_size and 0 <= col < self.board_size):
            self.alive = False
            return ate

        self.snake.appendleft(head)
        self.body.add(head)

        if ate:
            self.food = self._random_food()
        return ate

    def _random_food(self):
        n = self.board_size
        if len(self.body) >= n * n:
            self.won = True
            self.alive = False
            return None
        while True:
            cell = (self.rng.randrange(n), self.rng.randrange(n))
            if cell not in self.body:
                return cell

    def reachable_area(self):
        """Number of free cells the head can still reach (flood fill)."""
        n = self.board_size
        start = self.snake[0]
        tail = self.snake[-1]
        seen = {start}
        queue = [start]
        count = 0
        while queue:
            row, col = queue.pop()
            for dr, dc in MOVES.values():
                cell = (row + dr, col + dc)
                if cell in seen or not (0 <= cell[0] < n and 0 <= cell[1] < n):
                    continue
                if cell in self.body and cell != tail:
                    continue
                seen.add(cell)
                queue.append(cell)
                count += 1
        return count


class Node:
    __slots__ = ("children", "visits", "value")

    def __init__(self):
        self.children = {}  # action -> Node
        self.visits = 0
        self.value = 0.0


class MCTSAgent:
    def __init__(self, iterations=300, time_limit=None, rollout_depth=30,
                 exploration=1.0, gamma=0.97, seed=None, safe=False):
        self.safe = safe
        self.iterations = iterations
        self.time_limit = time_limit  # Seconds per move; stops early if reached before `iterations`.
        self.rollout_depth = rollout_depth
        self.exploration = exploration
        self.gamma = gamma
        self.rng = random.Random(seed)  # Own RNG so planning does not disturb the game's food sequence.

    def choose_action(self, game):
        root_state = SnakeState.from_game(game, self.rng)
        safe = [a for a in root_state.legal_actions() if root_state.is_safe(a)]
        if self.safe:
            # Keep only moves after which the head can still reach the tail, if there are any.
            safe = [a for a in safe if self._tail_reachable_after(root_state, a)] or safe
        if len(safe) <= 1:
            return safe[0] if safe else root_state.direction

        root = Node()
        deadline = time.perf_counter() + self.time_limit if self.time_limit else None
        for _ in range(self.iterations):
            self._iterate(root, root_state, safe)
            if deadline and time.perf_counter() >= deadline:
                break

        return max(root.children, key=lambda a: root.children[a].visits)

    @staticmethod
    def _tail_reachable_after(state, action):
        from astar import tail_reachable  # Imported here because astar.py imports this module.

        nxt = state.next_head(action)
        body = list(state.snake)
        body = [nxt] + (body if nxt == state.food else body[:-1])
        return tail_reachable(body, state.board_size)

    def _iterate(self, root, root_state, root_actions):
        state = root_state.copy()
        node = root
        path = [root]
        total = 0.0
        discount = 1.0

        # 1. Selection + 2. Expansion
        while state.alive:
            actions = root_actions if node is root else state.legal_actions()
            untried = [a for a in actions if a not in node.children]
            if untried:
                action = self.rng.choice(untried)
                node.children[action] = Node()
                node = node.children[action]
                path.append(node)
                total += discount * self._reward(state, action)
                discount *= self.gamma
                break
            action = self._uct_select(node)
            node = node.children[action]
            path.append(node)
            total += discount * self._reward(state, action)
            discount *= self.gamma

        # 3. Simulation
        total += discount * self._rollout(state)

        # 4. Backpropagation
        for n in path:
            n.visits += 1
            n.value += total

    def _uct_select(self, node):
        log_n = math.log(node.visits)
        best_action, best_score = None, -math.inf
        for action, child in node.children.items():
            score = child.value / child.visits + self.exploration * math.sqrt(log_n / child.visits)
            if score > best_score:
                best_action, best_score = action, score
        return best_action

    def _reward(self, state, action):
        """Take one step on `state` and return its immediate reward."""
        ate = state.step(action)
        if state.won:
            return 10.0
        if not state.alive:
            return -1.0
        return 1.0 if ate else 0.0

    def _rollout(self, state):
        """Play ahead with a greedy-but-safe policy, then score the final position."""
        total = 0.0
        discount = 1.0
        for _ in range(self.rollout_depth):
            if not state.alive:
                return total
            total += discount * self._reward(state, self._rollout_policy(state))
            discount *= self.gamma
        if not state.alive:
            return total
        return total + discount * self._evaluate(state)

    def _rollout_policy(self, state):
        actions = state.legal_actions()
        safe = [a for a in actions if state.is_safe(a)]
        if not safe:
            return actions[0]
        if self.rng.random() < 0.2:
            return self.rng.choice(safe)
        food_r, food_c = state.food
        return min(safe, key=lambda a: abs(state.next_head(a)[0] - food_r) + abs(state.next_head(a)[1] - food_c))

    def _evaluate(self, state):
        """Heuristic value of a position where the rollout stopped while still alive."""
        n = state.board_size
        head_r, head_c = state.snake[0]
        food_r, food_c = state.food
        closeness = 1.0 - (abs(head_r - food_r) + abs(head_c - food_c)) / (2 * n)
        # Heavily penalise positions where the snake has boxed itself in.
        if self.safe:
            from astar import tail_reachable
            trapped = 0.0 if tail_reachable(list(state.snake), n) else -0.5
        else:
            trapped = -0.5 if state.reachable_area() < len(state.snake) else 0.0
        return 0.3 * closeness + trapped
