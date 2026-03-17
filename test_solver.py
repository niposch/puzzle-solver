import numpy as np
from z3 import Not, is_true, sat, unsat

from solver import (
    EAST,
    NORTH,
    East,
    North,
    SOUTH,
    South,
    WEST,
    West,
    EdgePosition,
    entry_to_side,
    exit_dir,
    in_field,
    make_solver,
    offsets,
    side_to_entry,
    simulate,
    solve_from_clues,
)


def test_straight_through():
    laser = side_to_entry(WEST, 1, 4)
    r, c, d = laser
    solver, balls, active = make_solver(
        grid_size=4, ball_count=0, laser_entries=[laser]
    )
    solver.add(active[0][r][c][d])
    solver.add(Not(active[0][1][3][EAST]))
    assert solver.check() == unsat


def test_absorption():
    laser = side_to_entry(WEST, 1, 4)
    r, c, d = laser
    solver, balls, active = make_solver(
        grid_size=4, ball_count=1, laser_entries=[laser]
    )
    solver.add(balls[1][2])
    solver.add(active[0][r][c][d])
    solver.add(active[0][1][3][EAST])
    assert solver.check() == unsat


def test_no_absorption_without_ball():
    laser = side_to_entry(WEST, 1, 4)
    r, c, d = laser
    solver, balls, active = make_solver(
        grid_size=4, ball_count=0, laser_entries=[laser]
    )
    solver.add(active[0][r][c][d])
    assert solver.check() == sat
    model = solver.model()
    assert is_true(model.eval(active[0][1][2][EAST]))


def test_reflection_right():
    laser = side_to_entry(WEST, 2, 4)
    r, c, d = laser
    solver, balls, active = make_solver(
        grid_size=4, ball_count=1, laser_entries=[laser]
    )
    solver.add(balls[3][1])
    solver.add(active[0][r][c][d])
    assert solver.check() == sat
    model = solver.model()
    assert is_true(model.eval(active[0][2][0][NORTH]))
    assert not is_true(model.eval(active[0][2][1][EAST]))


def test_reflection_left():
    laser = side_to_entry(WEST, 2, 4)
    r, c, d = laser
    solver, balls, active = make_solver(
        grid_size=4, ball_count=1, laser_entries=[laser]
    )
    solver.add(balls[1][1])
    solver.add(active[0][r][c][d])
    assert solver.check() == sat
    model = solver.model()
    assert is_true(model.eval(active[0][2][0][SOUTH]))
    assert not is_true(model.eval(active[0][2][1][EAST]))


def test_reflection_back():
    laser = side_to_entry(WEST, 2, 4)
    r, c, d = laser
    solver, balls, active = make_solver(
        grid_size=4, ball_count=2, laser_entries=[laser]
    )
    solver.add(balls[1][1])
    solver.add(balls[3][1])
    solver.add(active[0][r][c][d])
    assert solver.check() == sat
    model = solver.model()
    assert is_true(model.eval(active[0][2][0][WEST]))
    assert not is_true(model.eval(active[0][2][1][EAST]))


def test_double_deflection():
    laser = side_to_entry(WEST, 2, 4)
    r, c, d = laser
    solver, balls, active = make_solver(
        grid_size=4, ball_count=2, laser_entries=[laser]
    )
    solver.add(balls[3][1])
    solver.add(balls[0][1])
    solver.add(active[0][r][c][d])
    assert solver.check() == sat
    model = solver.model()
    assert is_true(model.eval(active[0][2][0][EAST]))
    assert is_true(model.eval(active[0][2][0][NORTH]))
    assert is_true(model.eval(active[0][1][0][NORTH]))
    assert is_true(model.eval(active[0][1][0][WEST]))


def test_two_lasers_no_interference():
    lasers = [side_to_entry(WEST, 2, 4), side_to_entry(WEST, 0, 4)]
    solver, balls, active = make_solver(grid_size=4, ball_count=3, laser_entries=lasers)
    solver.add(balls[3][1])
    solver.add(balls[1][1])
    solver.add(active[1][0][0][EAST])
    solver.add(active[0][2][0][EAST])
    assert solver.check() == sat
    model = solver.model()
    assert is_true(model.eval(active[0][2][0][EAST]))
    assert is_true(model.eval(active[0][2][0][WEST]))
    assert is_true(model.eval(active[1][0][0][EAST]))
    assert is_true(model.eval(active[1][0][0][NORTH]))


