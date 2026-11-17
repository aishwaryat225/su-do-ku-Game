# Sudoku (Python + Robot Framework + Playwright)

A web app that makes a random 9x9 Sudoku at 4 difficulty levels. Robot Framework tests
fill in the missing numbers **left to right, one cell at a time**, entering only the
number that fits.

| Difficulty | Empty cells |
|------------|-------------|
| easy       | 36 |
| medium     | 46 |
| hard       | 52 |
| expert     | 56 |

Every puzzle is checked to have **exactly one solution**.

## Project layout

```
app.py                     Flask web app (/, /api/new, /api/check)
sudoku/engine.py           generator, solver, "fits" rule check
templates/index.html       page
static/app.js, style.css   grid UI (cells are #cell-<row>-<col>, 0-8)
tests/unit/test_engine.py  pytest unit tests for the engine
tests/robot/sudoku.robot   Robot Framework end-to-end tests
tests/robot/SudokuLibrary.py  Robot keywords built on Playwright (Python)
```

## Setup (once)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

## Play the game

```bash
python app.py
# open http://127.0.0.1:5000
```

Green = correct number, red = wrong number (counts as a mistake).

## Run the tests

```bash
pytest tests/unit                               # engine unit tests
robot --outputdir results tests/robot           # browser tests (headless)
robot --outputdir results -v HEADLESS:False -v SLOW_MO:100 tests/robot   # watch it play
robot --outputdir results -t "Solve Hard Sudoku" tests/robot             # one test
```

Open `results/log.html` to see each step, the number entered in every cell and
screenshots of the solved boards.

### What the Robot tests do

* **Solve Easy/Medium/Hard/Expert Sudoku**: start a game, read the grid from the page,
  check it has one solution, then go through the empty cells row by row, left to right.
  For each cell: work out the number that fits, type it, and check the app marks it
  correct. At the end, check the "Solved!" message.
* **Wrong Number Is Rejected**: enter a number that doesn't fit and check it shows red
  and counts as a mistake. Then enter the right one.
* **Try Numbers One By One In First Empty Cell**: try 1, 2, 3 … in one cell until the
  app accepts one.
* **Given Numbers Cannot Be Changed**: the puzzle's own numbers are read-only.

> The tests use a Python Playwright keyword library, so you **don't need Node.js**.
> (The `robotframework-browser` library also uses Playwright, but it needs Node.js.)

## VS Code

Install the **Python** and **RobotCode** extensions. `.vscode/settings.json` already
points to `.venv`, so you can run the pytest and Robot tests from the Testing panel.
