import pytest

from sudoku import engine


@pytest.mark.parametrize("difficulty", list(engine.DIFFICULTY_HOLES))
def test_puzzle_is_valid_and_unique(difficulty):
    puzzle, solution = engine.generate_puzzle(difficulty)
    assert engine.is_solved(solution)
    assert engine.count_solutions(puzzle) == 1
    assert engine.solve(puzzle) == solution
    for r in range(9):
        for c in range(9):
            assert puzzle[r][c] in (0, solution[r][c])


def test_harder_means_more_empty_cells():
    empties = []
    for d in ["easy", "medium", "hard"]:
        puzzle, _ = engine.generate_puzzle(d)
        empties.append(sum(v == 0 for row in puzzle for v in row))
    assert empties[0] < empties[1] < empties[2]


def test_puzzles_are_random():
    assert engine.generate_puzzle("easy")[1] != engine.generate_puzzle("easy")[1]


def test_unknown_difficulty():
    with pytest.raises(ValueError):
        engine.generate_puzzle("impossible")
