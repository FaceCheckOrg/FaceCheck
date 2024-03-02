import tkinter as tk
from tkinter import Label, Button, Entry, messagebox
from PIL import Image, ImageTk
import cv2
import torch
from facenet_pytorch import MTCNN, InceptionResnetV1
import os
import sys
import threading  
import time
from database import combine_pt_files,download_file_combine
from database import retrieve_encodings_from_class,retrieve_class_embedding,retrieve_encodings_from_class,update_class_encoding,download_pt_file_student
from database import get_doc
from recognition import setup_device, load_models, prepare_data, recognize_faces, update_attendance
from firebase_admin import firestore, credentials, initialize_app
from pathlib import Path
import firebase_admin
from datetime import datetime, timedelta
import numpy as np


# Only initialize the app if it hasn't been initialized already
if not firebase_admin._apps:
    cred_path = 'db_credentials.json'  # Ensure the credential file path is correct
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {'storageBucket': 'facecheck-93450.appspot.com'})

db = firestore.client()
# Function to handle resource paths (for PyInstaller)
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def class_section_validation(class_section):
    
    doc = get_doc("class_doc")
    class_list = list(doc['classes'].keys())
    if class_section in class_list:
        return True, doc['classes'][class_section]
    return False, None

class_section_validation('CSC_4996_001')

def time_validation(class_info):
    now = datetime.now()
    week_day = now.strftime("%A")
    if week_day in class_info['schedule']:  # This line is corrected
        class_start_new = class_info['schedule'][week_day][0].replace('.', ':')
        class_end_new = class_info['schedule'][week_day][1].replace('.', ':')

        class_start_time = datetime.strptime(class_start_new, '%H:%M')
        class_end_time = datetime.strptime(class_end_new, '%H:%M')

        class_start_time = now.replace(hour=class_start_time.hour, minute=class_start_time.minute, second=0, microsecond=0)
        class_end_time = now.replace(hour=class_end_time.hour, minute=class_end_time.minute, second=0, microsecond=0)

        if class_start_time - timedelta(minutes=15) <= now <= class_end_time:
            return True
    return False



def attempt_start_attendance():
    class_section = class_section_entry.get().upper()
    exists, class_data = class_section_validation(class_section)
    
    if not exists:
        messagebox.showerror("Error", "Class section does not exist. Please enter a valid one.")
        return
    if retrieve_class_embedding(class_section) != "NO ENCODING":
        download_file_combine(retrieve_class_embedding(class_section), f'{class_section}.pt')
    else:
        combine_pt_files(class_section)

    threading.Thread(target=start_attendance, args=(class_section,)).start()
def start_attendance(class_section):
    def attendance_process():
        device = setup_device()
        mtcnn, resnet = load_models(device)
        
        embedding_list, name_list = torch.load('hi4718.pt', map_location=device)
        print(embedding_list)
        print(name_list)
        
        cam = cv2.VideoCapture(0)
        while True:
            ret, frame = cam.read()
            if not ret:
                print("Failed to grab frame, try again")
                continue

            recognized_names = recognize_faces(frame, device, mtcnn, resnet, embedding_list, name_list)
            if recognized_names:
                print(f"Recognized {len(recognized_names)} faces: {', '.join(recognized_names)}")
                update_attendance(recognized_names, class_section)  # Removed .get() as class_section is already a string
            else:
                print("No recognized people in the frame.")

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            time.sleep(10) 

        cam.release()
        cv2.destroyAllWindows()

    threading.Thread(target=attendance_process).start()


# GUI setup
root = tk.Tk()
root.title("Enrollment and Attendance App")
root.geometry("800x600")

my_image = Image.open(resource_path("FaceCheckLogo.png"))
photo = ImageTk.PhotoImage(my_image)

image_label = Label(root, image=photo)
image_label.pack(pady=20)

class_section_label = Label(root, text="Enter Class Section:", font=("Helvetica", 12))
class_section_label.pack()

class_section_entry = Entry(root, font=("Helvetica", 12))
class_section_entry.pack()

attendance_button = Button(root, text="Start Attendance", font=("Helvetica", 16), command=attempt_start_attendance)
attendance_button.pack(pady=20)

root.mainloop()