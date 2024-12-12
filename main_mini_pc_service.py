from datetime import datetime
from flask import Flask, jsonify, request, render_template, redirect, url_for, flash, abort, session
import threading
import paho.mqtt.client as mqtt
import requests
import json
import pandas as pd
import time
import sqlite3
from dash import Dash, dcc, html, Input, Output, State
import plotly.express as px
from matplotlib.pyplot import title
from openmeteo_requests import Client

WATER_TANK_ARDUINO_IP = "192.168.100.218"
SPRINKLER_CONTROLL_ARDUINO_IP = "192.168.100.216"

app = Flask(__name__)
app.secret_key = 'my_secret'

global current_temp, current_rain, temp_forecast, \
    rain_forecast, current_air_humidity, current_ground_humidity, \
    water_level, sprinkler_state, max_temp, min_soil_humidity, critical_water_level,\
    water_pump_state, critical_humidity, sprinkler_manual_mode, water_tank_manual_mode

current_ground_humidity = 0.5
current_temp = 20
current_air_humidity = 0.5
prognosed_moisture = 0.3
max_temp = 30
sprinkler_state = "on"
water_level = 0.5

rain_forecast = 0.2
min_soil_humidity = 0.6
critical_humidity = 0.2
ROOFTOP_SIZE = 10  # m2
GEOGRAPHICAL_LATITUDE = 17.02
GEOGRAPHICAL_LONGITUDE = 51.1
WATER_CONTAINER_SIZE = 10  # m3
FORECAST_HOURS = 6
FORECAST_PARAMS = ['relative_humidity_2m', 'temperature_2m', 'precipitation_probability', 'precipitation', 'rain',
                   'showers', 'wind_speed_10m', 'wind_direction_10m', 'wind_gusts_10m']

sprinkler_manual_mode = False

TIMEZONE = None
VALID_TOKEN = "my_secret_token"  # Przykładowy token

# Konfiguracja brokera MQTT
MQTT_BROKER = "192.168.100.189"
MQTT_TOPIC = "sensor/status"
mqtt_client = mqtt.Client()

# Inicjalizacja klienta openmeteo_requests
client = Client()


# Funkcja nasłuchująca MQTT
def mqtt_listener():
    db = sqlite3.connect('data.db', check_same_thread=False)
    cursor = db.cursor()
    def on_connect(client, userdata, flags, rc):
        print(f"Connected with result code {rc}")
        client.subscribe(MQTT_TOPIC)

    def on_message(client, userdata, msg):
        try:
            global current_temp, current_ground_humidity, current_air_humidity, sprinkler_state, sprinkler_manual_mode
            data = json.loads(msg.payload.decode())
            current_temp = data.get('temperature')
            current_ground_humidity = data.get('soil_moisture')
            current_air_humidity = data.get('air_humidity')
            write_db_timestamp = time.strftime('%Y-%m-%d %H:%M', time.localtime())
            sprinkler_state_bool = 0
            if sprinkler_state == "on":
                sprinkler_state_bool = 1
            sprinkler_manual_bool = 0
            if sprinkler_manual_mode:
                sprinkler_manual_bool = 1
            cursor.execute(
                "INSERT INTO measurements (occurance_time,sprinkler_state, sprnkler_auto_mode, temperature, humidity ) VALUES (?, ?, ?, ?, ?)",
                ( write_db_timestamp, sprinkler_state_bool,sprinkler_manual_bool,  current_temp, current_ground_humidity))
            db.commit()
            print(f"Received MQTT message: {data}")
            print("received humidity: ", current_ground_humidity)
        except Exception as e:
            print("exception occured - something is wrong with mqtt message")
            print(e)
            pass

    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_BROKER, 1883, 60)
    mqtt_client.loop_forever()


