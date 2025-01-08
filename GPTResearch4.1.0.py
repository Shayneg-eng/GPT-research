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
import time

class ResearchBot:
    def __init__(self, api_key="sk-91243ea8c2584fbc888cc7ed818cc4cf", research_dir="research"):
        """Initialize the researcher with DeepSeek API"""
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        self.research_dir = research_dir
        self.files = {
            'data': 'research_data.txt',
            'links': 'research_links.txt',
            'history': 'research_history.txt',
            'final': 'final_research.txt'
        }
        self.setup_research_dir()

    def setup_research_dir(self):
        """Create necessary directories and files"""
        os.makedirs(self.research_dir, exist_ok=True)
        print(f"{Fore.BLUE}Created research directory: {self.research_dir}{Style.RESET_ALL}")
        for file in self.files.values():
            with open(os.path.join(self.research_dir, file), 'w', encoding='utf-8') as f:
                f.write('')
            print(f"{Fore.BLUE}Created file: {file}{Style.RESET_ALL}")

    def log_history(self, action):
        """Log actions to history file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(os.path.join(self.research_dir, self.files['history']), 'a', encoding='utf-8') as f:
            f.write(f"{timestamp}: {action}\n")
        print(f"{Fore.WHITE}[LOG] {action}{Style.RESET_ALL}")

    def web_search(self, query):
        """Perform web search and store links"""
        print(f"\n{Fore.CYAN}🔍 Searching for: {query}{Style.RESET_ALL}")
        try:
            search_results = list(search(query, num=10, stop=10))
            print(f"{Fore.GREEN}Found {len(search_results)} results{Style.RESET_ALL}")
            with open(os.path.join(self.research_dir, self.files['links']), 'w', encoding='utf-8') as f:
                for i, link in enumerate(search_results, 1):
                    f.write(f"{i}. {link}\n")
                    print(f"{Fore.CYAN}[{i}] {link}{Style.RESET_ALL}")
            self.log_history(f"Performed web search for: {query}")
            return search_results
        except Exception as e:
            print(f"{Fore.RED}Search error: {str(e)}{Style.RESET_ALL}")
            self.log_history(f"Search error: {str(e)}")
            return []

    def ai_chat(self, prompt):
        """Interface with Ollama using llama3.1"""
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

    def scrape_webpage(self, url):
        """Scrape content from a webpage and extract important information"""
        print(f"\n{Fore.CYAN}📄 Scraping content from: {url}{Style.RESET_ALL}")
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            text = ' '.join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2', 'h3'])])
            
            print(f"{Fore.YELLOW}Summarizing content...{Style.RESET_ALL}")
            summary_prompt = f"""Summarize the following text, focusing only on the most important information. 
            Keep only factual, relevant information that directly relates to the topic [{topic}]:

            {text[:40000]}"""
            
            summary = self.ai_chat(summary_prompt)
            if summary:
                print(f"{Fore.GREEN}Successfully summarized content{Style.RESET_ALL}")
                return summary
            else:
                print(f"{Fore.RED}Failed to summarize content{Style.RESET_ALL}")
                return ""
                
        except Exception as e:
            print(f"{Fore.RED}Scraping error: {str(e)}{Style.RESET_ALL}")
            self.log_history(f"Scraping error for {url}: {str(e)}")
            return ""

    def read_file_content(self, file_name):
        """Read content from a file"""
        try:
            with open(os.path.join(self.research_dir, file_name), 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"{Fore.RED}Error reading {file_name}: {str(e)}{Style.RESET_ALL}")
            self.log_history(f"Error reading {file_name}: {str(e)}")
            return ""

    def write_file_content(self, file_name, content):
        """Write content to a file"""
        try:
            if isinstance(content, list):
                content = '\n'.join(str(item) for item in content)
            else:
                content = str(content)
                
            with open(os.path.join(self.research_dir, file_name), 'a', encoding='utf-8') as f:
                f.write(content + "\n")
            print(f"{Fore.GREEN}Content written to {file_name}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error writing to {file_name}: {str(e)}{Style.RESET_ALL}")
            self.log_history(f"Error writing to {file_name}: {str(e)}")

    def create_ai_prompt(self, topic, format_type):
        """Create a prompt for DeepSeek with all available information"""
        print(f"\n{Fore.CYAN}Creating prompt for AI...{Style.RESET_ALL}")
        history = self.read_file_content(self.files['history'])
        links = self.read_file_content(self.files['links'])
        data = self.read_file_content(self.files['data'])
        
        prompt = f"""Topic: {topic}
    Format: {format_type}

    CURRENT STATUS:
    Available Data:
    {data}

    Available Links (you dont have to use all of them but you can. aka: only use the ones you think will be the most useful. you can always make another websearch.):
    {links}

    Research History:
    {history}

    INSTRUCTIONS:
    1. Gather comprehensive research by:
    - Searching for relevant information (use --websearch--)
    - Reading and analyzing sources (use --readlink--)
    - Collecting diverse perspectives and data points

    2. When ready to synthesize (use --synthesize--), create a well-researched document that:
    - Follows the requested {format_type} format
    - Includes extensive citations using this format: 
        In-text citation: (#)
        Reference list at end: (#) www.example.com - Brief description
    - Cites at least {numSources} different sources
    - Balances different viewpoints and sources
    - Presents information clearly and logically
    - Includes relevant statistics and data when available

    Available Actions:
    --websearch-- [your search query]
    --readlink-- [number of link to read] (only one at a time)
    --synthesize-- (only when you have enough diverse sources to create comprehensive research)

    Remember: Quality research requires multiple high-quality sources. Don't synthesize until you have gathered enough diverse and reliable sources to create a well-cited document.

    What would you like to do next? Choose an action based on whether you need more sources or are ready to synthesize."""

        return prompt

    def process_ai_response(self, response_text):
        """Process AI's response and execute requested actions"""
        print(f"\n{Fore.YELLOW}AI's response:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{response_text}{Style.RESET_ALL}\n")
        
        if '--websearch--' in response_text:
            query = response_text.split('--websearch--')[1].strip()
            print(f"{Fore.YELLOW}Executing web search for: {query}{Style.RESET_ALL}")
            search_results = self.web_search(query)
            
            if search_results:
                with open(os.path.join(self.research_dir, self.files['data']), 'a', encoding='utf-8') as f:
                    f.write(f"\nSearch Results for: {query}\n")
                    for idx, url in enumerate(search_results, 1):
                        f.write(f"{idx}. {url}\n")
            return True
            
        elif '--readlink--' in response_text:
            link_num = response_text.split('--readlink--')[1].strip()
            print(f"{Fore.YELLOW}Reading link #{link_num}...{Style.RESET_ALL}")
            links = self.read_file_content(self.files['links']).split('\n')
            try:
                link = links[int(link_num)-1].split('. ')[1]
                summary = self.scrape_webpage(link)
                if summary:
                    self.write_file_content(
                        self.files['data'], 
                        f"\nSummarized content from {link}:\n{summary}\n"
                    )
            except:
                print(f"{Fore.RED}Error processing link {link_num}{Style.RESET_ALL}")
                self.log_history(f"Error processing link {link_num}")
            return True
            
        elif '--synthesize--' in response_text:
            print(f"{Fore.YELLOW}Starting final synthesis...{Style.RESET_ALL}")
            return False
                
        return True

    def research(self, topic, format_type):
        """Main research function"""
        print(f"\n{Fore.GREEN}=== Starting research on: {topic} ==={Style.RESET_ALL}")
        print(f"{Fore.GREEN}=== Format: {format_type} ==={Style.RESET_ALL}\n")
        self.log_history(f"Started research on: {topic}")
        
        continue_research = True
        iteration = 1
        
        while continue_research and iteration < 15:
            print(f"\n{Fore.YELLOW}=== Research Iteration {iteration} ==={Style.RESET_ALL}")
            prompt = self.create_ai_prompt(topic, format_type)
            
            try:
                print(f"{Fore.CYAN}Sending request to AI...{Style.RESET_ALL}")
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "You are a research assistant"},
                        {"role": "user", "content": prompt}
                    ],
                    stream=False
                )
                
                continue_research = self.process_ai_response(response.choices[0].message.content)
                self.log_history(f"Iteration {iteration}: {response.choices[0].message.content}")
                
            except Exception as e:
                print(f"{Fore.RED}AI API error: {str(e)}{Style.RESET_ALL}")
                self.log_history(f"AI API error: {str(e)}")
                continue_research = False
                
            iteration += 1

        # Generate final research
        print(f"\n{Fore.GREEN}=== Generating Final Research Document ==={Style.RESET_ALL}")
        collected_data = self.read_file_content(self.files['data'])
        collected_links = self.read_file_content(self.files['links'])
        
        final_prompt = f"""Using all the collected information, create a comprehensive research document on {topic} in {format_type} format.

    AVAILABLE RESEARCH:
    {collected_data}

    AVAILABLE SOURCES:
    {collected_links}

    REQUIREMENTS:
    1. Follow the {format_type} format strictly
    2. Use in-text citations in (#) format
    3. Include direct quotes where appropriate
    4. Cite at least 8-10 different sources
    5. Include a numbered reference list at the end in this format:
    (#) www.example.com - Brief description of source

    Make sure the document is well-organized, thoroughly researched, and properly cited."""
        
        try:
            final_response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a research assistant"},
                    {"role": "user", "content": final_prompt}
                ],
                stream=False
            )
            
            content = final_response.choices[0].message.content
            self.write_file_content(self.files['final'], content)
            print(f"\n{Fore.GREEN}Research completed! Results saved in {self.files['final']}{Style.RESET_ALL}")
            
        except Exception as e:
            print(f"{Fore.RED}Error generating final research: {str(e)}{Style.RESET_ALL}")
            self.log_history(f"Error generating final research: {str(e)}")

def main():
    global topic
    global numSources
    
    print(f"{Fore.GREEN}=== Research Bot Starting ==={Style.RESET_ALL}")
    bot = ResearchBot()
    topic = input(f"{Fore.CYAN}Enter research topic: {Style.RESET_ALL}")
    numSources = input(f"{Fore.CYAN}Enter the approximate number of sources you would like: {Style.RESET_ALL}")
    format_type = input(f"{Fore.CYAN}Enter desired format (e.g., academic, informal, bullet points): {Style.RESET_ALL}")
    bot.research(topic, format_type)

if __name__ == "__main__":
    main()