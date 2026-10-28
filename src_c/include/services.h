#pragma once
#include "core.h"
#include <Arduino.h>
#include <Adafruit_ADS1X15.h>
#include <Adafruit_APDS9960.h>
#include <Adafruit_LIS3DH.h>
#include <Adafruit_SSD1306.h>
#include <ArduinoJson.h>
#include <map>

namespace proto {
struct Config {
  std::map<String,String> values;
  String get(const char* key,const char* fallback="")const;
  void load(Settings&);
  void save(const Settings&);
};
class Sensors {
  Adafruit_ADS1115 ads;
  Adafruit_APDS9960 apds;
  Adafruit_LIS3DH lis;
  bool micReady=false,proxReady=false,accReady=false;
  uint8_t accAddress=0;
  int micCount=0,accCount=0;
  double micSum=0;
  float micBase=0;
  std::array<float,3> accSum{},accBase{};
  uint32_t micRetry=0,proxRetry=0,accRetry=0;
 public:
  Sensors():lis(&Wire){}
  Sample read(const Settings&,uint32_t now);
};
class Oled {
  Adafruit_SSD1306 display;
  std::array<uint8_t,1024> previous{};
  bool present=false,rendered=false;
  int scaleNum=3,scaleDen=2;
  int extent(int n) const { return (n*scaleNum+scaleDen-1)/scaleDen; }
  void text(const String&,int x,int y,int maxWidth);
 public:
  Oled():display(128,64,&Wire,-1,400000,400000){}
  bool begin(bool enabled);
  bool ready()const{return present;}
  void font(uint8_t index);
  int charWidth()const{return extent(5)+1;}
  int lineHeight()const{return extent(7)+1;}
  int visibleRows()const{return std::max(1,64/lineHeight()-1);}
  String settingText(int,const Settings&)const;
  void render(Menu&,const Settings&,const String& clock,const std::vector<String>& debug);
  void snapshot(JsonDocument&,Menu&,const Settings&,const String& clock,const std::vector<String>& debug);
};
struct Perf {
  uint32_t start=0,last=0,reportAt=0,count=0,periods=0,sectionStart=0;
  double loopTotal=0,workTotal=0,work=0;
  float loopMax=0,workMax=0,sectionMax=0;
  String section,slowest;
  JsonDocument snapshot;
  void begin(uint32_t now);
  void beginSection(const char* name);
  void endSection();
  bool end();
};
String clockText();
bool setLocalTime(int year,int month,int day,int hour,int minute,int second);
}
