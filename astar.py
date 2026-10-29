"""
A* search controller for the snake game.

Every move, the agent plans the shortest path from the head to the food with
A* (cost = steps taken, heuristic = Manhattan distance). The search is
time-aware: body segment k (0 = head) leaves its cell after len(snake) - k
steps, so the path may pass through cells the tail will have vacated.

Two variants:
    plain - follow the A* path to the food; if there is none, move to the
            neighbour with the most free space.
    safe  - only follow the path if, after eating, the snake can still reach
            its own tail (so it cannot trap itself). Otherwise wander in a
            direction that keeps the tail reachable until the food is safe.
"""

import heapq
import random

from mcts import MOVES, SnakeState


def astar(snake, goal, board_size):
    """Shortest path (list of cells, excluding the head) from snake[0] to goal, or None."""
    length = len(snake)
    index = {cell: k for k, cell in enumerate(snake)}
    start = snake[0]

    def h(cell):
        return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])

    open_heap = [(h(start), 0, start)]
    came_from = {}
    best_g = {start: 0}
    while open_heap:
        _, g, cell = heapq.heappop(open_heap)
        if cell == goal:
            path = [cell]
            while path[-1] in came_from:
                path.append(came_from[path[-1]])
            return path[-2::-1]  # Drop the start cell and put it in head-to-goal order.
        if g > best_g[cell]:
            continue
        for dr, dc in MOVES.values():
            nxt = (cell[0] + dr, cell[1] + dc)
            if not (0 <= nxt[0] < board_size and 0 <= nxt[1] < board_size):
                continue
            k = index.get(nxt)
            if k is not None and g + 1 < length - k:  # That body segment has not moved away yet.
                continue
            if g + 1 < best_g.get(nxt, float("inf")):
                best_g[nxt] = g + 1
                came_from[nxt] = cell
                heapq.heappush(open_heap, (g + 1 + h(nxt), g + 1, nxt))
    return None


def tail_reachable(snake, board_size):
    return astar(snake, snake[-1], board_size) is not None


def snake_after_path(snake, path):
    """Body of the snake after following `path`, eating food at its last cell."""
    return (path[::-1] + snake)[:len(snake) + 1]


class AStarAgent:
    def __init__(self, safe=True):
        self.safe = safe

    def choose_action(self, game):
        n = game.board_size
        snake = list(game.snake)
        head = snake[0]
        food = game.food

        path = astar(snake, food, n)
        if path and (not self.safe or tail_reachable(snake_after_path(snake, path), n)):
            return self._action(head, path[0])

        state = SnakeState.from_game(game, random.Random(0))
        safe_actions = [a for a in state.legal_actions() if state.is_safe(a)]
        if not safe_actions:
            return state.direction

        if self.safe:
            # Stall: keep the tail reachable and stay away from the food until it is safe to eat.
            def body_after(action):
                nxt = state.next_head(action)
                return [nxt] + (snake if nxt == food else snake[:-1])
            options = [a for a in safe_actions if tail_reachable(body_after(a), n)]
            if options:
                return max(options, key=lambda a: self._distance(state.next_head(a), food))

        # Last resort: move where there is the most room.
        def room(action):
            next_state = state.copy()
            next_state.step(action)
            return next_state.reachable_area() if next_state.alive else -1
        return max(safe_actions, key=room)

    @staticmethod
    def _action(head, cell):
        delta = (cell[0] - head[0], cell[1] - head[1])
        return next(a for a, move in MOVES.items() if move == delta)

    @staticmethod
    def _distance(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
