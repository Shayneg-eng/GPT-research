import os
from datetime import datetime
from openai import OpenAI
from googlesearch import search
import requests
from bs4 import BeautifulSoup

class ResearchSession:
    def __init__(self):
        self.topic = ''
        self.numSources = 0
        self.sourcesUsedSoFar = 0
        self.outputFormat = ''
        self.apiKey = ''
        
        self.startTime = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.baseFolder = self.createResearchFolders()
        self.client = OpenAI(api_key=self.apiKey, base_url="https://api.deepseek.com")
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def createResearchFolders(self):
        # Create path for research folder and new dated folder
        researchPath = os.path.join(os.getcwd(), 'research')
        datedFolder = os.path.join(researchPath, self.startTime)
        
        # Create research folder if it doesn't exist
        if not os.path.exists(researchPath):
            os.makedirs(researchPath)
        
        # Create dated folder
        os.makedirs(datedFolder)
        
        # List of files to create
        files = ['links.txt', 'history.txt', 'final_research.txt', 'extracted_data.txt']
        
        # Create each file
        for file in files:
            filePath = os.path.join(datedFolder, file)
            with open(filePath, 'w') as f:
                pass  # Creates empty file

        return datedFolder

    def readFile(self, fileName):
        path = os.path.join(os.getcwd(), 'research', self.startTime, fileName + '.txt')
        
        try:
            with open(path, 'r') as f:
                content = f.read()
            return content
        except FileNotFoundError:
            print(f"Error: Could not find the file {fileName}.txt")
            return None
        except Exception as e:
            print(f"Error reading file: {e}")
            return None
        
    def writeToFile(self, fileName, content):
        # Construct full path to the file using stored startTime
        researchPath = os.path.join(os.getcwd(), 'research', self.startTime, fileName + '.txt')
        
        try:
            # Read existing content first
            existingContent = ''
            try:
                with open(researchPath, 'r') as f:
                    existingContent = f.read()
            except FileNotFoundError:
                pass

            with open(researchPath, 'w') as f:
                # Write existing content if any
                if existingContent:
                    f.write(existingContent)
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
            print(f"Error: Could not find the research folder ({self.startTime})")
            return False
        except Exception as e:
            print(f"Error writing to file: {e}")
            return False

    def removeStringFromFile(self, fileName, stringToRemove):
        # Construct full path to the file using stored startTime
        researchPath = os.path.join(os.getcwd(), 'research', self.startTime, fileName + '.txt')
        
        try:
            with open(researchPath, 'r') as file:
                content = file.read()
            
            content = content.replace(stringToRemove, '')
            
            with open(researchPath, 'w') as file:
                file.write(content)
                
            return True
            
        except FileNotFoundError:
            print(f"Error: Could not find the research folder ({self.startTime})")
            return False
        except Exception as e:
            print(f"Error writing to file: {e}")
            return False

    def cleanLinksFileForDuplicates(self):
        linksFile = os.path.join(os.getcwd(), 'research', self.startTime, 'links.txt')
        seenLinks = set()
        cleanedLines = []

        with open(linksFile, 'r') as file:
            for line in file:
                strippedLine = line.strip()  # Remove leading/trailing whitespaces
                if strippedLine.startswith("http"):  # Identify links
                    if strippedLine not in seenLinks:
                        seenLinks.add(strippedLine)  # Add new link to set
                        cleanedLines.append(line)  # Preserve the line
                else:
                    # Retain blank lines or lines that are not links
                    cleanedLines.append(line)

        with open(linksFile, 'w') as file:
            file.writelines(cleanedLines)
            
    def cleanExtractedDataFileForDuplicateData(self):
        extractedDataFile = os.path.join(os.getcwd(), 'research', self.startTime, 'extracted_data.txt')
        
        # Read the current content
        with open(extractedDataFile, 'r') as file:
            current_content = file.read()
        
        # Create the prompt for cleaning duplicates
        prompt = f"""
        reorganize the data using these rules:

        1. Keep information grouped by their original links/sources
        2. When reviewing each subsequent link, remove any information that has already appeared in previous links
        3. The first occurrence of any piece of information should be preserved in its original link
        4. Continue this process through all links, ensuring each link only contains unique information not mentioned before
        5. Maintain the original source attribution for all information
        6. Do NOT write anything extra other than what you are explicitly told to 
        
        For example:
        If Link A and Link B both mention "the sky is blue", this fact would remain in Link A's section but be removed from Link B's section, since Link A mentioned it first.
        
        Here is the data: {current_content}
        """
        
        # Get cleaned content from AI
        cleaned_content = self.getAIResponse(prompt)
        
        # Write the cleaned content back to the file
        with open(extractedDataFile, 'w') as file:
            file.write(cleaned_content)

    def webSearch(self, query):
        """Perform web search and store links"""
        try:
            searchResults = list(search(query, num=12, stop=12))
            return searchResults
        except Exception as e:
            print(f"Search error: {str(e)}")
            return []

    def readWebpage(self, url):
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
    
    def checkForFinishedResearch(self):
        prompt = f"""
        
        you will check to see if the following research information is enough information to start writing a research findings paper.
        Here are the criteria you will use to make that decision:
        #1: the information has to fully answer the research question/topic: [{self.topic}]
        #2: the information has to draw from about {self.numSources} sources. it uses {self.sourcesUsedSoFar} so far.
        #3 there should be no gaps in the research. ie: the research should not have left anything out to fully address the research question/topic: [{self.topic}]
        
        If you think there is enough information you will type "__finalize__" EXACTLY as the output with no other words
        
        EX: there is enough info
        Your response: __finalize__
        
        If you think we should continue going to get more research type "continue research"
        
        here is the current research: {self.readFile('extracted_data')}
        
        Type your response now.
        
        """
        
        return self.getAIResponse(prompt)

    def getAIMainDecision(self):    
    
        prompt = f"""
        you will use the following research information files to make an informed decision about how to proceed with the current research on the topic: [{self.topic}]
        
        >> history file (this is the past stuff that has been done. DO NOT repeat the same action twice in a row):
        {self.readFile('history')}
        >> end of history file
        
        >> links file (DO NOT choose this option if you see useful links):
        {self.readFile('links')}
        >> end of links file
        
        >> data file:
        {self.readFile('extracted_data')}
        >> end of data file
        
        the structure of your response should contain the following
        
        here are your ONLY 2 options (__web_search__ , __read_link__)
        Your response will be read verbatim to search for one of the above commands so type them out exactly.
        the command contains 2 parts. Part #1 is the command itself and part #2 is the information for the command to act on. here are two examples.
        EX: __read_link__ www.dogz.com --- This should be the default command if there are links in the above links file. This will read the "www.dogz.com" website (only possible to do with the links given to you in the provided links file. If there are none you should do a web search)
        EX: __web_search__ dogs health --- ### ONLY do this if you need more websites to read or different websites to read ###       
        
        Here are 2 complete examples of responses to this prompt:
        EX #1:
        I'm not satisfied with the information I have access to regarding carbon emissions __web_search__ carbon emissions
        
        EX #2:
        I want to analyze the details on climate change effects provided in the link __read_link__ www.climate-research.org/effects
        
        ### IMPORTANT ###
        DO NOT REPEAT ACTIONS TWICE IN A ROW
        ### IMPORTANT ###
        
        make your decision now.
        """
        
        return self.getAIResponse(prompt)

    def getSummary(self, text):
        prompt = f"""
        
        Summarize the following text on the topic: {self.topic}.
        List as many bullet pointed facts as possible. Keep the facts short and concise while maintaining meaning. Prioritize quantitative over qualitative data. Source text: \n\n{text}.
        
        """
        return self.getAIResponse(prompt)

    def createMessage(self, researchNote):
        prompt = f"""
        
        Given my research on {self.topic}, convert this research note into a natural first-person statement: {researchNote}
        
        the above research note is either a link or a google search so act accordingly.

        Requirements:
        - Speak as an AI researcher investigating {self.topic}
        - Create a single sentence without final punctuation
        - Keep it concise and conversational
        - If theres a link, include it in the response
        
        here is are the past natural first-person statements. try not to repeat the same wording and try to provide new reasons each time {self.readFile('history')}

        Example input:  
        I'm not satisfied with the information I have access to regarding carbon emissions __web_search__ carbon emissions

        Example output:
        I'm not satisfied with the information I have access to regarding carbon emissions so ill search the web for it

        Please convert the research note now
        
        """
        
        return self.getAIResponse(prompt)

    def createExtractedDataHeader(self, link):
        return f'The following information derived from this source: {link}'

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
        DO not use this character "�"
        ###IMPORTANT###
        
        information:
        {self.readFile('extracted_data')}
        
        """
        
        return self.getAIResponse(prompt)
    
    def startResearch(self):
        while True:
    
            aiDecision = self.getAIMainDecision()
            parsedAIResult = ResearchSession.parseAIMessageAndCommand(aiDecision)
            
            checkForFinalize = self.checkForFinishedResearch() # dedicated finalize checker     
            
            # 1 = web search
            # 2 = read link
            # 3 = finalize
            print(self.createMessage(parsedAIResult['afterText']))
            
            self.writeToFile('history', '[Bot decision]' + parsedAIResult['beforeText'])
            
            if checkForFinalize == '__finalize__':
                self.writeToFile('final_research', self.finalize())
                break

            elif parsedAIResult['foundString'] == '__web_search__':
                self.writeToFile('links', self.webSearch(parsedAIResult['afterText']))
                self.cleanLinksFileForDuplicates()
                
            elif parsedAIResult['foundString'] == '__read_link__':
                self.sourcesUsedSoFar += 1
                self.writeToFile('extracted_data', self.createExtractedDataHeader(parsedAIResult['afterText']))
                self.writeToFile('extracted_data', self.getSummary(parsedAIResult['afterText'])) # summarize link
                self.removeStringFromFile('links', parsedAIResult['afterText']) # remove link from txt
                self.cleanExtractedDataFileForDuplicateData()
            
            else:
                print("invalid AI decision")
                pass
            
            
        print("research complete")

    @staticmethod
    def parseAIMessageAndCommand(text):
        searchString1 = '__web_search__'
        searchString2 = '__read_link__'
        
        # Initialize variables
        result = {
            'foundNumber': 0,
            'beforeText': '',
            'afterText': '',
            'foundString': ''
        }
        
        # Check for each string in order
        if searchString1 in text:
            index = text.find(searchString1)
            result['foundNumber'] = 1
            result['foundString'] = searchString1
        elif searchString2 in text:
            index = text.find(searchString2)
            result['foundNumber'] = 2
            result['foundString'] = searchString2
        else:
            return None  # None of the strings were found
        
        # Get context before the found string
        result['beforeText'] = text[0:index].strip()
        
        # Get context after the found string
        result['afterText'] = text[index + len(result['foundString']):].strip()
        
        return result



researchBot = ResearchSession()

researchBot.apiKey = 'sk-91243ea8c2584fbc888cc7ed818cc4cf'
researchBot.topic = 'History of Hamas and the PA'
researchBot.numSources = 3
researchBot.outputFormat = 'formal essay'
researchBot.startResearch()


