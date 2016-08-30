#include "tscanvas.hpp"

using namespace std;

void subcopy( IplImage* src, int sx, int sy, IplImage* dst, int dx, int dy, int width, int height )
{
  for ( int y=0; y<height; y++ ){
    for ( int x=0; x<width; x++ ){
      for (int ch=0; ch<3; ch++){
	dst->imageData[dst->widthStep * (dy+y) + (dx+x) * 3 + ch] = 
	  src->imageData[src->widthStep * (sy+y) + (sx+x) * 3 + ch];
      }
    }
  }
}



