import streamlit as st
import pandas as pd
import logging
import asyncio
import httpx
import json
import os
from components.documents import document_multiselect_with_expander, DocumentExpander

PDF_PROCESSOR_URL = os.environ["PDF_PROCESSOR_URL"]
logger = logging.getLogger(__name__)
client = httpx.AsyncClient(cookies=st.session_state.httpx_cookies)

runner = asyncio.Runner()
st.header("📋 Table Extraction")


async def get_tables(doc_id: str, status_bar, max_retries=600, delay=1):
    """
    Poll the backend for table extraction results.
    """
    for attempt in range(max_retries):
        try:
            response = await client.get(f"{PDF_PROCESSOR_URL}/tables/{doc_id}")
            logger.info(f"Table extraction response status: {response.status_code}")
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                data = {}
                logger.error(f"Failed to decode JSON from response: {response.text}: {e}")

            if response.status_code == 200:
                status_bar.empty()
                return data  # Success - return the actual data
            elif response.status_code == 202:
                # Still processing, continue polling
                if attempt < max_retries - 1:
                    if status_bar:
                        reason = data.get("detail", "in progress") if data else "in progress"
                        status_bar.info(
                            f"Document still processing... ({(attempt + 1) * delay}s)"
                            f"\nReason: {reason}"
                        )
                    await asyncio.sleep(delay)
                    await asyncio.sleep(0)  # Yield to Streamlit
                    continue
                else:
                    raise TimeoutError(
                        "Document processing timed out after maximum retries"
                    )
            elif response.status_code == 450:
                # Processing failed
                error_msg = data.get("detail", "Processing failed") if data else "Processing failed"
                status_bar.error(f"Document processing failed: {error_msg}")
                logger.error(f"Document processing failed for {doc_id}: {error_msg}")
                return None
            response.raise_for_status()
        except httpx.RequestError as e:
            status_bar.error("Error Processing your file. Please try re uploading.")
            logger.error(f"Request error on attempt: {e}")
            return None
        except TimeoutError:
            logger.error(f"Document ID: {doc_id} took too long to process.")
            status_bar.error(
                "Retry limit reached. Please retry by clicking on page on left."
            )
            return None


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


def display_tables(table_response):
    """
    Display tables extracted from the processed PDF document.
    """
    # Handle the case where table_response is None (processing failed)
    if table_response is None:
        st.warning("Failed to process document for table extraction")
        return
    
    # Check if we have tables in the response
    if table_response and isinstance(table_response, list) and len(table_response) > 0:
        st.success(f"Found {len(table_response)} tables in the document")
        for i, table_data in enumerate(table_response):
            with st.container():
                col1, col2 = st.columns([2, 1], border=True)

                with col1:
                    # Get page number and table position
                    page_num = table_data.get("prov", [{}])[0].get("page_no", "N/A")

                    # Convert and display table data
                    df = table_json_to_df(table_data)

                    st.text(f"Table {i + 1}")

                    # Show dataframe
                    if df is not None:
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.warning("Could not parse table data.")

                    # Display title with page info and copy button
                    if df is not None:
                        csv_string = df.to_csv(index=False)
                        st.code(csv_string, language="csv")

                with col2:
                    # Metadata display
                    st.markdown(f"**Location:** Page {page_num}")

                    # Display table structure info
                    grid_data = table_data.get("data", {}).get("grid", [])
                    num_rows = len(grid_data)
                    num_cols = len(grid_data[0]) if grid_data else 0
                    st.markdown(f"**Dimensions:** {num_rows}×{num_cols}")

                    # Display header information if available
                    headers = [
                        cell.get("text", "")
                        for cell in grid_data[0]
                        if cell.get("column_header", False)
                    ]
                    if headers:
                        for header in headers:
                            st.markdown(f"- {header}")

    else:
        # This covers cases where table_response is an empty list or other falsy values
        logger.info("No tables found in the document")
        st.info("No tables found in the document")

async def display_table_extraction(expander: DocumentExpander):
    """Display table extraction for a single document"""
    with expander:
        # Add refresh button for each document
        col1, col2 = st.columns([3, 1])
        with col2:
            refresh_key = f"refresh_tables_{expander.doc_id}"
            retry_key = f"retry_tables_{expander.doc_id}"
            
            # Initialize retry state if not exists
            if retry_key not in st.session_state:
                st.session_state[retry_key] = False
            
            if st.button("🔄 Refresh", key=refresh_key, help="Retry table extraction for this document"):
                st.session_state[retry_key] = True
        
        with col1:
            st.markdown(f"**Document ID:** {expander.doc_id}")
        
        # Check if this document should be retried
        force_retry = st.session_state.get(retry_key, False)
        if force_retry:
            # Reset the retry flag
            st.session_state[retry_key] = False
            # Clear any cached status for this document
            expander.status.empty()
            expander.status.info("Retrying table extraction...")
        
        table_response = await get_tables(expander.doc_id, expander.status)
        # Always call display_tables - it handles both success and no-tables cases
        display_tables(table_response)


async def display_all_tables(expanders: list[DocumentExpander]):
    """Display table extraction for all documents concurrently"""
    displays = [display_table_extraction(expander) for expander in expanders]
    await asyncio.gather(*displays, return_exceptions=True)


if "processed_data" in st.session_state and st.session_state.processed_data:
    # Initialize session state for expander states if not exists
    if "expander_states" not in st.session_state:
        st.session_state.expander_states = {}

    expanders = document_multiselect_with_expander()
    runner.run(display_all_tables(expanders))

else:
    st.info("Please upload and process a PDF first to extract tables")
