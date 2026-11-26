import pygame
import sys

# Initialize Pygame
pygame.init()

# Screen settings
WIDTH, HEIGHT = 800, 600
FPS = 60
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("rishi likes men")
clock = pygame.time.Clock()

# Colors
SKY_BLUE = (135, 206, 235)
GREEN = (50, 205, 50)
RED = (220, 20, 60)
GOLD = (255, 215, 0)
WHITE = (255, 255, 255)

# Physics constants
GRAVITY = 0.8
JUMP_STRENGTH = -15
PLAYER_SPEED = 5


class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 40, 50)
        self.vel_y = 0
        self.on_ground = False

    def move(self, platforms):
        keys = pygame.key.get_pressed()
        dx = 0

        # Horizontal input
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -PLAYER_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = PLAYER_SPEED

        # Jump input
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
            self.vel_y = JUMP_STRENGTH
            self.on_ground = False

        # Apply horizontal movement & check horizontal collisions
        self.rect.x += dx
        self.rect.x = max(0, min(WIDTH - self.rect.width, self.rect.x))  # Keep on screen
        for platform in platforms:
            if self.rect.colliderect(platform):
                if dx > 0:
                    self.rect.right = platform.left
                elif dx < 0:
                    self.rect.left = platform.right

        # Apply gravity & vertical movement
        self.vel_y += GRAVITY
        self.rect.y += self.vel_y
        self.on_ground = False

        # Check vertical collisions
        for platform in platforms:
            if self.rect.colliderect(platform):
                if self.vel_y > 0:  # Falling down
                    self.rect.bottom = platform.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:  # Jumping into bottom of platform
                    self.rect.top = platform.bottom
                    self.vel_y = 0

    def draw(self, surface):
        pygame.draw.rect(surface, RED, self.rect)


def main():
    player = Player(100, 450)

    # Define platforms (x, y, width, height)
    platforms = [
        pygame.Rect(0, HEIGHT - 40, WIDTH, 40),   # Ground
        pygame.Rect(150, 450, 150, 20),
        pygame.Rect(400, 360, 150, 20),
        pygame.Rect(200, 260, 150, 20),
        pygame.Rect(500, 180, 180, 20),
    ]

    # Define collectible coins
    coins = [
        pygame.Rect(215, 410, 20, 20),
        pygame.Rect(465, 320, 20, 20),
        pygame.Rect(265, 220, 20, 20),
        pygame.Rect(580, 140, 20, 20),
    ]

    score = 0
    font = pygame.font.SysFont(None, 36)

    # Main game loop
    while True:
        clock.tick(FPS)

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # Update player
        player.move(platforms)

        # Check coin collection
        for coin in coins[:]:
            if player.rect.colliderect(coin):
                coins.remove(coin)
                score += 1

        # Draw everything
        screen.fill(SKY_BLUE)

        for platform in platforms:
            pygame.draw.rect(screen, GREEN, platform)

        for coin in coins:
            pygame.draw.ellipse(screen, GOLD, coin)

        player.draw(screen)

        # Draw UI
        score_text = font.render(f"Coins: {score}/4", True, WHITE)
        screen.blit(score_text, (15, 15))

        if len(coins) == 0:
            win_text = font.render("You collected all coins!", True, WHITE)
            screen.blit(win_text, (WIDTH // 2 - win_text.get_width() // 2, 60))

        pygame.display.flip()


if __name__ == "__main__":
    main()
