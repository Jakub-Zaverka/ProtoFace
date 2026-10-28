#include "core.h"
#include "animation_state.h"
#include "panels.h"
#include <cassert>
#include <cmath>
#include <iostream>
using namespace proto;

void settingsTests(){
  Settings s;s.brightness=4;s.fan=2;s.font=1;s.set(SmoothSpeak,true);
  auto bytes=s.encode();Settings restored;
  assert(restored.import(bytes.data(),bytes.size()));assert(restored.encode()==bytes);
  bytes[6]=255;bytes[7]=255;bytes[8]=255;
  assert(restored.import(bytes.data(),9));assert(restored.brightness==2&&restored.font==0&&restored.fan==0);
  uint8_t old[]={'P','F','S','1',0};Settings legacy;
  assert(legacy.import(old,5));assert(!legacy.get(Mic));assert(legacy.get(WifiBroadcast));
  assert(legacy.get(Wifi));assert(!legacy.import(old,4));old[3]='2';assert(!legacy.import(old,5));
  uint8_t v3[]={'P','F','S','3',0xff,0};assert(legacy.import(v3,6));
  assert(legacy.get(Mic)&&!legacy.get(WifiConnect)&&!legacy.get(WifiBroadcast)&&!legacy.get(Wifi));
}
void inputTests(){
  uint8_t packet[]={0x78,0x56,0x34,0x12,1,0,1,1};Input i;
  assert(decode(packet,8,i)&&i.counter==0x12345678&&i.up&&!i.down&&i.ok&&i.back);
  assert(decode(packet,7,i)&&!i.back);assert(!decode(packet,6,i));assert(!decode(packet,9,i));
  Menu m;assert(m.screen==Screen::Main);m.action(Action::Up);assert(m.selected[0]==2);
  m.action(Action::Down);assert(m.selected[0]==0);m.action(Action::Ok);assert(m.screen==Screen::Emotes);
  m.action(Action::Ok);assert(m.activeEmote()==0);m.action(Action::Ok);assert(m.activeEmote()==0);
  m.action(Action::Down);assert(m.screen==Screen::Emotes&&m.activeEmote()==-1);
  m.action(Action::Back);m.action(Action::Down);m.action(Action::Ok);
  assert(m.screen==Screen::Settings);assert(m.action(Action::Ok)==0);
}
void boopTests(){
  BoopTracker t;assert(t.update(100,true,0,false)==225);
  assert(t.update(100,true,50,false)==115);
  assert(t.update(116,true,100,false)==115); // spike is not learned
  assert(t.update(200,true,500,false)==115);
  assert(t.update(0,false,700,false)==115);
  assert(t.update(100,true,1101,false)==115);
  assert(t.update(100,true,1151,false)==115);
  t.calibrate(250,true);assert(t.threshold==255);t.calibrate(0,false);assert(t.threshold==225);
  assert(t.update(225,true,0xfffffff0u,false)==225);
  assert(t.update(240,true,20,false)==240); // equality is not a spike
}
void faceTests(){
  Settings s;s.set(Blink,false);Face f;Sample v;
  v.micValid=true;v.mic=5;f.update(s,-1,v,225,0,1);
  assert(f.regions[2].shown()==Asset::Speak&&f.speakLevel==1);
  v.mic=3;f.update(s,-1,v,225,199,1);assert(f.regions[2].active);
  f.update(s,-1,v,225,200,1);assert(!f.regions[2].active);
  v.mic=5;f.update(s,-1,v,225,250,1);v.mic=4;f.update(s,-1,v,225,400,1);
  assert(f.speakUntil==600);v.mic=3;f.update(s,-1,v,225,600,1);assert(!f.regions[2].active);
  // Menu priority and optional mouth override.
  v.mic=5;f.update(s,2,v,225,650,1);assert(f.regions[2].shown()==Asset::SadMouth);
  s.set(SpeakOverride,true);f.update(s,2,v,225,700,1);assert(f.regions[2].shown()==Asset::Speak);
  f.update(s,12,v,225,750,1);assert(f.regions[3].shown()==Asset::Clock);
  assert(f.requests[2].asset==Asset::None);
  // Blink only counts eligible ticks, and boop prevents blink.
  f=Face{};v={};s.set(Blink,true);
  for(int tick=0;tick<124;tick++)f.update(s,-1,v,225,tick*50,1);
  assert(!f.regions[0].active);f.update(s,-1,v,225,6200,1);assert(f.regions[0].current==Asset::Blink);
  for(int tick=0;tick<16;tick++)f.update(s,-1,v,225,6250+tick*50,1);
  assert(!f.regions[0].active);
  v.proxValid=true;v.proximity=225;f.update(s,-1,v,225,7100,1);assert(!f.boopActive());
  v.proximity=226;f.update(s,-1,v,225,7150,1);assert(f.boopActive());
  // Slots: one rising edge, no automatic restart with held proximity.
  f=Face{};for(int tick=0;tick<40;tick++)f.update(s,14,v,225,tick*50,123);
  assert(!f.slotSpinning&&f.slotFrame==28);auto symbols=f.symbols;
  f.update(s,14,v,225,2050,123);assert(f.symbols==symbols);
  v.proximity=0;f.update(s,14,v,225,2100,123);v.proximity=226;f.update(s,14,v,225,2150,123);assert(f.slotSpinning&&f.slotFrame==1);
  f.update(s,-1,v,225,2200,123);assert(!f.slotSpinning&&!f.slotLatched);
  // Smooth Speak turns around from the current level, not from an endpoint.
  f=Face{};s.set(SmoothSpeak,true);v={};v.micValid=true;v.mic=5;
  f.update(s,-1,v,225,0,1);assert(f.speakLevel==0);
  f.update(s,-1,v,225,100,1);assert(std::abs(f.speakLevel-.5f)<1e-6);
  v.mic=0;f.update(s,-1,v,225,300,1);assert(f.speakLevel==0);
  v.mic=5;f.update(s,-1,v,225,350,1);assert(std::abs(f.speakLevel-.25f)<1e-6);
  // Monotonic wrap-around must not terminate a new microphone hold.
  f=Face{};s.set(SmoothSpeak,false);f.update(s,-1,v,225,0xfffffff0u,1);
  v.mic=0;f.update(s,-1,v,225,30,1);assert(f.regions[2].active);
}
void graphicsMathTests(){
  assert(fanDuty(0)==0&&fanDuty(50)==512&&fanDuty(100)==1023);
  assert(fanDuty(-1)==0&&fanDuty(101)==1023);
  assert(panelColor(255,0,0,1)==0xf800);
  assert(panelColor(0,255,0,1)==0x001f); // physical G/B swap
  assert(panelColor(0,0,255,1)==0x07e0);
  assert(canonicalColor(0xf800,1)==0xf800);
  assert(transitionStep(0,7)==0&&transitionStep(100,7)==3&&transitionStep(200,7)==6&&transitionStep(999,7)==6);
  assert(panelColor(255,255,255,.5f)==((15<<11)|(31<<5)|15));
}
void regionTransitionTests(){
  auto probe=[](void*,Asset a,Asset b,int,int){return a!=b&&a!=Asset::None&&b!=Asset::None;};
  Region eye(Asset::Eye);
  eye.update({Asset::Blink,2,false},0,true,probe);
  assert(eye.active&&eye.transitioning&&eye.shown()==Asset::Blink);
  eye.update({},100,true,probe);assert(eye.transitioning&&eye.elapsed==0);
  eye.update({},200,true,probe);assert(!eye.transitioning&&eye.active);
  eye.update({},250,true,probe);assert(eye.elapsed==1);
  eye.update({},300,true,probe);assert(eye.transitioning&&eye.toIdle&&eye.active&&eye.shown()==Asset::Eye);
  eye.update({},499,true,probe);assert(eye.active);
  eye.update({},500,true,probe);assert(!eye.active&&!eye.transitioning&&!eye.toIdle);
  // Starting another expression cancels a return-to-idle animation.
  eye.update({Asset::Blink,1,false},600,true,probe);
  eye.update({},800,true,probe);eye.update({},850,true,probe);assert(eye.toIdle);
  eye.update({Asset::Cross,1,false},900,true,probe);assert(!eye.toIdle&&eye.current==Asset::Cross);
}
void snapshotTests(){
  AnimationInput input;input.samples.micValid=input.samples.proxValid=input.samples.motionValid=true;
  input.samples.mic=5;input.samples.proximity=230;input.sampledAt=100;
  AnimationInput copied=input;
  input.settings.brightness=4;input.samples.mic=0;input.clock[0]='2';
  assert(copied.settings.brightness==2&&copied.samples.mic==5&&copied.clock[0]=='0');
  assert(animationSample(copied,350).micValid);
  Sample stale=animationSample(copied,351);
  assert(!stale.micValid&&!stale.proxValid&&!stale.motionValid);
  copied.sampledAt=0xfffffff0u;
  assert(animationSample(copied,30).micValid);
  assert(!animationSample(copied,300).micValid);
  LogicalTick timer;assert(timer.due(0));assert(!timer.due(49));assert(timer.due(50));
  assert(timer.due(1000));assert(!timer.due(1001));assert(timer.due(1050));
  timer.last=0xfffffff0u;timer.first=false;
  assert(!timer.due(20));assert(timer.due(40));
}
void independentAnimationTests(){
  Face f;Settings s;s.set(SmoothSpeak,true);Sample sample;sample.micValid=true;sample.mic=5;
  f.update(s,-1,sample,225,0,1);
  int blink=f.blinkTicks;uint32_t hold=f.speakUntil;
  for(uint32_t now=10;now<=100;now+=10)f.animate(s,now);
  assert(std::abs(f.speakLevel-.5f)<1e-5);
  assert(f.blinkTicks==blink&&f.slotFrame==0&&f.speakUntil==hold);
  f.animate(s,200);assert(std::abs(f.speakLevel-1)<1e-5);
  // With stalled logic, fresh animation ticks do not extend the mic deadline.
  AnimationInput input;input.settings=s;input.samples=sample;input.sampledAt=0;
  f.update(s,-1,animationSample(input,300),225,300,1);
  float level=f.speakLevel;
  f.animate(s,350);assert(f.speakLevel<level);
  f.animate(s,550);assert(f.speakLevel==0&&!f.regions[2].active);
  // Rendering must not advance the slot-machine's logical counter.
  f=Face{};sample={};sample.proxValid=true;sample.proximity=230;
  f.update(s,14,sample,225,0,1);int slot=f.slotFrame;
  for(uint32_t now=10;now<50;now+=10)f.animate(s,now);
  assert(f.slotFrame==slot&&f.slotSpinning);
}
void stationAttemptsTests(){
  StationAttempts attempts;
  assert(attempts.count==0&&!attempts.exhausted());
  assert(attempts.start()&&attempts.count==1&&!attempts.exhausted());
  assert(attempts.start()&&attempts.count==2&&attempts.exhausted());
  assert(!attempts.start()&&attempts.count==2);
  attempts.reset();assert(attempts.start()&&attempts.count==1);
}
void restartTests(){
  Menu menu;menu.screen=Screen::Settings;menu.selected[2]=HwResetSetting;
  assert(menu.action(Action::Ok)==HwResetSetting&&menu.screen==Screen::Settings);
  menu.selected[2]=BackSetting;assert(menu.action(Action::Ok)==-1&&menu.screen==Screen::Main);
  RestartRequest restart;assert(!restart.due(1000));
  restart.request(100);assert(!restart.due(399)&&restart.due(400));
  restart.request(390);assert(restart.due(400)); // repeated click doesn't postpone
  restart=RestartRequest{};restart.request(0xfffffff0u);
  assert(!restart.due(20)&&restart.due(284));
}
void panelTests(){
  // Face mapping stays symmetric; text reads forward in both logical halves.
  for(int width:{32,64})for(int x=0;x<width;x++){
    assert(Panels[0].pixelX(x,width,false)==width-1-x);
    assert(Panels[0].pixelX(x,width,true)==x);
    assert(Panels[1].pixelX(x,width,false)==x);
    assert(Panels[1].pixelX(x,width,true)==x);
  }
  // An asymmetric row must retain its source order in BOTH fullscreen halves.
  const int row[]={1,0,0,1,1,0,0,0};int left[8]{},rightFace[8]{},rightText[8]{};
  for(int x=0;x<8;x++){
    left[Panels[0].pixelX(x,8,true)]=row[x];
    rightFace[Panels[1].pixelX(x,8,false)]=row[x];
    rightText[Panels[1].pixelX(x,8,true)]=row[x];
  }
  for(int x=0;x<8;x++){assert(left[x]==row[x]);assert(rightFace[x]==row[x]);assert(rightText[x]==row[x]);}
  assert(Panels[0].contains(0,0)&&Panels[0].contains(63,31));
  assert(!Panels[0].contains(64,0)&&!Panels[0].contains(-1,0));
  assert(Panels[1].contains(64,0)&&Panels[1].contains(127,31));
  assert(!Panels[1].contains(63,0)&&!Panels[1].contains(128,0));
  assert(!Panels[0].contains(0,32)&&!Panels[1].contains(64,-1));
}
int main(){settingsTests();inputTests();boopTests();faceTests();graphicsMathTests();regionTransitionTests();snapshotTests();independentAnimationTests();stationAttemptsTests();restartTests();panelTests();std::cout<<"11 C++ test groups passed\n";}
