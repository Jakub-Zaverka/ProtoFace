#pragma once
#include "core.h"
#include <Adafruit_Protomatter.h>
#include <FS.h>
#include <map>
#include <memory>

namespace proto {
struct Image { int width=0,height=0; std::vector<uint16_t> pixels; };
struct SparsePixel { uint8_t x,y; uint16_t color; };
struct Morph { int width=0,height=0; std::vector<std::vector<SparsePixel>> frames; };
struct MorphRef { std::shared_ptr<Morph> morph; bool reverse=false; };
class AssetStore {
  fs::FS& fs;
  std::map<int,std::shared_ptr<Image>> images;
  std::map<std::string,std::shared_ptr<Morph>> morphs;
 public:
  float brightness=.5;
  String error;
  explicit AssetStore(fs::FS& filesystem):fs(filesystem){}
  std::shared_ptr<Image> image(Asset);
  MorphRef morph(Asset a,Asset b,int width,int height);
  void clear(){images.clear();morphs.clear();error="";}
};
class Graphics {
  AssetStore assets;
  std::unique_ptr<Adafruit_Protomatter> matrix;
  struct Layer {
    Asset shown=Asset::None;
    Image bitmap;
    MorphRef morph;
    uint32_t start=0;
    int lastFrame=-1;
    bool red=false;
  };
  std::array<Layer,4> layers;
  MorphRef speak;
  uint16_t wheel[256]{};
  std::array<int,4> x{{1,32,0,0}},y{{0,0,16,0}};
  std::array<uint16_t,4096> previous{};
  std::array<uint16_t,4096> frame{}; // Not on Arduino loop task's 8 KiB stack.
  uint8_t phase=0,cadence=0;
  bool lastRainbow=false,force=true;
  std::string lastClock;
  std::array<int,3> lastSymbols{{-1,-1,-1}};
  bool lastSpinning=false;
  bool updateLayer(int,Asset,bool,bool,uint32_t);
  void sparse(Layer&,const MorphRef&,int);
  void dynamic(Layer&,Asset,const Face&,const String&);
 public:
  explicit Graphics(fs::FS& filesystem):assets(filesystem){}
  bool begin(const Settings&);
  void end();
  void motion(const Sample&,bool enabled,bool fullscreen);
  void render(const Face&,const Settings&,uint32_t now,const String& clock,bool logicalTick=true);
  bool ready()const{return bool(matrix);}
  void finishTransitions(){for(auto& layer:layers){layer.morph={};layer.shown=Asset::None;layer.lastFrame=-1;}}
  bool hasMorph(Asset a,Asset b,int width,int height){return bool(assets.morph(a,b,width,height).morph);}
  const String& error()const{return assets.error;}
};
}
