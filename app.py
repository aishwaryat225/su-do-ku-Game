"""Flask web app that serves a random Sudoku game.

Run:  python app.py   then open http://127.0.0.1:5000
"""
import uuid

from flask import Flask, jsonify, render_template, request

from sudoku import DIFFICULTY_HOLES, generate_puzzle

app = Flask(__name__)

# game_id -> solution (kept on the server so the page cannot "cheat")
GAMES = {}


@app.get("/")
def index():
    return render_template("index.html", difficulties=list(DIFFICULTY_HOLES))


@app.get("/api/new")
def new_game():
    difficulty = request.args.get("difficulty", "easy").lower()
    if difficulty not in DIFFICULTY_HOLES:
        return jsonify(error=f"unknown difficulty '{difficulty}'"), 400
    puzzle, solution = generate_puzzle(difficulty)
    game_id = uuid.uuid4().hex
    GAMES[game_id] = solution
    return jsonify(id=game_id, difficulty=difficulty, puzzle=puzzle)


@app.post("/api/check")
def check_move():
    """Body: {"id": ..., "row": 0-8, "col": 0-8, "value": 1-9} -> {"correct": bool}"""
    data = request.get_json(force=True)
    solution = GAMES.get(data.get("id"))
    if solution is None:
        return jsonify(error="unknown game"), 404
    try:
        row, col, value = int(data["row"]), int(data["col"]), int(data["value"])
    except (KeyError, TypeError, ValueError):
        return jsonify(error="row, col and value must be numbers"), 400
    if not (0 <= row < 9 and 0 <= col < 9 and 1 <= value <= 9):
        return jsonify(error="out of range"), 400
    return jsonify(correct=solution[row][col] == value)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
