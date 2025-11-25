import pygame
import time
import json


def load_config(path="config.json"):
    'Загружает конфигурацию из файла config.json'
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print("Ошибка чтения файла с конфигурацией:", e)
        return {}


class Field:
    'Методы для работы с полем'
    def __init__(self, path, H, W):
        self.H = H # высота
        self.W = W # ширина
        self.grid = self.read_field(path) # изначальное состояние поля

    def read_field(self, path):
        'Читает изначальное состояние поля из файла'
        field = []
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                field.append([1 if c == "O" else 0 for c in line])
        return field

    def count_neighbours(self, x, y):
        'Считает количество живых соседей вокруг клетки (x, y)'
        n = 0
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == dy == 0: # саму себя не считаем
                    continue
                nx = (x + dx) % self.W
                ny = (y + dy) % self.H
                n += self.grid[ny][nx]
        return n

    def next_generation(self, survive, birth):
        'Вычисляет следующее состояние поля'
        new = [[0] * self.W for _ in range(self.H)]
        for y in range(self.H):
            for x in range(self.W):
                n = self.count_neighbours(x, y)
                if self.grid[y][x] == 1:
                    new[y][x] = 1 if n in survive else 0
                else:
                    new[y][x] = 1 if n in birth else 0
        return new

    def is_equal(self, other):
        'Проверяет, равны ли два поля'
        return all(self.grid[y][x] == other[y][x] for y in range(self.H) for x in range(self.W))


class Panel:
    'Методы для работы с панелью'
    def __init__(self, x0, width, color, border_color, patterns):
        self.x0 = x0 # начальная координата панели по X
        self.width = width # ширина 
        self.color = color # цвет 
        self.border_color = border_color # цвет границы 
        self.patterns = patterns # шаблоны для размещения на поле
    
    def draw(self, screen, H, cell_size, selected_pattern):
        'Отрисовывает панель'
        pygame.draw.rect(screen, self.color, (self.x0, 0, self.width, H * cell_size))
        pygame.draw.line(screen, self.border_color, (self.x0, 0), (self.x0, H * cell_size))
        font = pygame.font.SysFont("monospace", 16)
        y = 20 # отступ по Y
        for name in self.patterns:
            color = (255, 255, 255) if name != selected_pattern else (255, 0, 255) # выделение выбранного шаблона
            text = font.render(name, True, color) # превращаем текст в изображение
            screen.blit(text, (self.x0 + 20, y)) # добавляем изображение текста на экран
            y += 40

    def handle_mouse(self, event, field, cell_size, W, H, selected_pattern, dragging):
        'Обрабатывает клики и перетаскивания'
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if mx > W * cell_size:  # клик в панели
                index = (my - 20) // 40 # вычисляем индекс названия фигуры
                names = list(self.patterns.keys())
                if 0 <= index < len(names):
                    selected_pattern = names[index]
                    dragging = True
        elif event.type == pygame.MOUSEBUTTONUP and dragging:
            mx, my = event.pos
            if mx < W * cell_size and selected_pattern:
                gx = mx // cell_size # координата по X на поле
                gy = my // cell_size # координата по Y на поле
                self.place_pattern(field.grid, selected_pattern, gx, gy, H, W)
            dragging = False
        return selected_pattern, dragging

    def place_pattern(self, field, name, gx, gy, H, W):
        'Размещает выбранный шаблон на поле'
        for dx, dy in self.patterns[name]:
            x = (gx + dx) % W
            y = (gy + dy) % H
            field[y][x] = 1


def draw_field(screen, field, H, W, cell_size, bg_color, cell_color, text_color, speed_ms):
    'Отрисовывает текущее состояние поля'
    screen.fill(bg_color)
    for y in range(H):
        for x in range(W):
            if field[y][x]:
                pygame.draw.rect(screen, cell_color, (x * cell_size, y * cell_size, cell_size - 1, cell_size - 1))
    font = pygame.font.SysFont("monospace", 16)
    text = font.render(f"Speed: {speed_ms} ms | A/Z speed, SPACE exit", True, text_color)
    screen.blit(text, (5, H * cell_size - 20))
    pygame.display.flip()


def init_game(cfg):
    'Инициализирует игру и возвращает основные объекты'
    window_width = cfg.get("window_width")
    window_height = cfg.get("window_height")
    cell_size = cfg.get("cell_size")
    panel_width = cfg.get("panel_width")

    H = window_height // cell_size
    W = window_width // cell_size

    field = Field(cfg.get("field_path"), H, W)

    pygame.init()
    screen = pygame.display.set_mode((window_width + panel_width, window_height))
    pygame.display.set_caption("Game of Life")
    clock = pygame.time.Clock()
    
    return screen, clock, field, H, W, cell_size, panel_width


def main():
    cfg = load_config("config.json")

    FPS = cfg.get("fps")
    speed_ms = cfg.get("initial_speed_ms")
    bg_color = tuple(cfg.get("background_color"))
    cell_color = tuple(cfg.get("cell_color"))
    text_color = tuple(cfg.get("text_color"))
    
    rule_name = cfg.get("current_rule")
    rule = cfg["rules"][rule_name]
    survive = rule["survive"]
    birth = rule["birth"]
    
    panel_color = tuple(cfg.get("panel_color"))
    panel_border_color = tuple(cfg.get("panel_border_color"))
    patterns = cfg.get("patterns")

    screen, clock, field, H, W, cell_size, panel_width = init_game(cfg)
    panel = Panel(W * cell_size, panel_width, panel_color, panel_border_color, patterns)

    running = True
    dragging = False
    selected_pattern = None
    last_update = time.time()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    running = False
                elif event.key == pygame.K_a:
                    speed_ms = max(10, speed_ms - 10)
                elif event.key == pygame.K_z:
                    speed_ms = min(2000, speed_ms + 10)

            selected_pattern, dragging = panel.handle_mouse(event, field, cell_size, W, H, selected_pattern, dragging)

        now = time.time()
        if now - last_update >= speed_ms / 1000.0: # переводим миллисекунды в секунды и смотрим, прошло ли столько времени
            new = field.next_generation(survive, birth)
            if field.is_equal(new): # если новое состояние равно старому, останавливаем игру
                running = False
            field.grid = new
            last_update = now

        draw_field(screen, field.grid, H, W, cell_size, bg_color, cell_color, text_color, speed_ms)
        panel.draw(screen, H, cell_size, selected_pattern)

        if dragging and selected_pattern:
            mx, my = pygame.mouse.get_pos()
            gx = mx // cell_size
            gy = my // cell_size
            for dx, dy in patterns[selected_pattern]:
                x = (gx + dx) * cell_size
                y = (gy + dy) * cell_size
                pygame.draw.rect(screen, (255, 255, 255), (x, y, cell_size, cell_size), 1)

        pygame.display.flip()
        clock.tick(FPS) # ограничение по FPS

    pygame.quit()


main()