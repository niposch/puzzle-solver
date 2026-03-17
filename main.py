from z3 import *
import numpy as np

North = 0
East = 1
South = 2
West = 3

SIDE_TO_ENTRY = {
    North: lambda n, size: (0, n, South),
    East: lambda n, size: (n, size - 1, West),
    South: lambda n, size: (size - 1, n, North),
    West: lambda n, size: (n, 0, East),
}

DIR_TO_EXIT_SIDE = {
    South: lambda r, c: (North, c),
    West: lambda r, c: (East, r),
    North: lambda r, c: (South, c),
    East: lambda r, c: (West, r),
}

offsets = [
    [np.array([-1, 0]), np.array([0, -1])],  # north
    [np.array([0, 1]), np.array([-1, 0])],  # east
    [np.array([1, 0]), np.array([0, 1])],  # south
    [np.array([0, -1]), np.array([1, 0])],  # west
]

# ─── edge addressing ──────────────────────────────────────────────────────────


def side_to_entry(side, n, grid_size):
    """Convert (side, index) to (r, c, inward_direction)."""
    try:
        return SIDE_TO_ENTRY[side](n, grid_size)
    except KeyError as exc:
        raise ValueError(f"unknown side: {side}") from exc


def entry_to_side(r, c, d, grid_size):
    """Convert (r, c, inward_direction) to (side, index)."""
    _ = grid_size
    try:
        return DIR_TO_EXIT_SIDE[d](r, c)
    except KeyError as exc:
        raise ValueError(f"unknown direction: {d}") from exc


def exit_dir(inward_dir):
    return (inward_dir + 2) % 4


# ─── solver ───────────────────────────────────────────────────────────────────


def in_field(vec, grid_size):
    return 0 <= vec[0] < grid_size and 0 <= vec[1] < grid_size


def make_variables(grid_size, num_lasers):
    balls = [
        [Bool(f"ball_{r}_{c}") for c in range(grid_size)] for r in range(grid_size)
    ]
    active = [
        [
            [
                [Bool(f"laser_{L}_{r}_{c}_{d}") for d in range(4)]
                for c in range(grid_size)
            ]
            for r in range(grid_size)
        ]
        for L in range(num_lasers)
    ]
    return balls, active


def make_solver(grid_size, ball_count, laser_entries):
    """laser_entries: list of (r, c, inward_direction)"""
    s = Solver()
    balls, active = make_variables(grid_size, len(laser_entries))
    add_ball_count_constraint(s, balls, ball_count, grid_size)
    for i, (row, col, direction) in enumerate(laser_entries):
        add_laser_constraints(s, balls, active, grid_size, i, row, col, direction)
    return s, balls, active


def add_ball_count_constraint(s, balls, ball_count, grid_size):
    all_balls = [balls[r][c] for r in range(grid_size) for c in range(grid_size)]
    s.add(PbEq([(b, 1) for b in all_balls], ball_count))


