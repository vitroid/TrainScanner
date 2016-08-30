#ifndef _TSCANVAS_H
#define _TSCANVAS_H
#include <opencv/cv.h>
#include <opencv/highgui.h>
#include <ctype.h>
#include <iostream>
#include <vector>
#include <cstdio>
void subcopy( IplImage* src, int sx, int sy, IplImage* dst, int dx, int dy, int width, int height );

using namespace std;

class TSCanvas {
  //origin on the canvas
  int originx;
  int originy;
  int incrw;
  int incrh;
  //int last10;
  //int npaste;
  IplImage* img;
  int expands;
public:
  TSCanvas( IplImage* i, int expands_=10 ):  img(i), expands(expands_) {
    originx = 0;
    originy = 0;
    incrw   = 10;
    incrh   = 10;
    //last10  = 0;
    //npaste  = 0;
  }
  ~TSCanvas(){
    if ( img )
      cvReleaseImage( &img );
  }
  //extract the canvas image
  IplImage* detach(){
    IplImage* i = img;
    img = 0;
    return i;
  }
  //
  IplImage* getImage(){
    return img;
  }
// Put a fragment image at the specified position of the expansible canvas.
// The canvas automatically expands when the fragment protrudes.
// Returns the expanded canvas.
  void add( IplImage* fragment, int dx, int dy, int offset, int verbosity )
  {
    int fragw = fragment->width;
    int fragh = fragment->height;
    int canw = img->width;
    int canh = img->height;
    offset = offset * (fragw+fragh) / 250; //from percent to absolute pixel size
    //npaste += 1;

    //int fragorigx = originx + dx;
    //int fragorigy = originy + dy;
    int neww = canw;
    int newh = canh;
    int newcanox = 0;  // new origin of the expanded campas
    int newcanoy = 0;
    
    int expand = 0;
    while ( neww < originx + dx + fragw ){
      expand += 1;
      neww += incrw;
    }
    while ( newh < originy + dy + fragh ){
      expand += 1;
      newh += incrh;
    }
    while (originx + dx < 0){
      expand += 1;
      neww += incrw;
      originx += incrw;
      newcanox += incrw;
      //fragorigx += 100;
    }
    while (originy + dy < 0){
      expand += 1;
      newh += incrh;
      originy += incrh;
      newcanoy += incrh;
      //fragorigy += 100;
    }
    if ( expand ){
      //last10 += 1;
      incrw = abs(dx) * expands;
      incrh = abs(dy) * expands;
      if ( incrw < 400 ) incrw = 400;
      if ( incrh < 400 ) incrh = 400;
      
      IplImage* newimg = cvCreateImage (cvSize (neww, newh), IPL_DEPTH_8U, 3);
      if ( verbosity == 2 ){
	printf("expanded to %d %d, and append at %d %d, size %d %d\n", neww,newh, originx, originy, canw, canh);
      }
      subcopy( img, 0,0, newimg, newcanox, newcanoy, canw, canh );
      cvReleaseImage (&img);
      img = newimg;
    }
    //if ( npaste % 10 == 0 ){
    /*
if (last10 > 1){
	cout << "Bonus" << endl;
	incrh = incrh * 2;
	incrw = incrw * 2;
      }
      last10 = 0;
    }
    */
    int halfh = fragh / 2;
    int halfw = fragw / 2;
    
    originx += dx;
    originy += dy;
    //cout << neww << "\t" << originx << "\t" << dx <<"\t" << fragw << endl;
    float delta = dx*dx + dy*dy;
    float rootd = sqrt(delta);
    if ( delta > 2*50*50 ){
      delta = 2*50*50;
    }
    for ( int y=0; y<fragh; y++ ){
      for ( int x=0; x<fragw; x++ ){
	int relx = x - halfw;
	int rely = y - halfh;
	float det = dx*relx + dy*rely;
	for (int ch=0; ch<3; ch++){
	  if ( det > delta - rootd*offset){
	    int p0 = fragment->imageData[fragment->widthStep * y + x * 3 + ch];
	    img->imageData[img->widthStep * (originy+y) + (originx+x) * 3 + ch] = p0;
	  }
	  else if ( det > - rootd*offset ){
	    float mix = (det+rootd*offset) / delta;
	    float p0 = (unsigned char)fragment->imageData[fragment->widthStep * y + x * 3 + ch];
	    float p1 = (unsigned char)img->imageData[img->widthStep * (originy+y) + (originx+x) * 3 + ch];
	    float p2 = p0*mix + p1*(1.0-mix);
	    img->imageData[img->widthStep * (originy+y) + (originx+x) * 3 + ch] = p2;
	  }
	}
      }
    }
    //return img;
  }

