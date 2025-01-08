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
        self.history_file = os.path.join(self.research_dir, "research_history.txt")
        self.action_history = []

        # Make sure the research directory exists
        if not os.path.exists(self.research_dir):
            os.makedirs(self.research_dir)
        
        # Initialize all required files
        files_to_init = [
            (self.raw_data_file, f"Research started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"),
            (self.final_research_file, f"Research started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"),
            (self.pending_links_file, f"Research started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"),
            (self.history_file, f"Research History for topic: {self.current_topic}\n")
        ]

        for file_path, initial_content in files_to_init:
            # Clear file contents if it exists, otherwise create it
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(initial_content)

        print(f"{Fore.GREEN}ResearchBot Initialized for topic: {self.current_topic}{Style.RESET_ALL}")

    def log_action(self, action_type, details):
        """
        Log an AI action to both memory and file
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        action_entry = f"[{timestamp}] {action_type}: {details}"
        
        # Add to memory
        self.action_history.append(action_entry)
        
        # Write to file
        with open(self.history_file, 'a', encoding='utf-8') as f:
            f.write(action_entry + "\n")
        
        # print(f"{Fore.BLUE}[HISTORY] {action_entry}{Style.RESET_ALL}")

    def search_web(self, query):
        """
        Perform a web search for the given query and save new links to our pending links file.
        """
        self.log_action("WEB_SEARCH", f"Query: {query}")
        print(f"{Fore.GREEN}[AI DECISION] Searching the web for: {query}{Style.RESET_ALL}")
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
            self.log_action("ERROR", f"Search failed: {str(e)}")
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
        # Clean the URL by removing any trailing spaces
        url = url.strip()
        self.log_action("ANALYZE_LINK", f"URL: {url}")
        
        # Basic check: URL must be in pending links
        pending_links = self.get_pending_links()
        if url not in pending_links:
            self.log_action("ERROR", f"Link not in pending list: {url}")
            # Force a new web search when link is invalid
            self.search_web(self.current_topic)
            return

        if url in self.visited_urls:
            self.log_action("SKIP", f"Link already analyzed: {url}")
            print(f"{Fore.YELLOW}Link already analyzed: {url}{Style.RESET_ALL}")
            return None

        print(f"{Fore.CYAN}[AI DECISION] Analyzing link: {url}{Style.RESET_ALL}")
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
                model='qwen:14b',
                messages=[{'role': 'user', 'content': analysis_prompt}],
            )
            extracted_info = analysis_response['message']['content'].strip()

            # Save info to raw data
            self.save_data(f"Source: {url}\nExtracted Info:\n{extracted_info}\n", file_type="raw")

            # Mark as visited, remove from pending
            self.visited_urls.add(url)
            self.remove_pending_link(url)
            self.log_action("SUCCESS", f"Analyzed and extracted info from: {url}")

        except Exception as e:
            print(f"{Fore.RED}Error analyzing URL {url}: {e}{Style.RESET_ALL}")
            self.log_action("ERROR", f"Analysis failed for {url}: {str(e)}")

    def save_data(self, content, file_type):
        """
        Save content to either raw_data.txt or final_research.txt
        """
        file_map = {
            'raw': self.raw_data_file,
            'final': self.final_research_file
        }
        target_file = file_map[file_type]

        try:
            with open(target_file, 'a', encoding='utf-8') as f:
                f.write(f"\n--- New Content: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                f.write(content + "\n")
            print(f"{Fore.GREEN}Data saved to: {os.path.basename(target_file)}{Style.RESET_ALL}")
            self.log_action("SAVE", f"Saved {file_type} data to {os.path.basename(target_file)}")
        except Exception as e:
            print(f"{Fore.RED}Error saving data to {target_file}: {e}{Style.RESET_ALL}")
            self.log_action("ERROR", f"Failed to save {file_type} data: {str(e)}")

    def compile_final_research(self):
        """
        Read all raw_data.txt, then prompt the AI to create a final organized summary.
        Save it to final_research.txt.
        """
        self.log_action("FINALIZE", "Starting final compilation")
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
                model='qwen:14b',
                messages=[{'role': 'user', 'content': compile_prompt}],
            )
            final_summary = compile_response['message']['content'].strip()

            # Save to final output
            self.save_data(final_summary, 'final')
            self.log_action("SUCCESS", "Final research compiled and saved")

        except Exception as e:
            print(f"{Fore.RED}Error compiling final research: {e}{Style.RESET_ALL}")
            self.log_action("ERROR", f"Final compilation failed: {str(e)}")

    def build_ai_prompt(self):
        """
        Build the prompt telling the AI about:
        1) The current topic
        2) The action history
        3) The raw data we've collected so far
        4) The pending links
        5) Any constraints/instructions
        """
        # Add recent history (last 10 actions)
        recent_history = self.action_history[-10:] if self.action_history else ["No actions yet"]
        history_str = "\nRecent actions:\n" + "\n".join(recent_history)

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

Here is the past research actions you've taken (History):
IMPORTANT: DO NOT REPEAT ACTIONS FROM THIS LIST
###{history_str}###

Collected raw info so far:
###{raw_info}###

Pending links (only real, fully qualified URLs, e.g. https://...):
###{pending_list_str}###

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


###IMPORTANT###
1. do not repeat past actions. reference the history part of this prompt to ensure new research steps are taken.
2. Nothing else in your response. No extra text.
"""
        return autoprompt.strip()

    def run_autonomous_research(self):
        """
        Modified main loop with better error handling and retry logic
        """
        self.log_action("START", f"Beginning research on topic: {self.current_topic}")
        print(f"{Fore.GREEN}Autonomous research beginning...{Style.RESET_ALL}")
        
        consecutive_errors = 0
        max_errors = 3
        
        while True:
            try:
                # Build AI prompt
                prompt = self.build_ai_prompt()
                
                # Query the model
                response = ollama.chat(model='qwen:14b', messages=[{'role': 'user', 'content': prompt}])
                ai_command = response['message']['content'].strip()

                if not ai_command:
                    self.log_action("ERROR", "AI returned empty command")
                    consecutive_errors += 1
                    if consecutive_errors >= max_errors:
                        print(f"{Fore.RED}[ERROR] Too many consecutive errors. Stopping.{Style.RESET_ALL}")
                        break
                    continue

                # Use a regex to parse:  --XYZ-- content
                pattern = r"^--(web-search|analyze-link|finalize)--\s*(.*)$"
                match = re.match(pattern, ai_command, re.IGNORECASE)
                if not match:
                    self.log_action("ERROR", f"Malformed command: {ai_command}")
                    # Force a web search on error
                    self.search_web(self.current_topic)
                    consecutive_errors += 1
                    if consecutive_errors >= max_errors:
                        print(f"{Fore.RED}[ERROR] Too many consecutive errors. Stopping.{Style.RESET_ALL}")
                        break
                    continue

                cmd_type = match.group(1).lower()
                cmd_content = match.group(2).strip()

                # Reset error counter on successful command parse
                consecutive_errors = 0
                
                if cmd_type == "web-search":
                    if not cmd_content or cmd_content.lower() in ["<some real, relevant query>", ""]:
                        self.log_action("ERROR", "Empty search query")
                        self.search_web(self.current_topic)  # Fall back to topic search
                        continue
                    self.search_web(cmd_content)

                elif cmd_type == "analyze-link":
                    if not cmd_content.startswith("http"):
                        self.log_action("ERROR", "Invalid URL format")
                        self.search_web(self.current_topic)  # Fall back to topic search
                        continue
                    self.analyze_link(cmd_content)

                elif cmd_type == "finalize":
                    if not self.visited_urls:  # Check if we've analyzed any URLs
                        self.log_action("ERROR", "Attempting to finalize without analyzing any links")
                        self.search_web(self.current_topic)
                        continue
                    self.log_action("FINALIZE", "AI decided to finish research")
                    print(f"{Fore.MAGENTA}[AI DECISION] Finalizing research...{Style.RESET_ALL}")
                    break

            except Exception as e:
                self.log_action("ERROR", f"Unexpected error: {str(e)}")
                consecutive_errors += 1
                if consecutive_errors >= max_errors:
                    print(f"{Fore.RED}[ERROR] Too many consecutive errors. Stopping.{Style.RESET_ALL}")
                    break
                continue

        # Compile final research
        self.compile_final_research()
        self.log_action("END", "Research completed")
        print(f"{Fore.GREEN}Autonomous research completed. Final output saved to {self.final_research_file}{Style.RESET_ALL}")

def main():
    print(f"{Fore.GREEN}=== Starting Autonomous Research Session ==={Style.RESET_ALL}")
    topic = input("Enter your research topic: ").strip()
    bot = ResearchBot(topic)
    bot.run_autonomous_research()
    print(f"{Fore.GREEN}=== Research Session Complete ==={Style.RESET_ALL}")

if __name__ == "__main__":
    main()