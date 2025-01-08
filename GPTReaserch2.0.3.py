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
        """Init bot with a given topic."""
        self.current_topic = topic.strip()
        self.visited_urls = set()
        self.search_history = set()  # Tracks completed search queries
        self.research_dir = "GPTResearch"
        self.raw_data_file = os.path.join(self.research_dir, "raw_data.txt")
        self.final_research_file = os.path.join(self.research_dir, "final_research.txt")
        self.pending_links_file = os.path.join(self.research_dir, "pending_links.txt")
        self.history_file = os.path.join(self.research_dir, "research_history.txt")
        self.action_history = []

        if not os.path.exists(self.research_dir):
            os.makedirs(self.research_dir)

        files_to_init = [
            (self.raw_data_file, f"Research started: {datetime.now()}\n\n"),
            (self.final_research_file, f"Research started: {datetime.now()}\n\n"),
            (self.pending_links_file, f"Research started: {datetime.now()}\n\n"),
            (self.history_file, f"Research History: {self.current_topic}\n")
        ]
        for path, content in files_to_init:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

        print(f"{Fore.GREEN}ResearchBot Initialized for: {self.current_topic}{Style.RESET_ALL}")

    def log_action(self, action_type, details):
        """Log an action."""
        t = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        entry = f"[{t}] {action_type}: {details}"
        self.action_history.append(entry)
        with open(self.history_file, 'a', encoding='utf-8') as f:
            f.write(entry + "\n")

    def search_web(self, query):
        """Web search, add new links to pending unless it's already been done."""
        # Skip if repeated or if we already have pending links to analyze
        if query.lower() in self.search_history:
            print(f"{Fore.YELLOW}Skipping repeated search: {query}{Style.RESET_ALL}")
            return
        if self.get_pending_links():
            print(f"{Fore.YELLOW}Skipping search. Pending links exist; analyzing them first.{Style.RESET_ALL}")
            return
        self.search_history.add(query.lower())

        self.log_action("WEB_SEARCH", f"Query: {query}")
        print(f"{Fore.GREEN}[AI] Searching web for: {query}{Style.RESET_ALL}")
        results = []
        try:
            for url in search(query, num=3, stop=3, pause=2):
                if url not in self.visited_urls:
                    results.append(url)
            if results:
                print(f"{Fore.GREEN}Found {len(results)} new links.{Style.RESET_ALL}")
                self.save_pending_links(results)
            else:
                print(f"{Fore.YELLOW}No new links found.{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Search error: {e}{Style.RESET_ALL}")
            self.log_action("ERROR", f"Search failed: {str(e)}")

    def save_pending_links(self, links):
        with open(self.pending_links_file, 'a', encoding='utf-8') as f:
            for link in links:
                f.write(link + "\n")

    def get_pending_links(self):
        if not os.path.exists(self.pending_links_file):
            return []
        with open(self.pending_links_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        return [l.strip() for l in lines if l.strip() and not l.startswith("Research started")]

    def remove_pending_link(self, link):
        all_links = self.get_pending_links()
        updated = [l for l in all_links if l != link]
        with open(self.pending_links_file, 'w', encoding='utf-8') as f:
            for l in updated:
                f.write(l + "\n")

    def analyze_link(self, url):
        """Analyze URL content via model qwen:14b."""
        url = url.strip()
        self.log_action("ANALYZE_LINK", f"URL: {url}")
        pending_links = self.get_pending_links()
        if url not in pending_links:
            self.log_action("ERROR", f"Link not in pending: {url}")
            self.search_web(self.current_topic)
            return
        if url in self.visited_urls:
            self.log_action("SKIP", f"Link already done: {url}")
            print(f"{Fore.YELLOW}Already done: {url}{Style.RESET_ALL}")
            return

        print(f"{Fore.CYAN}[AI] Analyzing: {url}{Style.RESET_ALL}")
        try:
            r = requests.get(url, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            text = " ".join([p.get_text() for p in soup.find_all(['p','h1','h2','h3','h4','h5','h6'])])
            analysis_prompt = f"""
Topic: {self.current_topic}
New Content: {url}
{text}
Extract key info for {self.current_topic}.
""".strip()
            output = ollama.chat(
                model='qwen:14b',
                messages=[{'role': 'user', 'content': analysis_prompt}]
            )
            extracted = output['message']['content'].strip()
            self.save_data(f"Source: {url}\n{extracted}\n", "raw")
            self.visited_urls.add(url)
            self.remove_pending_link(url)
            self.log_action("SUCCESS", f"Analyzed: {url}")
        except Exception as e:
            print(f"{Fore.RED}Error analyzing {url}: {e}{Style.RESET_ALL}")
            self.log_action("ERROR", f"{url} analysis fail: {str(e)}")

    def save_data(self, content, file_type):
        """Save data to raw or final."""
        file_map = {'raw': self.raw_data_file, 'final': self.final_research_file}
        path = file_map[file_type]
        try:
            with open(path, 'a', encoding='utf-8') as f:
                f.write(f"\n--- {datetime.now()} ---\n{content}\n")
            print(f"{Fore.GREEN}Saved to {os.path.basename(path)}{Style.RESET_ALL}")
            self.log_action("SAVE", f"To {os.path.basename(path)}")
        except Exception as e:
            print(f"{Fore.RED}Save error: {e}{Style.RESET_ALL}")
            self.log_action("ERROR", f"Save fail: {str(e)}")

    def compile_final_research(self):
        """Compile final summary."""
        self.log_action("FINALIZE", "Starting compilation")
        try:
            with open(self.raw_data_file, 'r', encoding='utf-8') as f:
                raw_data = f.read()
            prompt = f"""
Topic: {self.current_topic}
Raw data:
{raw_data}
Please summarize concisely.
""".strip()
            resp = ollama.chat(
                model='qwen:14b',
                messages=[{'role': 'user', 'content': prompt}]
            )
            final_summary = resp['message']['content'].strip()
            self.save_data(final_summary, 'final')
            self.log_action("SUCCESS", "Compiled final")
        except Exception as e:
            print(f"{Fore.RED}Compilation error: {e}{Style.RESET_ALL}")
            self.log_action("ERROR", f"Compile fail: {str(e)}")

    def build_ai_prompt(self):
        """Short instructions for the AI."""
        recent = "\n".join(self.action_history[-10:]) or "No actions"
        print(recent)
        try:
            with open(self.raw_data_file, 'r', encoding='utf-8') as f:
                raw_info = f.read()
        except:
            raw_info = "No raw info."
        pending = self.get_pending_links()
        pending_str = "\n".join(pending) if pending else "None"

        return f"""
Topic: {self.current_topic}
Recent Actions (do not repeat):
{recent}

Raw Info:
{raw_info}

Pending Links:
{pending_str}

INSTRUCTIONS (One line only):
1) If no pending links: --web-search-- <query>
2) If pending links exist: --analyze-link-- <exact URL>
3) If finished: --finalize--
""".strip()

    def run_autonomous_research(self):
        """Main loop."""
        self.log_action("START", f"Begin research: {self.current_topic}")
        print(f"{Fore.GREEN}Research started...{Style.RESET_ALL}")
        errs = 0
        while True:
            if errs > 2:
                print(f"{Fore.RED}Too many errors. Stopping.{Style.RESET_ALL}")
                break
            prompt = self.build_ai_prompt()
            try:
                r = ollama.chat(model='qwen:14b', messages=[{'role': 'user', 'content': prompt}])
                cmd = r['message']['content'].strip()
                if not cmd:
                    self.log_action("ERROR", "Empty cmd")
                    errs += 1
                    continue
                m = re.match(r"^--(web-search|analyze-link|finalize)--\s*(.*)$", cmd, re.IGNORECASE)
                if not m:
                    self.log_action("ERROR", f"Bad cmd: {cmd}")
                    self.search_web(self.current_topic)
                    errs += 1
                    continue
                ctype = m.group(1).lower()
                cval = m.group(2).strip()
                errs = 0

                if ctype == "web-search":
                    # If there's already pending links, prefer analyzing first
                    if self.get_pending_links():
                        print(f"{Fore.YELLOW}Skip new search; pending links present.{Style.RESET_ALL}")
                        continue
                    self.search_web(cval if cval else self.current_topic)

                elif ctype == "analyze-link":
                    self.analyze_link(cval)

                elif ctype == "finalize":
                    if not self.visited_urls:
                        self.log_action("ERROR", "No links analyzed yet")
                        self.search_web(self.current_topic)
                        continue
                    self.log_action("FINALIZE", "AI finalize")
                    print(f"{Fore.MAGENTA}[AI] Finalizing...{Style.RESET_ALL}")
                    break

            except Exception as e:
                self.log_action("ERROR", f"Main loop error: {str(e)}")
                errs += 1

        self.compile_final_research()
        self.log_action("END", "Research complete")
        print(f"{Fore.GREEN}Done. Final saved to {self.final_research_file}{Style.RESET_ALL}")

def main():
    print(f"{Fore.GREEN}=== Start Research ==={Style.RESET_ALL}")
    topic = input("Enter topic: ").strip()
    bot = ResearchBot(topic)
    bot.run_autonomous_research()
    print(f"{Fore.GREEN}=== End Research ==={Style.RESET_ALL}")

if __name__ == "__main__":
    main()