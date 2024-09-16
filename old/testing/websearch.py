from googlesearch import search

def get_top_links(query, num=10):
    try:
        # Perform a Google search and get the top links
        search_results = search(query, num=num, stop=num, pause=2)
        
        # Print the links
        for index, link in enumerate(search_results, start=1):
            print(f"{index}. {link}")

    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage
search_query = "dog"
get_top_links(search_query)