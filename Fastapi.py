from bs4 import BeautifulSoup
import urllib.request
import re
import matplotlib.pyplot as plt
from fastapi import FastAPI, Response
import base64
from fastapi.responses import HTMLResponse
import io
import numpy as np
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Form
import requests
from geopy.geocoders import Nominatim
from urllib.parse import quote
import pandas as pd
from matplotlib.figure import Figure
from io import BytesIO
import base64
from jsonpath_ng import parse
from PIL import Image

app = FastAPI()

# Point to the directory where templates are located
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

def get_random_recipe():
    url = "https://low-carb-recipes.p.rapidapi.com/random"
    headers = {
        "X-RapidAPI-Key": "32d7001925msh402480830a5cbe4p168062jsn0a84d9fe7556",  # Use your actual API key here
        "X-RapidAPI-Host": "low-carb-recipes.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return None

@app.get("/meal", response_class=HTMLResponse)
async def read_item(request: Request):
    recipe = get_random_recipe()
    return templates.TemplateResponse("results_meal.html", {"request": request, "recipe": recipe})

data = [
    {'Description': 'Croissants, apple', 'fdcId': 174988, 'Calories (kcal)': 254},
    {'Description': 'Strudel, apple', 'fdcId': 175032, 'Calories (kcal)': 274},
    {'Description': 'Babyfood, juice, apple', 'fdcId': 170959, 'Calories (kcal)': 47.0},
    {'Description': 'Fruit butters, apple', 'fdcId': 168816, 'Calories (kcal)': 173},
    {'Description': 'Rose-apples, raw', 'fdcId': 168171, 'Calories (kcal)': 25.0}
]

df = pd.DataFrame(data)

@app.get("/nutrition")
async def read_root():
    # Calculate average calories and the item with the minimum calories
    average_calories = df['Calories (kcal)'].mean()
    min_calories_item = df.loc[df['Calories (kcal)'].idxmin()].to_dict()

    # Generate recommendations
    recommendations = """
    Ensure data accuracy, especially with the average calorie content vs. highest calorie item discrepancy.<br>
    For low-calorie diets, Rose-apples, raw, are a great choice at only 25.0 kcal.<br>
    Remember the importance of nutritional diversity beyond just calorie content.<br>
    Adjust serving sizes as necessary to meet your dietary goals.<br>
    Align food choices with your broader health and wellness goals, whether that's weight loss, maintenance, or gain.<br>
    """

    # Generate plots
    fig = Figure()
    ax = fig.subplots()
    ax.bar(df['Description'], df['Calories (kcal)'], color='skyblue')
    ax.set_title('Calories Content in Different Foods')
    ax.set_xticks(range(len(df['Description'])))
    ax.set_xticklabels(df['Description'], rotation=45, ha="right")
    ax.set_ylabel('Calories (kcal)')

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    calories_bar_plot = base64.b64encode(buf.read()).decode('utf-8')

    # Construct HTML response
    html_content = f"""
    <html>
        <head>
            <title>Nutritional Information Visualization</title>
        </head>
        <body>
            <h1>Nutritional Analysis</h1>
            <p>Average calories: {average_calories} kcal</p>
            <p>Item with the lowest calorie content: {min_calories_item['Description']} at {min_calories_item['Calories (kcal)']} kcal</p>
            <h2>Recommendations</h2>
            <p>{recommendations}</p>
            <h2>Visualizations</h2>
            <img src="data:image/png;base64,{calories_bar_plot}" width="500"><br>
        </body>
    </html>
    """
    return Response(content=html_content, media_type="text/html")

@app.get("/meal", response_class=HTMLResponse)
def read_root():
    try:
        results = main()
        return "Here is the best 15 restaurants: <br>" + str(results)
    except Exception as e:
        return str(e)

# Define a function to get data from an API
def get_data_from_api(url, headers):
    response = requests.get(url, headers=headers)
    print(response)
    if response.status_code == 200:
        return response.json()
    else:
        return None

# Filter the data by the conditions
def data_filter(data, jsonpath_exprs):
    extracted_data = {}
    for field, expr in jsonpath_exprs.items():
        extracted_data[field] = [match.value for match in expr.find(data)]
    data_list = [{'price': item.count('$'), 'rating': extracted_data['rating'][i], 'distance': extracted_data['distance'][i], 'name': extracted_data['name'][i]} for i, item in enumerate(extracted_data['price'])]
    sorted_data = sorted(data_list, key=lambda x: (-x['rating'], x['price'], x['distance']))
    result = ""
    for i, item in enumerate(sorted_data[:15], start=1):
        result += f"{i}. {item['name']}, Rating: {item['rating']}, Distance: {item['distance']}, Price: {'$'*item['price']}\n"
    return result

# Get the data from API and extract them
def main():
    url = "https://api.yelp.com/v3/businesses/search?location=1305%2018th%20Avenue%20San%20Francisco%2C%20CA%2094122&sort_by=distance&limit=50"
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer XYYISJqZ1-M7I9Zon6QhZN2chnvpG4CWnpqEVu2diJhm-pahqXR4npTo0QS7KoKntQxC0MRTbAt3YIPGtV3k_EWam6iQsyfkoRN26DAaC_dawUhTFNqDjwrPTj7uZXYx"
    }
    jsonpath_exprs = {
        'price': parse('$..businesses[*].price'),
        'distance': parse('$..businesses[*].distance'),
        'name': parse('$..businesses[*].name'),
        'rating': parse('$..businesses[*].rating')
    }

    data = get_data_from_api(url, headers)
    filtered_data = data_filter(data, jsonpath_exprs)
    filtered_data = filtered_data.replace("\n", "<br>")
    return filtered_data

