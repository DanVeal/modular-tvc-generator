import streamlit as st
import os
import uuid
import subprocess
from itertools import product
from zipfile import ZipFile

st.set_page_config(page_title="Modular TVC Generator", layout="centered")
st.title("🎞️ Modular Commercial Generator")

st.markdown("Upload interchangeable intro, product, and outro video files. We'll generate all possible combinations.")

st.header("📥 Upload Your Video Assets")

intros = st.file_uploader("Upload Intro Videos", type=["mp4", "mov"], accept_multiple_files=True)
products = st.file_uploader("Upload Product Videos", type=["mp4", "mov"], accept_multiple_files=True)
outros = st.file_uploader("Upload Outro Videos", type=["mp4", "mov"], accept_multiple_files=True)

bg_music = st.file_uploader("Optional: Background Music (mp3)", type=["mp3"])

if st.button("🎬 Generate Commercial Variations"):
    if not intros or not products or not outros:
        st.error("Please upload at least one file for each section (intro, product, outro).")
        st.stop()

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

    music_path = None
    if bg_music:
        music_path = os.path.join(job_dir, "music.mp3")
        with open(music_path, "wb") as f:
            f.write(bg_music.read())

    combos = list(product(intro_paths, product_paths, outro_paths))
    output_paths = []

    st.write(f"Generating {len(combos)} combinations...")

    for i, (intro, prod, outro) in enumerate(combos):
        combo_filelist = os.path.join(job_dir, f"combo_{i}.txt")
        final_output = os.path.join(job_dir, f"tvc_{i+1}.mp4")
        with open(combo_filelist, "w") as f:
            f.write(f"file '{os.path.abspath(intro)}'\n")
            f.write(f"file '{os.path.abspath(prod)}'\n")
            f.write(f"file '{os.path.abspath(outro)}'\n")

        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", combo_filelist,
            "-c", "copy", final_output
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            st.error(f"❌ FFmpeg error while creating video {i+1}:\n{result.stderr}")
            continue

        # Add music if provided
        if music_path:
            music_output = os.path.join(job_dir, f"tvc_{i+1}_music.mp4")
            music_cmd = [
                "ffmpeg", "-y", "-i", final_output, "-i", music_path,
                "-shortest", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", music_output
            ]
            subprocess.run(music_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            output_paths.append(music_output)
        else:
            output_paths.append(final_output)

    zip_name = os.path.join(job_dir, "tvc_variations.zip")
    with ZipFile(zip_name, "w") as zipf:
        for vid in output_paths:
            if os.path.exists(vid):
                zipf.write(vid, arcname=os.path.basename(vid))
            else:
                st.warning(f"⚠️ Skipping missing file: {os.path.basename(vid)}")

    st.success(f"✅ Created {len(output_paths)} commercials.")
    with open(zip_name, "rb") as f:
        st.download_button("📦 Download All Videos (ZIP)", f, file_name="tvc_variations.zip")
