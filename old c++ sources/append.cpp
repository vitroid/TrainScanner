#include <opencv/cv.h>
#include <opencv/highgui.h>
#include <ctype.h>
#include <iostream>
#include <vector>
#include <cstdio>
#include "tscanvas.hpp"
using namespace std;

#include <sys/stat.h>

int fexist( char *filename ) {
  struct stat buffer ;
  if ( stat( filename, &buffer ) ) return 0 ;
  return 1 ;
}


void usage(int argc, char* argv[])
{
  cout << "usage: " << argv[0] << " [-v][-d n] moviefile\n";
  cout << "\t-v\tVerbose." << endl;
  cout << "\t-d n\tDirection (default=0)." << endl;
  exit(1);
}

#define CVCLOSE_ITR 1

int
main (int argc, char **argv)
{
  int result;
  int direction = 0;
  int verbosity = 1;
  while((result=getopt(argc,argv,"vd:"))!=-1){
    switch(result){
      case 'd':
        // by default,frames are laid at the center of image. Positive value moves the point to forward.
        // the value must be between -100 and +100
        sscanf( optarg, "%d", &direction );
        break;
      case 'v':
        //verbose
        verbosity += 1;
        break;
      case ':':
        usage( argc, argv );
        break;
      case '?':
        usage( argc, argv );
        break;
    }
  }
  
  if (optind +1 != argc){
    usage( argc,argv );
  }

  int n = 0;
  char filename[1000];
  sprintf( filename, "%s_%03d.tif", argv[optind],n );
  cout << filename << endl;
  int margin = 2;
  TSCanvas canvas( cvLoadImage( filename ), margin );
  int lastw = canvas.getImage()->width;
  int lasth = canvas.getImage()->height;
  n += 1;
  while ( 1 ){
    sprintf( filename, "%s_%03d.tif", argv[optind],n );
    if ( ! fexist( filename ) ) break;
    cout << filename << endl;
    IplImage* frame = cvLoadImage( filename );
    if ( direction == 0 ){
      canvas.add( frame, lastw, 0, 100, verbosity );
    }
    else if ( direction == 1 ){
      canvas.add( frame, 0, -frame->height, 100, verbosity );
    }
    else if ( direction == 2 ){
      canvas.add( frame, -frame->width, 0, 100, verbosity );
    }
    else if ( direction == 3 ){
      canvas.add( frame, 0, lasth, 100, verbosity );
    }      
    lastw = frame->width;
    lasth = frame->height;
    n += 1;
    cvReleaseImage( &frame );
  }
  sprintf( filename, "%s.tif", argv[optind] );
  cout << filename << endl;
  if ( fexist( filename ) ){
    IplImage* frame = cvLoadImage( filename );
    if ( direction == 0 ){
      canvas.add( frame, lastw, 0, 100, verbosity );
    }
    else if ( direction == 1 ){
      canvas.add( frame, 0, -frame->height, 100, verbosity );
    }
    else if ( direction == 2 ){
      canvas.add( frame, -frame->width, 0, 100, verbosity );
    }
    else if ( direction == 3 ){
      canvas.add( frame, 0, lasth, 100, verbosity );
    }      
    //lastw = frame->width;
    cvReleaseImage( &frame );
  }

  sprintf(filename, "%s_append.tif", argv[optind] );
  cvSaveImage( filename, canvas.detach() );

  return 0;
}
