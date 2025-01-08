import re
import requests
from googlesearch import search
from bs4 import BeautifulSoup
import os
import ollama
import colorama
from colorama import Fore, Style
from datetime import datetime
from openai import OpenAI

# ----------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------

# DeepSeek API configuration
DEEPSEEK_API_KEY = "sk-91243ea8c2584fbc888cc7ed818cc4cf"
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

# Path to text files
HISTORY_FILE = "history.txt"
LINKS_FILE = "links.txt"
EXTRACTED_DATA_FILE = "extracted_data.txt"
FINAL_RESEARCH_FILE = "final_research.txt"

# ----------------------------------------------------------------
# Helper Functions to Manage Files
# ----------------------------------------------------------------

def read_file(filename: str) -> str:
    """Return the full content of a file as a string. Create the file if it doesn't exist."""
    if not os.path.exists(filename):
        open(filename, 'a').close()
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(filename: str, content: str, mode: str = 'w') -> None:
    """Write content to a file. Overwrite by default, or append if mode='a'."""
    with open(filename, mode, encoding='utf-8') as f:
        f.write(content)

def append_history(action_description: str) -> None:
    """Record a brief history/action step in the history file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    write_file(HISTORY_FILE, f"[{timestamp}] {action_description}\n", mode='a')

# ----------------------------------------------------------------
# DeepSeek API Interaction
# ----------------------------------------------------------------

def chat_with_deepseek(prompt: str) -> str:
    """
    Sends a chat request to DeepSeek API and returns the response text.
    """
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful research assistant"},
                {"role": "user", "content": prompt}
            ],
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error talking to DeepSeek: {e}")
        return "Error: Could not fetch response from DeepSeek."

# ----------------------------------------------------------------
# Functions to Carry Out DeepSeek's Actions
# ----------------------------------------------------------------

def perform_web_search(query: str) -> None:
    """
    Perform a Google search on the given query, then store the top links
    in the links file for further reading.
    """
    append_history(f"Performing web search on: {query}")
    results = []
    try:
        for url in search(query, num_results=5):
            results.append(url)
    except Exception as e:
        print(f"Error performing Google search: {e}")

    # Append these results to the links file
    for r in results:
        write_file(LINKS_FILE, r + "\n", mode='a')

def read_and_extract(link: str) -> None:
    """
    Read the content of a link, extract relevant text using BeautifulSoup,
    then append it to the extracted_data file.
    """
    append_history(f"Reading link: {link}")
    try:
        r = requests.get(link, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        text_content = soup.get_text(separator=' ', strip=True)
        write_file(EXTRACTED_DATA_FILE, f"---CONTENT FROM {link}---\n{text_content}\n\n", mode='a')
    except Exception as e:
        print(f"Error reading link {link}: {e}")

# ----------------------------------------------------------------
# The Main Research Loop
# ----------------------------------------------------------------

def main():
    colorama.init()
    
    print(Fore.GREEN + "Welcome to the DeepSeek Research Bot" + Style.RESET_ALL)
    topic = input("Enter a topic you wish to research: ")
    final_format = input("Enter your desired final format (e.g., 'APA style', 'MLA style', 'Plain text'): ")

    while True:
        # Read the data from text files
        history_data = read_file(HISTORY_FILE)
        links_data = read_file(LINKS_FILE)
        extracted_data = read_file(EXTRACTED_DATA_FILE)
        final_research_data = read_file(FINAL_RESEARCH_FILE)

        # Construct the prompt for DeepSeek
        base_prompt = f"""
You have the following data from different text files:

[History File Contents]
{history_data}

[Links File Contents]
{links_data}

[Extracted Data File Contents]
{extracted_data}

[Final Research File Contents]
{final_research_data}

The user wants to research the topic: '{topic}'.
The user wants the final output in this format: '{final_format}'.

At any time, if you need to gather new information, you can choose an action in the form:
   --websearch-- <search query>
   --readlink-- <URL>
indicating you want the script to do a web search or read a specific URL. 
After these actions, the relevant data is appended to the text files, and you will be prompted again
with all updated data.

Your ultimate goal is to produce a final paragraph with cited information in user's desired format,
always including links and data references. You can produce this final paragraph by outputting:
   --final-- <Your final research paragraph here>

Remember to always include citations with links and references to data. Do not produce code for the user.

Please decide your next step or produce the final result.
"""

        # Pass this prompt to DeepSeek
        response = chat_with_deepseek(base_prompt)
        print(Fore.YELLOW + "DeepSeek's Response:\n" + Style.RESET_ALL, response)
        
        # Parse DeepSeek's response for any actions or final output
        action_websearch = re.findall(r"--websearch--\s*(.*)", response)
        action_readlink = re.findall(r"--readlink--\s*(.*)", response)
        action_final = re.findall(r"--final--\s*(.*)", response, re.DOTALL)
        
        if action_websearch:
            for query in action_websearch:
                perform_web_search(query.strip())
            continue
        
        elif action_readlink:
            for url in action_readlink:
                read_and_extract(url.strip())
            continue
        
        elif action_final:
            final_paragraph = action_final[0].strip()
            write_file(FINAL_RESEARCH_FILE, final_paragraph)
            append_history("Final research concluded.")
            print(Fore.BLUE + "Final Research Output:\n" + Style.RESET_ALL, final_paragraph)
            break
        
        else:
            write_file(FINAL_RESEARCH_FILE, f"Unrecognized action from DeepSeek:\n{response}\n\n", mode='a')
            append_history("No recognized action from DeepSeek. Stopping.")
            break

    print(Fore.GREEN + "Research session complete. Check your text files for details!" + Style.RESET_ALL)

if __name__ == "__main__":
    main()