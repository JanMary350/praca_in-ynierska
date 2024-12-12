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
import time
from datetime import datetime
from logging import CRITICAL
import requests
import matplotlib.pyplot as plt

START_DATE = "2023-01-01"
END_DATE = "2023-12-31"
ROOFTOP_SIZE = 10  # m2
GEOGRAPHICAL_LATITUDE = 17.02
GEOGRAPHICAL_LONGITUDE = 51.1
WATER_CONTAINER_SIZE = 100  # m3
FORECAST_HOURS = 6
FORECAST_PARAMS = ['relative_humidity_2m', 'temperature_2m', 'precipitation_probability','precipitation', 'rain', 'showers', 'wind_speed_10m', 'wind_direction_10m', 'wind_gusts_10m', "cloud_cover", "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high"]

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
        # print(data)  # Wyświetlenie pełnej odpowiedzi API

        # Sprawdzenie, czy klucz 'hourly' istnieje w odpowiedzi
        if 'hourly' not in data:
            print("Błąd: Brak klucza 'hourly' w odpowiedzi API")
            return

        data_X_tmp = []
        data_Y_tmp = []

        forecast_tmp = data['hourly']
        forecast_tmp['avg_soil_moisture'] = []
        for i in range(len(forecast_tmp['time'])):
            forecast_tmp['avg_soil_moisture'].append(avg([forecast_tmp['soil_moisture_0_to_1cm'][i]]))

        #replace forecasted probability of rain / rain max
        max_rain = max(forecast_tmp['rain']) if max(forecast_tmp['rain']) > 0 else 1
        forecast_tmp['precipitation_probability'] = [r / max_rain for r in forecast_tmp['rain']]

        # print(forecast_tmp['showers'])
        # print("max rain:", max(forecast_tmp['showers']))

        response_weather = requests.get(
            f"https://archive-api.open-meteo.com/v1/archive",
            params={
                "latitude": GEOGRAPHICAL_LATITUDE,
                "longitude": GEOGRAPHICAL_LONGITUDE,
                "hourly": "precipitation",
                "timezone": "Europe/Warsaw",
                # "forecast_days": 16,
                "start_date": START_DATE,
                "end_date": END_DATE
            }
        )
        data_actual_weather = response_weather.json()
        forecast_actual_weather_tmp = data_actual_weather['hourly']

        for start_position in range(0, len(forecast_tmp['time']) - FORECAST_HOURS):
            data_record = []
            for param in FORECAST_PARAMS:
                for i in range(FORECAST_HOURS):
                    data_record.append(forecast_tmp[param][start_position + i])
            data_X_tmp.append(data_record)

        for position in range(FORECAST_HOURS, len(forecast_tmp['time'])):
            rain_water_added_sum = 0
            for i in range(FORECAST_HOURS):
                rain_water_added_sum += forecast_tmp['precipitation'][position - i] * ROOFTOP_SIZE / WATER_CONTAINER_SIZE
            data_X_tmp[position - FORECAST_HOURS].append(rain_water_added_sum)

        ##delta prognozy i aktualnej pogody
        for position in range(FORECAST_HOURS, len(forecast_tmp['time'])):
            rain_water_added_sum = 0
            for i in range(FORECAST_HOURS):
                # print((position - i), forecast_actual_weather_tmp['precipitation'][position - i])
                rain_water_added_sum += forecast_actual_weather_tmp['precipitation'][position - i] * ROOFTOP_SIZE /WATER_CONTAINER_SIZE
            data_Y_tmp.append(rain_water_added_sum - data_X_tmp[position - FORECAST_HOURS][-1] )



        # print("data_X_tmp size: ", len(data_X_tmp))

        # print("actula forecast_tmp size: ", forecast_tmp)
        # print("actual real forecast : ", forecast_actual_weather_tmp)
        # lists_square_error_val = lists_mean_square_error(data_Y_tmp)
        # print("Mean Square Error for LISTS before ML:", lists_square_error_val)

    except Exception as e:
        print("Exception occurred:", e)

    return forecast_tmp, forecast_actual_weather_tmp, data_X_tmp, data_Y_tmp

