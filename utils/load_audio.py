import pygame
import os

# พยายาม Init เสียง ถ้าไม่ได้ให้ปิดระบบเสียงไปเลย
AUDIO_ENABLED = False
try:
    pygame.mixer.init()
    AUDIO_ENABLED = True
except pygame.error:
    print("[WARNING] Audio device not found. Sound disabled.")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Global SFX variables
button_sfx = None
tower_shoot_sfx = None
enemy_die_sfx = None
tower_place_sfx = None
wave_start_sfx = None
game_over_sfx = None
victory_sfx = None

# BGM paths
menu_bgm_path = os.path.join(BASE_DIR, "assets", "sfx", "menu_bgm.mp3")
game_bgm_path = os.path.join(BASE_DIR, "assets", "sfx", "game_bgm.mp3")

def _load_sound(filename, volume=1.0):
    """Helper to load a single sound file with graceful fallback."""
    path = os.path.join(BASE_DIR, "assets", "sfx", filename)
    if os.path.exists(path):
        try:
            snd = pygame.mixer.Sound(path)
            snd.set_volume(volume)
            return snd
        except pygame.error as e:
            print(f"[WARNING] Could not load {filename}: {e}")
    else:
        print(f"[WARNING] Sound file not found: {path}")
    return None

def load_sfx():
    global button_sfx, tower_shoot_sfx, enemy_die_sfx, tower_place_sfx
    global wave_start_sfx, game_over_sfx, victory_sfx

    if not AUDIO_ENABLED:
        return

    try:
        button_sfx = _load_sound("button.wav", 1.0)
        tower_shoot_sfx = _load_sound("tower_shoot.wav", 0.5)
        enemy_die_sfx = _load_sound("enemy_die.wav", 0.6)
        tower_place_sfx = _load_sound("tower_place.wav", 0.7)
        wave_start_sfx = _load_sound("wave_start.wav", 0.8)
        game_over_sfx = _load_sound("game_over.wav", 0.8)
        victory_sfx = _load_sound("victory.wav", 0.8)
    except pygame.error as e:
        print(f"Error loading sound files: {e}")

def play_button_sfx():
    if AUDIO_ENABLED and button_sfx:
        button_sfx.play()

def play_tower_shoot_sfx():
    if AUDIO_ENABLED and tower_shoot_sfx:
        tower_shoot_sfx.play()

def play_enemy_die_sfx():
    if AUDIO_ENABLED and enemy_die_sfx:
        enemy_die_sfx.play()

def play_tower_place_sfx():
    if AUDIO_ENABLED and tower_place_sfx:
        tower_place_sfx.play()

def play_wave_start_sfx():
    if AUDIO_ENABLED and wave_start_sfx:
        wave_start_sfx.play()

def play_game_over_sfx():
    if AUDIO_ENABLED and game_over_sfx:
        game_over_sfx.play()

def play_victory_sfx():
    if AUDIO_ENABLED and victory_sfx:
        victory_sfx.play()

def play_bgm(track="menu"):
    """Play background music. track: 'menu' or 'game'"""
    if not AUDIO_ENABLED:
        return
    path = menu_bgm_path if track == "menu" else game_bgm_path
    if os.path.exists(path):
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0.4)
            pygame.mixer.music.play(-1)  # loop forever
        except pygame.error as e:
            print(f"[WARNING] Could not play BGM: {e}")

def stop_bgm():
    """Stop background music."""
    if AUDIO_ENABLED:
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass
