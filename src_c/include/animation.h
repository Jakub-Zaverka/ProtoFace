#pragma once
#include "animation_state.h"
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>

namespace proto {
class AnimationWorker {
  QueueHandle_t inputs=nullptr,outputs=nullptr;
  static void taskEntry(void*);
  void run();
 public:
  bool begin(const AnimationInput&);
  void publish(const AnimationInput& value);
  bool status(AnimationStatus& out)const;
};
}
