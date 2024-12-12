//arduino obsługa zbiornika na wodę
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266HTTPClient.h>  // Biblioteka dla HTTP GET
#include <ArduinoJson.h>        // Biblioteka dla JSON

const char* ssid = "";  // Nazwa sieci Wi-Fi
const char* password = "";           // Hasło Wi-Fi

ESP8266WebServer server(80);

// Stan zbiornika początkowy
bool adding_water = false;
float predicted_rain = 0.0;
bool critical_level = false;

// Konfiguracja początkowa
float min_water_level = 20;      // Poziom poniżej którego woda nie powinna schodzić
float critical_water_level = 10; // Poziom krytyczny

// Poziom wody  początkowy
float current_level = 25;

//czy_jest_sterowanie_manualne
bool manual_steering = true;

//do robienia delaya pobierania pogody (get_forecast)
unsigned long lastActionTime = 1001;  // Zmienna do zapamiętania ostatniego czasu akcji
unsigned long delayTime = 10000;    // Opóźnienie w milisekundach (10 sekunda)

void setup() {
  Serial.begin(115200);

  // Połączenie z Wi-Fi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Łączenie zbiornika z siecią WiFi...");
  }
  Serial.println("Połączono zbiornik z siecią WiFi");
  Serial.println(WiFi.localIP());

  // Konfiguracja routingu
  server.on("/on", HTTP_POST, handleOn);
  server.on("/off", HTTP_POST, handleOff);
  server.on("/auto", HTTP_POST, handleAuto);

  // mock na czujnik poziomu wody
  server.on("/update_water_level", HTTP_POST, handleUpdateLevel);
  
  server.on("/get_status", HTTP_GET, handleGetStatus);

  // Start serwera
  server.begin();
  Serial.println("Serwer HTTP działa!");
}

void loop() {

/*
1. sprawdzenie predykcji zmiany poziomu wody (co jakiś czas - na przykład minutę) - done przez get_forecast
2.Sprawdzenie poziomu wody
3.Obsługa serwera do żądań z mikrokomputera - na przykład sprawdzenie poziomu wody
4.Podjęcie decyzji o zmianie stanu zbiornika
*/

  //sprawdzenie predykcji prognozy pogody
  ///obsługa prognozy modelu predykcyjnego co określony okres czasu
  unsigned long currentMillis = millis();
  if (currentMillis - lastActionTime >= delayTime) {
    get_forecast();
    // Serial.println("Akcja wykonana po opóźnieniu");
    lastActionTime = currentMillis;
    
  if (manual_steering == false){
    check_and_start_adding_water_if_needed();
  }

  }
  server.handleClient();  // Obsługa połączeń HTTP

  // // Odczyt poziomu wody i logika napełniania
  update_water_level();

}

void handleGetStatus() {
  String response;
  response = "{\"manual_mode\":" + String(manual_steering) + ", \"water_level\":" + String(current_level) + ", \"water_pump_state\":" + String(adding_water) + "}";
  server.send(200, "application/json", response);
}


void update_water_level() {
  // TODO odczyt poziomu wody - w zależności od rodzaju czujnika
  // current_level = odczyt z czujnika
  //tupowinno dochodzić do zmiany poziomu wody
  if (current_level < 0 || current_level > 100) {
    //obsługa awarii odczytu
  }
  // Serial.print("Aktualny poziom wody: ");
  // Serial.println(current_level);
}

void check_and_start_adding_water_if_needed() {
  //sprawdzenie czy aktualny poziom + predykcja są mniejsze niż zakłądana
  if(current_level + predicted_rain < min_water_level || current_level <= critical_water_level) {
    start_adding_water();
  } else {
    stop_adding_water();
  }
}

void get_forecast() {
  HTTPClient http;
  WiFiClient client;
  String forecast_url = "http://192.168.100.189:4000/get_rain_forecast"; //URL do servera

  http.begin(client, forecast_url);

  

  int httpCode = http.GET();
  if (httpCode == 200) {
    String payload = http.getString();
    DynamicJsonDocument doc(1024);
    DeserializationError error = deserializeJson(doc, payload);

    if (error) {
      Serial.println("Błąd deserializacji JSON: ");
      Serial.println(error.f_str());
      return;
    }

     if (doc.containsKey("prediction")) {
      float prediction = doc["prediction"];  // Pobierz wartość klucza "prediction"
      predicted_rain = prediction;
      // Wyświetl otrzymaną wartość
      Serial.println("Wartość prognozy (prediction): ");
      Serial.println(prediction);
      
      // Można tu podjąć dalsze akcje z tą wartością, np. zapisać w zmiennej globalnej lub wykorzystać w logice programu.
    } else {
      Serial.println("Klucz 'prediction' nie został znaleziony w odpowiedzi.");
    }

      if (doc.containsKey("min_level") && doc.containsKey("crit_level")) {
      min_water_level = doc["min_level"];  // Pobierz wartość klucza "min_level"
      critical_water_level = doc["crit_level"];  // Pobierz wartość klucza "min_level"
      // Wyświetl otrzymaną wartość
      Serial.println("Wartość preferowana (min_water_level): ");
      Serial.println(min_water_level);
      Serial.println("Wartość krytyczna (critical_water_level): ");
      Serial.println(critical_water_level);
    } 
  } else {
    Serial.println("Błąd HTTP: ");
    Serial.println(httpCode);  // Wyświetl kod błędu HTTP
  }
  http.end();
}


void start_adding_water() {
  adding_water = true;
  Serial.println("napełnianie zbiornika.");
}

void stop_adding_water() {
  adding_water = false;
  Serial.println("Zakończono napełnianie zbiornika.");
}

// Endpointy manualne
void handleOn() {
  manual_steering = true;
  adding_water = true;
  start_adding_water();
  Serial.println("Ręczne uruchomienie napełniania przez API.");
  server.send(200, "text/plain", "Napełnianie uruchomione.");
}

void handleOff() {
  manual_steering = true;
  adding_water = false;
  stop_adding_water();
  Serial.println("Ręczne zatrzymanie napełniania przez API.");
  server.send(200, "text/plain", "Napełnianie zatrzymane.");
}

void handleAuto() {
  manual_steering = false;
  Serial.println("wejście w tryb automatyczny");
  server.send(200, "text/plain", "tryb auto");
}


//mock czujnika do obsługi z postmana
void handleUpdateLevel() {
  // Sprawdź, czy ciało żądania jest w formacie JSON
  if (server.hasArg("plain")) {
    String body = server.arg("plain");
    
    // Tworzymy obiekt do parsowania JSON
    DynamicJsonDocument doc(1024);  // Alokujemy pamięć dla dokumentu JSON
    DeserializationError error = deserializeJson(doc, body);

    if (error) {
      Serial.println("Error parsing JSON");
      server.send(400, "application/json", "{\"error\":\"Invalid JSON\"}");
      return;
    }
    
    // Pobierz wartość level z JSON-a
    float new_level = doc["level"];  // Zmienna "level" z requesta
    
    // Zaktualizuj zmienną current_level
    current_level = new_level;
    
    // Odpowiedź na request
    String response = "{\"current_level\": " + String(current_level) + "}";
    server.send(200, "application/json", response);
    
    Serial.print("Updated water level to: ");
    Serial.println(current_level);
  } else {
    server.send(400, "application/json", "{\"error\":\"No body in request\"}");
  }
}

