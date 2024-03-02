import cv2
from facenet_pytorch import MTCNN
import torch

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
mtcnn = MTCNN(keep_all=True, device=device)

def detect_faces(frame):
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    faces, _ = mtcnn.detect(frame_rgb)

    if faces is not None:
        count = len(faces)
        for face in faces:
            cv2.rectangle(frame,
                          (int(face[0]), int(face[1])),
                          (int(face[2]), int(face[3])),
                          (0, 0, 0), 2)
        cv2.putText(frame, f"Number of faces detected: {count}", (130, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 255, 255), 1)
    else:
        cv2.putText(frame, "No faces detected", (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    return frame

# Function to check for external cameras
def find_external_camera():
    for index in range(10):
        camera = cv2.VideoCapture(index)
        if camera.isOpened():
            _, _ = camera.read()  # Grab a frame to check if camera is working
            if _ is not None:
                return index
            camera.release()
    return None

external_camera_index = find_external_camera()
if external_camera_index is not None:
    print(f"External camera found at index {external_camera_index}")
    camera = cv2.VideoCapture(external_camera_index)
else:
    print("External camera not found. Using default camera.")
    camera = cv2.VideoCapture(0)

camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

while True:
    ret, frame = camera.read()

    processed = detect_faces(frame)
    cv2.imshow("Face detector", processed)

    if cv2.waitKey(1) & 0xFF == ord('c'):
        break

camera.release()
cv2.destroyAllWindows()