"""

data_X = [wilgotnosc_teraz, wilgotnosc_prognoza_1_h, wilgotnosc_prognoza_2_h, wilgotnosc_prognoza_3_h,
    wilgotnosc_prognoza_4_h,wilogtnosc_prognoza_5_h, wilogtnosc_prognoza_6_h, prawdopodobienstwo_opad_1_h, prawdopodobienstwo_opad_2_h, ..., prawdopodobienstwo_opad_6_h,
    przewidywany_deszcz_1h, przewidywany_deszcz_2h, ..., przewidywany_deszcz_6h,
    przewidywana_mrzawka_1h, przewidywana_mrzawka_2h, ..., przewidywana_mrzawka_6h,
    przewidywany_wiatr, przewidywany_kierunek_wiatru]

data_Y_wilgotnosc = [delta_wilgotnosc_6h]
data_Y_napelnienie = [delta_napelnienie_6h]

api - open meteo

"""
from datetime import datetime
import requests
import matplotlib.pyplot as plt

START_DATE = "2023-01-01"
END_DATE = "2023-12-31"
ROOFTOP_SIZE = 10  # m2
GEOGRAPHICAL_LATITUDE = 17.02
GEOGRAPHICAL_LONGITUDE = 51.1
WATER_CONTAINER_SIZE = 10  # m3
FORECAST_HOURS = 6
FORECAST_PARAMS = ['relative_humidity_2m', 'temperature_2m', 'precipitation_probability', 'precipitation', 'rain', 'showers', 'wind_speed_10m', 'wind_direction_10m', 'wind_gusts_10m']

global lists_square_error_val


def lists_mean_square_error(list1):
    return sum([i**2 for i in list1]) / len(list1)


def avg(lst):
    return sum(lst) / len(lst)


def weather_api(START_DATE, END_DATE, plot = False):
    try:

        hourly_params_str = ",".join(FORECAST_PARAMS)
        # print(hourly_params_str)

        # Podstawowe zapytanie z mniejszą liczbą parametrów hourly
        response_forecast = requests.get(
            f"https://historical-forecast-api.open-meteo.com/v1/forecast",
            params={
                "latitude": GEOGRAPHICAL_LATITUDE,
                "longitude": GEOGRAPHICAL_LONGITUDE,
                "hourly": str(hourly_params_str)+",soil_moisture_1_to_3cm,soil_moisture_3_to_9cm,soil_moisture_0_to_1cm",
                "timezone": "Europe/Warsaw",
                # "forecast_days": 16,
                "start_date": START_DATE,
                "end_date": END_DATE
            }
        )

        data = response_forecast.json()

        # Sprawdzenie, czy klucz 'hourly' istnieje w odpowiedzi
        if 'hourly' not in data:
            print("Błąd: Brak klucza 'hourly' w odpowiedzi API")
            return

        data_X_tmp = []
        data_Y_tmp = []

        forecast_tmp = data['hourly']
        forecast_tmp['avg_soil_moisture'] = []
        for i in range(len(forecast_tmp['time'])):
            forecast_tmp['avg_soil_moisture'].append((forecast_tmp['soil_moisture_0_to_1cm'][i] + forecast_tmp['soil_moisture_1_to_3cm'][i] + forecast_tmp['soil_moisture_3_to_9cm'][i]) / 3)

        #replace forecasted probability of precipation / precipation max
        max_rain = max(forecast_tmp['precipitation']) if max(forecast_tmp['precipitation']) > 0 else 1
        forecast_tmp['precipitation_probability'] = [r / max_rain for r in forecast_tmp['precipitation']]

        # print(forecast_tmp['showers'])
        # print("max rain:", max(forecast_tmp['showers']))

        response_weather = requests.get(
            f"https://archive-api.open-meteo.com/v1/archive",
            params={
                "latitude": GEOGRAPHICAL_LATITUDE,
                "longitude": GEOGRAPHICAL_LONGITUDE,
                "hourly": "soil_moisture_0_to_7cm",
                "timezone": "Europe/Warsaw",
                # "forecast_days": 16,
                "start_date": START_DATE,
                "end_date": END_DATE
            }
        )
        data_actual_weather = response_weather.json()
        forecast_actual_weather_tmp = data_actual_weather['hourly']

        # #soil moisture plot
        if plot:
            plt.plot(forecast_tmp['time'], forecast_tmp['avg_soil_moisture'], label='0-9cm avg')
            plt.plot(forecast_tmp['time'], forecast_actual_weather_tmp['soil_moisture_0_to_7cm'], label='0-7cm')
            plt.legend()
            plt.show()

        for start_position in range(0, len(forecast_tmp['time']) - FORECAST_HOURS):
            data_record = []
            for param in FORECAST_PARAMS:
                for i in range(FORECAST_HOURS):
                    data_record.append(forecast_tmp[param][start_position + i])
            data_record.append(forecast_actual_weather_tmp['soil_moisture_0_to_7cm'][start_position])
            data_X_tmp.append(data_record)

        ##delta prognozy i aktualnej pogody
        for position in range(FORECAST_HOURS, len(forecast_tmp['time'])):
            # data_Y_tmp.append(forecast_tmp['avg_soil_moisture'][position] - forecast_actual_weather_tmp['soil_moisture_0_to_7cm'][position - FORECAST_HOURS])
            data_Y_tmp.append(forecast_actual_weather_tmp['soil_moisture_0_to_7cm'][position] - forecast_tmp['avg_soil_moisture'][position])
            # print("actual time: ", forecast_actual_weather_tmp['time'][position])
            # print("forecast time: ", forecast_tmp['time'][position])

        # print("actula forecast_tmp size: ", forecast_tmp)
        # print("actual real forecast : ", forecast_actual_weather_tmp)
        # lists_square_error_val = lists_mean_square_error(data_Y_tmp)
        # print("Mean Square Error for LISTS before ML:", lists_square_error_val)

    except Exception as e:
        print("Exception occurred:", e)

    return forecast_tmp, forecast_actual_weather_tmp, data_X_tmp, data_Y_tmp

