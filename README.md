# GPT-research

A research agent that runs on its own. You give it a topic, and it loops: decide what to do next, search Google or read a page, pull out the facts, repeat. Once it decides it has enough, it writes the whole thing up with numbered citations.

Every version is still in here, from a 100-line script that pasted one Google result into ChatGPT up to the agent loop in 5.0.1, so you can watch it develop.

## How the latest version works (`GPTResearch5.0.1.py`)

Each research run gets its own timestamped folder under `research/` with four text files that act as the agent's memory:

| File | What goes in it |
|---|---|
| `history.txt` | Every decision the agent has made, so it doesn't repeat itself |
| `links.txt` | Search results it hasn't read yet (deduplicated) |
| `extracted_data.txt` | Bullet-point facts pulled from each page it read, grouped by source |
| `final_research.txt` | The finished write-up |

Every turn, the model sees all of that and answers with one of two commands, `__web_search__ <query>` or `__read_link__ <url>`. The script parses the command and runs it. A separate check asks whether the research fully answers the question with roughly the number of sources you asked for. Once it does, the agent writes the final document in whatever format you chose ("formal essay", for example), citing sources as (1), (2,3) and so on, with a reference list at the end.

Two parts I'm still happy with. After each new source, the extracted notes get passed back through the model to remove facts an earlier source already covered, so the notes don't balloon. And the summarizer is told to prefer numbers over vague statements, which made the final papers a lot less fluffy.

## How it got here

| Version | What changed |
|---|---|
| 1.0.0 | Google search, scrape the top result with BeautifulSoup, send it to the ChatGPT API |
| 1.1.0 | Switched to a local model (Llama 3.1 through Ollama) and added a check for whether the research is done |
| 2.0.x | Mistral, a queue of pending links, and a separate step that extracts the key facts from each page |
| 3.0.0 | Rewrote it as small functions, tried Qwen 14B, and had the model filter out pages that weren't on topic |
| 4.x | Moved to the DeepSeek API. The local models I could run weren't reliable enough at following a strict output format |
| 5.0.x | The command-based agent loop described above |

Older experiments (the first ChatGPT test, a PDF reader, a search test) are in `old/testing/`.

## Running it

```bash
pip install openai google requests beautifulsoup4
```

Set your DeepSeek API key and research topic at the bottom of `GPTResearch5.0.1.py`, then:

```bash
python GPTResearch5.0.1.py
```

Versions 1.1 through 3.0 need [Ollama](https://ollama.com) running locally with the model named in the file.
