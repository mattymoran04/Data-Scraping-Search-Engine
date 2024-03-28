from flask import Flask, render_template, request, redirect, url_for
from duckduckgo_search import DDGS
from search_engines import Yahoo
import search_engines.results
from openai import OpenAI
import json
import os
import requests
from bs4 import BeautifulSoup

client = OpenAI()
engine = Yahoo()
res = search_engines.results

#creating a Flask application instance
app = Flask(__name__)

#Welcome page, with a link to the search page
@app.route('/')
def index():
    return '<title>Search Engines Data Scraper</title> <h1>Welcome!</h1> <p><a href="/search">Perform a DuckDuckGo Search</a><br><a href="/browse">Browse Files</a></p>'

@app.route('/browse')
def browse():
    # Get the path from the request arguments, defaulting to a specific directory
    path = request.args.get('path', r"C:\Users\matty\OneDrive\Documents\CSC1028\jsonFiles")
    
    # Initialize an empty list to store directory contents
    contents = []
    
    # Get the list of files and directories in the specified path
    files = os.listdir(path)
    
    # Iterate over each item in the directory
    for item in files:
        # Create the full path of the item
        item_path = os.path.join(path, item)
        
        # Check if the item is a directory
        if os.path.isdir(item_path):
            # If it's a directory, add it to the contents list with type 'directory'
            contents.append({'name': item, 'type': 'directory'})
        # Check if the item is a JSON file
        elif item.endswith('.json'):
            # If it's a JSON file, add it to the contents list with type 'json'
            contents.append({'name': item, 'type': 'json'})
    
    # Render the 'browse.html' template with the contents and current path
    return render_template('browse.html', contents=contents, current_path=path)


@app.route('/view_json_file/<path:filename>')
def view_json_file(filename):
    # Construct the full path to the JSON file
    json_file_path = os.path.join(request.args.get('path'), filename)
    with open(json_file_path, 'r') as file:
        json_data = json.load(file)
    return render_template('view_json_file.html', filename=filename, json_data=json_data)

#This function handles search requests
@app.route('/search', methods=['GET', 'POST'])
def search():
    #if the user submits a search request
    if request.method == 'POST':
        #get the search type and query from the submitted form
        search_type = request.form.get('search_type')
        search_query = request.form.get('query')

        #if it's a search for a person, 
        if search_type == 'person':
            return redirect(url_for('specific_queries', query=search_query, search_type=search_type))
        #if it's a search for a business
        elif search_type == 'business':
           return redirect(url_for('specific_queries', query=search_query, search_type=search_type))
        else:
           #return an error message if the search type is invalid
           search_results = {"error": "Invalid search type"}

        #render the results.html template with the search query and results
        return render_template('results.html', query=search_query, display=search_results)
    #render the search.html template if the request method is GET
    return render_template('search.html')

@app.route('/specific_queries/<query>/<search_type>', methods=['GET', 'POST'])
def specific_queries(query, search_type):
    if request.method == 'POST':
        #Get the selected query from the form and redirect to the display_results route
        selected_query = request.form.get('selected_query')
        return redirect(url_for('display_results', query=selected_query, search_type=search_type))
    elif request.method == 'GET':
        #Depending on the search type, generate results and render the specific_queries.html template
        if search_type == 'person':
            people = generateResults(query, search_type)
            return render_template('specific_queries.html', query=query, people=people, search_type=search_type)
        elif search_type == 'business':
            businesses = generateResults(query, search_type)
            return render_template('specific_queries.html', query=query, businesses=businesses, search_type=search_type)


@app.route('/display_results/<query>/<search_type>')
def display_results(query, search_type):
    #Depending on the search type, generate results and render the results.html template
    if search_type == 'person':
        results = person_query(query)
    elif search_type == 'business':
        results = business_query(query)
    return render_template('results.html', query=query, display=results, search_type=search_type)

def split_string_with_overlap(input_string):
    #Define chunk size and overlap
    chunk_size = 60000 #Max size of each chunk
    overlap = 1000 #Number of characters to overlap between chunks

    #Initialize an empty list to store the chunks
    chunks = []

    #Start index of the current chunk
    start_idx = 0
    
    #Iterate over the input string until the end
    while start_idx < len(input_string):
        #Calculate the end index of the current chunk
        end_idx = min(start_idx + chunk_size, len(input_string))

        #Extract the chunk from the input string and append it to the list
        chunks.append(input_string[start_idx:end_idx])

        #Move the start index to the beginning of the next chunk, considering the overlap
        start_idx += chunk_size - overlap
    
    #Return the list of chunks
    return chunks