def test_special_case_ball_on_edge():
    laser = side_to_entry(WEST, 2, 4)
    r, c, d = laser
    solver, balls, active = make_solver(
        grid_size=4, ball_count=2, laser_entries=[laser]
    )
    solver.add(balls[1][0])
    solver.add(active[0][r][c][d])
    assert solver.check() == sat
    model = solver.model()
    assert is_true(model.eval(active[0][2][0][EAST]))
    assert is_true(model.eval(active[0][2][0][WEST]))


def test_solve_from_number_pair():
    clues = {
        EdgePosition("W", 2): "1",
        EdgePosition("N", 0): "1",
    }
    solution = solve_from_clues(grid_size=4, ball_count=1, clues=clues)
    assert solution is not None
    assert solution.ball_positions == ((3, 1),)


def test_numbered_clues_must_be_pairs():
    try:
        solve_from_clues(
            grid_size=4,
            ball_count=1,
            clues={EdgePosition("W", 2): "1"},
        )
    except ValueError as exc:
        assert "exactly twice" in str(exc)
    else:
        raise AssertionError("Expected ValueError for incomplete numbered clue")


def test_puzzle_from_screenshot():
    grid_size = 5
    balls = {(1, 0), (1, 4), (3, 4)}

    hits = [
        (NORTH, 0),
        (NORTH, 4),
        (EAST, 1),
        (EAST, 3),
        (SOUTH, 0),
        (SOUTH, 4),
        (WEST, 3),
        (WEST, 1),
    ]
    reflect = [(EAST, 0), (EAST, 2), (EAST, 4), (WEST, 0), (WEST, 2), (SOUTH, 1)]
    pairs = [
        ((WEST, 4), (SOUTH, 3)),
        ((SOUTH, 2), (NORTH, 2)),
        ((NORTH, 1), (NORTH, 3)),
    ]

    observed = {}
    for side in [NORTH, EAST, SOUTH, WEST]:
        for n in range(grid_size):
            r, c, d = side_to_entry(side, n, grid_size)
            path = simulate(grid_size, balls, r, c, d)
            last_r, last_c, last_d = path[-1]
            last_infront = (
                np.array([last_r, last_c])
                + [
                    np.array([-1, 0]),
                    np.array([0, 1]),
                    np.array([1, 0]),
                    np.array([0, -1]),
                ][last_d]
            )
            if in_field(last_infront, grid_size):
                observed[(side, n)] = "H"
            else:
                exit_side = entry_to_side(last_r, last_c, exit_dir(last_d), grid_size)
                observed[(side, n)] = "R" if exit_side == (side, n) else exit_side

    for side_n in hits:
        assert observed[side_n] == "H"
    for side_n in reflect:
        assert observed[side_n] == "R"
    for side_a, side_b in pairs:
        assert observed[side_a] == side_b
        assert observed[side_b] == side_a


def test_puzzle_from_screenshot_original_regression():
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


def test_solve_from_screenshot_clues():
    clues = {
        EdgePosition("N", 0): "H",
        EdgePosition("N", 1): "3",
        EdgePosition("N", 2): "2",
        EdgePosition("N", 3): "3",
        EdgePosition("N", 4): "H",
        EdgePosition("W", 0): "R",
        EdgePosition("W", 1): "H",
        EdgePosition("W", 2): "R",
        EdgePosition("W", 3): "H",
        EdgePosition("W", 4): "1",
        EdgePosition("E", 0): "R",
        EdgePosition("E", 1): "H",
        EdgePosition("E", 2): "R",
        EdgePosition("E", 3): "H",
        EdgePosition("E", 4): "R",
        EdgePosition("S", 0): "H",
        EdgePosition("S", 1): "R",
        EdgePosition("S", 2): "2",
        EdgePosition("S", 3): "1",
        EdgePosition("S", 4): "H",
    }

    solution = solve_from_clues(grid_size=5, ball_count=3, clues=clues)
    assert solution is not None
    assert set(solution.ball_positions) == {(1, 0), (1, 4), (3, 4)}
