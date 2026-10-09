# gameInterface/entities.py
import pygame
import math
import random
import os
from gameData.config import *
IMG_CACHE = {}

def get_image(path, scale_size=None):
    key = (path, scale_size)
    if key not in IMG_CACHE:
        try:
            img = pygame.image.load(path).convert_alpha()
            if scale_size:
                img = pygame.transform.scale(img, scale_size)
            IMG_CACHE[key] = img
        except Exception as e:
            print(f"Error loading {path}: {e}")
            surf = pygame.Surface(scale_size if scale_size else (40, 40))
            surf.fill((255, 0, 255))
            IMG_CACHE[key] = surf
    return IMG_CACHE[key]

class FloatingText:
    """ ตัวเลขดาเมจลอยขึ้น """
    def __init__(self, x, y, text, color=(255, 255, 255)):
        self.x = x
        self.y = y
        self.text = str(text)
        self.color = color
        self.life = 30
        self.font = pygame.font.Font(os.path.join("assets", "fonts", "RasterForgeRegular-JpBgm.ttf"), 20)

    def update(self):
        self.y -= 1 # ลอยขึ้น
        self.life -= 1

    def draw(self, screen):
        if self.life > 0:
            surf = self.font.render(self.text, True, self.color)
            alpha = int((self.life / 30) * 255)
            surf.set_alpha(alpha)
            screen.blit(surf, (self.x, self.y))
# ... (Class Particle และ Bullet เหมือนเดิม ไม่ต้องแก้) ...
class Particle:
    """ เอฟเฟกต์ประกายไฟเวลาศัตรูตาย """
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-3, 3)
        self.life = random.randint(20, 40)
        self.color = color
        self.size = random.randint(2, 5)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        self.size = max(0, self.size - 0.1)

    def draw(self, screen):
        if self.life > 0:
            s = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, 200), (self.size, self.size), self.size)
            screen.blit(s, (self.x - self.size, self.y - self.size))

class Bullet:
    def __init__(self, start_pos, target, damage, is_corn=False, is_sniper=False, is_splash=False, splash_radius=0, bullet_color=None):
        self.x, self.y = start_pos
        self.target = target
        self.speed = 12
        self.damage = damage
        self.active = True
        self.radius = 4

        self.is_corn = is_corn
        self.is_sniper = is_sniper
        self.is_splash = is_splash
        self.splash_radius = splash_radius
        self.bullet_color = bullet_color or (255, 255, 100)
        self.glow_color = (255, 200, 50)
        self.angle = 0
        if self.is_corn:
            self.image = get_image(os.path.join("assets", "images", "bullet", "c_bullet.png"), (24, 12))
        elif self.is_sniper:
            self.image = get_image(os.path.join("assets", "images", "bullet", "b_bullet.png"), (24, 12))

    def update(self):
        if not self.target in self.target.alive_list:
            self.active = False
            return

        dx = self.target.x - self.x
        dy = self.target.y - self.y
        dist = math.hypot(dx, dy)

        self.angle = math.degrees(math.atan2(-dy, dx))

        if dist < self.speed:
            if self.is_splash and self.splash_radius > 0:
                # AoE damage: full to target, 50% to others in radius
                self.target.take_damage(self.damage)
                for enemy in self.target.alive_list[:]:
                    if enemy is not self.target:
                        edist = math.hypot(enemy.x - self.target.x, enemy.y - self.target.y)
                        if edist <= self.splash_radius:
                            enemy.take_damage(int(self.damage * 0.5))
            else:
                self.target.take_damage(self.damage)
            self.active = False
        else:
            self.x += (dx / dist) * self.speed
            self.y += (dy / dist) * self.speed

    def draw(self, screen):
        if (self.is_corn or self.is_sniper) and hasattr(self, 'image'):
            rotated_bullet = pygame.transform.rotate(self.image, self.angle)
            bullet_rect = rotated_bullet.get_rect(center=(int(self.x), int(self.y)))
            screen.blit(rotated_bullet, bullet_rect)
        else:
            pygame.draw.circle(screen, self.bullet_color, (int(self.x), int(self.y)), self.radius)
            # Glow effect
            pygame.draw.circle(screen, self.glow_color, (int(self.x), int(self.y)), self.radius + 2, 1)

