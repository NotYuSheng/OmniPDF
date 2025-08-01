import streamlit as st
import logging
import pandas as pd
from io import StringIO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.write("📋 Extract Tables")

if 'tables' not in st.session_state:
    st.info("No tables found in the document.")
if "processed_data" in st.session_state and st.session_state.processed_data:
    data = st.session_state.processed_data
    tables = data.get('tables', [])
    if tables:
        for i, table_data in enumerate(tables):
            with st.container():
                st.markdown('<div class="image-container">', unsafe_allow_html=True)
                
                st.markdown(f"**Table {i+1} (Page {table_data['page']})**")
                
                # Display table as CSV
                try:
                    df = pd.read_csv(StringIO(table_data['csv']))
                    st.dataframe(df, use_container_width=True)
                    
                    # Download button for CSV
                    st.download_button(
                        label=f"📥 Download Table {i+1} (CSV)",
                        data=table_data['csv'],
                        file_name=f"table_{i+1}_page_{table_data['page']}.csv",
                        mime="text/csv"
                    )
                except Exception as e:
                    st.error(f"Error displaying table: {e}")
                    st.text(table_data['csv'])
                
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No tables found in the document")
else:
    st.info("Please upload and process a PDF first")