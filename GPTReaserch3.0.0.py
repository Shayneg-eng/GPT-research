import re
import requests
from googlesearch import search
from bs4 import BeautifulSoup
import os
import ollama
import colorama
from colorama import Fore, Style
from datetime import datetime
    
    
topic = ''
history = ''
visited_urls = []
pendingLinks = []

    
def ai_chat(prompt):
    try:
        response = ollama.chat(model='qwen:14b', messages=[
            {
                'role': 'user',
                'content': prompt,
            },
        ])
        return response['message']['content']
    except Exception as e:
        print(f"{Fore.RED}Error in AI chat: {e}{Style.RESET_ALL}")
        return None
    
def web_search(query):
    if not query or query.isspace():
        print(f"{Fore.RED}Error: Empty search query{Style.RESET_ALL}")
        return
        
    print(f"{Fore.GREEN}Searching for: {query}{Style.RESET_ALL}")
    
    try:
        results = []
        for url in search(query, num=3, stop=3, pause=2):
            if url not in visited_urls:
                results.append(url)
                pendingLinks.append(url)
        
        if results:
            print(f"{Fore.GREEN}Found {len(results)} new links. Saving to pending links.{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}No new links found.{Style.RESET_ALL}")
            
    except Exception as e:
        print(f"{Fore.RED}Search error: {e}{Style.RESET_ALL}")
        return

def read_link(url):
    global history
    print(f"{Fore.GREEN}Reading content from: {url}{Style.RESET_ALL}")
    
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        text_content = " ".join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])])
        history += f"READ_LINK with URL: {url}\n"
        return text_content
    except Exception as e:
        print(f"{Fore.RED}Error reading URL: {e}{Style.RESET_ALL}")
        return None
    
def shouldWeAddUrlContents(contents):
    print(topic)
    return ai_chat(f"""
            your response to this message will be based on
            
            does the following information pertain to the topic: {topic}
            Information: {contents}
            
            ### If the information does relate to the topic respond with 1
            otherwise respond with 0 (respond only with the number. no other characters. your response should be one character long) ###
            """)
    
    
        
LINKSPERSEARCH = 3
topic = "cow"
web_search("cow")
print(pendingLinks)
#print(read_link(pendingLinks[0]))
for link in range(LINKSPERSEARCH):
    print(shouldWeAddUrlContents(read_link(pendingLinks[link])))