def weather_api():
    while True:
        try:
            now = datetime.now()
            now_iso8601 = now.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M")

            hourly_params_str = ",".join(FORECAST_PARAMS)
            print(hourly_params_str)

            # Podstawowe zapytanie z mniejszą liczbą parametrów hourly
            response = requests.get(
                f"https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": GEOGRAPHICAL_LATITUDE,
                    "longitude": GEOGRAPHICAL_LONGITUDE,
                    "hourly": str(hourly_params_str),
                    "timezone": "Europe/Warsaw",
                    "forecast_days": 2
                }
            )

            data = response.json()
            print(data)  # Wyświetlenie pełnej odpowiedzi API

            # Sprawdzenie, czy klucz 'hourly' istnieje w odpowiedzi
            if 'hourly' not in data:
                print("Błąd: Brak klucza 'hourly' w odpowiedzi API")
                return

            forecast = data['hourly']

            start_position = forecast['time'].index(now_iso8601)
            print(f"Start position: {start_position} ({now_iso8601}) to {forecast['time'][start_position]}")

            data_record = []
            for param in FORECAST_PARAMS:
                for i in range(FORECAST_HOURS):
                    data_record.append(forecast[param][start_position + i])
            print(data_record)

            # Tworzenie odpowiednich nazw zmiennych (opcjonalnie)
            # data_X_named = {
            #     f"wilgotnosc_prognoza_{i + 1}h": data_X[0][i] for i in range(6)
            # }
            # data_X_named.update({
            #     f"prawdopodobienstwo_opad_{i + 1}h": data_X[1][i] for i in range(6)
            # })

            # print(data_X)

        except Exception as e:
            print("Exception occurred:", e)

        time.sleep(300)  # Aktualizacja co 5 minut


def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            flash("You need to be logged in to access this page.")
            return redirect(url_for('home_login_page'))
        return f(*args, **kwargs)

    decorated_function.__name__ = f.__name__
    return decorated_function


# Endpoint do pobrania stanu systemu
@app.route('/system_status', methods=['GET'])
def get_system_status():
    return jsonify(sprinkler_state)


# Endpoint do zmiany konfiguracji systemu
@app.route('/update_config', methods=['POST'])
@login_required
def update_config():
    min_temp = 0
    min_humidity = request.json.get('min_humidity')
    max_temp = request.json.get('max_temp')
    requests.post(f"http://{SPRINKLER_CONTROLL_ARDUINO_IP}/update_config",
                  json={'min_temp': min_temp, 'min_humidity': min_humidity, 'max_temp': max_temp})
    return redirect(url_for('home'))

@app.route('/update_config_by_interface', methods=['POST'])
@login_required
def updated_config():
    min_temp = 0
    min_humidity = request.form.get('min_humidity')
    max_temperature = request.form.get('max_temp')
    crit_humidity = request.form.get('crit_humidity')
    min_water_level = request.form.get('min_water_level')
    crit_water_level = request.form.get('crit_water_level')
    print("config changed")
    try:
        global min_soil_humidity, critical_humidity, critical_water_level, max_temp
        min_soil_humidity = min_humidity
        critical_humidity = crit_humidity
        critical_water_level = crit_water_level
        max_temp = max_temperature
    except Exception as e:
        print("Exception occurred:", e)
    return redirect(url_for('home'))

@app.route('/', methods=['GET'])
def home_login_page():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login():
    token = request.form.get('token')
    if token == VALID_TOKEN:
        session['logged_in'] = True
        return redirect(url_for('home'))
    else:
        message = "Invalid token. Please try again."
        return render_template('login.html', message=message)


@app.route('/home', methods=['GET'])
@login_required
def home():
    global current_air_humidity, current_temp, current_ground_humidity, sprinkler_state, sprinkler_manual_mode, water_pump_state
    try:
        request = requests.get(f'http://{WATER_TANK_ARDUINO_IP}/get_status')
        water_tank_manual_mode = request.json().get('manual_mode')
        water_level = request.json().get('water_level')
        water_pump_state = request.json().get('pump_state')
        if water_tank_manual_mode:
            water_pump_state = "on"
        else:
            water_pump_state = "off"

        if water_pump_state:
            water_pump_state = "on"
        else:
            water_pump_state = "off"

    except Exception as e:
        water_tank_manual_mode = True
        water_pump_state = "off"
        water_level = 0.5
        print("exception occured: ", e)

    return render_template('home.html',
                           current_air_humidity=current_air_humidity,
                           current_temp=current_temp,
                           current_ground_humidity=current_ground_humidity,
                           sprinkler_state=sprinkler_state,
                           water_pump_state = water_pump_state,
                           sprinkler_manual_mode=sprinkler_manual_mode,
                           water_tank_manual_mode=water_tank_manual_mode,
                           water_level=water_level)


