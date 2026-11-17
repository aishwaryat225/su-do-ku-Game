// Sudoku front-end. Each cell is <input id="cell-R-C"> with classes:
//   given   - number from the puzzle (read-only)
//   correct - the user entered the right number
//   wrong   - the user entered a number that does not fit
const boardEl = document.getElementById("board");
const messageEl = document.getElementById("message");
const emptyEl = document.getElementById("empty-count");
const mistakesEl = document.getElementById("mistakes");
const difficultyEl = document.getElementById("difficulty");

let gameId = null;
let mistakes = 0;

function cell(r, c) {
  return document.getElementById(`cell-${r}-${c}`);
}

function updateStats() {
  const empty = [...boardEl.querySelectorAll("input")]
    .filter((i) => !i.classList.contains("given") && !i.classList.contains("correct")).length;
  emptyEl.textContent = empty;
  mistakesEl.textContent = mistakes;
  if (empty === 0) {
    messageEl.textContent = "Solved! Well done.";
    messageEl.className = "message success";
    boardEl.dataset.solved = "true";
  }
}

function buildBoard(puzzle) {
  boardEl.innerHTML = "";
  boardEl.dataset.ready = "false";
  boardEl.dataset.solved = "false";
  for (let r = 0; r < 9; r++) {
    for (let c = 0; c < 9; c++) {
      const input = document.createElement("input");
      input.id = `cell-${r}-${c}`;
      input.dataset.row = r;
      input.dataset.col = c;
      input.inputMode = "numeric";
      input.maxLength = 1;
      input.autocomplete = "off";
      input.setAttribute("aria-label", `Row ${r + 1} column ${c + 1}`);
      if (c % 3 === 2 && c !== 8) input.classList.add("box-right");
      if (r % 3 === 2 && r !== 8) input.classList.add("box-bottom");
      if (puzzle[r][c] !== 0) {
        input.value = puzzle[r][c];
        input.readOnly = true;
        input.classList.add("given");
      } else {
        input.addEventListener("input", onInput);
      }
      boardEl.appendChild(input);
    }
  }
  boardEl.dataset.ready = "true";
}

async function onInput(e) {
  const input = e.target;
  input.classList.remove("correct", "wrong");
  input.value = input.value.replace(/[^1-9]/g, "").slice(-1);
  if (!input.value) { updateStats(); return; }

  const res = await fetch("/api/check", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      id: gameId, row: +input.dataset.row, col: +input.dataset.col, value: +input.value,
    }),
  });
  const data = await res.json();
  if (data.correct) {
    input.classList.add("correct");
    input.readOnly = true; // lock correct answers
  } else {
    input.classList.add("wrong");
    mistakes++;
  }
  input.dataset.checked = "true";
  updateStats();
}

async function newGame() {
  messageEl.textContent = "Generating…";
  messageEl.className = "message";
  const res = await fetch(`/api/new?difficulty=${difficultyEl.value}`);
  const data = await res.json();
  gameId = data.id;
  mistakes = 0;
  buildBoard(data.puzzle);
  messageEl.textContent = "";
  updateStats();
}

document.getElementById("new-game").addEventListener("click", newGame);
newGame();
