import streamlit as st
import pyodbc
import requests
from datetime import datetime
from passlib.hash import bcrypt
import streamlit.components.v1 as components
from PIL import Image
from io import BytesIO

# Custom CSS for styling
st.markdown("""
   <style>
    .main {
        background-color: #f5f5f5;
        padding: 20px;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        padding: 14px 20px;
        margin: 8px 0;
        border: none;
        cursor: pointer;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .stTextInput>div>div>input {
        background-color: #f1f1f1;
        padding: 10px;
        width: 100%;
        border: 1px solid #ccc;
        margin: 8px 0;
        box-sizing: border-box;
    }
    .stNumberInput>div>div>input {
        background-color: #f1f1f1;
        padding: 10px;
        width: 100%;
        border: 1px solid #ccc;
        margin: 8px 0;
        box-sizing: border-box;
    }
    .stButton>div>button:focus {
        background-color: #4CAF50 !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)


st.title('🌍 Location Viewer & Image Analyzer')



def connect_to_db():
    server = 'tcp:destinations4.database.windows.net'
    database = '...'
    username = '...'
    password = '...'
    driver = '{ODBC Driver 18 for SQL Server}'
    connection_string = f'DRIVER={driver};SERVER={server};PORT=1433;DATABASE={database};UID={username};PWD={password}'

    conn = pyodbc.connect(connection_string)
    return conn



def create_user(username, password):
    conn = connect_to_db()
    cursor = conn.cursor()
    password_hash = bcrypt.hash(password)
    cursor.execute("INSERT INTO Users (Username, PasswordHash) VALUES (?, ?)", (username, password_hash))
    conn.commit()
    conn.close()


def authenticate_user(username, password):
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("SELECT UserID, PasswordHash FROM Users WHERE Username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    if user and bcrypt.verify(password, user.PasswordHash):
        return user.UserID
    return None


def log_query(user_id, destination):
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Queries (UserID, Destination, CreatedAt)
        VALUES (?, ?, ?)
    """, (user_id, destination, datetime.now()))
    conn.commit()
    conn.close()


def get_coordinates(destination):
    subscription_key = '...'
    search_url = f"https://atlas.microsoft.com/search/address/json?api-version=1.0&query={destination}&subscription-key={subscription_key}"
    response = requests.get(search_url)
    if response.status_code == 200:
        result = response.json()
        if result['results']:
            position = result['results'][0]['position']
            return position['lat'], position['lon']
    return None, None


def generate_map_html(latitude, longitude):
    subscription_key = '...'
    map_html = f"""
    <html>
    <head>
        <title>Azure Maps</title>
        <meta name="viewport" content="initial-scale=1,maximum-scale=1,user-scalable=no">
        <script src="https://atlas.microsoft.com/sdk/javascript/mapcontrol/2/atlas.min.js"></script>
        <link rel="stylesheet" href="https://atlas.microsoft.com/sdk/javascript/mapcontrol/2/atlas.min.css" type="text/css">
        <script type="text/javascript">
            var map;
            function GetMap() {{
                map = new atlas.Map('myMap', {{
                    center: [{longitude}, {latitude}],
                    zoom: 10,
                    view: 'Auto',
                    authOptions: {{
                        authType: 'subscriptionKey',
                        subscriptionKey: '{subscription_key}'
                    }}
                }});
                // Add a symbol layer to the map
                var symbolLayer = new atlas.layer.SymbolLayer(datasource, null, {{
                    iconOptions: {{
                        image: 'pin-round-darkblue'
                    }}
                }});
                var datasource = new atlas.source.DataSource();
                map.sources.add(datasource);
                datasource.add(new atlas.data.Feature(new atlas.data.Point([{longitude}, {latitude}])));
                map.layers.add(symbolLayer);
            }}
        </script>
    </head>
    <body onload="GetMap();">
        <div id="myMap" style="position:relative;width:600px;height:400px;"></div>
    </body>
    </html>
    """
    return map_html


