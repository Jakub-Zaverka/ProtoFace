import board

i2c = board.STEMMA_I2C() if hasattr(board, "STEMMA_I2C") else board.I2C()

while not i2c.try_lock():
    pass

try:
    print([hex(x) for x in i2c.scan()])
finally:
    i2c.unlock()
