import sys

import pygame

from enemyai import Enemy, Navigation
from levels import create_levels
from physics import Body


WIDTH, HEIGHT = 800, 600
FPS = 60
PLAYER_SPEED = 5
SKY_BLUE = (135, 206, 235)
GREEN = (50, 205, 50)
RED = (220, 20, 60)
GOLD = (255, 215, 0)
WHITE = (255, 255, 255)


class Player(Body):
    def __init__(self, x, y):
        super().__init__(x, y, 40, 50)

    def move(self, platforms, world_width, keys):
        dx = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -PLAYER_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = PLAYER_SPEED
        jump = keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]
        self.step(dx, jump, platforms, world_width)

    def draw(self, surface, camera):
        super().draw(surface, RED, camera)


class Game:
    def __init__(self):
        self.levels = create_levels()
        self.navigation_cache = {}
        self.restart()

    def restart(self):
        self.total_coins = 0
        self.completed = False
        self.load_level(0)

    def load_level(self, index):
        self.level_index = index
        self.level = self.levels[index]
        self.coins = [coin.copy() for coin in self.level.coin_spawns]
        self.player = Player(*self.level.player_spawn)
        self.player.on_ground = True
        if index not in self.navigation_cache:
            self.navigation_cache[index] = Navigation(
                self.level.platforms, self.level.width, self.level.height,
            )
        self.enemy = Enemy(self.navigation_cache[index], self.level.enemy_spawn)

    def update(self, keys):
        if self.completed:
            return
        self.player.move(self.level.platforms, self.level.width, keys)
        self.enemy.update(self.player)
        if (self.player.rect.colliderect(self.enemy.rect)
                or self.player.rect.top >= self.level.height):
            self.restart()
            return
        for coin in self.coins[:]:
            if self.player.rect.colliderect(coin):
                self.coins.remove(coin)
                self.total_coins += 1
        if not self.coins and self.player.rect.colliderect(self.level.exit):
            if self.level_index + 1 < len(self.levels):
                self.load_level(self.level_index + 1)
            else:
                self.completed = True

    def camera(self):
        return (
            max(0, min(self.level.width - WIDTH, self.player.rect.centerx - WIDTH // 2)),
            max(0, min(self.level.height - HEIGHT, self.player.rect.centery - HEIGHT // 2)),
        )

    def draw(self, screen, font):
        camera = self.camera()
        screen.fill(SKY_BLUE)
        for platform in self.level.platforms:
            pygame.draw.rect(screen, GREEN, platform.move(-camera[0], -camera[1]))
        for coin in self.coins:
            pygame.draw.ellipse(screen, GOLD, coin.move(-camera[0], -camera[1]))
        exit_color = GOLD if not self.coins else (90, 90, 90)
        pygame.draw.rect(screen, exit_color, self.level.exit.move(-camera[0], -camera[1]))
        self.player.draw(screen, camera)
        self.enemy.draw(screen, camera)

        collected = len(self.level.coin_spawns) - len(self.coins)
        lines = [
            f"Level {self.level_index + 1}/{len(self.levels)}: {self.level.name}",
            f"Coins: {collected}/{len(self.level.coin_spawns)}   Total: {self.total_coins}",
            "Exit unlocked! Head right." if not self.coins else "Collect every coin to unlock the exit.",
        ]
        if self.completed:
            lines.append("All 11 levels complete! Press R to play again.")
        for index, text in enumerate(lines):
            label = font.render(text, True, WHITE)
            shadow = font.render(text, True, (30, 30, 30))
            screen.blit(shadow, (17, 17 + index * 30))
            screen.blit(label, (15, 15 + index * 30))


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Simple Platformer")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 28)
    game = Game()
    while True:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r and game.completed:
                game.restart()
        game.update(pygame.key.get_pressed())
        game.draw(screen, font)
        pygame.display.flip()


if __name__ == "__main__":
    main()