# This function generates search results based on the query and search type (person or business)
def generateResults(query, search_type):
    #If the search type is 'person'
    if search_type == 'person':
        #Initialize variables
        fullResults = []
        people = []
        returnedData = []
    
        #Try searching Britannica for profiles of people
        try:
            results = engine.search("site:britannica.com " + query, max_results=10)
            srs = res.SearchResults(results)
            title = srs.titles()
            text = srs.text()
            urls = srs.links()
    
            #Loop through search results and filter by URL pattern
            for i in range(len(srs)):
                varstr = title[i] + "|" + text[i]
                #This keyword means that it is a profile page, and not posts aboout the person
                #This means that we are given more concise search queries for the person, and not numerous
                # for the same person
                if "/biography/" in urls[i]:
                    fullResults.append(varstr)
        except Exception as e:
            print(str(e))

        #Same thing as above for music artists through genius.com
        try:
            results = engine.search("site:genius.com " + query, max_results=10)
            srs = res.SearchResults(results)
            title = srs.titles()
            text = srs.text()
            urls = srs.links()
    
            for i in range(len(srs)):
                varstr = title[i] + "|" + text[i]
                if "/artists/" in urls[i]:
                    fullResults.append(varstr)
        except Exception as e:
            print(str(e))

        #Same thing as above for footballers, through transfermarkt.co.uk
        try:
            results = engine.search("site:transfermarkt.co.uk " + query, max_results=10)
            srs = res.SearchResults(results)
            title = srs.titles()
            text = srs.text()
            urls = srs.links()
    
            for i in range(len(srs)):
                varstr = title[i] + "|" + text[i]
                if "/profile/" in urls[i]:
                    fullResults.append(varstr)
        except Exception as e:
            print(str(e))

        #Same thing as above for actors and actresses, through imdb.com
        try:
            results = engine.search("site:imdb.com " + query, max_results=10)
            srs = res.SearchResults(results)
            title = srs.titles()
            text = srs.text()
            urls = srs.links()
    
            for i in range(len(srs)):
                varstr = title[i] + "|" + text[i]
                if "/name/" in urls[i]:
                    fullResults.append(varstr)
        except Exception as e:
            print(str(e))

        #Same thing as above for jobs, most people with professional jobs will have a linkedin account
        try:
            results = engine.search("site:linkedin.com " + query, max_results=10)
            srs = res.SearchResults(results)
            title = srs.titles()
            text = srs.text()
            urls = srs.links()
    
            for i in range(len(srs)):
                varstr = title[i] + "|" + text[i]
                if "/in/" in urls[i]:
                    fullResults.append(varstr)
        except Exception as e:
            print(str(e))
                    
        #Process each result to exrtact name and description
        for r in fullResults:
            varstr = r.split('|')
            name = varstr[0]
            description = varstr[1]
            full = name + " " + description
            people.append(full)
        
        #Initialize list to store AI-generated responses
        returnedData = []

        #Generate AI responses for each person
        for p in people:
            completion = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role":"system", "content": "You are an expert at creating a short sentence which summarises a small body of text to tell the user who they are" +
                        "(what their profession is). The format of the return would be something like: 'Donald Trump - Former President of the U.S.A'"},
                        {"role": "user", "content": "" + p}
                    ]
                )
            resultAI = completion.choices[0].message.content
            returnedData.append(resultAI)

        return returnedData
    
    #If the search type is 'business'
    elif search_type == 'business':
        #Initialize variables
        fullResults = []
        businesses = []
        returnedData = []

        #Try searching LinkedIn for specific companies
        try:
            results = engine.search("site:linkedin.com " + query, max_results=10)
            srs = res.SearchResults(results)
            title = srs.titles()
            text = srs.text()
            urls = srs.links()
    
            #Loop through search results and filter by URL pattern
            for i in range(len(srs)):
                varstr = title[i] + "|" + text[i]
                #If this keyword is in link, it is the profile for a company
                if "/company/" in urls[i]:
                    fullResults.append(varstr)
        except Exception as e:
            print(str(e))

        #Process each result to extract name and description
        for r in fullResults:
            varstr = r.split('|')
            name = varstr[0]
            description = varstr[1]
            full = name + " " + description
            businesses.append(full)

        #Initialize list to store AI-generated responses
        returnedData = []

        #Generate AI responses for each business
        for b in businesses:
            completion = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role":"system", "content": "You are an expert at creating a short sentence which summarises a small body of text to tell the user a business' name" +
                        " and what they do. The format of the return would be something like: 'ASDA - Supermarket Chain'"},
                        {"role": "user", "content": "" + b}
                    ]
                )
            resultAI = completion.choices[0].message.content
            returnedData.append(resultAI)
            
        return returnedData
    
