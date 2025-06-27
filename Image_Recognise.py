import streamlit as st
import requests
import json
import base64
from PIL import Image
import io
import re

# Page configuration
st.set_page_config(
    page_title="Image Recognition App",
    page_icon="📸",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #2E86AB;
        margin-bottom: 2rem;
    }
    .upload-section {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .results-section {
        background-color: #e8f4fd;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #2E86AB;
    }
    .object-card {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .confidence-badge {
        background-color: #28a745;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 8px;
        border-left: 5px solid #dc3545;
    }
</style>
""", unsafe_allow_html=True)

def encode_image_to_base64(image):
    """Convert PIL Image to base64 string"""
    # Convert to RGB if image has transparency or is in different mode
    if image.mode in ('RGBA', 'LA', 'P'):
        # Create a white background
        background = Image.new('RGB', image.size, (255, 255, 255))
        if image.mode == 'P':
            image = image.convert('RGBA')
        background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
        image = background
    elif image.mode != 'RGB':
        image = image.convert('RGB')
    
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=95)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str

def call_n8n_api(image_base64, text_query, api_url):
    """Call the N8N API with image and text query"""
    payload = {
        "image": image_base64,
        "query": text_query
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse API response: {str(e)}")
        return None

def extract_detected_objects(api_response):
    """Extract detected objects from the API response"""
    try:
        if isinstance(api_response, list) and len(api_response) > 0:
            output = api_response[0].get("output", "")
            
            # Extract JSON from the output string (it might be wrapped in markdown)
            json_match = re.search(r'```json\n(.*?)\n```', output, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                data = json.loads(json_str)
                return data.get("detected_objects", [])
            else:
                # Try parsing the output directly as JSON
                try:
                    data = json.loads(output)
                    return data.get("detected_objects", [])
                except:
                    return []
        return []
    except Exception as e:
        st.error(f"Error extracting objects: {str(e)}")
        return []

def display_detected_objects(detected_objects):
    """Display detected objects in a clean format"""
    if not detected_objects:
        st.warning("No objects detected in the image.")
        return
    
    st.markdown('<div class="results-section">', unsafe_allow_html=True)
    st.markdown("### 🔍 Detected Objects")
    
    for i, obj in enumerate(detected_objects):
        name = obj.get("name", "Unknown")
        confidence = obj.get("confidence", "N/A")
        
        st.markdown(f"""
        <div class="object-card">
            <div style="display: flex; justify-content: between; align-items: center;">
                <div style="flex-grow: 1;">
                    <strong>{name}</strong>
                </div>
                <div>
                    <span class="confidence-badge">{confidence}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def main():
    st.markdown('<h1 class="main-header">📸 Image Recognition App</h1>', unsafe_allow_html=True)
    st.markdown("Upload an image or take a photo to identify objects using AI")
    
    # Sidebar for API configuration
    st.sidebar.markdown("### ⚙️ API Configuration")
    api_url = st.sidebar.text_input(
        "N8N API Endpoint", 
        placeholder="https://your-n8n-instance.com/webhook/image-recognition",
        help="Enter your N8N webhook URL"
    )
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown('<div class="upload-section">', unsafe_allow_html=True)
        st.markdown("### 📁 Image Input")
        
        # Image input options
        input_method = st.radio(
            "Choose input method:",
            ["Upload Image", "Take Photo"],
            horizontal=True
        )
        
        image = None
        
        if input_method == "Upload Image":
            uploaded_file = st.file_uploader(
                "Choose an image file",
                type=['png', 'jpg', 'jpeg'],
                help="Supported formats: PNG, JPG, JPEG"
            )
            if uploaded_file is not None:
                image = Image.open(uploaded_file)
        
        else:  # Take Photo
            camera_image = st.camera_input("Take a photo")
            if camera_image is not None:
                image = Image.open(camera_image)
        
        # Text query input
        st.markdown("### 💬 Additional Query (Optional)")
        text_query = st.text_area(
            "Enter your question about the image:",
            placeholder="What do you see in this image?",
            height=100
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        if image is not None:
            st.markdown("### 🖼️ Selected Image")
            st.image(image, caption="Image to analyze", use_column_width=True)
            
            # Process button
            if st.button("🔍 Analyze Image", type="primary", use_container_width=True):
                if not api_url:
                    st.error("Please enter the N8N API endpoint in the sidebar.")
                else:
                    with st.spinner("Analyzing image... Please wait."):
                        # Convert image to base64
                        image_base64 = encode_image_to_base64(image)
                        
                        # Call API
                        api_response = call_n8n_api(image_base64, text_query, api_url)
                        
                        if api_response:
                            # Extract and display results
                            detected_objects = extract_detected_objects(api_response)
                            display_detected_objects(detected_objects)
                            
                            # Optional: Show raw API response in expandable section
                            with st.expander("🔧 Raw API Response (for debugging)"):
                                st.json(api_response)
        else:
            st.markdown("### 👆 Please select an image above")
            st.info("Choose to upload an image file or take a photo using your camera.")
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666; padding: 1rem;'>"
        "Image Recognition App powered by N8N API</div>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()