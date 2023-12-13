from PyPDF2 import PdfReader
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LAParams
from cleantext import clean
import re
import wordninja
import json
import streamlit as st

laparams = LAParams(line_overlap=0.25)

import re

def clean_title(title):
    cleaned_title = re.sub(r'^\s*(Chapter|Section)?\s*\d*\.?\d*\s*-*\s*', '', title, flags=re.IGNORECASE)

    if '-' in cleaned_title:
        parts = cleaned_title.split('-')
        cleaned_title = parts[-1] if len(parts[-1].strip()) > 3 else cleaned_title

    cleaned_title = cleaned_title.strip()

    # Fallback to original title if cleaned title becomes too short, indicating over-cleaning
    if len(cleaned_title) < 3:
        cleaned_title = title.strip()

    return cleaned_title


def convert_outline(reader, outline):
    data = []
    for i, item in enumerate(outline):
        if isinstance(item, dict):
            json_item = {'title': item.title,
                         'start_page': reader.get_destination_page_number(item)}
        next_item = outline[i + 1] if i + 1 < len(outline) else None
        if isinstance(next_item, list):
            json_item['children'] = convert_outline(reader, next_item)
            continue
        data.append(json_item)
    return data

def calculate_end_pages(reader, data, parent_end_page=None):
    for i, item in enumerate(data):
        item['end_page'] = data[i + 1]['start_page'] if i + 1 < len(data) else parent_end_page
        if item['end_page'] is None:
            item['end_page'] = len(reader.pages) - 1
        if 'children' in item:
            calculate_end_pages(reader, item['children'], item['end_page'])

# def extract_page_range_content(start_page, end_page):
#     content = ''
#     for page_num in range(start_page, end_page + 1):
#         content += reader.pages[page_num].extract_text()
#     return content

def extract_page_range_content(pdf_path, start_page, end_page):
    # print(f"Extracting content from between p.{start_page} and p.{end_page}")
    with st.spinner(f"Extracting content from between p.{start_page} and p.{end_page}"):
        content = ''
        page_numbers = range(start_page, end_page + 1)
        for page_layout in extract_pages(pdf_path, page_numbers=page_numbers, laparams=laparams):
            for element in page_layout:
                if isinstance(element, LTTextContainer):
                    content += element.get_text() + '\n\n'
        return content

def populate_content(pdf_path, data):
    for item in data:
        if 'children' in item:
            populate_content(pdf_path, item['children'])
            continue
        item['content'] = extract_page_range_content(pdf_path, item['start_page'], item['end_page'])

def transform(data, parent_title=None):
    result = []
    for item in data:
        title = clean_title(item['title'])
        content = item.get('content')
        if content:
            json_item = {'section_title': title, 'content': content}
            if parent_title:
                clean_parent_title = clean_title(parent_title)
                json_item['parent_section_title'] = clean_parent_title
            result.append(json_item)
        if 'children' in item:
            result.extend(transform(item['children'], title))
    return result

def separate_into_paragraphs(data):
    result = []
    for item in data:
        paragraphs = item['content'].split('\n\n')
        for paragraph in paragraphs:
            json_item = {
                'section_title': item['section_title'],
                'content': paragraph.strip()
            }
            if 'parent_section_title' in item:
                json_item['parent_section_title'] = item['parent_section_title']
            result.append(json_item)
    return result

def remove_noises(data):
    data[:] = [item for item in data if len(item['content']) >= 32 and len(item['content'].split()) >= 8]

def clean_text(data):
    for item in data:
        content = item['content']
        content = clean(content, no_line_breaks=True, no_urls=True, no_emails=True, no_punct=True)
        item['content'] = content

def remove_spaces(data):
    for item in data:
        content = item['content']
        content = re.sub(r' ', '', content)
        item['content'] = content

def separate_words(data):
    for item in data:
        text = item['content']
        words = wordninja.split(text)
        item['content'] = ' '.join(words)

def main():
    st.title("Attributes education knowledge graph PDF to JSON Converter")

    # Provide a brief instruction
    st.markdown(
        "Upload a PDF file and get its content in JSON format. This tool extracts the outlines and content of the PDF.")

    col1, col2 = st.columns(2)

    with col1:
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

    if uploaded_file:
        with st.spinner("Processing the PDF..."):
            reader = PdfReader(uploaded_file)
            outline = reader.outline

            with st.spinner('Extracing content...'):
                textbook = convert_outline(reader, outline)
                calculate_end_pages(reader, textbook)
                populate_content(uploaded_file, textbook)

            with st.spinner('Processing extracted content...'):
                textbook = transform(textbook)
                paragraphs = separate_into_paragraphs(textbook)
                remove_noises(paragraphs)
                clean_text(paragraphs)
                remove_spaces(paragraphs)
                separate_words(paragraphs)
            
            json_data = paragraphs

        st.success("PDF processed successfully!")

        flie_name = uploaded_file.name.split(".")[0]
        json_file_name = f"{flie_name}.json"

        json_str = json.dumps(json_data, indent=4)

        with col2:
            if st.button("Show JSON data"):
                st.text_area("JSON Content", json_str, height=300)

            st.download_button(
                label="Download JSON",
                data=json_str.encode(),
                file_name=json_file_name,
                mime="application/json"
            )
    else:
        st.warning("Please upload a PDF to proceed.")


if __name__ == '__main__':
    main()
