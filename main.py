import cv2
import imutils
import streamlit as st
from imutils.video import VideoStream
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.models import load_model
import numpy as np

def load_mask_detection_model(model_path):
    return load_model(model_path)

def detect_and_predict_mask(frame, faceNet, maskNet):
    (h, w) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 1.0, (224, 224), (104.0, 177.0, 123.0))
    faceNet.setInput(blob)
    detections = faceNet.forward()

    faces = []
    locs = []
    preds = []

    for i in range(0, detections.shape[2]):
        confidence = detections[0, 0, i, 2]

        if confidence > 0.5:
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")
            (startX, startY) = (max(0, startX), max(0, startY))
            (endX, endY) = (min(w - 1, endX), min(h - 1, endY))

            face = frame[startY:endY, startX:endX]
            face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
            face = cv2.resize(face, (224, 224))
            face = img_to_array(face)
            face = preprocess_input(face)

            faces.append(face)
            locs.append((startX, startY, endX, endY))

    if len(faces) > 0:
        faces = np.array(faces, dtype="float32")
        preds = maskNet.predict(faces, batch_size=32)

    return (locs, preds)

def main():
    st.title("Face Mask Detection Streamlit App")

    # Load the face detection model
    prototxtPath = 'face_detector/deploy.prototxt'
    weightsPath = 'face_detector/res10_300x300_ssd_iter_140000.caffemodel'
    faceNet = cv2.dnn.readNet(prototxtPath, weightsPath)

    # Load the mask detection model
    maskNet = load_mask_detection_model("mask_detector.model")

    # Create a VideoStream object
    vs = None

    # Create start and stop buttons
    start_button = st.button("Start Video Stream")
    stop_button = st.button("Stop Video Stream")

    # Check if the start button is pressed
    if start_button:
        # Start the video stream
        vs = VideoStream(src=0).start()

    # Check if the stop button is pressed
    if stop_button:
        # Stop the video stream
        if vs is not None:
            vs.stop()

    # If the video stream is running, process frames
    if vs is not None:
        # Grab the frame from the threaded video stream and resize it
        frame = vs.read()
        frame = imutils.resize(frame, width=400)

        # Detect faces and predict mask
        (locs, preds) = detect_and_predict_mask(frame, faceNet, maskNet)

        # Loop over the detected face locations and their corresponding locations
        for (box, pred) in zip(locs, preds):
            # Unpack the bounding box and predictions
            (startX, startY, endX, endY) = box
            (mask, withoutMask) = pred

            # Determine the class label and color
            label = "Mask" if mask > withoutMask else "No Mask"
            color = (0, 255, 0) if label == "Mask" else (0, 0, 255)

            # Include the probability in the label
            label = "{}: {:.2f}%".format(label, max(mask, withoutMask) * 100)

            # Display the label and bounding box rectangle on the output frame
            cv2.putText(frame, label, (startX, startY - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)
            cv2.rectangle(frame, (startX, startY), (endX, endY), color, 2)

        # Show the output frame
        st.image(frame, channels="BGR", use_column_width=True)

if __name__ == "__main__":
    main()
