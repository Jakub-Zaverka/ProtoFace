#pragma once
#include "core.h"
#include <type_traits>

namespace proto {
constexpr uint32_t RenderMs=10;
constexpr uint32_t SensorStaleMs=250;
constexpr int AnimationCore=1,LogicCore=0;
constexpr uint32_t AnimationStackBytes=12288,LogicStackBytes=16384;

// FreeRTOS copies queue items byte-for-byte. No String, vector, owning pointer,
// framebuffer, or reference may cross this boundary.
struct AnimationInput {
  Settings settings;
  Sample samples;
  uint32_t sampledAt=0;
  uint32_t displayRevision=0,transitionResetRevision=0;
  int menuEmote=-1,boopThreshold=225;
  char clock[6]={'0','0',':','0','0',0};
};
struct AnimationStatus {
  bool ready=false,boopActive=false,fullscreen=false,inputStale=true;
  int core=-1;
  uint32_t updatedAt=0,frames=0,logicalTicks=0,stackFreeBytes=0;
  float periodAvgMs=0,periodMaxMs=0,workAvgMs=0,workMaxMs=0;
  SlotSnapshot slots;
  char error[128]{};
};
static_assert(std::is_trivially_copyable<AnimationInput>::value,"Queue input must be a value snapshot");
static_assert(std::is_trivially_copyable<AnimationStatus>::value,"Queue output must be a value snapshot");

inline Sample animationSample(const AnimationInput& in,uint32_t now){
  Sample sample=in.samples;
  if(uint32_t(now-in.sampledAt)>SensorStaleMs)
    sample.micValid=sample.proxValid=sample.motionValid=false;
  return sample;
}
// No catch-up loop: an overrun advances counters once, not in a burst.
struct LogicalTick {
  uint32_t last=0;
  bool first=true;
  bool due(uint32_t now){
    if(!first&&uint32_t(now-last)<TickMs)return false;
    first=false;last=now;return true;
  }
};
}
