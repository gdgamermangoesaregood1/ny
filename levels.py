from dataclasses import dataclass

import pygame


@dataclass
class Level:
    name: str
    width: int
    height: int
    platforms: list[pygame.Rect]
    coin_spawns: list[pygame.Rect]
    player_spawn: tuple[int, int]
    enemy_spawn: tuple[int, int]
    exit: pygame.Rect


def create_levels():
    names = [
        "First Steps", "Tall Towers", "Sky Gardens", "Zigzag Heights",
        "Cloud Climb", "High Bridges", "Purple Peaks", "Long Way Up",
        "Skyline Run", "Summit Chase", "Final Ascent",
    ]
    levels = []
    for index, name in enumerate(names):
        width = 2400 + index * 160
        height = 1200 + index * 40
        ground_y = height - 60
        platforms = [pygame.Rect(0, ground_y, width, 60)]
        coins = []

        if index == 0:
            # Keep the original platforms, with stepping stones for the enemy.
            for x, rise, platform_width in [
                (150, 110, 150), (290, 155, 150), (400, 200, 150),
                (200, 300, 150), (440, 340, 190), (500, 380, 180),
            ]:
                platforms.append(pygame.Rect(x, ground_y - rise, platform_width, 20))
            for platform_index in (1, 3, 4, 6):
                platform = platforms[platform_index]
                coins.append(pygame.Rect(platform.centerx - 10, platform.top - 30, 20, 20))
            bases = [900, 1450, 2000]
        else:
            tower_count = 3 + index // 3
            bases = [
                180 + tower * (width - 600) // (tower_count - 1)
                for tower in range(tower_count)
            ]

        tiers = 8 + index % 4
        rise = 75 + (index % 3) * 5
        for tower, base in enumerate(bases):
            direction = 1 if tower % 2 == 0 else -1
            for tier in range(tiers):
                x = base + direction * (tier % 2) * 100
                platform = pygame.Rect(x, ground_y - (tier + 1) * rise, 200, 20)
                platforms.append(platform)
                if tier % 3 == 2 or tier == tiers - 1:
                    coins.append(pygame.Rect(platform.centerx - 10, platform.top - 30, 20, 20))

        levels.append(Level(
            name, width, height, platforms, coins,
            (80, ground_y - 50), (500, ground_y - 40),
            pygame.Rect(width - 100, ground_y - 80, 50, 80),
        ))
    return levels
