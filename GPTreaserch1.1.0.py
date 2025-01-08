import requests
from googlesearch import search
from bs4 import BeautifulSoup
import os
import ollama
from tqdm import tqdm
import colorama
from colorama import Fore, Style
import time
from datetime import datetime

# Initialize colorama
colorama.init()

class ResearchBot:
    def __init__(self):
        self.visited_urls = set()
        self.search_count = 0
        self.MAX_SEARCHES = 50
        self.MAX_LINKS_PER_SEARCH = 10
        self.history = []
        
    def log_action(self, action_type, content):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {action_type}: {content}\n"
        
        with open("research_history.txt", "a", encoding="utf-8") as f:
            f.write(log_entry)
        
        self.history.append(log_entry)

    def ai_chat(self, prompt):
        try:
            response = ollama.chat(model='llama3.1', messages=[
                {
                    'role': 'user',
                    'content': prompt,
                },
            ])
            return response['message']['content']
        except Exception as e:
            print(f"{Fore.RED}Error in AI chat: {e}{Style.RESET_ALL}")
            return None

    def web_search(self, query):
        print(f"{Fore.GREEN}Executing search: {query}{Style.RESET_ALL}")
        self.search_count += 1
        if self.search_count > self.MAX_SEARCHES:
            print(f"{Fore.RED}Maximum search limit reached{Style.RESET_ALL}")
            return []
        
        try:
            results = []
            search_results = search(query, num=self.MAX_LINKS_PER_SEARCH, stop=self.MAX_LINKS_PER_SEARCH, pause=2)
            
            for index, url in enumerate(search_results, start=1):
                if url not in self.visited_urls:
                    results.append(url)
                    print(f"    {index}. {url}")
                else:
                    print(f"    Skipped (already visited): {url}")
            
            self.log_action("WEB_SEARCH", f"Query: {query}\nResults: {len(results)} new URLs")
            return results
        except Exception as e:
            print(f"{Fore.RED}Search error: {e}{Style.RESET_ALL}")
            return []

    def read_link(self, url):
        print(f"{Fore.GREEN}Reading content from: {url}{Style.RESET_ALL}")
        if url in self.visited_urls:
            print(f"    Skipped (already read): {url}")
            return None
        
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            text_content = " ".join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])])
            self.visited_urls.add(url)
            self.log_action("READ_LINK", f"URL: {url}")
            return text_content
        except Exception as e:
            print(f"{Fore.RED}Error reading URL: {e}{Style.RESET_ALL}")
            return None

    def save_raw_data(self, content, source=None):
        print(f"{Fore.GREEN}Saving raw data{Style.RESET_ALL}")
        try:
            with open("raw_data.txt", "a", encoding="utf-8") as f:
                f.write(f"\n--- New Content ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---\n")
                if source:
                    f.write(f"Source: {source}\n")
                f.write(content + "\n")
            self.log_action("SAVE_RAW", f"Saved {len(content)} characters")
        except Exception as e:
            print(f"{Fore.RED}Error saving raw data: {e}{Style.RESET_ALL}")

    def save_final(self, content):
        print(f"{Fore.GREEN}Saving to final research document{Style.RESET_ALL}")
        try:
            with open("final_research.txt", "a", encoding="utf-8") as f:
                f.write(f"\n--- New Research ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---\n")
                f.write(content + "\n")
            self.log_action("SAVE_FINAL", f"Saved {len(content)} characters")
        except Exception as e:
            print(f"{Fore.RED}Error saving final research: {e}{Style.RESET_ALL}")

    def process_ai_command(self, command):
        if '{' in command and '}' in command:
            thought = command[command.find('{')+1:command.find('}')]
            print(f"    AI: {thought}")
            command = command[command.find('}')+1:].strip()

        lines = command.strip().split('\n')
        cmd_type = lines[0].strip()
        content = '\n'.join(lines[1:]) if len(lines) > 1 else ""

        if cmd_type.startswith("--web-search--"):
            if not content:
                print(f"{Fore.RED}Error: Empty search query{Style.RESET_ALL}")
                return None
            results = self.web_search(content)
            return results
        elif cmd_type.startswith("--read-link--"):
            if not content:
                print(f"{Fore.RED}Error: Empty URL{Style.RESET_ALL}")
                return None
            content = self.read_link(content)
            return content
        elif cmd_type.startswith("--save-raw--"):
            self.save_raw_data(content)
        elif cmd_type.startswith("--save-final--"):
            self.save_final(content)
        elif cmd_type.startswith("--analyze--"):
            print(f"    Analyzing: {content}")
            self.log_action("ANALYSIS", content)
        else:
            print(f"{Fore.RED}Unknown command: {cmd_type}{Style.RESET_ALL}")

