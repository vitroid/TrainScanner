#include <opencv/cv.h>
#include <opencv/highgui.h>
#include <ctype.h>
#include <iostream>
#include <vector>
#include <list>
#include <cstdio>
#include <cmath>
#include "tscanvas.hpp"

float match_rgbimages( IplImage* i0, IplImage* i1,
                   int xs, int xe, int ys, int ye,
		       int* resx, int* resy );

class FirstPass {
private:
  int dx;
  int dy;
  vector<int>& vx;
  vector<int>& vy;
  vector<int>& fr;
  int offset;
  int verbosity;
  float angle;
  int vanishx;
  int vanishy;

  int npurge;
  //adaptive match depth
  int amdepth;
  // Number of frames
  int counter;
  int succ;
  //CvMat M;
  float mat[6];
  vector<int> mx;
  vector<int> my;
  CvCapture* capture;
  //IplImage* one;
  IplImage* tmp1;
  IplImage* tmp2;
  IplImage* frame;
  IplImage* masked;
  IplImage* last_img;
  TSCanvas* canvas;
public:
  int scale;
  FirstPass( const char* filename,
	     int dx, 
	     int dy,
	     vector<int>& vx,
	     vector<int>& vy,
	     vector<int>& fr,
	     int offset,
	     int vanishx,
	     int vanishy,
	     int verbosity,
	     float angle );
  ~FirstPass();
  int update();
};



class SecondPass {
private:
  char* basename;
  const vector<int>& vx;
  const vector<int>& vy;
  const vector<int>& fr;
  int scale;
  int isHoriz;
  int offset;
  int split;
  int straighten;
  int verbosity;
  float angle;
  IplImage* frame;
  IplImage* masked;
  IplImage* tmp1;
  IplImage* last_img;
  CvCapture* capture;
  //CvMat M;
  float mat[6];
  int npurge;
  int counter;
  float lastdx;
  float lastdy;
  int elem;
  int vanishx;
  int vanishy;

public:
  TSCanvas* canvas;
  SecondPass( const char* filename_,
	      const vector<int>& vx_,
	      const vector<int>& vy_,
	      const vector<int>& fr_,
	      int scale_,
	      int isHoriz_,
	      int offset_,
	      int split_,
	      int straighten_,
	      int vanishx,
	      int vanishy,
	      int verbosity_,
	      float angle_ );
  ~SecondPass();
  int update();
};


class TrainScanner {
private:
  int dx;
  int dy;
  int split;
  int straighten;
  int offset;
  float angle;
  int verbosity;
  char* movie;
  //internal
  CvCapture* capture;
  vector <int> vx,vy,fr;
  int stage;
  FirstPass* firstpass;
  SecondPass* secondpass;
  int horiz;
  int scale;
  int vanishx,vanishy;
public:
  TrainScanner( int dx_,
		int dy_,
		int split_,
		int straighten_,
		int offset_,
		float angle_,
		int vanishx_,
		int vanishy_,
		int verbosity_,
		const char* movie_ );
  ~TrainScanner();
  int update();

};

