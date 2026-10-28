#include "graphics.h"
#include "fonts.h"
#include <algorithm>
#include <cstring>
#include <cmath>
namespace proto {
namespace {
bool readExact(File& f,void* out,size_t n){return f.read(static_cast<uint8_t*>(out),n)==n;}
uint16_t u16(const uint8_t* p){return p[0]|(uint16_t(p[1])<<8);}
uint32_t u32(const uint8_t* p){return u16(p)|(uint32_t(u16(p+2))<<16);}
void glyph(GFXcanvas16& c,uint8_t ch,int x,int y,int scale,uint16_t color){
  auto rows=faceGlyph(ch);for(int yy=0;yy<7;yy++)for(int xx=0;xx<5;xx++)
    if(rows[yy]&(1<<(4-xx)))c.fillRect(x+xx*scale,y+yy*scale,scale,scale,color);
}
void symbol(GFXcanvas16& c,int s,int x,int y,uint16_t col){
  auto line=[&](int a,int b,int d,int e){c.drawLine(x+a,y+b,x+d,y+e,col);};
  switch(s){
    case 0:line(-4,-5,4,-5);line(4,-5,-1,5);break;
    case 1:line(-4,-4,4,-4);line(4,-4,4,4);line(4,4,-4,4);line(-4,4,-4,-4);break;
    case 2:{static const int8_t points[][2]={{-2,-5},{-1,-5},{0,-5},{1,-5},{2,-5},
      {-4,-3},{4,-3},{-5,-2},{5,-2},{-5,-1},{5,-1},{-5,0},{5,0},{-5,1},{5,1},
      {-5,2},{5,2},{-4,3},{4,3},{-2,5},{-1,5},{0,5},{1,5},{2,5}};
      for(auto& p:points)c.drawPixel(x+p[0],y+p[1],col);break;}
    case 3:line(0,-5,-5,5);line(-5,5,5,5);line(5,5,0,-5);break;
    case 4:line(0,-6,-5,0);line(-5,0,0,6);line(0,6,5,0);line(5,0,0,-6);break;
    default:line(0,-5,0,5);line(-5,0,5,0);break;
  }
}
}
std::shared_ptr<Image> AssetStore::image(Asset a){
  auto it=images.find(int(a));if(it!=images.end())return it->second;
  const char* name=assetName(a);if(!*name)return {};
  String path=String("/faces/")+name+".bmp";
  File f=fs.open(path,"r");uint8_t h[54];
  if(!f||!readExact(f,h,54)||h[0]!='B'||h[1]!='M'){error="Invalid/missing BMP: "+path;return {};}
  int32_t w=int32_t(u32(h+18)),height=int32_t(u32(h+22));
  uint16_t depth=u16(h+28);uint32_t compression=u32(h+30),offset=u32(h+10),dib=u32(h+14);
  if(w<=0||w>128||height==0||std::abs(height)>64||compression||
     (depth!=24&&depth!=32&&depth!=8&&depth!=4&&depth!=1)){
    error="Unsupported BMP: "+path;return {};
  }
  std::vector<uint16_t> palette;
  if(depth<=8){size_t count=u32(h+46);if(!count)count=1u<<depth;
    if(count>256||!f.seek(14+dib)){error="Bad BMP palette";return {};}
    palette.resize(count);for(auto& color:palette){uint8_t b[4];if(!readExact(f,b,4)){error="Truncated BMP palette";return {};}
      color=panelColor(b[2],b[1],b[0],brightness);}
  }
  auto img=std::make_shared<Image>();img->width=w;img->height=std::abs(height);
  img->pixels.resize(w*img->height);
  size_t stride=((w*depth+31)/32)*4;std::vector<uint8_t> row(stride);
  if(!f.seek(offset)){error="Bad BMP offset";return {};}
  for(int fileY=0;fileY<img->height;fileY++){
    if(!readExact(f,row.data(),stride)){error="Truncated BMP pixels";return {};}
    int y=height>0?img->height-1-fileY:fileY;
    for(int x=0;x<w;x++){
      uint16_t color=0;
      if(depth>=24){auto p=&row[x*(depth/8)];color=panelColor(p[2],p[1],p[0],brightness);}
      else {int idx=depth==8?row[x]:depth==4?(row[x/2]>>((1-x%2)*4))&15:(row[x/8]>>(7-x%8))&1;
        if(size_t(idx)>=palette.size()){error="Bad BMP index";return {};}
        color=palette[idx];}
      img->pixels[y*w+x]=color;
    }
  }
  images[int(a)]=img;return img;
}
MorphRef AssetStore::morph(Asset a,Asset b,int width,int height){
  std::string first=assetName(a),second=assetName(b);if(first.empty()||second.empty()||first==second)return {};
  bool rev=first>second;if(rev)std::swap(first,second);
  std::string key=first+"--"+second+":"+std::to_string(width)+":"+std::to_string(height);
  auto hit=morphs.find(key);if(hit!=morphs.end())return {hit->second,rev};
  File f=fs.open(("/transitions/"+first+"--"+second+".mph").c_str(),"r");if(!f)return {};
  uint8_t h[7];if(!readExact(f,h,7)||std::memcmp(h,"MPH1",4)||h[4]!=width||h[5]!=height||h[6]<2){error="Invalid morph header";return {};}
  auto result=std::make_shared<Morph>();result->width=width;result->height=height;
  for(int i=0;i<h[6];i++){
    uint8_t count[2];if(!readExact(f,count,2)){error="Truncated morph count";return {};}
    std::vector<SparsePixel> frame;frame.reserve(u16(count));
    for(int j=0;j<u16(count);j++){
      uint8_t p[4];if(!readExact(f,p,4)||p[0]>=width||p[1]>=height){error="Invalid morph frame";return {};}
      frame.push_back({p[0],p[1],canonicalColor(u16(p+2),brightness)});
    }
    result->frames.push_back(std::move(frame));
  }
  if(morphs.size()>=6)morphs.clear();morphs[key]=result;return {result,rev};
}
bool Graphics::begin(const Settings& s){
  end();assets.brightness=Brightness[s.brightness];
  // MatrixPortal S3 rev B/C pin map from Adafruit's official simple example.
  static uint8_t rgb[]={42,41,40,38,39,37},addr[]={45,36,48,35};
  matrix.reset(new Adafruit_Protomatter(128,2,1,rgb,4,addr,2,47,14,true));
  auto status=matrix->begin();if(status!=PROTOMATTER_OK){assets.error="Protomatter begin failed: "+String(int(status));matrix.reset();return false;}
  speak=assets.morph(Asset::Mouth,Asset::Speak,64,16);
  if(!speak.morph){assets.error="Missing/invalid mandatory mouth--mouth_speak.mph";matrix.reset();return false;}
  for(int a=1;a<=int(Asset::UwuFull);a++)if(!assets.image(Asset(a))){matrix.reset();return false;}
  for(int i=0;i<256;i++){int p=i,r,g,b;
    if(p<85){r=255-p*3;g=p*3;b=0;}else if(p<170){p-=85;r=0;g=255-p*3;b=p*3;}
    else{p-=170;r=p*3;g=0;b=255-p*3;}wheel[i]=panelColor(r,g,b,assets.brightness);
  }
  for(int i=0;i<4;i++){layers[i]=Layer{};layers[i].bitmap.width=i==0||i==1?32:64;
    layers[i].bitmap.height=i==3?32:16;layers[i].bitmap.pixels.resize(layers[i].bitmap.width*layers[i].bitmap.height);}
  x={{1,32,0,0}};y={{0,0,16,0}};phase=cadence=0;force=true;return true;
}
void Graphics::end(){if(matrix){matrix->fillScreen(0);matrix->show();matrix.reset();}speak={};for(auto& l:layers)l=Layer{};assets.clear();}
void Graphics::motion(const Sample& v,bool enabled,bool fullscreen){
  if(!enabled||fullscreen||!v.motionValid)return;
  if(std::abs(v.dx)>1||std::abs(v.dy)>1||std::abs(v.dz)>1){
    for(int i=0;i<4;i++){// Saturation prevents undefined signed overflow on sustained tilt.
      x[i]=std::max(-4096,std::min(4096,x[i]-int(v.dx)));y[i]=std::max(-4096,std::min(4096,y[i]+int(v.dy)));}
  }else{x={{1,32,0,0}};y={{0,0,16,0}};}
}
void Graphics::sparse(Layer& l,const MorphRef& ref,int step){
  auto& frames=ref.morph->frames;if(ref.reverse)step=frames.size()-1-step;
  std::fill(l.bitmap.pixels.begin(),l.bitmap.pixels.end(),0);
  for(auto p:frames[step])l.bitmap.pixels[p.y*l.bitmap.width+p.x]=p.color;
}
bool Graphics::updateLayer(int i,Asset a,bool red,bool smooth,uint32_t now){
  auto& l=layers[i];bool changed=l.shown!=a||l.red!=red;
  if(changed){
    l.morph=smooth?assets.morph(l.shown,a,l.bitmap.width,l.bitmap.height):MorphRef{};
    l.start=now;l.lastFrame=-1;l.shown=a;l.red=red;
    if(!l.morph.morph){
      std::fill(l.bitmap.pixels.begin(),l.bitmap.pixels.end(),0);
      auto img=assets.image(a);if(img)for(int yy=0;yy<std::min(img->height,l.bitmap.height);yy++)
        for(int xx=0;xx<std::min(img->width,l.bitmap.width);xx++)l.bitmap.pixels[yy*l.bitmap.width+xx]=img->pixels[yy*img->width+xx];
    }
  }
  if(l.morph.morph){int step=transitionStep(now-l.start,l.morph.morph->frames.size());
    if(step!=l.lastFrame){sparse(l,l.morph,step);l.lastFrame=step;changed=true;}
    if(now-l.start>=200)l.morph={};
  }
  return changed;
}
void Graphics::dynamic(Layer& l,Asset a,const Face& face,const String& clock){
  GFXcanvas16 c(64,32);c.fillScreen(0);uint16_t white=panelColor(255,255,255,assets.brightness);
  if(a==Asset::Clock){for(int i=0;i<5&&i<int(clock.length());i++)glyph(c,clock[i],3+i*12,9,2,white);}
  else if(a==Asset::Name){const uint8_t text[]={'Z','T','R','A','C','E','N',221};for(int i=0;i<8;i++)glyph(c,text[i],5+i*7,12,1,white);}
  else{
    const uint32_t palette[]={0,0xffffff,0xff2020,0xffd020,0x20d0ff,0x40ff60,0xd060ff};uint16_t p[7];
    for(int i=0;i<7;i++)p[i]=panelColor(palette[i]>>16,palette[i]>>8,palette[i],assets.brightness);
    c.drawRect(2,2,60,28,p[3]);c.drawFastVLine(22,4,24,p[1]);c.drawFastVLine(41,4,24,p[1]);
    const int centers[]={12,32,51};for(int i=0;i<3;i++)symbol(c,face.symbols[i],centers[i],16,p[1+face.symbols[i]%6]);
    if(face.slotSpinning)for(int yy:{7,11,21,25}){c.drawPixel(4,yy,p[4]);c.drawPixel(59,yy,p[4]);}
  }
  std::copy(c.getBuffer(),c.getBuffer()+2048,l.bitmap.pixels.begin());
}
void Graphics::render(const Face& face,const Settings& settings,uint32_t now,const String& clock,bool logicalTick){
  if(!matrix)return;
  bool rainbow=settings.get(RainbowOverride)||(settings.get(BoopRainbow)&&face.boopActive()&&!face.regions[3].active);
  if(rainbow&&!lastRainbow)phase=cadence=0;
  if(rainbow&&logicalTick&&++cadence>=3){cadence=0;++phase;}lastRainbow=rainbow;
  for(int i=0;i<4;i++){
    Asset a=face.regions[i].shown();bool red=face.regions[i].red;
    bool changed=updateLayer(i,a,red,settings.get(SmoothTransitions)||(i==2&&settings.get(SmoothSpeak)&&
      (a==Asset::Speak||layers[i].shown==Asset::Speak)),now);
    if(i==2&&face.speakManaged){layers[i].morph={};sparse(layers[i],speak,int(face.speakLevel*6+.5f));}
    if(a==Asset::Clock&&(changed||lastClock!=clock.c_str())){
      dynamic(layers[i],a,face,clock);lastClock=clock.c_str();
    }
    if(a==Asset::Name&&changed)dynamic(layers[i],a,face,clock);
    if(a==Asset::Slots&&(changed||lastSymbols!=face.symbols||lastSpinning!=face.slotSpinning)){
      dynamic(layers[i],a,face,clock);lastSymbols=face.symbols;lastSpinning=face.slotSpinning;
    }
  }
  frame.fill(0);
  // TileGroups are opaque, including black. Copy nose, eye, mouth, then whole.
  const int order[]={1,0,2,3};bool whole=face.regions[3].active;
  for(int side=0;side<2;side++)for(int idx:order){
    if((whole&&idx!=3)||(!whole&&idx==3))continue;
    auto& l=layers[idx];int w=l.bitmap.width,h=l.bitmap.height;
    int sourceX=idx==0?31:0;int baseX=side?sourceX:x[idx];int baseY=y[idx];
    if(side)baseX+=x[idx]-(64-sourceX-w);
    for(int yy=0;yy<h;yy++)for(int xx=0;xx<w;xx++){
      int localX=side?xx:w-1-xx;int destX=side*64+baseX+localX,destY=baseY+yy;
      // A displayio screen Group does not clip at its 64px boundary.
      if(destX<0||destX>=128||destY<0||destY>=32)continue;
      uint16_t color=l.bitmap.pixels[yy*w+xx];
      if(color){if(rainbow)color=wheel[(localX*10+yy*16+phase*8)&255];
        else if(l.red)color=panelColor(255,0,0,assets.brightness);}
      frame[destY*128+destX]=color;
    }
  }
  if(force||frame!=previous){std::copy(frame.begin(),frame.end(),matrix->getBuffer());matrix->show();previous=frame;force=false;}
}
}
