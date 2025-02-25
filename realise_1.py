import logging

import cv2
import numpy as np
from onvif import ONVIFCamera
from camera_config import *
from yolo_config import *
import threading

logging.getLogger("ultralytics").setLevel(logging.ERROR)

# Подключение к камере и инициализация ONVIF
capture = cv2.VideoCapture(RTSP_URL)

try:
    onvif_camera = ONVIFCamera(onvif_ip, onvif_port, onvif_user, onvif_pass)
    media_service = onvif_camera.create_media_service()
    ptz_service = onvif_camera.create_ptz_service()
    media_profile = media_service.GetProfiles()[0]
except Exception as e:
    print(f"Ошибка подключения к камере: {e}")
    exit()

profile_token = media_profile.token
status = ptz_service.GetStatus({'ProfileToken': profile_token})

pan, tilt, zoom = 0.0, 0.0, 0.0

if not capture.isOpened():
    print("Ошибка открытия RTSP потока.")
    exit()


cv2.namedWindow('Stream с детекцией', cv2.WINDOW_NORMAL)

frame_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Центр фрейма
center_x, center_y = frame_width // 2, frame_height // 2

# Функция с отправкой запроса камере
def move_camera(ptz_service, profile_token, pan_speed, tilt_speed):
    request = ptz_service.create_type("ContinuousMove")
    request.ProfileToken = profile_token
    request.Velocity = {
        "PanTilt": {
            "x": pan_speed,
            "y": tilt_speed,
        },
        "Zoom": {
            "x": 0.0
        }
    }
    ptz_service.ContinuousMove(request)

# Функция для обработки кадров с использованием YOLO на GPU
def process_frame(frame):
    results = model(frame)[0]
    classes_names = results.names
    classes = results.boxes.cls.cpu().numpy()
    boxes = results.boxes.xyxy.cpu().numpy().astype(np.int32)
    confidences = results.boxes.conf.cpu().numpy()

    person_detected = False

    for class_id, box, conf in zip(classes, boxes, confidences):
        if conf > 0.5 and classes_names[int(class_id)] == select_object:
            person_detected = True
            class_name = classes_names[int(class_id)]
            color = colors[int(class_id) % len(colors)]
            x1, y1, x2, y2 = box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, class_name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            person_center_x = (x1 + x2) // 2
            person_center_y = (y1 + y2) // 2

            # Расчет смещения объекта относительно центра кадра
            offset_x = person_center_x - center_x
            offset_y = person_center_y - center_y

            # Проверка, находится ли объект в пределах центральной области
            if abs(offset_x) <= center_threshold_x and abs(offset_y) <= center_threshold_y:
                # Остановка камеры, если объект в центре
                move_camera(ptz_service, profile_token, 0.0, 0.0)
            else:
                # Определение направления и скорости поворота
                pan_speed_cmd = 0.0
                tilt_speed_cmd = 0.0

                if abs(offset_x) > min_pan_threshold:
                    pan_speed_cmd = pan_speed if offset_x > 0 else -pan_speed

                if abs(offset_y) > min_tilt_threshold:
                    tilt_speed_cmd = tilt_speed if offset_y > 0 else -tilt_speed

                # Движение камеры
                if pan_speed_cmd != 0.0 or tilt_speed_cmd != 0.0:
                    move_camera(ptz_service, profile_token, pan_speed_cmd, -tilt_speed_cmd)

    if not person_detected:
        move_camera(ptz_service, profile_token, 0.0, 0.0)

    return frame


# Функция для захвата кадров
def capture_frames():
    capture = cv2.VideoCapture(RTSP_URL)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 10)  # Уменьшаем размер буфера
    while True:
        ret, frame = capture.read()
        if not ret:
            print("Ошибка чтения кадра. Пропуск...")
            continue

        if not frame_queue.full():
            frame_queue.put(frame)


# Функция для обработки и отображения кадров
def process_and_display_frames():
    while True:
        if not frame_queue.empty():
            frame = frame_queue.get()
            processed_frame = process_frame(frame)
            cv2.imshow('Stream с детекцией', processed_frame)

        key = cv2.waitKey(30)
        if key == ord('q'):
            print("Выход...")
            break


# Основной поток
if __name__ == "__main__":
    # Запуск потока захвата кадров
    capture_thread = threading.Thread(target=capture_frames)
    capture_thread.daemon = True  # Поток завершится при завершении основного потока
    capture_thread.start()

    # Основной поток обрабатывает и отображает кадры
    process_and_display_frames()
    cv2.destroyAllWindows()
