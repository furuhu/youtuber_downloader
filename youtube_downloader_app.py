# youtube_downloader_app.py

import streamlit as st
from pytube import YouTube
import os
from io import BytesIO # Needed for in-memory file handling

# --- Helper Function for Progress (using session state) ---
def progress_callback(stream, chunk, bytes_remaining):
    """Updates download progress in Streamlit session state."""
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percentage = (bytes_downloaded / total_size) * 100
    # Store percentage in session state to survive reruns
    st.session_state.download_progress = percentage

def complete_callback(stream, file_path):
    """Sets completion flag in session state."""
    st.session_state.download_complete = True
    # We don't use file_path directly here as we download to memory
    # but pytube requires the argument

# --- Main App Logic ---

st.set_page_config(page_title="YouTube Downloader", layout="centered")
st.title("🚀 YouTube Video Downloader")

# Initialize session state variables if they don't exist
if 'download_progress' not in st.session_state:
    st.session_state.download_progress = 0.0
if 'download_complete' not in st.session_state:
    st.session_state.download_complete = False
if 'video_info' not in st.session_state:
    st.session_state.video_info = None
if 'download_error' not in st.session_state:
    st.session_state.download_error = None
if 'download_data' not in st.session_state:
    st.session_state.download_data = None
if 'download_filename' not in st.session_state:
    st.session_state.download_filename = None
if 'download_mime' not in st.session_state:
    st.session_state.download_mime = None


# --- Input URL ---
url = st.text_input("Enter YouTube URL:", key="youtube_url_input")

# --- Buttons and Download Logic ---
col1, col2 = st.columns(2)

# Variable to track if download process started
download_triggered = False

with col1:
    if st.button("Download MP4 (Video)"):
        if url:
            st.session_state.download_type = "mp4"
            download_triggered = True
        else:
            st.warning("Please enter a YouTube URL.")

with col2:
    if st.button("Download MP3 (Audio)"):
        if url:
            st.session_state.download_type = "mp3"
            download_triggered = True
        else:
            st.warning("Please enter a YouTube URL.")

# --- Status Display Area ---
status_placeholder = st.empty() # Placeholder for status messages
progress_placeholder = st.empty() # Placeholder for progress bar
info_placeholder = st.empty() # Placeholder for video info
download_button_placeholder = st.empty() # Placeholder for download button

# --- Execute Download if Triggered ---
if download_triggered:
    # Reset state for new download attempt
    st.session_state.download_progress = 0.0
    st.session_state.download_complete = False
    st.session_state.video_info = None
    st.session_state.download_error = None
    st.session_state.download_data = None
    st.session_state.download_filename = None
    st.session_state.download_mime = None
    # Clear previous UI elements
    status_placeholder.empty()
    progress_placeholder.empty()
    info_placeholder.empty()
    download_button_placeholder.empty()


    try:
        with status_placeholder.container():
             with st.spinner("Fetching video info... Please wait."):
                yt = YouTube(
                    url,
                    on_progress_callback=progress_callback,
                    on_complete_callback=complete_callback
                )
                # Sanitize title for filename
                sanitized_title = "".join(c for c in yt.title if c.isalnum() or c in (' ', '.', '_', '-')).rstrip()
                st.session_state.video_info = f"**Title:** {yt.title}\n**Length:** {yt.length // 60}m {yt.length % 60}s"

        info_placeholder.markdown(st.session_state.video_info)

        stream = None
        file_extension = ""
        mime_type = ""

        if st.session_state.download_type == "mp4":
            with status_placeholder.container():
                with st.spinner("Getting MP4 stream..."):
                    stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
                    file_extension = ".mp4"
                    mime_type = "video/mp4"
                    st.session_state.download_filename = f"{sanitized_title}{file_extension}"
                    st.session_state.download_mime = mime_type

        elif st.session_state.download_type == "mp3":
            with status_placeholder.container():
                with st.spinner("Getting Audio stream..."):
                    stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
                    # Note: Saving as .mp3, actual format might be mp4/webm audio container
                    file_extension = ".mp3"
                    mime_type = "audio/mp3" # Standard mime for mp3
                    st.session_state.download_filename = f"{sanitized_title}{file_extension}"
                    st.session_state.download_mime = mime_type

        if not stream:
            st.session_state.download_error = f"No suitable {st.session_state.download_type.upper()} stream found."
            status_placeholder.error(st.session_state.download_error)
        else:
            # Download to an in-memory buffer
            buffer = BytesIO()
            with status_placeholder.container():
                 with st.spinner(f"Downloading {st.session_state.download_type.upper()}..."):
                    # Display progress bar - it updates based on session_state changes triggered by callback
                    progress_bar = progress_placeholder.progress(st.session_state.download_progress / 100.0)
                    stream.stream_to_buffer(buffer)
                    # Note: The spinner finishes when the 'with' block exits.
                    # The actual completion signal comes from the callback setting the flag.


            # Store downloaded data in session state
            buffer.seek(0) # Reset buffer position to the beginning
            st.session_state.download_data = buffer.getvalue()

            # Wait briefly for the completion callback to potentially update state if needed
            # (Sometimes helps ensure state changes propagate before the final check)
            # import time
            # time.sleep(0.5)

            # Explicitly check completion flag set by callback
            if st.session_state.download_complete:
                status_placeholder.success("Download Ready!")
                progress_placeholder.empty() # Clear progress bar on completion
            else:
                 # If callback didn't fire or finish in time (less likely with stream_to_buffer)
                 # Assume success if we have data, but maybe show a slightly different message.
                 status_placeholder.success("Processing Complete!")
                 progress_placeholder.empty()


    except Exception as e:
        st.session_state.download_error = f"An error occurred: {e}"
        status_placeholder.error(st.session_state.download_error)
        # Clear potentially leftover state
        st.session_state.download_data = None
        st.session_state.video_info = None
        progress_placeholder.empty()
        info_placeholder.empty()
        download_button_placeholder.empty()

# --- Display Download Button if data is ready ---
# This part runs on every interaction. If download data exists in state, show the button.
if st.session_state.download_data and st.session_state.download_filename:
    with download_button_placeholder.container():
        st.download_button(
            label=f"Click to Download {st.session_state.download_filename}",
            data=st.session_state.download_data,
            file_name=st.session_state.download_filename,
            mime=st.session_state.download_mime
        )
        st.info("Note: MP3 is the highest quality audio stream available, saved with an .mp3 extension (actual format might be different but usually compatible).")

# Display persistent info or errors if they exist in state
if st.session_state.video_info and not download_triggered and not st.session_state.download_data :
     info_placeholder.markdown(st.session_state.video_info) # Show info if no new download started

if st.session_state.download_error and not download_triggered:
    status_placeholder.error(st.session_state.download_error) # Show error if no new download started