forecast, forecast_actual_weather, data_X, data_Y = weather_api(START_DATE, END_DATE)
print(data_X[0])
print(data_Y[0])
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
model_watering_plants = RandomForestRegressor(n_estimators=100, random_state=42)

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

test_prediction_X = [[59, 61, 62, 63, 63, 63, 15.1, 14.8, 14.5, 14.2, 14.1, 14.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 8.7, 10.6, 10.6, 10.5, 9.7, 9.8, 30, 24, 24, 27, 27, 28, 15.1, 14.4, 16.6, 16.9, 16.2, 15.5, 27, 74, 63, 78, 72, 88, 0, 0, 0, 0, 0, 0, 27, 0, 0, 0, 0, 0, 0, 74, 63, 78, 72, 88, 0.0]]
print("sample delta soil moisture prediction:", model_watering_plants.predict(test_prediction_X))


global current_temp, current_rain, temp_forecast, \
    rain_forecast, current_air_humidity, current_ground_humidity, \
    water_level, sprinkler_state, max_temp, min_temp, min_soil_humidity, min_water_level, manual_mode, critical_water_level, critical_humidity

GEOGRAPHICAL_LATITUDE = 17.02
GEOGRAPHICAL_LONGITUDE = 51.1
WATER_CONTAINER_SIZE = 100  # m3
FORECAST_HOURS = 6

critical_humidity = 0.1
min_soil_humidity = 0.25
max_temp = 30
min_temp = 15

# def makeDecisionWaterResupplying(test_prediction_X, current_water_level):
#     water_level_delta = model_water_level.predict(test_prediction_X) #
#     if current_water_level <= critical_water_level or water_level_delta < current_water_level - min_water_level:
#         return "Należy zwiększyć poziom wody"
#     else:
#         return "Nie trzeba zwiększać poziomu wody"
#
#
# def makeDecisionWatering(test_prediction_X, current_soil_moisture, current_temp):
#     soil_moisture_delta = model_watering_plants.predict(test_prediction_X)
#     temp_out_of_range_change = temp_out_of_range(current_soil_moisture)
#     if (soil_moisture_delta < min_soil_humidity - current_soil_moisture or current_soil_moisture <= critical_humidity or temp_out_of_range_change) and max_temp > current_temp > min_temp:
#         return "Należy podlać ogród - włączanie pompy"
#     else:
#         return "Nie należy podlewać - wyłączanie pompy"
#
# ###no precipation
# test_prediction_X = [[81, 84, 85, 86, 87, 85, 25.7, 25.0, 24.7, 24.5, 24.5, 24.7, 0.85, 0.9, 0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 6.5, 5.4, 2.9, 2.7, 10.2, 5.4, 186, 176, 187, 157, 198, 127, 10.1, 10.4, 9.4, 6.1, 16.9, 17.6]]
# print("sample delta soil moisture prediction with no precipation:", model_watering_plants.predict(test_prediction_X))
# print(makeDecisionWatering(test_prediction_X, 0.2, 25.7))
# #
# # ###precipation, high rain and high showers
# # test_prediction_X = [[81, 84, 85, 86, 87, 85, 25.7, 25.0, 24.7, 24.5, 24.5, 24.7, 0.65, 0.6, 0, 0.7, 0.6, 0, 0.5, 0.6, 0.6, 0.5, 0.4, 0.3, 0.5, 0.4, 1.1, 0.75, 0.8, 0.5, 0.7, 0.7, 0.6, 0.65, 0.7, 0.75, 6.5, 5.4, 2.9, 2.7, 10.2, 5.4, 186, 176, 187, 157, 198, 127, 10.1, 10.4, 9.4, 6.1, 16.9, 17.6]]
# # print("sample delta soil moisture prediction with precipation:", model_watering_plants.predict(test_prediction_X))
# # print(makeDecisionWatering(test_prediction_X, 0.2, 25.7))
# #
# # ###precipation, some rain and high showers - od tego miejsca not done
# # test_prediction_X = [[81, 84, 85, 86, 87, 85, 25.7, 25.0, 24.7, 24.5, 24.5, 24.7, 0.65, 0.6, 0, 0.7, 0.6, 0, 0.5, 0.6, 0.6, 0.5, 0.4, 0.1, 0.2, 0.2, 0.2, 0.1, 0.2, 0.1, 0.7, 0.9, 0.7, 0.8, 0.8, 0.85, 6.5, 5.4, 2.9, 2.7, 10.2, 5.4, 186, 176, 187, 157, 198, 127, 10.1, 10.4, 9.4, 6.1, 16.9, 17.6]]
# # print("sample delta soil moisture prediction with precipation:", model_watering_plants.predict(test_prediction_X))
# # print(makeDecisionWatering(test_prediction_X, 0.2, 25.7))
# #
# # ###precipation, rain and some showers
# # test_prediction_X = [[81, 84, 85, 86, 87, 85, 25.7, 25.0, 24.7, 24.5, 24.5, 24.7, 0.65, 0.6, 0, 0.7, 0.6, 0, 0.5, 0.6, 0.6, 0.5, 0.4, 0.3, 0.5, 0.4, 1.1, 0.75, 0.8, 0.2, 0.2, 0.25, 0.3, 0.2, 0.15, 0.15, 6.5, 5.4, 2.9, 2.7, 10.2, 5.4, 186, 176, 187, 157, 198, 127, 10.1, 10.4, 9.4, 6.1, 16.9, 17.6]]
# # print("sample delta soil moisture prediction with precipation:", model_watering_plants.predict(test_prediction_X))
# # print(makeDecisionWatering(test_prediction_X, 0.2, 25.7))
#
### current humidity + delta vs actual humidity plot on data from other year
START_DATE = "2024-01-01"
END_DATE = "2024-03-31"
forecast, forecast_actual_weather, data_X, data_Y = weather_api(START_DATE, END_DATE)
# print("forecast size ", forecast.keys())
# print("forecast size actual size ", forecast_actual_weather.keys())
predicted_water_level_difference = []
prognosed_water_level_difference = []
actual_water_level_difference = []
# print(data_X)
# print("forecast ", forecast['avg_soil_moisture'])

