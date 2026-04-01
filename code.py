import socketpool
import wifi
import os
import board
import neopixel
import time
#Display imports
import displayio
import framebufferio
import rgbmatrix
import adafruit_imageload
import random

import life



from adafruit_httpserver import Request, FileResponse, Server, GET, POST


#WIFI stuff
wifi.radio.hostname="Brain"

#WIFI connect stuff
WIFI_SSID = os.getenv("HOME_WIFI_SSID")
WIFI_PASSWORD = os.getenv("HOME_WIFI_PASSWORD")


# print(f"Connecting to {WIFI_SSID}...")
# wifi.radio.connect(ssid=WIFI_SSID, password=WIFI_PASSWORD)
# print(f"Connected to {WIFI_SSID}")

#WIFI AP stuff
MY_WIFI_SSID = os.getenv("MY_WIFI_SSID")
MY_WIFI_PASSWORD = os.getenv("MY_WIFI_PASSWORD")

print(f"Starting AP {MY_WIFI_SSID}, Password: {MY_WIFI_PASSWORD}...")
wifi.radio.start_ap(ssid=MY_WIFI_SSID, password=MY_WIFI_PASSWORD)
print(f"Started {MY_WIFI_SSID}")


pool = socketpool.SocketPool(wifi.radio)

neopixel_led =  neopixel.NeoPixel(board.NEOPIXEL, 1)


#Server stuff
server = Server(pool, "/static", debug=True)

@server.route("/",GET)
def base(request: Request):
    return FileResponse(request,"index.html")

@server.route("/api", POST)
def api(request: Request):
    print(request.body)

@server.route("/api/change_color", POST)
def change_color(request: Request):
    data = request.json()
    print(data)
    neopixel_led.fill((int(data["r"]),int(data["g"]),int(data["b"])))
    #neopixel_led.brightness = int(data["brightness"])

@server.route("/api/checkboxes", POST)
def checkboxes(request: Request):
    data = request.json()
    # print(data)


    for item in data:
        if item["status"] == 1:
            bitmap[item["x"], item["y"]] = 1
        else:
            bitmap[item["x"], item["y"]] = 0

@server.route("/caramel", POST)
def caramel(request: Request):
    colors = [
        {"r": 255, "g": 0, "b": 0},
        {"r": 255, "g": 128, "b": 0},
        {"r": 255, "g": 255, "b": 0},
        {"r": 0, "g": 255, "b": 0},
        {"r": 0, "g": 255, "b": 255},
        {"r": 0, "g": 0, "b": 255},
        {"r": 128, "g": 0, "b": 255},
        {"r": 255, "g": 0, "b": 255}
    ]
    while True:
        for data in colors:
            neopixel_led.fill((int(data["r"]),int(data["g"]),int(data["b"])))
            time.sleep(0.3)

@server.route("/conway", [POST,GET])
def conway(request: Request):
    if request.method == GET:
        global start_life
        start_life = True
        return FileResponse(request,"conway.html")
    if request.method == POST:
        data = request.json()
        if data != []:
            #print(len(data))
            #print(data)
            for item in data:
                if item["status"] == 1:
                    game_space[item["y"]][item["x"]] = 1
                else:
                    game_space[item["y"]][item["x"]] = 0
            data = []



#Not really working
#Přepsat jak funguje endpoint, jinak life funguje
# @server.route("/conway", [POST,GET])
# def conway(request: Request):
#     #while True:
#         server.poll()
#         #create game area
#         if "game_space" not in locals():
#             width = 63
#             height = 31
#             # game_space = [[0 for x in range(height)] for y in range(width)]
#             # for _ in range (64):
#             #     rand_x = random.randint(20,40)
#             #     rand_y = random.randint(10,20)
#             #     game_space[rand_x][rand_y]=1
#             #     bitmap[rand_x, rand_y] = 1
#             game_space = life.create_space(width,height)
#             game_space[0][1]=1
#             game_space[1][1]=1
#             game_space[2][1]=1
        
#         game_space = life.update_matrix(game_space)

#         for x_cor in range(width):
#             for y_cor in range(height):
#                 bitmap[x_cor,y_cor] = game_space[y_cor][x_cor]

#         if request.method == GET:
#             return FileResponse(request,"conway.html")
        