def add_laser_constraints(
    s, balls, active, grid_size, laser_idx, entry_r, entry_c, entry_d
):
    for r in range(grid_size):
        for c in range(grid_size):
            for d in range(4):
                [forward, left] = offsets[d]
                pos = np.array([r, c])
                infront_coord = pos + forward
                front_left_coord = pos + forward + left
                front_right_coord = pos + forward - left
                back_coord = pos - forward

                laser_here = active[laser_idx][r][c][d]
                laser_left = active[laser_idx][r][c][(d - 1) % 4]
                laser_right = active[laser_idx][r][c][(d + 1) % 4]
                laser_backwards = active[laser_idx][r][c][(d + 2) % 4]

                ball_left = (
                    balls[int(front_left_coord[0])][int(front_left_coord[1])]
                    if in_field(front_left_coord, grid_size)
                    else False
                )
                ball_right = (
                    balls[int(front_right_coord[0])][int(front_right_coord[1])]
                    if in_field(front_right_coord, grid_size)
                    else False
                )
                ball_entry_left = (
                    balls[int((pos + left)[0])][int((pos + left)[1])]
                    if in_field(pos + left, grid_size)
                    else False
                )
                ball_entry_right = (
                    balls[int((pos - left)[0])][int((pos - left)[1])]
                    if in_field(pos - left, grid_size)
                    else False
                )

                if in_field(back_coord, grid_size):
                    d_from_right = (d + 1) % 4
                    [fwd_fr, lft_fr] = offsets[d_from_right]
                    pred_right_ball = pos + fwd_fr - lft_fr

                    d_from_left = (d - 1) % 4
                    [fwd_fl, lft_fl] = offsets[d_from_left]
                    pred_left_ball = pos + fwd_fl + lft_fl

                    d_opp = (d + 2) % 4
                    [fwd_opp, lft_opp] = offsets[d_opp]
                    opp_ball_left = (
                        balls[int((pos + fwd_opp + lft_opp)[0])][
                            int((pos + fwd_opp + lft_opp)[1])
                        ]
                        if in_field(pos + fwd_opp + lft_opp, grid_size)
                        else False
                    )
                    opp_ball_right = (
                        balls[int((pos + fwd_opp - lft_opp)[0])][
                            int((pos + fwd_opp - lft_opp)[1])
                        ]
                        if in_field(pos + fwd_opp - lft_opp, grid_size)
                        else False
                    )

                    from_straight = active[laser_idx][int(back_coord[0])][
                        int(back_coord[1])
                    ][d]
                    from_right_deflect = (
                        And(
                            active[laser_idx][r][c][d_from_right],
                            balls[int(pred_right_ball[0])][int(pred_right_ball[1])],
                        )
                        if in_field(pred_right_ball, grid_size)
                        else False
                    )
                    from_left_deflect = (
                        And(
                            active[laser_idx][r][c][d_from_left],
                            balls[int(pred_left_ball[0])][int(pred_left_ball[1])],
                        )
                        if in_field(pred_left_ball, grid_size)
                        else False
                    )
                    from_180 = And(
                        active[laser_idx][r][c][d_opp], opp_ball_left, opp_ball_right
                    )
                    from_edge_refl = (
                        And(
                            active[laser_idx][r][c][(d + 2) % 4],
                            Or(ball_entry_left, ball_entry_right),
                        )
                        if (r == entry_r and c == entry_c and d == (entry_d + 2) % 4)
                        else False
                    )

                    s.add(
                        Implies(
                            laser_here,
                            Or(
                                from_straight,
                                from_right_deflect,
                                from_left_deflect,
                                from_180,
                                from_edge_refl,
                            ),
                        )
                    )
                else:
                    if not (r == entry_r and c == entry_c and d == entry_d):
                        s.add(Not(laser_here))
                    else:
                        s.add(
                            Implies(And(laser_here, balls[r][c]), Not(laser_backwards))
                        )
                        s.add(
                            Implies(
                                And(
                                    laser_here,
                                    Not(balls[r][c]),
                                    Or(ball_entry_left, ball_entry_right),
                                ),
                                laser_backwards,
                            )
                        )
                        if in_field(infront_coord, grid_size):
                            lf = active[laser_idx][int(infront_coord[0])][
                                int(infront_coord[1])
                            ][d]
                            s.add(Implies(And(laser_here, balls[r][c]), Not(lf)))
                            s.add(
                                Implies(
                                    And(
                                        laser_here,
                                        Not(balls[r][c]),
                                        Or(ball_entry_left, ball_entry_right),
                                    ),
                                    Not(lf),
                                )
                            )

                if not in_field(infront_coord, grid_size):
                    continue

                laser_forward = active[laser_idx][int(infront_coord[0])][
                    int(infront_coord[1])
                ][d]
                absorption = balls[int(infront_coord[0])][int(infront_coord[1])]
                at_entry = r == entry_r and c == entry_c and d == entry_d
                entry_absorption = And(at_entry, balls[r][c])
                entry_adj_ball = (
                    Or(ball_entry_left, ball_entry_right) if at_entry else False
                )

                s.add(
                    Implies(
                        And(
                            laser_here,
                            Not(ball_left),
                            Not(ball_right),
                            Not(absorption),
                            Not(entry_absorption),
                            Not(entry_adj_ball),
                        ),
                        And(laser_forward, Not(laser_backwards)),
                    )
                )
                s.add(
                    Implies(
                        And(laser_here, ball_left, ball_right),
                        And(laser_backwards, Not(laser_forward)),
                    )
                )
                s.add(
                    Implies(
                        And(laser_here, ball_right, Not(ball_left)),
                        And(laser_left, Not(laser_forward)),
                    )
                )
                s.add(
                    Implies(
                        And(laser_here, Not(ball_right), ball_left),
                        And(laser_right, Not(laser_forward)),
                    )
                )
                s.add(Implies(And(laser_here, absorption), Not(laser_forward)))


# ─── simulate (plain Python, for verification) ────────────────────────────────


