import streamlit as st
import pandas as pd
import io

# 1. Tetris-themed configuration
st.set_page_config(page_title="Open na", page_icon="📟", layout="wide")

st.title("Extractor")
st.info("Pwede mag-upload ng multiple file, pero kung malaki yung .txt much better isa muna i-upload.")

# 2. Multiple File Uploader
# Ensure .streamlit/config.toml exists with maxUploadSize = 20480
uploaded_files = st.file_uploader(
    "Choose .txt files", 
    type="txt", 
    accept_multiple_files=True
)

if uploaded_files:
    all_data = []
    status_container = st.empty()
    
    for uploaded_file in uploaded_files:
        tape_name = uploaded_file.name.replace(".txt", "")
        status_container.text(f"Currently processing: {tape_name}...")
        
        # Unique to THIS tape only (keeps same node name if it appears on different tapes)
        seen_in_this_tape = set()

        try:
            # Memory-efficient streaming for huge files
            for line_bytes in uploaded_file:
                line = line_bytes.decode("utf-8", errors="ignore")
                
                # STICKY FILTER: 
                # Skip continuation lines (IBM TSM paths start with spaces)
                if not line.strip() or line.startswith(" "):
                    continue
                
                # Skip TSM system headers/messages
                if line.startswith("ANS") or "Node Name" in line or "----" in line:
                    continue

                # 3. FIXED-WIDTH SLICING (The Precision Fix)
                # IBM Layout: Node Name (0-16), Type (17-25)
                # This prevents picking up 'backup' from inside a long file path
                node_name = line[0:16].strip()
                raw_type = line[17:25].strip().lower()

                # 4. Strict Type Mapping
                clean_type = None
                if "bkup" in raw_type:
                    clean_type = "Backup"
                elif "arch" in raw_type:
                    clean_type = "Archive"

                # Only add if we found a valid Backup/Archive type
                if clean_type and node_name:
                    if node_name not in seen_in_this_tape:
                        all_data.append({
                            "Tape ID": tape_name,
                            "Node Name": node_name,
                            "Type": clean_type
                        })
                        seen_in_this_tape.add(node_name)

        except Exception as e:
            st.error(f"Error processing {tape_name}: {e}")

    # 5. Results Display
    if all_data:
        df_final = pd.DataFrame(all_data)
        
        status_container.success(f"🟪 T-Spin Complete! Found {len(df_final):,} unique entries across {len(uploaded_files)} tapes.")
        
        st.subheader("Combined Data Preview")
        st.dataframe(df_final, use_container_width=True)

        # 6. Export to Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False, sheet_name='Tape Report')
        
        st.download_button(
            label="📥 Download All Tapes Excel Report",
            data=buffer.getvalue(),
            file_name="combined_tape_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("No valid Backup or Archive data found in the files.")
