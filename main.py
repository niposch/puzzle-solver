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

def make_variables(grid_size, num_lasers):
    balls  = [[Bool(f"ball_{r}_{c}") for c in range(grid_size)] for r in range(grid_size)]
    active = [[[[Bool(f"laser_{L}_{r}_{c}_{d}") for d in range(4)] for c in range(grid_size)] for r in range(grid_size)] for L in range(num_lasers)]
    return balls, active

# laser entries is: [(row, column, direction)]
def make_solver(grid_size, ball_count, laser_entries):
    s = Solver()
    balls, active = make_variables(grid_size, len(laser_entries))
    add_ball_count_constraint(s, balls, ball_count, grid_size)
    for i, (row, col, direction) in enumerate(laser_entries):
        add_laser_constraints(s, balls, active, grid_size, i, row, col, direction)
    return s, balls, active

def add_ball_count_constraint(s, balls, ball_count, grid_size):
    all_balls = [balls[r][c] for r in range(grid_size) for c in range(grid_size)]
    s.add(PbEq([(b, 1) for b in all_balls], ball_count))

def add_laser_constraints(s, balls, active, grid_size, laser_idx, entry_r, entry_c, entry_d):
    for r in range(grid_size):
        for c in range(grid_size):
            for d in range(4):
                [forward, left] = offsets[d]
                pos = np.array([r, c])
                infront_coord     = pos + forward
                front_left_coord  = pos + forward + left
                front_right_coord = pos + forward - left
                back_coord        = pos - forward

                laser_here      = active[laser_idx][r][c][d]
                laser_left      = active[laser_idx][r][c][(d - 1) % 4]
                laser_right     = active[laser_idx][r][c][(d + 1) % 4]
                laser_backwards = active[laser_idx][r][c][(d + 2) % 4]

                ball_left  = balls[int(front_left_coord[0])][int(front_left_coord[1])]   if in_field(front_left_coord,  grid_size) else False
                ball_right = balls[int(front_right_coord[0])][int(front_right_coord[1])] if in_field(front_right_coord, grid_size) else False

                if in_field(back_coord, grid_size):
                    d_from_right = (d + 1) % 4
                    [forward_from_right, left_from_right] = offsets[d_from_right]
                    pred_right_reflection_ball_pos = pos + forward_from_right - left_from_right

                    d_from_left = (d - 1) % 4
                    [forward_from_left, left_from_left] = offsets[d_from_left]
                    pred_left_reflection_ball_pos = pos + forward_from_left + left_from_left

                    d_opp = (d + 2) % 4
                    [forward_opp, left_opp] = offsets[d_opp]
                    opp_ball_left  = balls[int((pos + forward_opp + left_opp)[0])][int((pos + forward_opp + left_opp)[1])] if in_field(pos + forward_opp + left_opp, grid_size) else False
                    opp_ball_right = balls[int((pos + forward_opp - left_opp)[0])][int((pos + forward_opp - left_opp)[1])] if in_field(pos + forward_opp - left_opp, grid_size) else False

                    from_straight      = active[laser_idx][int(back_coord[0])][int(back_coord[1])][d]
                    from_right_deflect = And(active[laser_idx][r][c][d_from_right], balls[int(pred_right_reflection_ball_pos[0])][int(pred_right_reflection_ball_pos[1])]) if in_field(pred_right_reflection_ball_pos, grid_size) else False
                    from_left_deflect  = And(active[laser_idx][r][c][d_from_left],  balls[int(pred_left_reflection_ball_pos[0])][int(pred_left_reflection_ball_pos[1])]) if in_field(pred_left_reflection_ball_pos, grid_size) else False
                    from_180           = And(active[laser_idx][r][c][d_opp], opp_ball_left, opp_ball_right)

                    from_edge_reflection = And(
                            active[laser_idx][r][c][(d + 2) % 4],
                            Or(ball_entry_left, ball_entry_right)
                        ) if (r == entry_r and c == entry_c and d == (entry_d + 2) % 4) else False

                    s.add(Implies(laser_here, Or(from_straight, from_right_deflect, from_left_deflect, from_180, from_edge_reflection)))
                else:
                    if not (r == entry_r and c == entry_c and d == entry_d):
                        s.add(Not(laser_here))
                    else:
                        # edge case: ball adjacent to entry reflects immediately
                        ball_entry_left  = balls[int((pos + left)[0])][int((pos + left)[1])]  if in_field(pos + left,  grid_size) else False
                        ball_entry_right = balls[int((pos - left)[0])][int((pos - left)[1])]  if in_field(pos - left, grid_size) else False

                        s.add(Implies(
                            And(laser_here, Or(ball_entry_left, ball_entry_right)),
                            laser_backwards
                        ))

                if not in_field(infront_coord, grid_size):
                    continue

                laser_forward = active[laser_idx][int(infront_coord[0])][int(infront_coord[1])][d]
                absorption    = balls[int(infront_coord[0])][int(infront_coord[1])]

                s.add(Implies(
                    And(laser_here, Not(ball_left), Not(ball_right), Not(absorption)),
                    And(laser_forward, Not(laser_backwards))
                ))
                s.add(Implies(
                    And(laser_here, ball_left, ball_right),
                    And(laser_backwards, Not(laser_forward))
                ))
                s.add(Implies(
                    And(laser_here, ball_right, Not(ball_left)),
                    And(laser_left, Not(laser_forward))
                ))
                s.add(Implies(
                    And(laser_here, Not(ball_right), ball_left),
                    And(laser_right, Not(laser_forward))
                ))
                s.add(Implies(
                    And(laser_here, absorption),
                    Not(laser_forward)
                ))


