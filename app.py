import streamlit as st
import os
import zipfile
import base64
from openai import OpenAI
from PIL import Image, UnidentifiedImageError

# Initialize OpenAI client
client = OpenAI()

# Function to encode an image to base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# Function to call the OpenAI API with an image
def call_open_ai_api(image_path):
    base64_image = encode_image(image_path)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What is in this image?"},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                        },
                    ],
                }
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

# Function to process images in a folder
def call_llm_for_images(image_folder, mock=True):
    """Call an LLM for each image in the folder and store results."""
    results = []
    image_files = [f for f in os.listdir(image_folder) if f.lower().endswith(('.jpeg', '.jpg', '.png'))]

    if not image_files:
        print("No image files found in the folder.")
        return ["No image files found."]

    # Sort images by numerical value if filenames include 'Slide'
    try:
        sorted_files = sorted(image_files, key=lambda x: int(x.split('Slide')[1].split('.')[0]) if 'Slide' in x else 0)
    except Exception as e:
        print(f"Error sorting files: {e}")
        sorted_files = image_files

    for image_file in sorted_files:
        image_path = os.path.join(image_folder, image_file)
        if mock:
            result = f"Mock response for {image_file}"
        else:
            result = call_open_ai_api(image_path)
        print(f"Processed {image_file}: {result}")
        results.append(result)

    return results

# Save content to a text file
def save_to_txt(content, file_name="output.txt"):
    with open(file_name, "w") as file:
        file.write(content)
    return file_name

# Read content from a text file
def read_file(file_path):
    try:
        with open(file_path, "r") as file:
            return file.read()
    except FileNotFoundError:
        return None

# Construct a prompt for summarization
def construct_prompt(base_content, audience_type, tone, example):
    prompt = f"""
    Original Content:
    {base_content}

    Please summarize the above content in the form of a story for {audience_type} in the tone: {tone}.
    Here is an example for the story: {example}.
    """
    return prompt

# Call the OpenAI API with a text prompt
def call_llm(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "developer", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

# Streamlit UI
st.title("PharmaLLM")


# streamlit start 
st.header("Upload Image Folder")
uploaded_folder = st.file_uploader("Upload a folder with images (zip):", type=["zip"])
if uploaded_folder:
    image_folder = os.getenv("UPLOAD_FOLDER", "./uploaded_images")
    os.makedirs(image_folder, exist_ok=True)

    # Extract the uploaded zip folder
    zip_path = f"{image_folder}/uploaded.zip"
    with open(zip_path, "wb") as f:
        f.write(uploaded_folder.getbuffer())

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(image_folder)

    st.success("Folder uploaded and extracted successfully!")


if st.button("Process Images"):
    if uploaded_folder:
        zip_file_name = uploaded_folder.name
        print('Uploaded folder name is ', zip_file_name) # Eg., ABCPharma.zip
        base_name = os.path.splitext(zip_file_name)[0]
        image_folder_updated = os.path.join(image_folder, base_name)
        #image_folder_updated = os.path.join(image_folder, zip_file_name)
        #base_name = os.path.splitext(zip_file_name)[0] # ['ABCPharma', 'zip']
        # print("------------")
        # print(len(base_name))
        # Removes the extension # ./uploaded_images/ABCPharma
        results = call_llm_for_images(image_folder_updated, mock=False)  # Set mock=True for testing without API calls
        #combined_text = "\n\n\n".join(results)
        combined_text = "\n\n\n".join([f"Slide {idx + 1}:\n{result}" for idx, result in enumerate(results)])
        

        # Debugging print
        print(f"Combined text to save: {combined_text}")

        # Ensure results are non-empty before proceeding
        if combined_text.strip():
            output_file = save_to_txt(combined_text)  # Save the results
            st.success("Images processed successfully! Results saved to output.txt.")
            st.download_button("Download Results", combined_text, file_name="output.txt", mime="text/plain")
        else:
            st.error("No content generated from images. Please check your API or input files.")
    else:
        st.warning("Please upload a folder with images first!")

# Step 3: Summarize content from `.txt` file
st.header("Summarize Content")
tone = st.text_input("Enter the desired tone (e.g., formal, casual, professional):")
audience_type = st.text_input("Enter the audience type (e.g., Business User, Pharmacist):")
example = st.text_area("Provide an example tone/style:")

if st.button("Generate Summary"):
    if os.path.exists("output.txt"):
        base_content = read_file("output.txt")
        if base_content:
            prompt = construct_prompt(base_content, audience_type, tone, example)
            summary = call_llm(prompt)
            st.subheader("Generated Summary:")
            st.write(summary)
        else:
            st.error("Failed to read content from output.txt!")
    else:
        st.warning("Please process images first to generate output.txt!")
