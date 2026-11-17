"""Robot Framework keyword library for the Sudoku app, built on Playwright (Python).

Keywords drive a real browser and read/fill the 9x9 grid. The library has its own
solver, so the test works out the right number independently of the app.
"""
import os
import sys
import threading

from playwright.sync_api import expect, sync_playwright
from robot.api import logger
from robot.api.deco import keyword, library

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from sudoku import engine  # noqa: E402


@library(scope="GLOBAL")
class SudokuLibrary:
    def __init__(self):
        self._pw = None
        self._browser = None
        self.page = None
        self._server = None

    # ------------------------------------------------------------- server
    @keyword
    def start_sudoku_server(self, port=5001):
        """Start the Flask app in a background thread. Returns its base URL."""
        from werkzeug.serving import make_server
        from app import app

        self._server = make_server("127.0.0.1", int(port), app)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return f"http://127.0.0.1:{port}"

    @keyword
    def stop_sudoku_server(self):
        if self._server:
            self._server.shutdown()
            self._server = None

    # ------------------------------------------------------------ browser
    @keyword
    def open_sudoku_app(self, url, headless=True, slow_mo=0):
        """Open the browser at `url`. Pass headless=False to watch it play."""
        headless = str(headless).lower() not in ("false", "0", "no")
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=headless, slow_mo=float(slow_mo))
        self.page = self._browser.new_page()
        self.page.goto(url)
        self._wait_for_board()

    @keyword
    def close_sudoku_app(self):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        self._browser = self._pw = self.page = None

    @keyword
    def start_new_game(self, difficulty="easy"):
        """Pick a difficulty, click New game and wait for the new grid."""
        old_first = self.page.locator("#cell-0-0").element_handle()
        self.page.select_option("#difficulty", difficulty)
        self.page.click("#new-game")
        self.page.wait_for_function("(el) => !el.isConnected", arg=old_first)
        self._wait_for_board()

    def _wait_for_board(self):
        self.page.wait_for_selector("#board[data-ready='true'] #cell-8-8")

    @keyword
    def take_board_screenshot(self, name="board.png"):
        from robot.libraries.BuiltIn import BuiltIn
        out_dir = BuiltIn().get_variable_value("${OUTPUT_DIR}", os.getcwd())
        path = os.path.join(out_dir, name)
        self.page.locator("#board").screenshot(path=path)
        logger.info(f'<img src="{name}" width="300">', html=True)

    # --------------------------------------------------------- read board
    @keyword
    def read_board_from_page(self):
        """Return the grid shown in the browser as 9 lists of 9 ints (0 = empty)."""
        values = self.page.eval_on_selector_all(
            "#board input", "els => els.map(e => e.value)"
        )
        if len(values) != 81:
            raise AssertionError(f"Expected 81 cells, found {len(values)}")
        board = [[int(v) if v else 0 for v in values[r * 9:(r + 1) * 9]] for r in range(9)]
        logger.info("Board on page:\n" + engine.board_to_string(board))
        return board

    @keyword
    def count_empty_cells(self, board):
        return sum(1 for row in board for v in row if v == 0)

    @keyword
    def get_empty_cells_left_to_right(self, board):
        """Empty cells in reading order: row 0 left->right, then row 1, ..."""
        return [(r, c) for r in range(9) for c in range(9) if board[r][c] == 0]

    # -------------------------------------------------------------- logic
    @keyword
    def board_should_have_one_solution(self, board):
        n = engine.count_solutions(board, limit=2)
        if n != 1:
            raise AssertionError(f"Puzzle should have exactly 1 solution, found {n}")

    @keyword
    def solve_board(self, board):
        solution = engine.solve(board)
        if solution is None:
            raise AssertionError("Board on the page cannot be solved")
        return solution

    @keyword
    def get_candidates(self, board, row, col):
        """Numbers 1-9 that fit in (row, col) by row/column/box rules right now."""
        return engine.candidates(board, int(row), int(col))

    @keyword
    def get_number_that_fits(self, board, solution, row, col):
        """The only number that fits this cell. It must also pass the rules check."""
        row, col = int(row), int(col)
        number = solution[row][col]
        cands = engine.candidates(board, row, col)
        if number not in cands:
            raise AssertionError(f"{number} breaks row/col/box rules at ({row},{col})")
        logger.info(f"Cell ({row},{col}) candidates {cands} -> enter {number}")
        return number

    @keyword
    def get_wrong_number(self, board, solution, row, col):
        """A number that does not fit, used for negative tests."""
        row, col = int(row), int(col)
        for n in range(1, 10):
            if n != solution[row][col]:
                return n
        raise AssertionError("no wrong number available")

    # ---------------------------------------------------------- UI actions
    def _cell(self, row, col):
        return self.page.locator(f"#cell-{int(row)}-{int(col)}")

    @keyword
    def enter_number(self, row, col, number):
        """Type one number into a cell and wait for the app to check it."""
        cell = self._cell(row, col)
        cell.fill("")
        cell.evaluate("el => delete el.dataset.checked")
        cell.fill(str(number))
        expect(cell).to_have_attribute("data-checked", "true")

    @keyword
    def set_board_value(self, board, row, col, number):
        board[int(row)][int(col)] = int(number)

    @keyword
    def clear_cell(self, row, col):
        self._cell(row, col).fill("")

    @keyword
    def cell_should_be_correct(self, row, col):
        expect(self._cell(row, col)).to_have_class(_has("correct"))

    @keyword
    def cell_is_correct(self, row, col):
        """True/False right now (no waiting). Use after Enter Number."""
        classes = self._cell(row, col).get_attribute("class") or ""
        return "correct" in classes.split()

    @keyword
    def cell_should_be_wrong(self, row, col):
        expect(self._cell(row, col)).to_have_class(_has("wrong"))

    @keyword
    def given_cells_should_be_read_only(self):
        assert self.page.locator("#board input.given:not([readonly])").count() == 0

    @keyword
    def mistakes_should_be(self, expected):
        expect(self.page.locator("#mistakes")).to_have_text(str(expected))

    @keyword
    def empty_count_should_be(self, expected):
        expect(self.page.locator("#empty-count")).to_have_text(str(expected))

    @keyword
    def board_should_be_solved(self):
        expect(self.page.locator("#board")).to_have_attribute("data-solved", "true")
        expect(self.page.locator("#message")).to_have_text("Solved! Well done.")
        board = self.read_board_from_page()
        if not engine.is_solved(board):
            raise AssertionError("Board on the page is not a valid solution")


def _has(cls):
    import re
    return re.compile(rf"(^|\s){cls}(\s|$)")
