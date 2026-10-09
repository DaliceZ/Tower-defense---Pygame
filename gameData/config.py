# gameData/config.py

# --- Screen ---
WIDTH = 1280
HEIGHT = 720
FPS = 60
TILE_SIZE = 64

# --- Colors (Professional Palette) ---
C_BG = (30, 33, 40)          # พื้นหลังสีเทาเข้มเกือบดำ
C_PATH = (255, 255, 204)     # ทางเดินสีเทาอ่อน (สว่าง)
C_WALL = (50, 55, 65)        # พื้นที่วางป้อม (เทาเข้ม)
C_BASE = (70, 130, 255)      # ฐานเรา (สีฟ้าสวยๆ)
C_SPAWN = (255, 80, 80)      # จุดเกิด (สีแดงละมุน)

C_UI_BG = (20, 20, 25)       # พื้นหลัง UI
C_TEXT = (255, 255, 255)
C_MONEY = (255, 215, 0)      # สีทอง

# --- Gameplay Stats ---
START_MONEY = 150
START_LIVES = 20
TOWER_COST = 100
MOONFLOWER_COST = 50
POWER_COST = 80             # ราคาสำหรับใช้สกิล
ENEMY_BOUNTY = 15            # เงินที่ได้เมื่อฆ่าศัตรู
MAP_OFFSET_Y = 30       # layout offset y

# --- New Tower Costs ---
SNIPER_COST = 275



# --- Difficulty Presets ---
DIFFICULTY_PRESETS = {
    "easy": {
        "survival_money": 200, "survival_lives": 10, "survival_max_waves": 5,
        "puzzle_money": 900, "puzzle_lives": 3,
        "hp_mult": 0.7, "speed_mult": 0.85, "wave_size_mult": 0.7,
    },
    "normal": {
        "survival_money": 150, "survival_lives": 5, "survival_max_waves": 5,
        "puzzle_money": 700, "puzzle_lives": 1,
        "hp_mult": 1.0, "speed_mult": 1.0, "wave_size_mult": 1.0,
    },
    "hard": {
        "survival_money": 125, "survival_lives": 3, "survival_max_waves": 7,
        "puzzle_money": 500, "puzzle_lives": 1,
        "hp_mult": 1.0, "speed_mult": 1.15, "wave_size_mult": 1.3,
    },
    "nightmare": {
        "survival_money": 100, "survival_lives": 1, "survival_max_waves": 10,
        "puzzle_money": 400, "puzzle_lives": 1,
        "hp_mult": 1.0, "speed_mult": 1.3, "wave_size_mult": 1.5,
    },
}
