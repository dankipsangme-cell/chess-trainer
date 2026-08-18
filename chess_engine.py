"""
Minimal but complete chess rules engine (no external dependencies).
Board squares are indexed 0..63:  a1=0, b1=1, ... h1=7, a2=8, ... h8=63.
"""

import copy

FILES = "abcdefgh"

def sq(file, rank):
    return rank * 8 + file

def sq_name(s):
    return FILES[s % 8] + str(s // 8 + 1)

def parse_sq(name):
    return sq(FILES.index(name[0]), int(name[1]) - 1)

WHITE, BLACK = "w", "b"

KNIGHT_OFFS = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]
KING_OFFS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
BISHOP_DIRS = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
ROOK_DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
QUEEN_DIRS = BISHOP_DIRS + ROOK_DIRS


class Move:
    __slots__ = ("frm", "to", "promo", "is_ep", "is_castle")

    def __init__(self, frm, to, promo=None, is_ep=False, is_castle=None):
        self.frm = frm
        self.to = to
        self.promo = promo          # 'q','r','b','n' or None
        self.is_ep = is_ep          # en-passant capture
        self.is_castle = is_castle  # 'K','Q' (for the moving side) or None

    def uci(self):
        s = sq_name(self.frm) + sq_name(self.to)
        if self.promo:
            s += self.promo
        return s

    def __eq__(self, other):
        return (self.frm, self.to, self.promo) == (other.frm, other.to, other.promo)

    def __repr__(self):
        return self.uci()


