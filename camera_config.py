import queue

# Файл со статическими данными

RTSP_URL = 'rtsp://username:password@192.168.100.152:554/live/av0'

onvif_ip = '192.168.100.152'
onvif_port = 2000  # Replace with your camera's ONVIF port
onvif_user = 'admin'
onvif_pass = 'admin'

frame_skip = 10


# Каллибровочные данные
fov_horizontal = 65  # Горизонтальный угол обзора камеры
fov_vertical = 45  # Вертикальный угол обзора камеры

# Пороговые значения для смещения (в пикселях)
min_pan_threshold = 200  # минимальное смещение для поворота по горизонтали
min_tilt_threshold = 60


# Скорость движения камеры (от -1.0 до 1.0)
pan_speed = 0.40  # скорость движения по горизонтали
tilt_speed = 0.15  # скорость движения по вертикали

center_threshold_x = 70  # Погрешность по горизонтали
center_threshold_y = 70  # Погрешность по вертикали

frame_count = 0

# Очередь для хранения кадров
frame_queue = queue.Queue(maxsize=10)
