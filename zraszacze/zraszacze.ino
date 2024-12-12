//sterowanie
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>

// // Dane do połączenia z Wi-Fi
// const char* ssid = "Janek Samsung";  // Nazwa sieci Wi-Fi
// const char* password = "haslo1234";   // Hasło Wi-Fi

const char* ssid = "";  // Nazwa sieci Wi-Fi
const char* password = "";           // Hasło Wi-Fi

// Tworzymy serwer na porcie 80
ESP8266WebServer server(80);

bool is_running = false;

// Obsługa zapytań GET na root ("/")
void handleRoot() {
  String response = "{\"message\": \"GET received at root\"}";
  server.send(200, "application/json", response);
}

// Obsługa zapytań GET na "/status"
void handleGetCurrentState() {
  String response;
  if (is_running == true) {
    Serial.println("zwrocono status on");
    response = "{\"status\": \"on\"}";
  } else {
    Serial.println("zwrocono status off");
    response = "{\"status\": \"off\" }";
  };
  server.send(200, "application/json", response);
}

// Obsługa zapytań POST na "/data"
void handleOff() {
  server.send(200, "application/json", "turned off");
  switchState(false);
}

// Obsługa zapytań POST na "/data"
void handleOn() {
  server.send(200, "application/json", "turned on");
  switchState(true);
}

void switchState(bool to_state){
  if (to_state) {
    //TODO turning on
    is_running = true;
    Serial.println("Zmiana statusu na on");
  } else {
        //TODO turning off
    is_running = false;
    Serial.println("Zmiana statusu na off");
  }
}

void setup() {
  Serial.begin(115200);

  // Łączenie z Wi-Fi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Łączenie z siecią WiFi...");
  }
  Serial.println("Połączono z siecią WiFi");
  Serial.println(WiFi.localIP());

  // Konfiguracja routingu
  server.on("/", HTTP_GET, handleRoot);       // Obsługa GET na "/"
  server.on("/get_current_state", HTTP_GET, handleGetCurrentState);  // Obsługa GET na "/status" //zgodne już z flask
  server.on("/turn_on", HTTP_POST, handleOn);  // zmiana statusu na on
  server.on("/turn_off", HTTP_POST, handleOff);  // zmiana statusu na off


  // Start serwera
  server.begin();
  Serial.println("Serwer HTTP działa!");
}

void loop() {
  // Nasłuchiwanie na nowe połączenia
  server.handleClient();
}
