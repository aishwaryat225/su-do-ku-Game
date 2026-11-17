"""Flask web app that serves a random Sudoku game.

Run:  python app.py   then open http://127.0.0.1:5050
"""
import uuid

from flask import Flask, jsonify, render_template, request

from sudoku import DIFFICULTY_HOLES, generate_puzzle

app = Flask(__name__)

HINTS_PER_GAME = 3

# game_id -> {"solution": board, "hints_left": int}
# The solution stays on the server so the page cannot "cheat".
GAMES = {}


def _game_or_404(data):
    game = GAMES.get((data or {}).get("id"))
    if game is None:
        return None, (jsonify(error="unknown game"), 404)
    return game, None


def _cell_from(data):
    """Read and validate row/col (0-8) from the request body."""
    row, col = int(data["row"]), int(data["col"])
    if not (0 <= row < 9 and 0 <= col < 9):
        raise ValueError("row/col out of range")
    return row, col


@app.get("/")
def index():
    return render_template(
        "index.html", difficulties=list(DIFFICULTY_HOLES), hints=HINTS_PER_GAME
    )


@app.get("/api/new")
def new_game():
    difficulty = request.args.get("difficulty", "easy").lower()
    if difficulty not in DIFFICULTY_HOLES:
        return jsonify(error=f"unknown difficulty '{difficulty}'"), 400
    puzzle, solution = generate_puzzle(difficulty)
    game_id = uuid.uuid4().hex
    GAMES[game_id] = {"solution": solution, "hints_left": HINTS_PER_GAME}
    return jsonify(id=game_id, difficulty=difficulty, puzzle=puzzle, hints=HINTS_PER_GAME)


@app.post("/api/check")
def check_move():
    """Check one number. Body: {"id", "row", "col", "value"} -> {"correct": bool}"""
    data = request.get_json(force=True, silent=True)
    game, err = _game_or_404(data)
    if err:
        return err
    try:
        row, col = _cell_from(data)
        value = int(data["value"])
        if not 1 <= value <= 9:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        return jsonify(error="row, col must be 0-8 and value 1-9"), 400
    return jsonify(correct=game["solution"][row][col] == value)


@app.post("/api/hint")
def hint():
    """Reveal one cell. Body: {"id", "row", "col"} -> {"value", "hints_left"}"""
    data = request.get_json(force=True, silent=True)
    game, err = _game_or_404(data)
    if err:
        return err
    try:
        row, col = _cell_from(data)
    except (KeyError, TypeError, ValueError):
        return jsonify(error="row and col must be 0-8"), 400
    if game["hints_left"] <= 0:
        return jsonify(error="no hints left", hints_left=0), 409
    game["hints_left"] -= 1
    return jsonify(value=game["solution"][row][col], hints_left=game["hints_left"])


@app.post("/api/verify")
def verify_board():
    """Check the whole board. Body: {"id", "board": 9x9 ints, 0 = empty}
    -> {"solved": bool, "wrong": [[row, col], ...], "empty": int}"""
    data = request.get_json(force=True, silent=True)
    game, err = _game_or_404(data)
    if err:
        return err
    board = data.get("board")
    if not (isinstance(board, list) and len(board) == 9
            and all(isinstance(r, list) and len(r) == 9 for r in board)):
        return jsonify(error="board must be 9 lists of 9 numbers"), 400
    solution = game["solution"]
    wrong, empty = [], 0
    for r in range(9):
        for c in range(9):
            v = board[r][c]
            if not v:
                empty += 1
            elif v != solution[r][c]:
                wrong.append([r, c])
    return jsonify(solved=not wrong and empty == 0, wrong=wrong, empty=empty)


if __name__ == "__main__":
    # Port 5000 is used by macOS AirPlay Receiver, so default to 5050.
    import os
    app.run(debug=True, port=int(os.environ.get("PORT", 5050)))
