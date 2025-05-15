import streamlit as st
import os
import uuid
import subprocess
from itertools import product
from zipfile import ZipFile

st.set_page_config(page_title="Modular TVC Generator", layout="centered")
st.title("🎞️ Modular Commercial Generator")

st.markdown("Upload interchangeable intro, product, and outro video files. We'll generate a set of commercial variations.")

st.header("📥 Upload Your Video Assets")

intros = st.file_uploader("Upload Intro Videos", type=["mp4", "mov"], accept_multiple_files=True)
products = st.file_uploader("Upload Product Videos", type=["mp4", "mov"], accept_multiple_files=True)
outros = st.file_uploader("Upload Outro Videos", type=["mp4", "mov"], accept_multiple_files=True)

bg_music = st.file_uploader("Optional: Background Music (mp3)", type=["mp3"])

ready_to_generate = False
generate_limit = 0
intro_paths, product_paths, outro_paths = [], [], []
all_combos = []

if intros and products and outros:
    st.subheader("🧠 Choose How Many Variations to Generate")
    job_id = str(uuid.uuid4())
    job_dir = os.path.join("temp", job_id)
    os.makedirs(job_dir, exist_ok=True)

    def save_uploaded(file_list, prefix):
        paths = []
        for i, f in enumerate(file_list):
            filename = f"{prefix}_{i}.mp4"
            path = os.path.join(job_dir, filename)
            with open(path, "wb") as out_file:
                out_file.write(f.read())
            paths.append(path)
        return paths

    intro_paths = save_uploaded(intros, "intro")
    product_paths = save_uploaded(products, "product")
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
        music_path = os.path.join("temp", str(uuid.uuid4()) + "_music.mp3")
        with open(music_path, "wb") as f:
            f.write(bg_music.read())

    output_paths = []

    st.write(f"Generating {len(combos)} combinations...")
    progress_bar = st.progress(0)
    total = len(combos)

    for i, (intro, outro) in enumerate(combos):
        st.write(f"🎞️ Processing variation {i+1}/{total}")
        combo_files = [intro]  # Start with intro

        # Add as many product clips as possible (assuming ~6.5s each)
        estimated_clip_duration = 6.5
        max_product_clips = int(20 / estimated_clip_duration)
        selected_products = product_paths[:max_product_clips]
        combo_files.extend(selected_products)

        combo_files.append(outro)

        combo_filelist = os.path.join(job_dir, f"combo_{i}.txt")
        final_output = os.path.join(job_dir, f"tvc_{i+1}.mp4")

        with open(combo_filelist, "w") as f:
            for clip in combo_files:
                f.write(f"file '{os.path.abspath(clip)}'\n")

        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", combo_filelist,
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", final_output
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            st.error(f"❌ FFmpeg error while creating video {i+1}:
{result.stderr}")
            continue

        trimmed_output = os.path.join(job_dir, f"tvc_{i+1}_30s.mp4")

        if music_path:
            music_trim_cmd = [
                "ffmpeg", "-y", "-i", final_output, "-i", music_path,
                "-t", "30", "-shortest",
                "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
                trimmed_output
            ]
        else:
            music_trim_cmd = [
                "ffmpeg", "-y", "-i", final_output,
                "-t", "30",
                "-c:v", "libx264", "-c:a", "aac", trimmed_output
            ]

        subprocess.run(music_trim_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        output_paths.append(trimmed_output)
        progress_bar.progress((i + 1) / total)

    zip_name = os.path.join(job_dir, "tvc_variations.zip")
    with ZipFile(zip_name, "w") as zipf:
        for vid in output_paths:
            if os.path.exists(vid):
                zipf.write(vid, arcname=os.path.basename(vid))
            else:
                st.warning(f"⚠️ Skipping missing file: {os.path.basename(vid)}")

    st.success(f"✅ Created {len(output_paths)} 30-second commercials.")
    with open(zip_name, "rb") as f:
        st.download_button("📦 Download All Videos (ZIP)", f, file_name="tvc_variations.zip")
