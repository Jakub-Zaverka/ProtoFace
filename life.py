def create_space(width,height):
    '''Vytvoří matici [Y][X]'''
    matrix = []
    for _ in range(height):
        row = []
        for _ in range(width):
            row.append(0)
        matrix.append(row)
    return matrix

#Nefunguje
def print_matrix(matrix):
    print("-------------------------------------------------------------")
    for row in matrix:
        row_str = "| "
        for element in row:
            row_str += str(row[element])+" | "
        print(row_str)
    print("-------------------------------------------------------------")

# def _edge(cord,max):
#     if cord+1 >= max:
#         return True
#     if cord-1 < 0:
#         return True
#     return False

def _check_boundary(x_cor, y_cor,width,height):
    if x_cor >= width:
        return False
    if y_cor >= height:
        return False
    if x_cor < 0:
        return False
    if y_cor < 0:
        return False
    return True

def update_matrix(matrix):
    width = len(matrix[0])
    height = len(matrix)
    #print(f"{width}x{height}")

    next_generation = create_space(width,height)
    #print(next_generation[0][5])

    for x_cor in range(width):
        for y_cor in range(height):
            live = 0
            # if game_space[x_cor][y_cor] == 1:
            #     live +=1
            #print(f"X:{x_cor} Y:{y_cor}")
            # print(matrix[y_cor][x_cor+1])
            # print(matrix[y_cor-1][x_cor+1])
            # print(matrix[y_cor+1][x_cor+1])
            # print(matrix[y_cor][x_cor-1])
            # print(_edge(x_cor,width))

            # print(f"{_check_boundary(x_cor+1,y_cor,width,height)} {matrix[y_cor][x_cor+1]}{matrix[y_cor][x_cor+1] == 1}")
            # print(f"{_check_boundary(x_cor+1,y_cor+1,width,height)} {matrix[y_cor+1][x_cor+1]}{matrix[y_cor+1][x_cor+1] == 1}")
            pass
            if _check_boundary(x_cor+1,y_cor,width,height) and matrix[y_cor][x_cor+1] == 1:
                #print("here")
                live +=1
            if _check_boundary(x_cor+1,y_cor+1,width,height) and matrix[y_cor+1][x_cor+1] == 1:
                #print("here")
                live +=1
            if _check_boundary(x_cor,y_cor+1,width,height) and matrix[y_cor+1][x_cor] == 1:
                #print("here")
                live +=1
            if _check_boundary(x_cor-1,y_cor,width,height) and matrix[y_cor][x_cor-1] == 1:
                #print("here")
                live +=1
            if _check_boundary(x_cor-1,y_cor-1,width,height) and matrix[y_cor-1][x_cor-1] == 1:
                #print("here")
                live +=1
            if _check_boundary(x_cor,y_cor-1,width,height) and matrix[y_cor-1][x_cor] == 1:
                #print("here")
                live +=1
            if _check_boundary(x_cor+1,y_cor-1,width,height) and matrix[y_cor-1][x_cor+1] == 1:
                #print("here")
                live +=1
            if _check_boundary(x_cor-1,y_cor+1,width,height) and matrix[y_cor+1][x_cor-1] == 1:
                #print("here")
                live +=1
            #print(f"{x_cor}x{y_cor} Live {live}")

            if live <2 and matrix[y_cor][x_cor] == 1:
                next_generation[y_cor][x_cor] = 0
                #bitmap[x_cor, y_cor] = 0
            elif live in [2,3] and matrix[y_cor][x_cor] == 1:
                next_generation[y_cor][x_cor] = 1
                #bitmap[x_cor, y_cor] = game_space[x_cor][y_cor]
            elif live > 3 and matrix[y_cor][x_cor] == 1:
                next_generation[y_cor][x_cor] = 0
                #bitmap[x_cor, y_cor] = 0
            elif live == 3 and matrix[y_cor][x_cor] == 0:
                next_generation[y_cor][x_cor] = 1
                pass
                #bitmap[x_cor, y_cor] = 1
            #print(live)
    #print("updated")
    return next_generation


