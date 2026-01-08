import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Open Na!", layout="wide")

st.title("📟 Extractor")
st.info("Pwede mag-upload ng multiple file, pero kung malaki yung .txt much better isa muna i-upload.")

# 1. Multiple File Uploader
# Remember to set your .streamlit/config.toml maxUploadSize = 20480
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
        
        
        seen_in_this_tape = set()

        try:
            # Streaming read to handle 20GB files
            for line_bytes in uploaded_file:
                line = line_bytes.decode("utf-8", errors="ignore")
                
                # Skip lines that are empty or path continuations (starting with space)
                if not line.strip() or line.startswith(" "):
                    continue
                
                # Skip TSM headers and system messages
                if line.startswith("ANS") or "Node Name" in line or "----" in line:
                    continue

                # Fixed-Width Slicing for IBM TSM Layout
                # Column 1: Node Name (0-16), Column 2: Type (17-25)
                node_name = line[0:16].strip()
                raw_type = line[17:25].strip().lower()

                # Filter and Map Type
                clean_type = None
                if "bkup" in raw_type:
                    clean_type = "Backup"
                elif "arch" in raw_type:
                    clean_type = "Archive"

                # If valid data found, add it
                if clean_type and node_name:
                    # Deduplicate only within the SAME tape
                    if node_name not in seen_in_this_tape:
                        all_data.append({
                            "Tape ID": tape_name,
                            "Node Name": node_name,
                            "Type": clean_type
                        })
                        seen_in_this_tape.add(node_name)

        except Exception as e:
            st.error(f"Error processing {tape_name}: {e}")

    # 2. Results Display & Download
    if all_data:
        df_final = pd.DataFrame(all_data)
        
        status_container.success(f"✅ Processing Complete! Found {len(df_final):,} entries across {len(uploaded_files)} tapes.")
        
        # Data Preview
        st.subheader("Combined Data Preview")
        st.dataframe(df_final, use_container_width=True)

        # 3. Export to Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # We save everything to one sheet named 'Tape Report'
            df_final.to_excel(writer, index=False, sheet_name='Tape Report')
        
        st.download_button(
            label="📥 Download All Tapes Excel Report",
            data=buffer.getvalue(),
            file_name="combined_tape_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("No valid data found in the uploaded files.")