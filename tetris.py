"""
俄罗斯方块 (Tetris)
使用 pygame 实现

操作说明:
  ← / →  左右移动
  ↑      旋转
  ↓      软降（加速下落）
  空格   硬降（瞬间落底）
  P      暂停/继续
  R      重新开始
  ESC    退出
"""

import pygame
import random
import sys

# ── 常量 ──────────────────────────────────────────────
COLS = 10
ROWS = 20
CELL = 30
SIDEBAR = 160
WIDTH = COLS * CELL + SIDEBAR
HEIGHT = ROWS * CELL
FPS = 60

# 颜色 (R, G, B)
BLACK = (15, 15, 25)
GRID_COLOR = (35, 35, 55)
WHITE = (230, 230, 240)
GRAY = (100, 100, 120)
RED = (220, 60, 60)

# 七种方块及其颜色
SHAPES = {
    "I": {"color": (0, 240, 240), "cells": [(0, 1), (1, 1), (2, 1), (3, 1)]},
    "O": {"color": (240, 240, 0), "cells": [(1, 0), (2, 0), (1, 1), (2, 1)]},
    "T": {"color": (180, 0, 240), "cells": [(1, 0), (0, 1), (1, 1), (2, 1)]},
    "S": {"color": (0, 240, 0), "cells": [(1, 0), (2, 0), (0, 1), (1, 1)]},
    "Z": {"color": (240, 0, 0), "cells": [(0, 0), (1, 0), (1, 1), (2, 1)]},
    "J": {"color": (0, 0, 240), "cells": [(0, 0), (0, 1), (1, 1), (2, 1)]},
    "L": {"color": (240, 160, 0), "cells": [(2, 0), (0, 1), (1, 1), (2, 1)]},
}

# 每消除一行得分，连消有加成
LINE_SCORES = {1: 100, 2: 300, 3: 500, 4: 800}

# 每消除 10 行升一级，下落速度加快
LEVEL_SPEED = {0: 800, 1: 650, 2: 520, 3: 410, 4: 320, 5: 250, 6: 190, 7: 140, 8: 100, 9: 70}


def rotate_cells(cells, pivot=(1, 1)):
    """绕 pivot 顺时针旋转 90°"""
    px, py = pivot
    return [(py - (y - py) + px, (x - px) + py) for x, y in cells]


class Piece:
  def __init__(self, shape_key=None):
    self.shape_key = shape_key or random.choice(list(SHAPES.keys()))
    info = SHAPES[self.shape_key]
    self.color = info["color"]
    self.cells = list(info["cells"])
    self.x = COLS // 2 - 2
    self.y = 0

  def rotated(self):
    p = Piece.__new__(Piece)
    p.shape_key = self.shape_key
    p.color = self.color
    p.cells = rotate_cells(self.cells)
    p.x, p.y = self.x, self.y
    return p

  def absolute_cells(self):
    return [(self.x + cx, self.y + cy) for cx, cy in self.cells]


