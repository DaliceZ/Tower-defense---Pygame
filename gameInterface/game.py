# gameInterface/game.py
import pygame
import sys
import random
import math
import time
from gameData.config import *
from gameData.map_layout import generate_random_map
from utils.pathfinding import Pathfinder
from gameInterface.entities import Enemy, Tower, Bullet, Particle, FloatingText, SpecialPower, get_image
from utils.gadgets import Button
from utils.save_writer import SaveManager
from utils.load_audio import (load_sfx, play_button_sfx, play_tower_place_sfx,
                               play_wave_start_sfx, play_game_over_sfx, play_victory_sfx,
                               play_bgm, stop_bgm)
import os

STATE_MENU = 0
STATE_PLAYING = 1
STATE_GAME_OVER = 2
STATE_WIN = 3
STATE_DIFFICULTY = 4
STATE_PAUSED = 5

MODE_SURVIVAL = "survival"
MODE_PUZZLE = "puzzle"

class GameManager:
    def __init__(self, mode, difficulty="normal"):
        self.mode = mode
        self.difficulty = difficulty
        self.particles = []
        self.effects = []
        self.available_types = ["standard", "smart", "tank", "rusher"]
        self.available_types = ["standard", "smart", "tank", "rusher"]

        preset = DIFFICULTY_PRESETS[difficulty]
        self.hp_mult = preset["hp_mult"]
        self.speed_mult = preset["speed_mult"]
        self.wave_size_mult = preset["wave_size_mult"]

        # --- Variables for Wave Text Effect ---
        self.show_wave_text = True
        self.wave_alpha = 255

        if self.mode == MODE_SURVIVAL:
            self.money = preset["survival_money"]
            self.lives = preset["survival_lives"]
            self.wave = 1
            self.max_waves = preset["survival_max_waves"]
            self.spawn_queue = self.generate_random_wave(5, 1)
            self.boss_spawned = False

        elif self.mode == MODE_PUZZLE:
            self.money = preset["puzzle_money"]
            self.lives = preset["puzzle_lives"]
            self.wave = 1
            self.max_waves = 1
            base_queue = (
                ["standard"] * 10 +
                ["smart"] * 5 +
                ["tank"] * 5 +
                ["rusher"] * 10
            )
            scaled_count = int(len(base_queue) * self.wave_size_mult)
            self.spawn_queue = base_queue[:scaled_count] if scaled_count <= len(base_queue) else base_queue + [random.choice(self.available_types) for _ in range(scaled_count - len(base_queue))]

    def generate_random_wave(self, count, wave_num):
        pool = ["standard"]
        if wave_num == 2 and self.mode == MODE_SURVIVAL:
            pool = ["standard", "smart"]
        elif wave_num >= 3 and self.mode == MODE_SURVIVAL:
            pool = ["standard", "smart", "rusher", "tank"]
        elif self.mode == MODE_PUZZLE:
            pool = ["standard", "smart", "rusher", "tank"]

        scaled_count = max(1, int(count * self.wave_size_mult))
        return [random.choice(pool) for _ in range(scaled_count)]

    def add_money(self, amount):
        if self.mode == MODE_SURVIVAL:
            self.money += amount

    def spend_money(self, amount):
        if self.money >= amount:
            self.money -= amount
            return True
        return False

    def record_kill(self, bounty):
        pass

    def trigger_next_wave(self):
        self.show_wave_text = True
        self.wave_alpha = 255
        play_wave_start_sfx()

    def get_next_wave_preview(self):
        """Return cached dict of enemy type counts for the NEXT wave (survival only)."""
        if self.mode != MODE_SURVIVAL or self.wave >= self.max_waves:
            self._preview_cache = None
            return None
        # Cache per wave so it doesn't flicker every frame
        if getattr(self, '_preview_cache_wave', None) != self.wave:
            next_wave_num = self.wave + 1
            next_count = 5 + (next_wave_num * 5)
            preview_queue = self.generate_random_wave(next_count, next_wave_num)
            counts = {}
            for et in preview_queue:
                counts[et] = counts.get(et, 0) + 1
            self._preview_cache = counts
            self._preview_cache_wave = self.wave
        return self._preview_cache

    def get_current_wave_counts(self, enemies):
        """Return dict of remaining enemy type counts (queue + alive)."""
        counts = {}
        for et in self.spawn_queue:
            counts[et] = counts.get(et, 0) + 1
        for e in enemies:
            counts[e.enemy_type] = counts.get(e.enemy_type, 0) + 1
        return counts


def reset_game(mode, difficulty="normal"):
    game_map = generate_random_map()
    pathfinder = Pathfinder(game_map)
    enemies = []
    towers = []
    bullets = []
    powers = []
    manager = GameManager(mode, difficulty)
    return pathfinder, enemies, towers, bullets, powers, manager


