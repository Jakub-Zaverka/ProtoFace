#include "animation.h"
#include "graphics.h"
#include <LittleFS.h>
#include <freertos/task.h>
#include <algorithm>
#include <cstdio>

#if defined(CONFIG_FREERTOS_UNICORE) && CONFIG_FREERTOS_UNICORE
#error "ProtoFace requires both ESP32-S3 cores; disable CONFIG_FREERTOS_UNICORE"
#endif

namespace proto {
namespace {
// These objects have exactly one owner: the animation task, including begin/end
// and Protomatter's timer/interrupt allocation on core 1. Never touch from logic.
Graphics graphics(LittleFS);
Face face;
}
bool AnimationWorker::begin(const AnimationInput& initial){
  if(inputs||outputs)return false;
  inputs=xQueueCreate(1,sizeof(AnimationInput));
  outputs=xQueueCreate(1,sizeof(AnimationStatus));
  if(inputs&&outputs){
    xQueueOverwrite(inputs,&initial);
    if(xTaskCreatePinnedToCore(taskEntry,"proto_animation",AnimationStackBytes,
                              this,2,nullptr,AnimationCore)==pdPASS)return true;
  }
  if(inputs)vQueueDelete(inputs);
  if(outputs)vQueueDelete(outputs);
  inputs=outputs=nullptr;return false;
}
void AnimationWorker::publish(const AnimationInput& value){if(inputs)xQueueOverwrite(inputs,&value);}
bool AnimationWorker::status(AnimationStatus& out)const{return outputs&&xQueuePeek(outputs,&out,0)==pdTRUE;}
void AnimationWorker::taskEntry(void* context){static_cast<AnimationWorker*>(context)->run();}
void AnimationWorker::run(){
  AnimationInput input;
  xQueueReceive(inputs,&input,portMAX_DELAY);
  bool first=true;
  uint32_t displayRevision=input.displayRevision,resetRevision=input.transitionResetRevision;
  Settings applied=input.settings;
  AnimationStatus state;
  LogicalTick ticks;
  uint32_t windowStart=millis(),lastStart=0,windowFrames=0,windowPeriods=0;
  double periodTotal=0,workTotal=0;
  float periodMax=0,workMax=0;
  for(;;){
    TickType_t wake=xTaskGetTickCount();
    uint32_t started=micros();
    if(lastStart){float ms=uint32_t(started-lastStart)/1000.f;
      periodTotal+=ms;periodMax=std::max(periodMax,ms);++windowPeriods;}
    lastStart=started;
    AnimationInput latest;
    if(xQueueReceive(inputs,&latest,0)==pdTRUE)input=latest;
    if(first||displayRevision!=input.displayRevision||
       applied.get(Display)!=input.settings.get(Display)||applied.brightness!=input.settings.brightness){
      if(input.settings.get(Display))graphics.begin(input.settings);
      else graphics.end();
      face=Face{};ticks.first=true;
      displayRevision=input.displayRevision;
    }
    if(resetRevision!=input.transitionResetRevision||
       (applied.get(SmoothTransitions)&&!input.settings.get(SmoothTransitions))){
      for(auto& region:face.regions)if(region.transitioning){
        if(region.toIdle){region.active=false;region.current=Asset::None;region.red=false;}
        region.transitioning=region.toIdle=false;
      }
      graphics.finishTransitions();resetRevision=input.transitionResetRevision;
    }
    first=false;applied=input.settings;
    uint32_t now=millis();
    bool logicalTick=ticks.due(now);
    Sample sample=animationSample(input,now);
    if(graphics.ready()){
      if(logicalTick){
        graphics.motion(sample,input.settings.get(Accel),face.regions[3].active);
        face.update(input.settings,input.menuEmote,sample,input.boopThreshold,now,esp_random(),
          [](void* g,Asset a,Asset b,int w,int h){return static_cast<Graphics*>(g)->hasMorph(a,b,w,h);},&graphics);
        ++state.logicalTicks;
      }else face.animate(input.settings,now);
      graphics.render(face,input.settings,now,String(input.clock),logicalTick);
    }
    float work=uint32_t(micros()-started)/1000.f;
    ++windowFrames;++state.frames;workTotal+=work;workMax=std::max(workMax,work);
    if(uint32_t(now-windowStart)>=5000){
      state.periodAvgMs=windowPeriods?periodTotal/windowPeriods:0;
      state.periodMaxMs=periodMax;state.workAvgMs=workTotal/windowFrames;state.workMaxMs=workMax;
      windowFrames=windowPeriods=0;periodTotal=workTotal=0;periodMax=workMax=0;windowStart=now;
    }
    state.ready=graphics.ready();state.boopActive=state.ready&&face.boopActive();
    state.fullscreen=state.ready&&face.regions[3].active;
    state.slots=face.slots.status;
    state.inputStale=uint32_t(now-input.sampledAt)>SensorStaleMs;
    state.core=xPortGetCoreID();state.updatedAt=millis();
    state.stackFreeBytes=uxTaskGetStackHighWaterMark(nullptr);
    std::snprintf(state.error,sizeof(state.error),"%s",graphics.error().c_str());
    xQueueOverwrite(outputs,&state);
    // Always yield, including after an overrun, so the idle task/watchdog runs.
    TickType_t period=std::max<TickType_t>(1,pdMS_TO_TICKS(RenderMs));
    TickType_t elapsed=xTaskGetTickCount()-wake;
    vTaskDelay(elapsed<period?period-elapsed:1);
  }
}
}
