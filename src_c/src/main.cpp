#include "core.h"
#include "animation.h"
#include "services.h"
#include <LittleFS.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <esp_arduino_version.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/task.h>
#include <deque>

using namespace proto;
namespace {
Settings settings;
Config config;
Menu menu;
AnimationWorker animation;
AnimationStatus animationStatus;
BoopTracker tracker;
Sensors sensors;
Oled oled;
Perf perf;
Sample samples;
WebServer web(80);
QueueHandle_t controlQueue=nullptr;
bool fsReady=false,httpRunning=false,espReady=false;
bool fanPwmReady=false;
bool previousButtons[3]{};
uint32_t lastDebug=0,connectAt=0,sampledAt=0;
uint32_t displayRevision=0,transitionResetRevision=0;
bool stationPending=false,backupAttempt=false;
StationAttempts stationAttempts;
int pendingNetwork=-1;
std::vector<String> debug;
std::deque<String> logs;
String lastAnimationError;
RestartRequest restartRequest;

AnimationInput animationInput(){
  AnimationInput input;
  input.settings=settings;input.samples=samples;input.sampledAt=sampledAt;
  input.menuEmote=oled.ready()?menu.activeEmote():-1;
  input.boopThreshold=tracker.threshold;
  input.displayRevision=displayRevision;input.transitionResetRevision=transitionResetRevision;
  std::snprintf(input.clock,sizeof(input.clock),"%s",clockText().c_str());
  return input;
}
void addTaskMetrics(JsonDocument& doc){
  // Both this JSON document and the received status copy belong to logic only.
  doc["logic_core"]=xPortGetCoreID();
  doc["logic_stack_free_bytes"]=uxTaskGetStackHighWaterMark(nullptr);
  doc["fan_pwm_ready"]=fanPwmReady;
  doc["fan_percent"]=FanPercent[settings.fan];
  JsonObject network=doc["wifi"].to<JsonObject>();
  network["connect_enabled"]=settings.get(WifiConnect);
  network["station_connected"]=WiFi.status()==WL_CONNECTED;
  network["connecting"]=stationPending;
  network["attempt"]=stationAttempts.count;
  network["max_attempts"]=StationAttempts::Limit;
  network["profile"]=settings.get(WifiConnect)?(backupAttempt?"backup":"main"):"";
  network["ip"]=WiFi.status()==WL_CONNECTED?WiFi.localIP().toString():String("");
  JsonObject a=doc["animation"].to<JsonObject>();
  a["core"]=animationStatus.core;a["ready"]=animationStatus.ready;
  a["frames"]=animationStatus.frames;a["logical_ticks"]=animationStatus.logicalTicks;
  a["period_avg_ms"]=animationStatus.periodAvgMs;a["period_max_ms"]=animationStatus.periodMaxMs;
  a["work_avg_ms"]=animationStatus.workAvgMs;a["work_max_ms"]=animationStatus.workMaxMs;
  a["stack_free_bytes"]=animationStatus.stackFreeBytes;
  a["input_stale"]=animationStatus.inputStale;
  a["status_age_ms"]=animationStatus.core<0?0:uint32_t(millis()-animationStatus.updatedAt);
  a["error"]=animationStatus.error;
}

void log(const String& message){Serial.println(message);logs.push_back(message);if(logs.size()>100)logs.pop_front();}
void applyFan(){
  if(!fanPwmReady)return;
  // Arduino selects the 40 MHz XTAL clock on S3: 25 kHz permits 10 bits.
  uint32_t duty=fanDuty(FanPercent[settings.fan]);
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWrite(A1,duty);
#else
  ledcWrite(0,duty);
#endif
}
void receiveControl(const uint8_t* bytes,int length){
  Input input;if(decode(bytes,length,input)&&controlQueue)xQueueSend(controlQueue,&input,0);
}
#if ESP_ARDUINO_VERSION_MAJOR >= 3
void onReceive(const esp_now_recv_info_t*,const uint8_t* data,int len){receiveControl(data,len);}
#else
void onReceive(const uint8_t*,const uint8_t* data,int len){receiveControl(data,len);}
#endif
void ensureEsp(){if(!espReady){espReady=esp_now_init()==ESP_OK;
  if(espReady)esp_now_register_recv_cb(onReceive);else log("ESP-NOW init failed");}}
void stopHttp(){if(httpRunning)web.stop();httpRunning=false;MDNS.end();}
void startHttp(bool station){
  if(station&&MDNS.begin(config.get("DEVICE_HOSTNAME","protogen").c_str()))MDNS.addService("http","tcp",80);
  web.begin();httpRunning=true;
  log("HTTP: http://"+(station?WiFi.localIP():WiFi.softAPIP()).toString()+"/");
}
void fallback(){
  WiFi.disconnect(false,false);WiFi.softAPdisconnect(false);WiFi.mode(WIFI_AP_STA);
  String ssid=config.get("DEVICE_HOSTNAME","protogen")+"-fallback";
  if(!WiFi.softAP(ssid.c_str(),nullptr,1,false,1))log("Fallback AP failed");
  esp_wifi_set_channel(1,WIFI_SECOND_CHAN_NONE);
}
void requestBroadcast(){
  stationPending=false;
  // Reuse the regular AP transition, outside HTTP handlers, including NVS save.
  pendingNetwork=2;
  log("Wi-Fi connection unavailable; switching to Wifi_Broadcast");
}
void beginStation(bool backup){
  backupAttempt=backup;
  String ssid=config.get(backup?"BACKUP_WIFI_SSID":"HOME_WIFI_SSID");
  String password=config.get(backup?"BACKUP_WIFI_PASSWORD":"HOME_WIFI_PASSWORD");
  if(ssid.isEmpty()){
    // Empty profiles are not attempts. With one configured profile, try it twice.
    backupAttempt=!backup;
    ssid=config.get(backupAttempt?"BACKUP_WIFI_SSID":"HOME_WIFI_SSID");
    password=config.get(backupAttempt?"BACKUP_WIFI_PASSWORD":"HOME_WIFI_PASSWORD");
    if(ssid.isEmpty()){requestBroadcast();return;}
  }
  if(!stationAttempts.start()){requestBroadcast();return;}
  WiFi.softAPdisconnect(false);
  WiFi.begin(ssid.c_str(),password.c_str());connectAt=millis();stationPending=true;
  log(String("Wi-Fi attempt ")+stationAttempts.count+"/2: "+ssid);
}
// Must run outside an active WebServer handler, including network toggle requests.
void changeNetwork(int mode,bool persist){
  stopHttp();stationPending=false;
  if(mode==1)stationAttempts.reset();
  WiFi.setAutoReconnect(false);WiFi.persistent(false);
  WiFi.disconnect(false,false);WiFi.softAPdisconnect(false);
  WiFi.mode(WIFI_AP_STA);WiFi.setHostname(config.get("DEVICE_HOSTNAME","protogen").c_str());
  settings.set(WifiConnect,mode==1);settings.set(WifiBroadcast,mode==2);settings.deriveWifi();
  if(mode==2){
    String ssid=config.get("AP_SSID","Alan_Protogen-");if(ssid.isEmpty())ssid="Alan_Protogen-";
    String password=config.get("AP_PASSWORD");
    if(WiFi.softAP(ssid.c_str(),password.isEmpty()?nullptr:password.c_str(),1,false,4))startHttp(false);
    else{log("AP start failed");settings.set(WifiBroadcast,false);settings.deriveWifi();fallback();}
  }else if(mode==1)beginStation(false);
  else fallback();
  ensureEsp();if(persist)config.save(settings);
}
void pollNetwork(){
  if(pendingNetwork>=0){int mode=pendingNetwork;pendingNetwork=-1;changeNetwork(mode,true);}
  if(stationPending){
    if(WiFi.status()==WL_CONNECTED){stationPending=false;stationAttempts.reset();startHttp(true);
      // ESP32 keeps system time in local wall-clock convention for compatibility
      // with /api/time. Server offset is applied by libc TZ, not by the browser.
      configTime(2*3600,0,"tak.cesnet.cz");
    }else if(uint32_t(millis()-connectAt)>=WifiAttemptMs){
      WiFi.disconnect(false,false);
      if(stationAttempts.exhausted())requestBroadcast();
      else beginStation(!backupAttempt);
    }
  }else if(settings.get(WifiConnect)&&WiFi.status()!=WL_CONNECTED){
    stopHttp();WiFi.disconnect(false,false);beginStation(false);
  }
}
void setSetting(int index){
  if(index<0||index>=BackSetting)return;
  if(index==HwResetSetting){
    restartRequest.request(millis());
    log("HW Reset requested; restarting in 300 ms");
    return;
  }
  if(index==1){settings.brightness=(settings.brightness+1)%5;++displayRevision;}
  else if(index==2){settings.font=(settings.font+1)%3;oled.font(settings.font);}
  else if(index==3){settings.fan=(settings.fan+1)%3;applyFan();}
  else if(index==5){tracker.calibrate(samples.proximity,samples.proxValid);return;}
  else if(SettingFlags[index]>=0){Flag f=Flag(SettingFlags[index]);bool enabled=!settings.get(f);
    settings.set(f,enabled);
    // The rendering task owns all display lifetime and transition operations.
    if(f==Display)++displayRevision;
    if(f==SmoothTransitions&&!enabled)++transitionResetRevision;
    if(f==WifiConnect||f==WifiBroadcast){
      settings.set(f==WifiConnect?WifiBroadcast:WifiConnect,false);settings.deriveWifi();
      pendingNetwork=enabled?(f==WifiConnect?1:2):0;
    }
  }
  config.save(settings);
}
void action(Action a){if(oled.ready())setSetting(menu.action(a));}
String json(const JsonDocument& document){String result;serializeJson(document,result);return result;}
void replyMenu(){
  oled.render(menu,settings,clockText(),debug);
  JsonDocument doc;oled.snapshot(doc,menu,settings,clockText(),debug);web.send(200,"application/json",json(doc));
}
void routeAction(Action a){action(a);replyMenu();}
void setupRoutes(){
  web.on("/",HTTP_GET,[]{File f=LittleFS.open("/static/index.html","r");if(f)web.streamFile(f,"text/html");
    else web.send(200,"text/html","<!doctype html><h1>Menu UI unavailable</h1><p>Missing /static/index.html</p>");});
  web.on("/menu",HTTP_GET,replyMenu);web.on("/api/menu",HTTP_GET,replyMenu);
  web.on("/up",HTTP_GET,[]{routeAction(Action::Up);});
  web.on("/down",HTTP_GET,[]{routeAction(Action::Down);});
  web.on("/ok",HTTP_GET,[]{routeAction(Action::Ok);});
  web.on("/api/action/up",HTTP_GET,[]{routeAction(Action::Up);});
  web.on("/api/action/down",HTTP_GET,[]{routeAction(Action::Down);});
  web.on("/api/action/ok",HTTP_GET,[]{routeAction(Action::Ok);});
  web.on("/api/action/back",HTTP_GET,[]{routeAction(Action::Back);});
  web.on("/api/perf",HTTP_GET,[]{addTaskMetrics(perf.snapshot);web.send(200,"application/json",json(perf.snapshot));});
  web.on("/api/time",HTTP_GET,[]{
    const char* names[]={"year","month","day","hour","minute","second"};int v[6]{};bool valid=true;
    for(int i=0;i<6;i++){String value=web.arg(names[i]);if(!web.hasArg(names[i])||value.isEmpty()){valid=false;break;}
      char* end=nullptr;long number=strtol(value.c_str(),&end,10);if(*end||number<0||number>9999){valid=false;break;}v[i]=int(number);}
    JsonDocument doc;
    if(valid&&setLocalTime(v[0],v[1],v[2],v[3],v[4],v[5])){doc["ok"]=true;doc["clock_text"]=clockText();}
    else{doc["ok"]=false;doc["error"]="invalid_datetime";}
    web.send(200,"application/json",json(doc));
  });
  web.serveStatic("/static/",LittleFS,"/static/");
}
void updateDebug(){
  debug.clear();
  debug.push_back(samples.motionValid?String("Acc: ")+String(samples.dx,2)+","+String(samples.dy,2):String("Acc: --"));
  debug.push_back(samples.micValid?String("Mic: ")+String(samples.mic,2):String("Mic: --"));
  debug.push_back(samples.proxValid?String("APDS: ")+samples.proximity:String("APDS: --"));
  debug.push_back(String("Boop T: ")+tracker.threshold);
  debug.push_back(String("Loop: ")+String(perf.snapshot["loop_avg_ms"].as<float>(),1)+"/"+String(perf.snapshot["loop_max_ms"].as<float>(),1)+"ms");
  debug.push_back(String("Work: ")+String(perf.snapshot["work_avg_ms"].as<float>(),1)+"ms "+String(perf.snapshot["load_pct"].as<float>(),0)+"%");
  debug.push_back(String("Mem: ")+perf.snapshot["mem_free"].as<unsigned long>()+"B");
  debug.push_back(String("Anim C")+animationStatus.core+": "+String(animationStatus.periodAvgMs,1)+"ms");
}
}
void initializeLogic(){
  Wire.begin(SDA,SCL);Wire.setClock(400000);Wire.setTimeOut(25);
  setenv("TZ","UTC0",1);tzset();
  // Do not format on a mount failure: an absent image must be visible to the user.
  // Match the partition NAME in partitions.csv. Arduino's default is "spiffs",
  // which does not exist in this project even though the subtype is spiffs.
  fsReady=LittleFS.begin(false,"/littlefs",10,"littlefs");
  if(!fsReady)log("LittleFS partition 'littlefs' mount failed: upload filesystem image");
  else{
    File required=LittleFS.open("/transitions/mouth--mouth_speak.mph","r");
    log(String("LittleFS mounted: ")+LittleFS.usedBytes()+"/"+LittleFS.totalBytes()+
        " bytes; mouth transition: "+(required?String(required.size())+" bytes":"MISSING"));
  }
  config.load(settings);
  pinMode(PIN_BUTTON_UP,INPUT_PULLUP);pinMode(PIN_BUTTON_DOWN,INPUT_PULLUP);pinMode(A4,INPUT_PULLUP);
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  fanPwmReady=ledcAttach(A1,FanPwmHz,FanPwmBits);
#else
  fanPwmReady=ledcSetup(0,FanPwmHz,FanPwmBits)>0;
  if(fanPwmReady)ledcAttachPin(A1,0);
#endif
  if(!fanPwmReady)log("Fan PWM initialization failed on A1/GPIO3");
  else log(String("Fan PWM ready: A1/GPIO3, 25000 Hz, 10 bit, requested ")+FanPercent[settings.fan]+"%");
  applyFan();
  if(!oled.begin(settings.oled))log("OLED unavailable: reference UI is disabled");
  oled.font(settings.font);
  controlQueue=xQueueCreate(16,sizeof(Input));
  if(!controlQueue||!animation.begin(animationInput())){
    log("Failed to allocate dual-core tasks/queues");
    for(;;)vTaskDelay(pdMS_TO_TICKS(1000));
  }
  setupRoutes();
  changeNetwork(settings.get(WifiBroadcast)?2:settings.get(WifiConnect)?1:0,false);
  log("ESP-NOW receiver MAC (STA): "+WiFi.macAddress());
  for(auto key:{"loops","loop_avg_ms","loop_max_ms","work_avg_ms","work_max_ms","load_pct","mem_free","mem_alloc","slowest_section_ms"})perf.snapshot[key]=0;
  perf.snapshot["ok"]=true;perf.snapshot["slowest_section"]="";
  oled.render(menu,settings,clockText(),debug);
  log("Logic pinned to core 0; animation pinned to core 1");
}
void logicStep(){
  // Run after the previous HTTP handler returned so its reply can leave first.
  if(restartRequest.due(millis())){ESP.restart();return;}
  uint32_t now=millis();perf.begin(micros());
  if(animation.status(animationStatus)){
    String error=animationStatus.error;
    if(error!=lastAnimationError){if(error.length())log(error);lastAnimationError=error;}
  }
  perf.beginSection("sensors");samples=sensors.read(settings,now);
  sampledAt=millis();
  tracker.update(samples.proximity,samples.proxValid,sampledAt,animationStatus.boopActive);perf.endSection();
  perf.beginSection("buttons");Input remote;
  bool have=controlQueue&&xQueueReceive(controlQueue,&remote,0)==pdTRUE;
  bool pressed[]={digitalRead(PIN_BUTTON_UP)==LOW,digitalRead(PIN_BUTTON_DOWN)==LOW,digitalRead(A4)==LOW};
  bool confirm=(pressed[0]&&!previousButtons[0])||(have&&remote.ok);
  bool next=(pressed[1]&&!previousButtons[1])||(have&&remote.down);
  bool prev=(pressed[2]&&!previousButtons[2])||(have&&remote.up);
  perf.endSection();
  perf.beginSection("ui");bool wasDebug=menu.screen==Screen::Debug;
  if(have&&remote.back)action(Action::Back);
  // Match Python's simultaneous-input order. Do not turn confirm into a cursor-up.
  Screen inputScreen=menu.screen;
  if(oled.ready()&&inputScreen==Screen::Debug){if(prev||next||confirm)action(Action::Back);}
  else if(oled.ready()&&menu.list()<0){if(prev||next)action(Action::Back);}
  else{if(prev)action(Action::Up);if(next)action(Action::Down);if(confirm)action(Action::Ok);}
  if(menu.screen==Screen::Debug&&(!wasDebug||uint32_t(now-lastDebug)>=1000)){updateDebug();lastDebug=now;}
  oled.render(menu,settings,clockText(),debug);perf.endSection();
  perf.beginSection("server");pollNetwork();if(httpRunning)web.handleClient();perf.endSection();
  perf.beginSection("animation_publish");animation.publish(animationInput());perf.endSection();
  for(int i=0;i<3;i++)previousButtons[i]=pressed[i];
  if(perf.end()){addTaskMetrics(perf.snapshot);if(settings.get(Verbose))log(json(perf.snapshot));}
  if(settings.get(Verbose)){log(String("Mic: ")+(samples.micValid?String(samples.mic):"--")+" APDS: "+(samples.proxValid?String(samples.proximity):"--")+" T: "+tracker.threshold);}
}
namespace {
void logicTask(void*){
  initializeLogic();
  for(;;){
    TickType_t wake=xTaskGetTickCount();
    logicStep();
    TickType_t period=std::max<TickType_t>(1,pdMS_TO_TICKS(TickMs));
    TickType_t elapsed=xTaskGetTickCount()-wake;
    vTaskDelay(elapsed<period?period-elapsed:1);
  }
}
}
void setup(){
  Serial.begin(115200);
  if(xTaskCreatePinnedToCore(logicTask,"proto_logic",LogicStackBytes,
                            nullptr,1,nullptr,LogicCore)!=pdPASS){
    Serial.println("Failed to create core 0 logic task");
    for(;;)delay(1000);
  }
}
void loop(){
  // Arduino setup/loop runs on core 1 by default. Both real application tasks
  // are explicitly pinned, so release this unused loop task and its stack.
  vTaskDelete(nullptr);
}
