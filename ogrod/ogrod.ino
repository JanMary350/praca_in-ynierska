#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <ArduinoJson.h>  // Dodajemy do tworzenia JSON

#include <ESP8266WebServer.h>
#include <ESP8266HTTPClient.h>  // Biblioteka dla HTTP

#define DHTPIN D0         // Pin czujnika
#define DHTTYPE DHT22     // Typ czujnika DHT11 lub DHT22

const char* ssid = "";  // Nazwa sieci Wi-Fi
const char* password = "";           // Hasło Wi-Fi
const char* mqtt_server = "192.168.100.189"; // Adres IP brokera MQTT

ESP8266WebServer server(80); //do mockowania czujników

unsigned long lastActionTime = 10001;  // Zmienna do zapamiętania ostatniego czasu akcji
unsigned long delayTime = 10000;    // Opóźnienie w milisekundach (10 sekunda)


struct {
  float temperature = 11.4;      // temperatura powietrza
  float air_humidity = 13.2;     // wilgotność powietrza
  float soil_moisture = 11.1;    // wilgotność gleby
} sprinkler_status;

WiFiClient espClient;
PubSubClient client(espClient);
DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200);

  
  dht.begin();
  setup_wifi();
  client.setServer(mqtt_server, 1883);

  server.on("/mock_sensors", HTTP_POST, handleSensorsMock);
  server.begin();
  Serial.println("Serwer HTTP działa!");
}

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Lacze sie z Wi-Fi: ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi polaczone");
  Serial.println("ip mikrokontrol");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Lacze sie z MQTT brokerem: ");
    Serial.println(mqtt_server);
    if (client.connect("ESP8266Client")) {
      Serial.println("Polaczenie z MQTT udane");
    } else {
      Serial.print("Blad polaczenia, kod=");
      Serial.println(client.state());
      delay(1000);
    }
  }
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  server.handleClient();

  unsigned long currentMillis = millis();
  if (currentMillis - lastActionTime >= delayTime) {
      lastActionTime = currentMillis;
      // float temperature = dht.readTemperature();
      // if (isnan(temperature)) {
      //   Serial.println("Błąd odczytu temperatury!");
      //   sprinkler_status.temperature = 22.0;
      // } else {
      //   sprinkler_status.temperature = temperature;
      // }
      // float humidity = dht.readHumidity();
      // if (isnan(humidity)) {
      //   Serial.println("Błąd odczytu wilgotności powietrza!");
      //   sprinkler_status.air_humidity = 26.0;
      // } else {
      //   sprinkler_status.air_humidity = humidity;
      // }

      // Odczyt temperatury i wilgotności z DHT
      //dht.readTemperature();
      // sprinkler_status.air_humidity = 28; //dht.readHumidity();
      // sprinkler_status.soil_moisture = 27; //sprinkler_status.air_humidity; // Tymczasowe przypisanie

      // Sprawdzenie, czy odczyty są poprawne
      if (isnan(sprinkler_status.temperature) || isnan(sprinkler_status.air_humidity)) {
        Serial.println("Blad odczytu z DHT");
        return;
      }

      // Utworzenie JSON
      StaticJsonDocument<200> jsonDoc;
      jsonDoc["temperature"] = sprinkler_status.temperature;
      jsonDoc["air_humidity"] = sprinkler_status.air_humidity;
      jsonDoc["soil_moisture"] = sprinkler_status.soil_moisture;

      // Serializacja JSON do bufora
      char buffer[256];
      size_t n = serializeJson(jsonDoc, buffer);

      // Publikacja JSON w MQTT
      client.publish("sensor/status", buffer, n);

      // Wyświetlenie JSON w serial monitorze
      Serial.print("Wyslany JSON: ");
      Serial.println(buffer);
  }

}
//mock czujnikow do obsługi z postmana
void handleSensorsMock() {
// Sprawdź, czy ciało żądania jest w formacie JSON
if (server.hasArg("plain")) {
  String body = server.arg("plain");
  
  // Tworzymy obiekt do parsowania JSON
  DynamicJsonDocument doc(512);  // Alokujemy pamięć dla dokumentu JSON
  DeserializationError error = deserializeJson(doc, body);

  if (error) {
    Serial.println("Error parsing JSON");
    server.send(400, "application/json", "{\"error\":\"Invalid JSON\"}");
    return;
  }
  
  // Pobierz wartość level z JSON-a
  float new_temp = doc["temp"];  // Zmienna "temp" z requesta
  float new_moisture = doc["soil_moisture"];  // Zmienna "wilgotnosci_gleby" z requesta
  float new_humidity = doc["air_humidity"];  // Zmienna "wilgotnosc powietrza" z requesta
  // Zaktualizuj zmienną current_level
  sprinkler_status.temperature = new_temp;
  sprinkler_status.soil_moisture = new_moisture;
  sprinkler_status.air_humidity = new_humidity;
  
  // Odpowiedź na request
  String response = "{\"current_levels\": \"updated\"}";
  server.send(200, "application/json", response);
  
  Serial.println("new temp, moisture and humidity:");
  Serial.println(String(sprinkler_status.temperature) + " " + String(sprinkler_status.soil_moisture) + " " + String(sprinkler_status.air_humidity));
} else {
  server.send(400, "application/json", "{\"error\":\"something is wrong, but received\"}");
}
}