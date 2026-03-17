from z3 import *
import numpy as np

North = 0
East = 1
South = 2
West = 3

offsets = [
    [np.array([-1, 0]), np.array([0, -1])],  # north
    [np.array([0, 1]),  np.array([-1, 0])],  # east
    [np.array([1, 0]),  np.array([0, 1])],   # south
    [np.array([0, -1]), np.array([1, 0])],   # west
]

def in_field(vec, grid_size):
    return 0 <= vec[0] < grid_size and 0 <= vec[1] < grid_size

def make_variables(grid_size):
    balls = [[Bool(f"ball_{r}_{c}") for c in range(grid_size)] for r in range(grid_size)]
    active = [[[Bool(f"laser_{r}_{c}_{d}") for d in range(4)] for c in range(grid_size)] for r in range(grid_size)]
    return balls, active

def add_ball_count_constraint(s, balls, ball_count, grid_size):
    all_balls = [balls[r][c] for r in range(grid_size) for c in range(grid_size)]
    s.add(PbEq([(b, 1) for b in all_balls], ball_count))

def add_laser_constraints(s, balls, active, grid_size):
    for r in range(grid_size):
        for c in range(grid_size):
            for d in range(4):
                [forward, left] = offsets[d]
                pos = np.array([r, c])
                infront_coord = pos + forward
                front_right_coord = pos + forward - left
                front_left_coord = pos + forward + left

                if not in_field(infront_coord, grid_size):
                    continue

                laser_here = active[r][c][d]
                laser_forward = active[infront_coord[0]][infront_coord[1]][d]

                ball_left = balls[front_left_coord[0]][front_left_coord[1]] if in_field(front_left_coord, grid_size) else False
                ball_right = balls[front_right_coord[0]][front_right_coord[1]] if in_field(front_right_coord, grid_size) else False
                absorption = balls[infront_coord[0]][infront_coord[1]]

                laser_left = # todo
                laser_rigth = # todo
                laser_backwards = # todo

                # laser continues straight
                s.add(Implies(
                    And(laser_here, Not(ball_left), Not(ball_right), Not(absorption)),
                    laser_forward
                ))

                # laser gets reflected back
                s.add(Implies(
                    And(laser_here, ball_right, ball_left),
                    laser_backwards
                ))

                # laser gets reflected left
                s.add(Implies(
                    And(laser_here, ball_right, Not(ball_left)),
                    laser_left
                ))

                # laser gets reflected right
                s.add(Implies(
                    And(laser_here, Not(ball_right), ball_left),
                    laser_right
                ))

                # laser gets absorbed
                s.add(Implies(
                    And(laser_here, absorption),
                    Not(laser_forward)
                ))

def make_solver(grid_size, ball_count):
    s = Solver()
    balls, active = make_variables(grid_size)
    add_ball_count_constraint(s, balls, ball_count, grid_size)
    add_laser_constraints(s, balls, active, grid_size)
    return s, balls, active


# --- tests ---

def test_straight_through():
    s, balls, active = make_solver(grid_size=4, ball_count=0)
    s.add(active[1][0][East])
    s.add(Not(active[1][3][East]))
    assert s.check() == unsat, "laser should reach far side with no balls"

def test_absorption():
    s, balls, active = make_solver(grid_size=4, ball_count=1)
    s.add(balls[1][2])
    s.add(active[1][0][East])
    s.add(active[1][3][East])
    assert s.check() == unsat, "laser should be absorbed before reaching far side"

def test_no_absorption_without_ball():
    s, balls, active = make_solver(grid_size=4, ball_count=0)
    s.add(active[1][0][East])
    assert s.check() == sat
    m = s.model()
    assert is_true(m.eval(active[1][2][East])), "laser should pass through freely"