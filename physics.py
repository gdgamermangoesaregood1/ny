import pygame


GRAVITY = 0.8
JUMP_STRENGTH = -15


class Body:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.vel_y = 0.0
        self.on_ground = False

    def step(self, dx, jump, platforms, world_width):
        if jump and self.on_ground:
            self.vel_y = JUMP_STRENGTH
            self.on_ground = False

        self.rect.x += dx
        self.rect.x = max(0, min(world_width - self.rect.width, self.rect.x))
        blocked = False
        for index in self.rect.collidelistall(platforms):
            platform = platforms[index]
            if dx > 0:
                self.rect.right = platform.left
                blocked = True
            elif dx < 0:
                self.rect.left = platform.right
                blocked = True

        previous_top = self.rect.top
        previous_bottom = self.rect.bottom
        self.vel_y += GRAVITY
        self.rect.y += round(self.vel_y)
        self.on_ground = False
        # Sweep the feet/head so fast falls cannot tunnel through thin platforms.
        overlapping = [
            platform for platform in platforms
            if self.rect.right > platform.left and self.rect.left < platform.right
        ]
        if self.vel_y > 0:
            crossed = [
                platform.top for platform in overlapping
                if previous_bottom <= platform.top <= self.rect.bottom
            ]
            if crossed:
                self.rect.bottom = min(crossed)
                self.vel_y = 0.0
                self.on_ground = True
        elif self.vel_y < 0:
            crossed = [
                platform.bottom for platform in overlapping
                if self.rect.top <= platform.bottom <= previous_top
            ]
            if crossed:
                self.rect.top = max(crossed)
                self.vel_y = 0.0
        return blocked

    def draw(self, surface, color, camera):
        pygame.draw.rect(surface, color, self.rect.move(-camera[0], -camera[1]))
