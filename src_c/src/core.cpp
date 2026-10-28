#include "core.h"
#include <algorithm>
#include <cmath>
#include <cstring>
namespace proto {
bool Settings::import(const uint8_t* b,size_t n) {
  if(n<5) return false;
  size_t flagBytes=0;
  if(!std::memcmp(b,"PFS4",4)) { if(n<9)return false; flagBytes=2; }
  else if(!std::memcmp(b,"PFS3",4)) {if(n<6)return false;flagBytes=2;}
  else if(!std::memcmp(b,"PFS1",4))flagBytes=1;
  else return false;
  for(int i=0;i<14;i++) if(size_t(i/8)<flagBytes)
    set(static_cast<Flag>(i),b[4+i/8]&(1<<(i%8)));
  if(b[3]=='4') {
    brightness=b[6]<5?b[6]:2; font=b[7]<3?b[7]:0; fan=b[8]<3?b[8]:0;
  }
  deriveWifi(); return true;
}
std::array<uint8_t,9> Settings::encode() const {
  return {{'P','F','S','4',uint8_t(flags),uint8_t(flags>>8),brightness,font,fan}};
}
int BoopTracker::update(int value,bool valid,uint32_t now,bool freeze) {
  auto trim=[&] {while(!samples.empty() && uint32_t(now-samples.front().first)>1000) samples.pop_front();};
  if(!valid){trim();return threshold;}
  bool paused=freeze||(frozen&&before(now,frozenUntil));
  if(!paused)trim();
  if(!samples.empty()) { int sum=0; for(auto s:samples)sum+=s.second;
    threshold=std::min(255,sum/int(samples.size())+15); }
  if(paused)return threshold;
  frozen=false;
  if(value>threshold){frozen=true;frozenUntil=now+1000;}
  else samples.push_back({now,value});
  return threshold;
}
void BoopTracker::calibrate(int v,bool valid){samples.clear();frozen=false;threshold=valid?std::min(255,v+15):225;}
bool decode(const uint8_t* d,size_t n,Input& out) {
  if(n!=7&&n!=8)return false;
  out.counter=uint32_t(d[0])|(uint32_t(d[1])<<8)|(uint32_t(d[2])<<16)|(uint32_t(d[3])<<24);
  out.up=d[4];out.down=d[5];out.ok=d[6];out.back=n==8&&d[7];return true;
}
int Menu::list()const{return screen==Screen::Main?0:screen==Screen::Emotes?1:screen==Screen::Settings?2:-1;}
int Menu::count()const{int l=list();return l==0?3:l==1?16:l==2?SettingCount:0;}
const char* Menu::item(int i)const{int l=list();return l==0?MainItems[i]:l==1?EmoteItems[i]:SettingItems[i];}
const char* Menu::screenName()const{
  static const char* names[]={"main_menu","main_screen","emotes_menu","emote_detail","settings_menu","debug_menu"};
  return names[int(screen)];
}
int Menu::action(Action a) {
  if(a==Action::Back){screen=screen==Screen::Detail?Screen::Emotes:Screen::Main;return -1;}
  int l=list();
  if(l<0){if(screen==Screen::Debug||a!=Action::Ok)action(Action::Back);return -1;}
  int& i=selected[l];
  if(a==Action::Up)i=(i+count()-1)%count();
  if(a==Action::Down)i=(i+1)%count();
  if(a!=Action::Ok)return -1;
  if(l==0){screen=i==0?Screen::Emotes:i==1?Screen::Settings:Screen::Debug;}
  else if(l==1){if(i==15)screen=Screen::Main;else{emote=i;screen=Screen::Detail;}}
  else if(i==BackSetting)screen=Screen::Main;
  else return i;
  return -1;
}
const char* assetName(Asset a){
  static const char* names[]={"","eye","eye_blink","eye_open","nose","mouth",
    "mouth_speak","cross","hearth","question","flat_mouth","sad_eye",
    "sad_mouth","blep","sleep","u","wwww","uwu_text","","","",""};
  return names[int(a)];
}
bool Region::update(Request r,uint32_t now,bool smooth,MorphProbe probe,void* context,int width,int height) {
  bool started=false;
  if(r.asset!=Asset::None){
    started=!active||current!=r.asset||red!=r.red;
    if(started){
      transitioning=smooth&&probe&&probe(context,current!=Asset::None?current:idle,r.asset,width,height);
      transitionStart=now;toIdle=false;
    }else if(transitioning&&uint32_t(now-transitionStart)>=200)transitioning=false;
    active=true;current=r.asset;red=r.red;elapsed=0;duration=r.duration;
  }else if(active){
    if(transitioning){
      if(uint32_t(now-transitionStart)>=200){transitioning=false;
        if(toIdle){active=false;current=Asset::None;red=false;toIdle=false;}}
      return false;
    }
    if(++elapsed>=duration){
      if(smooth&&probe&&idle!=Asset::None&&probe(context,current,idle,width,height)){
        transitioning=toIdle=true;transitionStart=now;elapsed=0;
      }else{active=false;current=Asset::None;red=false;toIdle=false;}
    }
  }
  return started;
}
void Face::update(const Settings& s,int menu,const Sample& v,int threshold,uint32_t now,uint32_t rnd,MorphProbe probe,void* context){
  requests={};
  auto req=[&](int region,Asset a,int duration=1,bool red=false){requests[region]={a,duration,red};};
  bool slotBoop=v.proxValid&&v.proximity>threshold;
  if(menu==14){
    if(slotBoop&&!slotLatched&&!slotSpinning){slotSpinning=true;slotFrame=0;}
    slotLatched=slotBoop;
    if(slotSpinning){++slotFrame;int cadence=slotFrame<12?1:2;
      if(slotFrame%cadence==0)for(int i=0;i<3;i++)if(slotFrame<=(16+i*6)) {
        rnd=rnd*1664525u+1013904223u;symbols[i]=(rnd>>16)%6; }
      if(slotFrame>=28)slotSpinning=false;
    }
  }else{slotLatched=false;slotSpinning=false;}
  switch(menu){
    case 0:req(0,Asset::Hearth);break;
    case 1:req(0,Asset::Blink);req(2,Asset::Flat);break;
    case 2:req(0,Asset::SadEye);req(2,Asset::SadMouth);break;
    case 3:req(0,Asset::Question);break;
    case 4:req(0,Asset::Cross);break;
    case 5:req(0,Asset::Open);req(2,Asset::Speak);break;
    case 6:req(0,Asset::U);req(1,Asset::Blank);req(2,Asset::W);break;
    case 7:req(3,Asset::UwuFull);break;
    case 8:req(0,Asset::Open);req(1,Asset::Blank);req(2,Asset::W);break;
    case 9:req(0,Asset::Sleep);req(2,Asset::Flat);break;
    case 10:req(2,Asset::Blep);break;
    case 11:req(0,Asset::Cross,1,true);req(1,Asset::Nose,1,true);req(2,Asset::SadMouth,1,true);break;
    case 12:req(3,Asset::Clock);break;
    case 13:req(3,Asset::Name);break;
    case 14:req(3,Asset::Slots);break;
  }
  bool whole=regions[3].active||requests[3].asset!=Asset::None;
  if((menu<0||s.get(SpeakOverride))&&v.micValid&&!whole){
    if(v.mic>=5||(v.mic>3&&speaking&&before(now,speakUntil))){speakUntil=now+200;speaking=true;}
    if(speaking&&before(now,speakUntil))req(2,Asset::Speak,6);
  }
  if(speaking&&!before(now,speakUntil))speaking=false;
  if(menu<0&&v.proxValid&&!whole&&v.proximity>threshold)req(0,Asset::Open,5);
  if(s.get(Blink)&&menu<0&&!whole&&requests[0].asset==Asset::None){
    if(!regions[0].active){if(++blinkTicks>=125){req(0,Asset::Blink,16);blinkTicks=0;}}
    else if(regions[0].current!=Asset::Blink)blinkTicks=0;
  }
  bool started=false;
  for(int i=0;i<4;i++){
    // Dedicated speak controller bypasses frame-count region duration.
    if(i==2&&(requests[i].asset==Asset::None||requests[i].asset==Asset::Speak)&&
       (speakManaged||regions[i].current==Asset::None||regions[i].current==Asset::Speak)&&!regions[i].transitioning){
      if(!speakManaged){speakLevel=regions[i].active?1:0;lastSpeak=now;speakManaged=true;}
      float target=requests[i].asset==Asset::Speak?1.f:0.f;
      bool start=target&&regions[i].current!=Asset::Speak;
      speakTarget=target;
      animate(s,now);
      regions[i].active=target||speakLevel>0;regions[i].current=regions[i].active?Asset::Speak:Asset::None;
      regions[i].red=false;regions[i].elapsed=0;regions[i].duration=requests[i].duration;
      started|=start;
    }else{
      if(i==2)speakManaged=false;
      bool smooth=s.get(SmoothTransitions)||(i==2&&s.get(SmoothSpeak)&&
        (requests[i].asset==Asset::Speak||regions[i].current==Asset::Speak));
      started|=regions[i].update(requests[i],now,smooth,probe,context,i<2?32:64,i==3?32:16);
    }
  }
  if((started&&regions[0].current!=Asset::Blink)||menu>=0)blinkTicks=0;
}
void Face::animate(const Settings& s,uint32_t now){
  if(!speakManaged)return;
  float delta=uint32_t(now-lastSpeak)/200.f;lastSpeak=now;
  if(s.get(SmoothSpeak)||s.get(SmoothTransitions))
    speakLevel=speakTarget>speakLevel?std::min(speakTarget,speakLevel+delta):std::max(speakTarget,speakLevel-delta);
  else speakLevel=speakTarget;
  regions[2].active=speakTarget||speakLevel>0;
  regions[2].current=regions[2].active?Asset::Speak:Asset::None;
}
uint16_t panelColor(uint8_t r,uint8_t g,uint8_t b,float scale){
  std::swap(g,b);int rr=int((r>>3)*scale),gg=int((g>>2)*scale),bb=int((b>>3)*scale);
  return uint16_t((rr<<11)|(gg<<5)|bb);
}
uint16_t canonicalColor(uint16_t c,float scale){return panelColor(((c>>11)&31)*255/31,((c>>5)&63)*255/63,(c&31)*255/31,scale);}
int transitionStep(uint32_t elapsed,size_t frames){return frames?int(std::min<uint32_t>(elapsed,200)*(frames-1)/200):0;}
}
