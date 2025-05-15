import streamlit as st
from streamlit_sortables import sort_items
import os
import uuid
import cv2
from PIL import Image
import tempfile

st.set_page_config(page_title="Product Order Selector", layout="centered")
st.title("🪄 Select and Reorder Product Scenes")

st.markdown("Upload your product video files and arrange them in the order you'd like them to appear in your final edit.")

uploaded_videos = st.file_uploader("Upload Product Video Clips", type=["mp4", "mov"], accept_multiple_files=True)

if uploaded_videos:
    st.subheader("Step 1: Choose Product Order")
    tmp_dir = tempfile.mkdtemp()
    thumb_map = {}

    for i, video in enumerate(uploaded_videos):
        # Save video file temporarily
        filename = f"video_{i}.mp4"
        video_path = os.path.join(tmp_dir, filename)
        with open(video_path, "wb") as f:
            f.write(video.read())

        # Extract first frame as thumbnail
        cap = cv2.VideoCapture(video_path)
        success, frame = cap.read()
        thumb_path = os.path.join(tmp_dir, f"thumb_{i}.jpg")
        if success:
            cv2.imwrite(thumb_path, frame)
            thumb_map[f"Video {i+1}"] = (thumb_path, video_path)
        cap.release()

    # Display draggable items with thumbnails
    st.write("👉 Drag and drop to rearrange:")
    sorted_labels = sort_items(list(thumb_map.keys()), direction="horizontal", label_htmls=[
        f"<img src='data:image/jpeg;base64,{Image.open(thumb_map[label][0]).resize((160, 90)).tobytes().hex()}' width='160'/>"
        for label in thumb_map.keys()
    ])

    st.subheader("Your Custom Order:")
    for label in sorted_labels:
        st.markdown(f"- {label}")
