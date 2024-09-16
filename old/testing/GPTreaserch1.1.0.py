import requests
from googlesearch import search
from bs4 import BeautifulSoup
import tiktoken
from io import BytesIO
import PyPDF2
import os
import ollama
from tqdm import tqdm
import colorama
from colorama import Fore, Style
import codecs
colorama.init()

blacklistedURLs = []
allLinks = []  # Initialize allLinks as an empty list

def AIchat(prompt):
    response = ollama.chat(model='phi3', messages=[
        {
            'role': 'user',
            'content': prompt,
        },
    ])
    return response['message']['content']

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

def get_top_links(blacklistedURLs, query, num=4):
    global allLinks

    try:
        # Perform a Google search and get the top links
        search_results = search(query, num=num, stop=num, pause=2)

        # Print the links
        for index, link in enumerate(search_results, start=1):
            if link not in blacklistedURLs:
                allLinks.append(link)
                blacklistedURLs.append(link)
                print(f"{index}. {link}")
            else:
                print(f"Skipped a URL that I already read: {link}")

    except Exception as e:
        print(f"An error occurred: {e}")

def splitSearchIdeas(ideas_string):
    # Remove the brackets and split the string into a list
    ideas_list = ideas_string[1:-1].split(", ")

    # Strip leading and trailing whitespace from each idea
    ideas_list = [idea.strip() for idea in ideas_list]

    # Create a list with the non-None values
    filtered_ideas = [value for value in ideas_list if value is not None]
    return filtered_ideas

def googleSearchLinkGeneration(userInputedTopic):
    prompt = f"You will come up with 2 good Google searches that will help find out more about the topic: {userInputedTopic}. You will format the Google search ideas in the form of a single list with your three search ideas separated by a comma and surrounded by square brackets, e.g., [types of trees, benefits of trees, tree conservation efforts]. ###IMPORTANT - only provide the list and NO other words."

    googleSearchIdeas = AIchat(prompt)
    googleSearchIdeas = splitSearchIdeas(googleSearchIdeas)
    print(f"{Fore.CYAN}Google searches: {', '.join(googleSearchIdeas)}{Style.RESET_ALL}")

    for query in googleSearchIdeas:
        links = get_top_links(blacklistedURLs, query)
        # Check if links is not None before extending the list
        if links is not None:
            allLinks.extend(links)

    return allLinks

def getDataFromLinks(allLinks, userInputedTopic):
    allData = []
    getMoreLinks = 0

    print(f"{Fore.CYAN}All links: {', '.join(allLinks)}{Style.RESET_ALL}")
    for link in tqdm(allLinks, desc="Reading links", unit="link", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"):

        textFromLink = extract_text_from_html(get_html_content(link))

        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")  # checking that token length is ok
        token_count = len(encoding.encode(textFromLink))

        if token_count == 0:
            print(f"{Fore.RED}Couldn't access this weblink: {link}{Style.RESET_ALL}")
            if (getMoreLinks % 2) == 0:
                getMoreLinks += 1

        elif token_count > 160000:
            print(f"{Fore.YELLOW}Weblink too large: {link}{Style.RESET_ALL}")
            getMoreLinks += 1

        elif token_count < 16000:
            prompt = f"You will read through all this and extract all the relevant data concerning {userInputedTopic}. You will prioritize: numbers, statistics, facts, etc. Here is the website's text: {textFromLink}."
            GPTdataFromLink = AIchat(prompt)
            allData.append((GPTdataFromLink, link))  # Append a tuple containing the data and the link

    return allData, getMoreLinks

def writeToTXTandEdit(allLinks, allData):
    numbered_data = []
    link_references = {}

    for i, (link, data) in enumerate(zip(allLinks, allData), start=1):
        numbered_data.append(f"{i}. {data}")
        link_references[i] = link

    with open('sourcesAndData.txt', 'w') as file:
        for num, (data, link) in enumerate(zip(numbered_data, allLinks), start=1):
            file.write(f"{data}\n{link}\n\n")

    with open("sourcesAndData.txt", "r") as file:
        existing_content = file.read()

        prompt = (f"Read this information and keep as much data as you can but delete duplicates. Make sure all information pertains to: {userInputedTopic}. After each piece of information, include the corresponding number in square brackets. At the end, include a section titled 'Sources' and list the links corresponding to each number. Here is the information: {existing_content}")

        rejiggeredData = AIchat(prompt)

    # Write the modified content back to the text document
    with open("outputFinal.txt", "w") as file:
        file.write(rejiggeredData)

def reassessData(userInputedTopic):
    with open("sourcesAndData.txt", "r") as file:
        existing_content = file.read()
        prompt = (f"Read this {existing_content}. and look at it in relation to the topic: {userInputedTopic}. Come up with something else that you would like to know about this topic in the form of what someone would search on Google. You will come up with your one more Google search that will help find out more about the topic: {userInputedTopic}. You will respond to this prompt with only the Google search words and nothing else. ###IMPORTANT the only output from this prompt should be the Google search and no surrounding words.")
        newGoogleSearch = AIchat(prompt)
        return newGoogleSearch
        
def writeNewDataToNewTXT(allLinks, allData):
    with open('rejiggeredSourcesAndData.txt', 'w') as file:
        shorter_list = min(allLinks, allData, key=len)
        for i in range(len(shorter_list)):
            file.write(allLinks[i])
            file.write(allData[i])
            
def combineTXTFiles(file1_path, file2_path, output_path):
    # Open the first file in read mode to read its content
    with open(file1_path, 'r') as file1:
        content_file1 = file1.read()

    # Open the second file in read mode to read its content
    with open(file2_path, 'r') as file2:
        content_file2 = file2.read()

    # Combine the content of the two files
    combined_content = content_file1 + '\n' + content_file2

    # Open the output file in write mode to write the combined content
    with open(output_path, 'w') as output_file:
        output_file.write(combined_content)
    
def run():
    global userInputedTopic

    userInputedTopic = input("Enter a research topic: ")
    allLinks = googleSearchLinkGeneration(userInputedTopic)
    allData, getMoreLinks = getDataFromLinks(allLinks, userInputedTopic)
    writeToTXTandEdit(allLinks, allData)

    if os.path.isfile("sourcesAndData.txt"):
        for linkNumber in range(getMoreLinks):
            new_links = googleSearchLinkGeneration(reassessData(userInputedTopic))
            new_data, _ = getDataFromLinks(new_links, userInputedTopic)
            allLinks.extend(new_links)

            with open("outputFinal.txt", "a", encoding="utf-8") as output_file:
                for data, link in new_data:
                    output_file.write(f"{data}\nSource: {link}\n\n")
    else:
        print("sourcesAndData.txt file not found. Skipping additional data gathering.")

if __name__ == "__main__":
    run()