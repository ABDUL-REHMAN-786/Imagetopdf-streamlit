import streamlit as st
import os
import cv2
import numpy as np
import pytesseract
from PIL import Image
import img2pdf
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, letter, legal
import tempfile
import time
import dropbox
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

# Streamlit Page Configuration
st.set_page_config(page_title="AI Image to PDF Converter", layout="wide", initial_sidebar_state="expanded")

st.title("📄 AI-Powered Image to PDF Converter")

# Upload Images
uploaded_files = st.file_uploader("Upload Images", type=["jpg", "jpeg", "png", "bmp", "gif", "tiff", "webp"], accept_multiple_files=True)

# Sidebar Options
st.sidebar.header("Customization Options")
apply_ocr = st.sidebar.checkbox("Enable OCR (Make PDF Searchable)")
language = st.sidebar.selectbox("OCR Language", ["eng", "spa", "fra", "deu", "chi_sim", "ara", "hin"])
watermark_text = st.sidebar.text_input("Add Watermark (Optional)")
password = st.sidebar.text_input("Set PDF Password (Optional)", type="password")
page_size = st.sidebar.selectbox("Page Size", ["A4", "Letter", "Legal"])
cloud_option = st.sidebar.radio("Upload to Cloud", ["None", "Google Drive", "Dropbox"])
dark_mode = st.sidebar.checkbox("Enable Dark Mode")

# Dark Mode Styling
if dark_mode:
    st.markdown("""
    <style>
        body { background-color: #1e1e1e; color: white; }
    </style>
    """, unsafe_allow_html=True)

# Image Processing Functions
def preprocess_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary

def correct_orientation(image):
    angle = pytesseract.image_to_osd(image)["rotate"]
    if angle != 0:
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, -angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated
    return image

def extract_text_from_image(image):
    return pytesseract.image_to_string(image, lang=language)

def images_to_pdf(images, output_pdf_path, apply_ocr):
    pdf_writer = PdfWriter()
    
    for image in images:
        img = Image.open(image)
        img = img.convert("RGB")

        if apply_ocr:
            text = extract_text_from_image(np.array(img))
            temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            c = canvas.Canvas(temp_pdf.name, pagesize=A4)
            c.drawString(100, 750, text)
            c.save()
            
            pdf_reader = PdfReader(temp_pdf.name)
            pdf_writer.add_page(pdf_reader.pages[0])
        else:
            pdf_writer.add_page(img2pdf.convert(img))

    with open(output_pdf_path, "wb") as f:
        pdf_writer.write(f)

def add_watermark(input_pdf, output_pdf, watermark_text):
    pdf_reader = PdfReader(input_pdf)
    pdf_writer = PdfWriter()

    for page in pdf_reader.pages:
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        c = canvas.Canvas(temp_pdf.name, pagesize=A4)
        c.setFont("Helvetica", 20)
        c.drawString(200, 500, watermark_text)
        c.save()

        watermark_reader = PdfReader(temp_pdf.name)
        page.merge_page(watermark_reader.pages[0])
        pdf_writer.add_page(page)

    with open(output_pdf, "wb") as f:
        pdf_writer.write(f)

def encrypt_pdf(input_pdf, output_pdf, password):
    pdf_reader = PdfReader(input_pdf)
    pdf_writer = PdfWriter()

    for page in pdf_reader.pages:
        pdf_writer.add_page(page)

    pdf_writer.encrypt(password)

    with open(output_pdf, "wb") as f:
        pdf_writer.write(f)

# Cloud Upload Functions
def upload_to_google_drive(file_path, file_name):
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    drive = GoogleDrive(gauth)
    file = drive.CreateFile({'title': file_name})
    file.SetContentFile(file_path)
    file.Upload()
    st.success("Uploaded to Google Drive!")

def upload_to_dropbox(file_path, file_name):
    DROPBOX_ACCESS_TOKEN = "your_dropbox_token"
    dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
    with open(file_path, "rb") as f:
        dbx.files_upload(f.read(), f"/{file_name}")
    st.success("Uploaded to Dropbox!")

# Conversion Button
if st.button("Convert to PDF"):
    with st.spinner("Processing..."):
        output_pdf_path = "converted.pdf"
        
        progress = st.progress(0)
        for i in range(100):
            time.sleep(0.02)
            progress.progress(i + 1)

        images_to_pdf(uploaded_files, output_pdf_path, apply_ocr)

        if watermark_text:
            temp_path = "watermarked.pdf"
            add_watermark(output_pdf_path, temp_path, watermark_text)
            output_pdf_path = temp_path

        if password:
            temp_path = "encrypted.pdf"
            encrypt_pdf(output_pdf_path, temp_path, password)
            output_pdf_path = temp_path

        st.success("PDF Conversion Successful!")
        st.download_button("Download PDF", open(output_pdf_path, "rb"), file_name="converted.pdf", mime="application/pdf")

# Cloud Upload
if st.button("Upload to Cloud"):
    if cloud_option == "Google Drive":
        upload_to_google_drive("converted.pdf", "converted.pdf")
    elif cloud_option == "Dropbox":
        upload_to_dropbox("converted.pdf", "converted.pdf")

# Offline Caching
@st.cache
def cache_pdf(file_path):
    with open(file_path, "rb") as f:
        return f.read()

if os.path.exists("converted.pdf"):
    pdf_data = cache_pdf("converted.pdf")
    st.download_button("Download Cached PDF", pdf_data, "converted.pdf", "application/pdf")

st.sidebar.info("📌 Tip: Enable OCR to make the PDF text searchable!")
st.sidebar.info("🔒 Set a password for extra security.")
