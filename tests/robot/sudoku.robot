*** Settings ***
Documentation     End-to-end tests for the Sudoku app using Robot Framework + Playwright.
...               The main test reads a random puzzle, then fills the empty cells
...               LEFT TO RIGHT, ROW BY ROW, ONE NUMBER AT A TIME, entering only
...               the number that fits, and checks the app accepts each one.
Library           SudokuLibrary.py
Suite Setup       Open App
Suite Teardown    Close App
# The app has no checking by default. Most tests need right/wrong feedback,
# so each test starts with "Check as I go" switched on.
Test Setup        Set Check As I Go    on
Test Template     Solve Puzzle Left To Right


*** Variables ***
${HEADLESS}       True
${SLOW_MO}        0
${PORT}           5001
&{MIN_EMPTY}      easy=30    medium=40    hard=45    expert=48
${STEP_DELAY}     0.4s
${TRY_LEVEL}      easy


*** Test Cases ***              DIFFICULTY
Solve Easy Sudoku               easy
Solve Medium Sudoku             medium
Solve Hard Sudoku               hard
Solve Expert Sudoku             expert

Wrong Number Is Rejected
    [Template]    NONE
    Start New Game    easy
    ${board}=        Read Board From Page
    ${solution}=     Solve Board    ${board}
    ${cells}=        Get Empty Cells Left To Right    ${board}
    ${row}    ${col}=    Set Variable    ${cells}[0]
    ${wrong}=        Get Wrong Number    ${board}    ${solution}    ${row}    ${col}
    Enter Number     ${row}    ${col}    ${wrong}
    Cell Should Be Wrong    ${row}    ${col}
    Mistakes Should Be      1
    ${right}=        Get Number That Fits    ${board}    ${solution}    ${row}    ${col}
    Enter Number     ${row}    ${col}    ${right}
    Cell Should Be Correct    ${row}    ${col}

Try Numbers One By One In First Empty Cell
    [Documentation]    Try 1..9 in the first empty cell until the app accepts one.
    [Template]    NONE
    Start New Game    medium
    ${board}=        Read Board From Page
    ${cells}=        Get Empty Cells Left To Right    ${board}
    ${row}    ${col}=    Set Variable    ${cells}[0]
    ${candidates}=   Get Candidates    ${board}    ${row}    ${col}
    Log    Numbers that fit the rules at (${row},${col}): ${candidates}
    FOR    ${n}    IN RANGE    1    10
        Enter Number    ${row}    ${col}    ${n}
        ${ok}=    Cell Is Correct    ${row}    ${col}
        IF    ${ok}
            Log    App accepted ${n} at (${row},${col})
            BREAK
        END
    END
    Should Be True    ${ok}    No number 1-9 was accepted
    Should Contain    ${candidates}    ${n}

Solve By Trying 1 To 9 In Every Cell
    [Documentation]    Like a person: in each empty cell (left to right, row by row)
    ...    try the numbers in order, skipping any already in the same row,
    ...    column or 3x3 box, until the app accepts one.
    [Tags]    trial
    [Template]    NONE
    Start New Game    ${TRY_LEVEL}
    ${board}=    Read Board From Page
    ${cells}=    Get Empty Cells Left To Right    ${board}
    FOR    ${cell}    IN    @{cells}
        ${row}    ${col}=    Set Variable    ${cell}
        Try Numbers Until Correct    ${board}    ${row}    ${col}
    END
    Empty Count Should Be    0
    Board Should Be Solved
    Take Board Screenshot    solved-by-trying.png

Given Numbers Cannot Be Changed
    [Template]    NONE
    Start New Game    easy
    Given Cells Should Be Read Only

No Checking Until The Board Is Full
    [Documentation]    With "Check as I go" off, a wrong number is not shown as
    ...    wrong until every cell is filled. Then the app checks the whole board.
    [Template]    NONE
    Set Check As I Go    off
    Start New Game    easy
    ${board}=       Read Board From Page
    ${solution}=    Solve Board    ${board}
    ${cells}=       Get Empty Cells Left To Right    ${board}
    # Put a wrong number in the first empty cell, everything else right.
    ${first}=       Set Variable    ${cells}[0]
    ${wrong}=       Get Wrong Number    ${board}    ${solution}    ${first}[0]    ${first}[1]
    Enter Number    ${first}[0]    ${first}[1]    ${wrong}
    Wrong Cell Count Should Be    0
    FOR    ${cell}    IN    @{cells}[1:]
        Enter Number    ${cell}[0]    ${cell}[1]    ${solution}[${cell}[0]][${cell}[1]]
    END
    Message Should Contain        Not quite: 1 number is wrong
    Wrong Cell Count Should Be    1
    Cell Should Be Wrong          ${first}[0]    ${first}[1]
    # Fix it.
    Enter Number    ${first}[0]    ${first}[1]    ${solution}[${first}[0]][${first}[1]]
    Board Should Be Solved

