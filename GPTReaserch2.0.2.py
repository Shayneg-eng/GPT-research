import re
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
    def __init__(self, topic):
        """
        Initialize the ResearchBot with a specific research topic.
        This is the only user input required.
        """
        self.current_topic = topic.strip()
        self.visited_urls = set()
        self.research_dir = "GPTResearch"
        self.raw_data_file = os.path.join(self.research_dir, "raw_data.txt")
        self.final_research_file = os.path.join(self.research_dir, "final_research.txt")
        self.pending_links_file = os.path.join(self.research_dir, "pending_links.txt")

        # Make sure the research directory and files exist
        if not os.path.exists(self.research_dir):
            os.makedirs(self.research_dir)
        
        for file_path in [self.raw_data_file, self.final_research_file, self.pending_links_file]:
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"Research started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        print(f"{Fore.GREEN}ResearchBot Initialized for topic: {self.current_topic}{Style.RESET_ALL}")

    def save_data(self, content, file_type="raw"):
        """
        Save given text to the appropriate file (either raw_data_file or final_research_file).
        """
        if file_type == "raw":
            target_file = self.raw_data_file
        elif file_type == "final":
            target_file = self.final_research_file
        else:
            # Default case, just treat as raw
            target_file = self.raw_data_file

        with open(target_file, 'a', encoding='utf-8') as f:
            f.write(content + "\n")

    def search_web(self, query):
        """
        Perform a web search for the given query and save new links to our pending links file.
        """
        thought = ollama.chat(
            model='mistral',
            messages=[{'role': 'user', 'content': f"In one brief sentence, explain why you want to search for '{query}' when researching {self.current_topic}"}]
        )
        print(f"{Fore.GREEN}[AI DECISION] {thought['message']['content']}")
        print(f"{Fore.GREEN}Searching the web for: {query}{Style.RESET_ALL}")
        results = []
        try:
            for url in search(query, num=3, stop=3, pause=2):
                # Only keep fresh links
                if url not in self.visited_urls:
                    results.append(url)
            if results:
                print(f"{Fore.GREEN}Found {len(results)} new links. Adding them to pending_links.txt{Style.RESET_ALL}")
                self.save_pending_links(results)
            else:
                print(f"{Fore.YELLOW}No new links found for query: {query}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Search error: {e}{Style.RESET_ALL}")
        return results

    def save_pending_links(self, links):
        """
        Append newly found links to the pending_links file.
        """
        with open(self.pending_links_file, 'a', encoding='utf-8') as f:
            for link in links:
                f.write(link + "\n")

    def get_pending_links(self):
        """
        Return all pending links from the pending_links.txt file that haven't been visited yet.
        """
        if not os.path.exists(self.pending_links_file):
            return []
        with open(self.pending_links_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        links = [l.strip() for l in lines if l.strip() and not l.startswith("Research started")]
        return links

    def remove_pending_link(self, link):
        """
        Once visited, remove link from the pending_links file.
        """
        all_links = self.get_pending_links()
        updated_list = [l for l in all_links if l != link]
        with open(self.pending_links_file, 'w', encoding='utf-8') as f:
            for l in updated_list:
                f.write(l + "\n")

    def analyze_link(self, url):
        """
        Fetch the URL content, parse it, then use the ollama model to extract info.
        The extracted info is appended to raw_data.txt.
        """
        # Basic check: URL must be in pending links
        pending_links = self.get_pending_links()
        if url not in pending_links:
            return

        if url in self.visited_urls:
            print(f"{Fore.YELLOW}Link already analyzed: {url}{Style.RESET_ALL}")
            return None

        thought = ollama.chat(
            model='qwen:14b',
            messages=[{'role': 'user', 'content': f"In one brief sentence, explain why you want to analyze this link: {url} for research about {self.current_topic}"}]
        )
        print(f"{Fore.CYAN}[AI DECISION] {thought['message']['content']}")
        print(f"{Fore.CYAN}Analyzing link: {url}{Style.RESET_ALL}")
        
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            text = " ".join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])])
            
            analysis_prompt = f"""
    You're researching the topic: {self.current_topic}

    Here is some new content from {url}:
    {text}

    Please extract the most important information: facts, dates, key figures, or any relevant details for {self.current_topic}.
    """
            analysis_response = ollama.chat(
                model='mistral',
                messages=[{'role': 'user', 'content': analysis_prompt}],
            )
            extracted_info = analysis_response['message']['content'].strip()

            # Save info to raw data
            self.save_data(f"Source: {url}\nExtracted Info:\n{extracted_info}\n", file_type="raw")

            # Mark as visited, remove from pending
            self.visited_urls.add(url)
            self.remove_pending_link(url)

        except Exception as e:
            print(f"{Fore.RED}Error analyzing URL {url}: {e}{Style.RESET_ALL}")

    def compile_final_research(self):
        """
        Read all raw_data.txt, then prompt the AI to create a final organized summary.
        Save it to final_research.txt.
        """
        try:
            with open(self.raw_data_file, 'r', encoding='utf-8') as f:
                raw_content = f.read()

            compile_prompt = f"""
You have collected these pieces of raw data and notes about the topic: {self.current_topic}.
Below is all the raw text you collected:

{raw_content}

Please provide a concise yet comprehensive final summary, focusing on the most important details for {self.current_topic}.
"""
            compile_response = ollama.chat(
                model='mistral',
                messages=[{'role': 'user', 'content': compile_prompt}],
            )
            final_summary = compile_response['message']['content'].strip()

            # Save to final output
            self.save_data(final_summary, 'final')

        except Exception as e:
            print(f"{Fore.RED}Error compiling final research: {e}{Style.RESET_ALL}")

    def build_ai_prompt(self):
        """
        Build the prompt telling the AI about:
        1) The current topic
        2) The raw data we've collected so far
        3) The pending links
        4) Any constraints/instructions
        """
        # Get raw data (for reference)
        try:
            with open(self.raw_data_file, 'r', encoding='utf-8') as f:
                raw_info = f.read()
        except:
            raw_info = "No raw info collected yet."

        # Pending links
        pending_links = self.get_pending_links()
        pending_list_str = "\n".join(pending_links) if pending_links else "No pending links"

        # Give very explicit guidelines to the AI
        autoprompt = f"""
You are a Research Assistant working on the topic: [{self.current_topic}]

Collected raw info so far:
{raw_info}

Pending links (only real, fully qualified URLs, e.g. https://...):
{pending_list_str}

INSTRUCTIONS:

If there are NO pending links, you must do: --web-search-- <some real, relevant query>
Example: --web-search-- best dog breeds
If there ARE pending links, you may analyze one of them with: --analyze-link-- <exact URL from the list above>
Use the exact link (complete with https://).
Or if you are done collecting info, use: --finalize--
Only respond with EXACTLY one line in the format:
--COMMAND-- <content>

Examples:
--web-search-- best dog breeds
--analyze-link-- https://www.akc.org/dog-breeds/
--finalize--

Nothing else in your response. No extra text.
"""
        return autoprompt.strip()

    def run_autonomous_research(self):
        """
        The main loop:
         1) Build a prompt for the AI to decide what to do next.
         2) Parse the command from the AI (web-search, analyze-link, finalize).
         3) Execute the command.
         4) Repeat until AI says "finalize," then compile final data.
        """
        print(f"{Fore.GREEN}Autonomous research beginning...{Style.RESET_ALL}")
        while True:
            # Build AI prompt
            prompt = self.build_ai_prompt()
            
            # Query the model
            response = ollama.chat(model='qwen:14b', messages=[{'role': 'user', 'content': prompt}])
            ai_command = response['message']['content'].strip()

            if not ai_command:
                print(f"{Fore.RED}[ERROR] AI returned empty command. Stopping.{Style.RESET_ALL}")
                break

            # Use a regex to parse:  --XYZ-- content
            pattern = r"^--(web-search|analyze-link|finalize)--\s*(.*)$"
            match = re.match(pattern, ai_command, re.IGNORECASE)
            if not match:
                continue

            cmd_type = match.group(1).lower()     # web-search or analyze-link or finalize
            cmd_content = match.group(2).strip()  # The remainder  
            
            if cmd_type == "web-search":
                # Make sure there's actual content
                if not cmd_content or cmd_content.lower() in ["<some real, relevant query>", ""]:
                    print(f"{Fore.RED}[ERROR] AI gave an empty or placeholder search query.{Style.RESET_ALL}")
                    break
                self.search_web(cmd_content)

            elif cmd_type == "analyze-link":
                # Must be a pending link. Also must be a full URL (at least starts with http)
                if not cmd_content.startswith("http"):
                    print(f"{Fore.RED}[ERROR] AI gave a link that doesn't start with http(s).{Style.RESET_ALL}")
                    break
                self.analyze_link(cmd_content)

            elif cmd_type == "finalize":
                print(f"{Fore.MAGENTA}[AI DECISION] Finalizing research...{Style.RESET_ALL}")
                break

        # Compile final research
        self.compile_final_research()
        print(f"{Fore.GREEN}Autonomous research completed. Final output saved to {self.final_research_file}{Style.RESET_ALL}")

def main():
    print(f"{Fore.GREEN}=== Starting Autonomous Research Session ==={Style.RESET_ALL}")
    topic = input("Enter your research topic: ").strip()
    bot = ResearchBot(topic)
    bot.run_autonomous_research()
    print(f"{Fore.GREEN}=== Research Session Complete ==={Style.RESET_ALL}")

if __name__ == "__main__":
    main()