from chess_engine import Position, WHITE, BLACK

PIECE_VALUES = {"P": 100, "N": 320, "B": 330, "R": 500, "Q": 900, "K": 0}

# Simplified piece-square tables (white's perspective, rank1->rank8 top-to-bottom
# here written rank8 first for readability, then reversed to match board order).
PAWN_PST = [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
]
KNIGHT_PST = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50,
]
BISHOP_PST = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20,
]
ROOK_PST = [
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0,
]
QUEEN_PST = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20,
]
KING_PST = [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20,
]

PST = {"P": PAWN_PST, "N": KNIGHT_PST, "B": BISHOP_PST, "R": ROOK_PST, "Q": QUEEN_PST, "K": KING_PST}


def _pst_value(kind, square, color):
    table = PST[kind]
    # table index 0 corresponds to rank8/a8 in the array above; our sq index 0 is a1.
    row = square // 8
    col = square % 8
    if color == WHITE:
        table_index = (7 - row) * 8 + col
    else:
        table_index = row * 8 + col
    return table[table_index]


def evaluate(pos: Position) -> int:
    """Positive = good for White, negative = good for Black."""
    score = 0
    for s, p in enumerate(pos.board):
        if p == ".":
            continue
        kind = p.upper()
        color = WHITE if p.isupper() else BLACK
        val = PIECE_VALUES[kind] + _pst_value(kind, s, color)
        score += val if color == WHITE else -val
    if pos.king_in_check(pos.turn):
        score += -30 if pos.turn == WHITE else 30
    return score


def order_moves(pos, moves):
    def key(m):
        return 1 if pos.is_capture(m) else 0
    return sorted(moves, key=key, reverse=True)


def negamax(pos, depth, alpha, beta):
    """Returns score from the perspective of the side to move (negamax convention)."""
    if depth == 0:
        s = evaluate(pos)
        return s if pos.turn == WHITE else -s

    moves = pos.legal_moves()
    if not moves:
        if pos.king_in_check(pos.turn):
            return -100000 + (5 - depth)  # checkmate, prefer faster mates
        return 0  # stalemate

    best = -10**9
    for m in order_moves(pos, moves):
        child = pos.clone()
        child.push(m)
        score = -negamax(child, depth - 1, -beta, -alpha)
        if score > best:
            best = score
        if best > alpha:
            alpha = best
        if alpha >= beta:
            break
    return best


def best_moves(pos: Position, depth=3, top_n=3):
    """Returns a list of (move, score) sorted best-first, score from side-to-move's perspective."""
    moves = pos.legal_moves()
    scored = []
    for m in order_moves(pos, moves):
        child = pos.clone()
        child.push(m)
        score = -negamax(child, depth - 1, -10**9, 10**9)
        scored.append((m, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_n]
