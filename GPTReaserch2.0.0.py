import requests
from googlesearch import search
from bs4 import BeautifulSoup
import os
import ollama
import colorama
from colorama import Fore, Style
from datetime import datetime

colorama.init()

class ResearchBot:
    def __init__(self):
        self.visited_urls = set()
        self.research_dir = "GPTResearch2"
        self.pending_links_file = os.path.join(self.research_dir, "pending_links.txt")
        
        if not os.path.exists(self.research_dir):
            os.makedirs(self.research_dir)
            for file in ['raw_data.txt', 'research_history.txt', 'final_research.txt', 'pending_links.txt']:
                with open(os.path.join(self.research_dir, file), 'w', encoding='utf-8') as f:
                    f.write(f"Research started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    def save_pending_links(self, links):
        with open(self.pending_links_file, 'a', encoding='utf-8') as f:
            for link in links:
                f.write(f"{link}\n")

    def get_pending_links(self):
        if not os.path.exists(self.pending_links_file):
            return []
        with open(self.pending_links_file, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f.readlines() if line.strip() and not line.startswith("Research started")]

    def remove_link_from_pending(self, link_to_remove):
        links = self.get_pending_links()
        links = [link for link in links if link != link_to_remove]
        with open(self.pending_links_file, 'w', encoding='utf-8') as f:
            for link in links:
                f.write(f"{link}\n")

    def web_search(self, query):
        if not query or query.isspace():
            print(f"{Fore.RED}Error: Empty search query{Style.RESET_ALL}")
            return []
            
        print(f"{Fore.GREEN}Searching for: {query}{Style.RESET_ALL}")
        
        try:
            results = []
            for url in search(query, num=10, stop=10, pause=2):
                if url not in self.visited_urls:
                    results.append(url)
            
            if results:
                print(f"{Fore.GREEN}Found {len(results)} new links. Saving to pending links.{Style.RESET_ALL}")
                self.save_pending_links(results)
            else:
                print(f"{Fore.YELLOW}No new links found.{Style.RESET_ALL}")
                
            return results
        except Exception as e:
            print(f"{Fore.RED}Search error: {e}{Style.RESET_ALL}")
            return []

    def analyze_link(self, url):
        if url in self.visited_urls:
            print(f"{Fore.YELLOW}Skipping: Already analyzed {url}{Style.RESET_ALL}")
            return None
            
        try:
            print(f"\n{Fore.CYAN}=== Analyzing Link ==={Style.RESET_ALL}")
            print(f"URL: {url}")
            
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            text = " ".join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])])
            
            print(f"{Fore.CYAN}Extracting information...{Style.RESET_ALL}")
            analysis_prompt = f"""Analyze this content and extract the most important information about {self.current_topic}.
            Focus on factual information, key events, statistics, and significant details.

            Content from {url}:
            {text}

            Extract and summarize the key information:"""
            
            analysis_response = ollama.chat(model='mistral', messages=[
                {
                    'role': 'user',
                    'content': analysis_prompt,
                }
            ])
            
            extracted_info = analysis_response['message']['content']
            
            print(f"{Fore.GREEN}Information extracted and saved to raw_data.txt{Style.RESET_ALL}")
            self.save_data(f"Source: {url}\nExtracted Information:\n{extracted_info}\n", "raw")
            
            self.visited_urls.add(url)
            self.remove_link_from_pending(url)
            
            return extracted_info
        except Exception as e:
            print(f"{Fore.RED}Error analyzing URL: {e}{Style.RESET_ALL}")
            return None
    
    def save_data(self, content, file_type="raw"):
        filename = "raw_data.txt" if file_type == "raw" else "final_research.txt"
        try:
            with open(os.path.join(self.research_dir, filename), "a", encoding="utf-8") as f:
                f.write(f"\n--- New Content ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---\n")
                f.write(content + "\n")
        except Exception as e:
            print(f"{Fore.RED}Error saving data: {e}{Style.RESET_ALL}")

    def process_command(self, command):
        if '{' in command and '}' in command:
            thought = command[command.find('{')+1:command.find('}')]
            print(f"\n{Fore.BLUE}AI Thought: {thought}{Style.RESET_ALL}")
            command = command[command.find('}')+1:].strip()

        parts = command.split('--')
        if len(parts) < 3:
            print(f"{Fore.RED}Error: Invalid command format{Style.RESET_ALL}")
            return None

        cmd_type = parts[1].strip()
        content = parts[2].strip()

        if not content:
            print(f"{Fore.RED}Error: No content provided{Style.RESET_ALL}")
            return None

        print(f"\n{Fore.GREEN}Executing command: {cmd_type}{Style.RESET_ALL}")
        
        if cmd_type == "web-search":
            return self.web_search(content)
        elif cmd_type == "analyze-link":
            return self.analyze_link(content)
        elif cmd_type == "save-final":
            self.save_data(content, "final")
        else:
            print(f"{Fore.RED}Unknown command: {cmd_type}{Style.RESET_ALL}")
                
