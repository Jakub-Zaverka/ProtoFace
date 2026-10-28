#pragma once

namespace proto {
constexpr int PanelWidth=64,PanelHeight=32,PanelCount=2;
struct PanelMapping {
  int offsetX;
  bool mirrorFaceX;
  bool mirrorFullscreenX;
  constexpr int pixelX(int sourceX,int width,bool fullscreen)const{
    return (fullscreen?mirrorFullscreenX:mirrorFaceX)?width-1-sourceX:sourceX;
  }
  constexpr bool contains(int x,int y)const{
    return x>=offsetX&&x<offsetX+PanelWidth&&y>=0&&y<PanelHeight;
  }
};
// Physical chain: ESP -> LEFT -> RIGHT. The physical left panel corresponds
// to framebuffer half 1, not half 0 (confirmed by the wearer's text test).
// Faces retain their symmetric mapping; readable fullscreen is unmirrored.
inline constexpr PanelMapping Panels[PanelCount]={
  {0, true, false}, // Physical RIGHT, framebuffer columns 0..63
  {64,false,false},// Physical LEFT, framebuffer columns 64..127
};
}
