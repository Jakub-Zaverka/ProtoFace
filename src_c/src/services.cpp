#include "services.h"
#include "fonts.h"
#include <LittleFS.h>
#include <Preferences.h>
#include <Wire.h>
#include <esp_heap_caps.h>
#include <sys/time.h>
#include <algorithm>
#include <cmath>
#include <cstring>

namespace proto {
String Config::get(const char* key,const char* fallback)const{auto i=values.find(key);return i==values.end()?String(fallback):i->second;}
void Config::load(Settings& s){
  File f=LittleFS.open("/settings.toml","r");
  while(f&&f.available()){
    String line=f.readStringUntil('\n');line.trim();if(!line.length()||line[0]=='#')continue;
    int eq=line.indexOf('=');if(eq<1)continue;
    String key=line.substring(0,eq),value=line.substring(eq+1);key.trim();value.trim();
    // The supported TOML subset is flat strings/bools, as in settings.example.toml.
    if(value.startsWith("\"")||value.startsWith("'")){
      char quote=value[0];int end=value.lastIndexOf(quote);if(end<=0)continue;value=value.substring(1,end);
    }else{int hash=value.indexOf('#');if(hash>=0)value=value.substring(0,hash);value.trim();}
    values[key]=value;
  }
  for(int i=0;i<14;i++)if(i!=Wifi&&values.count(FlagKeys[i]))s.set(Flag(i),get(FlagKeys[i])=="true");
  if(values.count("SSD1306_ON"))s.oled=get("SSD1306_ON")=="true";
  Preferences prefs;
  bool saved=false;
  if(prefs.begin("protoface",true)){
    uint8_t b[9];size_t n=prefs.getBytesLength("pfs");
    if(n<=sizeof(b)&&n>=5){prefs.getBytes("pfs",b,n);saved=s.import(b,n);}prefs.end();
  }
  // Optional one-time export from CircuitPython NVM. Never overwrite a newer NVS record.
  if(!saved){File legacy=LittleFS.open("/runtime.pfs","r");uint8_t b[9];
    if(legacy){size_t n=legacy.read(b,9);if(s.import(b,n))save(s);}}
  s.deriveWifi();
}
void Config::save(const Settings& s){Preferences prefs;if(prefs.begin("protoface",false)){
  auto bytes=s.encode();if(prefs.putBytes("pfs",bytes.data(),bytes.size())!=bytes.size())Serial.println("NVS write failed");prefs.end();
}else Serial.println("NVS unavailable");}
namespace {
bool ack(uint8_t a){Wire.beginTransmission(a);return Wire.endTransmission()==0;}
float round2(float x){return std::round(x*100)/100;}
}
Sample Sensors::read(const Settings& s,uint32_t now){
  Sample out;
  if(!s.get(Mic)){micReady=false;micCount=0;micSum=0;}
  else{
    if(!micReady&&!before(now,micRetry)){
      micReady=ads.begin(0x48,&Wire);micRetry=now+1000;micCount=0;micSum=0;
      if(micReady){ads.setGain(GAIN_ONE);ads.setDataRate(RATE_ADS1115_860SPS);}
    }
    if(micReady){
      if(!ack(0x48)){micReady=false;micCount=0;micSum=0;micRetry=now+1000;}
      else{
        // ADS1115 AnalogIn.value returns signed 16-bit counts directly (no shift).
        // The blocking readADC_SingleEnded() has an unbounded conversion poll.
        // Use the official asynchronous API with our own deadline for hot unplug.
        ads.startADCReading(ADS1X15_REG_CONFIG_MUX_SINGLE_0,false);
        uint32_t conversionStart=micros();bool converted=false;
        while(uint32_t(micros()-conversionStart)<10000){
          if(!ack(0x48))break;
          if(ads.conversionComplete()){converted=true;break;}
          delayMicroseconds(100);
        }
        float raw=converted?ads.getLastConversionResults():0;
        if(!converted||!ack(0x48)){micReady=false;micRetry=now+1000;}
        else if(micCount<20){micSum+=raw;if(++micCount==20)micBase=micSum/20;}
        else{out.micValid=true;out.mic=round2(std::abs(raw-micBase)/1000);}
      }
    }
  }
  if(!s.get(Boop))proxReady=false;
  else{
    if(!proxReady&&!before(now,proxRetry)){
      proxReady=apds.begin(712,APDS9960_AGAIN_4X,0x39,&Wire);proxRetry=now+1000;
      if(proxReady){
        apds.setProxGain(APDS9960_PGAIN_1X);
        apds.setProxPulse(APDS9960_PPULSELEN_8US,1);
        apds.setLED(APDS9960_LEDDRIVE_100MA,APDS9960_LEDBOOST_100PCNT);
        apds.enableProximity(true);apds.enableColor(true);
      }
    }
    if(proxReady){if(ack(0x39)){out.proximity=apds.readProximity();out.proxValid=ack(0x39);}
      if(!out.proxValid){proxReady=false;proxRetry=now+1000;}}
  }
  if(!s.get(Accel)){accReady=false;accCount=0;accSum={};}
  else{
    if(!accReady&&!before(now,accRetry)){
      accAddress=ack(0x19)?0x19:0x18;accReady=lis.begin(accAddress);accRetry=now+1000;accCount=0;accSum={};
      if(accReady)lis.setRange(LIS3DH_RANGE_2_G);
    }
    if(accReady){
      if(!ack(accAddress)){accReady=false;accRetry=now+1000;}
      else{
        sensors_event_t event;lis.getEvent(&event);
        float v[]={event.acceleration.x,event.acceleration.y,event.acceleration.z};
        if(!ack(accAddress)){accReady=false;accRetry=now+1000;}
        else if(accCount<20){for(int i=0;i<3;i++)accSum[i]+=v[i];if(++accCount==20)for(int i=0;i<3;i++)accBase[i]=accSum[i]/20;}
        else{out.motionValid=true;out.dx=round2(v[0]-accBase[0]);out.dy=round2(v[1]-accBase[1]);out.dz=round2(v[2]-accBase[2]);}
      }
    }
  }
  return out;
}
bool Oled::begin(bool enabled){present=enabled&&ack(0x3c)&&display.begin(SSD1306_SWITCHCAPVCC,0x3c,false,false);return present;}
void Oled::font(uint8_t i){static const int num[]={3,2,5},den[]={2,1,2};scaleNum=num[i%3];scaleDen=den[i%3];}
void Oled::text(const String& value,int x,int y,int maxWidth){
  int ox=x;for(size_t i=0;i<value.length();i++){
    char c=value[i];if(c>='a'&&c<='z')c-=32;auto cols=oledGlyph(c);
    // Match Python's overlapping ceil-scaled source pixels at fractional scales.
    for(int sx=0;sx<5;sx++)for(int sy=0;sy<7;sy++)if(cols[sx]&(1<<sy))
      for(int dx=sx*scaleNum/scaleDen;dx<((sx+1)*scaleNum+scaleDen-1)/scaleDen;dx++)
        for(int dy=sy*scaleNum/scaleDen;dy<((sy+1)*scaleNum+scaleDen-1)/scaleDen;dy++)
          if(x+dx<ox+maxWidth)display.drawPixel(x+dx,y+dy,SSD1306_WHITE);
    x+=charWidth();if(x>=ox+maxWidth)break;
  }
}
String Oled::settingText(int i,const Settings& s)const{
  if(i==1)return String(Brightness[s.brightness],1);
  if(i==2){static const char* labels[]={"1.5x","2x","2.5x"};return labels[s.font];}
  if(i==3)return String(FanPercent[s.fan])+"%";
  if(i==5)return "RUN";
  return SettingFlags[i]>=0?(s.get(Flag(SettingFlags[i]))?"ON":"OFF"):"";
}
void Oled::render(Menu& menu,const Settings& settings,const String& clock,const std::vector<String>& debug){
  if(!present)return;font(settings.font);display.clearDisplay();
  int l=menu.list(),row=0,cw=charWidth(),lh=lineHeight();std::vector<String> lines;
  auto wrap=[&](String value){do{
    int width=row?128:std::max(cw,128-int(clock.length())*cw-2);
    int chars=std::max(1,width/cw);text(value.substring(0,chars),0,row*lh,width);
    value=value.substring(std::min(int(value.length()),chars));++row;
  }while(value.length()&&row*lh<64);};
  if(l>=0){
    int cols=std::max(1,128/cw),budget=visibleRows();std::vector<String> labels;std::vector<int> rows;
    for(int i=0;i<menu.count();i++){
      String value=menu.item(i);if(l==2&&i!=17)value+=": "+settingText(i,settings);
      labels.push_back(value);rows.push_back((value.length()+2+cols-1)/cols);
    }
    int& scroll=menu.scroll[l];scroll=std::min(std::max(0,scroll),menu.count()-1);
    if(menu.selected[l]<scroll)scroll=menu.selected[l];
    while(scroll<menu.selected[l]){int used=0;for(int i=scroll;i<=menu.selected[l];i++)used+=rows[i];if(used<=budget)break;++scroll;}
    const char* title=l==0?"Main":l==1?"Emotes":"Settings";
    wrap(String(title).substring(0,std::max(1,(128-int(clock.length())*cw-2)/cw)));
    int used=0;
    for(int i=scroll;i<menu.count();i++){
      if(used&&used+rows[i]>budget)break;
      wrap((i==menu.selected[l]?String("> "):String("  "))+labels[i]);used+=rows[i];if(used>=budget)break;
    }
  }else if(menu.screen==Screen::Detail){wrap("Emote:");wrap(EmoteItems[menu.emote]);wrap("PREV/NEXT=BACK");}
  else if(menu.screen==Screen::Debug){wrap("Debug");for(auto line:debug){if(row*lh>=64)break;wrap(line);}}
  else{wrap("Main");wrap("PREV/NEXT=BACK");}
  text(clock,128-clock.length()*cw,0,clock.length()*cw);
  auto buffer=display.getBuffer();
  if(!rendered||std::memcmp(previous.data(),buffer,1024)){
    if(!ack(0x3c)){rendered=false;return;}
    display.display();if(ack(0x3c)){std::memcpy(previous.data(),buffer,1024);rendered=true;}else rendered=false;
  }
}
void Oled::snapshot(JsonDocument& doc,Menu& menu,const Settings& s,const String& clock,const std::vector<String>& debug){
  doc.clear();if(!present){doc["ok"]=false;doc["error"]="menu_snapshot_unavailable";return;}
  font(s.font);doc["ok"]=true;doc["active_screen"]=menu.screenName();
  const char* indices[]={"main_selected_index","emotes_selected_index","settings_selected_index"};
  const char* offsets[]={"main_scroll_offset","emotes_scroll_offset","settings_scroll_offset"};
  for(int i=0;i<3;i++){doc[indices[i]]=menu.selected[i];doc[offsets[i]]=menu.scroll[i];}
  if(menu.emote>=0)doc["selected_emote"]=EmoteItems[menu.emote];else doc["selected_emote"]=nullptr;
  doc["clock_text"]=clock;
  int l=menu.list(),scroll=0;JsonArray items=doc["visible_items"].to<JsonArray>();
  if(l>=0){int n=menu.count(),rows=visibleRows();scroll=std::min(menu.scroll[l],std::max(0,n-rows));
    if(menu.selected[l]<scroll)scroll=menu.selected[l];if(menu.selected[l]>=scroll+rows)scroll=menu.selected[l]-rows+1;
    doc["selected_index"]=menu.selected[l];
    for(int i=scroll;i<std::min(n,scroll+rows);i++){JsonObject e=items.add<JsonObject>();e["index"]=i;e["label"]=menu.item(i);e["selected"]=i==menu.selected[l];
      if(l==2&&i!=17){int f=SettingFlags[i];if(f>=0)e["value"]=s.get(Flag(f));
        else if(i==1)e["value"]=Brightness[s.brightness];else if(i==3)e["value"]=FanPercent[s.fan];
        else if(i==5)e["value"]=true;else e["value"]=settingText(i,s);
        e["display_value"]=settingText(i,s);}}
  }else{doc["selected_index"]=nullptr;
    if(menu.screen==Screen::Detail){auto e=items.add<JsonObject>();e["index"]=0;e["label"]=EmoteItems[menu.emote];e["selected"]=true;}
    if(menu.screen==Screen::Debug)for(int i=0;i<std::min(int(debug.size()),visibleRows());i++){
      auto e=items.add<JsonObject>();e["index"]=i;e["label"]=debug[i];e["selected"]=false;}}
  doc["scroll_offset"]=scroll;auto controls=doc["controls"].to<JsonArray>();for(auto c:{"up","ok","down","back","refresh"})controls.add(c);
}
void Perf::begin(uint32_t now){start=now;work=0;if(last){float delta=uint32_t(now-last)/1000.f;loopTotal+=delta;loopMax=std::max(loopMax,delta);++periods;}last=now;}
void Perf::beginSection(const char* name){endSection();section=name;sectionStart=micros();}
void Perf::endSection(){if(section.isEmpty())return;float elapsed=uint32_t(micros()-sectionStart)/1000.f;
  work+=elapsed;if(elapsed>sectionMax){sectionMax=elapsed;slowest=section;}section="";}
bool Perf::end(){endSection();++count;workTotal+=work;workMax=std::max(workMax,float(work));
  if(uint32_t(millis()-reportAt)<5000)return false;reportAt=millis();
  float avg=periods?loopTotal/periods:0,wavg=workTotal/count;
  snapshot["ok"]=true;snapshot["loops"]=count;snapshot["loop_avg_ms"]=avg;snapshot["loop_max_ms"]=loopMax;
  snapshot["work_avg_ms"]=wavg;snapshot["work_max_ms"]=workMax;snapshot["load_pct"]=avg?std::min(100.f,wavg*100/avg):0;
  size_t free=heap_caps_get_free_size(MALLOC_CAP_8BIT),total=heap_caps_get_total_size(MALLOC_CAP_8BIT);
  snapshot["mem_free"]=free;snapshot["mem_alloc"]=total-free;snapshot["slowest_section"]=slowest;snapshot["slowest_section_ms"]=sectionMax;
  count=periods=0;loopTotal=workTotal=0;loopMax=workMax=sectionMax=0;slowest="";return true;
}
String clockText(){time_t t=time(nullptr);tm local{};localtime_r(&t,&local);char buffer[6];std::snprintf(buffer,sizeof(buffer),"%02d:%02d",local.tm_hour,local.tm_min);return buffer;}
bool setLocalTime(int year,int month,int day,int hour,int minute,int second){
  if(year<1970||year>2099||month<1||month>12||day<1||day>31||hour<0||hour>23||minute<0||minute>59||second<0||second>59)return false;
  tm value{};value.tm_year=year-1900;value.tm_mon=month-1;value.tm_mday=day;value.tm_hour=hour;value.tm_min=minute;value.tm_sec=second;
  time_t seconds=mktime(&value);if(seconds<0||value.tm_year!=year-1900||value.tm_mon!=month-1||value.tm_mday!=day)return false;
  timeval tv{seconds,0};return settimeofday(&tv,nullptr)==0;
}
}