class Position:
    def __init__(self):
        self.board = list("RNBQKBNR" + "P" * 8 + "." * 32 + "p" * 8 + "rnbqkbnr")
        self.turn = WHITE
        self.castling = set(["K", "Q", "k", "q"])
        self.ep_square = None
        self.halfmove = 0
        self.fullmove = 1

    def clone(self):
        return copy.deepcopy(self)

    def piece_at(self, s):
        return self.board[s]

    def color_of(self, piece):
        if piece == ".":
            return None
        return WHITE if piece.isupper() else BLACK

    def find_king(self, color):
        target = "K" if color == WHITE else "k"
        return self.board.index(target)

    # ---------- attack detection ----------
    def is_attacked(self, target, by_color):
        board = self.board
        tf, tr = target % 8, target // 8

        # pawns
        pawn = "P" if by_color == WHITE else "p"
        dr = -1 if by_color == WHITE else 1  # attacker's pawn sits one rank behind (from target's view)
        for df in (-1, 1):
            f, r = tf + df, tr + dr
            if 0 <= f < 8 and 0 <= r < 8:
                if board[sq(f, r)] == pawn:
                    return True

        # knights
        knight = "N" if by_color == WHITE else "n"
        for df, dr2 in KNIGHT_OFFS:
            f, r = tf + df, tr + dr2
            if 0 <= f < 8 and 0 <= r < 8 and board[sq(f, r)] == knight:
                return True

        # king
        king = "K" if by_color == WHITE else "k"
        for df, dr2 in KING_OFFS:
            f, r = tf + df, tr + dr2
            if 0 <= f < 8 and 0 <= r < 8 and board[sq(f, r)] == king:
                return True

        # sliding: bishop/queen
        bishoplike = ("B", "Q") if by_color == WHITE else ("b", "q")
        for df, dr2 in BISHOP_DIRS:
            f, r = tf + df, tr + dr2
            while 0 <= f < 8 and 0 <= r < 8:
                p = board[sq(f, r)]
                if p != ".":
                    if p in bishoplike:
                        return True
                    break
                f += df
                r += dr2

        rooklike = ("R", "Q") if by_color == WHITE else ("r", "q")
        for df, dr2 in ROOK_DIRS:
            f, r = tf + df, tr + dr2
            while 0 <= f < 8 and 0 <= r < 8:
                p = board[sq(f, r)]
                if p != ".":
                    if p in rooklike:
                        return True
                    break
                f += df
                r += dr2

        return False

    def king_in_check(self, color):
        return self.is_attacked(self.find_king(color), BLACK if color == WHITE else WHITE)

    # ---------- move generation ----------
    def pseudo_legal_moves(self):
        moves = []
        board = self.board
        color = self.turn
        opp = BLACK if color == WHITE else WHITE

        for s in range(64):
            p = board[s]
            if p == "." or self.color_of(p) != color:
                continue
            f, r = s % 8, s // 8
            kind = p.upper()

            if kind == "P":
                fwd = 1 if color == WHITE else -1
                start_rank = 1 if color == WHITE else 6
                promo_rank = 7 if color == WHITE else 0
                # single push
                nr = r + fwd
                if 0 <= nr < 8 and board[sq(f, nr)] == ".":
                    dest = sq(f, nr)
                    if nr == promo_rank:
                        for pr in ("q", "r", "b", "n"):
                            moves.append(Move(s, dest, promo=pr))
                    else:
                        moves.append(Move(s, dest))
                    # double push
                    if r == start_rank:
                        nr2 = r + 2 * fwd
                        if board[sq(f, nr2)] == ".":
                            moves.append(Move(s, sq(f, nr2)))
                # captures
                for df in (-1, 1):
                    nf, nr2 = f + df, r + fwd
                    if 0 <= nf < 8 and 0 <= nr2 < 8:
                        dest = sq(nf, nr2)
                        target = board[dest]
                        if target != "." and self.color_of(target) == opp:
                            if nr2 == promo_rank:
                                for pr in ("q", "r", "b", "n"):
                                    moves.append(Move(s, dest, promo=pr))
                            else:
                                moves.append(Move(s, dest))
                        elif self.ep_square == dest:
                            moves.append(Move(s, dest, is_ep=True))

            elif kind == "N":
                for df, dr in KNIGHT_OFFS:
                    nf, nr = f + df, r + dr
                    if 0 <= nf < 8 and 0 <= nr < 8:
                        dest = sq(nf, nr)
                        target = board[dest]
                        if target == "." or self.color_of(target) == opp:
                            moves.append(Move(s, dest))

            elif kind == "K":
                for df, dr in KING_OFFS:
                    nf, nr = f + df, r + dr
                    if 0 <= nf < 8 and 0 <= nr < 8:
                        dest = sq(nf, nr)
                        target = board[dest]
                        if target == "." or self.color_of(target) == opp:
                            moves.append(Move(s, dest))
                moves.extend(self._castle_moves(color))

            else:
                dirs = BISHOP_DIRS if kind == "B" else ROOK_DIRS if kind == "R" else QUEEN_DIRS
                for df, dr in dirs:
                    nf, nr = f + df, r + dr
                    while 0 <= nf < 8 and 0 <= nr < 8:
                        dest = sq(nf, nr)
                        target = board[dest]
                        if target == ".":
                            moves.append(Move(s, dest))
                        else:
                            if self.color_of(target) == opp:
                                moves.append(Move(s, dest))
                            break
                        nf += df
                        nr += dr
        return moves

    def _castle_moves(self, color):
        moves = []
        board = self.board
        opp = BLACK if color == WHITE else WHITE
        if color == WHITE:
            if "K" in self.castling and board[5] == "." and board[6] == "." and board[7] == "R":
                if not self.is_attacked(4, opp) and not self.is_attacked(5, opp) and not self.is_attacked(6, opp):
                    moves.append(Move(4, 6, is_castle="K"))
            if "Q" in self.castling and board[1] == "." and board[2] == "." and board[3] == "." and board[0] == "R":
                if not self.is_attacked(4, opp) and not self.is_attacked(3, opp) and not self.is_attacked(2, opp):
                    moves.append(Move(4, 2, is_castle="Q"))
        else:
            if "k" in self.castling and board[61] == "." and board[62] == "." and board[63] == "r":
                if not self.is_attacked(60, opp) and not self.is_attacked(61, opp) and not self.is_attacked(62, opp):
                    moves.append(Move(60, 62, is_castle="K"))
            if "q" in self.castling and board[57] == "." and board[58] == "." and board[59] == "." and board[56] == "r":
                if not self.is_attacked(60, opp) and not self.is_attacked(59, opp) and not self.is_attacked(58, opp):
                    moves.append(Move(60, 58, is_castle="Q"))
        return moves

    def legal_moves(self):
        legal = []
        for m in self.pseudo_legal_moves():
            nb = self.clone()
            nb._apply(m)
            if not nb.king_in_check(self.turn):
                legal.append(m)
        return legal

    def is_capture(self, m):
        return self.board[m.to] != "." or m.is_ep

    # ---------- apply ----------
    def _apply(self, m):
        board = self.board
        piece = board[m.frm]
        color = self.color_of(piece)
        kind = piece.upper()

        self.ep_square_next = None

        if m.is_ep:
            board[m.to] = piece
            board[m.frm] = "."
            cap_sq = m.to - 8 if color == WHITE else m.to + 8
            board[cap_sq] = "."
        elif m.is_castle:
            board[m.to] = piece
            board[m.frm] = "."
            if color == WHITE:
                if m.is_castle == "K":
                    board[5], board[7] = board[7], "."
                else:
                    board[3], board[0] = board[0], "."
            else:
                if m.is_castle == "K":
                    board[61], board[63] = board[63], "."
                else:
                    board[59], board[56] = board[56], "."
        else:
            if m.promo:
                newp = m.promo.upper() if color == WHITE else m.promo.lower()
                board[m.to] = newp
            else:
                board[m.to] = piece
            board[m.frm] = "."

        # en passant target square update
        if kind == "P" and abs(m.to - m.frm) == 16:
            self.ep_square = (m.frm + m.to) // 2
        else:
            self.ep_square = None

        # castling rights update
        if kind == "K":
            self.castling.discard("K" if color == WHITE else "k")
            self.castling.discard("Q" if color == WHITE else "q")
        for corner, right in ((0, "Q"), (7, "K"), (56, "q"), (63, "k")):
            if m.frm == corner or m.to == corner:
                self.castling.discard(right)

        self.turn = BLACK if color == WHITE else WHITE
        if color == BLACK:
            self.fullmove += 1

    def push(self, m):
        self._apply(m)

    def is_checkmate(self):
        return self.king_in_check(self.turn) and not self.legal_moves()

    def is_stalemate(self):
        return not self.king_in_check(self.turn) and not self.legal_moves()

    def result_string(self):
        if self.is_checkmate():
            winner = "Black" if self.turn == WHITE else "White"
            return f"Checkmate — {winner} wins"
        if self.is_stalemate():
            return "Stalemate — draw"
        return None

    def print_board(self):
        lines = []
        for r in range(7, -1, -1):
            row = [self.board[sq(f, r)] for f in range(8)]
            lines.append(f"{r + 1} " + " ".join(row))
        lines.append("  a b c d e f g h")
        print("\n".join(lines))
