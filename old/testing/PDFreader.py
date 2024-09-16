import requests
import PyPDF2
import io

url = "https://www.amnesty.org/en/wp-content/uploads/2022/02/MDE1551412022ENGLISH.pdf"

try:
    response = requests.get(url)
    response.raise_for_status()  # Raise an exception for 403 error

    with io.BytesIO(response.content) as pdf_file:
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        # Proceed with PDF processing (extract text, etc.)

except requests.exceptions.HTTPError as err:
    print("Error:", err)
    # Handle access restrictions or alternative approaches

# Create a PDF reader object
pdf_reader = PyPDF2.PdfReader(response.content)

# Get the number of pages in the PDF
num_pages = len(pdf_reader.pages)

# Print information about the PDF
print("Number of pages:", num_pages)

# Iterate through each page and extract text
for page_num in range(num_pages):
    page = pdf_reader.pages[page_num]
    text = page.extract_text()
    print("Page {}: {}".format(page_num + 1, text))