import streamlit as st
import pandas as pd
import logging
import asyncio
import httpx
import json
import os

PDF_PROCESSOR_URL = os.getenv("PDF_PROCESSOR_URL", "http://localhost:8080/pdf_processor")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


st.header("📋 Table Extraction")
table_status = st.empty()
server_status = st.empty()

async def get_tables(doc_id, max_retries=60, delay=1) -> dict:
    for attempt in range(max_retries):
        async with httpx.AsyncClient(cookies=st.session_state.httpx_cookies) as client:
            try:
                response = await client.get(f"{PDF_PROCESSOR_URL}/tables/{doc_id}")
                logger.info(f"Table extraction response status: {response.status_code}")
                try:
                    data = response.json()
                    if "detail" in data:
                        server_status.info(data["detail"])
                        logger.info(f"Info details: {data['detail']}")
                    else:
                        server_status.info("Successfully retrieved tables")
                        logger.info(f"Table extraction response: {response}")
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode JSON from response: {response.text}")
                    server_status.error("Received an invalid response from the server.")
                
                if response.status_code == 200:
                    return response.json()  # Success - return the actual data
                elif response.status_code == 202:
                    # Still processing, continue polling
                    if attempt < max_retries - 1:
                        table_status.info(f"Document still processing... ({(attempt + 1)*delay}s)")
                        if "detail" in response.json():
                            server_status.info(response.json()["detail"])
                        else:
                            if len(response.json()) > 100:
                                server_status.info(response.text[50:])
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise TimeoutError("Document processing timed out after maximum retries")
                else:
                    # Handle other HTTP errors
                    logger.error(f"HTTP error {response.status_code}: {response.text}")
                    response.raise_for_status()
                    
            except httpx.RequestError as e:
                logger.error(f"Request error on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(delay)
    
    raise TimeoutError("Max retries exceeded")

def table_json_to_df(table_json):
    """
    Convert a table's 'grid' field (list of lists of cell dicts) to a pandas DataFrame.
    """
    grid = table_json.get("data", {}).get("grid", [])
    if not grid or not isinstance(grid, list):
        return None
    
    # Extract headers (first row)
    headers = [cell.get("text", "") for cell in grid[0]]
    
    # Handle duplicate column names by adding suffixes
    seen_headers = {}
    unique_headers = []
    for header in headers:
        if header in seen_headers:
            seen_headers[header] += 1
            unique_headers.append(f"{header}_{seen_headers[header]}")
        else:
            seen_headers[header] = 0
            unique_headers.append(header)
    
    # Extract rows (remaining rows)
    rows = []
    for row in grid[1:]:
        rows.append([cell.get("text", "") for cell in row])
    
    return pd.DataFrame(rows, columns=unique_headers)

def display_tables(table_response, doc_id=None):
    """
    Display tables extracted from the processed PDF document.
    """
     # Check if we have tables in the response
    if table_response:
        table_status.success(f"Found {len(table_response)} tables in the document")
        for i, table_data in enumerate(table_response):
            with st.container():
                col1, col2 = st.columns([2, 1], border=True)
                
                with col1:
                    # Get page number and table position
                    page_num = table_data.get('prov', [{}])[0].get('page_no', 'N/A')

                    # Convert and display table data
                    df = table_json_to_df(table_data)

                    # Display table title with page info and copy button
                    if st.button(f"📋Table {i+1}", key=f"copy_icon_{doc_id}_{i+1}", help=f"Copy table {i+1} to clipboard"):
                        if df is not None:
                            df.to_clipboard(index=False)
                            st.toast("Table copied to clipboard!")


                    if df is not None:
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.warning("Could not parse table data.")
                    
                with col2:
                    # Metadata display
                    st.markdown(f"**Location:** Page {page_num}")
                    
                    # Display table structure info
                    grid_data = table_data.get('data', {}).get('grid', [])
                    num_rows = len(grid_data)
                    num_cols = len(grid_data[0]) if grid_data else 0
                    st.markdown(f"**Dimensions:** {num_rows}×{num_cols}")
                    

                    # Display header information if available
                    headers = [cell.get('text', '') for cell in grid_data[0] if cell.get('column_header', False)]
                    if headers:
                        for header in headers:
                            st.markdown(f"- {header}")
                    
    else:
        logger.info("No tables found in the document")
        st.info("No tables found in the document")

def describe_table(table_data):
    """
    Placeholder function to describe the table.
    In a real application, this could call an AI model or service to generate a description.
    """
    # Simulate a description
    return "Description for table"


if "processed_data" in st.session_state and st.session_state.processed_data:
    # Initialize session state for expander states if not exists
    if 'expander_states' not in st.session_state:
        st.session_state.expander_states = {}
    
    response_lst = list(st.session_state.processed_data.items())
    doc_names = [data['uploaded_filename'] for _, data in response_lst]
    
    # Initialize expander states for new documents
    for doc_name in doc_names:
        if doc_name not in st.session_state.expander_states:
            st.session_state.expander_states[doc_name] = True
    
    # Update multiselect based on expander states
    expanded_docs = st.multiselect(
        label="Expand documents:",
        options=doc_names,
        default=[doc for doc in doc_names if st.session_state.expander_states.get(doc, True)],
        help="Choose which documents should be expanded",
        key="expander_multiselect"
    )
    
    # Update session state based on multiselect
    for doc_name in doc_names:
        st.session_state.expander_states[doc_name] = doc_name in expanded_docs

    try:
        table_responses = []
        # Show loading message
        with st.spinner("Extracting tables from document..."):
            for doc_id, data in response_lst:
                if data['uploaded_filename'] in doc_names:
                    # Create expander and update state when it's clicked
                    expander_key = f"expander_{data['uploaded_filename']}"
                    file_lst = st.expander(
                        label=f"**{data['uploaded_filename']}**", 
                        expanded=st.session_state.expander_states.get(data['uploaded_filename'], True)
                    )
                    
                    # Update expander state and multiselect when expander is toggled
                    if not file_lst:  # expander is closed
                        st.session_state.expander_states[data['uploaded_filename']] = False
                        if data['uploaded_filename'] in expanded_docs:
                            expanded_docs.remove(data['uploaded_filename'])
                    else:  # expander is open
                        st.session_state.expander_states[data['uploaded_filename']] = True
                    
                    with file_lst:
                        st.markdown(f"**Document ID:** {doc_id}")
                        st.markdown(f"**Filename:** [{data['filename']}]({data['download_url']})") # Download link
                        logger.info(f"Extracting tables for document ID: {doc_id}")
                        table_response = asyncio.run(get_tables(doc_id=doc_id))
                        table_responses.append(table_response)
                        display_tables(table_response, doc_id=doc_id)

            
    except TimeoutError as e:
        st.error(f"Timeout error: {e}")
        st.info("The document is taking longer than expected to process. Please try again later.")
        
    except httpx.RequestError as e:
        st.error(f"Network error: {e}")
        st.info("There was a problem connecting to the server. Please check your connection and try again.")
        
    except Exception as e:
        logger.error(f"Unexpected error in table extraction: {e}")
        st.error(f"An unexpected error occurred: {e}")
        
else:
    st.info("Please upload and process a PDF first to extract tables")