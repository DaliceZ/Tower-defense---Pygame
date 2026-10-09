# utils/pathfinding.py
import heapq
from collections import deque

class Pathfinder:
    def __init__(self, matrix):
        self.matrix = [row[:] for row in matrix]
        self.rows = len(matrix)
        self.cols = len(matrix[0])
        self.base_pos = None
        self.spawn_pos = []
        
        # 2 Flow Fields
        self.flow_field_safe = {} # สำหรับตัวฉลาด
        self.flow_field_rush = {} # สำหรับตัวโง่
        
        # Costs
        self.COST_NORMAL = 1
        self.COST_DANGER = 20 # เพิ่มโทษของการเดินผ่านหน้าป้อมให้สูงขึ้น เพื่อให้เห็นผลชัดเจน
        
        for r in range(self.rows):
            for c in range(self.cols):
                if self.matrix[r][c] == 9:
                    self.base_pos = (c, r)
                elif self.matrix[r][c] == 8:
                    self.spawn_pos.append((c, r))
        
        self.calculate_flows()

    def get_neighbors(self, cx, cy):
        moves = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        result = []
        for dx, dy in moves:
            nx, ny = cx + dx, cy + dy
            if 0 <= ny < self.rows and 0 <= nx < self.cols:
                if self.matrix[ny][nx] not in (1, 2): # ไม่ใช่ Wall(1) และ Tower(2)
                    result.append((nx, ny))
        return result

    def calculate_flows(self):
        # 1. Calculate Rush Field (BFS - Shortest Distance ONLY)
        self.flow_field_rush.clear()
        queue = deque([self.base_pos])
        visited = {self.base_pos}
        
        while queue:
            cx, cy = queue.popleft()
            for nx, ny in self.get_neighbors(cx, cy):
                if (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append((nx, ny))
                    self.flow_field_rush[(nx, ny)] = (cx - nx, cy - ny)

        # 2. Calculate Safe Field (Dijkstra - Avoid Danger)
        self.flow_field_safe.clear()
        pq = [(0, self.base_pos)]
        costs = {self.base_pos: 0}
        
        while pq:
            current_cost, (cx, cy) = heapq.heappop(pq)
            if current_cost > costs.get((cx, cy), float('inf')): continue

            for nx, ny in self.get_neighbors(cx, cy):
                # Check danger (Is near tower?)
                is_danger = False
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        tx, ty = nx+dx, ny+dy
                        if 0 <= ty < self.rows and 0 <= tx < self.cols:
                            if self.matrix[ty][tx] == 2: is_danger = True
                
                tile_cost = self.COST_DANGER if is_danger else self.COST_NORMAL
                new_cost = current_cost + tile_cost
                
                if new_cost < costs.get((nx, ny), float('inf')):
                    costs[(nx, ny)] = new_cost
                    heapq.heappush(pq, (new_cost, (nx, ny)))
                    self.flow_field_safe[(nx, ny)] = (cx - nx, cy - ny)

    def get_direction(self, col, row, is_smart=True):
        if is_smart:
            # ถ้าฉลาดให้ใช้ทางปลอดภัย แต่ถ้าทางปลอดภัยตัน (หาไม่เจอ) ให้ใช้ทางลุยแทน
            return self.flow_field_safe.get((col, row), self.flow_field_rush.get((col, row), (0,0)))
        else:
            return self.flow_field_rush.get((col, row), (0, 0))

    def place_tower(self, col, row):
        if (col, row) == self.base_pos or (col, row) in self.spawn_pos: return False
        if self.matrix[row][col] == 0:
            self.matrix[row][col] = 2
            self.calculate_flows()
            
            # Check blocking (ใช้ Rush field เช็ค เพราะเป็นเส้นทางที่สั้นที่สุดที่เป็นไปได้)
            path_exists = True
            for spawn in self.spawn_pos:
                if spawn not in self.flow_field_rush:
                    path_exists = False; break
            
            if not path_exists:
                print("Blocked path!")
                self.matrix[row][col] = 0
                self.calculate_flows()
                return False
            return True
        return False