@app.get("/")
async def get_index(request: Request):
    # Render the index.html template
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/submit-delivery")
async def submit_delivery(request: Request,location: str = Form(...)):
    def get_lat_lon(location):
        geolocator = Nominatim(user_agent="tripadvisor_app")
        location = geolocator.geocode(location)
        if location:
            return f"{location.latitude},{location.longitude}"
        else:
            print("Error: Unable to retrieve latitude and longitude.")
            return None
    
    def get_nearby_locations(lat_long):
        url = f"https://api.content.tripadvisor.com/api/v1/location/nearby_search?latLong={lat_long}&key=537AAD46EB2E4C54987FBE1A33086409&category=restaurants&language=en"
        headers = {"accept": "application/json"}
        response = requests.get(url, headers=headers)
        return response.json()
    
    def get_restaurant_details(location_id):
        url = f"https://api.content.tripadvisor.com/api/v1/location/{location_id}/details?key=537AAD46EB2E4C54987FBE1A33086409&language=en&currency=USD"
        headers = {"accept": "application/json"}
        response = requests.get(url, headers=headers)
        return response.json()
    
    def calculate_delivery_time(distance):
        # Assuming average speed of 45 mph and adding 20 minutes for other factors
        delivery_time_hours = distance / 45
        delivery_time_minutes = round(delivery_time_hours * 60 + 20,2)
        return delivery_time_minutes
    
    lat_lon = get_lat_lon(location)
    restaurant_data = []
    if lat_lon:
        nearby_locations = get_nearby_locations(lat_lon)
        for loc in nearby_locations['data'][:10]:  # Limit to first 10 restaurants
            details = get_restaurant_details(loc['location_id']) if 'location_id' in loc else {}
            restaurant_data.append({
                'name': loc['name'],
                'distance': loc.get('distance', 'N/A'),
                'address': loc['address_obj']['address_string'] if loc.get('address_obj') else 'Address not available',
                'phone': details.get('phone', 'N/A'),
                'website': details.get('website', 'N/A'),
                'rating': details.get('rating', 'N/A'),
                'delivery_time': calculate_delivery_time(float(loc['distance'])) if loc.get('distance') else 'N/A'
            })
    
    # Render the template with restaurant data
    return templates.TemplateResponse("results_delivery.html", {
        "request": request,
        "restaurants": restaurant_data
    })
    