  //If the canvas becomes too large, purge the static part.
  void purge( int& npurge, const char* basename, IplImage* frame, int outwidth )
  {
    //horizontal case
    const int MARGIN = 100;
    if ( img->width > img->height ){
      if ( img->width > outwidth ){
	if ( originx + frame->width + MARGIN + outwidth < img->width ){
	  IplImage* newimg = cvCreateImage (cvSize (outwidth, img->height), IPL_DEPTH_8U, 3);
	  int delta = img->width - outwidth;
	  subcopy( img, delta, 0, newimg, 0, 0, outwidth, img->height );
	  if ( basename ){
	    char filename[1000];
	    sprintf(filename, "%s_%03d.tif", basename, npurge );
	    cvSaveImage( filename, newimg );
	  }
	  cvReleaseImage( &newimg );
	  newimg = cvCreateImage (cvSize (delta, img->height), IPL_DEPTH_8U, 3);
	  subcopy( img, 0, 0, newimg, 0, 0, delta, img->height );
	  cvReleaseImage( &img );
	  img = newimg;
	  npurge += 1;
	  return;
	}
	if ( outwidth + MARGIN < originx ){
	  IplImage* newimg = cvCreateImage (cvSize (outwidth, img->height), IPL_DEPTH_8U, 3);
	  int delta = img->width - outwidth;
	  subcopy( img, 0, 0, newimg, 0, 0, outwidth, img->height );
	  if ( basename ){
	    char filename[1000];
	    sprintf(filename, "%s_%03d.tif", basename, npurge );
	    cvSaveImage( filename, newimg );
	  }
	  cvReleaseImage( &newimg );
	  newimg = cvCreateImage (cvSize (delta, img->height), IPL_DEPTH_8U, 3);
	  subcopy( img, outwidth, 0, newimg, 0, 0, delta, img->height );
	  cvReleaseImage( &img );
	  img = newimg;
	  originx -= outwidth;
	  npurge += 1;
	  return;
	}
      }
    }
    else{
      if ( img->height > outwidth ){
	if ( originy + frame->height + MARGIN + outwidth < img->height ){
	  IplImage* newimg = cvCreateImage (cvSize (img->width, outwidth), IPL_DEPTH_8U, 3);
	  int delta = img->height - outwidth;
	  subcopy( img, 0, delta, newimg, 0, 0, img->width, outwidth );
	  if ( basename ){
	    char filename[1000];
	    sprintf(filename, "%s_%03d.tif", basename, npurge );
	    cvSaveImage( filename, newimg );
	  }
	  cvReleaseImage( &newimg );
	  newimg = cvCreateImage (cvSize (img->width, delta), IPL_DEPTH_8U, 3);
	  subcopy( img, 0, 0, newimg, 0, 0, img->width, delta );
	  cvReleaseImage( &img );
	  img = newimg;
	  npurge += 1;
	  return;
	}
	if ( outwidth + MARGIN < originy ){
	  IplImage* newimg = cvCreateImage (cvSize (img->width, outwidth), IPL_DEPTH_8U, 3);
	  int delta = img->height - outwidth;
	  subcopy( img, 0, 0, newimg, 0, 0, img->width, outwidth );
	  if ( basename ){
	    char filename[1000];
	    sprintf(filename, "%s_%03d.tif", basename, npurge );
	    cvSaveImage( filename, newimg );
	  }
	  cvReleaseImage( &newimg );
	  newimg = cvCreateImage (cvSize (img->width, outwidth), IPL_DEPTH_8U, 3);
	  subcopy( img, 0, outwidth, newimg, 0, 0, img->width, delta );
	  cvReleaseImage( &img );
	  img = newimg;
	  originy -= outwidth;
	  npurge += 1;
	  return;
	}
      }
    }
    return;
  }
};


#endif
