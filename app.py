import streamlit as st
from streamlit_sortables import sort_items
import os
import uuid
import subprocess
import cv2
import base64
from PIL import Image
from itertools import product
from zipfile import ZipFile
import tempfile

st.set_page_config(page_title="Modular TVC Generator", layout="centered")
st.title("🎞️ Modular Commercial Generator with Custom Product Order")

st.markdown("Upload your intro, product, and outro video files. Drag product thumbnails to define the playback order.")

intros = st.file_uploader("Upload Intro Videos", type=["mp4", "mov"], accept_multiple_files=True)
products = st.file_uploader("Upload Product Videos", type=["mp4", "mov"], accept_multiple_files=True)
outros = st.file_uploader("Upload Outro Videos", type=["mp4", "mov"], accept_multiple_files=True)

bg_music = st.file_uploader("Optional: Background Music (mp3)", type=["mp3"])

ready_to_generate = False
generate_limit = 0
intro_paths, product_paths, outro_paths = [], [], []
all_combos = []

tmp_dir = tempfile.mkdtemp()
ordered_product_paths = []

def save_uploaded(file_list, prefix):
    paths = []
    for i, f in enumerate(file_list):
        filename = f"{prefix}_{i}.mp4"
        path = os.path.join(tmp_dir, filename)
        with open(path, "wb") as out_file:
            out_file.write(f.read())
        paths.append(path)
    return paths

def image_to_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

if products:
    st.subheader("👉 Step 1: Drag to Reorder Product Scenes")
    thumb_map = {}
    for i, video in enumerate(products):
        filename = f"product_{i}.mp4"
        video_path = os.path.join(tmp_dir, filename)
        with open(video_path, "wb") as f:
            f.write(video.read())

        cap = cv2.VideoCapture(video_path)
        success, frame = cap.read()
        thumb_path = os.path.join(tmp_dir, f"thumb_{i}.jpg")
        if success:
            cv2.imwrite(thumb_path, frame)
            thumb_map[f"Product {i+1}"] = (thumb_path, video_path)
        cap.release()

    label_htmls = [
        f"<img src='data:image/jpeg;base64,{image_to_base64(thumb_map[label][0])}' width='160'/>"
        for label in thumb_map.keys()
    ]
    sorted_labels = sort_items(list(thumb_map.keys()), direction="horizontal", label_htmls=label_htmls)

    st.subheader("Your Product Scene Order:")
    for label in sorted_labels:
        st.markdown(f"🔹 {label}")
        ordered_product_paths.append(thumb_map[label][1])

if intros and ordered_product_paths and outros:
    st.subheader("🧠 Step 2: Choose How Many Variations to Generate")
    intro_paths = save_uploaded(intros, "intro")
    outro_paths = save_uploaded(outros, "outro")
    all_combos = list(product(intro_paths, outro_paths))
    total_available = len(all_combos)
    st.write(f"🧠 {total_available} total intro–outro pairings available.")
    generate_limit = st.slider("How many variations would you like to generate?", 1, total_available, value=min(3, total_available))
    ready_to_generate = True

if ready_to_generate and st.button("🎬 Generate Commercial Variations"):
    combos = all_combos[:generate_limit]

    music_path = None
    if bg_music:
        music_path = os.path.join(tmp_dir, "music.mp3")
        with open(music_path, "wb") as f:
            f.write(bg_music.read())

    output_paths = []
    st.write(f"Generating {len(combos)} combinations...")
    progress_bar = st.progress(0)
    total = len(combos)

    for i, (intro, outro) in enumerate(combos):
        st.write(f"🎞️ Processing variation {i+1}/{total}")
        combo_files = [intro]

        # Insert ordered product clips (trimmed to ~20s worth)
        estimated_clip_duration = 6.5
        max_product_clips = int(20 / estimated_clip_duration)
        selected_products = ordered_product_paths[:max_product_clips]
        combo_files.extend(selected_products)
        combo_files.append(outro)

        combo_filelist = os.path.join(tmp_dir, f"combo_{i}.txt")
        final_output = os.path.join(tmp_dir, f"tvc_{i+1}.mp4")

        with open(combo_filelist, "w") as f:
            for clip in combo_files:
                f.write(f"file '{clip}'\n")

        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", combo_filelist,
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", final_output
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            st.error(f"❌ FFmpeg error while creating video {i+1}:\n{result.stderr}")
            continue

        trimmed_output = os.path.join(tmp_dir, f"tvc_{i+1}_30s.mp4")
        if music_path:
            music_trim_cmd = [
                "ffmpeg", "-y", "-i", final_output, "-i", music_path,
                "-t", "30", "-shortest", "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
                trimmed_output
            ]
        else:
            music_trim_cmd = [
                "ffmpeg", "-y", "-i", final_output,
                "-t", "30", "-c:v", "libx264", "-c:a", "aac", trimmed_output
            ]

        subprocess.run(music_trim_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        output_paths.append(trimmed_output)
        progress_bar.progress((i + 1) / total)

    zip_name = os.path.join(tmp_dir, "tvc_variations.zip")
    with ZipFile(zip_name, "w") as zipf:
        for vid in output_paths:
            if os.path.exists(vid):
                zipf.write(vid, arcname=os.path.basename(vid))

    st.success(f"✅ Created {len(output_paths)} 30-second commercials.")
    with open(zip_name, "rb") as f:
        st.download_button("📦 Download All Videos (ZIP)", f, file_name="tvc_variations.zip")