def create_fresh_files():
    files = ['raw_data.txt', 'research_history.txt', 'final_research.txt']
    for file in files:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(f"Research started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

def get_context_for_ai(history):
    recent_history = history[-10:] if len(history) > 10 else history
    context = "\n".join(recent_history)
    return context

def create_ai_prompt(topic, context, bot):
    prompt = f"""You are an autonomous research bot investigating: {topic}

Your available commands are:
--web-search-- [search query]
--read-link-- [URL]
--save-raw-- [content]
--save-final-- [organized findings]
--analyze-- [your analysis]

IMPORTANT: Before each command, include your thought process in curly braces.
Example:
{{I need to search for basic information about the topic}}
--web-search-- {topic} history and background

OR
{{This source seems relevant, let me read it}}
--read-link-- [URL]

Recent history:
{context}

Based on this information, decide your next action. You can:
1. Search for new information
2. Read from a specific link
3. Save raw data you've collected
4. Save organized findings to the final research
5. Analyze current information and determine next steps

You should think like a human researcher:
- Cross-reference information
- Look for contradictions
- Seek multiple sources
- Ask follow-up questions
- Organize information logically

IMPORTANT: 
- Always include your thought process in curly braces {{}}
- Always include specific search terms or URLs with your commands
- Never send an empty search query or URL

What is your next action?"""
    return prompt

def check_research_complete(topic, current_data, bot):
    prompt = f"""Review this research topic and current findings to determine if the research is complete.

Topic: {topic}

Current Research Status:
{current_data}

Should the research continue? Respond with only 'COMPLETE' or 'CONTINUE' followed by a brief reason why."""
    
    response = bot.ai_chat(prompt)
    return response.startswith('COMPLETE')

def main():
    print(f"{Fore.GREEN}=== Research Bot Initializing ==={Style.RESET_ALL}")
    create_fresh_files()
    bot = ResearchBot()
    
    topic = input("Enter research topic: ")
    print(f"{Fore.GREEN}Starting research on: {topic}{Style.RESET_ALL}")
    
    # Initial setup
    bot.log_action("INIT", f"Research topic: {topic}")
    last_command = None
    
    while True:
        context = get_context_for_ai(bot.history)
        prompt = create_ai_prompt(topic, context, bot)
        ai_response = bot.ai_chat(prompt)
        
        if not ai_response:
            print(f"{Fore.RED}Error: No response from AI{Style.RESET_ALL}")
            continue
            
        if ai_response == last_command:
            print(f"{Fore.RED}Detected command loop. Forcing analysis...{Style.RESET_ALL}")
            ai_response = f"{{Analyzing current information to break the loop}}\n--analyze-- Reviewing collected data"
        
        last_command = ai_response
        result = bot.process_ai_command(ai_response)
        
        if result:
            process_prompt = f"""Process this new information related to {topic}:

{result}

Decide what to do with this information. You can:
1. Save it as raw data
2. Save it as organized findings
3. Analyze it to determine next steps

IMPORTANT: Include your thought process in curly braces {{}}.
Respond with the appropriate command."""
            
            process_response = bot.ai_chat(process_prompt)
            if process_response:
                bot.process_ai_command(process_response)
        
        with open("final_research.txt", "r", encoding="utf-8") as f:
            current_research = f.read()
        
        if check_research_complete(topic, current_research, bot):
            print(f"{Fore.GREEN}Research complete! Check final_research.txt for results.{Style.RESET_ALL}")
            break
            
        time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Research interrupted by user{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Fatal error: {e}{Style.RESET_ALL}")
    finally:
        print(f"{Fore.GREEN}Research session ended{Style.RESET_ALL}")