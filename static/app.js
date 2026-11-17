// Sudoku front-end.
//
// Each cell is <input id="cell-R-C"> (R, C = 0-8) with these classes:
//   given   - number from the puzzle (read-only)
//   correct - right number ("Check as I go" on)
//   wrong   - wrong number ("Check as I go" on, or after the full-board check)
//   hinted  - filled in by the Hint button
//   selected / peer - the clicked cell and its row, column and 3x3 box
"use strict";

const $ = (sel) => document.querySelector(sel);
const boardEl = $("#board");
const messageEl = $("#message");
const emptyEl = $("#empty-count");
const mistakesEl = $("#mistakes");
const difficultyEl = $("#difficulty");
const checkEl = $("#check-mode");
const notesBtn = $("#notes-toggle");
const hintBtn = $("#hint");
const hintsLeftEl = $("#hints-left");

const LOCKED = new Set(["correct", "hinted"]);

let game = null;     // {id, given, values, notes, status}
let history = [];    // undo stack
let mistakes = 0;
let hintsLeft = 0;
let notesMode = false;
let selected = null; // [row, col]
let finished = false;

// ---------------------------------------------------------------- helpers
const grid = (fill) => Array.from({ length: 9 }, () => Array.from({ length: 9 }, fill));
const inputAt = (r, c) => document.getElementById(`cell-${r}-${c}`);
const isGiven = (r, c) => game.given[r][c] !== 0;
const isLocked = (r, c) => isGiven(r, c) || LOCKED.has(game.status[r][c]);

function unitCells(r, c) {
  const row = [], col = [], box = [];
  const br = 3 * Math.floor(r / 3), bc = 3 * Math.floor(c / 3);
  for (let i = 0; i < 9; i++) {
    row.push([r, i]);
    col.push([i, c]);
    box.push([br + Math.floor(i / 3), bc + (i % 3)]);
  }
  return { row, col, box };
}

function peersOf(r, c) {
  const seen = new Set(), out = [];
  const { row, col, box } = unitCells(r, c);
  for (const [rr, cc] of [...row, ...col, ...box]) {
    const key = rr * 9 + cc;
    if ((rr !== r || cc !== c) && !seen.has(key)) { seen.add(key); out.push([rr, cc]); }
  }
  return out;
}

async function api(path, body) {
  const res = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  return res.json();
}

function say(text, kind = "") {
  messageEl.textContent = text;
  messageEl.className = `message ${kind}`;
}

function replayAnimation(el, cls) {
  el.classList.remove(cls);
  void el.offsetWidth; // restart the CSS animation
  el.classList.add(cls);
}

// ---------------------------------------------------------------- render
function renderCell(r, c) {
  const input = inputAt(r, c);
  const v = game.values[r][c];
  const status = game.status[r][c];
  input.value = v || "";
  input.readOnly = isLocked(r, c);
  input.classList.toggle("correct", status === "correct" || status === "hinted");
  input.classList.toggle("hinted", status === "hinted");
  input.classList.toggle("wrong", status === "wrong");
  const notes = input.nextElementSibling.children;
  for (let n = 1; n <= 9; n++) {
    notes[n - 1].textContent = !v && game.notes[r][c].includes(n) ? n : "";
  }
}

function renderAll() {
  for (let r = 0; r < 9; r++) for (let c = 0; c < 9; c++) renderCell(r, c);
  updateStats();
}

function updateStats() {
  let empty = 0;
  for (const row of game.values) for (const v of row) if (!v) empty++;
  emptyEl.textContent = empty;
  mistakesEl.textContent = mistakes;
  hintsLeftEl.textContent = hintsLeft;
  hintBtn.disabled = hintsLeft <= 0 || finished;
  return empty;
}

function highlight(r, c) {
  boardEl.querySelectorAll(".selected, .peer").forEach((el) => el.classList.remove("selected", "peer"));
  if (r == null) return;
  inputAt(r, c).classList.add("selected");
  for (const [pr, pc] of peersOf(r, c)) inputAt(pr, pc).classList.add("peer");
}

function buildBoard() {
  boardEl.innerHTML = "";
  boardEl.dataset.ready = "false";
  boardEl.dataset.solved = "false";
  for (let r = 0; r < 9; r++) {
    for (let c = 0; c < 9; c++) {
      const cell = document.createElement("div");
      cell.className = "cell";
      if (c % 3 === 2 && c !== 8) cell.classList.add("box-right");
      if (r % 3 === 2 && r !== 8) cell.classList.add("box-bottom");

      const input = document.createElement("input");
      input.id = `cell-${r}-${c}`;
      input.dataset.row = r;
      input.dataset.col = c;
      input.inputMode = "numeric";
      input.autocomplete = "off";
      input.setAttribute("aria-label", `Row ${r + 1} column ${c + 1}`);
      if (isGiven(r, c)) input.classList.add("given");
      input.addEventListener("focus", onFocus);
      input.addEventListener("keydown", onKeyDown);
      input.addEventListener("input", onInput);

      const notes = document.createElement("div");
      notes.className = "notes";
      for (let n = 0; n < 9; n++) notes.appendChild(document.createElement("span"));

      cell.append(input, notes);
      boardEl.appendChild(cell);
    }
  }
  renderAll();
  boardEl.dataset.ready = "true";
}