for i in range(FORECAST_HOURS, len(forecast['time'])):
    rain_added_sum = 0
    for j in range(FORECAST_HOURS):
        rain_added_sum += forecast['precipitation'][i - j] * ROOFTOP_SIZE / WATER_CONTAINER_SIZE
    prognosed_water_level_difference.append(rain_added_sum)

for i in range(FORECAST_HOURS, len(forecast['time'])):
    rain_added_sum = 0
    for j in range(FORECAST_HOURS):
        rain_added_sum += forecast_actual_weather['precipitation'][i - j] * ROOFTOP_SIZE / WATER_CONTAINER_SIZE
    actual_water_level_difference.append(rain_added_sum)

try:
    for i in range(len(data_X)):
        predicted_water_level_difference.append(float(model_watering_plants.predict([data_X[i]])[0]))
        predicted_water_level_difference[i] = predicted_water_level_difference[i] + prognosed_water_level_difference[i]
    print("predicted_water_level_difference: ", predicted_water_level_difference)

except Exception as e:
    print("Exception occurred:", e, " at index:", i, " with data_X:", data_X[i])
### predicted soil moisture vs feracst moisture vs actual moisture
plt.plot(forecast['time'][6:], predicted_water_level_difference, label="forecast + prediction")
plt.plot(forecast['time'][6:], actual_water_level_difference, label='actual water level difference')
plt.plot(forecast['time'][6:], prognosed_water_level_difference, label='forecast water level difference')


# print("forecast: ", forecast['avg_soil_moisture'][0])
# print("actual: ", forecast_actual_weather['soil_moisture_0_to_7cm'][0])
# print("forecast + prediction: ", predicted_water_level_difference[0])
#
# print("forecast size: ", len(forecast['avg_soil_moisture']))
# print("actual size: ", len(forecast_actual_weather['soil_moisture_0_to_7cm']))
# print("forecast + prediction size: ", len(predicted_water_level_difference))
#
plt.xlabel('time')
plt.ylabel('Predicted water level difference')
plt.title('Actual vs predicted water level difference')
plt.legend()
plt.show()
#
# ###MSE for forecast and forecast+prediction compared to actual data
print("forecast MSE: ", mean_squared_error(prognosed_water_level_difference, actual_water_level_difference))
print("forecast + prediction MSE: ", mean_squared_error(predicted_water_level_difference, actual_water_level_difference))