class SpecialPower:
    # special power
    def __init__(self, pos, tile_size, game_manager):
        self.x, self.y = pos
        self.tile_size = tile_size
        self.game_manager = game_manager
        self.timer = 30 # 0.5 sec delay at 60 FPS
        self.radius = tile_size * 2 # 4x4 radius approx (2 tiles from center)
        self.damage = 500
        self.active = True
        self.state = "placed"
        self.anim_timer = 0
        self.anim_frame = 0
        
    def update(self, enemies):
        if self.state == "placed":
            self.timer -= 1
            self.anim_timer += 1
            if self.timer <= 0:
                # Boom!
                for enemy in enemies:
                    dist = math.hypot(enemy.x - self.x, enemy.y - self.y)
                    if dist <= self.radius:
                        enemy.take_damage(self.damage)
                
                # Setup explosion state
                self.state = "exploding"
                self.anim_timer = 0
                self.anim_frame = 0
        elif self.state == "exploding":
            self.anim_timer += 1
            if self.anim_timer >= 5: # Animation speed (frames per sprite)
                self.anim_timer = 0
                self.anim_frame += 1
                if self.anim_frame > 3: # 4 frames: 0, 1, 2, 3
                    self.active = False
            
    def draw(self, screen):
        # Draw targeting circle that grows or pulses
        if self.state == "placed":
            alpha = int((30 - self.timer) / 30 * 150)
            surf = pygame.Surface((self.radius*2, self.radius*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 50, 50, alpha), (self.radius, self.radius), self.radius)
            pygame.draw.circle(surf, (255, 0, 0, 200), (self.radius, self.radius), self.radius, 2)
            screen.blit(surf, (self.x - self.radius, self.y - self.radius))
            
            # Draw standard tomato (tomato1 or tomato2)
            frame_idx = (self.anim_timer // 15) % 2 + 1
            img_path = os.path.join("assets", "images", "plants", f"tomato{frame_idx}.PNG")
            img = get_image(img_path, (self.tile_size, self.tile_size)) # Smaller (tile size)
            if img: screen.blit(img, img.get_rect(center=(int(self.x), int(self.y))))
            
        elif self.state == "exploding":
            # Just draw explosion, circle is gone
            img_name = f"tomato_exp{self.anim_frame + 1}.PNG"
            img_path = os.path.join("assets", "images", "plants", img_name)
            img = get_image(img_path, (int(self.radius * 2), int(self.radius * 2))) # Bigger (radius * 2)
            if img: screen.blit(img, img.get_rect(center=(int(self.x), int(self.y))))

class Enemy:
    def __init__(self, pos, tile_size, pathfinder, alive_list, game_manager, enemy_type="standard"):

        self.grid_pos = list(pos)
        self.tile_size = tile_size
        self.pathfinder = pathfinder
        self.alive_list = alive_list
        self.game_manager = game_manager
        self.enemy_type = enemy_type
        
        self.game_manager = game_manager
        self.enemy_type = enemy_type
        
        self.x = (pos[0] * tile_size) + (tile_size // 2)
        self.y = (pos[1] * tile_size) + (tile_size // 2) + MAP_OFFSET_Y
        
        # --- Config Speed ---
        # ปรับความเร็ว Puzzle Mode: จาก 0.5 เป็น 0.75 (เร็วขึ้นหน่อย)
        speed_mod = 0.75 if game_manager.mode == "puzzle" else 1.0

        if self.enemy_type == "standard":
            self.speed = 1.2 * speed_mod
            self.max_health = 70
            self.color = (0, 255, 0)
            self.is_smart = True 
            self.bounty = 10

        elif self.enemy_type == "smart":
            self.speed = 2.5 * speed_mod
            self.max_health = 80
            self.color = (180, 60, 220)
            self.is_smart = True 
            self.bounty = 15

        elif self.enemy_type == "tank":
            self.speed = 0.8 * speed_mod
            self.max_health = 450
            self.color = (60, 180, 60)
            self.is_smart = False 
            self.bounty = 20

        elif self.enemy_type == "rusher":
            self.speed = 3.5 * speed_mod
            self.max_health = 70
            self.color = (220, 220, 60)
            self.is_smart = False
            self.bounty = 15
            
        elif self.enemy_type == "boss":
            self.speed = 1.2 * speed_mod
            self.max_health = 4500
            self.color = (150, 0, 0)
            self.is_smart = True
            self.bounty = 0
            
        # Apply difficulty multipliers
        hp_mult = getattr(game_manager, 'hp_mult', 1.0)
        speed_mult_diff = getattr(game_manager, 'speed_mult', 1.0)
        self.max_health = int(self.max_health * hp_mult)
        self.speed = self.speed * speed_mult_diff

        self.health = self.max_health
        self.base_speed = self.speed  # store original speed for slow effect
        self.radius = 24 if self.enemy_type == "boss" else 14
        self.reached_base = False
        self.dead = False
        self.is_visible = False if self.enemy_type == "rusher" else True
        self.slow_timer = 0
        self.slow_factor = 1.0
        
        self.anim_frame = 0
        self.anim_timer = 0
        self.hit_timer = 0
        self.anim_speed = 8
        self.frames = None
        self.hit_frame = None
        
        img_size = (36, 36)
        if self.enemy_type == "standard":
            self.frames = [
                get_image(os.path.join("assets", "images", "hostiles", "slime1.PNG"), img_size),
                get_image(os.path.join("assets", "images", "hostiles", "slime2.PNG"), img_size),
                get_image(os.path.join("assets", "images", "hostiles", "slime3.PNG"), img_size),
                get_image(os.path.join("assets", "images", "hostiles", "slime2.PNG"), img_size),
            ]
            self.hit_frame = get_image(os.path.join("assets", "images", "hostiles", "slime_hit.PNG"), img_size)
        elif self.enemy_type == "smart":
            self.frames = [
                get_image(os.path.join("assets", "images", "hostiles", "skeleton1.PNG"), img_size),
                get_image(os.path.join("assets", "images", "hostiles", "skeleton2.PNG"), img_size),
                get_image(os.path.join("assets", "images", "hostiles", "skeleton3.PNG"), img_size),
                get_image(os.path.join("assets", "images", "hostiles", "skeleton2.PNG"), img_size),
            ]
            self.hit_frame = get_image(os.path.join("assets", "images", "hostiles", "skeleton_hit.PNG"), img_size)
        elif self.enemy_type == "tank":
            tank_size = (54, 54)
            self.frames = [
                get_image(os.path.join("assets", "images", "hostiles", "chick1.PNG"), tank_size),
                get_image(os.path.join("assets", "images", "hostiles", "chick2.PNG"), tank_size),
                get_image(os.path.join("assets", "images", "hostiles", "chick3.PNG"), tank_size),
                get_image(os.path.join("assets", "images", "hostiles", "chick2.PNG"), tank_size),
            ]
            self.hit_frame = get_image(os.path.join("assets", "images", "hostiles", "chick_hit.PNG"), tank_size)
        elif self.enemy_type == "rusher":
            self.frames_invisible = [
                get_image(os.path.join("assets", "images", "hostiles", "ghost1.PNG"), img_size),
                get_image(os.path.join("assets", "images", "hostiles", "ghost2.PNG"), img_size),
                get_image(os.path.join("assets", "images", "hostiles", "ghost3.PNG"), img_size),
                get_image(os.path.join("assets", "images", "hostiles", "ghost2.PNG"), img_size),
            ]
            self.frames_visible = [
                get_image(os.path.join("assets", "images", "hostiles", "ghost1_r.PNG"), img_size),
                get_image(os.path.join("assets", "images", "hostiles", "ghost2_r.PNG"), img_size),
                get_image(os.path.join("assets", "images", "hostiles", "ghost3_r.PNG"), img_size),
                get_image(os.path.join("assets", "images", "hostiles", "ghost2_r.PNG"), img_size),
            ]
            self.frames = self.frames_invisible
            self.hit_frame = get_image(os.path.join("assets", "images", "hostiles", "ghost_hit.PNG"), img_size)
        elif self.enemy_type == "boss":
            boss_size = (80, 80)
            self.frames = [
                get_image(os.path.join("assets", "images", "hostiles", "boss1.PNG"), boss_size),
                get_image(os.path.join("assets", "images", "hostiles", "boss2.PNG"), boss_size),
                get_image(os.path.join("assets", "images", "hostiles", "boss3.PNG"), boss_size),
                get_image(os.path.join("assets", "images", "hostiles", "boss2.PNG"), boss_size),
            ]
            self.hit_frame = get_image(os.path.join("assets", "images", "hostiles", "boss_hit.PNG"), boss_size)

    def take_damage(self, amount):
        self.health -= amount
        self.hit_timer = 30
        self.game_manager.effects.append(FloatingText(self.x, self.y - 20, str(amount)))
        if self.health <= 0:
            self.dead = True
            self.game_manager.add_money(self.bounty)
            for _ in range(6):
                self.game_manager.particles.append(Particle(self.x, self.y, self.color))
            try:
                from utils.load_audio import play_enemy_die_sfx
                play_enemy_die_sfx()
            except Exception:
                pass

    def update(self):
        if self.hit_timer > 0:
            self.hit_timer -= 1

        # Slow effect
        if self.slow_timer > 0:
            self.slow_timer -= 1
            current_speed = self.base_speed * self.slow_factor
        else:
            current_speed = self.base_speed
            self.slow_factor = 1.0

        grid_x = int(self.x // self.tile_size)
        grid_y = int((self.y - MAP_OFFSET_Y) // self.tile_size)

        # ถ้าตำแหน่ง Grid ปัจจุบัน ตรงกับตำแหน่ง Base -> เข้าฐานทันที!
        if self.pathfinder.base_pos and (grid_x, grid_y) == self.pathfinder.base_pos:
             self.reached_base = True
             return

        # Movement Logic
        direction = self.pathfinder.get_direction(grid_x, grid_y, self.is_smart)

        if direction != (0, 0):
            target_px = ((grid_x + direction[0]) * self.tile_size) + (self.tile_size // 2)
            target_py = ((grid_y + direction[1]) * self.tile_size) + (self.tile_size // 2) + MAP_OFFSET_Y

            if not self.is_smart:
                target_px += random.randint(-5, 5)
                target_py += random.randint(-5, 5)

            dx = target_px - self.x
            dy = target_py - self.y
            dist = math.hypot(dx, dy)

            if dist > 0:
                self.x += (dx / dist) * current_speed
                self.y += (dy / dist) * current_speed
        else:
            if self.pathfinder.base_pos:
                 bx = (self.pathfinder.base_pos[0] * self.tile_size) + (self.tile_size // 2)
                 by = (self.pathfinder.base_pos[1] * self.tile_size) + (self.tile_size // 2) + MAP_OFFSET_Y

                 dx = bx - self.x
                 dy = by - self.y
                 dist = math.hypot(dx, dy)

                 # ถ้าใกล้มากแล้ว (< 5px) ก็ถือว่าเข้าเลย
                 if dist < 5:
                     self.reached_base = True
                 elif dist > 0:
                     self.x += (dx / dist) * current_speed
                     self.y += (dy / dist) * current_speed

    def draw(self, screen):
        if self.frames and self.hit_frame:
            if self.enemy_type == "rusher":
                self.frames = self.frames_visible if getattr(self, 'is_visible', True) else self.frames_invisible

            if self.hit_timer > 0:
                current_img = self.hit_frame
            else:
                self.anim_timer += 1
                if self.anim_timer >= self.anim_speed:
                    self.anim_timer = 0
                    self.anim_frame += 1
                if self.anim_frame >= len(self.frames):
                    self.anim_frame = 0
                current_img = self.frames[self.anim_frame]
                
            img_rect = current_img.get_rect(center=(int(self.x), int(self.y)))
            screen.blit(current_img, img_rect)
            
            if self.enemy_type == "boss":
                # Boss Label Map
                font = pygame.font.Font(os.path.join("assets", "fonts", "RasterForgeRegular-JpBgm.ttf"), 14)
                txt = font.render("BOSS", True, (255, 100, 100))
                screen.blit(txt, txt.get_rect(center=(int(self.x), int(self.y - 45))))
        else:
            # Fallback for tank and rusher
            # Outline
            pygame.draw.circle(screen, (30, 30, 30), (int(self.x), int(self.y)), self.radius + 2)
            # Body
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
            
            # Icon/Shape differentiation (Optional visual flair)
            if self.enemy_type == "tank":
                pygame.draw.circle(screen, (30, 30, 30), (int(self.x), int(self.y)), 6) # เกราะกลางอก
            elif self.enemy_type == "boss":
                pygame.draw.circle(screen, (0, 0, 0), (int(self.x), int(self.y)), 12)
                
                # Boss Label Map
                font = pygame.font.Font(os.path.join("assets", "fonts", "RasterForgeRegular-JpBgm.ttf"), 14)
                txt = font.render("BOSS", True, (255, 100, 100))
                screen.blit(txt, txt.get_rect(center=(int(self.x), int(self.y - 35))))
        
        # Slow indicator
        if self.slow_timer > 0:
            slow_surf = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.circle(slow_surf, (100, 200, 255, 150), (8, 8), 8)
            screen.blit(slow_surf, (int(self.x) - 8, int(self.y) + 10))

        # Health Bar
        if self.health < self.max_health:
            bar_w = 24
            bar_h = 4
            hp_percent = max(0, self.health / self.max_health)
            cx, cy = int(self.x) - bar_w//2, int(self.y) + self.radius + 5
            pygame.draw.rect(screen, (50, 0, 0), (cx, cy, bar_w, bar_h))
            pygame.draw.rect(screen, (0, 255, 100), (cx, cy, bar_w * hp_percent, bar_h))

class Tower:
    def __init__(self, grid_pos, tile_size, tower_type="corneto"):
        self.grid_pos = grid_pos
        self.tile_size = tile_size
        self.rect = pygame.Rect(grid_pos[0]*tile_size, grid_pos[1]*tile_size + MAP_OFFSET_Y, tile_size, tile_size)

        self.tower_type = tower_type
        self.total_invested = 0  # track total cost for shovel refund

        # Defaults
        self.is_corn = False
        self.idle_frames = []
        self.atk_frames = []
        self.anim_state = "idle"
        self.anim_timer = 0
        self.anim_frame = 0
        self.anim_speed = 16
        self.angle = 0
        self.cooldown = 0

        if self.tower_type == "moonflower":
            self.range = 180
            self.fire_rate = 0
            self.base_damage = 0
            self.idle_frames = [
                get_image(os.path.join("assets", "images", "plants", "moonflower1.PNG"), (60, 60)),
                get_image(os.path.join("assets", "images", "plants", "moonflower2.PNG"), (60, 60)),
                get_image(os.path.join("assets", "images", "plants", "moonflower3.PNG"), (60, 60)),
                get_image(os.path.join("assets", "images", "plants", "moonflower2.PNG"), (60, 60))
            ]
            # Aura Animation
            rad_size = (self.range * 2, self.range * 2)
            self.aura_frames = [
                get_image(os.path.join("assets", "images", "bullet", "moon_e1.PNG"), rad_size),
                get_image(os.path.join("assets", "images", "bullet", "moon_e2.PNG"), rad_size),
                get_image(os.path.join("assets", "images", "bullet", "moon_e3.PNG"), rad_size)
            ]
            self.aura_timer = 0
            self.aura_frame = 0
            self.aura_speed = 45

        elif self.tower_type == "sniper":
            self.range = 450
            self.fire_rate = 250
            self.base_damage = 300
            self.idle_frames = [
                get_image(os.path.join("assets", "images", "plants", "blueberry1.PNG"), (60, 60)),
                get_image(os.path.join("assets", "images", "plants", "blueberry2.PNG"), (60, 60))
            ]
            self.atk_frames = [
                get_image(os.path.join("assets", "images", "plants", "blueberry_atk1.PNG"), (60, 60)),
                get_image(os.path.join("assets", "images", "plants", "blueberry_atk2.PNG"), (60, 60)),
                get_image(os.path.join("assets", "images", "plants", "blueberry_atk3.PNG"), (60, 60))
            ]

        else:  # corneto
            self.is_corn = True
            self.range = 220
            self.fire_rate = 40
            self.base_damage = 35
            self.idle_frames = [
                get_image(os.path.join("assets", "images", "plants", "corn1.PNG"), (60, 60)),
                get_image(os.path.join("assets", "images", "plants", "corn2.PNG"), (60, 60)),
                get_image(os.path.join("assets", "images", "plants", "corn3.PNG"), (60, 60)),
                get_image(os.path.join("assets", "images", "plants", "corn2.PNG"), (60, 60))
            ]
            self.atk_frames = [
                get_image(os.path.join("assets", "images", "plants", "corn_atk1.PNG"), (60, 60)),
                get_image(os.path.join("assets", "images", "plants", "corn_atk2.PNG"), (60, 60))
            ]

        self.base_range = self.range
        self.base_fire_rate = self.fire_rate

    def update(self, enemies, bullets):
        if self.cooldown > 0:
            self.cooldown -= 1

        center = self.rect.center

        if self.tower_type == "moonflower":
            for enemy in enemies:
                if enemy.enemy_type == "rusher":
                    dist = math.hypot(center[0] - enemy.x, center[1] - enemy.y)
                    if dist <= self.range:
                        enemy.is_visible = True
            self.anim_state = "idle"
            self.anim_timer += 1
            if self.anim_timer >= self.anim_speed:
                self.anim_timer = 0
                self.anim_frame += 1
            if self.anim_frame >= len(self.idle_frames):
                self.anim_frame = 0
            self.aura_timer += 1
            if self.aura_timer >= self.aura_speed:
                self.aura_timer = 0
                self.aura_frame += 1
            if self.aura_frame >= len(self.aura_frames):
                self.aura_frame = 0
            return

        # For shooting towers: corneto, sniper
        target = None
        closest_dist = self.range
        for enemy in enemies:
            can_see = getattr(enemy, 'is_visible', True) or self.tower_type == "sniper"
            if can_see:
                dist = math.hypot(center[0] - enemy.x, center[1] - enemy.y)
                if dist < closest_dist:
                    closest_dist = dist
                    target = enemy

        # Attack/idle animation for towers with atk_frames
        if self.atk_frames:
            if target:
                if self.anim_state == "idle" and self.cooldown <= 0:
                    self.anim_state = "attack"
                    self.anim_frame = 0
                    self.anim_timer = 0
            
            if self.anim_state == "attack":
                self.anim_timer += 1
                if self.anim_timer >= self.anim_speed:
                    self.anim_timer = 0
                    self.anim_frame += 1
                    
                    # Sniper fires at the end of its animation
                    if self.tower_type == "sniper" and self.anim_frame == len(self.atk_frames) - 1:
                        if target:  # Target might have died or moved, but we shoot at the last known or current target
                            bullets.append(Bullet(center, target, damage=self.base_damage,
                                                  bullet_color=(255, 50, 50), is_sniper=True))
                            try:
                                from utils.load_audio import play_tower_shoot_sfx
                                play_tower_shoot_sfx()
                            except Exception:
                                pass
                        self.cooldown = self.fire_rate

                    # Stop at the last frame, don't loop
                    if self.anim_frame >= len(self.atk_frames):
                        self.anim_state = "idle"
                        self.anim_frame = 0
            else:
                self.anim_state = "idle"
                self.anim_timer += 1
                if self.anim_timer >= self.anim_speed:
                    self.anim_timer = 0
                    self.anim_frame += 1
                if self.idle_frames and self.anim_frame >= len(self.idle_frames):
                    self.anim_frame = 0
        else:
            # Idle-only animation for towers without atk_frames
            self.anim_timer += 1
            if self.anim_timer >= self.anim_speed:
                self.anim_timer = 0
                self.anim_frame = (self.anim_frame + 1) % max(1, len(self.idle_frames)) if self.idle_frames else 0

        if target:
            dx = target.x - center[0]
            dy = target.y - center[1]
            self.angle = math.degrees(math.atan2(-dy, dx))

            # Non-sniper towers fire immediately when cooldown is 0
            if self.cooldown <= 0 and self.tower_type != "sniper":
                dmg = self.base_damage
                bullets.append(Bullet(center, target, damage=dmg, is_corn=self.is_corn))
                self.cooldown = self.fire_rate
                # Start attack animation reliably
                self.anim_state = "attack"
                self.anim_frame = 0
                self.anim_timer = 0
                try:
                    from utils.load_audio import play_tower_shoot_sfx
                    play_tower_shoot_sfx()
                except Exception:
                    pass

    def draw(self, screen, is_hovered=False):
        cx, cy = self.rect.center

        # Draw Moonflower Aura
        if self.tower_type == "moonflower" and getattr(self, "aura_frames", []):
            aura_img = self.aura_frames[self.aura_frame]
            if aura_img:
                screen.blit(aura_img, aura_img.get_rect(center=(cx, cy)))

        # Range Indicator on hover
        if is_hovered:
            range_surf = pygame.Surface((self.range*2, self.range*2), pygame.SRCALPHA)
            range_color = (80, 180, 255, 40)
            border_color = (80, 180, 255, 100)
            if self.tower_type == "sniper":
                range_color = (255, 50, 50, 40)
                border_color = (255, 50, 50, 100)
            pygame.draw.circle(range_surf, range_color, (self.range, self.range), self.range)
            pygame.draw.circle(range_surf, border_color, (self.range, self.range), self.range, 1)
            screen.blit(range_surf, (cx - self.range, cy - self.range))

        # Draw tower sprite
        if self.idle_frames:
            frames = self.atk_frames if self.anim_state == "attack" and self.atk_frames else self.idle_frames
            current_frame = frames[self.anim_frame % len(frames)]
            img_rect = current_frame.get_rect(center=(cx, cy))
            screen.blit(current_frame, img_rect)
        else:
            # Fallback generic turret (shouldn't happen now)
            pygame.draw.rect(screen, (100, 100, 120), self.rect, border_radius=4)
            pygame.draw.rect(screen, (200, 200, 200), self.rect, 2, border_radius=4)