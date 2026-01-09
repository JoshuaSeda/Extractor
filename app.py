import streamlit as st
import pandas as pd
import io
from gtts import gTTS
import base64

# 1. Page Configuration with Tape Icon 📟
st.set_page_config(
    page_title="Extractor", 
    page_icon="📟", 
    layout="wide"
)

# Helper function for AI Voice
def speak_text(text):
    tts = gTTS(text=text, lang='en')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    audio_b64 = base64.b64encode(fp.read()).decode()
    html_string = f"""
        <audio autoplay>
            <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
        </audio>
    """
    st.components.v1.html(html_string, height=0)

st.title("📟Tape Extractor")
st.info("Pwede mag-upload ng multiple file. Kung malaki yung .txt, better kung isa-isa lang.")

# 2. Multiple File Uploader
uploaded_files = st.file_uploader(
    "Choose .txt files", 
    type="txt", 
    accept_multiple_files=True
)

if uploaded_files:
    all_data = []
    processed_tape_names = [] # To store names for the AI voice
    status_container = st.empty()
    
    for uploaded_file in uploaded_files:
        tape_name = uploaded_file.name.replace(".txt", "")
        processed_tape_names.append(tape_name)
        status_container.text(f"Processing: {tape_name}...")
        
        # Track (Node Name, Type) to allow both Bkup and Arch
        seen_in_this_tape = set() 
        pending_entry = None

        try:
            for line_bytes in uploaded_file:
                line = line_bytes.decode("utf-8", errors="ignore")
                
                # Column 1: Node Name (0-16), Column 2: Type (17-25)
                node_part = line[0:16].strip()
                raw_type = line[17:25].strip().lower()

                clean_type = None
                if "bkup" in raw_type:
                    clean_type = "Backup"
                elif "arch" in raw_type:
                    clean_type = "Archive"

                if clean_type:
                    if pending_entry:
                        unique_id = (pending_entry["Node Name"], pending_entry["Type"])
                        if unique_id not in seen_in_this_tape:
                            all_data.append(pending_entry)
                            seen_in_this_tape.add(unique_id)
                    
                    name_to_store = node_part
                    waiting_for_more = False
                    
                    # Handle TSM name wrapping
                    if name_to_store.endswith("-"):
                        name_to_store = name_to_store[:-1]
                        waiting_for_more = True
                    
                    pending_entry = {
                        "Tape ID": tape_name,
                        "Node Name": name_to_store,
                        "Type": clean_type,
                        "is_wrapped": waiting_for_more
                    }

                elif pending_entry and pending_entry["is_wrapped"]:
                    if node_part and not line.startswith(" "):
                        pending_entry["Node Name"] += node_part
                        pending_entry["is_wrapped"] = False 

                if not line.strip() or line.startswith("ANS") or "Node Name" in line or "----" in line:
                    continue

            if pending_entry:
                unique_id = (pending_entry["Node Name"], pending_entry["Type"])
                if unique_id not in seen_in_this_tape:
                    all_data.append(pending_entry)
                    seen_in_this_tape.add(unique_id)

        except Exception as e:
            st.error(f"Error processing {tape_name}: {e}")

    # 3. Final Voice and Display Logic
    if all_data:
        df_final = pd.DataFrame(all_data)
        if "is_wrapped" in df_final.columns:
            df_final = df_final.drop(columns=["is_wrapped"])

        # Create the success message for multiple tapes
        tapes_string = ", ".join(processed_tape_names)
        success_voice = f"Here's the result for {tapes_string} tapes. Thank you."
        speak_text(success_voice)
        
        status_container.success(f"✅ Found {len(df_final):,} total entries.")
        st.dataframe(df_final, use_container_width=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False, sheet_name='Tape Report')
        
        st.download_button(
            label="📥 Download Excel Report",
            data=buffer.getvalue(),
            file_name="combined_tape_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        # Error Voice if no Backup/Archive data found at all
        speak_text("Error, data cannot be found.")
        st.error("No valid Backup or Archive data found in the files.")
