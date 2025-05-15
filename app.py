import streamlit as st
from streamlit_sortables import sort_items
import os
import uuid
import cv2
from PIL import Image
import tempfile
import base64

st.set_page_config(page_title="🪄 Reorder Product Scenes", layout="centered")
st.title("🪄 Reorder Product Scenes by Thumbnail")

st.markdown("Upload your product video clips and drag them into your preferred order.")

uploaded_videos = st.file_uploader("Upload Product Video Clips", type=["mp4", "mov"], accept_multiple_files=True)

def image_to_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

if uploaded_videos:
    st.subheader("Step 1: Drag to Reorder")
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

    # Encode thumbnails as base64 for display
    label_htmls = [
        f"<img src='data:image/jpeg;base64,{image_to_base64(thumb_map[label][0])}' width='160'/>"
        for label in thumb_map.keys()
    ]

    sorted_labels = sort_items(list(thumb_map.keys()), direction="horizontal", label_htmls=label_htmls)

    st.subheader("Your Custom Product Order:")
    for label in sorted_labels:
        st.markdown(f"🔹 {label}")
§
