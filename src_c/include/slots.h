#pragma once
#include <array>
#include <cstdint>

namespace proto {
enum class SlotOutcome : uint8_t { Waiting,Spinning,Miss,Pair,Triple,Jackpot };
struct SlotSnapshot {
  bool spinning=false,hasResult=false;
  uint8_t stoppedMask=7;
  uint32_t spinId=0;
  std::array<uint8_t,3> symbols{{0,1,2}};
  SlotOutcome outcome=SlotOutcome::Waiting;
};
inline const char* slotSymbolName(int s){
  constexpr const char* names[]={"7","BAR","CHERRY","BELL","GEM","STAR"};
  return s>=0&&s<6?names[s]:"?";
}
inline const char* slotOutcomeName(SlotOutcome result){
  switch(result){
    case SlotOutcome::Spinning:return "TOCENI";
    case SlotOutcome::Miss:return "BEZ VYHRY";
    case SlotOutcome::Pair:return "DVOJICE";
    case SlotOutcome::Triple:return "TROJICE";
    case SlotOutcome::Jackpot:return "JACKPOT";
    default:return "BOOP = START";
  }
}
struct SlotMachine {
  static constexpr uint32_t Duration[3]={1700,2200,2700};
  SlotSnapshot status;
  bool boopLatched=false;
  uint32_t startedAt=0,finishedAt=0;
  std::array<float,3> position{{0,1,2}};
  std::array<int,3> start{},goal{};
  static SlotOutcome evaluate(const std::array<uint8_t,3>& s){
    if(s[0]==s[1]&&s[1]==s[2])return s[0]==0?SlotOutcome::Jackpot:SlotOutcome::Triple;
    if(s[0]==s[1]||s[0]==s[2]||s[1]==s[2])return SlotOutcome::Pair;
    return SlotOutcome::Miss;
  }
  void update(bool boop,uint32_t now,uint32_t randomWord){
    if(boop&&!boopLatched&&!status.spinning){
      ++status.spinId;status.spinning=true;status.hasResult=false;
      status.outcome=SlotOutcome::Spinning;status.stoppedMask=0;startedAt=now;
      for(int i=0;i<3;i++){
        randomWord=randomWord*1664525u+1013904223u;
        int target=(randomWord>>16)%6;start[i]=status.symbols[i];
        goal[i]=start[i]+18+i*6+(target-start[i]+6)%6;
        position[i]=start[i];
      }
    }
    boopLatched=boop;advance(now);
  }
  void advance(uint32_t now){
    if(!status.spinning)return;
    uint32_t elapsed=now-startedAt;
    for(int i=0;i<3;i++){
      if(elapsed>=Duration[i]){
        position[i]=goal[i];status.symbols[i]=goal[i]%6;status.stoppedMask|=1<<i;
      }else{
        float t=float(elapsed)/Duration[i],remaining=1-t;
        position[i]=start[i]+(goal[i]-start[i])*(1-remaining*remaining*remaining);
      }
    }
    if(status.stoppedMask==7){
      status.spinning=false;status.hasResult=true;status.outcome=evaluate(status.symbols);
      finishedAt=startedAt+Duration[2];
    }
  }
  bool celebrating(uint32_t now)const{
    return status.hasResult&&status.outcome>=SlotOutcome::Pair&&uint32_t(now-finishedAt)<1600;
  }
  void leave(){
    boopLatched=false;
    if(status.spinning){status.spinning=false;status.hasResult=false;status.outcome=SlotOutcome::Waiting;}
    status.stoppedMask=7;
    for(int i=0;i<3;i++)position[i]=status.symbols[i];
  }
};
}
