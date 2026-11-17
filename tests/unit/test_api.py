import pytest

from app import GAMES, HINTS_PER_GAME, app


@pytest.fixture
def client():
    return app.test_client()


@pytest.fixture
def game(client):
    data = client.get("/api/new?difficulty=easy").get_json()
    return data, GAMES[data["id"]]["solution"]


def first_empty(puzzle):
    return next((r, c) for r in range(9) for c in range(9) if puzzle[r][c] == 0)


def test_new_game(client, game):
    data, _ = game
    assert len(data["puzzle"]) == 9 and data["hints"] == HINTS_PER_GAME
    assert client.get("/api/new?difficulty=nope").status_code == 400


def test_check(client, game):
    data, solution = game
    r, c = first_empty(data["puzzle"])
    right = solution[r][c]
    wrong = right % 9 + 1
    ok = client.post("/api/check", json={"id": data["id"], "row": r, "col": c, "value": right})
    bad = client.post("/api/check", json={"id": data["id"], "row": r, "col": c, "value": wrong})
    assert ok.get_json()["correct"] is True
    assert bad.get_json()["correct"] is False
    assert client.post("/api/check", json={"id": "x", "row": 0, "col": 0, "value": 1}).status_code == 404


def test_hints_run_out(client, game):
    data, solution = game
    r, c = first_empty(data["puzzle"])
    for left in range(HINTS_PER_GAME - 1, -1, -1):
        res = client.post("/api/hint", json={"id": data["id"], "row": r, "col": c}).get_json()
        assert res == {"value": solution[r][c], "hints_left": left}
    assert client.post("/api/hint", json={"id": data["id"], "row": r, "col": c}).status_code == 409


def test_verify(client, game):
    data, solution = game
    board = [row[:] for row in data["puzzle"]]
    res = client.post("/api/verify", json={"id": data["id"], "board": board}).get_json()
    assert res["solved"] is False and res["wrong"] == [] and res["empty"] > 0

    r, c = first_empty(data["puzzle"])
    board = [row[:] for row in solution]
    board[r][c] = solution[r][c] % 9 + 1
    res = client.post("/api/verify", json={"id": data["id"], "board": board}).get_json()
    assert res == {"solved": False, "wrong": [[r, c]], "empty": 0}

    res = client.post("/api/verify", json={"id": data["id"], "board": solution}).get_json()
    assert res["solved"] is True
    assert client.post("/api/verify", json={"id": data["id"], "board": [[0]]}).status_code == 400
