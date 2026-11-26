import pygame


class Enemy:
    def __init__(self, platform, x, screen_width):
        self.rect = pygame.Rect(x, platform.top - 40, 40, 40)
        self.screen_width = screen_width
        self.speed = 3
        self.vel_y = 0
        self.on_ground = True

    def update(self, player, platforms):
        distance = player.rect.centerx - self.rect.centerx
        dx = max(-self.speed, min(self.speed, distance))
        self.rect.x += dx
        self.rect.x = max(0, min(self.screen_width - self.rect.width, self.rect.x))

        blocked = False
        for platform in platforms:
            if self.rect.colliderect(platform):
                if dx > 0:
                    self.rect.right = platform.left
                    blocked = True
                elif dx < 0:
                    self.rect.left = platform.right
                    blocked = True

        if self.on_ground and (player.rect.bottom < self.rect.bottom or blocked):
            self.vel_y = -15
            self.on_ground = False

        self.vel_y += 0.8
        self.rect.y += round(self.vel_y)
        self.on_ground = False

        for platform in platforms:
            if self.rect.colliderect(platform):
                if self.vel_y > 0:
                    self.rect.bottom = platform.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.rect.top = platform.bottom
                    self.vel_y = 0

    def draw(self, surface):
        pygame.draw.rect(surface, (100, 40, 140), self.rect)

