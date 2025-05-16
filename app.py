import streamlit as st
import os
import subprocess
import uuid
from itertools import product
from zipfile import ZipFile
import tempfile
import cv2
import base64
from PIL import Image
from io import BytesIO
import plotly.graph_objects as go

st.set_page_config(page_title="TVC Generator", layout="centered")
st.title("🎞️ Modular TVC Builder with Equalised Product Timeline")

if "selected" not in st.session_state:
    st.session_state.selected = []
if "available" not in st.session_state:
    st.session_state.available = []

tmp_dir = tempfile.mkdtemp()

def save_and_analyse_video(uploaded_file, name_prefix):
    path = os.path.join(tmp_dir, f"{name_prefix}_{uuid.uuid4()}.mp4")
    with open(path, "wb") as out:
        out.write(uploaded_file.read())
    cap = cv2.VideoCapture(path)
    success, frame = cap.read()
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    if success and frame is not None:
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        thumb = base64.b64encode(buffered.getvalue()).decode()
        return path, thumb, round(duration, 1)
    return path, None, 0.0

def display_clip(label, duration, thumb, action_btn=None, key=None, disabled=False):
    col1, col2 = st.columns([5, 1])
    col1.markdown(f"**{label}**  \n⏱ {duration}s")
    if thumb:
        col1.image(f"data:image/jpeg;base64,{thumb}", width=160)
    if action_btn:
        col2.button(action_btn, key=key, disabled=disabled)

# Upload section
st.subheader("🗂 Upload Your Assets")
intros = st.file_uploader("Upload Intro Videos", type=["mp4", "mov"], accept_multiple_files=True)
products = st.file_uploader("Upload Product Clips", type=["mp4", "mov"], accept_multiple_files=True)
outros = st.file_uploader("Upload Outro Videos", type=["mp4", "mov"], accept_multiple_files=True)
bg_music = st.file_uploader("Optional: Background Music", type=["mp3"])

if products and not st.session_state.available and not st.session_state.selected:
    for i, file in enumerate(products):
        name = f"Product {i+1}"
        path, thumb, duration = save_and_analyse_video(file, "product")
        if i < 3:
            st.session_state.selected.append((name, path, thumb, duration))
        else:
            st.session_state.available.append((name, path, thumb, duration))

# Handle safe remove after loop
remove_index = None

st.subheader("🧩 Selected Clips (Used in Order)")
for i, (label, path, thumb, duration) in enumerate(st.session_state.selected):
    key = f"remove_{i}"
    if st.button("↩️ Remove", key=key):
        remove_index = i
    display_clip(f"#{i+1} {label}", duration, thumb)

if remove_index is not None:
    st.session_state.available.append(st.session_state.selected.pop(remove_index))
    st.experimental_rerun()

st.subheader("📦 Available Clips (Click to Use)")
for i, (label, path, thumb, duration) in enumerate(st.session_state.available):
    key = f"add_{i}"
    disabled = len(st.session_state.selected) >= 3
    if st.button("➕ Use", key=key, disabled=disabled):
        if not disabled:
            st.session_state.selected.append(st.session_state.available.pop(i))
            st.experimental_rerun()
    display_clip(label, duration, thumb)

# === EQUALISED TIMELINE CHART ===
intro_dur = 4
outro_dur = 4
product_block = 22
num_products = len(st.session_state.selected)
equal_product_dur = product_block / num_products if num_products > 0 else 0

labels = ["Intro"] + [clip[0] for clip in st.session_state.selected] + ["Outro"]
durations = [intro_dur] + [equal_product_dur] * num_products + [outro_dur]
colors = ["#4CAF50"] + ["#2196F3"] * num_products + ["#FF9800"]

fig = go.Figure()
start = 0
for i, (label, dur, color) in enumerate(zip(labels, durations, colors)):
    fig.add_trace(go.Bar(
        x=[dur],
        y=["TVC Timeline"],
        name=label,
        orientation='h',
        marker=dict(color=color),
        hovertemplate=f"{label}: {dur:.1f}\"<extra></extra>\"",
        offset=start
    ))
    start += dur

fig.update_layout(
    barmode='stack',
    height=100,
    margin=dict(l=20, r=20, t=30, b=20),
    showlegend=True,
    xaxis=dict(range=[0, 30], title="Total Duration (seconds)"),
    yaxis=dict(showticklabels=False),
)

st.markdown("### ⏱️ TVC Timeline Overview")
st.plotly_chart(fig, use_container_width=True)

# Duration feedback
actual_total = sum([clip[3] for clip in st.session_state.selected])
product_limit = 22
if actual_total <= product_limit:
    st.success(f"✅ Product slot: {round(actual_total, 1)}s total (within 22s).")
else:
    st.error(f"⚠️ Product slot exceeds 22s by {round(actual_total - product_limit, 1)}s.")

# Upload intros/outros
intro_paths = []
outro_paths = []
if intros:
    for i, f in enumerate(intros):
        path, _, _ = save_and_analyse_video(f, "intro")
        intro_paths.append(path)

if outros:
    for i, f in enumerate(outros):
        path, _, _ = save_and_analyse_video(f, "outro")
        outro_paths.append(path)

# Generate videos
if intro_paths and outro_paths and st.session_state.selected:
    st.subheader("🎬 Generate TVC Variations")
    combos = list(product(intro_paths, outro_paths))
    generate_limit = st.slider("How many variations to generate?", 1, len(combos), 3)
    if st.button("🚀 Generate Videos"):
        output_paths = []
        music_path = None
        if bg_music:
            music_path = os.path.join(tmp_dir, "music.mp3")
            with open(music_path, "wb") as m:
                m.write(bg_music.read())

        with st.spinner("Creating your commercials..."):
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

        st.success("✅ All commercials created!")
        with open(zip_name, "rb") as f:
            st.download_button("📦 Download All (ZIP)", f, file_name="tvc_variations.zip")
