#pragma once
#include <array>
#include <cstdint>
#include <deque>
#include <string>
#include <vector>

namespace proto {
// Original Python loop measured about 50 ms. Use one logical tick per 50 ms
// (without catch-up bursts) for counter-based blink/boop/slots/motion.
constexpr uint32_t TickMs = 50;
constexpr uint32_t WifiAttemptMs=10000;
struct StationAttempts {
  static constexpr uint8_t Limit=2;
  uint8_t count=0;
  void reset(){count=0;}
  bool exhausted()const{return count>=Limit;}
  bool start(){if(exhausted())return false;++count;return true;}
};
inline bool before(uint32_t now, uint32_t deadline) {
  return static_cast<int32_t>(now - deadline) < 0;
}
enum Flag { Accel=0, Mic=1, Boop=2, Wifi=3, Verbose=4, Blink=5,
  Display=6, BoopRainbow=7, RainbowOverride=8, WifiConnect=9,
  WifiBroadcast=10, SmoothTransitions=11, SmoothSpeak=12, SpeakOverride=13 };
inline constexpr const char* FlagKeys[] = {"ACCELEROMETER_ON", "MIC_ON",
  "APDS_ON", "WIFI_ON", "VERBOSE", "BLINK_ON", "DISPLAY_ON",
  "BOOP_RAINBOW_ON", "RAINBOW_OVERRIDE_ON", "WIFI_CONNECT_ON",
  "WIFI_BROADCAST_ON", "SMOOTH_TRANSITIONS_ON", "SMOOTH_SPEAK_ON", "SPEAK_OVERRIDE_ON"};
struct Settings {
  uint16_t flags=(1<<Accel)|(1<<Mic)|(1<<Boop)|(1<<Blink)|(1<<Display)|
    (1<<BoopRainbow)|(1<<WifiBroadcast)|(1<<Wifi);
  uint8_t brightness=2, font=0, fan=0;
  bool oled=true;
  bool get(Flag f) const { return flags & (1<<f); }
  void set(Flag f, bool v) { flags = v ? flags|(1<<f) : flags&~(1<<f); }
  void deriveWifi() { set(Wifi,get(WifiConnect)||get(WifiBroadcast)); }
  bool import(const uint8_t* bytes, size_t size);
  std::array<uint8_t,9> encode() const;
};
inline constexpr float Brightness[] = {.3f,.4f,.5f,.7f,1.f};
inline constexpr int FanPercent[] = {0,50,100};
constexpr uint32_t FanPwmHz=25000;
constexpr uint8_t FanPwmBits=10;
constexpr uint32_t FanDutyMax=(1u<<FanPwmBits)-1;
static_assert(FanPwmHz*(1u<<FanPwmBits)<=40000000u,"PWM must fit the S3 40 MHz XTAL clock");
inline uint32_t fanDuty(int percent){
  percent=percent<0?0:percent>100?100:percent;
  return (uint32_t(percent)*FanDutyMax+50)/100;
}
struct Sample {
  bool micValid=false, proxValid=false, motionValid=false;
  float mic=0, dx=0, dy=0, dz=0;
  int proximity=0;
};
class BoopTracker {
  std::deque<std::pair<uint32_t,int>> samples;
  uint32_t frozenUntil=0;
  bool frozen=false;
 public:
  int threshold=225;
  int update(int value, bool valid, uint32_t now, bool freeze);
  void calibrate(int value, bool valid);
};
enum class Action { Up, Down, Ok, Back };
struct Input { uint32_t counter=0; bool up=false,down=false,ok=false,back=false; };
bool decode(const uint8_t* data,size_t len,Input& out);
enum class Screen { Main, MainScreen, Emotes, Detail, Settings, Debug };
inline constexpr const char* MainItems[] = {"Emotes","Settings","Debug"};
inline constexpr const char* EmoteItems[] = {"Hearth","Narrow","Sad","Question",
  "Cross","Open eye","UwU","UwU Full","OwO","Sleep","Blep","Dead",
  "Clock","Name","Slots","Back"};
inline constexpr const char* SettingItems[] = {"Display","Brightness","Font","Fan",
  "Boop","Boop Calibrate","Boop Rainbow","Rainbow Override","Mic",
  "Smooth Speak","Speak Override","Blink","Smooth Transitions","Accelerometer",
  "Wifi_Broadcast","Wifi_Connect","Verbose","Back"};
inline constexpr int SettingFlags[] = {Display,-1,-1,-1,Boop,-1,BoopRainbow,
  RainbowOverride,Mic,SmoothSpeak,SpeakOverride,Blink,SmoothTransitions,Accel,
  WifiBroadcast,WifiConnect,Verbose,-1};
struct Menu {
  Screen screen=Screen::Main;
  std::array<int,3> selected{{0,0,0}}, scroll{{0,0,0}};
  int emote=-1;
  // Returns a selected settings index, or -1.
  int action(Action a);
  int list() const;
  int count() const;
  const char* item(int i) const;
  const char* screenName() const;
  int activeEmote() const { return screen==Screen::Detail ? emote : -1; }
};
enum class Asset { None, Eye, Blink, Open, Nose, Mouth, Speak, Cross,
  Hearth, Question, Flat, SadEye, SadMouth, Blep, Sleep, U, W, UwuFull,
  Blank, Clock, Name, Slots };
const char* assetName(Asset a);
struct Request { Asset asset=Asset::None; int duration=0; bool red=false; };
using MorphProbe = bool (*)(void*,Asset,Asset,int,int);
struct Region {
  Asset idle, current=Asset::None;
  int elapsed=0,duration=0;
  bool active=false,red=false;
  bool transitioning=false,toIdle=false;
  uint32_t transitionStart=0;
  explicit Region(Asset a):idle(a){}
  bool update(Request req,uint32_t now=0,bool smooth=false,MorphProbe probe=nullptr,
              void* context=nullptr,int width=32,int height=16);
  Asset shown() const { return toIdle ? idle : active ? current : idle; }
};
struct Face {
  std::array<Region,4> regions{{Region(Asset::Eye),Region(Asset::Nose),
    Region(Asset::Mouth),Region(Asset::None)}};
  std::array<Request,4> requests;
  uint32_t speakUntil=0,lastSpeak=0;
  bool speaking=false,speakManaged=false,slotLatched=false,slotSpinning=false;
  float speakLevel=0,speakTarget=0;
  int blinkTicks=0,slotFrame=0;
  std::array<int,3> symbols{{0,1,2}};
  bool boopActive() const { return regions[0].active && regions[0].current==Asset::Open; }
  // randomWord is supplied by hardware or by deterministic host tests.
  void update(const Settings&,int menuEmote,const Sample&,int threshold,
              uint32_t now,uint32_t randomWord,MorphProbe probe=nullptr,void* context=nullptr);
  // Advance only time-based mouth animation between 50 ms logical ticks.
  // Does not advance blink/Slots/motion or retrigger microphone hold.
  void animate(const Settings&,uint32_t now);
};
uint16_t panelColor(uint8_t r,uint8_t g,uint8_t b,float brightness);
uint16_t canonicalColor(uint16_t rgb565,float brightness);
int transitionStep(uint32_t elapsed,size_t frames);
}