// ---------------------------------------------------------------- history
function snapshot(r, c) {
  return {
    r, c,
    value: game.values[r][c],
    status: game.status[r][c],
    notes: game.notes.map((row) => row.map((n) => n.slice())),
  };
}

function undo() {
  if (finished || !history.length) return;
  const h = history.pop();
  game.values[h.r][h.c] = h.value;
  game.status[h.r][h.c] = h.status;
  game.notes = h.notes;
  renderAll();
  selectCell(h.r, h.c);
}

// ---------------------------------------------------------------- moves
function removeNoteFromPeers(r, c, n) {
  for (const [pr, pc] of peersOf(r, c)) {
    game.notes[pr][pc] = game.notes[pr][pc].filter((x) => x !== n);
  }
}

function toggleNote(r, c, n) {
  if (isLocked(r, c) || game.values[r][c]) return;
  history.push(snapshot(r, c));
  const list = game.notes[r][c];
  game.notes[r][c] = list.includes(n) ? list.filter((x) => x !== n) : [...list, n];
  renderCell(r, c);
}

async function enterDigit(r, c, n) {
  if (finished || isLocked(r, c)) return renderCell(r, c);
  if (notesMode) { renderCell(r, c); return toggleNote(r, c, n); }
  if (game.values[r][c] === n && game.status[r][c] !== "wrong") return renderCell(r, c);

  history.push(snapshot(r, c));
  game.values[r][c] = n;
  game.status[r][c] = "";
  game.notes[r][c] = [];
  removeNoteFromPeers(r, c, n);
  const input = inputAt(r, c);
  delete input.dataset.checked;
  renderAll();
  replayAnimation(input, "pop");

  if (checkEl.checked) {
    const { correct } = await api("/api/check", { id: game.id, row: r, col: c, value: n });
    if (game.values[r][c] !== n) return; // changed while we waited
    game.status[r][c] = correct ? "correct" : "wrong";
    if (!correct) { mistakes++; replayAnimation(input, "shake"); }
    renderCell(r, c);
    input.dataset.checked = "true";
  }
  await afterChange(r, c);
}

function eraseCell(r, c) {
  if (finished || isLocked(r, c)) return;
  if (!game.values[r][c] && !game.notes[r][c].length) return;
  history.push(snapshot(r, c));
  game.values[r][c] = 0;
  game.status[r][c] = "";
  game.notes[r][c] = [];
  renderAll();
}

async function useHint() {
  if (finished || hintsLeft <= 0) return;
  // Use the selected cell if it can take a hint, else the first empty / wrong cell.
  let target = selected && !isLocked(...selected) ? selected : null;
  if (!target) {
    outer: for (let r = 0; r < 9; r++) {
      for (let c = 0; c < 9; c++) {
        if (!isLocked(r, c) && (!game.values[r][c] || game.status[r][c] === "wrong")) {
          target = [r, c];
          break outer;
        }
      }
    }
  }
  if (!target) return;
  const [r, c] = target;
  const res = await api("/api/hint", { id: game.id, row: r, col: c });
  hintsLeft = res.hints_left ?? 0;
  if (res.value == null) return updateStats();

  game.values[r][c] = res.value;
  game.status[r][c] = "hinted";
  game.notes[r][c] = [];
  removeNoteFromPeers(r, c, res.value);
  renderAll();
  replayAnimation(inputAt(r, c), "sparkle");
  selectCell(r, c);
  await afterChange(r, c);
}

// When a row, column or box is full (and has no known mistakes), celebrate it.
function celebrateUnits(r, c) {
  for (const cells of Object.values(unitCells(r, c))) {
    const vals = cells.map(([rr, cc]) => game.values[rr][cc]);
    const complete = vals.every(Boolean) && new Set(vals).size === 9
      && cells.every(([rr, cc]) => game.status[rr][cc] !== "wrong");
    if (!complete) continue;
    cells.forEach(([rr, cc], i) => {
      const el = inputAt(rr, cc);
      el.style.animationDelay = `${i * 40}ms`;
      replayAnimation(el, "flash");
      setTimeout(() => { el.classList.remove("flash"); el.style.animationDelay = ""; }, 1200);
    });
  }
}

async function afterChange(r, c) {
  const empty = updateStats();
  celebrateUnits(r, c);
  if (empty === 0) await checkWholeBoard();
}

async function checkWholeBoard() {
  const res = await api("/api/verify", { id: game.id, board: game.values });
  if (res.solved) {
    finished = true;
    boardEl.dataset.solved = "true";
    say("Solved! Well done.", "success");
    updateStats();
    confetti();
    return;
  }
  for (const [r, c] of res.wrong) if (!isGiven(r, c)) game.status[r][c] = "wrong";
  renderAll();
  const n = res.wrong.length;
  say(`Not quite: ${n} number${n === 1 ? " is" : "s are"} wrong. Fix the red cells.`, "error");
}