# This function finds the folder path in which to store data based on a given SIC code.
def find_SIC_section_path(sicCode):
    # Define the path to the directory where folders containing data for different SIC code sections are stored.
    folder_path = r"C:\Users\matty\OneDrive\Documents\CSC1028\jsonFiles\business"
    
    # List all the subfolders (SIC code sections) in the specified directory.
    subfolders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
    
    # Initialize an empty string to store the name of the folder corresponding to the given SIC code.
    pathName = ""
    
    # Iterate through each subfolder (SIC code section) to find the one that matches the given SIC code.
    for folder in subfolders:
        # Extract the range of SIC codes from the folder name.
        numRange = folder.split(" - ")
        # Split the range into two numbers.
        numbers = numRange[0].split("-")
        # Check if the given SIC code falls within the range of SIC codes for this folder.
        if sicCode >= int(numbers[0]) and sicCode <= int(numbers[1]):
            # If the SIC code is within the range, store the folder name and exit the loop.
            pathName = folder
            break
    
    # Combine the folder path with the folder name to get the final folder path.
    finalFolder = os.path.join(folder_path, pathName)
    
    # Return the final folder path.
    return finalFolder

# This function finds the folder name containing data for a specific SIC code within a given directory.
def find_SIC_code(fPath, sicCode):
    # List all the subfolders (SIC code sections) in the specified directory.
    subfolders = [f for f in os.listdir(fPath) if os.path.isdir(os.path.join(fPath, f))]
    
    # Initialize an empty string to store the name of the folder corresponding to the given SIC code.
    pathName = ""
    
    # Iterate through each subfolder (SIC code section) to find the one that matches the given SIC code.
    for folder in subfolders:
        # Split the folder name to extract the SIC code.
        number = folder.split(" - ")
        # Check if the SIC code matches the given SIC code.
        if sicCode == number[0]:
            # If the SIC code matches, store the folder name and exit the loop.
            pathName = folder
    
    # Return the folder name corresponding to the given SIC code.
    return pathName


