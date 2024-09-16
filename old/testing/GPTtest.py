import requests


def chatgpt_api_call(api_key, organization_code, message):
    url = "https://api.openai.com/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "Openai-Organization": organization_code,
    }
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "system", "content": 
                    '''" CONTEXT ### you are a web assistant"'''}
                     , {"role": "user", "content": message}],
    }

    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"Error: {response.status_code}, {response.text}"

# Replace these with your actual API key and organization code
api_key = "......."
organization_code = "......."


for i in range(5):
    userMessage = input("enter text: ")
    response = chatgpt_api_call(api_key, organization_code, userMessage)
    print(response)
    