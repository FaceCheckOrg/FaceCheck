import cv2
import torch
from torch.utils.data import DataLoader
from torchvision import datasets
from facenet_pytorch import MTCNN, InceptionResnetV1
from firebase_admin import storage
import io
import firebase_admin
from firebase_admin import credentials
import torch
import torchvision.transforms as transforms

import requests
from io import BytesIO
from PIL import Image
import numpy as np

# Path to your Firebase service account JSON file
cred_path = 'db_credentials.json'

def detect_and_crop_face(image_path, device='cpu', min_face_size=20, thresholds=[0.6, 0.7, 0.7], factor=0.709):
    mtcnn = MTCNN(keep_all=True, device=device, min_face_size=min_face_size, thresholds=thresholds, factor=factor)

    # Load the image
    response = requests.get(image_path)
    if response.status_code != 200:
        # If the image cannot be downloaded, raise an error
        raise FileNotFoundError(f"The specified image_path cannot be downloaded: {image_path}")
    
    
    image_bytes = BytesIO(response.content)
    image = Image.open(image_bytes)
    
    image_rgb = image.convert('RGB')
    frame_rgb = np.array(image_rgb)
    #Face detection
    faces, _ = mtcnn.detect(frame_rgb)
    
    #if there is only one face detected, crop the face
    if faces is not None and len(faces) == 1:
        face = faces[0]
        # Get the coordinates of faces to crop
        #x1, y1, x2, y2 are the coordinates of the bounding box
        x1, y1, x2, y2 = [int(coord) for coord in face]

        # Ensure that x1 and y1 are not less than 0. If they are, set them to 0.
        x1, y1 = max(0, x1), max(0, y1)

        # Ensure that x2 does not exceed the width of the frame (frame_rgb.shape[1]) and y2 does not exceed the height of the frame (frame_rgb.shape[0]).
        # If they do, set x2 to the frame width and y2 to the frame height.
        x2, y2 = min(frame_rgb.shape[1], x2), min(frame_rgb.shape[0], y2)

        # Ensure the crop dimensions are valid
        if x2 <= x1 or y2 <= y1:
            return None  # Invalid crop dimensions
        # Crop the face from the frame
        cropped_face = frame_rgb[y1:y2, x1:x2]
        # Check if the cropped face is empty
        if cropped_face.size == 0:
            return None  # Cropped face is empty
        # Convert the cropped face from RGB to BGR
        cropped_face_bgr = cv2.cvtColor(cropped_face, cv2.COLOR_RGB2BGR)
        # Return the cropped face
        return cropped_face_bgr
    else:
        # No face detected or multiple faces detected return None
        return None

device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')



def face_encode(cropped_face, device):
    #intialize the embedding list
    embedding_list = [] 
    #Initialize the model
    resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)

    # Define transformations
    preprocess = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize(160),  # Resize the image to the size expected by the model
        transforms.ToTensor(),  # Convert the image to a PyTorch tensor
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])  # Normalize
    ])

    # Apply the transformations
    cropped_face_tensor = preprocess(cropped_face).unsqueeze(0)  # Add batch dimension

    # Get the embedding
    emb = resnet(cropped_face_tensor.to(device))
    # Append the embedding to the list of embeddings
    embedding_list.append(emb.detach())
    # Return the list of embeddings
    return embedding_list

# Save the embeddings and names to a .pt file
def make_pt_file(embedding_list, name_list):
    # Save the file to an in-memory file-like object
    file_name = f'{name_list[0]}.pt'
    buffer = io.BytesIO()
    torch.save([embedding_list, name_list], buffer)
    buffer.seek(0)

    # Get a reference to the storage service
    bucket = storage.bucket()

    # Create a new blob and upload the file's content.
    blob = bucket.blob(file_name)
    blob.upload_from_file(buffer)

    # Make the blob publicly viewable.
    blob.make_public()

    # Get the URL of the blob
    url = blob.public_url
    return url
    