# --- tests ---

def test_straight_through():
    lasers = [(1,0,East)]
    s, balls, active = make_solver(grid_size=4, ball_count=0, laser_entries=lasers)
    s.add(active[0][1][0][East])
    s.add(Not(active[0][1][3][East]))
    assert s.check() == unsat, "laser should reach far side with no balls"

def test_absorption():
    lasers = [(1,0,East)]
    s, balls, active = make_solver(grid_size=4, ball_count=1, laser_entries=lasers)
    s.add(balls[1][2])
    s.add(active[0][1][0][East])
    s.add(active[0][1][3][East])
    assert s.check() == unsat, "laser should be absorbed before reaching far side"

def test_no_absorption_without_ball():
    lasers = [(1,0,East)]
    s, balls, active = make_solver(grid_size=4, ball_count=0, laser_entries=lasers)
    s.add(active[0][1][0][East])
    assert s.check() == sat
    m = s.model()
    assert is_true(m.eval(active[0][1][2][East])), "laser should pass through freely"


def test_reflection_right():
    # Ball at front-left (row+1, col+1) when going East should deflect the laser North
    # Laser enters East at (2,0), ball at (3,1)
    # Should deflect to North at (2,0), ending up going North from there
    lasers = [(2,0,East)]
    s, balls, active = make_solver(grid_size=4, ball_count=1, laser_entries=lasers)
    s.add(balls[3][1])
    s.add(active[0][2][0][East])
    assert s.check() == sat
    m = s.model()
    assert is_true(m.eval(active[0][2][0][North])), "laser should deflect to North"
    assert not is_true(m.eval(active[0][2][1][East])), "laser should not continue East"

def test_reflection_left():
    # Ball at front-right (row-1, col+1) when going East should deflect the laser South
    # Laser enters East at (2,0), ball at (1,1)
    lasers = [(2,0,East)]
    s, balls, active = make_solver(grid_size=4, ball_count=1, laser_entries=lasers)
    s.add(balls[1][1])
    s.add(active[0][2][0][East])
    assert s.check() == sat
    m = s.model()
    assert is_true(m.eval(active[0][2][0][South])), "laser should deflect to South"
    assert not is_true(m.eval(active[0][2][1][East])), "laser should not continue East"

def test_reflection_back():
    # Balls on both diagonals should reflect laser straight back
    # Laser enters East at (2,0), balls at (1,1) and (3,1)
    lasers = [(2,0,East)]
    s, balls, active = make_solver(grid_size=4, ball_count=2, laser_entries=lasers)
    s.add(balls[1][1])
    s.add(balls[3][1])
    s.add(active[0][2][0][East])
    assert s.check() == sat
    m = s.model()
    assert is_true(m.eval(active[0][2][0][West])), "laser should reflect back West"
    assert not is_true(m.eval(active[0][2][1][East])), "laser should not enter the grid"

def test_double_deflection():
    # Laser deflects North, then deflects again due to another ball
    # Laser enters East at (2,0), ball at (3,1) deflects it North
    # Ball at (1,1) should then deflect it East again (front-right when going North)
    lasers = [(2,0,East)]
    s, balls, active = make_solver(grid_size=4, ball_count=2, laser_entries=lasers)
    s.add(balls[3][1])
    s.add(balls[0][1])
    s.add(active[0][2][0][East])
    assert s.check() == sat
    m = s.model()
    assert is_true(m.eval(active[0][2][0][East])), "Laser comes in going eastwards"
    assert is_true(m.eval(active[0][2][0][North])), "first deflection north"
    assert is_true(m.eval(active[0][1][0][North])), "goes north"
    assert is_true(m.eval(active[0][1][0][West])), "second deflection should go westwards"

def test_two_lasers_no_interference():
    # Laser 0: enters East at (2,0), ball at (3,1) deflects it North (90 degrees)
    # Laser 1: enters East at (0,0), balls at (1,1) and (-1,1) -- wait, need valid positions
    # Laser 1: enters East at (1,0), balls at (0,1) and (2,1) deflects it back West (180 degrees)
    lasers = [(2,0,East), (0,0, East)]
    s, balls, active = make_solver(grid_size=4, ball_count=3, laser_entries=lasers)
    s.add(balls[3][1])  # deflects laser 0 North
    s.add(balls[1][1])  # deflects laser 1 back 

    # laser 0 entry
    s.add(active[1][0][0][East])
    # laser 1 entry
    s.add(active[0][2][0][East])

    assert s.check() == sat
    m = s.model()

    # laser 0 should be reflected back
    assert is_true(m.eval(active[0][2][0][East]))
    assert is_true(m.eval(active[0][2][0][West]))
    # laser 1 should be deflected north
    assert is_true(m.eval(active[1][0][0][East]))
    assert is_true(m.eval(active[1][0][0][North]))

def test_special_case_ball_on_edge():
    lasers = [(2,0,East)]
    s, balls, active = make_solver(grid_size=4, ball_count=2, laser_entries=lasers)
    s.add(balls[1][0])
    s.add(active[0][2][0][East])
    assert s.check() == sat
    m = s.model()
    assert is_true(m.eval(active[0][2][0][East])), "Laser comes in going eastwards"
    assert is_true(m.eval(active[0][2][0][West])), "gets deflected out immediately"
