import random
import string

def create_board():
    return [[0 for _ in range(9)] for _ in range(9)]

def is_valid(board, row, col, num):
    for i in range(9):
        if board[row][i] == num or board[i][col] == num:
            return False
    start_row = (row // 3) * 3
    start_col = (col // 3) * 3
    for i in range(start_row, start_row + 3):
        for j in range(start_col, start_col + 3):
            if board[i][j] == num:
                return False
    return True

def solve_board(board):
    for row in range(9):
        for col in range(9):
            if board[row][col] == 0:
                nums = list(range(1, 10))
                random.shuffle(nums)
                for num in nums:
                    if is_valid(board, row, col, num):
                        board[row][col] = num
                        if solve_board(board):
                            return True
                        board[row][col] = 0
                return False
    return True

def count_solutions(board, limit=2):
    for row in range(9):
        for col in range(9):
            if board[row][col] == 0:
                for num in range(1, 10):
                    if is_valid(board, row, col, num):
                        board[row][col] = num
                        sols = count_solutions(board, limit)
                        board[row][col] = 0
                        if sols >= limit:
                            return sols
                return 0
    return 1

def remove_numbers_unique(board, num_holes):
    positions = [(r, c) for r in range(9) for c in range(9)]
    random.shuffle(positions)

    removed = 0
    for row, col in positions:
        if removed >= num_holes:
            break
        backup = board[row][col]
        if backup == 0:
            continue
        board[row][col] = 0
        board_copy = [r[:] for r in board]
        if count_solutions(board_copy, 2) == 1:
            removed += 1
        else:
            board[row][col] = backup

def print_board(board):
    for i in range(9):
        if i % 3 == 0 and i != 0:
            print("-" * 21)
        for j in range(9):
            if j % 3 == 0 and j != 0:
                print("|", end=" ")
            print(board[i][j] if board[i][j] != 0 else ".", end=" ")
        print()

def generate_sudoku():
    board = create_board()
    solve_board(board)

    difficulty = input("Choose difficulty (easy, medium, hard): ").lower()
    if difficulty == 'easy':
        holes = 30
    elif difficulty == 'medium':
        holes = 40
    elif difficulty == 'hard':
        holes = 55
    else:
        print("Invalid choice, using medium.")
        holes = 40

    remove_numbers_unique(board, holes)
    print("\n🎲 Sudoku Puzzle:\n")
    print_board(board)

generate_sudoku()
