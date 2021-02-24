from numpy import array, int16

TEMPLATES_DIR = 'templates/{}.ui'
LOGO_PATH = 'data/logo.ico'
WINDOW_SIZE = (1920, 1080)
WORKSPACE_SIZE = (1366, 768)

MARGIN_TOP = 26
MARGIN = 6

# CAMERA


# ANIMATION
EMPTY_PIXEL = array([255, 255, 255, 255], dtype=int16)

TICK_RATE = 60
INTERVAL = int(1 / 60 * 1000 // 1)
DELAYS_SUB_AMOUNT = 0.25
DELAYS_ADD_AMOUNT = 0.25
