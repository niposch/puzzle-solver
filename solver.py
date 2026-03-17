from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

import numpy as np
from z3 import And, Bool, Implies, Not, Or, PbEq, Solver, is_true, sat, unsat

NORTH = 0
EAST = 1
SOUTH = 2
WEST = 3

SIDE_TO_ENTRY = {
    NORTH: lambda n, size: (0, n, SOUTH),
    EAST: lambda n, size: (n, size - 1, WEST),
    SOUTH: lambda n, size: (size - 1, n, NORTH),
    WEST: lambda n, size: (n, 0, EAST),
}

DIR_TO_EXIT_SIDE = {
    SOUTH: lambda r, c: (NORTH, c),
    WEST: lambda r, c: (EAST, r),
    NORTH: lambda r, c: (SOUTH, c),
    EAST: lambda r, c: (WEST, r),
}

OFFSETS = [
    [np.array([-1, 0]), np.array([0, -1])],
    [np.array([0, 1]), np.array([-1, 0])],
    [np.array([1, 0]), np.array([0, 1])],
    [np.array([0, -1]), np.array([1, 0])],
]

SIDE_NAMES = {NORTH: "N", EAST: "E", SOUTH: "S", WEST: "W"}

North = NORTH
East = EAST
South = SOUTH
West = WEST
offsets = OFFSETS


@dataclass(frozen=True)
class EdgePosition:
    side: str
    index: int


@dataclass(frozen=True)
class Solution:
    grid_size: int
    ball_positions: tuple[tuple[int, int], ...]


def side_to_entry(side: int, n: int, grid_size: int) -> tuple[int, int, int]:
    try:
        return SIDE_TO_ENTRY[side](n, grid_size)
    except KeyError as exc:
        raise ValueError(f"unknown side: {side}") from exc


def entry_to_side(r: int, c: int, d: int, grid_size: int) -> tuple[int, int]:
    _ = grid_size
    try:
        return DIR_TO_EXIT_SIDE[d](r, c)
    except KeyError as exc:
        raise ValueError(f"unknown direction: {d}") from exc


def exit_dir(inward_dir: int) -> int:
    return (inward_dir + 2) % 4


def in_field(vec, grid_size: int) -> bool:
    return 0 <= vec[0] < grid_size and 0 <= vec[1] < grid_size


def make_variables(grid_size: int, num_lasers: int):
    balls = [
        [Bool(f"ball_{r}_{c}") for c in range(grid_size)] for r in range(grid_size)
    ]
    active = [
        [
            [
                [Bool(f"laser_{laser}_{r}_{c}_{d}") for d in range(4)]
                for c in range(grid_size)
            ]
            for r in range(grid_size)
        ]
        for laser in range(num_lasers)
    ]
    return balls, active


def make_solver(
    grid_size: int, ball_count: int, laser_entries: list[tuple[int, int, int]]
):
    solver = Solver()
    balls, active = make_variables(grid_size, len(laser_entries))
    add_ball_count_constraint(solver, balls, ball_count, grid_size)
    for laser_idx, (row, col, direction) in enumerate(laser_entries):
        add_laser_constraints(
            solver, balls, active, grid_size, laser_idx, row, col, direction
        )
    return solver, balls, active


def add_ball_count_constraint(solver: Solver, balls, ball_count: int, grid_size: int):
    all_balls = [balls[r][c] for r in range(grid_size) for c in range(grid_size)]
    solver.add(PbEq([(ball, 1) for ball in all_balls], ball_count))