@app.post("/submit-restaurants")
async def submit_restaurants(request: Request, location: str = Form(...)):
    def get_lat_lon(location):
        geolocator = Nominatim(user_agent="tripadvisor_app")
        location = geolocator.geocode(location)
        if location:
            return f"{location.latitude},{location.longitude}"
        else:
            print("Error: Unable to retrieve latitude and longitude.")
        return None
    
    def get_nearby_locations(lat_long):
        url = f"https://api.content.tripadvisor.com/api/v1/location/nearby_search?latLong={lat_long}&key=537AAD46EB2E4C54987FBE1A33086409&category=restaurants&language=en"
        headers = {"accept": "application/json"}
        response = requests.get(url, headers=headers)
        return response.json()
    
    lat_lon = get_lat_lon(location)
    restaurant_data = []
    if lat_lon:
        nearby_locations = get_nearby_locations(lat_lon)
        # Assuming the API response structure, adjust as needed
        restaurant_data = [{
            'name': loc['name'],
            'distance': loc.get('distance', 'N/A'),
            'address': loc['address_obj']['address_string'] if loc.get('address_obj') else 'Address not available'
        } for loc in nearby_locations['data'][:10]]  # Select up to 10 restaurants
    
    # Render the template with restaurant data
    return templates.TemplateResponse("results_restaurants.html", {
        "request": request,
        "restaurants": restaurant_data
    })

@app.get("/restaurant")
async def get_index(request: Request):
    # Render the index.html template
    return templates.TemplateResponse("restaurants.html", {"request": request})

@app.get("/delivery")
async def get_index(request: Request):
    # Render the index.html template
    return templates.TemplateResponse("delivery.html", {"request": request})

