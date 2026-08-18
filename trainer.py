"""
Chess Trainer — learn and play chess quickly.

Modes:
  1) Play against the engine (you play White or Black)
  2) Ask the engine to suggest & explain the best move in a position
  3) Tactics trainer — quick puzzles that teach pattern recognition
  4) Opening principles cheat-sheet

Run:  python3 trainer.py
"""

from chess_engine import Position, Move, WHITE, BLACK, sq_name, parse_sq
from chess_ai import evaluate, best_moves, PIECE_VALUES

PIECE_NAMES = {"P": "pawn", "N": "knight", "B": "bishop", "R": "rook", "Q": "queen", "K": "king"}
CENTER = {parse_sq(n) for n in ("d4", "d5", "e4", "e5")}


# ---------------------------------------------------------------- explanations
def explain_move(pos: Position, m: Move) -> str:
    """Very lightweight, rule-based commentary — good enough to teach the 'why'."""
    reasons = []
    piece = pos.board[m.frm]
    kind = piece.upper()
    color = WHITE if piece.isupper() else BLACK

    if pos.is_capture(m):
        target = pos.board[m.to]
        if target != ".":
            reasons.append(f"captures a {PIECE_NAMES[target.upper()]}")
        else:
            reasons.append("captures en passant")

    if m.is_castle:
        reasons.append("gets the king to safety and connects the rooks (castling)")

    if m.promo:
        reasons.append(f"promotes the pawn to a {PIECE_NAMES[m.promo.upper()]}")

    if m.to in CENTER and kind in ("P", "N", "B"):
        reasons.append("stakes a claim on the center")

    if kind in ("N", "B") and (m.frm // 8) in (0, 7):
        reasons.append("develops a piece off the back rank")

    child = pos.clone()
    child.push(m)
    if child.king_in_check(child.turn):
        reasons.append("gives check")

    if not reasons:
        reasons.append("improves piece activity / position")

    return "; ".join(reasons)


def score_to_text(score, side_to_move_before):
    """score is from perspective of side to move BEFORE the move (negamax convention
    used by best_moves), so a positive number is good for whoever is moving."""
    pawns = score / 100
    who = "White" if side_to_move_before == WHITE else "Black"
    if score > 20000:
        return f"{who} is winning big (near-forced mate)"
    sign = "+" if pawns >= 0 else ""
    return f"{sign}{pawns:.2f} pawns in {who}'s favor"


# ---------------------------------------------------------------- modes
def suggest_mode():
    pos = Position()
    while True:
        pos.print_board()
        print(f"\nTurn: {'White' if pos.turn == WHITE else 'Black'}")
        result = pos.result_string()
        if result:
            print(result)
            break
        print("Commands: move e.g. 'e2e4' (add promo letter for pawn promotion, e.g. e7e8q)")
        print("          'hint' = show top 3 suggested moves with explanations")
        print("          'quit' = back to menu\n")
        cmd = input("> ").strip().lower()
        if cmd == "quit":
            break
        if cmd == "hint":
            depth = 3
            print("Thinking...")
            suggestions = best_moves(pos, depth=depth, top_n=3)
            for i, (m, score) in enumerate(suggestions, 1):
                print(f"  {i}. {m.uci():6s}  ({score_to_text(score, pos.turn)}) — {explain_move(pos, m)}")
            print()
            continue
        move = _parse_user_move(pos, cmd)
        if move is None:
            print("Sorry, that's not a legal move (or bad format). Try again.\n")
            continue
        print(f"-> {explain_move(pos, move)}")
        pos.push(move)
        print()


def _parse_user_move(pos, text):
    if len(text) not in (4, 5):
        return None
    try:
        frm = parse_sq(text[0:2])
        to = parse_sq(text[2:4])
    except (ValueError, IndexError):
        return None
    promo = text[4] if len(text) == 5 else None
    for m in pos.legal_moves():
        if m.frm == frm and m.to == to and (m.promo == promo or (promo is None and m.promo is None)):
            return m
        if m.frm == frm and m.to == to and m.promo and promo == m.promo:
            return m
    return None


def play_mode():
    print("Play as White or Black? (w/b): ", end="")
    human_color = WHITE if input().strip().lower().startswith("w") else BLACK
    depth = 3
    pos = Position()
    while True:
        pos.print_board()
        result = pos.result_string()
        if result:
            print("\n" + result)
            break
        if pos.turn == human_color:
            print(f"\nYour move ({'White' if human_color == WHITE else 'Black'}). "
                  f"Format e2e4, or 'hint', or 'quit'.")
            cmd = input("> ").strip().lower()
            if cmd == "quit":
                break
            if cmd == "hint":
                m, score = best_moves(pos, depth=depth, top_n=1)[0]
                print(f"Suggestion: {m.uci()}  ({score_to_text(score, pos.turn)}) — {explain_move(pos, m)}\n")
                continue
            move = _parse_user_move(pos, cmd)
            if move is None:
                print("Illegal move or bad format. Use e.g. e2e4.\n")
                continue
            pos.push(move)
        else:
            print("\nEngine is thinking...")
            m, score = best_moves(pos, depth=depth, top_n=1)[0]
            print(f"Engine plays {m.uci()} — {explain_move(pos, m)}")
            pos.push(m)
        print()


# ---------------------------------------------------------------- tactics trainer
PUZZLES = [
    {
        "desc": "White to move. Find the fork.",
        "board": "6k1/5ppp/8/8/4N3/8/8/6K1 w - - 0 1",
        "solution": "e4f6",
        "explain": "The knight forks the king and would fork rook/king patterns like this "
                    "any time a knight can jump to a square attacking two undefended targets "
                    "at once — always scan for knight forks when the enemy king is exposed.",
    },
    {
        "desc": "White to move. Win material with a pin-exploiting capture.",
        "board": "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
        "solution": "f3e5",
        "explain": "The knight on e5 grabs a central pawn; because Black's own pieces are still "
                    "undeveloped, tactics like this are common in the opening if you develop faster "
                    "than your opponent.",
    },
    {
        "desc": "White to move, mate in 1.",
        "board": "6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1",
        "solution": "a1a8",
        "explain": "A rook on an open file delivers back-rank mate when the enemy king has no "
                    "escape square — always check for back-rank mate ideas when the opponent's "
                    "king is boxed in by its own pawns.",
    },
]


def parse_fen(fen):
    parts = fen.split()
    board_part, turn, castling, ep = parts[0], parts[1], parts[2], parts[3]
    pos = Position()
    # FEN ranks run rank8 -> rank1, each rank left(a) -> right(h); convert to our
    # sq-index scheme where index 0 = a1 ... 63 = h8.
    fixed = [None] * 64
    idx = 0
    ranks = board_part.split("/")
    for r_i, row in enumerate(ranks):  # r_i=0 is rank8
        rank_num = 7 - r_i
        file_i = 0
        for ch in row:
            if ch.isdigit():
                file_i += int(ch)
            else:
                fixed[rank_num * 8 + file_i] = ch
                file_i += 1
    pos.board = [c if c else "." for c in fixed]
    pos.turn = WHITE if turn == "w" else BLACK
    pos.castling = set(c for c in castling if c in "KQkq")
    pos.ep_square = None if ep == "-" else parse_sq(ep)
    return pos


def tactics_mode():
    import random
    puzzles = PUZZLES[:]
    random.shuffle(puzzles)
    solved = 0
    for i, pz in enumerate(puzzles, 1):
        pos = parse_fen(pz["board"])
        print(f"\nPuzzle {i}/{len(puzzles)}: {pz['desc']}")
        pos.print_board()
        guess = input("Your move (e.g. e2e4), or 'skip': ").strip().lower()
        if guess == pz["solution"]:
            print("Correct! " + pz["explain"])
            solved += 1
        else:
            print(f"Not quite. Best was {pz['solution']}. {pz['explain']}")
    print(f"\nScore: {solved}/{len(puzzles)}")


OPENING_TIPS = """
OPENING PRINCIPLES (apply these in the first ~10 moves of every game)
 1. Control the center — occupy or attack d4/d5/e4/e5 early (pawns first).
 2. Develop knights before bishops, and develop before you attack.
 3. Castle early (usually by move 6-10) to get your king safe and rook active.
 4. Don't move the same piece twice in the opening without a good reason.
 5. Don't bring your queen out too early — it can be chased around, losing tempo.
 6. Connect your rooks (clear the back rank) once development is done.
 7. Every move, ask: "does this help development, center control, or king safety?"

COMMON TACTICAL PATTERNS TO RECOGNIZE
 - Fork: one piece attacks two+ enemy pieces at once (knights are the classic forker).
 - Pin: a piece can't move without exposing a more valuable piece behind it.
 - Skewer: like a pin, but the more valuable piece is in front and forced to move,
   exposing the piece behind it.
 - Discovered attack: moving one piece reveals an attack from another piece behind it.
 - Back-rank mate: a king trapped behind its own pawns is mated by a rook/queen on
   the back rank.

Fastest way to actually improve: play games, then run 'hint' on every move you're
unsure about and read the explanation — pattern recognition builds from repetition.
"""


def main():
    while True:
        print("\n=== Chess Trainer ===")
        print("1) Play against the engine")
        print("2) Move-suggestion sandbox (set up any game, get hints + explanations)")
        print("3) Tactics puzzles")
        print("4) Opening principles / cheat sheet")
        print("5) Quit")
        choice = input("> ").strip()
        if choice == "1":
            play_mode()
        elif choice == "2":
            suggest_mode()
        elif choice == "3":
            tactics_mode()
        elif choice == "4":
            print(OPENING_TIPS)
        elif choice == "5":
            break
        else:
            print("Pick 1-5.")


if __name__ == "__main__":
    main()