def run_game():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Tower Defense")
    clock = pygame.time.Clock()

    # Load audio
    load_sfx()

    font_path = os.path.join("assets", "fonts", "RasterForgeRegular-JpBgm.ttf")
    font_ui = pygame.font.Font(font_path, 20)
    font_title = pygame.font.Font(font_path, 90)
    font_btn = pygame.font.Font(font_path, 28)
    font_sub = pygame.font.Font(font_path, 16)
    font_wave = pygame.font.Font(font_path, 120)
    font_small = pygame.font.Font(font_path, 14)

    # Save manager
    save_mgr = SaveManager()

    current_state = STATE_MENU

    pathfinder = None
    enemies = []
    towers = []
    bullets = []
    powers = []
    manager = None
    spawn_timer = 0
    selected_action = "tower"
    tower_cd = 0
    power_cd = 0
    shovel_cd = 0
    moonflower_cd = 0
    sniper_cd = 0
    tower_cd_max = 5 * FPS
    power_cd_max = 30 * FPS
    shovel_cd_max = 3 * FPS
    moonflower_cd_max = 15 * FPS
    sniper_cd_max = 10 * FPS

    game_speed = 1  # 1x, 2x, 3x
    end_sfx_played = False  # prevent repeated sfx

    btn_surv = Button(pygame.Rect(WIDTH//2 - 210, 220, 420, 150), "SURVIVAL MODE", font_btn,
                      subtext="Endless waves & Money management", subfont=font_sub,
                      image_path=os.path.join("assets", "images", "ui", "button.png"))
    btn_puzz = Button(pygame.Rect(WIDTH//2 - 210, 390, 420, 150), "PUZZLE MODE", font_btn,
                      subtext="Fixed budget, One massive wave", subfont=font_sub,
                      image_path=os.path.join("assets", "images", "ui", "button.png"))
    btn_quit = Button(pygame.Rect(WIDTH//2 - 100, HEIGHT - 120, 200, 80), "EXIT GAME", font_btn,
                      image_path=os.path.join("assets", "images", "ui", "button.png"))
    btn_back = Button(pygame.Rect(WIDTH - 130, 0, 110, 60), "MENU", font_ui,
                      image_path=os.path.join("assets", "images", "ui", "button.png"))

    # Difficulty selection buttons
    diff_btn_y_start = 220
    diff_btn_gap = 110
    btn_easy = Button(pygame.Rect(WIDTH//2 - 150, diff_btn_y_start, 300, 90), "EASY", font_btn,
                      subtext="Relaxed gameplay", subfont=font_sub,
                      image_path=os.path.join("assets", "images", "ui", "button.png"))
    btn_normal = Button(pygame.Rect(WIDTH//2 - 150, diff_btn_y_start + diff_btn_gap, 300, 90), "NORMAL", font_btn,
                        subtext="Standard challenge", subfont=font_sub,
                        image_path=os.path.join("assets", "images", "ui", "button.png"))
    btn_hard = Button(pygame.Rect(WIDTH//2 - 150, diff_btn_y_start + diff_btn_gap*2, 300, 90), "HARD", font_btn,
                      subtext="For experienced players", subfont=font_sub,
                      image_path=os.path.join("assets", "images", "ui", "button.png"))
    btn_nightmare = Button(pygame.Rect(WIDTH//2 - 150, diff_btn_y_start + diff_btn_gap*3, 300, 90), "NIGHTMARE", font_btn,
                           subtext="No room for mistakes", subfont=font_sub,
                           image_path=os.path.join("assets", "images", "ui", "button.png"))

    # Pause menu buttons
    btn_resume = Button(pygame.Rect(WIDTH//2 - 140, HEIGHT//2 - 80, 280, 70), "RESUME", font_btn,
                        image_path=os.path.join("assets", "images", "ui", "button.png"))
    btn_restart = Button(pygame.Rect(WIDTH//2 - 140, HEIGHT//2, 280, 70), "RESTART", font_btn,
                         image_path=os.path.join("assets", "images", "ui", "button.png"))
    btn_quit_menu = Button(pygame.Rect(WIDTH//2 - 140, HEIGHT//2 + 80, 280, 70), "QUIT TO MENU", font_btn,
                           image_path=os.path.join("assets", "images", "ui", "button.png"))

    selected_mode = None

    img_game_bg = get_image(os.path.join("assets", "images", "ui", "game_bg.png"), (WIDTH, HEIGHT))
    img_lobby_bg = get_image(os.path.join("assets", "images", "ui", "lobby.png"), (WIDTH, HEIGHT))
    img_plant_wall = get_image(os.path.join("assets", "images", "ui", "plant_wall.png"), (TILE_SIZE, TILE_SIZE))
    img_bush = get_image(os.path.join("assets", "images", "ui", "bush.png"), (TILE_SIZE, TILE_SIZE))
    img_rock = get_image(os.path.join("assets", "images", "ui", "rock.png"), (TILE_SIZE, TILE_SIZE))
    img_barrier = get_image(os.path.join("assets", "images", "ui", "barrier.png"), (TILE_SIZE, TILE_SIZE))
    img_q_bg = get_image(os.path.join("assets", "images", "ui", "q_bg.png"), (36, 36))
    img_dock_bg = get_image(os.path.join("assets", "images", "ui", "dock_wall.png"), (460, 100))

    # UI Slots in PLAYING state (Dynamic Y PvZ Style)
    dock_width = 460
    dock_height = 100
    dock_x = (WIDTH - 460) // 2

    dock_current_y = -dock_height
    dock_target_y = -dock_height
    tab_h = 22  # pull-tab handle height

    # BGM state
    current_bgm = None

    running = True
    while running:
        mx, my = pygame.mouse.get_pos()
        gx, gy = mx // TILE_SIZE, (my - MAP_OFFSET_Y) // TILE_SIZE

        # BGM management
        if current_state in (STATE_MENU, STATE_DIFFICULTY):
            if current_bgm != "menu":
                play_bgm("menu")
                current_bgm = "menu"
        elif current_state in (STATE_PLAYING, STATE_PAUSED):
            if current_bgm != "game":
                play_bgm("game")
                current_bgm = "game"
        elif current_state in (STATE_GAME_OVER, STATE_WIN):
            if current_bgm != "none":
                stop_bgm()
                current_bgm = "none"

        # Dock slots positioning (compact: 55px wide, 65px apart)
        slot_w, slot_h = 55, 80
        slot_start = dock_x + 85  # after money area (80px + 5px gap)
        slot_gap = 63
        slot_tower = pygame.Rect(slot_start, dock_current_y + 10, slot_w, slot_h)
        slot_moonflower = pygame.Rect(slot_start + slot_gap, dock_current_y + 10, slot_w, slot_h)
        slot_sniper = pygame.Rect(slot_start + slot_gap*2, dock_current_y + 10, slot_w, slot_h)
        slot_power = pygame.Rect(slot_start + slot_gap*3, dock_current_y + 10, slot_w, slot_h)
        slot_shovel = pygame.Rect(slot_start + slot_gap*4.7, dock_current_y + 10, slot_w, slot_h)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    selected_action = None
                # Pause toggle
                if event.key == pygame.K_ESCAPE:
                    if current_state == STATE_PLAYING:
                        current_state = STATE_PAUSED
                    elif current_state == STATE_PAUSED:
                        current_state = STATE_PLAYING

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if current_state == STATE_MENU:
                        if btn_surv.clicked(event):
                            selected_mode = MODE_SURVIVAL
                            current_state = STATE_DIFFICULTY
                        elif btn_puzz.clicked(event):
                            selected_mode = MODE_PUZZLE
                            current_state = STATE_DIFFICULTY
                        elif btn_quit.clicked(event):
                            running = False

                    elif current_state == STATE_DIFFICULTY:
                        chosen_diff = None
                        if btn_easy.clicked(event):
                            chosen_diff = "easy"
                        elif btn_normal.clicked(event):
                            chosen_diff = "normal"
                        elif btn_hard.clicked(event):
                            chosen_diff = "hard"
                        elif btn_nightmare.clicked(event):
                            chosen_diff = "nightmare"
                        elif btn_back.clicked(event):
                            current_state = STATE_MENU

                        if chosen_diff:
                            pathfinder, enemies, towers, bullets, powers, manager = reset_game(selected_mode, chosen_diff)
                            current_state = STATE_PLAYING
                            game_speed = 1
                            end_sfx_played = False

                    elif current_state == STATE_PAUSED:
                        if btn_resume.clicked(event):
                            current_state = STATE_PLAYING
                        elif btn_restart.clicked(event):
                            pathfinder, enemies, towers, bullets, powers, manager = reset_game(selected_mode, manager.difficulty)
                            current_state = STATE_PLAYING
                            game_speed = 1
                            end_sfx_played = False
                        elif btn_quit_menu.clicked(event):
                            current_state = STATE_MENU
                            tower_cd = 0; power_cd = 0; shovel_cd = 0; moonflower_cd = 0
                            sniper_cd = 0
                            game_speed = 1

                    elif current_state == STATE_PLAYING:
                        # Speed button (top bar right area)
                        speed_btn_rect = pygame.Rect(WIDTH - 250, 10, 100, 40)
                        if speed_btn_rect.collidepoint(event.pos):
                            game_speed = game_speed % 3 + 1  # cycle 1->2->3->1

                        elif btn_back.clicked(event):
                            current_state = STATE_PAUSED
                            tower_cd = 0; power_cd = 0; shovel_cd = 0; moonflower_cd = 0
                            sniper_cd = 0
                            game_speed = 1
                        elif slot_tower.collidepoint(event.pos):
                            selected_action = "tower"
                        elif slot_moonflower.collidepoint(event.pos):
                            selected_action = "moonflower"
                        elif slot_sniper.collidepoint(event.pos):
                            selected_action = "sniper"
                        elif slot_power.collidepoint(event.pos):
                            selected_action = "power"
                        elif slot_shovel.collidepoint(event.pos):
                            selected_action = "shovel"
                        else:
                            # Map clicks
                            if selected_action == "tower" and tower_cd <= 0:
                                occupied = any(t.grid_pos == (gx, gy) for t in towers)
                                if not occupied:
                                    if pathfinder.place_tower(gx, gy):
                                        if manager.spend_money(TOWER_COST):
                                            t = Tower((gx, gy), TILE_SIZE, tower_type="corneto")
                                            t.total_invested = TOWER_COST
                                            towers.append(t)
                                            tower_cd = tower_cd_max
                                            play_tower_place_sfx()
                                        else:
                                            pathfinder.matrix[gy][gx] = 0
                                            pathfinder.calculate_flows()
                            elif selected_action == "moonflower" and moonflower_cd <= 0:
                                occupied = any(t.grid_pos == (gx, gy) for t in towers)
                                if not occupied:
                                    if pathfinder.place_tower(gx, gy):
                                        if manager.spend_money(MOONFLOWER_COST):
                                            t = Tower((gx, gy), TILE_SIZE, tower_type="moonflower")
                                            t.total_invested = MOONFLOWER_COST
                                            towers.append(t)
                                            moonflower_cd = moonflower_cd_max
                                            play_tower_place_sfx()
                                        else:
                                            pathfinder.matrix[gy][gx] = 0
                                            pathfinder.calculate_flows()
                            elif selected_action == "sniper" and sniper_cd <= 0:
                                occupied = any(t.grid_pos == (gx, gy) for t in towers)
                                if not occupied:
                                    if pathfinder.place_tower(gx, gy):
                                        if manager.spend_money(SNIPER_COST):
                                            t = Tower((gx, gy), TILE_SIZE, tower_type="sniper")
                                            t.total_invested = SNIPER_COST
                                            towers.append(t)
                                            sniper_cd = sniper_cd_max
                                            play_tower_place_sfx()
                                        else:
                                            pathfinder.matrix[gy][gx] = 0
                                            pathfinder.calculate_flows()
                            elif selected_action == "power" and power_cd <= 0:
                                if manager.spend_money(POWER_COST):
                                    powers.append(SpecialPower((mx, my), TILE_SIZE, manager))
                                    power_cd = power_cd_max
                            elif selected_action == "shovel" and shovel_cd <= 0:
                                for t in towers:
                                    if t.grid_pos == (gx, gy):
                                        towers.remove(t)
                                        refund = t.total_invested // 2
                                        manager.add_money(refund)
                                        pathfinder.matrix[gy][gx] = 0
                                        pathfinder.calculate_flows()
                                        shovel_cd = shovel_cd_max
                                        break

                    elif current_state in (STATE_GAME_OVER, STATE_WIN):
                        current_state = STATE_MENU
                        tower_cd = 0; power_cd = 0; shovel_cd = 0; moonflower_cd = 0
                        sniper_cd = 0
                        game_speed = 1

        # --- Game Logic (with speed multiplier) ---
        if current_state == STATE_PLAYING:
            for _tick in range(game_speed):
                if tower_cd > 0: tower_cd -= 1
                if power_cd > 0: power_cd -= 1
                if shovel_cd > 0: shovel_cd -= 1
                if moonflower_cd > 0: moonflower_cd -= 1
                if sniper_cd > 0: sniper_cd -= 1

                # Spawning
                if manager.spawn_queue:
                    spawn_timer += 1
                    limit = 30 if manager.mode == MODE_PUZZLE else 60
                    if spawn_timer >= limit:
                        spawn_timer = 0
                        e_type = manager.spawn_queue.pop(0)
                        for sp in pathfinder.spawn_pos:
                            enemies.append(Enemy(sp, TILE_SIZE, pathfinder, enemies, manager, enemy_type=e_type))
                elif manager.mode == MODE_SURVIVAL and manager.wave == manager.max_waves and not getattr(manager, 'boss_spawned', False):
                    boss_timer = getattr(manager, 'boss_timer', 0)
                    boss_timer += 1
                    setattr(manager, 'boss_timer', boss_timer)
                    if boss_timer >= 30:
                        manager.show_wave_text = "The BOSS is released!"
                        manager.wave_alpha = 255
                        manager.boss_spawned = True
                        for sp in pathfinder.spawn_pos:
                            enemies.append(Enemy(sp, TILE_SIZE, pathfinder, enemies, manager, enemy_type="boss"))

                # Update Entities
                for enemy in enemies[:]:
                    enemy.update()
                    if enemy.reached_base:
                        manager.add_money(enemy.bounty)
                        manager.lives -= 1
                        enemies.remove(enemy)
                        if manager.lives <= 0 or enemy.enemy_type == "boss":
                            current_state = STATE_GAME_OVER
                            if not end_sfx_played:
                                play_game_over_sfx()
                                end_sfx_played = True
                            break
                    elif enemy.dead:
                        enemies.remove(enemy)

                if current_state != STATE_PLAYING:
                    break

                # Reset visibility for rushers
                for enemy in enemies:
                    if enemy.enemy_type == "rusher":
                        enemy.is_visible = False

                # Update moonflowers first
                for t in towers:
                    if t.tower_type == "moonflower":
                        t.update(enemies, bullets)

                # Then update other towers
                for t in towers:
                    if t.tower_type != "moonflower":
                        t.update(enemies, bullets)
                for b in bullets[:]:
                    b.update()
                    if not b.active: bullets.remove(b)
                for pw in powers[:]:
                    pw.update(enemies)
                    if not pw.active: powers.remove(pw)
                for p in manager.particles[:]:
                    p.update()
                    if p.life <= 0: manager.particles.remove(p)
                for ef in manager.effects[:]:
                    ef.update()
                    if ef.life <= 0: manager.effects.remove(ef)

            # --- Wave/Win check (once per frame, OUTSIDE speed loop) ---
            if current_state == STATE_PLAYING and not manager.spawn_queue and len(enemies) == 0:
                if manager.wave < manager.max_waves:
                    manager.wave += 1
                    manager.trigger_next_wave()
                    if manager.mode == MODE_SURVIVAL:
                        new_count = 5 + (manager.wave * 5)
                        manager.spawn_queue = manager.generate_random_wave(new_count, manager.wave)
                else:
                    if manager.mode != MODE_SURVIVAL or getattr(manager, 'boss_spawned', False):
                        current_state = STATE_WIN
                        if not end_sfx_played:
                            play_victory_sfx()
                            end_sfx_played = True

            # --- Logic: Fade Text (once per frame) ---
            if manager and manager.show_wave_text:
                manager.wave_alpha -= 3
                if manager.wave_alpha <= 0:
                    manager.wave_alpha = 0
                    manager.show_wave_text = False

            # --- Logic: UI Dock Slide (once per frame) ---
            # Tab handle area (always visible below top bar) + dock itself
            hover_zone = max(60 + tab_h, dock_current_y + dock_height)
            if my < hover_zone:
                dock_target_y = 60
            else:
                dock_target_y = -dock_height + 60
            dock_current_y += (dock_target_y - dock_current_y) * 0.15

        # --- Drawing ---
        if current_state in (STATE_PLAYING, STATE_PAUSED) and img_game_bg:
            screen.blit(img_game_bg, (0, 0))
        else:
            screen.fill(C_BG)

        if current_state == STATE_MENU:
            if img_lobby_bg:
                screen.blit(img_lobby_bg, (0, 0))
            else:
                screen.fill((25, 28, 35))
                for i in range(0, HEIGHT, 20):
                    alpha = max(0, 50 - (i // 10))
                    line_surf = pygame.Surface((WIDTH, 2), pygame.SRCALPHA)
                    line_surf.fill((255, 255, 255, alpha))
                    screen.blit(line_surf, (0, i))

            t_shadow = font_title.render("TOWER DEFENSE", True, (0, 0, 0))
            t_main = font_title.render("TOWER DEFENSE", True, (255, 215, 0))
            screen.blit(t_shadow, t_shadow.get_rect(center=(WIDTH//2 + 5, 120 + 5)))
            screen.blit(t_main, t_main.get_rect(center=(WIDTH//2, 120)))
            sub = font_btn.render("- STRATEGIC WARFARE -", True, (100, 100, 110))
            screen.blit(sub, sub.get_rect(center=(WIDTH//2, 190)))

            btn_surv.draw(screen)
            btn_puzz.draw(screen)
            btn_quit.draw(screen)

        elif current_state == STATE_DIFFICULTY:
            if img_lobby_bg:
                screen.blit(img_lobby_bg, (0, 0))
            else:
                screen.fill((25, 28, 35))
                for i in range(0, HEIGHT, 20):
                    alpha = max(0, 50 - (i // 10))
                    line_surf = pygame.Surface((WIDTH, 2), pygame.SRCALPHA)
                    line_surf.fill((255, 255, 255, alpha))
                    screen.blit(line_surf, (0, i))

            mode_label = selected_mode.upper() if selected_mode else ""
            t_main = font_title.render("DIFFICULTY", True, (255, 215, 0))
            screen.blit(t_main, t_main.get_rect(center=(WIDTH//2, 100)))
            sub = font_btn.render(f"- {mode_label} MODE -", True, (100, 100, 110))
            screen.blit(sub, sub.get_rect(center=(WIDTH//2, 170)))

            btn_easy.draw(screen)
            btn_normal.draw(screen)
            btn_hard.draw(screen)
            btn_nightmare.draw(screen)
            btn_back.draw(screen)

        elif current_state in (STATE_PLAYING, STATE_PAUSED):
            # Map & Entities
            for r in range(pathfinder.rows):
                for c in range(pathfinder.cols):
                    val = pathfinder.matrix[r][c]
                    rect_y = r * TILE_SIZE + MAP_OFFSET_Y
                    rect = (c * TILE_SIZE, rect_y, TILE_SIZE, TILE_SIZE)

                    if val == 1:
                        is_edge = (r == 0 or r == pathfinder.rows - 1 or c == 0 or c == pathfinder.cols - 1)
                        if is_edge and img_barrier:
                            if selected_action in ["tower", "moonflower", "sniper", "power", "shovel"]:
                                s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                                s.fill((255, 100, 100, 100))
                                screen.blit(s, rect)
                            screen.blit(img_barrier, rect)
                        else:
                            random.seed(r * 1000 + c)
                            is_bush = random.choice([True, False])
                            random.seed(None)
                            if is_bush and img_bush:
                                screen.blit(img_bush, rect)
                            elif img_rock:
                                screen.blit(img_rock, rect)
                            else:
                                pygame.draw.rect(screen, C_WALL, rect)
                    elif val == 2:
                        if img_plant_wall:
                            screen.blit(img_plant_wall, rect)
                        else:
                            pygame.draw.rect(screen, (60, 60, 70), rect)

                    if selected_action in ["tower", "moonflower", "sniper", "power", "shovel"]:
                        if val == 0:
                            s_overlay = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                            s_overlay.fill((255, 255, 255, 30))
                            screen.blit(s_overlay, rect)
                        pygame.draw.rect(screen, (40, 43, 50), rect, 1)

            for t in towers: t.draw(screen, t.rect.collidepoint(mx, my))
            for e in enemies: e.draw(screen)
            for b in bullets: b.draw(screen)
            for pw in powers: pw.draw(screen)
            for p in manager.particles: p.draw(screen)
            for ef in manager.effects: ef.draw(screen)

            # --- Wave Text Overlay ---
            if manager.show_wave_text:
                txt_str = manager.show_wave_text if isinstance(manager.show_wave_text, str) else f"WAVE {manager.wave}"
                shadow_surf = font_wave.render(txt_str, True, (0, 0, 0))
                shadow_surf.set_alpha(manager.wave_alpha)
                shadow_rect = shadow_surf.get_rect(center=(WIDTH//2 + 5, HEIGHT//2 - 50 + 5))
                screen.blit(shadow_surf, shadow_rect)
                text_surf = font_wave.render(txt_str, True, (255, 215, 0))
                text_surf.set_alpha(manager.wave_alpha)
                text_rect = text_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 50))
                screen.blit(text_surf, text_rect)

            # --- Dynamic Sliding Dock System (draw BEFORE top bar so bar stays on top) ---
            dock_rect = pygame.Rect(dock_x, dock_current_y, dock_width, dock_height)
            if img_dock_bg:
                screen.blit(img_dock_bg, (dock_x, dock_current_y))
                pygame.draw.rect(screen, (51, 25, 0), dock_rect, 4, border_radius=8)
            else:
                pygame.draw.rect(screen, (255, 210, 85), dock_rect, border_radius=8)
                pygame.draw.rect(screen, (51, 25, 0), dock_rect, 4, border_radius=8)

            # Money area
            money_rect = pygame.Rect(dock_x, dock_current_y, 80, dock_height)
            money_val = font_ui.render(str(manager.money), True, (0, 0, 0))
            screen.blit(money_val, money_val.get_rect(center=(money_rect.centerx + 1, money_rect.bottom - 20 + 1)))
            money_val2 = font_ui.render(str(manager.money), True, (255, 255, 255))
            screen.blit(money_val2, money_val2.get_rect(center=(money_rect.centerx, money_rect.bottom - 20)))

            money_img_path = os.path.join("assets", "images", "money.PNG")
            money_img = get_image(money_img_path, (60, 60))
            if money_img:
                screen.blit(money_img, money_img.get_rect(center=(money_rect.centerx, money_rect.centery - 15)))

            # Helper to draw seed packet slots
            def draw_seed_packet(rect, cost, is_selected, icon_path, cd, cd_max):
                bg_col = (180, 180, 180) if not is_selected else (220, 255, 220)
                if rect.collidepoint(mx, my): bg_col = (200, 200, 200)
                pygame.draw.rect(screen, bg_col, rect, border_radius=4)
                pygame.draw.rect(screen, (0, 0, 0), rect, 2, border_radius=4)

                img_area = pygame.Rect(rect.x + 2, rect.y + 2, rect.width - 4, rect.height - 25)
                pygame.draw.rect(screen, (150, 200, 150), img_area, border_top_left_radius=4, border_top_right_radius=4)

                if icon_path:
                    icon_img = get_image(icon_path, (img_area.width - 10, img_area.height - 10))
                    if icon_img: screen.blit(icon_img, icon_img.get_rect(center=img_area.center))

                if cd > 0:
                    cd_surf = pygame.Surface((img_area.width, img_area.height), pygame.SRCALPHA)
                    fill_h = int(img_area.height * (cd / cd_max))
                    pygame.draw.rect(cd_surf, (128, 128, 128, 180), (0, img_area.height - fill_h, img_area.width, fill_h))
                    screen.blit(cd_surf, img_area.topleft)

                cost_area = pygame.Rect(rect.x + 2, rect.bottom - 22, rect.width - 4, 20)
                pygame.draw.rect(screen, (230, 230, 230), cost_area, border_bottom_left_radius=4, border_bottom_right_radius=4)
                cost_txt = font_sub.render(str(cost), True, (0, 0, 0))
                screen.blit(cost_txt, cost_txt.get_rect(center=cost_area.center))

            # Draw all packets
            path_corn = os.path.join("assets", "images", "plants", "corn1.PNG")
            path_tomato = os.path.join("assets", "images", "plants", "tomato1.PNG")
            path_moonflower = os.path.join("assets", "images", "plants", "moonflower1.PNG")
            path_shovel = os.path.join("assets", "images", "shovel.PNG")

            draw_seed_packet(slot_tower, TOWER_COST, selected_action == "tower", path_corn, tower_cd, tower_cd_max)
            draw_seed_packet(slot_moonflower, MOONFLOWER_COST, selected_action == "moonflower", path_moonflower, moonflower_cd, moonflower_cd_max)
            path_sniper = os.path.join("assets", "images", "plants", "blueberry1.PNG")

            draw_seed_packet(slot_sniper, SNIPER_COST, selected_action == "sniper", path_sniper, sniper_cd, sniper_cd_max)
            draw_seed_packet(slot_power, POWER_COST, selected_action == "power", path_tomato, power_cd, power_cd_max)
            draw_seed_packet(slot_shovel, "shovel", selected_action == "shovel", path_shovel, shovel_cd, shovel_cd_max)

            # --- UI Bar (drawn AFTER dock so it stays on top) ---
            pygame.draw.rect(screen, C_UI_BG, (0, 0, WIDTH, 60))
            pygame.draw.line(screen, (60, 60, 70), (0, 60), (WIDTH, 60), 2)

            stats = f"MODE: {manager.mode.upper()}  |  {manager.difficulty.upper()}  |  WAVE: {manager.wave}  |  LIVES: {manager.lives}"
            screen.blit(font_ui.render(stats, True, (255, 255, 255)), (20, 20))

            # Speed button
            speed_btn_rect = pygame.Rect(WIDTH - 250, 10, 100, 40)
            speed_col = (60, 60, 80) if game_speed == 1 else (80, 120, 60) if game_speed == 2 else (120, 80, 60)
            pygame.draw.rect(screen, speed_col, speed_btn_rect, border_radius=6)
            pygame.draw.rect(screen, (200, 200, 200), speed_btn_rect, 2, border_radius=6)
            speed_label = f"x{game_speed}"
            spd_txt = font_ui.render(speed_label, True, (255, 255, 255))
            screen.blit(spd_txt, spd_txt.get_rect(center=speed_btn_rect.center))

            btn_back.draw(screen)

            # --- Wave Preview Panel (Survival only) ---
            if manager.mode == MODE_SURVIVAL and selected_action in ["tower", "moonflower", "sniper", "power", "shovel"]:
                panel_x = 5
                panel_y = 65
                panel_w = 160
                remaining = manager.get_current_wave_counts(enemies)
                next_preview = manager.get_next_wave_preview()

                lines = []
                if remaining:
                    lines.append(("Remaining:", (255, 255, 255)))
                    for etype, cnt in remaining.items():
                        color_map = {"standard": (0, 255, 0), "smart": (180, 60, 220),
                                     "tank": (60, 180, 60), "rusher": (220, 220, 60), "boss": (255, 50, 50)}
                        lines.append((f"  {etype}: {cnt}", color_map.get(etype, (200, 200, 200))))
                if next_preview:
                    lines.append(("Next wave:", (200, 200, 200)))
                    for etype, cnt in next_preview.items():
                        color_map = {"standard": (0, 255, 0), "smart": (180, 60, 220),
                                     "tank": (60, 180, 60), "rusher": (220, 220, 60)}
                        lines.append((f"  {etype}: {cnt}", color_map.get(etype, (200, 200, 200))))

                if lines:
                    panel_h = len(lines) * 18 + 10
                    panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
                    panel_surf.fill((0, 0, 0, 140))
                    screen.blit(panel_surf, (panel_x, panel_y))
                    for i, (text, color) in enumerate(lines):
                        txt = font_small.render(text, True, color)
                        screen.blit(txt, (panel_x + 5, panel_y + 5 + i * 18))

            # --- Dock Pull-Tab Handle (always visible below top bar) ---
            tab_w = 120
            tab_x = dock_x + (dock_width - tab_w) // 2
            tab_y = 58  # just at bottom edge of top bar
            dock_is_hidden = dock_current_y < 20
            # Animate: bounce gently when hidden to attract attention
            if dock_is_hidden:
                bounce = abs(math.sin(time.time() * 2)) * 3
            else:
                bounce = 0
            tab_rect = pygame.Rect(tab_x, tab_y + int(bounce), tab_w, tab_h)
            tab_color = (220, 180, 60) if dock_is_hidden else (180, 150, 50)
            pygame.draw.rect(screen, tab_color, tab_rect,
                             border_bottom_left_radius=8, border_bottom_right_radius=8)
            pygame.draw.rect(screen, (51, 25, 0), tab_rect, 2,
                             border_bottom_left_radius=8, border_bottom_right_radius=8)
            # Arrow indicator
            arrow_txt = font_small.render("\u25BC TOWERS" if dock_is_hidden else "\u25B2", True, (51, 25, 0))
            screen.blit(arrow_txt, arrow_txt.get_rect(center=tab_rect.center))

            # --- Q to Cancel Hint ---
            if selected_action in ["tower", "moonflower", "sniper", "power", "shovel"]:
                if selected_action in ["tower", "moonflower", "sniper"] and 0 <= gy < pathfinder.rows and 0 <= gx < pathfinder.cols:
                    hint_x = gx * TILE_SIZE - 20
                    hint_y = gy * TILE_SIZE + MAP_OFFSET_Y + TILE_SIZE + 5
                else:
                    hint_x = mx - 20
                    hint_y = my + 35

                if img_q_bg:
                    screen.blit(img_q_bg, (hint_x, hint_y))
                    q_text = font_ui.render("q", True, (0, 0, 0))
                    screen.blit(q_text, q_text.get_rect(center=(hint_x + 18, hint_y + 18)))
                    cancel_text = font_sub.render("to cancel", True, (255, 255, 255))
                    cancel_shadow = font_sub.render("to cancel", True, (0, 0, 0))
                    screen.blit(cancel_shadow, (hint_x + 46, hint_y + 11))
                    screen.blit(cancel_text, (hint_x + 45, hint_y + 10))

            # --- Target Indicator Preview ---
            hovering_ui = False
            try:
                ui_rects = [btn_back.rect, slot_tower, slot_moonflower,
                            slot_sniper, slot_power, slot_shovel]
                for r in ui_rects:
                    if r.collidepoint(mx, my):
                        hovering_ui = True
                        break
            except: pass

            if not hovering_ui:
                tower_actions = {"tower": (TOWER_COST, 220, tower_cd, path_corn),
                                 "moonflower": (MOONFLOWER_COST, 180, moonflower_cd, path_moonflower),
                                 "sniper": (SNIPER_COST, 450, sniper_cd, path_sniper)}

                if selected_action in tower_actions:
                    cost, tr, cd, img_path = tower_actions[selected_action]
                    if 0 <= gy < pathfinder.rows and 0 <= gx < pathfinder.cols:
                        if pathfinder.matrix[gy][gx] == 0 and not any(t.grid_pos == (gx, gy) for t in towers):
                            col = (0, 255, 0, 50) if manager.money >= cost and cd <= 0 else (255, 0, 0, 50)
                            rad_surf = pygame.Surface((tr * 2, tr * 2), pygame.SRCALPHA)
                            pygame.draw.circle(rad_surf, col, (tr, tr), tr)
                            screen.blit(rad_surf, (gx*TILE_SIZE + TILE_SIZE//2 - tr, gy*TILE_SIZE + MAP_OFFSET_Y + TILE_SIZE//2 - tr))

                            s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                            s.fill((255, 255, 255, 128))
                            rect_tgt = (gx*TILE_SIZE, gy*TILE_SIZE + MAP_OFFSET_Y, TILE_SIZE, TILE_SIZE)
                            screen.blit(s, rect_tgt)
                            pygame.draw.rect(screen, (0, 0, 0), rect_tgt, 2)

                            if img_path:
                                prev_img = get_image(img_path, (TILE_SIZE, TILE_SIZE))
                                if prev_img:
                                    prev_img = prev_img.copy()
                                    prev_img.set_alpha(128)
                                    screen.blit(prev_img, (gx*TILE_SIZE, gy*TILE_SIZE + MAP_OFFSET_Y))

                elif selected_action == "power":
                    r = TILE_SIZE * 2
                    s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                    col = (0, 255, 0, 50) if manager.money >= POWER_COST and power_cd <= 0 else (255, 100, 100, 50)
                    pygame.draw.circle(s, col, (r, r), r)
                    screen.blit(s, (mx - r, my - r))
                    prev_img = get_image(path_tomato, (TILE_SIZE, TILE_SIZE))
                    if prev_img:
                        prev_img = prev_img.copy()
                        prev_img.set_alpha(128)
                        screen.blit(prev_img, prev_img.get_rect(center=(mx, my)))

                elif selected_action == "shovel":
                    if 0 <= gy < pathfinder.rows and 0 <= gx < pathfinder.cols:
                        has_tower = any(t.grid_pos == (gx, gy) for t in towers)
                        if has_tower:
                            col = (255, 100, 100, 150) if shovel_cd <= 0 else (100, 100, 100, 150)
                            s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                            s.fill(col)
                            screen.blit(s, (gx*TILE_SIZE, gy*TILE_SIZE + MAP_OFFSET_Y))
                    prev_img = get_image(path_shovel, (60, 60))
                    if prev_img:
                        prev_img = prev_img.copy()
                        prev_img.set_alpha(128)
                        screen.blit(prev_img, prev_img.get_rect(center=(mx, my)))

            # --- Pause Overlay ---
            if current_state == STATE_PAUSED:
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 150))
                screen.blit(overlay, (0, 0))
                pause_txt = font_title.render("PAUSED", True, (255, 215, 0))
                screen.blit(pause_txt, pause_txt.get_rect(center=(WIDTH//2, HEIGHT//2 - 150)))
                btn_resume.draw(screen)
                btn_restart.draw(screen)
                btn_quit_menu.draw(screen)

        elif current_state in (STATE_GAME_OVER, STATE_WIN):
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            screen.blit(overlay, (0, 0))
            msg = "VICTORY!" if current_state == STATE_WIN else "DEFEAT"
            color = (100, 255, 100) if current_state == STATE_WIN else (255, 50, 50)
            txt = font_title.render(msg, True, color)
            screen.blit(txt, txt.get_rect(center=(WIDTH//2, HEIGHT//2 - 40)))

            # Game over stats display
            if manager:
                wave_txt = font_btn.render(f"Waves Survived: {manager.wave}", True, C_MONEY)
                screen.blit(wave_txt, wave_txt.get_rect(center=(WIDTH//2, HEIGHT//2 + 20)))

            sub = font_btn.render("Click anywhere to return to Menu", True, (200, 200, 200))
            screen.blit(sub, sub.get_rect(center=(WIDTH//2, HEIGHT//2 + 90)))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()