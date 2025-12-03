"""
Modern Sudoku desktop app with a neon-dark UI, home menu, and smooth hover
interactions. Ready for PyInstaller packaging into a single executable.
"""

from __future__ import annotations

import random
import time
import tkinter as tk
from dataclasses import dataclass, field
from tkinter import messagebox
from typing import Dict, List, Optional, Set, Tuple

Board = List[List[int]]
Coord = Tuple[int, int]


# --------------------------- Sudoku engine --------------------------------- #


def deep_copy_board(board: Board) -> Board:
    return [row[:] for row in board]


class SudokuGenerator:
    """Generate full Sudoku boards and dig holes while keeping uniqueness."""

    def __init__(self) -> None:
        self.size = 9
        self.box = 3

    def _find_empty(self, board: Board) -> Optional[Coord]:
        for r in range(self.size):
            for c in range(self.size):
                if board[r][c] == 0:
                    return r, c
        return None

    def _is_valid(self, board: Board, row: int, col: int, num: int) -> bool:
        if num in board[row]:
            return False
        if any(board[r][col] == num for r in range(self.size)):
            return False
        start_r = (row // self.box) * self.box
        start_c = (col // self.box) * self.box
        for r in range(start_r, start_r + self.box):
            for c in range(start_c, start_c + self.box):
                if board[r][c] == num:
                    return False
        return True

    def _solve(self, board: Board) -> bool:
        empty = self._find_empty(board)
        if not empty:
            return True
        r, c = empty
        nums = list(range(1, 10))
        random.shuffle(nums)
        for num in nums:
            if self._is_valid(board, r, c, num):
                board[r][c] = num
                if self._solve(board):
                    return True
                board[r][c] = 0
        return False

    def _count_solutions(self, board: Board, limit: int = 2) -> int:
        empty = self._find_empty(board)
        if not empty:
            return 1
        r, c = empty
        count = 0
        for num in range(1, 10):
            if self._is_valid(board, r, c, num):
                board[r][c] = num
                count += self._count_solutions(board, limit)
                board[r][c] = 0
                if count >= limit:
                    break
        return count

    def _dig_holes(self, board: Board, holes: int) -> None:
        attempts = holes * 6
        removed = 0
        while removed < holes and attempts > 0:
            r = random.randint(0, 8)
            c = random.randint(0, 8)
            if board[r][c] == 0:
                attempts -= 1
                continue
            backup = board[r][c]
            board[r][c] = 0
            board_copy = deep_copy_board(board)
            if self._count_solutions(board_copy) == 1:
                removed += 1
            else:
                board[r][c] = backup
            attempts -= 1

    def generate(self, difficulty: str) -> Tuple[Board, Board]:
        config = DIFFICULTIES.get(difficulty, DIFFICULTIES["medium"])
        board: Board = [[0] * 9 for _ in range(9)]
        self._solve(board)
        solution = deep_copy_board(board)
        self._dig_holes(board, config["holes"])
        return board, solution


def find_conflicts(board: Board) -> Set[Coord]:
    """Return coordinates that violate Sudoku rules."""
    conflicts: Set[Coord] = set()
    # Rows and columns
    for idx in range(9):
        seen_row: Dict[int, List[int]] = {}
        seen_col: Dict[int, List[int]] = {}
        for j in range(9):
            row_val = board[idx][j]
            col_val = board[j][idx]
            if row_val:
                seen_row.setdefault(row_val, []).append(j)
            if col_val:
                seen_col.setdefault(col_val, []).append(j)
        for cols in seen_row.values():
            if len(cols) > 1:
                for col in cols:
                    conflicts.add((idx, col))
        for rows in seen_col.values():
            if len(rows) > 1:
                for row in rows:
                    conflicts.add((row, idx))
    # Boxes
    for br in range(0, 9, 3):
        for bc in range(0, 9, 3):
            seen_box: Dict[int, List[Coord]] = {}
            for r in range(br, br + 3):
                for c in range(bc, bc + 3):
                    val = board[r][c]
                    if val:
                        seen_box.setdefault(val, []).append((r, c))
            for coords in seen_box.values():
                if len(coords) > 1:
                    conflicts.update(coords)
    return conflicts


# --------------------------- Game state ------------------------------------ #

DIFFICULTIES: Dict[str, Dict[str, int]] = {
    "easy": {"holes": 36, "hints": 4, "max_mistakes": 5},
    "medium": {"holes": 45, "hints": 3, "max_mistakes": 4},
    "hard": {"holes": 52, "hints": 2, "max_mistakes": 3},
    "expert": {"holes": 58, "hints": 1, "max_mistakes": 3},
}


@dataclass
class SudokuGame:
    puzzle: Board
    solution: Board
    difficulty: str
    hints_left: int
    max_mistakes: int
    mistakes: int = 0
    notes: Dict[Coord, Set[int]] = field(default_factory=dict)
    history: List[Tuple[Board, Dict[Coord, Set[int]], int, int]] = field(
        default_factory=list
    )
    future: List[Tuple[Board, Dict[Coord, Set[int]], int, int]] = field(
        default_factory=list
    )

    @classmethod
    def new(cls, difficulty: str) -> "SudokuGame":
        generator = SudokuGenerator()
        puzzle, solution = generator.generate(difficulty)
        cfg = DIFFICULTIES.get(difficulty, DIFFICULTIES["medium"])
        return cls(
            puzzle=puzzle,
            solution=solution,
            difficulty=difficulty,
            hints_left=cfg["hints"],
            max_mistakes=cfg["max_mistakes"],
        )

    @property
    def fixed_cells(self) -> Set[Coord]:
        return {(r, c) for r in range(9) for c in range(9) if self.puzzle[r][c] != 0}

    def push_state(self) -> None:
        self.history.append(
            (
                deep_copy_board(self.puzzle),
                {k: set(v) for k, v in self.notes.items()},
                self.mistakes,
                self.hints_left,
            )
        )
        self.future.clear()

    def undo(self) -> None:
        if not self.history:
            return
        snapshot = self.history.pop()
        self.future.append(
            (
                deep_copy_board(self.puzzle),
                {k: set(v) for k, v in self.notes.items()},
                self.mistakes,
                self.hints_left,
            )
        )
        self.puzzle, self.notes, self.mistakes, self.hints_left = snapshot

    def redo(self) -> None:
        if not self.future:
            return
        snapshot = self.future.pop()
        self.history.append(
            (
                deep_copy_board(self.puzzle),
                {k: set(v) for k, v in self.notes.items()},
                self.mistakes,
                self.hints_left,
            )
        )
        self.puzzle, self.notes, self.mistakes, self.hints_left = snapshot

    def set_value(self, coord: Coord, value: int) -> None:
        if coord in self.fixed_cells:
            return
        self.push_state()
        r, c = coord
        self.puzzle[r][c] = value
        self.notes.pop(coord, None)
        if value and value != self.solution[r][c]:
            self.mistakes += 1

    def toggle_note(self, coord: Coord, value: int) -> None:
        if coord in self.fixed_cells:
            return
        self.push_state()
        note_set = self.notes.setdefault(coord, set())
        if value in note_set:
            note_set.remove(value)
        else:
            note_set.add(value)
        if not note_set:
            self.notes.pop(coord, None)

    def hint(self, coord: Coord) -> Optional[int]:
        if self.hints_left <= 0 or coord in self.fixed_cells:
            return None
        self.push_state()
        r, c = coord
        self.puzzle[r][c] = self.solution[r][c]
        self.notes.pop(coord, None)
        self.hints_left -= 1
        return self.puzzle[r][c]

    def is_complete(self) -> bool:
        return all(
            self.puzzle[r][c] == self.solution[r][c]
            for r in range(9)
            for c in range(9)
        )


# --------------------------- UI layer -------------------------------------- #


class SudokuApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Sudoku — Vibe Edition")
        self.geometry("980x860")
        self.resizable(False, False)
        self.configure(bg="#050915")

        self.board_px = 570
        self.cell_px = self.board_px // 9
        self.selected: Optional[Coord] = None
        self.pencil_mode = False
        self.start_time = time.time()
        self.running = True

        self.game = SudokuGame.new("medium")
        self.home_difficulty = "medium"

        self.accent_colors = ["#22d3ee", "#a855f7", "#38bdf8", "#f472b6"]
        self.accent_index = 0

        self._setup_background()
        self._build_home()
        self._build_game()
        self.show_home()

        self.bind("<Key>", self.on_key)
        self.after(250, self._tick_timer)
        self.after(1200, self._animate_accent)

    # --------------------------- Layout ---------------------------------- #

    def _setup_background(self) -> None:
        self.bg_canvas = tk.Canvas(self, bd=0, highlightthickness=0)
        self.bg_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._draw_background()
        self.layer = tk.Frame(self, bg="#050915")
        self.layer.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _draw_background(self) -> None:
        self.bg_canvas.delete("all")
        width = 1000
        height = 900
        steps = 40
        for i in range(steps):
            ratio = i / steps
            color = self._blend("#0b1220", "#0d1b2e", ratio)
            self.bg_canvas.create_rectangle(
                0, height * ratio, width, height * (ratio + 1 / steps), fill=color, outline=""
            )
        for cx, cy, r, color in [
            (780, 160, 140, "#1b4e63"),
            (220, 260, 180, "#162447"),
            (520, 620, 200, "#122034"),
        ]:
            self.bg_canvas.create_oval(
                cx - r,
                cy - r,
                cx + r,
                cy + r,
                fill=color,
                outline="",
            )

    def _build_home(self) -> None:
        self.home_frame = tk.Frame(self.layer, bg="#050915", padx=32, pady=32)

        hero = tk.Frame(self.home_frame, bg="#0b1220", bd=0, highlightthickness=0)
        hero.pack(fill="x", pady=(18, 24))

        title = tk.Label(
            hero,
            text="Sudoku",
            fg="#e2e8f0",
            bg="#0b1220",
            font=("Helvetica", 40, "bold"),
        )
        subtitle = tk.Label(
            hero,
            text="Neon calm. Sharp focus. Take on fresh puzzles with hints, pencil marks, and smooth controls.",
            fg="#94a3b8",
            bg="#0b1220",
            font=("Helvetica", 14),
            wraplength=760,
            justify="left",
        )
        title.pack(anchor="w")
        subtitle.pack(anchor="w", pady=(10, 2))

        cta = tk.Frame(self.home_frame, bg="#050915")
        cta.pack(fill="x", pady=(6, 10))

        self.home_status = tk.Label(
            cta,
            text="Pick a vibe, then start.",
            fg="#94a3b8",
            bg="#050915",
            font=("Helvetica", 12),
        )
        self.home_status.pack(anchor="w", pady=(0, 6))

        diff_bar = tk.Frame(cta, bg="#050915")
        diff_bar.pack(anchor="w", pady=8)
        self.home_diff_buttons: List[tk.Button] = []
        for diff in ["easy", "medium", "hard", "expert"]:
            btn = self._make_button(
                diff.title(),
                lambda d=diff: self._select_home_difficulty(d),
                primary=diff == self.home_difficulty,
                width=12,
            )
            btn.pack(side="left", padx=6)
            self.home_diff_buttons.append(btn)

        start_btn = self._make_button(
            "Start Puzzle",
            self.start_from_home,
            primary=True,
            width=18,
            tall=True,
        )
        start_btn.pack(anchor="w", pady=(10, 4))

    def _build_game(self) -> None:
        self.game_frame = tk.Frame(self.layer, bg="#050915", padx=18, pady=18)

        header = tk.Frame(self.game_frame, bg="#050915")
        header.pack(fill="x", pady=(4, 12))

        self.title_label = tk.Label(
            header,
            text="Sudoku",
            fg="#e2e8f0",
            bg="#050915",
            font=("Helvetica", 30, "bold"),
        )
        self.title_label.pack(side="left")

        right_box = tk.Frame(header, bg="#050915")
        right_box.pack(side="right")

        self.timer_label = tk.Label(
            right_box,
            text="00:00",
            fg="#38bdf8",
            bg="#0b1220",
            font=("Consolas", 14, "bold"),
            padx=12,
            pady=6,
        )
        self.timer_label.pack(side="right", padx=(8, 0))

        self.status_label = tk.Label(
            right_box,
            text="Medium • 0 mistakes",
            fg="#94a3b8",
            bg="#050915",
            font=("Helvetica", 12),
        )
        self.status_label.pack(side="right")

        body = tk.Frame(self.game_frame, bg="#050915")
        body.pack(fill="both", expand=True)

        board_shell = tk.Frame(body, bg="#0b1220", padx=16, pady=16)
        board_shell.grid(row=0, column=0, sticky="n", padx=(0, 14))

        self.canvas = tk.Canvas(
            board_shell,
            width=self.board_px,
            height=self.board_px,
            bg="#0c1424",
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_click)

        sidebar = tk.Frame(body, bg="#050915")
        sidebar.grid(row=0, column=1, sticky="n")

        tk.Label(
            sidebar,
            text="New Game",
            fg="#e2e8f0",
            bg="#050915",
            font=("Helvetica", 13, "bold"),
        ).pack(anchor="w", pady=(0, 6))

        for diff in ["easy", "medium", "hard", "expert"]:
            self._make_button(
                diff.title(), lambda d=diff: self.new_game(d), primary=False, width=16
            ).pack(anchor="w", pady=4)

        tk.Label(
            sidebar,
            text="Actions",
            fg="#e2e8f0",
            bg="#050915",
            font=("Helvetica", 13, "bold"),
        ).pack(anchor="w", pady=(14, 6))

        actions = [
            ("Hint (H)", self.use_hint, True),
            ("Undo (Ctrl+Z)", self.undo, False),
            ("Redo (Ctrl+Y)", self.redo, False),
            ("Check", self.check_progress, False),
            ("Toggle Pencil (P)", self.toggle_pencil, False),
            ("Reset", self.reset_progress, False),
            ("Home", self.show_home, False),
        ]
        for text, cmd, primary in actions:
            self._make_button(text, cmd, primary=primary, width=18).pack(
                anchor="w", pady=4
            )

        pad_shell = tk.Frame(self.game_frame, bg="#050915")
        pad_shell.pack(fill="x", pady=(18, 0))
        pad_inner = tk.Frame(pad_shell, bg="#050915")
        pad_inner.pack()
        for i in range(1, 10):
            self._make_button(
                str(i),
                lambda v=i: self.handle_number(v),
                width=4,
                tall=True,
                primary=False,
            ).grid(row=0, column=i - 1, padx=4)
        self._make_button(
            "Clear", lambda: self.handle_number(0), width=6, tall=True, primary=True
        ).grid(row=0, column=9, padx=(14, 0))

        self._redraw()

    # --------------------------- UI helpers ------------------------------ #

    def _blend(self, c1: str, c2: str, ratio: float) -> str:
        def to_rgb(c: str) -> Tuple[int, int, int]:
            return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)

        r1, g1, b1 = to_rgb(c1)
        r2, g2, b2 = to_rgb(c2)
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _make_button(
        self, text: str, command, primary: bool = False, width: int = 14, tall: bool = False
    ) -> tk.Button:
        bg = "#22d3ee" if primary else "#111827"
        fg = "#0b1120" if primary else "#e2e8f0"
        hover = "#38bdf8" if primary else "#1f2a3c"
        btn = tk.Button(
            text=text,
            command=command,
            width=width,
            pady=10 if tall else 6,
            font=("Helvetica", 11, "bold"),
            bg=bg,
            fg=fg,
            activebackground=hover,
            activeforeground=fg,
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        btn.bind("<Enter>", lambda _e: btn.config(bg=hover))
        btn.bind("<Leave>", lambda _e: btn.config(bg=bg))
        return btn

    def _tick_timer(self) -> None:
        if self.running:
            elapsed = int(time.time() - self.start_time)
            mins, secs = divmod(elapsed, 60)
            self.timer_label.config(text=f"{mins:02d}:{secs:02d}")
        self.after(500, self._tick_timer)

    def _status_text(self) -> str:
        return (
            f"{self.game.difficulty.title()} • "
            f"{self.game.mistakes}/{self.game.max_mistakes} mistakes • "
            f"{self.game.hints_left} hints"
        )

    def _animate_accent(self) -> None:
        color = self.accent_colors[self.accent_index]
        self.accent_index = (self.accent_index + 1) % len(self.accent_colors)
        self.title_label.config(fg=color)
        self.bg_canvas.after(1200, self._animate_accent)

    def _redraw(self) -> None:
        self.canvas.delete("all")
        conflicts = find_conflicts(self.game.puzzle)
        glow_color = self._blend("#22d3ee", "#a855f7", (time.time() % 1))
        for r in range(9):
            for c in range(9):
                x0 = c * self.cell_px
                y0 = r * self.cell_px
                x1 = x0 + self.cell_px
                y1 = y0 + self.cell_px

                base = "#0c1424"
                selected_fill = "#162136"
                row_highlight = "#10192c"

                fill = base
                if self.selected:
                    sr, sc = self.selected
                    same_row = r == sr
                    same_col = c == sc
                    same_box = (r // 3, c // 3) == (sr // 3, sc // 3)
                    if same_row or same_col or same_box:
                        fill = row_highlight
                    if (r, c) == self.selected:
                        fill = selected_fill

                if (r, c) in conflicts:
                    fill = "#201427"

                self.canvas.create_rectangle(
                    x0, y0, x1, y1, fill=fill, outline="#0d1528", width=1
                )

                val = self.game.puzzle[r][c]
                if val:
                    fixed = (r, c) in self.game.fixed_cells
                    color = "#e2e8f0" if not fixed else "#22d3ee"
                    self.canvas.create_text(
                        x0 + self.cell_px / 2,
                        y0 + self.cell_px / 2,
                        text=str(val),
                        fill=color,
                        font=("Helvetica", 18, "bold"),
                    )
                elif (r, c) in self.game.notes:
                    notes = sorted(self.game.notes[(r, c)])
                    for note in notes:
                        nr = (note - 1) // 3
                        nc = (note - 1) % 3
                        nx = x0 + (nc + 0.5) * (self.cell_px / 3)
                        ny = y0 + (nr + 0.5) * (self.cell_px / 3)
                        self.canvas.create_text(
                            nx,
                            ny,
                            text=str(note),
                            fill="#64748b",
                            font=("Helvetica", 9, "bold"),
                        )

        for i in range(10):
            width = 3 if i % 3 == 0 else 1
            color = glow_color if i % 3 == 0 else "#1f2937"
            self.canvas.create_line(
                i * self.cell_px,
                0,
                i * self.cell_px,
                self.board_px,
                fill=color,
                width=width,
            )
            self.canvas.create_line(
                0,
                i * self.cell_px,
                self.board_px,
                i * self.cell_px,
                fill=color,
                width=width,
            )

        self.status_label.config(text=self._status_text())

    # --------------------------- Events ---------------------------------- #

    def on_click(self, event: tk.Event) -> None:
        col = event.x // self.cell_px
        row = event.y // self.cell_px
        if 0 <= row < 9 and 0 <= col < 9:
            self.selected = (row, col)
            self._redraw()

    def on_key(self, event: tk.Event) -> None:
        if self.game_frame.winfo_ismapped() is False:
            return
        if not self.selected:
            return
        if event.keysym in {"BackSpace", "Delete", "space"}:
            self.handle_number(0)
        elif event.keysym.lower() == "p":
            self.toggle_pencil()
        elif event.keysym.lower() == "h":
            self.use_hint()
        elif event.state & 0x4 and event.keysym.lower() == "z":  # Ctrl+Z
            self.undo()
        elif event.state & 0x4 and event.keysym.lower() == "y":  # Ctrl+Y
            self.redo()
        elif event.char.isdigit():
            val = int(event.char)
            if val == 0:
                self.handle_number(0)
            elif 1 <= val <= 9:
                self.handle_number(val)

    def handle_number(self, value: int) -> None:
        if not self.selected:
            return
        coord = self.selected
        if coord in self.game.fixed_cells:
            return
        if self.pencil_mode and value:
            self.game.toggle_note(coord, value)
        else:
            self.game.set_value(coord, value)
            if value and self.game.puzzle[coord[0]][coord[1]] == self.game.solution[
                coord[0]
            ][coord[1]]:
                self.game.notes.pop(coord, None)
        self._redraw()
        self._check_completion()

    # --------------------------- Actions --------------------------------- #

    def show_home(self) -> None:
        self.game_frame.pack_forget()
        self.home_frame.pack(fill="both", expand=True)
        self.running = False
        self.home_status.config(
            text=f"Difficulty: {self.home_difficulty.title()} • Hints and pencil ready."
        )

    def start_from_home(self) -> None:
        self.new_game(self.home_difficulty)
        self.home_frame.pack_forget()
        self.game_frame.pack(fill="both", expand=True)
        self.running = True
        self.start_time = time.time()

    def _select_home_difficulty(self, difficulty: str) -> None:
        self.home_difficulty = difficulty
        self.home_status.config(
            text=f"Difficulty set to {difficulty.title()}. Press Start when ready."
        )
        for btn in self.home_diff_buttons:
            if btn["text"].lower() == difficulty:
                btn.config(bg="#22d3ee", fg="#0b1120")
            else:
                btn.config(bg="#111827", fg="#e2e8f0")

    def new_game(self, difficulty: str) -> None:
        self.game = SudokuGame.new(difficulty)
        self.selected = None
        self.start_time = time.time()
        self.running = True
        self.pencil_mode = False
        self._redraw()

    def reset_progress(self) -> None:
        self.game = SudokuGame.new(self.game.difficulty)
        self.selected = None
        self.start_time = time.time()
        self.running = True
        self.pencil_mode = False
        self._redraw()

    def toggle_pencil(self) -> None:
        self.pencil_mode = not self.pencil_mode
        state = "ON" if self.pencil_mode else "OFF"
        self.status_label.config(text=f"{self._status_text()} • Pencil {state}")

    def use_hint(self) -> None:
        if not self.selected:
            return
        value = self.game.hint(self.selected)
        if value is None:
            messagebox.showinfo("Sudoku", "No hints left or cell is fixed.")
            return
        self._redraw()
        self._check_completion()

    def undo(self) -> None:
        self.game.undo()
        self._redraw()

    def redo(self) -> None:
        self.game.redo()
        self._redraw()

    def check_progress(self) -> None:
        conflicts = find_conflicts(self.game.puzzle)
        if not conflicts:
            messagebox.showinfo("Sudoku", "No conflicts so far. Keep going!")
        else:
            messagebox.showwarning(
                "Sudoku", f"Found {len(conflicts)} conflicting cells. Highlighted on board."
            )
        self._redraw()

    def _check_completion(self) -> None:
        if self.game.mistakes >= self.game.max_mistakes:
            self.running = False
            messagebox.showerror(
                "Sudoku", "Too many mistakes. Starting a fresh puzzle."
            )
            self.reset_progress()
            return
        if self.game.is_complete():
            self.running = False
            elapsed = int(time.time() - self.start_time)
            mins, secs = divmod(elapsed, 60)
            messagebox.showinfo(
                "Sudoku",
                f"Great job! You solved the {self.game.difficulty} puzzle in "
                f"{mins:02d}:{secs:02d}.",
            )


def main() -> None:
    app = SudokuApp()
    app.mainloop()


if __name__ == "__main__":
    main()
