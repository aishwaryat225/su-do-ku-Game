"""Sudoku engine: random 9x9 generator, solver and helpers.

A board is a list of 9 lists of 9 ints. 0 means an empty cell.
"""
import random

# How many cells to remove for each difficulty level.
DIFFICULTY_HOLES = {
    "easy": 36,
    "medium": 46,
    "hard": 52,
    "expert": 56,
}


def empty_board():
    return [[0] * 9 for _ in range(9)]


def copy_board(board):
    return [row[:] for row in board]


def fits(board, row, col, num):
    """True if `num` can go in (row, col) without breaking row/column/box rules."""
    for i in range(9):
        if i != col and board[row][i] == num:
            return False
        if i != row and board[i][col] == num:
            return False
    box_r, box_c = 3 * (row // 3), 3 * (col // 3)
    for r in range(box_r, box_r + 3):
        for c in range(box_c, box_c + 3):
            if (r, c) != (row, col) and board[r][c] == num:
                return False
    return True


def candidates(board, row, col):
    """All numbers 1-9 that fit in an empty cell."""
    if board[row][col] != 0:
        return []
    return [n for n in range(1, 10) if fits(board, row, col, n)]


def _find_best_empty(board):
    """Empty cell with the fewest candidates (makes solving much faster)."""
    best, best_cands = None, None
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                cands = candidates(board, r, c)
                if best is None or len(cands) < len(best_cands):
                    best, best_cands = (r, c), cands
                    if len(cands) <= 1:
                        return best, best_cands
    return best, best_cands


def _solve(board, limit, shuffle=False):
    """Backtracking solver. Fills `board` in place with the first solution.
    Returns the number of solutions found (stops counting at `limit`)."""
    cell, cands = _find_best_empty(board)
    if cell is None:
        return 1
    r, c = cell
    if shuffle:
        random.shuffle(cands)
    count = 0
    for n in cands:
        board[r][c] = n
        count += _solve(board, limit - count, shuffle)
        if count >= limit:
            if limit == 1:
                return count  # keep the solved board
            break
    board[r][c] = 0
    return count


def solve(board):
    """Return a solved copy of the board, or None if it has no solution."""
    work = copy_board(board)
    return work if _solve(work, 1) else None


def count_solutions(board, limit=2):
    return _solve(copy_board(board), limit)


def generate_full_board():
    board = empty_board()
    _solve(board, 1, shuffle=True)
    return board


def generate_puzzle(difficulty="easy"):
    """Return (puzzle, solution). The puzzle always has exactly one solution."""
    difficulty = difficulty.lower()
    if difficulty not in DIFFICULTY_HOLES:
        raise ValueError(f"Unknown difficulty {difficulty!r}. Use one of {list(DIFFICULTY_HOLES)}")
    target = DIFFICULTY_HOLES[difficulty]

    solution = generate_full_board()
    puzzle = copy_board(solution)
    cells = [(r, c) for r in range(9) for c in range(9)]
    random.shuffle(cells)

    removed = 0
    for r, c in cells:
        if removed >= target:
            break
        backup = puzzle[r][c]
        puzzle[r][c] = 0
        if count_solutions(puzzle) != 1:
            puzzle[r][c] = backup  # removing it would allow 2 solutions
        else:
            removed += 1
    return puzzle, solution


def is_solved(board):
    return all(
        board[r][c] != 0 and fits(board, r, c, board[r][c])
        for r in range(9) for c in range(9)
    )


def board_to_string(board):
    return "\n".join(" ".join(str(n) if n else "." for n in row) for row in board)
