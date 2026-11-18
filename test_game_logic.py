from main import WIN_LINES

def has_won(board, symbol):
    return any(all(board[i] == symbol for i in line) for line in WIN_LINES)

def test_horizontal_win():
    board = ["A", "A", "A", "", "B", "", "", "", ""]
    assert has_won(board, "A")

def test_no_winner_on_empty_board():
    board = [""] * 9
    assert not has_won(board, "A")

def test_diagonal_win():
    board = ["C", "", "", "", "C", "", "", "", "C"]
    assert has_won(board, "C")