@app.route('/change_config', methods=['GET'])
@login_required
def change_config():
    return render_template('change_config.html')

@app.route('/header.html', methods=['GET'])
@login_required
def make_header():
    return render_template('header.html')

@app.route('/manual_control', methods=['GET', 'POST'])
@login_required
def manual_control():
    global sprinkler_manual_mode, sprinkler_state
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'on':
            print("manual turn on")
            requests.post(f'http://{SPRINKLER_CONTROLL_ARDUINO_IP}/turn_on')  # Włącz zraszacze
            sprinkler_manual_mode = True
            sprinkler_state = "on"
        elif action == 'off':
            print("manual turn off")
            requests.post(f'http://{SPRINKLER_CONTROLL_ARDUINO_IP}/turn_off')  # Wyłącz zraszacze
            sprinkler_state = "off"
            sprinkler_manual_mode = True
        elif action == 'fill_tank':
            print("fill manual tank")
            requests.post(f'http://{WATER_TANK_ARDUINO_IP}/on')  # Wypełnij zbiornik wodny
        elif action == 'stop_tank':
            print("fill manual tank")
            requests.post(f'http://{WATER_TANK_ARDUINO_IP}/off')  # wyłącz napełnianie zbiornik wodny
        elif action == 'sprinkler_auto':
            print("sprinkler auto")
            sprinkler_manual_mode = False
            print(sprinkler_manual_mode)
        elif action == 'water_tank_auto':
            print("water tank manual")
            requests.post(f'http://{WATER_TANK_ARDUINO_IP}/auto')  # wyłącz napełnianie zbiornik wodny

        return redirect(url_for('home'))
    else:
        return render_template('manual_control.html')

# Utwórz instancję Dash
dash_app = Dash(__name__, server=app, url_base_pathname='/statistics/')

# Przykładowe dane do dashboardu
df = px.data.iris()  # Dane testowe
fig = px.scatter(df, x='sepal_width', y='sepal_length')

dash_app.layout = html.Div([

    html.Div([
        html.Iframe(src='/header.html', style={'width': '150px', 'height': '150px', 'border': 'none'})
    ], style={'display': 'flex', 'justify-content': 'center', 'align-items': 'center'}),
    html.H3("Statistics Dashboard"),
    html.Div([
        html.Label("Select Parameter:"),
        dcc.Dropdown(
            id='parameter-dropdown',
            options=[
                {'label': 'Temperature', 'value': 'temperature'},
                {'label': 'Humidity', 'value': 'humidity'},
                {'label': 'Rain', 'value': 'rain'}
            ],
            value='temperature'
        ),
    ]),
    html.Div([
        html.Label("Select Time Range:"),
        dcc.DatePickerRange(
            id='time-range-picker',
            start_date=datetime.now().date(),
            end_date=datetime.now().date()
        )
    ]),
    html.Div([
        html.Button("Generate Graph", id='generate-graph-btn', n_clicks=0)
    ]),
    dcc.Graph(id='line-graph')
])

def fetch_data_from_db(parameter, start_time, end_time):
    db = sqlite3.connect('data.db')
    query = f"""
        SELECT occurance_time, {parameter}
        FROM measurements_test
        WHERE occurance_time BETWEEN ? AND ?
    """
    df = pd.read_sql_query(query, db, params=(start_time, end_time))
    db.close()
    # Konwersja occurance_time na datetime, jeśli jeszcze tego nie zrobiłeś
    df['occurance_time'] = pd.to_datetime(df['occurance_time'])

    # Ustawienie tylko daty (bez godziny)
    df['occurance_date'] = df['occurance_time'].dt.date
    return df

