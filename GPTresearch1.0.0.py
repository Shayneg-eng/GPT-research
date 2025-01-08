import requests
from googlesearch import search
from bs4 import BeautifulSoup

whatToResearch = input("enter a topic you would like me to research: ")
depth = input("enter how many searches you want to do before getting a conclusion: ")

def get_top_links_text(query, num=1):
    try:
        # Perform a Google search and get the top links
        search_results = search(query, num=num, stop=num, pause=2)
        
        # Iterate through the links and fetch and extract text content
        for index, link in enumerate(search_results, start=1):
            html_content = get_html_content(link)
            text_content = extract_text_from_html(html_content)
            
            # Print the link and corresponding text content
            print("-----")
            print(f"[{link}]", text_content)
            print("-----")
            return f"[{link}]", text_content
            
         

    except Exception as e:
        print(f"An error occurred: {e}")
        
def extract_text_from_html(html_content):
    # Parse HTML content with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract text from relevant HTML tags (e.g., paragraphs, headers)
    text_content = ""
    for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        text_content += tag.get_text() + "\n"

    return text_content

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

def chatgpt_api_call(api_key, organization_code, message):
    url = "https://api.openai.com/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "Openai-Organization": organization_code,
    }
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "system", "content": '''" CONTEXT ### you are here to do reaserch on the topic you are given with access to the web.
                      You are interacting directly with the web so whatever you say will be the next search.
                      each time you search you will get back web links followed by the content of that web link
                      use that to formulate your next web search.
                      rinse and repeat this process until the {depth} search when whatever you get back will be the last piece of information and you will form a conclution which you will say out loud with links from your reaserch"'''}
                     , {"role": "user", "content": message}],
    }

    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"Error: {response.status_code}, {response.text}"

# Replace these with your actual API key and organization code
api_key = "......"
organization_code = "........"

searchNumber = 0
verdictReached = False
while verdictReached == False:
    if searchNumber == 0:
        response = chatgpt_api_call(api_key, organization_code, 'please reaserch: {whatToResearch}')
    elif searchNumber == int(depth):
        Finalresponse = chatgpt_api_call(api_key, organization_code, webData)
        print("========================================================================")
        print(Finalresponse)
        verdictReached = True
    else:
        response = chatgpt_api_call(api_key, organization_code, webData)
    
    webData = (get_top_links_text(response, num=3))
    
    searchNumber += 1