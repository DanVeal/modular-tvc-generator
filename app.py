import streamlit as st
import os
import uuid
import subprocess
from itertools import product
from zipfile import ZipFile
import tempfile

st.set_page_config(page_title="TVC Generator", layout="centered")
st.title("🎞️ Modular TVC Builder — Drag & Swap Product Clips")

# Session state for selections
if "selected" not in st.session_state:
    st.session_state.selected = []
if "available" not in st.session_state:
    st.session_state.available = []

tmp_dir = tempfile.mkdtemp()

# Upload videos
intros = st.file_uploader("Upload Intro Videos", type=["mp4", "mov"], accept_multiple_files=True)
products = st.file_uploader("Upload Product Clips", type=["mp4", "mov"], accept_multiple_files=True)
outros = st.file_uploader("Upload Outro Videos", type=["mp4", "mov"], accept_multiple_files=True)
bg_music = st.file_uploader("Optional: Background Music", type=["mp3"])

# Save product files and setup
if products and not st.session_state.available and not st.session_state.selected:
    for i, file in enumerate(products):
        name = f"Product {i+1}"
        path = os.path.join(tmp_dir, f"product_{i}.mp4")
        with open(path, "wb") as f:
            f.write(file.read())
        if i < 3:
            st.session_state.selected.append((name, path))
        else:
            st.session_state.available.append((name, path))

st.subheader("🧩 Selected Clips (used in your 30s TVC)")
for i, (label, _) in enumerate(st.session_state.selected):
    col1, col2 = st.columns([4, 1])
    col1.markdown(f"🔹 {label}")
    if col2.button("↩️", key=f"remove_{i}"):
        st.session_state.available.append(st.session_state.selected.pop(i))
        st.experimental_rerun()

st.subheader("📦 Available Clips (click to use)")
for i, (label, _) in enumerate(st.session_state.available):
    col1, col2 = st.columns([4, 1])
    col1.markdown(label)
    if col2.button("➕", key=f"add_{i}"):
        if len(st.session_state.selected) < 3:
            st.session_state.selected.append(st.session_state.available.pop(i))
            st.experimental_rerun()
        else:
            st.warning("You can only select 3 clips max.")

# Intro/Outro saving
intro_paths = []
outro_paths = []
if intros:
    for i, f in enumerate(intros):
        path = os.path.join(tmp_dir, f"intro_{i}.mp4")
        with open(path, "wb") as out:
            out.write(f.read())
        intro_paths.append(path)

if outros:
    for i, f in enumerate(outros):
        path = os.path.join(tmp_dir, f"outro_{i}.mp4")
        with open(path, "wb") as out:
            out.write(f.read())
        outro_paths.append(path)

# Build button
if intro_paths and outro_paths and st.session_state.selected:
    st.subheader("🎬 Generate Variations")
    combos = list(product(intro_paths, outro_paths))
    generate_limit = st.slider("How many variations to generate?", 1, len(combos), 3)
    if st.button("Generate TVCs"):
        output_paths = []
        music_path = None
        if bg_music:
            music_path = os.path.join(tmp_dir, "music.mp3")
            with open(music_path, "wb") as m:
                m.write(bg_music.read())

        with st.spinner("Creating videos..."):
            for i, (intro, outro) in enumerate(combos[:generate_limit]):
                combo = [intro] + [p[1] for p in st.session_state.selected] + [outro]
                combo_filelist = os.path.join(tmp_dir, f"combo_{i}.txt")
                with open(combo_filelist, "w") as f:
                    for clip in combo:
                        f.write(f"file '{clip}'\n")
                output_path = os.path.join(tmp_dir, f"tvc_{i+1}.mp4")
                cmd = [
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", combo_filelist,
                    "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", output_path
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

                trimmed_output = os.path.join(tmp_dir, f"tvc_{i+1}_30s.mp4")
                if music_path:
                    music_cmd = [
                        "ffmpeg", "-y", "-i", output_path, "-i", music_path,
                        "-t", "30", "-shortest", "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
                        trimmed_output
                    ]
                else:
                    music_cmd = [
                        "ffmpeg", "-y", "-i", output_path,
                        "-t", "30", "-c:v", "libx264", "-c:a", "aac", trimmed_output
                    ]
                subprocess.run(music_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                output_paths.append(trimmed_output)

            zip_name = os.path.join(tmp_dir, "tvc_variations.zip")
            with ZipFile(zip_name, "w") as zipf:
                for vid in output_paths:
                    zipf.write(vid, arcname=os.path.basename(vid))

        st.success("✅ All videos generated!")
        with open(zip_name, "rb") as f:
            st.download_button("📦 Download All as ZIP", f, file_name="tvc_variations.zip")