def getRawData(filename='raw_data.txt'):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            text = file.read()
        return text
    except FileNotFoundError:
        return "File not found."
    except Exception as e:
        return f"An error occurred: {e}"

def getPendingLinks(filename='GPTResearch2/pending_links.txt'):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            links = [line.strip() for line in file.readlines() if line.strip() and not line.startswith("Research")]
        return "\n".join(links)
    except FileNotFoundError:
        return "No pending links."
    except Exception as e:
        return f"An error occurred: {e}"

def create_ai_prompt(topic):
    return f"""You are researching: [{topic}]

Here are your possible commands:
--web-search-- specific search query with multiple keywords
--analyze-link-- specific URL (choose a URL from the pending links to analyze in depth)
--save-final-- organized findings

Follow This EXACT Response Format (dont add anything else):
{{This link seems most relevant to our current research needs}}
--analyze-link-- https://example.com

Current collected information:
[{getRawData()}]

Links to choose from (if there are no links below you need to search for some):
[{getPendingLinks()}]

IMPORTANT:
- only use ONE command in your response
- Think like a researcher: gather info, analyze, organize
- Look at the available links and choose one to analyze if you think it would be beneficial
- If no available links seem relevant to your current research needs, do a new web search
- Build on previous findings
- Focus on different aspects of the topic that haven't been covered yet

PRIORITIZE LINK ANALYSIS

### What is your response? ###"""

def main():
    print(f"{Fore.GREEN}=== Research Bot Initializing ==={Style.RESET_ALL}")
    bot = ResearchBot()
    
    topic = input("Enter research topic: ")
    bot.current_topic = topic  # Store the topic for use in analysis
    print(f"{Fore.GREEN}Starting research on: {topic}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Use Ctrl+C to exit{Style.RESET_ALL}\n")
    
    last_command = None
    
    while True:
        try:
            print(f"\n{Fore.CYAN}=== Waiting for AI Decision ==={Style.RESET_ALL}")
            response = ollama.chat(model='mistral', messages=[
                {
                    'role': 'user',
                    'content': create_ai_prompt(topic),
                }
            ])
            
            ai_response = response['message']['content']
            
            if not ai_response:
                print(f"{Fore.RED}Error: No response from AI{Style.RESET_ALL}")
                continue
                
            if ai_response == last_command:
                print(f"{Fore.RED}Command loop detected. Forcing final analysis...{Style.RESET_ALL}")
                ai_response = f"{{Summarizing current findings}}\n--save-final-- Summary of findings so far"
            
            last_command = ai_response
            bot.process_command(ai_response)
            
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Research interrupted by user{Style.RESET_ALL}")
            break
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
            continue

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"{Fore.RED}Fatal error: {e}{Style.RESET_ALL}")
    finally:
        print(f"{Fore.GREEN}Research session ended{Style.RESET_ALL}")