Undo And Erase
    [Template]    NONE
    Set Check As I Go    off
    Start New Game    easy
    ${board}=    Read Board From Page
    ${cells}=    Get Empty Cells Left To Right    ${board}
    ${row}    ${col}=    Set Variable    ${cells}[0]
    Press Key In Cell      ${row}    ${col}    5
    Press Key In Cell      ${row}    ${col}    7
    Cell Value Should Be   ${row}    ${col}    7
    Click Button           undo
    Cell Value Should Be   ${row}    ${col}    5
    Press Key In Cell      ${row}    ${col}    ControlOrMeta+z
    Cell Value Should Be   ${row}    ${col}    ${EMPTY}
    Press Key In Cell      ${row}    ${col}    3
    Click Button           erase
    Cell Value Should Be   ${row}    ${col}    ${EMPTY}
    Press Key In Cell      ${row}    ${col}    4
    Press Key In Cell      ${row}    ${col}    Backspace
    Cell Value Should Be   ${row}    ${col}    ${EMPTY}

Pencil Notes
    [Template]    NONE
    Start New Game    easy
    ${board}=       Read Board From Page
    ${solution}=    Solve Board    ${board}
    ${cells}=       Get Empty Cells Left To Right    ${board}
    ${row}    ${col}=    Set Variable    ${cells}[0]
    Click Cell             ${row}    ${col}
    Click Button           notes
    Notes Mode Should Be   On
    Press Key In Cell      ${row}    ${col}    1
    Press Key In Cell      ${row}    ${col}    5
    Press Key In Cell      ${row}    ${col}    9
    Cell Notes Should Be   ${row}    ${col}    1    5    9
    Cell Value Should Be   ${row}    ${col}    ${EMPTY}
    Press Key In Cell      ${row}    ${col}    5
    Cell Notes Should Be   ${row}    ${col}    1    9
    Click Button           undo
    Cell Notes Should Be   ${row}    ${col}    1    5    9
    Press Key In Cell      ${row}    ${col}    n
    Notes Mode Should Be   Off
    Enter Number           ${row}    ${col}    ${solution}[${row}][${col}]
    Cell Should Be Correct    ${row}    ${col}
    Cell Notes Should Be   ${row}    ${col}

Three Hints Per Game
    [Template]    NONE
    Start New Game    medium
    ${board}=       Read Board From Page
    ${solution}=    Solve Board    ${board}
    Hints Left Should Be    3
    FOR    ${left}    IN    2    1    0
        Click Button            hint
        Hints Left Should Be    ${left}
    END
    Hint Button Should Be Disabled
    ${hinted}=    Get Hinted Cells
    Length Should Be    ${hinted}    3
    FOR    ${cell}    IN    @{hinted}
        Should Be Equal As Integers    ${cell}[2]    ${solution}[${cell}[0]][${cell}[1]]
    END

Selected Cell Highlights Its Row Column And Box
    [Template]    NONE
    Start New Game    easy
    Click Cell    4    4
    Highlighted Cells Should Be    4    4
    Click Cell    0    8
    Highlighted Cells Should Be    0    8


*** Keywords ***
Open App
    ${url}=    Start Sudoku Server    ${PORT}
    Open Sudoku App    ${url}    headless=${HEADLESS}    slow_mo=${SLOW_MO}

Close App
    Close Sudoku App
    Stop Sudoku Server

Try Numbers Until Correct
    [Arguments]    ${board}    ${row}    ${col}
    # Skip numbers already in this row, column or 3x3 box.
    ${candidates}=    Get Candidates    ${board}    ${row}    ${col}
    Log    Cell (${row},${col}): try only ${candidates} (others are already in row/column/box)
    FOR    ${n}    IN    @{candidates}
        Enter Number    ${row}    ${col}    ${n}
        Sleep    ${STEP_DELAY}
        ${ok}=    Cell Is Correct    ${row}    ${col}
        IF    ${ok}
            Log    Cell (${row},${col}): tried ${candidates} -> ${n} is CORRECT    console=True
            Set Board Value    ${board}    ${row}    ${col}    ${n}
            RETURN
        ELSE
            Log    Cell (${row},${col}): ${n} is wrong
        END
    END
    Fail    None of ${candidates} was accepted at (${row},${col})

Solve Puzzle Left To Right
    [Arguments]    ${difficulty}
    Start New Game    ${difficulty}
    ${board}=       Read Board From Page
    ${empty}=       Count Empty Cells    ${board}
    Should Be True    ${empty} >= ${MIN_EMPTY}[${difficulty}]
    ...    ${difficulty} puzzle has only ${empty} empty cells
    Board Should Have One Solution    ${board}
    Empty Count Should Be    ${empty}
    ${solution}=    Solve Board    ${board}
    ${cells}=       Get Empty Cells Left To Right    ${board}
    FOR    ${cell}    IN    @{cells}
        ${row}    ${col}=    Set Variable    ${cell}
        ${number}=    Get Number That Fits    ${board}    ${solution}    ${row}    ${col}
        Enter Number             ${row}    ${col}    ${number}
        Cell Should Be Correct   ${row}    ${col}
        Set Board Value          ${board}    ${row}    ${col}    ${number}
    END
    Mistakes Should Be       0
    Empty Count Should Be    0
    Board Should Be Solved
    Take Board Screenshot    solved-${difficulty}.png