@dash_app.callback(
    Output('line-graph', 'figure'),
    [Input('generate-graph-btn', 'n_clicks')],
    [State('parameter-dropdown', 'value'),
     State('time-range-picker', 'start_date'),
     State('time-range-picker', 'end_date')]
)
def update_graph(n_clicks, selected_parameter, start_date, end_date):
    if not start_date or not end_date:
        return px.line(title="No data available")
    df = fetch_data_from_db(selected_parameter, start_date, end_date)
    if df.empty:
        return px.line(title="No data available")

    fig = px.line(
        df,
        x='occurance_time',
        y=selected_parameter,
        title=f"{selected_parameter.capitalize()} Over Time"
    )

    fig.update_xaxes(
        tickformat="%Y-%m-%d %H:%M",  # Możesz zmienić format, np. "%d-%m-%Y" (dzień-miesiąc-rok)
        title_text="Date/Hour"
    )

    return fig


# Widok Flask dla statystyk z nagłówkiem i stopką
@app.route('/statistics/', methods=['GET'])
@login_required
def render_statistics():
    # Renderuj template Flask z nagłówkiem, który zawiera Dash
    return render_template('base_dash.html')


# Widok Flask, który dostarcza zawartość Dash w iframe
@app.route('/statistics/dash_content', methods=['GET'])
@login_required
def dash_content():
    return dash_app.index()


@app.route('/get_rain_forecast', methods=['GET'])
def return_forecast():
    weather = [{'rain_forecast': rain_forecast}]
    return jsonify(weather, 200)


# Funkcja uruchamiająca Flask w osobnym wątku
def start_flask():
    app.run(host='0.0.0.0', port=5000, threaded=True)


def run_sprinkle_controller():
    global sprinkler_state, current_temp, current_ground_humidity, rain_forecast
    while (True):
        if sprinkler_manual_mode:
            time.sleep(30)
            continue
        if current_ground_humidity < critical_humidity or rain_forecast < min_soil_humidity:
            sprinkler_state = "on"
            requests.post(f"http://{SPRINKLER_CONTROLL_ARDUINO_IP}/turn_on")
            print("Sprinkler turned on with data: humidity -", current_ground_humidity,"rain forecast- ", rain_forecast)
            print("actual configuration: ", critical_humidity, min_soil_humidity)
        else:
            sprinkler_state = "off"
            requests.post(f"http://{SPRINKLER_CONTROLL_ARDUINO_IP}/turn_off")
            print("Sprinkler turned off with data: humidity- ", current_ground_humidity,"forecasted delta: ", rain_forecast)
            print("actual configuration: ", critical_humidity, min_soil_humidity)


        time.sleep(30)  # Sprawdzanie co pół minuty


def prepare_db():
    # check if db exists. If not, then create it. Otherwise, do nothing
    db = sqlite3.connect('data.db')
    cursor = db.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS measurements (occurance_time TIMESTAMP PRIMARY KEY, sprinkler_state INTEGER, sprinkler_auto_mode INTEGER, temperature REAL, humidity REAL, rain REAL)")
    db.commit()
    db.close()


def retention_data():
    db = sqlite3.connect('data.db', check_same_thread=False)
    cursor = db.cursor()
    while True:
        cursor.execute("DELETE FROM measurements WHERE occurance_time < datetime('now', '-360 day')")
        db.commit()
        print("Data retention: Old data removed")
        time.sleep(86400)  # Usuwanie co 24 godziny


# Uruchamianie wątków
if __name__ == '__main__':
    ### drop db
    # db = sqlite3.connect('data.db')
    # cursor = db.cursor()
    # cursor.execute("DROP TABLE measurements")
    # db.commit()
    # db.close()
    #
    # prepare_db()
    # #
    # # Wątek MQTT
    mqtt_thread = threading.Thread(target=mqtt_listener)
    mqtt_thread.start()
    time.sleep(1)

    # Wątek do retencji danych
    retention_thread = threading.Thread(target=retention_data)
    retention_thread.start()
    time.sleep(1)

    # # Wątek pobierania danych pogodowych
    weather_thread = threading.Thread(target=weather_api)
    weather_thread.start()
    time.sleep(1)

    # Wątek Flask
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.start()
    time.sleep(1)

    ###Wątek do kontroli zraszaczy
    sprinkle_controller_thread = threading.Thread(target=run_sprinkle_controller)
    sprinkle_controller_thread.start()
    ##
    #
    # ## Wątek do zbierania danych do treningu modelu
    # # data_collect_thread = threading.Thread(target=data_collect)
    #
