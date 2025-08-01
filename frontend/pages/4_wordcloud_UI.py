import streamlit as st
import logging
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from streamlit.components.v1 import html
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_wordcloud(text_data):
    """Generate word cloud from text data"""
    wordcloud = WordCloud(
        width=800, 
        height=400, 
        background_color='white',
        colormap='viridis'
    ).generate(' '.join(text_data))
    
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    return fig


st.write("☁️ Word Cloud")
if 'metadata' not in st.session_state:
    st.info("No metadata found in the document.")
if "processed_data" in st.session_state and st.session_state.processed_data:
    # Generate word cloud from keywords
    all_keywords = st.session_state.processed_data['metadata']['keywords'] + st.session_state.processed_data['metadata']['image_keywords']
    
    if all_keywords:
        import io
        fig = generate_wordcloud(all_keywords)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches='tight')
        buf.seek(0)
        encoded = base64.b64encode(buf.read()).decode("utf-8")
        # Custom HTML for zoomable image
        html_code = f"""
        <style>
        .zoomable-img {{
            transition: transform 0.3s ease;
            cursor: zoom-in;
            max-width: 100%;
            height: auto;
        }}

        .zoomed {{
            transform: scale(2.5);
            cursor: zoom-out;
            z-index: 9999;
            position: relative;
        }}
        </style>

        <img id="zoom-img" class="zoomable-img" src="data:image/jpeg;base64,{encoded}" onclick="toggleZoom()" />

        <script>
        function toggleZoom() {{
            var img = document.getElementById("zoom-img");
            img.classList.toggle("zoomed");
        }}
        </script>
        """
        # Display the image using custom HTML
        html(html_code, height=600)
    else:
        st.info("No keywords available for word cloud generation")
else:
    st.info("Please upload and process a PDF first to generate word cloud")
