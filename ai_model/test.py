from facenet_pytorch import MTCNN
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import cv2
import numpy as np

# Initialize MTCNN for face detection
mtcnn = MTCNN(keep_all=True, device='cpu')

# Step 1: Load Your Trained Model
def load_model(model_path, embedding_dimension=128):
    model = models.resnet50(pretrained=False)
    model.fc = nn.Linear(model.fc.in_features, embedding_dimension)
    model.load_state_dict(torch.load(model_path, map_location='cpu'))
    model.eval()  # Set to evaluation mode
    return model

# Step 2: Preprocess Input Image and Extract Face Encoding
def get_transform():
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

def extract_face_encoding(model, image_path):
    transform = get_transform()
    image = Image.open(image_path).convert('RGB')
    image = transform(image).unsqueeze(0)  # Add batch dimension
    with torch.no_grad():
        encoding = model(image)
    return encoding

# Initialize your model
model_path = 'triplet_model_face_recognition.pth'
model = load_model(model_path)

# Load images and extract encodings for both people
people_images = {
    'Ahmed': 'dataset/data/ahmed/ahmed.jpg',
    'aafnan': 'dataset/data/afnan/afnan.jpg',
    'Mohammed': 'dataset\data\mo\mo.jpeg'


}

people_encodings = {name: extract_face_encoding(model, path) for name, path in people_images.items()}

# Start webcam feed
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Detect faces in the frame
    boxes, _ = mtcnn.detect(frame)
    if boxes is not None:
        for box in boxes:
            box = box.astype(int)
            face = frame[box[1]:box[3], box[0]:box[2]]
            face = Image.fromarray(face)
            face_transformed = get_transform()(face).unsqueeze(0)
            
            with torch.no_grad():
                current_encoding = model(face_transformed)

            closest_person = None
            smallest_distance = float('inf')
            
            for name, encoding in people_encodings.items():
                distance = torch.norm(encoding - current_encoding)
                print("Distance:", distance)  # Add this line to debug distance values

                if distance < smallest_distance:
                    smallest_distance = distance
                    closest_person = name
            
            threshold = 5  # Adjust based on your model's performance
            if smallest_distance < threshold:
                print(f"{closest_person} detected!")
                cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 3)
                cv2.putText(frame, closest_person, (box[0], box[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

    cv2.imshow('Webcam', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