#         if request.method == POST:
#             data = request.json()
#             if data != []:
#                 #print(data)
#                 for item in data:
#                     if item["status"] == 1:
#                         game_space[item["x"]][item["y"]] = 1
#                         bitmap[item["x"], item["y"]] = 1
#                     else:
#                         print(f"{item["x"]} {item["y"]}")
#                         game_space[item["x"]][item["y"]] = game_space[item["x"]][item["y"]]
#                         bitmap[item["x"], item["y"]] = game_space[item["x"]][item["y"]]
#                 data = []
#         while True:
#             game_space = life.update_matrix(game_space)
#             for x_cor in range(width):
#                 for y_cor in range(height):
#                     bitmap[x_cor,y_cor] = game_space[y_cor][x_cor]

        # print(game_space)

        # time.sleep(1)

        # def edge(cord,param):
        #     return cord+1 >= param or cord-1 <= 0

        # game_space = life.update_matrix(game_space)
        # life.print_matrix(game_space)
        #print(game_space)
    # while True:
        # for x_cor in range(width):
        #     for y_cor in range(height):
        #         live = 0
        #         # if game_space[x_cor][y_cor] == 1:
        #         #     live +=1
        #         #print(f"X:{x_cor} Y:{y_cor}")
        #         if not edge(x_cor,width) and game_space[x_cor+1][y_cor] == 1:
        #             live +=1
        #         if not edge(x_cor,width) and not edge(y_cor,height) and game_space[x_cor+1][y_cor+1] == 1:
        #             live +=1
        #         if not edge(y_cor,height) and game_space[x_cor][y_cor+1] == 1:
        #             live +=1
        #         if not edge(y_cor,height) and game_space[x_cor-1][y_cor] == 1:
        #             live +=1
        #         if not edge(x_cor,width) and not edge(y_cor,height) and game_space[x_cor-1][y_cor-1] == 1:
        #             live +=1
        #         if not edge(y_cor,height) and game_space[x_cor][y_cor-1] == 1:
        #             live +=1
        #         if not edge(x_cor,width) and not edge(y_cor,height) and game_space[x_cor+1][y_cor-1] == 1:
        #             live +=1
        #         if not edge(x_cor,width) and not edge(y_cor,height) and game_space[x_cor-1][y_cor+1] == 1:
        #             live +=1

        #         if live <2:
        #             game_space[x_cor][y_cor] = 0
        #             #bitmap[x_cor, y_cor] = 0
        #         elif live in [2,3]:
        #             game_space[x_cor][y_cor] = game_space[x_cor][y_cor]
        #             #bitmap[x_cor, y_cor] = game_space[x_cor][y_cor]
        #         elif live > 3:
        #             game_space[x_cor][y_cor] = 0
        #             #bitmap[x_cor, y_cor] = 0
        #         elif live == 3:
        #             game_space[x_cor][y_cor] = 1
        #             #bitmap[x_cor, y_cor] = 1
        #         time.sleep(0.0005)
        # for x_cor in range(width):
        #     for y_cor in range(height):
        #         bitmap[x_cor,y_cor] = game_space[x_cor][y_cor]





#One is for AP and one for normal, replaced by server.start and server.poll in mainloop
#server.serve_forever(str(wifi.radio.ipv4_address))
#server.serve_forever(str(wifi.radio.ipv4_address_ap))

#Display stuff
displayio.release_displays()
matrix = rgbmatrix.RGBMatrix(
    width=64,
    height=32,
    bit_depth=3,
    rgb_pins=[
        board.MTX_R1,
        board.MTX_B1, #SWAP B a G kanály
        board.MTX_G1,
        board.MTX_R2,
        board.MTX_B2, #SWAP B a G kanály
        board.MTX_G2,
    ],
    addr_pins=[board.MTX_ADDRA, board.MTX_ADDRB, board.MTX_ADDRC, board.MTX_ADDRD],
    clock_pin=board.MTX_CLK,
    latch_pin=board.MTX_LAT,
    output_enable_pin=board.MTX_OE,
)

display = framebufferio.FramebufferDisplay(matrix)
#display.rotation=90
# Create a bitmap with two colors
bitmap = displayio.Bitmap(display.width, display.height, 2)

# Create a two color palette
palette = displayio.Palette(2)
palette[0] = 0x000000
palette[1] = 0xEFDC1D

# Create a TileGrid using the Bitmap and Palette
tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)


# Načtení bitmapy a palety z BMP - Protogen
bitmap2, palette2 = adafruit_imageload.load(
    "images/eye.bmp",
    bitmap=displayio.Bitmap,
    palette=displayio.Palette
)
bitmap3, palette3 = adafruit_imageload.load(
    "images/nose.bmp",
    bitmap=displayio.Bitmap,
    palette=displayio.Palette
)
bitmap4,palette4 = adafruit_imageload.load(
    "images/mouth.bmp",
    bitmap=displayio.Bitmap,
    palette=displayio.Palette
)
bitmap5,palette5 = adafruit_imageload.load(
    "images/blink.bmp",
    bitmap=displayio.Bitmap,
    palette=displayio.Palette
)
palette2.make_transparent(0)
tile_grid2 = displayio.TileGrid(bitmap2, pixel_shader=palette2)
tile_grid3 = displayio.TileGrid(bitmap3, pixel_shader=palette2)
tile_grid4 = displayio.TileGrid(bitmap4, pixel_shader=palette2)
tile_grid5 = displayio.TileGrid(bitmap5, pixel_shader=palette2)
group_test1 = displayio.Group()
group_test1.x = 0
group_test1.append(tile_grid2)
group_test1.append(tile_grid3)
group_test1.append(tile_grid4)
#display.root_group = group_test1

# Create a Group
group = displayio.Group()


# Add the TileGrid to the Group
group.append(tile_grid)




# Add the Group to the Display
display.root_group = group



#Mainloop
server.start(str(wifi.radio.ipv4_address_ap))
server.debug=True


debug = True
start_life = False
while True:
    server.poll()

    # bitmap[30, 15] = 1
    # time.sleep(1)
    # bitmap[30, 15] = 0
    # time.sleep(1)

    if start_life or debug:
        if "game_space" not in locals():
            game_space = life.create_space(64,32)
            for x_cor in range(64):
                for y_cor in range(32):
                    game_space[y_cor][x_cor] = random.randint(0,1)
        game_space = life.update_matrix(game_space)
        for x_cor in range(64):
            for y_cor in range(32):
                bitmap[x_cor,y_cor] = game_space[y_cor][x_cor]    



    #Protogen
    # group_test1.remove(tile_grid2)
    # group_test1.append(tile_grid5)
    # group_test1.y = 0
    # time.sleep(1)
    # group_test1.remove(tile_grid5)
    # group_test1.append(tile_grid2)
    # time.sleep(1)
    # group_test1.remove(tile_grid2)
    # group_test1.append(tile_grid5)
    # group_test1.y = 3
    # time.sleep(1)
    # group_test1.remove(tile_grid5)
    # group_test1.append(tile_grid2)
    # time.sleep(1)

    





