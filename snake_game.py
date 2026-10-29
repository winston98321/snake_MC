import os
import sys
import random

import numpy as np

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
from pygame import mixer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def asset(*parts):
    return os.path.join(BASE_DIR, *parts)


class SnakeGame:
    def __init__(self, seed=0, board_size=15, silent_mode=True):
        self.board_size = board_size
        self.grid_size = self.board_size ** 2
        self.cell_size = 40
        self.width = self.height = self.board_size * self.cell_size

        self.border_size = 20
        self.display_width = self.width + 2 * self.border_size
        self.display_height = self.height + 2 * self.border_size + 40

        self.silent_mode = silent_mode
        if not silent_mode:
            pygame.init()
            pygame.display.set_caption("MCTS Snake Game")
            self.screen = pygame.display.set_mode((self.display_width, self.display_height))
            self.font = pygame.font.Font(None, 36)

            # Load sound effects
            mixer.init()
            self.sound_start = mixer.Sound(asset("sound", "start.mp3"))
            self.sound_eat = mixer.Sound(asset("sound", "eat.mp3"))
            self.sound_game_over = mixer.Sound(asset("sound", "game_over.mp3"))
            self.sound_victory = mixer.Sound(asset("sound", "victory.wav"))

            # Load images once instead of every frame
            self.food_image = pygame.image.load(asset("image", "ham.png"))
            self.head_images = {
                "UP": pygame.image.load(asset("image", "snake_u.png")),
                "DOWN": pygame.image.load(asset("image", "snake_d.png")),
                "LEFT": pygame.image.load(asset("image", "snake_l.png")),
                "RIGHT": pygame.image.load(asset("image", "snake_r.png")),
            }
        else:
            self.screen = None
            self.font = None

        self.snake = None
        self.non_snake = None

        self.direction = None
        self.score = 0
        self.food = None
        self.seed_value = seed

        random.seed(seed) # Set random seed.

        self.reset()

    def reset(self):
        self.snake = [(self.board_size // 2 + i, self.board_size // 2) for i in range(1, -2, -1)] # Initialize the snake with three cells in (row, column) format.
        self.non_snake = set([(row, col) for row in range(self.board_size) for col in range(self.board_size) if (row, col) not in self.snake]) # Initialize the non-snake cells.
        self.direction = "DOWN" # Snake starts downward in each round
        self.food = self._generate_food()
        self.score = 0

    def step(self, action):
        self._update_direction(action) # Update direction based on action.

        # Move snake based on current action.
        row, col = self.snake[0]
        if self.direction == "UP":
            row -= 1
        elif self.direction == "DOWN":
            row += 1
        elif self.direction == "LEFT":
            col -= 1
        elif self.direction == "RIGHT":
            col += 1

        # Check if snake eats food.
        if (row, col) == self.food: # If snake eats food, it won't pop the last cell. The food grid will be taken by snake later, no need to update board vacancy matrix.
            food_obtained = True
            self.score += 1 # Add 1 points to the score when food is eaten.
            if not self.silent_mode:
                self.sound_eat.play()
        else:
            food_obtained = False
            self.non_snake.add(self.snake.pop()) # Pop the last cell of the snake and add it to the non-snake set.

        # Check if snake collided with itself or the wall
        done = (
            (row, col) in self.snake
            or row < 0
            or row >= self.board_size
            or col < 0
            or col >= self.board_size
        )

        if not done:
            self.snake.insert(0, (row, col))
            self.non_snake.remove((row, col))

        elif not self.silent_mode: # If game is over and the game is not in silent mode, play game over sound effect.
            if len(self.snake) < self.grid_size:
                self.sound_game_over.play()
            else:
                self.sound_victory.play()

        # Add new food after snake movement completes.
        if food_obtained:
            self.food = self._generate_food()

        info ={
            "snake_size": len(self.snake),
            "snake_head_pos": np.array(self.snake[0]),
            "prev_snake_head_pos": np.array(self.snake[1]),
            "food_pos": np.array(self.food),
            "food_obtained": food_obtained
        }

        return done, info

    # 0: UP, 1: DOWN, 2: LEFT, 3: RIGHT
    def _update_direction(self, action):

        if action == 0:
            if self.direction != "DOWN":
                self.direction = "UP"
        elif action == 1:
            if self.direction != "UP":
                self.direction = "DOWN"
        elif action == 2:
            if self.direction != "RIGHT":
                self.direction = "LEFT"
        elif action == 3:
            if self.direction != "LEFT":
                self.direction = "RIGHT"

    def _generate_food(self):
        if len(self.non_snake) > 0:
            food = random.choice(sorted(self.non_snake))
        else: # If the snake occupies the entire board, no need to generate new food and just default to (0, 0).
            food = (0, 0)
        return food

    def draw_score(self):
        score_text = self.font.render(f"Score: {self.score}", True, (255, 0, 0))
        self.screen.blit(score_text, (self.border_size, self.height + 2 * self.border_size))

    def draw_welcome_screen(self):
        title_text = self.font.render("MCTS SNAKE GAME", True, (255, 0, 0))
        start_button_text = "START THE GAME"

        self.screen.fill((0, 0, 0))
        self.screen.blit(title_text, (self.display_width // 2 - title_text.get_width() // 2, self.display_height // 4))
        self.draw_button_text(start_button_text, (self.display_width // 2, self.display_height // 2))
        pygame.display.flip()

    def draw_game_over_screen(self):
        game_over_text = self.font.render("GAME OVER", True, (255, 0, 0))
        final_score_text = self.font.render(f"SCORE: {self.score}", True, (255, 0, 0))
        retry_button_text = "RETRY"

        self.screen.fill((0, 0, 0))
        self.screen.blit(game_over_text, (self.display_width // 2 - game_over_text.get_width() // 2, self.display_height // 4))
        self.screen.blit(final_score_text, (self.display_width // 2 - final_score_text.get_width() // 2, self.display_height // 4 + final_score_text.get_height() + 10))
        self.draw_button_text(retry_button_text, (self.display_width // 2, self.display_height // 2))
        pygame.display.flip()

    def draw_button_text(self, button_text_str, pos, hover_color=(255, 255, 255), normal_color=(100, 100, 100)):
        mouse_pos = pygame.mouse.get_pos()
        button_text = self.font.render(button_text_str, True, normal_color)
        text_rect = button_text.get_rect(center=pos)

        if text_rect.collidepoint(mouse_pos):
            colored_text = self.font.render(button_text_str, True, hover_color)
        else:
            colored_text = self.font.render(button_text_str, True, normal_color)

        self.screen.blit(colored_text, text_rect)

    def draw_countdown(self, number):
        countdown_text = self.font.render(str(number), True, (255, 255, 255))
        self.screen.blit(countdown_text, (self.display_width // 2 - countdown_text.get_width() // 2, self.display_height // 2 - countdown_text.get_height() // 2))
        pygame.display.flip()

    def is_mouse_on_button(self, button_text):
        mouse_pos = pygame.mouse.get_pos()
        text_rect = button_text.get_rect(
            center=(
                self.display_width // 2,
                self.display_height // 2,
            )
        )
        return text_rect.collidepoint(mouse_pos)

    def render(self):
        self.screen.fill((0, 0, 0))

        # Draw border
        pygame.draw.rect(self.screen, (0, 0, 255), (self.border_size - 2, self.border_size - 2, self.width + 4, self.height + 4), 2)

        # Draw snake
        self.draw_snake()

        # Draw food
        if len(self.snake) < self.grid_size: # If the snake occupies the entire board, don't draw food.
            r, c = self.food
            food_rect = self.food_image.get_rect(center=(c * self.cell_size + self.border_size + self.cell_size // 2,
                                                         r * self.cell_size + self.border_size + self.cell_size // 2))
            self.screen.blit(self.food_image, food_rect)

        # Draw score
        self.draw_score()

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

    def draw_snake(self):
        # Draw the body (color gradient)
        color_list = np.linspace(255, 0, len(self.snake), dtype=np.uint8)
        body_radius = 5
        for i, (r, c) in enumerate(self.snake[1:], start=1):
            body_x = c * self.cell_size + self.border_size
            body_y = r * self.cell_size + self.border_size
            color = (0, 255, 0) if i == len(self.snake) - 1 else (100, color_list[i], 0) # Tail is bright green.
            pygame.draw.rect(self.screen, color, (body_x, body_y, self.cell_size, self.cell_size), border_radius=body_radius)

        # Draw the head, shifted slightly toward the direction it is facing
        head_r, head_c = self.snake[0]
        center_x = head_c * self.cell_size + self.border_size + self.cell_size // 2
        center_y = head_r * self.cell_size + self.border_size + self.cell_size // 2
        offset_x, offset_y = {"UP": (0, -10), "DOWN": (0, 10), "LEFT": (-10, 0), "RIGHT": (10, 0)}[self.direction]
        head = self.head_images[self.direction]
        self.screen.blit(head, head.get_rect(center=(center_x + offset_x, center_y + offset_y)))


def run_headless(agent, games, seed, board_size):
    """Let the MCTS agent play without a window and print the scores."""
    import time

    scores = []
    for g in range(games):
        game = SnakeGame(seed=seed + g, board_size=board_size, silent_mode=True)
        steps, steps_since_food = 0, 0
        start = time.time()
        while True:
            done, info = game.step(agent.choose_action(game))
            steps += 1
            steps_since_food = 0 if info["food_obtained"] else steps_since_food + 1
            if done:
                result = "won" if len(game.snake) >= game.grid_size else "died"
                break
            if steps_since_food > 4 * game.grid_size: # Stop if the snake just loops forever.
                result = "looping"
                break
        scores.append(game.score)
        print(f"Game {g + 1}: score={game.score} steps={steps} ({result}, {time.time() - start:.1f}s)")
    print(f"Average score over {games} games: {sum(scores) / len(scores):.1f}")


if __name__ == "__main__":
    import argparse
    import time

    from mcts import MCTSAgent

    parser = argparse.ArgumentParser(description="Snake game controlled by Monte Carlo Tree Search.")
    parser.add_argument("--iterations", type=int, default=300, help="MCTS iterations per move.")
    parser.add_argument("--time-limit", type=float, default=0.2, help="Max thinking time per move in seconds (0 = no limit).")
    parser.add_argument("--rollout-depth", type=int, default=30, help="Steps simulated in each rollout.")
    parser.add_argument("--interval", type=float, default=0.1, help="Minimum seconds between snake moves.")
    parser.add_argument("--board-size", type=int, default=15)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--headless", action="store_true", help="Run without a window and print scores.")
    parser.add_argument("--games", type=int, default=1, help="Number of games in headless mode.")
    args = parser.parse_args()

    seed = args.seed if args.seed is not None else random.randint(0, int(1e9))
    agent = MCTSAgent(iterations=args.iterations, time_limit=args.time_limit or None,
                      rollout_depth=args.rollout_depth, seed=seed)

    if args.headless:
        run_headless(agent, args.games, seed, args.board_size)
        sys.exit()

    game = SnakeGame(seed=seed, board_size=args.board_size, silent_mode=False)
    game.font = pygame.font.Font(None, 50)

    game_state = "welcome"

    # Two hidden button for start and retry click detection
    start_button = game.font.render("START", True, (0, 255, 0))
    retry_button = game.font.render("RETRY", True, (0, 255, 0))

    start_time = time.time()

    while True:

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if game_state in ("welcome", "game_over") and event.type == pygame.MOUSEBUTTONDOWN:
                button = start_button if game_state == "welcome" else retry_button
                if game.is_mouse_on_button(button):
                    for i in range(3, 0, -1):
                        game.screen.fill((0, 0, 0))
                        game.draw_countdown(i)
                        game.sound_start.play()
                        pygame.time.wait(1000)
                    if game_state == "game_over":
                        game.reset()
                    game_state = "running"

        if game_state == "welcome":
            game.draw_welcome_screen()

        if game_state == "game_over":
            game.draw_game_over_screen()

        if game_state == "running":
            if time.time() - start_time >= args.interval:
                action = agent.choose_action(game) # MCTS picks the next move.
                done, _ = game.step(action)
                game.render()
                start_time = time.time()

                if done:
                    game_state = "game_over"

        pygame.time.wait(1)
