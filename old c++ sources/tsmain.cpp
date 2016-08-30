#include <ctype.h>
#include <iostream>
#include <vector>
#include <cstdio>
#include "trainscanner.hpp"

using namespace std;

void usage(int argc, char* argv[])
{
  cout << "usage: " << argv[0] << " [-q][-v][-d x,y][-S][-s n][-o n][-a x] moviefile\n";
  cout << "\t-q\tQuiet." << endl;
  cout << "\t-v\tVerbose." << endl;
  cout << "\t-S\tStraighten (experimental)." << endl;
  cout << "\t-a x\tStraighten with angle x." << endl;
  cout << "\t-s n\tSplit the output in n pixels." << endl;
  cout << "\t-V x,y\tVanishing point." << endl;
  cout << "\t-d x,y\tDefault delta between frames." << endl;
  cout << "\t-o n\tLet the overlaid frame larger (in percent)." << endl;
  exit(1);
}

int
main (int argc, char **argv)
{
  int result;
  int offset = 0;
  int split = 0;
  int straighten = 0;
  int dx = 0;
  int dy = 0;
  int vanishx = 0;
  int vanishy = 0;
  int verbosity = 1;
  float angle = 0.0;
  while((result=getopt(argc,argv,"a:qvd:Ss:o:V:"))!=-1){
    switch(result){
      case 'o':
        // by default,frames are laid at the center of image. Positive value moves the point to forward.
        // the value must be between -100 and +100
        sscanf( optarg, "%d", &offset );
        break;
      case 's':
        // Split the output images in specified pixels
        // to reduce memory usage.
        sscanf( optarg, "%d", &split );
        break;
      case 'a':
        sscanf( optarg, "%f", &angle );
        break;
      case 'S':
        // straighten
        straighten = 1;
        break;
      case 'v':
        //verbose
        verbosity += 1;
        break;
      case 'q':
        //quiet
        verbosity = 0;
        break;        
      case 'd':
        // default delta
        sscanf( optarg, "%d,%d", &dx, &dy );
        break;
      case 'V':
        sscanf( optarg, "%d,%d", &vanishx, &vanishy );
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

  TrainScanner trainscanner( dx,dy,split,straighten,offset,angle,vanishx, vanishy,verbosity, argv[optind] );
  while ( trainscanner.update() == 0 ){
  }
  return 0;
}
