import os
from datetime import datetime
from openai import OpenAI
from googlesearch import search
import requests
from bs4 import BeautifulSoup

def parseAIMessageAndCommand(text):
    
    search_string1 = '__web_search__'
    search_string2 = '__read_link__'
    search_string3 = '__finalize__'
    
    # Initialize variables
    result = {
        'found_number': 0,
        'before_text': '',
        'after_text': '',
        'found_string': ''
    }
    
    # Check for each string in order
    if search_string1 in text:
        index = text.find(search_string1)
        result['found_number'] = 1
        result['found_string'] = search_string1
    elif search_string2 in text:
        index = text.find(search_string2)
        result['found_number'] = 2
        result['found_string'] = search_string2
    elif search_string3 in text:
        index = text.find(search_string3)
        result['found_number'] = 3
        result['found_string'] = search_string3
    else:
        return None  # None of the strings were found
    
    # Get context before the found string
    result['before_text'] = text[0:index].strip()
    
    # Get context after the found string
    result['after_text'] = text[index + len(result['found_string']):].strip()
    
    return result

class ResearchSession:
    def __init__(self):
        self.topic = ''
        self.numSources = 0
        self.sourcesUsedSoFar = 0
        self.outputFormat = ''
        
        self.start_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.base_folder = self.create_research_folders()
        self.client = OpenAI(api_key='sk-91243ea8c2584fbc888cc7ed818cc4cf', base_url="https://api.deepseek.com")
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
    def createExtractedDataHeader(self, link):
        return f'The following information derived from this source: {link}'
    
    def getAIMainDecision(self):    
        prompt = f"""
        
        you will use the following research information files to make an informed decision about how to proceed with the current research on the topic: [{self.topic}]
        
        >> links file (be very selective about the links you use. only use reputable sources):
        {self.read_file('links')}
        >> end of links file
        
        >> data file:
        {self.read_file('extracted_data')}
        >> end of data file
        
        >> history file (this is the past stuff has been done. DO NOT repeat the same action twice in a row):
        {self.read_file('history')}
        >> end of history file
        
        the structure of your response should contain the following 2 parts:
        
        
        the first part is a short one line explanation for your decision. Vary what you say based on what you said in the past located in the history file.
        EX: "I need more information on the main topic so I will do another websearch"
        
        the second part is decision command. here are your ONLY 3 options (__web_search__ , __read_link__ , __finalize__)
        Your response will be read verbatim to search for one of the above commands so type them out exactly
        the decision command contains 2 parts #1 the command itself and #2 the information for the command to act on. here are three examples.
        EX: __read_link__ www.dogz.com --- this will read the "www.dogz.com" website (only possible to do with the links given to you in the provided links file. If there are none you should do a web search)
        EX: __web_search__ dogs health --- ONLY do this if you need more websites to read or different websites to read
        EX: __finalize__ --- this option finalizes all the research. You cant choose this option until you have used {self.numSources} sources. currently you have used {self.sourcesUsedSoFar} sources.
        
        
        Here are 3 complete examples of responses to this prompt:
        EX #1:
        I'm not satisfied with the information I have access to regarding carbon emissions __web_search__ carbon emissions
        
        EX #2:
        I want to analyze the details on climate change effects provided in the link __read_link__ www.climate-research.org/effects

        EX #4:
        I have enough data to finalize the research on sustainable farming practices __finalize__
        
        make your decision now.
        """
        
        return self.getAIResponse(prompt)
        
    def create_research_folders(self):
        # Create path for research folder and new dated folder
        research_path = os.path.join(os.getcwd(), 'research')
        dated_folder = os.path.join(research_path, self.start_time)
        
        # Create research folder if it doesn't exist
        if not os.path.exists(research_path):
            os.makedirs(research_path)
        
        # Create dated folder
        os.makedirs(dated_folder)
        
        # List of files to create
        files = ['links.txt', 'history.txt', 'final_research.txt', 'extracted_data.txt']
        
        # Create each file
        for file in files:
            file_path = os.path.join(dated_folder, file)
            with open(file_path, 'w') as f:
                pass  # Creates empty file

        return dated_folder

    def writeToFile(self, file_name, content):
        # Construct full path to the file using stored start_time
        research_path = os.path.join(os.getcwd(), 'research', self.start_time, file_name + '.txt')
        
        try:
            # Read existing content first
            existing_content = ''
            try:
                with open(research_path, 'r') as f:
                    existing_content = f.read()
            except FileNotFoundError:
                pass

            with open(research_path, 'w') as f:
                # Write existing content if any
                if existing_content:
                    f.write(existing_content)
                    f.write('\n\n')  # Skip two lines
                    
                # If content is a list, write numbered lines
                if isinstance(content, list):
                    for i, item in enumerate(content, 1):
                        f.write(f"{i}: {item}\n")
                # Otherwise write content normally
                else:
                    f.write(content + '\n')
            return True
        except FileNotFoundError:
            print(f"Error: Could not find the research folder ({self.start_time})")
            return False
        except Exception as e:
            print(f"Error writing to file: {e}")
            return False

    def getAIResponse(self, prompt):
        
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a research assistant doing the next step of research"},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )
        return response.choices[0].message.content
    
    def getSummary(self, text):
        prompt = f"""
        Summarize the following text on the topic: {self.topic}.
        list as many bullet pointed facts as possible. keep the facts short and concise while maintaining meaning. Source text: \n\n{text}.
        """
        return self.getAIResponse(prompt)
    
    def finalize(self):

        prompt = f"""
        Using all the provided information below, create a document in [{self.outputFormat}] format.
        
        Citation Guidelines:
        1. Reference sources using numbered citations in parentheses
        2. Place citations immediately after the relevant information
        3. Use multiple numbers for multiple sources: (1,2)
        4. Include a numbered reference list at the end
        
        Example format for citations:

        dogs are great pets because dogs have four legs (3)
        dogs are the coolest animal with four legs (3,4) and they can even help humans without vision (1)

        References:
        1. animalhelp.com
        2. doghealth.com
        3. doglegs.com
        4. dogsarethecoolest.com
        
        ###IMPORTANT###
        >>> make sure that the citations correspond to the actual source you link at the bottom. <<<
        ###IMPORTANT###
        
        information:
        {self.read_file('extracted_data')}
        
        """
        
        return self.getAIResponse(prompt)

    # For use within the ResearchSession class, you would add:
    def read_file(self, file_name):
        path = os.path.join(os.getcwd(), 'research', self.start_time, file_name + '.txt')
        
        try:
            with open(path, 'r') as f:
                content = f.read()
            return content
        except FileNotFoundError:
            print(f"Error: Could not find the file {file_name}.txt")
            return None
        except Exception as e:
            print(f"Error reading file: {e}")
            return None
        
    def cleanLinksFileForDuplicates(self):

        linksFile = os.path.join(os.getcwd(), 'research', self.start_time, 'links.txt')
        seen_links = set()
        cleaned_lines = []

        with open(linksFile, 'r') as file:
            for line in file:
                stripped_line = line.strip()  # Remove leading/trailing whitespaces
                if stripped_line.startswith("http"):  # Identify links
                    if stripped_line not in seen_links:
                        seen_links.add(stripped_line)  # Add new link to set
                        cleaned_lines.append(line)  # Preserve the line
                else:
                    # Retain blank lines or lines that are not links
                    cleaned_lines.append(line)

        with open(linksFile, 'w') as file:
            file.writelines(cleaned_lines)
            
    def remove_string_from_file(self, file_name, string_to_remove):
        # Construct full path to the file using stored start_time
        research_path = os.path.join(os.getcwd(), 'research', self.start_time, file_name + '.txt')
        
        try:
            with open(research_path, 'r') as file:
                content = file.read()
            
            content = content.replace(string_to_remove, '')
            
            with open(research_path, 'w') as file:
                file.write(content)
                
            return True
            
        except FileNotFoundError:
            print(f"Error: Could not find the research folder ({self.start_time})")
            return False
        except Exception as e:
            print(f"Error writing to file: {e}")
            return False

    def web_search(self, query):
        """Perform web search and store links"""
        try:
            search_results = list(search(query, num=30, stop=30))
            return search_results
        except Exception as e:
            print(f"Search error: {str(e)}")
            return []

    def read_webpage(self, url):
        try:
            # Make request to webpage
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
                
            # Get text content
            text = soup.get_text()
            
            # Clean up text (remove extra whitespace)
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
        except requests.RequestException as e:
            print(f"Error fetching webpage: {e}")
            return None
        except Exception as e:
            print(f"Error processing webpage: {e}")
            return None
        
    def createMessage(self, researchNote):
        prompt = f"""
        
        Given my research on {self.topic}, convert this research note into a natural first-person statement: {researchNote}

        Requirements:
        - Speak as an AI researcher investigating {self.topic}
        - Create a single sentence without final punctuation
        - Keep it concise and conversational
        - If theres a link, include it in the response

        Example input:  
        I'm not satisfied with the information I have access to regarding carbon emissions __web_search__ carbon emissions

        Example output:
        I'm not satisfied with the information I have access to regarding carbon emissions so ill search the web for it

        Please convert the research note now
        
        """
        
        return self.getAIResponse(prompt)