forecast, forecast_actual_weather, data_X, data_Y = weather_api(START_DATE, END_DATE)
# print(data_X)
# print(data_Y)
# time.sleep(50)

def lists_square_error(list1, list2):
    return sum([(list1[i] - list2[i])**2 for i in range(len(list1))])

"""Model"""
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
# print("data_X ", data_X)
# print("data_Y ", data_Y)

# Podziel dane na zbiór treningowy i testowy (np. 80% treningowy, 20% testowy)
X_train, X_test, y_train, y_test = train_test_split(data_X, data_Y, test_size=0.2, random_state=42)

# Utwórz model drzewa losowego
model_watering_plants = RandomForestRegressor(n_estimators=200, random_state=42)

# Wytrenuj model na danych treningowych
model_watering_plants.fit(X_train, y_train)

# # Sprawdź jakość modelu na danych testowych
# y_pred = model_watering_plants.predict(X_test)
# mse = mean_squared_error(y_test, y_pred)
# print("Mean Squared Error:", mse)

# print(lists_square_error_val)
#relative_humidity - 0-6,
#temperature - 6-12,
#precipitation_probability - 12-18,
#precipitation - 18-24,
#rain - 24-30,
#showers - 30-36,
#wind_speed - 36-42,
#wind_direction - 42-48,
#wind_gusts - 48-54
# test_prediction_X = [[81, 84, 85, 86, 87, 85, 25.7, 25.0, 24.7, 24.5, 24.5, 24.7, None, 7, None, None, None, None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 6.5, 5.4, 2.9, 2.7, 10.2, 5.4, 186, 176, 187, 157, 198, 127, 10.1, 10.4, 9.4, 6.1, 16.9, 17.6]]
# print("sample delta soil moisture prediction:", model_watering_plants.predict(test_prediction_X))


global current_temp, current_rain, temp_forecast, \
    rain_forecast, current_air_humidity, current_ground_humidity, \
    water_level, sprinkler_state, max_temp, min_temp, min_soil_humidity, min_water_level, manual_mode, critical_water_level, critical_humidity

ROOFTOP_SIZE = 10  # m2
GEOGRAPHICAL_LATITUDE = 17.02
GEOGRAPHICAL_LONGITUDE = 51.1
WATER_CONTAINER_SIZE = 10  # m3
FORECAST_HOURS = 6

critical_humidity = 0.1
min_soil_humidity = 0.25
max_temp = 30
min_temp = 15


### current humidity + delta vs actual humidity plot on data from other year
START_DATE = "2024-01-22"
END_DATE = "2024-05-01"
forecast, forecast_actual_weather, data_X, data_Y = weather_api(START_DATE, END_DATE)
# print("forecast size ", forecast.keys())
# print("forecast size actual size ", forecast_actual_weather.keys())
predicted_soil_moisture = []
# print(data_X)
# print("forecast ", forecast['avg_soil_moisture'])
try:
    for i in range(len(data_X)):
        predicted_soil_moisture.append(float(model_watering_plants.predict([data_X[i]])[0]))
        predicted_soil_moisture[i] = predicted_soil_moisture[i] + forecast['avg_soil_moisture'][i + 6]
    print("predicted_soil_moisture: ", predicted_soil_moisture)

except Exception as e:
    print("Exception occurred:", e, " at index:", i, " with data_X:", data_X[i])
### predicted soil moisture vs feracst moisture vs actual moisture
# plt.plot(forecast['time'][6:], forecast['soil_moisture_0_to_1cm'][6:], label='forecast moisture 0-1cm')
# plt.plot(forecast['time'][6:], forecast['soil_moisture_1_to_3cm'][6:], label='forecast moisture 1-3cm')
# plt.plot(forecast['time'][6:], forecast['soil_moisture_3_to_9cm'][6:], label='forecast moisture 3-9cm')
plt.plot(forecast['time'][6:], forecast['avg_soil_moisture'][6:], label='forecast avg moisture')
plt.plot(forecast['time'][6:], predicted_soil_moisture, label="forecast avg + predicted delta")
plt.plot(forecast['time'][6:], forecast_actual_weather['soil_moisture_0_to_7cm'][6:], label='actual soil moisture 0-7cm')

print("forecast: ", forecast['avg_soil_moisture'][0])
print("actual: ", forecast_actual_weather['soil_moisture_0_to_7cm'][0])
print("forecast + prediction: ", predicted_soil_moisture[0])

print("forecast size: ", len(forecast['avg_soil_moisture']))
print("actual size: ", len(forecast_actual_weather['soil_moisture_0_to_7cm']))
print("forecast + prediction size: ", len(predicted_soil_moisture))

plt.xlabel('time')
plt.ylabel('Soil moisture')
plt.title('Soil moisture forecast vs actual data')
plt.legend()
plt.show()

###MSE for forecast and forecast+prediction compared to actual data
print("forecast MSE: ", mean_squared_error(forecast['avg_soil_moisture'][6:], forecast_actual_weather['soil_moisture_0_to_7cm'][6:]))
print("forecast + prediction MSE: ", mean_squared_error(predicted_soil_moisture, forecast_actual_weather['soil_moisture_0_to_7cm'][6:]))