# gameData/map_layout.py

import random
from collections import deque

TILE_SIZE = 64

# 0: Floor (Walkable & Buildable) -> พื้นที่เดินได้และวางป้อมได้
# 1: Wall (Obstacle) -> กำแพงถาวร
# 8: Spawn
# 9: Base

ROWS = 11
COLS = 20
SPAWN_POS = (0, 1)   # (col, row)
BASE_POS = (18, 10)   # (col, row)

# Wall cluster shapes: list of (dc, dr) offsets from anchor
_SHAPES = [
    # horizontal bar (3-4 tiles)
    [(0, 0), (1, 0), (2, 0)],
    [(0, 0), (1, 0), (2, 0), (3, 0)],
    # vertical bar (3-4 tiles)
    [(0, 0), (0, 1), (0, 2)],
    [(0, 0), (0, 1), (0, 2), (0, 3)],
    # L-shapes
    [(0, 0), (1, 0), (0, 1)],
    [(0, 0), (1, 0), (1, 1)],
    # 2x2 block
    [(0, 0), (1, 0), (0, 1), (1, 1)],
    # 2-tile bar
    [(0, 0), (1, 0)],
    [(0, 0), (0, 1)],
]

def _bfs_reachable(grid, start_col, start_row, goal_col, goal_row):
    """BFS check: can we reach (goal_col, goal_row) from (start_col, start_row)?"""
    rows = len(grid)
    cols = len(grid[0])
    visited = set()
    queue = deque([(start_col, start_row)])
    visited.add((start_col, start_row))
    while queue:
        cx, cy = queue.popleft()
        if cx == goal_col and cy == goal_row:
            return True
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < cols and 0 <= ny < rows and (nx, ny) not in visited:
                if grid[ny][nx] != 1:
                    visited.add((nx, ny))
                    queue.append((nx, ny))
    return False


def generate_random_map():
    """Generate a random map with wall clusters, guaranteed path from spawn to base."""
    # 1. Initialize empty grid with border walls
    grid = [[0] * COLS for _ in range(ROWS)]

    # Border walls
    for c in range(COLS):
        grid[0][c] = 1
        grid[ROWS - 1][c] = 1
    for r in range(ROWS):
        grid[r][0] = 1
        grid[r][COLS - 1] = 1

    # Place spawn and base
    sc, sr = SPAWN_POS
    bc, br = BASE_POS
    grid[sr][sc] = 8
    grid[br][bc] = 9

    # Protected zones: don't place walls near spawn or base (2-tile radius)
    protected = set()
    for dc in range(-2, 3):
        for dr in range(-2, 3):
            protected.add((sc + dc, sr + dr))
            protected.add((bc + dc, br + dr))

    # 2. Place random wall clusters
    num_clusters = random.randint(5, 8)
    for _ in range(num_clusters):
        placed = False
        for _retry in range(10):
            shape = random.choice(_SHAPES)
            # Pick random anchor inside the map (avoid edges)
            anchor_c = random.randint(2, COLS - 4)
            anchor_r = random.randint(2, ROWS - 4)

            # Compute actual wall positions
            cells = [(anchor_c + dc, anchor_r + dr) for dc, dr in shape]

            # Validate: all cells must be inside map, floor, and not protected
            valid = True
            for c, r in cells:
                if not (1 <= c < COLS - 1 and 1 <= r < ROWS - 1):
                    valid = False
                    break
                if grid[r][c] != 0:
                    valid = False
                    break
                if (c, r) in protected:
                    valid = False
                    break
            if not valid:
                continue

            # Tentatively place walls
            for c, r in cells:
                grid[r][c] = 1

            # 3. BFS check path from spawn to base
            if _bfs_reachable(grid, sc, sr, bc, br):
                placed = True
                break
            else:
                # 4. Revert walls
                for c, r in cells:
                    grid[r][c] = 0

    return grid


# Fallback static map
test_map = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1],
    [1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
    [1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
    [1, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 9, 1],
]