def analyze_image(image):
    subscription_key = '....'  # Replace with your actual subscription key
    endpoint = 'https://vision11.cognitiveservices.azure.com/'  # Replace with your actual endpoint
    analyze_url = f"{endpoint}vision/v3.1/analyze"

    headers = {'Ocp-Apim-Subscription-Key': subscription_key, 'Content-Type': 'application/octet-stream'}
    params = {'visualFeatures': 'Categories,Description,Color'}

    response = requests.post(analyze_url, headers=headers, params=params, data=image)

    if response.status_code == 200:
        analysis = response.json()
        return analysis
    else:
        st.error(f"Error: {response.status_code}, {response.text}")
        return None


def display_analysis(analysis):
    if "categories" in analysis:
        st.subheader("Categories")
        for category in analysis["categories"]:
            st.write(f"Category: {category['name']}, Score: {category['score']}")
            if "detail" in category and "landmarks" in category["detail"]:
                for landmark in category["detail"]["landmarks"]:
                    st.write(f"Landmark: {landmark['name']}, Confidence: {landmark['confidence']}")
    if "color" in analysis:
        st.subheader("Color")
        st.write(f"Dominant Color Foreground: {analysis['color']['dominantColorForeground']}")
        st.write(f"Dominant Color Background: {analysis['color']['dominantColorBackground']}")
        st.write(f"Dominant Colors: {', '.join(analysis['color']['dominantColors'])}")
        st.write(f"Accent Color: {analysis['color']['accentColor']}")
        st.write(f"Is Black and White: {analysis['color']['isBwImg']}")
    if "description" in analysis:
        st.subheader("Description")
        st.write(f"Tags: {', '.join(analysis['description']['tags'])}")
        if "captions" in analysis["description"]:
            for caption in analysis["description"]["captions"]:
                st.write(f"Caption: {caption['text']}, Confidence: {caption['confidence']}")
    if "metadata" in analysis:
        st.subheader("Metadata")
        st.write(f"Height: {analysis['metadata']['height']}")
        st.write(f"Width: {analysis['metadata']['width']}")
        st.write(f"Format: {analysis['metadata']['format']}")


if "menu" not in st.session_state:
    st.session_state.menu = "Login"

if st.session_state.menu == "Sign Up":
    st.subheader("Create an Account")
    new_username = st.text_input("New Username")
    new_password = st.text_input("New Password", type="password")
    if st.button("Sign Up"):
        if new_username and new_password:
            create_user(new_username, new_password)
            st.success("Account created successfully!")
            st.session_state.menu = "Login"
            st.experimental_rerun()
        else:
            st.error("Please enter both a username and password.")
elif st.session_state.menu == "Login":
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user_id = authenticate_user(username, password)
        if user_id:
            st.session_state.user_id = user_id
            st.session_state.menu = "Main"
            st.success("Logged in successfully!")
        else:
            st.error("Invalid username or password.")
    if st.button("Go to Sign Up"):
        st.session_state.menu = "Sign Up"
        st.experimental_rerun()

if st.session_state.menu == "Main":
    st.subheader('Enter a Location to View on the Map')
    destination = st.text_input('Destination')

    if st.button('Show on Map'):
        if destination:
            latitude, longitude = get_coordinates(destination)
            if latitude is not None and longitude is not None:
                st.markdown("### Location on Map")
                log_query(st.session_state.user_id, destination)
                map_html = generate_map_html(latitude, longitude)
                components.html(map_html, height=400)
            else:
                st.error('Could not find the location coordinates. Please try another destination.')
        else:
            st.error('Please enter a destination.')

    st.subheader('Enter Image URL for Analysis')
    image_url = st.text_area("Enter the URL of the image")

    if st.button("Load Image"):
        if image_url:
            try:
                response = requests.get(image_url)
                if response.status_code == 200:
                    image = Image.open(BytesIO(response.content))
                    st.image(image, caption='Loaded Image', use_column_width=True)

                    with st.spinner('Analyzing...'):
                        image_data = response.content
                        analysis = analyze_image(image_data)
                        if analysis:
                            display_analysis(analysis)
                else:
                    st.error(f"Failed to load image. HTTP Status Code: {response.status_code}")
            except Exception as e:
                st.error(f"Error loading image: {e}")

    if st.button("Logout"):
        del st.session_state.user_id
        st.session_state.menu = "Login"
        st.experimental_rerun()
