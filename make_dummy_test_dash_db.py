import sqlite3
import random

import numpy as np


# Funkcja do tworzenia testowej bazy danych i dodawania danych
def create_dummy_db():
    # Połączenie z bazą danych (utworzy nową bazę, jeśli nie istnieje)
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()

    cursor.execute('''DROP TABLE IF EXISTS measurements_test''')


    # Tworzenie tabeli "measurements"
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS measurements_test (
    occurance_time TIMESTAMP PRIMARY KEY, sprinkler_state INTEGER, sprinkler_auto_mode INTEGER, temperature REAL, humidity REAL, rain REAL
        )
    ''')

    # Dodanie przykładowych danych do tabeli
    dummy_data = []
    random_walk_humidity = 50
    random_walk_temperature = 20
    for i in range(10, 23):
        for j in range(10):
            random_walk_humidity += (random.randrange(1, 10) - 5)/10
            random_walk_temperature += (random.randrange(1, 11) - 5)/10
            dummy_data.append((f'2024-11-20 {i}:0{j}', 0, 0, random_walk_humidity, random_walk_temperature))
        for j in range(10, 60):
            random_walk_humidity += (random.randrange(1, 10) - 5)/10
            random_walk_temperature += (random.randrange(1, 10) - 5)/10
            dummy_data.append((f'2024-11-20 {i}:{j}', 0, 0, random_walk_humidity, random_walk_temperature ))

    # Wstawianie danych do tabeli
    cursor.executemany('''
        INSERT INTO measurements_test (occurance_time,sprinkler_state, sprinkler_auto_mode, temperature, humidity )
        VALUES (?, ?, ?, ?, ?)
    ''', dummy_data)

    # Zatwierdzenie zmian
    conn.commit()

    cursor.execute('SELECT * FROM measurements_test')
    print(cursor.fetchall())

    # Zamknięcie połączenia
    conn.close()

create_dummy_db()