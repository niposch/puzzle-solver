from z3 import *


grid = [
    [5, 3, 0, 0, 7, 0, 0, 0, 0],
    [6, 0, 0, 1, 9, 5, 0, 0, 0],
    [0, 9, 8, 0, 0, 0, 0, 6, 0],
    [8, 0, 0, 0, 6, 0, 0, 0, 3],
    [4, 0, 0, 8, 0, 3, 0, 0, 1],
    [7, 0, 0, 0, 2, 0, 0, 0, 6],
    [0, 6, 0, 0, 0, 0, 2, 8, 0],
    [0, 0, 0, 4, 1, 9, 0, 0, 5],
    [0, 0, 0, 0, 8, 0, 0, 7, 9],
]

def main():
    s = Solver()
    cells = [[Int(f'cell_{r}_{c}') for c in range(9)] for r in range(9)]

    for i in range(9):
        for j in range(9):
            s.add(cells[i][j] >= 1, cells[i][j] <= 9)
    
    # rows distinct
    for i in range(9):
        s.add(Distinct(cells[i]))

    
    # rows
    for i in range(9):
        s.add(Distinct([cells[j][i] for j in range(9) ]))

    # cols
    for i in range(9):
        for j in range(9):
            if grid[i][j] != 0:
                s.add(cells[i][j] == grid[i][j])

    # boxes
    for box_n in range(3):
        for box_m in range(3):
            box_cells = []
            for i in range(3):
                for j in range(3):
                    box_cells.append(cells[box_n * 3 + i][box_m * 3 + j])
                
            s.add(Distinct(box_cells))
    

    if s.check() == sat:
        m = s.model()
        print(("+" + "-" * 5) * 3 + "+")
        for i in range(9):
            print("|", end="")
            for j in range(9):
                print(m[cells[i][j]], end=" " if j % 3 != 2 else "|")
            print()
            if i % 3 == 2:
                print(("+" + "-" * 5) * 3 + "+")
    else:
        print("unsat")


if __name__ == "__main__":
    main()
