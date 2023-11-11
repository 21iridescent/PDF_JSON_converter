from PyPDF2 import PdfReader
import json
import re
# import wordninja
import streamlit as st

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

def extract_page_range_content(reader, start_page, end_page):
    content = ''
    for page_num in range(start_page, end_page + 1):
        content += reader.pages[page_num].extract_text()
    return content

def populate_content(reader, data):
    for item in data:
        if 'children' in item:
            populate_content(reader, item['children'])
            continue
        item['content'] = extract_page_range_content(reader, item['start_page'], item['end_page'])

def transform_into_paragraphs(data, parent_title=None):
    result = []
    for item in data:
        title = item['title']
        content = item.get('content')
        if content:
            json_item = {'section_title': title,
			 'parent_section_title': parent_title if parent_title is not None else '',
                         'content': content}
            if not parent_title:
                json_item.pop('parent_section_title', None)
            result.append(json_item)
        if 'children' in item:
            result.extend(transform_into_paragraphs(item['children'], title))
    return result

def remove_line_feeds(data):
    for item in data:
        content = item['content']
        content = re.sub(r'-\n', '', content)
        content = re.sub(r'\n', ' ', content)
        item['content'] = content

# def remove_spaces(data):
#     for item in data:
#         content = item['content']
#         content = re.sub(r' ', '', content)
#         item['content'] = content

# def separate_words(data):
#     for item in data:
#         text = item['content']
#         words = wordninja.split(text)
#         item['content'] = ' '.join(words)

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

            textbook = convert_outline(reader, outline)
            calculate_end_pages(reader, textbook)
            populate_content(reader, textbook)

            paragraphs = transform_into_paragraphs(textbook)
            remove_line_feeds(paragraphs)
            # remove_spaces(paragraphs)
            # separate_words(paragraphs)
            
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