researchBOT = ResearchSession()


researchBOT.topic = 'population transfer (of Arabs and Jews) theory during the 1948 war in israel'
researchBOT.numSources = 7
researchBOT.outputFormat = 'bullet points'

links = researchBOT.web_search(researchBOT.topic)


while True:
    
    AIDecision = researchBOT.getAIMainDecision()
    parsedAIResult = parseAIMessageAndCommand(AIDecision)
    
    # 1 = web search
    # 2 = read link
    # 3 = finalize
    print(researchBOT.createMessage(parsedAIResult['before_text'] + " -- " + parsedAIResult['after_text']))
    
    researchBOT.writeToFile('history', '[Bot decision]' + parsedAIResult['before_text'])

    if parsedAIResult['found_string'] == '__web_search__':
        researchBOT.writeToFile('links', researchBOT.web_search(parsedAIResult['after_text']))
        researchBOT.cleanLinksFileForDuplicates()
        
    elif parsedAIResult['found_string'] == '__read_link__':
        researchBOT.sourcesUsedSoFar += 1
        researchBOT.writeToFile('extracted_data', researchBOT.createExtractedDataHeader(parsedAIResult['after_text']))
        researchBOT.writeToFile('extracted_data', researchBOT.getSummary(parsedAIResult['after_text'])) # summarize link
        researchBOT.remove_string_from_file('links', parsedAIResult['after_text']) # remove link from txt
        
    elif parsedAIResult['found_string'] == '__finalize__':
        researchBOT.writeToFile('final_research', researchBOT.finalize())
        break
    
    else:
        print("invalid AI decision")
        pass
        
        
print("research complete")
