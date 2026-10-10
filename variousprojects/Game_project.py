import pygame #библиотека для игр
import random #
import math

# Инициализация Pygame
pygame.init()

# Константы
WIDTH, HEIGHT = 800, 600
FPS = 60
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)

# Создание окна
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("🚀 Космическая ракета")
clock = pygame.time.Clock()

class Rocket:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT // 2
        self.speed = 5
        self.angle = 0  # угол поворота в градусах
        self.score = 0
        self.lives = 3
        self.invincible = 0  # временная неуязвимость после столкновения
        
    def update(self, keys):
        # Поворот
        if keys[pygame.K_UP]:
            self.y -= self.speed
        if keys[pygame.K_DOWN]:
            self.y += self.speed
        if keys[pygame.K_LEFT]:
            self.x -= self.speed
        if keys[pygame.K_RIGHT]:
            self.x += self.speed
        
        # Движение вперёд (вверх)
        if keys[pygame.K_UP]:
            self.y -= self.speed
        
        # Движение назад (вниз)
        if keys[pygame.K_DOWN]:
            self.y += self.speed
        
        # Границы экрана (телепортация)
        if self.x < -20: self.x = WIDTH + 20
        if self.x > WIDTH + 20: self.x = -20
        if self.y < -20: self.y = HEIGHT + 20
        if self.y > HEIGHT + 20: self.y = -20
        
        # Уменьшение неуязвимости
        if self.invincible > 0:
            self.invincible -= 1
    
    def draw(self):
        # Создаём поверхность для ракеты
        rocket_surface = pygame.Surface((40, 60), pygame.SRCALPHA)
        
        # Рисуем ракету (треугольник)
        points = [(20, 0), (5, 45), (20, 35), (35, 45)]
        pygame.draw.polygon(rocket_surface, WHITE, points)
        
        # Огонь из двигателя
        if random.random() < 0.5:
            fire_points = [(15, 45), (25, 45), (20, 60)]
            pygame.draw.polygon(rocket_surface, ORANGE, fire_points)
        
        # Поворачиваем ракету
        rotated_rocket = pygame.transform.rotate(rocket_surface, self.angle)
        rect = rotated_rocket.get_rect(center=(self.x, self.y))
        
        # Мигание при неуязвимости
        if self.invincible == 0 or random.random() < 0.7:
            screen.blit(rotated_rocket, rect)
        
        # Отрисовка двигателя
        rad = math.radians(self.angle)
        engine_x = self.x - 30 * math.cos(rad)
        engine_y = self.y + 30 * math.sin(rad)
        
        if random.random() < 0.3:
            pygame.draw.circle(screen, YELLOW, (int(engine_x), int(engine_y)), 5)

class Asteroid:
    def __init__(self):
        self.x = random.choice([-50, WIDTH + 50])
        self.y = random.randint(0, HEIGHT)
        self.size = random.randint(15, 40)
        self.speed_x = random.uniform(-3, 3)
        self.speed_y = random.uniform(-3, 3)
        self.rotation = random.randint(0, 360)
        self.rotation_speed = random.uniform(-2, 2)
        
        # Направление к центру
        if self.x < 0:
            self.speed_x = random.uniform(1, 3)
        else:
            self.speed_x = random.uniform(-3, -1)
    
    def update(self):
        self.x += self.speed_x
        self.y += self.speed_y
        self.rotation += self.rotation_speed
        
        # Удаление за пределами экрана
        if self.x < -100 or self.x > WIDTH + 100:
            return False
        if self.y < -100 or self.y > HEIGHT + 100:
            return False
        return True
    
    def draw(self):
        # Создаём поверхность для астероида
        asteroid_surface = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        center = (self.size, self.size)
        
        # Рисуем неровный астероид
        points = []
        for i in range(8):
            angle = i * (2 * math.pi / 8)
            r = self.size * random.uniform(0.7, 1.0)
            x = center[0] + r * math.cos(angle)
            y = center[1] + r * math.sin(angle)
            points.append((x, y))
        
        pygame.draw.polygon(asteroid_surface, (150, 150, 150), points)
        pygame.draw.polygon(asteroid_surface, (100, 100, 100), points, 3)
        
        # Поворачиваем астероид
        rotated_asteroid = pygame.transform.rotate(asteroid_surface, self.rotation)
        rect = rotated_asteroid.get_rect(center=(self.x, self.y))
        screen.blit(rotated_asteroid, rect)