// "Check as I go" switched on mid-game: mark every typed number right or wrong.
async function applyCheckMode() {
  try { localStorage.setItem("sudoku-check-mode", checkEl.checked ? "1" : "0"); } catch (e) {}
  if (!game || finished) return;
  if (checkEl.checked) {
    const res = await api("/api/verify", { id: game.id, board: game.values });
    const wrong = new Set(res.wrong.map(([r, c]) => r * 9 + c));
    for (let r = 0; r < 9; r++) {
      for (let c = 0; c < 9; c++) {
        if (isGiven(r, c) || !game.values[r][c] || game.status[r][c] === "hinted") continue;
        game.status[r][c] = wrong.has(r * 9 + c) ? "wrong" : "correct";
        inputAt(r, c).dataset.checked = "true";
      }
    }
  } else {
    for (let r = 0; r < 9; r++) {
      for (let c = 0; c < 9; c++) {
        if (game.status[r][c] === "correct" || game.status[r][c] === "wrong") game.status[r][c] = "";
      }
    }
  }
  renderAll();
}

function setNotesMode(on) {
  notesMode = on;
  notesBtn.setAttribute("aria-pressed", String(on));
  notesBtn.classList.toggle("on", on);
  $("#notes-state").textContent = on ? "On" : "Off";
}

// ---------------------------------------------------------------- events
function selectCell(r, c) {
  selected = [r, c];
  highlight(r, c);
}

function onFocus(e) {
  const r = +e.target.dataset.row, c = +e.target.dataset.col;
  selectCell(r, c);
  e.target.select();
}

function onKeyDown(e) {
  const r = +e.target.dataset.row, c = +e.target.dataset.col;
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "z") {
    e.preventDefault();
    return undo();
  }
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  if (/^[1-9]$/.test(e.key)) {
    e.preventDefault();
    enterDigit(r, c, +e.key);
  } else if (e.key === "Backspace" || e.key === "Delete") {
    e.preventDefault();
    eraseCell(r, c);
  } else if (e.key === "n" || e.key === "N") {
    e.preventDefault();
    setNotesMode(!notesMode);
  } else if (e.key.length === 1) {
    e.preventDefault(); // ignore letters etc.
  }
}

// Fallback for phone keyboards, paste, and automated tests (fill()).
function onInput(e) {
  const r = +e.target.dataset.row, c = +e.target.dataset.col;
  const digit = (e.target.value.match(/[1-9]/g) || []).pop();
  if (digit) enterDigit(r, c, +digit);
  else if (!e.target.value) eraseCell(r, c);
  else renderCell(r, c);
}

// Keep focus on the board cell when clicking toolbar buttons.
document.querySelectorAll(".toolbar .btn").forEach((b) =>
  b.addEventListener("mousedown", (e) => e.preventDefault()));

$("#undo").addEventListener("click", undo);
$("#erase").addEventListener("click", () => selected && eraseCell(...selected));
notesBtn.addEventListener("click", () => setNotesMode(!notesMode));
hintBtn.addEventListener("click", useHint);
checkEl.addEventListener("change", applyCheckMode);
$("#new-game").addEventListener("click", newGame);

// ---------------------------------------------------------------- confetti
function confetti() {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const box = $("#confetti");
  const colors = ["#ff5d8f", "#ffb84c", "#4cc9f0", "#7b5cff", "#2ec4b6", "#ffd23f"];
  for (let i = 0; i < 120; i++) {
    const p = document.createElement("i");
    p.style.left = `${Math.random() * 100}vw`;
    p.style.background = colors[i % colors.length];
    p.style.animationDelay = `${Math.random() * 0.6}s`;
    p.style.animationDuration = `${2 + Math.random() * 1.5}s`;
    p.style.setProperty("--spin", `${Math.random() * 720 - 360}deg`);
    p.style.setProperty("--drift", `${Math.random() * 160 - 80}px`);
    box.appendChild(p);
  }
  setTimeout(() => { box.innerHTML = ""; }, 4500);
}

// ---------------------------------------------------------------- start
async function newGame() {
  say("Making a new puzzle…");
  const data = await api(`/api/new?difficulty=${difficultyEl.value}`);
  game = {
    id: data.id,
    given: data.puzzle.map((row) => row.slice()),
    values: data.puzzle.map((row) => row.slice()),
    notes: grid(() => []),
    status: grid(() => ""),
  };
  history = [];
  mistakes = 0;
  hintsLeft = data.hints;
  finished = false;
  selected = null;
  setNotesMode(false);
  $("#confetti").innerHTML = "";
  buildBoard();
  say("");
}

try { checkEl.checked = localStorage.getItem("sudoku-check-mode") === "1"; } catch (e) {}
newGame();