@app.get('/groceries')
def grocery():
    url = "https://www.driveresearch.com/market-research-company-blog/grocery-store-statistics-where-when-how-much-people-grocery-shop/"
    response = requests.get(url)

    if response.status_code == 200:
        print('The request was successful')
    else:
        print('The request failed')

    soup = BeautifulSoup(response.text, "html.parser")

    #Find the relevant paragraph containing the desired text
    relevant_paragraph = soup.find('p', class_='heading-three')
    next_paragraph = relevant_paragraph.find_next_sibling('p')
    text = next_paragraph.get_text(strip=True)
    #Regular expression pattern to find numbers with or without commas
    number_pattern = r'\d{1,3}(?:,\d{3})*(?:\.\d+)?'
    #Find all numbers in the text
    numbers = re.findall(number_pattern, text)

    #Convert percentage to float with percentage sign
    for i in range(len(numbers)):
        if '%' in numbers[i]:
            numbers[i] = numbers[i]
        else:
            numbers[i] = numbers[i].replace(',', '')
    #Print the original number and percentage
    number22 = numbers[0]
    number22 = int(number22)
    percentage = numbers[3]
    percentage = float(percentage)
    number21 = number22/(1-0.01*percentage)
    number21 = int(number21)
    data = [number21, number22]
    years = ['2021', '2022']


    #sentence
    sentence1 = ["<big><big>This is a statistic about when, where & how much consumers do per grocery trip in 2022.</big></big>"
                 "<p></p>"
                 "The research was conducted by <a href='https://www.driveresearch.com/'>Driveresearch</a> and was post on its website."
                 "Click <a href = 'https://www.driveresearch.com/market-research-company-blog/grocery-store-statistics-where-when-how-much-people-grocery-shop/'>here</a> to see"
                 "the original article."
                 "<p></p>"
                 "<p><big style = 'color:brown;'>Total geocery store number:</big></p>"
                 f"As of 2022, there are a total of <big style='color:orange;'>{number22}</big> functional grocery stores in the United States, a"
                 f"decrease of 1.2% compared to <big style='color:orange;'>{number21}</big> in 2021. The main reason for the permanent closure of"
                 "these grocery stores is due to the impact of the COVID-19 pandemic, which has led to a"
                 "decrease in customers or temporary closure, ultimately resulting in a significant decrease in"
                 "revenue and the inability to continue operating."
                 "<p></p>"]

    # Plot the histogram
    plt.figure(figsize=(8, 6))
    plt.bar(years, data, color='skyblue')


    # Add labels and title
    plt.xlabel('Year')
    plt.ylabel('Number')
    plt.title('Grocery store numbers in 2021 and 2022')

    for i in range(len(data)):
        plt.text(years[i], data[i], str(data[i]), ha='center', va='bottom')
    # Show the plot
    buffer1 = io.BytesIO()
    plt.savefig(buffer1, format='png')
    buffer1.seek(0)
    plt.close()  # Close the plot to release resources

    # Encode the plot image as base64
    plot_base64_1 = base64.b64encode(buffer1.getvalue()).decode()

    walmart_paragraph = soup.find('p', string='Walmart is the biggest grocer in the country')
    next_paragraph = walmart_paragraph.find_next_sibling('p')
    walmart_number = next_paragraph.find('a').string.split()[0].replace(',','')  # Extract number of locations
    next_paragraph = next_paragraph.find_next_sibling('p')

    # Find the relevant span tag
    span_tag = next_paragraph.find('span')

    # Extract text from the span tag
    span_text = span_tag.get_text().replace(',','')

    # Define the regular expression pattern to find the number with commas
    pattern = r"\b\d+\b"

    # Find all matches using the regular expression pattern
    matches = re.findall(pattern, span_text)

    # Extract the first match (assuming there is only one match in the given HTML content)
    square_footage = matches[0] if matches else None
    square_footage = int(square_footage)
    walmart_number = int(walmart_number)
    walmart = square_footage/walmart_number
    walmart = int(walmart)
    data = [walmart, 165000, 16400]
    grocery = ['Walmart', 'Kroger', 'Aldi']

    sentence2 = ["<p><big style = 'color: brown;'> 2022 top 3 largest grocery stores:</big></p>"
                 "<big style = 'color: goldenrod;'>Walmart</big> won the title of the largest grocer in the United States in 2022.\n"
                 f"With over <span style = 'color: lightgreen;'>4,000</span> active Walmart locations and a total of <span style = 'color: lightgreen;'>852,300,300</span> square feet.\n"
                 "which means the average square feet is more than 200,000.\n"
                 "Walmart can take over approximately <big style = 'color: red;'>4%</big> of America’s land!\n"
                 "<p></p>"]
    plt.bar(grocery, data, color=['lightblue', 'lightgreen', 'orange'])
    # Add labels and title
    plt.xlabel('Grocery')
    plt.ylabel('Average Square Feet')
    plt.title('Top 3 biggest groceries in 2022')
    for i in range(len(data)):
        plt.text(grocery[i], data[i], str(data[i]), ha='center', va='bottom')
    # Show the plot
    buffer2 = io.BytesIO()
    plt.savefig(buffer2, format='png')
    buffer2.seek(0)
    plt.close()  # Close the plot to release resources

    # Encode the plot image as base64
    plot_base64_2 = base64.b64encode(buffer2.getvalue()).decode()

    # Find all <ul> elements
    ul_elements = soup.find_all('ul')

    # Initialize an empty list to store target <ul> elements
    money = []

    # Iterate over each <ul> element
    for ul_element in ul_elements:
        # Check if the text of the <ul> element contains the desired content
        if "spend less than $100" in ul_element.get_text():
            # If it does, add it to the list of target elements
            money.append(ul_element)
    percentages_descriptions = []

    # Process each targeted <ul> element
    for ul_element in money:
        # Extract and save the content
        li_elements = ul_element.find_all('li')
        for li in li_elements:
            match = re.search(r'(\d+%)\s(.*)\son groceries per trip', li.get_text())
            if match:
                percentage = match.group(1)
                description = match.group(2)
                percentages_descriptions.append({"Percentage": percentage, "Description": description})

    # Extract percentages and descriptions
    percentages = [int(item["Percentage"][:-1]) for item in percentages_descriptions]
    descriptions = [item["Description"] for item in percentages_descriptions]

    sentence3 = ["<p><big style = 'color: brown;'>How much consumers spend per grocery trip:</big></p>"
                 "<big style = 'color:blue;'>35%</big> spend less than <big style = 'color:orange;'>$100</big> on groceries per trip,\n"
                 "<big style = 'color:blue;'>38%</big> spend <big style = 'color:orange;'>$100 to $199</big> on groceries per trip,\n"
                 "<big style = 'color:blue;'>27%</big> spend <big style = 'color:orange;'>$200 or more</big> on groceries per trip.\n"
                 "Totally, on average consumers spend <big style = 'color:orange;'>$155.62</big> on groceries per shopping trip."
                 "<p></p>"]
    # Plotting the pie chart
    plt.figure(figsize=(6, 4))
    plt.pie(percentages, labels=descriptions, autopct='%1.1f%%', startangle=140, labeldistance=1.1, textprops={'fontsize': 10})
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.title('How much people spend per grocery trip')

    # Show the plot
    buffer3 = io.BytesIO()
    plt.savefig(buffer3, format='png')
    buffer3.seek(0)
    plt.close()  # Close the plot to release resources

    # Encode the plot image as base64
    plot_base64_3 = base64.b64encode(buffer3.getvalue()).decode()

    ul_elements = soup.find_all('ul')
    # Initialize an empty list to store target <ul> elements
    time = []

    # Iterate over each <ul> element
    for ul_element in ul_elements:
        # Check if the text of the <ul> element contains the desired content
        if "spend less than 30 minutes" in ul_element.get_text():
        # If it does, add it to the list of target elements
         time.append(ul_element)
    percentages_descriptions = []

    # Process each targeted <ul> element
    for ul_element in time:
    # Extract and save the content
        li_elements = ul_element.find_all('li')
        for li in li_elements:
            match = re.search(r'(\d+%)\sof\speople\s(.*)\sgrocery\sshopping\sper\strip', li.get_text())
            if match:
                percentage = match.group(1)
                description = match.group(2)
                percentages_descriptions.append({"Percentage": percentage, "Description": description})
    # Extract percentages and descriptions
    percentages = [int(item["Percentage"][:-1]) for item in percentages_descriptions]
    descriptions = [item["Description"] for item in percentages_descriptions]

    sentence4 = ["<p><big style = 'color: brown;'>How long consumers spend per grocery trip:</big></p>"
                 "<big style = 'color: blue;'>36%</big> of people spend <big style = 'color:orange;'>less than 30 minutes</big> grocery shopping per trip,"
                 "<big style = 'color: blue;'>36%</big> of people spend <big style = 'color:orange;'>30 to 44 minutes</big> grocery shopping per trip,"
                 "<big style = 'color: blue;'>28%</big> of people spend <big style = 'color:orange;'>45 minutes or more</big> grocery shopping per trip."
                 "<p></p>"]
    # Plot histogram
    plt.bar(descriptions, percentages, color=['lightblue', 'lightgreen', 'orange'], edgecolor='black', )

    # Add labels and title
    plt.xlabel('Time')
    plt.ylabel('Percentage')
    plt.title('How many time people spend per grocery trip')
    plt.xticks(fontsize=8)

    for i in range(len(descriptions)):
        plt.text(descriptions[i], percentages[i], f'{percentages[i]:.1f}%', ha='center', va='bottom')

    # Show the plot
    buffer4 = io.BytesIO()
    plt.savefig(buffer4, format='png')
    buffer4.seek(0)
    plt.close()  # Close the plot to release resources

    # Encode the plot image as base64
    plot_base64_4 = base64.b64encode(buffer4.getvalue()).decode()

    # Find all <ul> elements
    ul_elements = soup.find_all('ul')

    # Initialize an empty list to store target <ul> elements
    day = []

    # Iterate over each <ul> element
    for ul_element in ul_elements:
        # Check if the text of the <ul> element contains the desired content
        if "Monday" in ul_element.get_text():
            # If it does, add it to the list of target elements
            day.append(ul_element)
    days = []
    percentages = []

    # Process each targeted <ul> element
    for ul_element in day:
        # Extract and save the content
        li_elements = ul_element.find_all('li')
        for li in li_elements:
            # Extract day and percentage
            day, percentage = li.get_text().split(' (')
            percentage_str = li.get_text().split('(')[1].split('%')[0].strip()
            percentage = int(percentage_str)
            # Append to the respective lists
            days.append(day)
            percentages.append(percentage)
    data = [64, 36]
    particular = ['Have particular day', 'No particular day']

    sentence5 =["<p><big style = 'color:brown;'>Do consumers have particular days for grocery shop?</big></p>"
                "Almost 2/3(<big style = 'color: blue'>64%</big>) people said they do <span style = 'color:red;'>have a particular day</span> go for a grocery trip."
               "Meanwhile, <big style = 'color: blue'>36%</big> percent of consumers said there are <span style = 'color:red;'>no particular days</span> of the week they do their grocery shopping."
               "<p></p>"]
    # Plotting the pie chart
    plt.figure(figsize=(8, 6))
    plt.pie(data, labels=particular, autopct='%1.1f%%', startangle=140, labeldistance=1.1, textprops={'fontsize': 10})
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.title('How many people have particular day for shopping')
    buffer5 = io.BytesIO()
    plt.savefig(buffer5, format='png')
    buffer5.seek(0)
    plt.close()



    particular_day = days[:-1]
    particular_percentage = percentages[:-1]

    sentence6 = ["<p><big style = 'color: brown;'>Which days are most popular?</big></p>"
                 "Most of surveyed people make <big style = 'color:orange;'>Friday</big> (<big style = 'color: blue'>20%</big>) and "
                 "<big style = 'color: orange;'>Saturday</big> (<big style = 'color: blue'>23%</big>) as the days for grocery shopping. "
                 "In fact, the end of the week is when <big style = 'color: blue'>59%</big> of consumers visit the grocery store."
                 "<p></p>"]
    # Plotting the bar chart
    plt.figure(figsize=(10, 6))
    plt.bar(particular_day, particular_percentage, color='skyblue', label='Percentage')

    # Plotting the line chart
    plt.plot(particular_day, particular_percentage, marker='o', color='red', label='Percentage')

    # Adding labels and title
    plt.xlabel('Day of the Week')
    plt.ylabel('Percentage')
    plt.title('Which day is the particular day for shopping')

    # Rotating x-axis labels for better readability
    plt.xticks(rotation=45)

    for i in range(len(particular_day)):
        plt.text(particular_day[i], particular_percentage[i], f'{percentages[i]:.1f}%', ha='center', va='bottom')

    # Show plot
    plt.tight_layout()
    buffer6 = io.BytesIO()
    plt.savefig(buffer6, format='png')
    buffer6.seek(0)
    plt.close()

    # Encode the plot images as base64
    plot_base64_5 = base64.b64encode(buffer5.getvalue()).decode()
    plot_base64_6 = base64.b64encode(buffer6.getvalue()).decode()


    # Find all <ul> elements
    ul_elements = soup.find_all('ul')

    # Initialize an empty list to store target <ul> elements
    place = []

    # Iterate over each <ul> element
    for ul_element in ul_elements:
        # Check if the text of the <ul> element contains the desired content
        if "Mainstream" in ul_element.get_text():
            # If it does, add it to the list of target elements
            place.append(ul_element)
    # Initialize empty lists to store places and percentages
    places = []
    percentages = []

    # Process each targeted <ul> element
    for ul_element in place:
        # Extract and save the content
        li_elements = ul_element.find_all('li')
        for li in li_elements:
            # Extract place and percentage
            place_percentage = li.get_text().split(':')
            place = place_percentage[0].split('(')[0].strip()
            percentage = float(place_percentage[1].strip('%'))
            # Append to the respective lists
            places.append(place)
            percentages.append(percentage)
    # Select top 5
    places = places[:5]
    percentages = percentages[:5]

    sentence7 = ["<p><big style = 'color: brown;'>Where do consumers shop?</big></p>"
                 "<big style = 'color:blue;'>55%</big> of surveyed will grocery shop at a <big style = 'color:orange;'>mainstream grocery chain</big>, such as Safeway, Kroger,"
                 "<big style = 'color:blue;'>54%</big> of surveyed will grocery shop at a <big style = 'color:orange;'>supercenter</big>, such as Target, Walmart."
                 "<p></p>"]
    # Plotting the bar chart
    plt.figure(figsize=(10, 6))
    plt.bar(places, percentages, color='skyblue', label='Percentage')

    # Plotting the line chart
    plt.plot(places, percentages, marker='o', color='orange', label='Percentage')

    # Adding labels and title
    plt.xlabel('Locations')
    plt.ylabel('Percentage')
    plt.title('Top 5 grocery stores consumers are most loyal')

    # Rotating x-axis labels for better readability
    plt.xticks(rotation=45)

    for i in range(len(places)):
        plt.text(places[i], percentages[i], f'{percentages[i]:.1f}%', ha='center', va='bottom')

    # Show plot
    plt.tight_layout()
    # Show the plot
    buffer7 = io.BytesIO()
    plt.savefig(buffer7, format='png')
    buffer7.seek(0)
    plt.close()  # Close the plot to release resources

    # Encode the plot image as base64
    plot_base64_7 = base64.b64encode(buffer7.getvalue()).decode()

    sentences = [sentence1, sentence2, sentence3, sentence4, sentence5, sentence6, sentence7]
    plots = [plot_base64_1, plot_base64_2, plot_base64_3, plot_base64_4, plot_base64_5, plot_base64_6, plot_base64_7]

    # Combine sentences and plot images in the HTML response body
    html_content = ""
    for sentence, plot in zip(sentences, plots):
        html_content += f"<p>{sentence[0]}</p>"
        html_content += f'<img src="data:image/png;base64,{plot}" alt="Plot"/>'
    # Return the HTML content as part of the API response
    return Response(content=html_content, media_type="text/html")