def simulate(grid_size, ball_positions, entry_r, entry_c, entry_d):
    ball_set = set(ball_positions)
    visited, seen = [], set()
    r, c, d = entry_r, entry_c, entry_d

    while True:
        if (r, c, d) in seen:
            break
        seen.add((r, c, d))
        visited.append((r, c, d))

        [forward, left] = offsets[d]
        pos = np.array([r, c])

        if not in_field(pos - forward, grid_size) and (r, c) in ball_set:
            break

        # edge special case: ball adjacent to entry reflects immediately
        if not in_field(pos - forward, grid_size):
            adj_l = (
                tuple(pos + left) in ball_set
                if in_field(pos + left, grid_size)
                else False
            )
            adj_r = (
                tuple(pos - left) in ball_set
                if in_field(pos - left, grid_size)
                else False
            )
            if adj_l or adj_r:
                d = (d + 2) % 4
                continue

        infront = pos + forward
        fl = pos + forward + left
        fr = pos + forward - left

        ball_infront = (
            tuple(infront) in ball_set if in_field(infront, grid_size) else False
        )
        ball_left = tuple(fl) in ball_set if in_field(fl, grid_size) else False
        ball_right = tuple(fr) in ball_set if in_field(fr, grid_size) else False

        if ball_infront:
            break
        elif ball_left and ball_right:
            d = (d + 2) % 4
            continue
        elif ball_left:
            d = (d + 1) % 4
            continue
        elif ball_right:
            d = (d - 1) % 4
            continue
        else:
            nr, nc = int(infront[0]), int(infront[1])
            if not in_field(np.array([nr, nc]), grid_size):
                break
            r, c = nr, nc

    return visited


# ─── verify helper ────────────────────────────────────────────────────────────

from rich.table import Table
from rich import print as rprint

SIDE_NAMES = {North: "N", East: "E", South: "S", West: "W"}


def fmt_result(result):
    if result in ("H", "R"):
        return result
    side, n = result
    return f"({SIDE_NAMES[side]},{n})"


def verify_observations_against_simulate(balls_set, N):
    results = {}
    for side in [North, East, South, West]:
        for n in range(N):
            r, c, d = side_to_entry(side, n, N)
            path = simulate(N, balls_set, r, c, d)
            last_r, last_c, last_d = path[-1]
            last_infront = np.array([last_r, last_c]) + offsets[last_d][0]
            if in_field(last_infront, N):
                result = "H"
            else:
                exit_side = entry_to_side(last_r, last_c, (last_d + 2) % 4, N)
                result = "R" if exit_side == (side, n) else exit_side
            results[(side, n)] = result

    table = Table(show_header=False, box=None, padding=(0, 1))
    for _ in range(N + 2):
        table.add_column(justify="center")

    # top edge
    top = (
        [""] + [f"(N,{n})\n{fmt_result(results[(North, n)])}" for n in range(N)] + [""]
    )
    table.add_row(*top)

    # grid rows
    for row in range(N):
        left = f"(W,{row})\n{fmt_result(results[(West, row)])}"
        right = f"(E,{row})\n{fmt_result(results[(East, row)])}"
        cells = [" O " if (row, col) in balls_set else " . " for col in range(N)]
        table.add_row(left, *cells, right)

    # bottom edge
    bot = (
        [""] + [f"(S,{n})\n{fmt_result(results[(South, n)])}" for n in range(N)] + [""]
    )
    table.add_row(*bot)

    rprint(table)


# ─── tests ────────────────────────────────────────────────────────────────────


def test_straight_through():
    laser = side_to_entry(West, 1, 4)
    r, c, d = laser
    s, balls, active = make_solver(grid_size=4, ball_count=0, laser_entries=[laser])
    s.add(active[0][r][c][d])
    s.add(Not(active[0][1][3][East]))
    assert s.check() == unsat, "laser should reach far side with no balls"


def test_absorption():
    laser = side_to_entry(West, 1, 4)
    r, c, d = laser
    s, balls, active = make_solver(grid_size=4, ball_count=1, laser_entries=[laser])
    s.add(balls[1][2])
    s.add(active[0][r][c][d])
    s.add(active[0][1][3][East])
    assert s.check() == unsat, "laser should be absorbed before reaching far side"


def test_no_absorption_without_ball():
    laser = side_to_entry(West, 1, 4)
    r, c, d = laser
    s, balls, active = make_solver(grid_size=4, ball_count=0, laser_entries=[laser])
    s.add(active[0][r][c][d])
    assert s.check() == sat
    m = s.model()
    assert is_true(m.eval(active[0][1][2][East])), "laser should pass through freely"