class TetrisGame:
  def __init__(self):
    pygame.init()
    pygame.display.set_caption("俄罗斯方块 Tetris")
    self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
    self.clock = pygame.time.Clock()
    self.font = pygame.font.SysFont("microsoftyahei,simsun,arial", 18)
    self.font_big = pygame.font.SysFont("microsoftyahei,simsun,arial", 28, bold=True)
    self.reset()

  def reset(self):
    self.board = [[None] * COLS for _ in range(ROWS)]
    self.score = 0
    self.lines = 0
    self.level = 0
    self.game_over = False
    self.paused = False
    self.current = Piece()
    self.next_piece = Piece()
    self.drop_timer = 0
    self.drop_interval = LEVEL_SPEED[0]

  def level_up(self):
    self.level = min(self.lines // 10, 9)
    self.drop_interval = LEVEL_SPEED[self.level]

  def valid(self, piece):
    for x, y in piece.absolute_cells():
      if x < 0 or x >= COLS or y >= ROWS:
        return False
      if y >= 0 and self.board[y][x] is not None:
        return False
    return True

  def lock_piece(self):
    for x, y in self.current.absolute_cells():
      if y < 0:
        self.game_over = True
        return
      self.board[y][x] = self.current.color

    cleared = self.clear_lines()
    if cleared:
      self.lines += cleared
      self.score += LINE_SCORES.get(cleared, cleared * 100) * (self.level + 1)
      self.level_up()

    self.current = self.next_piece
    self.next_piece = Piece()
    if not self.valid(self.current):
      self.game_over = True

  def clear_lines(self):
    new_board = [row for row in self.board if any(c is None for c in row)]
    cleared = ROWS - len(new_board)
    for _ in range(cleared):
      new_board.insert(0, [None] * COLS)
    self.board = new_board
    return cleared

  def move(self, dx, dy):
    moved = Piece.__new__(Piece)
    moved.shape_key = self.current.shape_key
    moved.color = self.current.color
    moved.cells = list(self.current.cells)
    moved.x = self.current.x + dx
    moved.y = self.current.y + dy
    if self.valid(moved):
      self.current = moved
      return True
    return False

  def rotate(self):
    rotated = self.current.rotated()
    # 简易 wall-kick：尝试左右偏移
    for dx in (0, -1, 1, -2, 2):
      rotated.x = self.current.x + dx
      rotated.y = self.current.y
      if self.valid(rotated):
        self.current = rotated
        return

  def hard_drop(self):
    while self.move(0, 1):
      self.score += 2
    self.lock_piece()

  def soft_drop(self):
    if self.move(0, 1):
      self.score += 1

  def update(self, dt):
    if self.game_over or self.paused:
      return
    self.drop_timer += dt
    if self.drop_timer >= self.drop_interval:
      self.drop_timer = 0
      if not self.move(0, 1):
        self.lock_piece()

  # ── 绘制 ──────────────────────────────────────────
  def draw_cell(self, x, y, color, offset_x=0, offset_y=0):
    rect = pygame.Rect(offset_x + x * CELL + 1, offset_y + y * CELL + 1, CELL - 2, CELL - 2)
    pygame.draw.rect(self.screen, color, rect, border_radius=3)
    highlight = tuple(min(c + 60, 255) for c in color)
    pygame.draw.line(self.screen, highlight, rect.topleft, rect.topright, 2)
    pygame.draw.line(self.screen, highlight, rect.topleft, rect.bottomleft, 2)

  def draw_board(self):
    self.screen.fill(BLACK)
    for y in range(ROWS):
      for x in range(COLS):
        pygame.draw.rect(
          self.screen, GRID_COLOR,
          (x * CELL, y * CELL, CELL, CELL), 1
        )
        if self.board[y][x]:
          self.draw_cell(x, y, self.board[y][x])

  def draw_piece(self, piece, offset_x=0, ghost=False):
    ghost_y = piece.y
    if not ghost:
      for x, y in piece.absolute_cells():
        if y >= 0:
          self.draw_cell(x, y, piece.color, offset_x)
      return
    # 绘制 ghost（落点预览）
    ghost = Piece.__new__(Piece)
    ghost.shape_key = piece.shape_key
    ghost.color = piece.color
    ghost.cells = list(piece.cells)
    ghost.x, ghost.y = piece.x, piece.y
    while self.valid(ghost):
      test = Piece.__new__(Piece)
      test.shape_key = ghost.shape_key
      test.color = ghost.color
      test.cells = list(ghost.cells)
      test.x, test.y = ghost.x, ghost.y + 1
      if self.valid(test):
        ghost.y += 1
      else:
        break
    for x, y in ghost.absolute_cells():
      if y >= 0:
        rect = pygame.Rect(offset_x + x * CELL + 1, y * CELL + 1, CELL - 2, CELL - 2)
        pygame.draw.rect(self.screen, piece.color, rect, 2, border_radius=3)

  def draw_sidebar(self):
    sx = COLS * CELL + 10
    # 标题
    title = self.font_big.render("俄罗斯方块", True, WHITE)
    self.screen.blit(title, (sx, 20))

    labels = [
      ("得分", str(self.score)),
      ("行数", str(self.lines)),
      ("等级", str(self.level + 1)),
    ]
    y = 70
    for label, value in labels:
      self.screen.blit(self.font.render(label, True, GRAY), (sx, y))
      self.screen.blit(self.font_big.render(value, True, WHITE), (sx, y + 22))
      y += 65

    # 下一个方块预览
    self.screen.blit(self.font.render("下一个", True, GRAY), (sx, y))
    for cx, cy in self.next_piece.cells:
      self.draw_cell(cx, cy, self.next_piece.color, sx + 10, y + 30)

    # 操作说明
    y = HEIGHT - 180
    self.screen.blit(self.font.render("操作说明", True, GRAY), (sx, y))
    hints = ["← → 移动", "↑ 旋转", "↓ 软降", "空格 硬降", "P 暂停", "R 重开"]
    for i, hint in enumerate(hints):
      self.screen.blit(self.font.render(hint, True, GRAY), (sx, y + 22 + i * 22))

  def draw_overlay(self, text, sub=""):
    overlay = pygame.Surface((COLS * CELL, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    self.screen.blit(overlay, (0, 0))
    main = self.font_big.render(text, True, WHITE)
    self.screen.blit(main, main.get_rect(center=(COLS * CELL // 2, HEIGHT // 2 - 20)))
    if sub:
      sub_surf = self.font.render(sub, True, GRAY)
      self.screen.blit(sub_surf, sub_surf.get_rect(center=(COLS * CELL // 2, HEIGHT // 2 + 20)))

  def draw(self):
    self.draw_board()
    if not self.game_over and not self.paused:
      self.draw_piece(self.current, ghost=True)
      self.draw_piece(self.current)
    self.draw_sidebar()
    if self.paused:
      self.draw_overlay("已暂停", "按 P 继续")
    if self.game_over:
      self.draw_overlay("游戏结束", "按 R 重新开始")
    pygame.display.flip()

  def handle_key(self, key):
    if key == pygame.K_ESCAPE:
      pygame.quit()
      sys.exit()
    if key == pygame.K_r:
      self.reset()
      return
    if self.game_over:
      return
    if key == pygame.K_p:
      self.paused = not self.paused
      return
    if self.paused:
      return
    if key == pygame.K_LEFT:
      self.move(-1, 0)
    elif key == pygame.K_RIGHT:
      self.move(1, 0)
    elif key == pygame.K_DOWN:
      self.soft_drop()
    elif key == pygame.K_UP:
      self.rotate()
    elif key == pygame.K_SPACE:
      self.hard_drop()

  def run(self):
    running = True
    while running:
      dt = self.clock.tick(FPS)
      for event in pygame.event.get():
        if event.type == pygame.QUIT:
          running = False
        elif event.type == pygame.KEYDOWN:
          self.handle_key(event.key)
      self.update(dt)
      self.draw()
    pygame.quit()


if __name__ == "__main__":
  TetrisGame().run()
