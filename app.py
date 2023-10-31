from PyPDF2 import PdfReader
import json
import streamlit as st

def convert_outline_to_json(reader, outline):
    json_data = []

    for i, item in enumerate(outline):
        item = outline[i]

        if isinstance(item, dict):
            json_item = {
                'title': item.title,
                'start_page': reader.get_destination_page_number(item)
            }

        next_item = outline[i + 1] if i + 1 < len(outline) else None
        if isinstance(next_item, list):
            json_item['children'] = convert_outline_to_json(reader, next_item)
            continue

        json_data.append(json_item)

    return json_data

def calculate_end_pages(reader, data, parent_end_page=None):
    for i, section in enumerate(data):
        section['end_page'] = data[i + 1]['start_page'] if i + 1 < len(data) else parent_end_page

        if section['end_page'] is None:
            section['end_page'] = len(reader.pages) - 1

        if 'children' in section:
            calculate_end_pages(reader, section['children'], section['end_page'])

def extract_page_range_content(reader, start_page, end_page):
    content = ''

    for page_num in range(start_page, end_page + 1):
        content += reader.pages[page_num].extract_text()

    return content

def populate_content(reader, data):
    for section in data:
        if 'children' in section:
            populate_content(reader, section['children'])
            continue

        try:
            section['content'] = extract_page_range_content(reader, section['start_page'], section['end_page'])
        except Exception as e:
            st.write(f"An error occurred: {str(e)}")

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

            json_data = convert_outline_to_json(reader, outline)
            calculate_end_pages(reader, json_data)
            populate_content(reader, json_data)

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