def test_reflection_right():
    laser = side_to_entry(West, 2, 4)
    r, c, d = laser
    s, balls, active = make_solver(grid_size=4, ball_count=1, laser_entries=[laser])
    s.add(balls[3][1])
    s.add(active[0][r][c][d])
    assert s.check() == sat
    m = s.model()
    assert is_true(m.eval(active[0][2][0][North])), "laser should deflect to North"
    assert not is_true(m.eval(active[0][2][1][East])), "laser should not continue East"


def test_reflection_left():
    laser = side_to_entry(West, 2, 4)
    r, c, d = laser
    s, balls, active = make_solver(grid_size=4, ball_count=1, laser_entries=[laser])
    s.add(balls[1][1])
    s.add(active[0][r][c][d])
    assert s.check() == sat
    m = s.model()
    assert is_true(m.eval(active[0][2][0][South])), "laser should deflect to South"
    assert not is_true(m.eval(active[0][2][1][East])), "laser should not continue East"


def test_reflection_back():
    laser = side_to_entry(West, 2, 4)
    r, c, d = laser
    s, balls, active = make_solver(grid_size=4, ball_count=2, laser_entries=[laser])
    s.add(balls[1][1])
    s.add(balls[3][1])
    s.add(active[0][r][c][d])
    assert s.check() == sat
    m = s.model()
    assert is_true(m.eval(active[0][2][0][West])), "laser should reflect back West"
    assert not is_true(m.eval(active[0][2][1][East])), "laser should not enter the grid"


def test_double_deflection():
    laser = side_to_entry(West, 2, 4)
    r, c, d = laser
    s, balls, active = make_solver(grid_size=4, ball_count=2, laser_entries=[laser])
    s.add(balls[3][1])
    s.add(balls[0][1])
    s.add(active[0][r][c][d])
    assert s.check() == sat
    m = s.model()
    assert is_true(m.eval(active[0][2][0][East])), "laser comes in going East"
    assert is_true(m.eval(active[0][2][0][North])), "first deflection North"
    assert is_true(m.eval(active[0][1][0][North])), "goes North"
    assert is_true(m.eval(active[0][1][0][West])), "second deflection West"


def test_two_lasers_no_interference():
    lasers = [side_to_entry(West, 2, 4), side_to_entry(West, 0, 4)]
    s, balls, active = make_solver(grid_size=4, ball_count=3, laser_entries=lasers)
    s.add(balls[3][1])
    s.add(balls[1][1])
    s.add(active[1][0][0][East])
    s.add(active[0][2][0][East])
    assert s.check() == sat
    m = s.model()
    assert is_true(m.eval(active[0][2][0][East]))
    assert is_true(m.eval(active[0][2][0][West]))
    assert is_true(m.eval(active[1][0][0][East]))
    assert is_true(m.eval(active[1][0][0][North]))


def test_special_case_ball_on_edge():
    laser = side_to_entry(West, 2, 4)
    r, c, d = laser
    s, balls, active = make_solver(grid_size=4, ball_count=2, laser_entries=[laser])
    s.add(balls[1][0])
    s.add(active[0][r][c][d])
    assert s.check() == sat
    m = s.model()
    assert is_true(m.eval(active[0][2][0][East])), "laser comes in going East"
    assert is_true(m.eval(active[0][2][0][West])), "gets deflected out immediately"


def test_puzzle_from_screenshot():
    N = 5
    balls = {(1, 0), (1, 4), (3, 4)}

    hits = [
        (North, 0),
        (North, 4),
        (East, 1),
        (East, 3),
        (South, 0),
        (South, 4),
        (West, 3),
        (West, 1),
    ]
    reflect = [(East, 0), (East, 2), (East, 4), (West, 0), (West, 2), (South, 1)]
    pairs = [
        ((West, 4), (South, 3)),
        ((South, 2), (North, 2)),
        ((North, 1), (North, 3)),
    ]

    observed = {}
    for side in [North, East, South, West]:
        for n in range(N):
            r, c, d = side_to_entry(side, n, N)
            path = simulate(N, balls, r, c, d)
            last_r, last_c, last_d = path[-1]
            last_infront = np.array([last_r, last_c]) + offsets[last_d][0]
            if in_field(last_infront, N):
                observed[(side, n)] = "H"
            else:
                exit_side = entry_to_side(last_r, last_c, exit_dir(last_d), N)
                observed[(side, n)] = "R" if exit_side == (side, n) else exit_side

    for side_n in hits:
        assert observed[side_n] == "H"
    for side_n in reflect:
        assert observed[side_n] == "R"
    for side_a, side_b in pairs:
        assert observed[side_a] == side_b
        assert observed[side_b] == side_a


if __name__ == "__main__":
    verify_observations_against_simulate({(1, 0), (1, 4), (3, 4)}, 5)
