import requests
from googlesearch import search
from bs4 import BeautifulSoup

def get_html_content(url):
    try:
        # Send a GET request to the URL
        response = requests.get(url)
        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            return response.text
        else:
            return f"Failed to retrieve content. Status code: {response.status_code}"
    except Exception as e:
        return f"An error occurred: {e}"

def extract_text_from_html(html_content):
    # Parse HTML content with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract text from relevant HTML tags (e.g., paragraphs, headers)
    text_content = ""
    for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        text_content += tag.get_text() + "\n"

    return text_content

def get_top_links_text(query, num=1):
    try:
        # Perform a Google search and get the top links
        search_results = search(query, num=num, stop=num, pause=2)
        
        # Iterate through the links and fetch and extract text content
        for index, link in enumerate(search_results, start=1):
            html_content = get_html_content(link)
            text_content = extract_text_from_html(html_content)
            
            # Print the link and corresponding text content
            print(f"[{link}]")
            print(text_content)
            print()

    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage
search_query = "https://python-googlesearch.readthedocs.io/en/latest/"
print(extract_text_from_html(get_html_content(search_query)))