def add_laser_constraints(
    solver: Solver,
    balls,
    active,
    grid_size: int,
    laser_idx: int,
    entry_r: int,
    entry_c: int,
    entry_d: int,
):
    for r in range(grid_size):
        for c in range(grid_size):
            for d in range(4):
                forward, left = OFFSETS[d]
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
                    fwd_fr, lft_fr = OFFSETS[d_from_right]
                    pred_right_ball = pos + fwd_fr - lft_fr

                    d_from_left = (d - 1) % 4
                    fwd_fl, lft_fl = OFFSETS[d_from_left]
                    pred_left_ball = pos + fwd_fl + lft_fl

                    d_opp = (d + 2) % 4
                    fwd_opp, lft_opp = OFFSETS[d_opp]
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

                    solver.add(
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
                        solver.add(Not(laser_here))
                    else:
                        solver.add(Implies(And(laser_here, balls[r][c]), True))
                        solver.add(
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
                            laser_forward = active[laser_idx][int(infront_coord[0])][
                                int(infront_coord[1])
                            ][d]
                            solver.add(Implies(And(laser_here, balls[r][c]), True))
                            solver.add(
                                Implies(
                                    And(
                                        laser_here,
                                        Not(balls[r][c]),
                                        Or(ball_entry_left, ball_entry_right),
                                    ),
                                    True,
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

                solver.add(
                    Implies(
                        And(
                            laser_here,
                            Not(ball_left),
                            Not(ball_right),
                            Not(absorption),
                            Not(entry_absorption),
                            Not(entry_adj_ball),
                        ),
                        laser_forward,
                    )
                )
                solver.add(
                    Implies(
                        And(laser_here, ball_left, ball_right),
                        laser_backwards,
                    )
                )
                solver.add(
                    Implies(
                        And(laser_here, ball_right, Not(ball_left)),
                        laser_left,
                    )
                )
                solver.add(
                    Implies(
                        And(laser_here, Not(ball_right), ball_left),
                        laser_right,
                    )
                )
                solver.add(Implies(And(laser_here, absorption), Not(laser_forward)))


def all_edge_positions(grid_size: int) -> list[EdgePosition]:
    positions = [EdgePosition("N", index) for index in range(grid_size)]
    positions.extend(EdgePosition("E", index) for index in range(grid_size))
    positions.extend(EdgePosition("S", index) for index in range(grid_size))
    positions.extend(EdgePosition("W", index) for index in range(grid_size))
    return positions


def edge_to_entry(edge: EdgePosition, grid_size: int) -> tuple[int, int, int]:
    if edge.side == "N":
        return side_to_entry(NORTH, edge.index, grid_size)
    if edge.side == "E":
        return side_to_entry(EAST, edge.index, grid_size)
    if edge.side == "S":
        return side_to_entry(SOUTH, edge.index, grid_size)
    if edge.side == "W":
        return side_to_entry(WEST, edge.index, grid_size)
    raise ValueError(f"Unsupported side: {edge.side}")


def edge_to_exit(edge: EdgePosition, grid_size: int) -> tuple[int, int, int]:
    if edge.side == "N":
        return 0, edge.index, NORTH
    if edge.side == "E":
        return edge.index, grid_size - 1, EAST
    if edge.side == "S":
        return grid_size - 1, edge.index, SOUTH
    if edge.side == "W":
        return edge.index, 0, WEST
    raise ValueError(f"Unsupported side: {edge.side}")


def validate_clues(grid_size: int, clues: dict[EdgePosition, str]) -> None:
    valid_edges = set(all_edge_positions(grid_size))
    number_counts = Counter()
    for edge, clue in clues.items():
        if edge not in valid_edges:
            raise ValueError(f"Invalid edge position: {edge}")
        if clue in {"H", "R"}:
            continue
        if not clue.isdigit() or int(clue) <= 0:
            raise ValueError(f"Unsupported clue value: {clue}")
        number_counts[clue] += 1
    incomplete = [value for value, count in number_counts.items() if count != 2]
    if incomplete:
        raise ValueError(
            "Each numbered clue must appear exactly twice. Incomplete: "
            + ", ".join(sorted(incomplete, key=int))
        )


def add_expected_exit_constraint(
    solver: Solver,
    active,
    laser_idx: int,
    grid_size: int,
    expected_exit: EdgePosition | None,
) -> None:
    for edge in all_edge_positions(grid_size):
        row, col, direction = edge_to_exit(edge, grid_size)
        if expected_exit is not None and edge == expected_exit:
            solver.add(active[laser_idx][row][col][direction])
        else:
            solver.add(Not(active[laser_idx][row][col][direction]))


def clue_to_expected_exit(
    edge: EdgePosition,
    clue: str,
    numbered_edges: dict[str, list[EdgePosition]],
) -> EdgePosition | None:
    if clue == "H":
        return None
    if clue == "R":
        return edge
    exits = [candidate for candidate in numbered_edges[clue] if candidate != edge]
    return exits[0]


def build_clue_solver(grid_size: int, ball_count: int, clues: dict[EdgePosition, str]):
    numbered_edges = defaultdict(list)
    for edge, clue in clues.items():
        if clue.isdigit():
            numbered_edges[clue].append(edge)

    laser_edges = list(clues)
    laser_entries = [edge_to_entry(edge, grid_size) for edge in laser_edges]
    solver, balls, active = make_solver(grid_size, ball_count, laser_entries)

    for laser_idx, edge in enumerate(laser_edges):
        entry_row, entry_col, entry_direction = laser_entries[laser_idx]
        solver.add(active[laser_idx][entry_row][entry_col][entry_direction])
        expected_exit = clue_to_expected_exit(edge, clues[edge], numbered_edges)
        add_expected_exit_constraint(
            solver, active, laser_idx, grid_size, expected_exit
        )

    return solver, balls


def solve_from_clues(
    grid_size: int, ball_count: int, clues: dict[EdgePosition, str]
) -> Solution | None:
    validate_clues(grid_size, clues)
    clue_solver, clue_balls = build_clue_solver(grid_size, ball_count, clues)
    if clue_solver.check() != sat:
        return None

    model = clue_solver.model()
    ball_positions = tuple(
        (r, c)
        for r in range(grid_size)
        for c in range(grid_size)
        if is_true(model.eval(clue_balls[r][c], model_completion=True))
    )
    return Solution(grid_size=grid_size, ball_positions=ball_positions)


def format_ball_positions(solution: Solution) -> str:
    if not solution.ball_positions:
        return "No balls"
    return ", ".join(f"({row + 1}, {col + 1})" for row, col in solution.ball_positions)


def fmt_result(result) -> str:
    if result in ("H", "R"):
        return result
    side, n = result
    return f"({SIDE_NAMES[side]},{n})"


def simulate(
    grid_size: int,
    ball_positions: set[tuple[int, int]] | tuple[tuple[int, int], ...],
    entry_r: int,
    entry_c: int,
    entry_d: int,
):
    ball_set = set(ball_positions)
    visited, seen = [], set()
    r, c, d = entry_r, entry_c, entry_d

    while True:
        if (r, c, d) in seen:
            break
        seen.add((r, c, d))
        visited.append((r, c, d))

        forward, left = OFFSETS[d]
        pos = np.array([r, c])

        if not in_field(pos - forward, grid_size) and (r, c) in ball_set:
            break

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
        if ball_left and ball_right:
            d = (d + 2) % 4
            continue
        if ball_left:
            d = (d + 1) % 4
            continue
        if ball_right:
            d = (d - 1) % 4
            continue

        nr, nc = int(infront[0]), int(infront[1])
        if not in_field(np.array([nr, nc]), grid_size):
            break
        r, c = nr, nc

    return visited


__all__ = [
    "EAST",
    "NORTH",
    "SOUTH",
    "WEST",
    "EdgePosition",
    "Solution",
    "East",
    "North",
    "South",
    "West",
    "add_expected_exit_constraint",
    "all_edge_positions",
    "build_clue_solver",
    "edge_to_entry",
    "edge_to_exit",
    "entry_to_side",
    "exit_dir",
    "format_ball_positions",
    "in_field",
    "make_solver",
    "offsets",
    "side_to_entry",
    "simulate",
    "solve_from_clues",
    "unsat",
    "validate_clues",
]