def person_query(query):
    #Split the query into individual strings and concatenate them into a file name
    name = query.split(' ')
    fileName = ""
    i = 0
    for string in name:
        fileName += name[i]
        i += 1

    #Define folder path and filename
    folder_path = r"C:\Users\matty\OneDrive\Documents\CSC1028\jsonFiles"
    file_name = fileName + ".json"
    file_path1 = os.path.join(folder_path, file_name)

    results_str = ""

    #Check if JSON file already exists, and if so, return its content
    if os.path.exists(file_path1):
        with open(file_path1, 'r') as file:
            json_content = file.read()
        json_data = json.loads(json_content)
        return json_content
    else:
        #If JSON file doesn't exist, gather data from various sources
        results = engine.search(query, max_results=10)
        srs = res.SearchResults(results)
        urls = srs.links()
        for u in urls:
            try:
                results_str += scrape_website(u)
            except Exception as e:
                print(str(e))

        results = engine.search("site:instagram.com" + query, max_results=10)
        srs = res.SearchResults(results)
        urls = srs.links()
        for u in urls:
            try:
                results_str += scrape_website(u)
            except Exception as e:
                print(str(e))

        results = engine.search("site:twitter.com" + query, max_results=10)
        srs = res.SearchResults(results)
        urls = srs.links()
        for u in urls:
            try:
                results_str += scrape_website(u)
            except Exception as e:
                print(str(e))

        results_str += wikipediaScrape(query)
                
        #Split the gathered data into segments and process each segment through AI
        inputs_for_prompt = split_string_with_overlap(results_str)
        jsons = []

        for s in inputs_for_prompt:
            completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role":"system", "content": "You are an expert at creating structured .json files about a person's personal details from an unorganised block of data returned about a person from a web search. Create a different json if there are different people. Return as much information as you can on the following topics only: Name, age, date of birth, place of birth, nationality, partner, family members, occupation, awards, education, employer, website, years active, date of death, cause of death, "
                    + "nickname, gender, ethnicity, early life, career highlights, notable achievements, awards and honours, significant events, children, career timeline, notable projects, instagram profile, twitter(X) profile, fanbase, media presence, charitable causes supported, "
                    + "hobbies and interests, books, health conditions, fitness routine, diet, net worth, financial investments, income sources, criminal record, fan clubs, impact on society, cultural legacy, influence on future generations, albums, songs, collaborations, movies, tv shows."
                        + "Do not include any of the above if they are not applicable or if the information is not found. If you think any of the information is about a different person, with the same name, exclude it."},
                    {"role": "user", "content": "This search: " + query + "returned this data: " + s}
                ]
            )
            search_results = completion.choices[0].message.content
            jsons.append(search_results)

        #Concatenate and refine JSON segments through AI processes
        prompt_string = ""
        for j in jsons:
            prompt_string += j + "\n"


        completion1 = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role":"system", "content": "You have a set of JSON files, each containing data in the form of JSON objects. Your task is to combine these JSON files into a single JSON file without duplicating data. The JSON objects in each file have the same structure." +
                " Your program should read all the JSON files from a specified directory, merge the data from each file into a single JSON object, and then write this combined data into a new JSON file." +
                " Make sure that if a key appears in multiple JSON objects, only one copy of the key should appear in the final JSON object, and its corresponding value should be a list containing all the values associated with that key from the different JSON objects." +
                " Ensure that the final JSON file is valid and properly formatted. Don't return the code to do this, just actually combine them, and note that there may only be one JSON present. If only one is present, just return the JSON file." +
                " The returned value should be only one single JSON file, with no other text at all present other than everything needed for and contained inside the JSON. The only text contained should be that of a JSON file."},                        
                {"role": "user", "content": "These are the json files: " + prompt_string}
            ]
        )

        search_results1 = completion1.choices[0].message.content


        completion2 = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
            {"role":"system", "content": "You are an assistant that generates JSON. You always return just the JSON with no additional description or context."},
            {"role":"user", "content": "" + search_results1}
            ]
        )

        #Convert the final JSON content into dictionary format and save it to the designated folder
        json_content = completion2.choices[0].message.content
        json_data = json.loads(json_content)
    
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        file_path = os.path.join(folder_path, fileName + '.json')

        with open(file_path, 'w') as json_file:
            json.dump(json_data, json_file, indent=4)

        return json_content