class Star:
    def __init__(self):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        self.size = random.randint(1, 3)
        self.twinkle_speed = random.uniform(0.01, 0.05)
        self.twinkle = random.uniform(0, 2 * math.pi)
    
    def update(self):
        self.twinkle += self.twinkle_speed
    
    def draw(self):
        brightness = abs(math.sin(self.twinkle)) * 255
        color = (int(brightness), int(brightness), int(brightness))
        pygame.draw.circle(screen, color, (self.x, self.y), self.size)

def check_collision(rocket, asteroid):
    """Проверка столкновения ракеты с астероидом"""
    distance = math.sqrt((rocket.x - asteroid.x)**2 + (rocket.y - asteroid.y)**2)
    return distance < asteroid.size + 20

def game_over_screen(final_score):
    """Экран окончания игры"""
    screen.fill(BLACK)
    
    font_large = pygame.font.Font(None, 72)
    font_small = pygame.font.Font(None, 36)
    
    # Заголовок
    title = font_large.render("ИГРА ОКОНЧЕНА", True, RED)
    title_rect = title.get_rect(center=(WIDTH//2, HEIGHT//2 - 50))
    screen.blit(title, title_rect)
    
    # Счёт
    score_text = font_small.render(f"Ваш счёт: {final_score}", True, WHITE)
    score_rect = score_text.get_rect(center=(WIDTH//2, HEIGHT//2 + 30))
    screen.blit(score_text, score_rect)
    
    # Подсказка
    hint = font_small.render("Нажмите SPACE для новой игры", True, YELLOW)
    hint_rect = hint.get_rect(center=(WIDTH//2, HEIGHT//2 + 80))
    screen.blit(hint, hint_rect)
    
    pygame.display.flip()
    
    # Ожидание новой игры
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    waiting = False

def main():
    # Создание объектов
    rocket = Rocket()
    asteroids = []
    stars = [Star() for _ in range(100)]
    
    # Таймеры
    asteroid_timer = 0
    asteroid_spawn_rate = 60  # кадров между появлением астероидов
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Обновление
        keys = pygame.key.get_pressed()
        rocket.update(keys)
        
        # Обновление звёзд
        for star in stars:
            star.update()
        
        # Создание астероидов
        asteroid_timer += 1
        if asteroid_timer >= asteroid_spawn_rate:
            asteroids.append(Asteroid())
            asteroid_timer = 0
            # Увеличиваем сложность
            asteroid_spawn_rate = max(20, asteroid_spawn_rate - 1)
        
        # Обновление астероидов
        asteroids = [a for a in asteroids if a.update()]
        
        # Проверка столкновений
        if rocket.invincible == 0:
            for asteroid in asteroids:
                if check_collision(rocket, asteroid):
                    rocket.lives -= 1
                    rocket.invincible = 60  # 1 секунда неуязвимости
                    if rocket.lives <= 0:
                        game_over_screen(rocket.score)
                        # Сброс игры
                        rocket = Rocket()
                        asteroids.clear()
                        asteroid_spawn_rate = 60
                        break
        
        # Увеличение счёта за выживание
        rocket.score += 0.01
        
        # Отрисовка
        screen.fill(BLACK)
        
        # Звёзды
        for star in stars:
            star.draw()
        
        # Астероиды
        for asteroid in asteroids:
            asteroid.draw()
        
        # Ракета
        rocket.draw()
        
        # Интерфейс
        font = pygame.font.Font(None, 36)
        
        # Счёт
        score_text = font.render(f"Счёт: {int(rocket.score)}", True, WHITE)
        screen.blit(score_text, (10, 10))
        
        # Жизни
        lives_text = font.render(f"Жизни: {'❤️' * rocket.lives}", True, RED)
        screen.blit(lives_text, (10, 50))
        
        # Подсказка
        if rocket.score < 5:
            hint = font.render("↑ Вниз | ↓ Вверх | ← → Поворот", True, YELLOW)
            hint_rect = hint.get_rect(center=(WIDTH//2, HEIGHT - 30))
            screen.blit(hint, hint_rect)
        
        pygame.display.flip()
        clock.tick(FPS)
    
    pygame.quit()

if __name__ == "__main__":
    main()