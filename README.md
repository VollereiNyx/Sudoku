# Sudoku (Vibe Edition)

A modern Sudoku desktop app inspired by sudoku.com. Features a clean neon-dark UI, multiple difficulty levels, hints, pencil marks, undo/redo, mistake tracking, timer, and on-screen/keyboard controls. Built with the Python standard library (Tkinter) and ready for PyInstaller packaging into a single executable.

---

## Features
- Fresh puzzles on Easy, Medium, Hard, and Expert with unique solutions
- Row/column/box highlighting, conflict highlighting, and mistake limit
- Pencil marks, hints, undo/redo history, reset, and progress check
- Timer plus keyboard shortcuts (digits, Backspace, H for hint, P for pencil, Ctrl+Z/Y)
- On-screen number pad and difficulty buttons
- Pure Python; optional PyInstaller build for a `.exe`

---

## Run (dev)
```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt   # installs PyInstaller (optional for packing)
python sudoku.py
```

---

## Build Windows executable
```bash
python -m pip install -r requirements.txt
pyinstaller --noconfirm --windowed --name SudokuVibe sudoku.py
```
The executable will be in `dist/SudokuVibe/SudokuVibe.exe`. You can zip and share the `dist/SudokuVibe` folder to run on other machines without Python.

---

## Repo layout
- `sudoku.py` — game logic, generator, and Tkinter UI entry point
- `requirements.txt` — optional PyInstaller dependency for packaging

---

## License
MIT