def business_query(query):
    #Extract the name from the query and generate a file name
    name = query.split(' ')
    fileName = ""
    i = 0
    for string in name:
        fileName += name[i]
        i += 1

    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role":"system", "content": "You are an expert at identifying the UK SIC code for a company. If the company is from outside the UK, assign the company a SIC code which is suitable for the company. If you cannot do this for any reason, assign the code 99999, but if the company is from outside the UK, give it a suitable code, not 99999. Only return a number and nothing else, no punctuation at all."},
            {"role": "user", "content": "" + query}
        ]
    )
    sicString = completion.choices[0].message.content
    sicCode = int(sicString)

    #Define folder path and file name
    folder_path = find_SIC_section_path(sicCode)
    folder_path = os.path.join(folder_path, find_SIC_code(folder_path, sicCode))

    file_name = fileName + ".json"
    file_path1 = os.path.join(folder_path, file_name)

    results_str = ""

    #Check if JSON file already exists, and if so, return its content
    if os.path.exists(file_path1):
        with open(file_path1, 'r') as file:
            json_content = file.read()
        json_data = json.loads(json_content)
        return json_content
    else:
        #If JSON file doesn't exist, gather data from various sources
        results = engine.search(query, max_results=10)
        srs = res.SearchResults(results)
        urls = srs.links()
        for u in urls:
            try:
                results_str += scrape_website(u)
            except Exception as e:
                print(str(e))

        results = engine.search("site:wikipedia.com" + query, max_results=10)
        srs = res.SearchResults(results)
        urls = srs.links()
        for u in urls:
            try:
                results_str += scrape_website(u)
            except Exception as e:
                print(str(e))

        results = engine.search("site:instagram.com" + query, max_results=10)
        srs = res.SearchResults(results)
        urls = srs.links()
        for u in urls:
            try:
                results_str += scrape_website(u)
            except Exception as e:
                print(str(e))

        results = engine.search("site:twitter.com" + query, max_results=10)
        srs = res.SearchResults(results)
        urls = srs.links()
        for u in urls:
            try:
                results_str += scrape_website(u)
            except Exception as e:
                print(str(e))
        
        results_str += wikipediaScrape(query)

        #Split the gathered data into segments and process each segment through AI
        inputs_for_prompt = split_string_with_overlap(results_str)
        jsons = []

        for s in inputs_for_prompt:
            completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role":"system", "content": "You are an expert at creating structured .json files about a business' details from an unorganised block of data returned about a business from a web search. Return as much information as you can on the following topics : "
                      + "Business Name, CEO Name, Year founded, Primary location, how many locations, type of business, industry, number of users, number of employees, revenue, parent company, url, founders, former names, motto, key people, nickname, affilations, "
                      + "stadium, capacity, chairman, manager, league, captain, emblem, world ranking, tournaments, company type, products, services, subsiduaries, traded as, predecessor, instagram link, twitter(X) link, facebook link, stock price, profit, "
                      + "board of directors, description, phone number, key milestones, partnership agreements, employee benefits, legal structure, regulatory compliance, competitors, global reach, principals, famous former students, subjects taught."
                        + "Do not include any of the above if they are not applicable or if the information is not found. If you think any of the information is about a different person, with the same name, exclude it."},
                    {"role": "user", "content": "This search: " + query + "returned this data: " + s}
                ]
            )
            search_results = completion.choices[0].message.content
            jsons.append(search_results)
        
        #Concatenate and refine JSON segments through AI processes
        prompt_string = ""
        for j in jsons:
            prompt_string += j + "\n"
            completion1 = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role":"system", "content": "You have a set of JSON files, each containing data in the form of JSON objects. Your task is to combine these JSON files into a single JSON file without duplicating data. The JSON objects in each file have the same structure." +
                    " Your program should read all the JSON files from a specified directory, merge the data from each file into a single JSON object, and then write this combined data into a new JSON file." +
                    " Make sure that if a key appears in multiple JSON objects, only one copy of the key should appear in the final JSON object, and its corresponding value should be a list containing all the values associated with that key from the different JSON objects." +
                    " Ensure that the final JSON file is valid and properly formatted. Don't return the code to do this, just actually combine them, and note that there may only be one JSON present. If only one is present, just return the JSON file." +
                    " The returned value should be only one single JSON file, with no other text at all present other than everything needed for and contained inside the JSON. The only text contained should be that of a JSON file."},                        
                    {"role": "user", "content": "These are the json files: " + prompt_string}
                ]
            )
            search_results1 = completion1.choices[0].message.content

        completion2 = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role":"system", "content": "You are an assistant that generates JSON. You always return just the JSON with no additional description or context."},
                {"role":"user", "content": "" + search_results1}
            ]
        )

        #Convert to a JSON file and save in a specific folder
        json_content = completion2.choices[0].message.content
        json_data = json.loads(json_content)
    
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        file_path = os.path.join(folder_path, fileName + '.json')

        with open(file_path, 'w') as json_file:
            json.dump(json_data, json_file, indent=4)

        return json_content
        
    
def scrape_website(url):
    try:
        #Send a GET request to the specified URL and retrieve the HTML content
        response = requests.get(url)

        #Extract the HTML content from the response 
        html_content = response.text

        #Create a BeautifulSoup object to parse the HTML
        soup = BeautifulSoup(html_content, 'html.parser')

        #Find all paragraphs in the HTML and extract their text content
        paragraphs = [p.text.strip() for p in soup.find_all('p')]

        #Initialize an empty string to store the concatenated paragraphs
        returnStr = ""

        #Conncatenate all paragraphs with newline characters between them
        for p in paragraphs:
            returnStr += "\n" + p + "\n"

        #Return the concatenated string
        return returnStr
    except Exception as e:
        #If an exception occurs during scraping, return an empty string
        return ""


def wikipediaScrape(query):
    retries = 3  # Number of retries
    for attempt in range(retries):
        try:
            #Search for the query using a search engine
            results = engine.search(query, max_results=1)
            srs = res.SearchResults(results)
            links = srs.links()
            url = links[0]

            #Retrieve the HTML content of the first search result URL
            response = requests.get(url)
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')

            #Extract text content of all paragraphs from the HTML content
            paragraphs = [p.text.strip() for p in soup.find_all('p')]

            #Initialize an empty string to store the concatenated paragraphs
            returnStr = ""

            #Concatenate all paragraphs into a single string
            for p in paragraphs:
                returnStr += "\n" + p + "\n"
            return returnStr
        except Exception as e:
            #Return an empty string if any exception occurs during the process
            return ""

if __name__ == "__main__":
    app.run(debug=True)

