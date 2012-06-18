#include "trainscanner.hpp"

using namespace std;





void Skew( IplImage* i0, IplImage* i1, int vanishx, int vanishy )
{
  int w = i0->width;
  int h = i0->height;
  //cout << "a " << a << endl;
  if ( h < vanishy ){
    float a = -log(1.0-(float)h/vanishy)/(float)h;
    for ( int y=0; y<h; y++ ){
      for ( int x=0; x<w; x++ ){
	float ratio = exp(-a*y);
	int newy = vanishy - (int)(vanishy * ratio);
	int newx = (int)((x - vanishx)*ratio) + vanishx;
	//cout << x << "," << y << "," << newx <<"," << newy << endl;
	for (int ch=0; ch<3; ch++){
	  i1->imageData[i1->widthStep * y + x * 3 + ch] = 
	    i0->imageData[i0->widthStep * newy + newx * 3 + ch];
	}
      }
    }
  }
  else if ( vanishy < 0 ){
    float a = -log(1.0-(float)h/(h-vanishy))/(float)h;
    for ( int y=0; y<h; y++ ){
      for ( int x=0; x<w; x++ ){
	float ratio = exp(-a*(h-y));
	int newy = (int)((h-vanishy) * ratio) + vanishy;
	int newx = (int)((x - vanishx)*ratio) + vanishx;
	//cout << x << "," << y << "," << newx <<"," << newy << endl;
	for (int ch=0; ch<3; ch++){
	  i1->imageData[i1->widthStep * y + x * 3 + ch] = 
	    i0->imageData[i0->widthStep * newy + newx * 3 + ch];
	}
      }
    }
  }
}




float sum( const vector<int>& v )
{
  float s = 0;
  for(int i=0; i<v.size(); i++ ){
    s += v[i];
  }
  return s;
}




//Compare pixels one by one, and fill black if they coincide.
//Returns the similarity of the images. (Similarity == percentage of coinciding pixels.)
float genMask( IplImage* i0, IplImage* i1, int dx, int dy )
{
  int w = i0->width;
  int h = i0->height;
  float similarity = 0;
  for ( int y=0; y<h; y++ ){
    for ( int x=0; x<w; x++ ){
      int yi = y + dy;
      int xi = x + dx;
      if ( (0 <= xi) && (xi < w) && (0<=yi) && (yi<h) ){
        int d = 0;
        int m = 0;
        for (int ch=0; ch<3; ch++){
          unsigned char p0 = i0->imageData[i0->widthStep * y + x * 3 + ch];
          unsigned char p1 = i1->imageData[i1->widthStep * (y+dy) + (x+dx) * 3 + ch];
          int diff = p0;
          diff -= p1;
          d += abs(diff);
          m += p0+p1;
        }
        //if they are similar, ie. the intensity is almost the same for two pixels,
        if ( d*13 < m ){
          //fill black
          for (int ch=0; ch<3; ch++){
            i0->imageData[i0->widthStep * y + x * 3 + ch] = 0;
          }
          similarity += 1.0;
        }
      }
    }
  }
  //return the similarity, which is defined as the ratio of similar pixels
  return similarity / w / h;
}

	
      
//Crude translation-invariant image matching
float match_rgbimages( IplImage* i0, IplImage* i1,
                   int xs, int xe, int ys, int ye,
                   int* resx, int* resy )
{
  int ox,oy,px,py,qx,qy;
  int w,h;
  w = i0->width;
  h = i0->height;
  float bestscore=-1;
  int w0,h0;
  if ( 0 < xs ){
    w0 = w - xe;
    qx = xe;
  }
  else if ( 0 < xe ){
    w0 = w - (xe-xs);
    qx = xe;
  }
  else{
    w0 = w + xs;
    qx = 0;
  }
  if ( 0 < ys ){
    h0 = h - ye;
    qy = ye;
  }
  else if ( 0 < ye ){
    h0 = h - (ye-ys);
    qy = ye;
  }
  else{
    h0 = h + ys;
    qy = 0;
  }
  for(oy=ys; oy<=ye; oy++){
    for(ox=xs; ox<=xe; ox++){
      float s0 = 0;
      float s1 = 0;
      float s2 = 0;
      float sx = 0;
      float sy = 0;
      float xxaa = 0;
      float xaa = 0;
      float yybb = 0;
      float ybb = 0;
      float co = 0;
      for( py=0; py<h0; py++ ){
        for( px=0; px<w0; px++ ){
          int x,y;
          x = px+qx;
          y = py+qy;
          if ( x< 0 || y < 0 ){
            exit (1);
          }
          float p0[3];
          p0[0] = i0->imageData[i0->widthStep * y + x * 3];        // B
          p0[1] = i0->imageData[i0->widthStep * y + x * 3 + 1];    // G
          p0[2] = i0->imageData[i0->widthStep * y + x * 3 + 2];    // R
          float v0 = p0[0] + p0[1] + p0[2];
          //fprintf(stderr,"%f ",v0);
          x = px+qx-ox;
          y = py+qy-oy;
          if ( x< 0 || y < 0 ){
            exit (2);
          }
          float p1[3];
          p1[0] = i1->imageData[i1->widthStep * y + x * 3];        // B
          p1[1] = i1->imageData[i1->widthStep * y + x * 3 + 1];    // G
          p1[2] = i1->imageData[i1->widthStep * y + x * 3 + 2];    // R
          float v1 = p1[0] + p1[1] + p1[2];
          //if ( v1 > 0.0 ){
          s0 += v0*v1;
          s1 += v0;
          s2 += v1;
          sx += v0;
          sy += v1;
          xaa += v0;
          xxaa += v0*v0;
          ybb += v1;
          yybb += v1*v1;
          //}
          co ++;
        }
      }
      sx /= co;
      sy /= co;
      //covariance
      float score = s0 - s1*sy - s2*sx + co*sx*sy;
      //correlation
      float score2 = score / sqrt( (xxaa-2*sx*xaa+sx*sx*co) * (yybb-2*sy*ybb+sy*sy*co));
      //fprintf(stderr,"%d %d (%d) %f %f %f %f %f %f\n",ox,oy,w,score2,sx,sy,s1,s2,s3);
    ext:
      //fprintf(stderr, "%d %d=%f\n", ox,oy, score2);
      if ( score2 > bestscore ){
        *resx = ox;
        *resy = oy;
        bestscore = score2;
      }
    }
  }
  //fprintf(stderr,"\n");
  return bestscore;
}



//Recursive translation-invariant image matching
float match_recursively( IplImage* i0, IplImage* i1,
			int depth, int* resx, int* resy, int delh, int delv )
{
  float score;
  int x,y;
  x = 0;
  y = 0;
  if ( depth > 0 ){
    int w = i0->width /2 ;
    int h = i0->height /2;
    IplImage* i0h = cvCreateImage (cvSize (w, h), IPL_DEPTH_8U, 3);
    cvResize( i0, i0h, CV_INTER_NN );
    w = i1->width / 2;
    h = i1->height /2;
    IplImage* i1h = cvCreateImage (cvSize (w, h), IPL_DEPTH_8U, 3);
    cvResize( i1, i1h, CV_INTER_NN );
    match_recursively( i0h, i1h, depth - 1, &x, &y, delh, delv );
    cvReleaseImage( &i0h );
    cvReleaseImage( &i1h );
    //printf("%d %d %d\n", depth, x,y);
    x *= 2;
    y *= 2;
  }
  if ( depth == 0 ){
    score = match_rgbimages( i0, i1, x-2*delh, x+2*delh, y-2*delv, y+2*delv, &x, &y );
  }
  else{
    score = match_rgbimages( i0, i1, x-delh, x+delh, y-delv, y+delv, &x, &y );
  }
  *resx = x;
  *resy = y;
  return score;
}


//Recursive translation-invariant image matching
float match_recursively2( IplImage* i0, IplImage* i1,
                        int depth, int& resx, int& resy, int isHoriz )
{
  int delh, delv;
  if (isHoriz){
    delh = 1;
    delv = 0;
  }
  else{
    delh = 0;
    delv = 1;
  }
  float score;
  int x,y;
  x = resx;
  y = resy;
  if ( depth > 0 ){
    int w = i0->width /2 ;
    int h = i0->height /2;
    x /= 2;
    y /= 2;
    IplImage* i0h = cvCreateImage (cvSize (w, h), IPL_DEPTH_8U, 3);
    cvResize( i0, i0h, CV_INTER_NN );
    w = i1->width / 2;
    h = i1->height /2;
    IplImage* i1h = cvCreateImage (cvSize (w, h), IPL_DEPTH_8U, 3);
    cvResize( i1, i1h, CV_INTER_NN );
    match_recursively2( i0h, i1h, depth - 1, x, y, isHoriz );
    cvReleaseImage( &i0h );
    cvReleaseImage( &i1h );
    x *= 2;
    y *= 2;
  }
  if ( depth == 0 ){
    score = match_rgbimages( i0, i1, x-2*delh, x+2*delh, y-2*delv, y+2*delv, &x, &y );
  }
  else{
    score = match_rgbimages( i0, i1, x-delh, x+delh, y-delv, y+delv, &x, &y );
  }
  resx = x;
  resy = y;
  return score;
}








    


FirstPass::FirstPass( const char* filename,
		      int dx_, 
		      int dy_,
		      vector<int>& vx_,
		      vector<int>& vy_,
		      vector<int>& fr_,
		      int offset_,
		      int vanishx_,
		      int vanishy_,
		      int verbosity_,
		      float angle_) : dx(dx_),
				      dy(dy_),
				      vx(vx_),
				      vy(vy_),
				      fr(fr_),
				      offset(offset_),
				      vanishx(vanishx_),
				      vanishy(vanishy_),
				      verbosity(verbosity_),
				      angle(angle_)
{
  //retrieve the file name
  //The name is also used for the prefix of the output file.
  capture = cvCaptureFromFile( filename );
  
  //Capture the first frame to determine the image size.
  IplImage* one = cvQueryFrame (capture);
  tmp1 = cvCloneImage( one );
  last_img = 0;
  int w = one->width;
  int h = one->height;
  //determine gradient
  mat[2] = w / 2;
  mat[5] = h / 2;
  scale = 0;
  float fscale = 1.0;
  while ( w > 256 && h > 256 ){
    w /= 2;
    h /= 2;
    scale += 1;
    fscale /= 2.0;
  }
  float co = cos(angle*M_PI/180.0);
  float si = sin(angle*M_PI/180.0);
  mat[0] = co;
  mat[1] = -si;
  mat[3] = si;
  mat[4] = co;
  CvMat M;
  cvInitMatHeader (&M, 2, 3, CV_32FC1, mat, CV_AUTOSTEP);

  frame   = cvCreateImage (cvSize (w, h), IPL_DEPTH_8U, 3);
  tmp2    = cvCloneImage( frame );
  last_img= cvCreateImage (cvSize (w, h), IPL_DEPTH_8U, 3);
  cvGetQuadrangleSubPix ( one,tmp1, &M);
  IplImage* guideimage = cvCloneImage( tmp1 );
  if ( vanishx || vanishy ){
    int w = tmp1->width;
    int h = tmp1->height;
    cout << vanishx <<":" <<vanishy << endl;
    for(int i=0; i<8; i++){
      cvLine(guideimage, cvPoint(vanishx,vanishy), cvPoint(w*i/8,0), CV_RGB (255, 0, 0), 1, 8, 0);
      cvLine(guideimage, cvPoint(vanishx,vanishy), cvPoint(0,h*i/8), CV_RGB (255, 0, 0), 1, 8, 0);
      cvLine(guideimage, cvPoint(vanishx,vanishy), cvPoint(w*i/8,h), CV_RGB (255, 0, 0), 1, 8, 0);
      cvLine(guideimage, cvPoint(vanishx,vanishy), cvPoint(w,h*i/8), CV_RGB (255, 0, 0), 1, 8, 0);
    }
    for (int i=1;i<4; i++){
      cvLine(guideimage, cvPoint(0,h*i/4), cvPoint(w,h*i/4), CV_RGB (255, 0, 0), 1, 8, 0);
      cvLine(guideimage, cvPoint(w*i/4,0), cvPoint(w*i/4,h), CV_RGB (255, 0, 0), 1, 8, 0);
    }
    IplImage* skew = cvCloneImage( guideimage );
    Skew( guideimage, skew, vanishx, vanishy );
    cvShowImage ("First frame", guideimage);
    cvShowImage ("Skew image", skew);
    vanishx >>= scale;
    vanishy >>= scale;
    cvResize( tmp1, tmp2, CV_INTER_NN );
    Skew( tmp2, last_img, vanishx, vanishy );
    cvReleaseImage( &guideimage );
    cvReleaseImage( &skew );
  }
  else{
    cvResize( tmp1, last_img, CV_INTER_NN );
  }
  masked   = cvCreateImage (cvSize (w, h), IPL_DEPTH_8U, 3);
  
  
   //for test
  npurge = 0;
  //adaptive match depth
  amdepth = 1;
  // Number of frames
  counter=1;
  succ = 0;
  canvas = new TSCanvas( cvCloneImage( last_img ) );
  //cvReleaseImage( &one );
}



int
FirstPass::update()
{
  //Retrieve a frame
  IplImage* one = cvQueryFrame ( capture );
  //printf("%d\n", res);
  if ( one == NULL ){
    if (verbosity == 2 ){
      cout << "End of the movie." << endl;
    }
    return 1;
  }
  //M is not preserved......why
  CvMat M;
  cvInitMatHeader (&M, 2, 3, CV_32FC1, mat, CV_AUTOSTEP);
  cvGetQuadrangleSubPix ( one,tmp1, &M);
  //cvShowImage ("Original", one);
  //cvShowImage ("Rotated", tmp1);
  if ( vanishx || vanishy ){
    cvResize( tmp1, tmp2, CV_INTER_NN);
    Skew( tmp2, frame, vanishx, vanishy );
  }
  else{
    cvResize( tmp1, frame, CV_INTER_NN);
  }
  //cvResize( one, frame, CV_INTER_NN);
  //cvShowImage ("Input", frame);
    
  int x,y;
  //match_recursively( last_img, frame, 2,&x,&y, 1,1);
  x = y = 0;
  cvCopy( frame, masked );
  // Fill background in black.
  float similarity = genMask( masked, last_img, x, y );
  cvShowImage ("Mask", masked);
  if ( similarity > 0.985 ){
    cvCopy( frame, last_img );
    if ( succ > 10 ){
      if (verbosity == 2 ){
	cout << "Similar frames" << succ << "," << similarity << endl;
      }
      return 1;
    }
    succ = 0;
  }
  else{
    //dx and dy are the last translational vector.
    dx += x;
    dy += y;
    //Expect that the translation vector is unchanged.
    int ex,ey;
    float score0 = match_rgbimages( last_img, masked, dx-1, dx+1, dy-1,dy+1, &ex,&ey);
    score0 *= 2; // optical inertia
    //Calculate the translation vector by image matching
    float score = match_recursively( last_img, masked, amdepth, &dx,&dy, 1,1 );
    //Use the better results of the two.
    if ( score0 > score ){
      dx = ex;
      dy = ey;
      score = score0;
    }
    fr.push_back(counter);
    
    //median filter
    mx.push_back(dx);
    int i=mx.size() - 7;
    if ( i < 0 ) i=0;
    vector<int> m;
    for(;i<mx.size();i++){
      m.push_back(mx[i]);
    }
    std::sort(m.begin(),m.end());
    dx = m[m.size()/2];
    vx.push_back(dx);
    
    my.push_back(dy);
    i=my.size() - 7;
    if ( i < 0 ) i=0;
    m.resize(0);
    for(;i<my.size();i++){
      m.push_back(my[i]);
    }
    std::sort(m.begin(),m.end());
    dy = m[m.size()/2];
    vy.push_back(dy);
    
    if ( verbosity == 1 ){
      cout << counter << "\t" << dx << "\t" << dy;
      cout << endl;
    }
    else if (verbosity == 2 ){
      cout << counter << "\t" << dx << "\t" << dy << "\t" << score << "\t" << similarity << "\t" << amdepth;
      cout << endl;
    }
    
    cvCopy( frame, last_img );
    canvas->add( frame, dx,dy, offset, verbosity );
    canvas->purge( npurge, NULL, frame, 1000 );
    cvShowImage ("Canvas", canvas->getImage() );
    
    //adapt the pyramid depth
    if ( dx < (1 << amdepth) && dy < (1 << amdepth )){
      if ( amdepth > 1 ){
	amdepth -= 1;
      }
    }
    if ( dx > (1 << amdepth) || dy > (1 << amdepth )){
      amdepth += 1;
    }
    succ++;
  }
  
  counter++;
  char c = cvWaitKey (10);
  if (c == '\x1b')
    return 1;
  return 0;
}



FirstPass::~FirstPass()
{
  cvReleaseImage (&frame);
  cvReleaseImage (&tmp1);
  cvReleaseImage (&tmp2);
  cvReleaseImage (&masked);
  cvReleaseImage (&last_img);
  cvReleaseCapture( &capture );
  delete canvas;
}    



SecondPass::SecondPass( const char* filename,
			const vector<int>& vx_,
			const vector<int>& vy_,
			const vector<int>& fr_,
			int scale_,
			int isHoriz_,
			int offset_,
			int split_,
			int straighten_,
			int vanishx_,
			int vanishy_,
			int verbosity_,
			float angle_ ) : vx(vx_),
					 vy(vy_),
					 fr(fr_),
					 scale(scale_),
					 isHoriz(isHoriz_),
					 offset(offset_),
					 split(split_),
					 straighten(straighten_),
					 vanishx(vanishx_),
					 vanishy(vanishy_),
					 verbosity(verbosity_),
					 angle(angle_)
{
  basename = strdup( filename );
  //retrieve the file name
  //The name is also used for the prefix of the output file.
  capture = cvCaptureFromFile( filename );
  
  //Capture the first frame to determine the image size.
  IplImage* one = cvQueryFrame (capture);

  int w = one->width;
  int h = one->height;
  
  //canvas = cvCreateImage (cvSize (w, h), IPL_DEPTH_8U, 3);
  //cvNot( canvas, canvas );

  CvMat M;
  if ( straighten ){
    //determine gradient
    float dx = sum( vx );
    float dy = sum( vy );
    float dd = sqrt(dx*dx + dy*dy);
    dx /= dd;
    dy /= dd;
    if ( isHoriz ){
      if ( dx < 0 ){
	dx = -dx;
	dy = -dy;
      }
      mat[0] = dx;
      mat[1] = -dy;
      mat[3] = dy;
      mat[4] = dx;
      mat[2] = w / 2;
      mat[5] = h / 2;
    }
    else{
      if ( dy < 0 ){
	dx = -dx;
	dy = -dy;
      }
      mat[0] = dy;
      mat[1] = dx;
      mat[3] = -dx;
      mat[4] = dy;
      mat[2] = w / 2;
      mat[5] = h / 2;
    }
    cvInitMatHeader (&M, 2, 3, CV_32FC1, mat, CV_AUTOSTEP);
  }
  if ( angle != 0.0 ){
    float dx = cos(angle*M_PI/180.0);
    float dy = sin(angle*M_PI/180.0);
    mat[0] = dx;
    mat[1] = -dy;
    mat[3] = dy;
    mat[4] = dx;
    mat[2] = w / 2;
    mat[5] = h / 2;
    cvInitMatHeader (&M, 2, 3, CV_32FC1, mat, CV_AUTOSTEP);
  }
  npurge = 0;
 // Number of frames
  counter=0;
  lastdx = 0;
  lastdy = 0;
  while ( fr[0]-1 > counter ){
    counter ++;
    one = cvQueryFrame ( capture );
  }
  last_img = cvCreateImage (cvSize (w, h), IPL_DEPTH_8U, 3);
  tmp1 = cvCloneImage( last_img );
  if ( straighten || angle != 0.0 ){
    cvGetQuadrangleSubPix ( one, tmp1, &M);
  }
  else {
    cvCopy( one, tmp1 );
  }
  if ( vanishx || vanishy ){
    Skew( tmp1, last_img, vanishx, vanishy );
  }
  else{
    cvCopy( tmp1, last_img );
  }
  
  canvas = new TSCanvas( cvCloneImage( last_img ) );
  //canvas->add( last_img, 0,0, 100, verbosity );
  cvShowImage ("Canvas", canvas->getImage() );
  //cvReleaseImage( &one );
  elem = 0;
  frame   = cvCreateImage (cvSize (w, h), IPL_DEPTH_8U, 3);
  masked = cvCloneImage( frame );
}



int
SecondPass::update()
{
  if ( verbosity == 2 ){
    cout << counter << "/" << elem << "/" << fr[elem] << "/" << fr.size() << endl;
  }
  if ( elem == fr.size() )
    return 1;
  IplImage* one = 0;
  //Retrieve a frame
  while ( fr[elem] != counter ){
    counter ++;
    one = cvQueryFrame ( capture );
  }
  if ( straighten || angle != 0.0 ){
    CvMat M;
    cvInitMatHeader (&M, 2, 3, CV_32FC1, mat, CV_AUTOSTEP);
    cvGetQuadrangleSubPix ( one,tmp1, &M);
  }
  else {
    cvCopy( one, tmp1 );
  }
  if ( vanishx || vanishy ){
    Skew( tmp1, frame, vanishx, vanishy );
  }
  else{
    cvCopy( tmp1, frame );
  }
  cvShowImage ("Input", frame);
    
  int x,y;
  //match_recursively( last_img, frame, 2,&x,&y, 1,1);
  x = y = 0;
  cvCopy( frame, masked );
  // Fill background in black.
  float similarity = genMask( masked, last_img, x, y );
  cvShowImage ("Mask", masked);

  int dx = vx[elem] << scale;
  int dy = vy[elem] << scale;
  int ddx = 1;
  int ddy = 1;
  if ( isHoriz ){
    dy = 0;
    ddy = 0;
  }
  else{
    dx = 0;
    ddx = 0;
  }
  
  int ex,ey;
  float score0 = match_rgbimages( last_img, masked, lastdx-ddx, lastdx+ddx, lastdy-ddy,lastdy+ddy, &ex,&ey);
  float score = match_recursively2( last_img, masked, scale, dx, dy, isHoriz );
  
  if ( verbosity == 2 ){
    cout << counter << "\t" << score0 << "\t" << score << "\t";
  }
  if ( score0 > score ){
    dx = ex;
    dy = ey;
    score = score0;
  }    
  
  lastdx = dx;
  lastdy = dy;
  
  if ( verbosity == 1 ){
    cout << dx << "\t" << dy;
    cout << endl;
  }
  else if ( verbosity == 2 ){
    cout << dx << "\t" << dy << "\t" << score << "\t" << similarity << "\t" << vx[elem] << "\t" << vy[elem];
    cout << endl;
  }
  cvCopy( frame, last_img );
  canvas->add( frame, dx,dy, offset, verbosity );
  if ( split ){
    canvas->purge( npurge, basename, frame, split );
  }
  cvShowImage ("Canvas", canvas->getImage() );
  
  char c = cvWaitKey (10);
  if (c == '\x1b')
    return 1;
  elem += 1;
  return 0;
}



SecondPass::~SecondPass()
{
  cvReleaseImage (&frame);
  cvReleaseImage (&tmp1);
  cvReleaseImage (&masked);
  cvReleaseImage (&last_img);
  delete canvas;
}    



float regression0( vector<int>& v, int verbosity, float tolerance, float& a, float& b )
{
  float n = v.size();
  float sx = 0.0;
  float sxx = 0.0;
  float sxy = 0.0;
  float sy = 0.0;
  sx = sxx = sxy = sy = 0;
  n = 0;
  if ( verbosity == 2 ) cout << "x: ";
  for ( int i=0; i<v.size(); i++ ){
    if ( verbosity == 2 ) cout << v[i] << "-" << a*i+b << endl;
    if ( abs(v[i]-(int)(a*i+b)) > tolerance ){
      if ( verbosity == 2 ) cout << i << ", ";
    }
    else{
      sx  += i;
      sxx += i*i;
      sy  += v[i];
      sxy += i*v[i];
      n ++;
    }
  }
  if ( verbosity == 2 ) cout << endl;
  //determine the parameters again, by omitting suspicious data
  a = (n*sxy - sx*sy)/(n*sxx - sx*sx);
  b = (sxx*sy - sxy*sx) / (n*sxx - sx*sx);
  float convergence = 0.0;
  for ( int i=0; i<v.size(); i++ ){
    if ( fabsf(v[i]-(int)(a*i+b)) < tolerance ){
      convergence += fabsf(v[i]-(int)(a*i+b));
    }
  }
  convergence /= n;
  if ( verbosity == 2 ){
    cout << "Regression a=" << a << ", b=" << b << ", convergence=" << convergence << endl;
  }
  return convergence;
}

void regression( vector<int>& v, int verbosity )
{
  float a=0,b=0;
  float convergence = 10.0;
  float tolerance = 4.0;
  float newconv = regression0( v, verbosity, 10000.0, a, b );
  while ( tolerance >= 1.0 || newconv < convergence ){
    convergence = newconv;
    newconv = regression0( v, verbosity, tolerance, a, b );
    tolerance /= 1.5;
  }
  for ( int i=0; i<v.size(); i++ ){
    v[i] = (int)(a*i+b);
  }
}




    
int repairvectors( vector<int>& vx, vector<int>& vy, int verbosity )
{
  int horiz = 1;
  float dx = 0;
  float dy = 0;
  //determine the direction
  for ( int i=0; i< vx.size(); i++ ){
    dx += vx[i];
    dy += vy[i];
  }
  if ( fabsf(dx) < fabsf(dy) ){
    horiz = 0;
  }
  //normalized translation vector
  float r = sqrt(dx*dx+dy*dy);
  dx /= r;
  dy /= r;
  //repair vectors
  for ( int i=0; i < vx.size(); i++ ){
    float x = vx[i];
    float y = vy[i];
    float r = sqrt(x*x+y*y);
    if ( r == 0.0 ){
      vx[i] = (int) dx;
      vx[i] = (int) dy;
    }
    else{
      x /= r;
      y /= r;
      if ( x*dx + y*dy < 0.8 ){
        vx[i] = (int) dx;
        vy[i] = (int) dy;
      }
    }
  }

  //regression
  if ( horiz ){
    regression( vx, verbosity );
  }
  else {
    regression( vy, verbosity );
  }
  
  return horiz;
}
      

  
  




TrainScanner::TrainScanner( int dx_,
			    int dy_,
			    int split_,
			    int straighten_,
			    int offset_,
			    float angle_,
			    int vanishx_,
			    int vanishy_,
			    int verbosity_,
			    const char* movie_ ): dx(dx_),
						  dy(dy_),
						  split(split_),
						  straighten(straighten_),
						  offset(offset_),
						  angle(angle_),
						  vanishx(vanishx_),
						  vanishy(vanishy_),
						  verbosity(verbosity_)
{
  stage = 0;
  movie = strdup( movie_ );
}



TrainScanner::~TrainScanner()
{
  if ( firstpass ){
    delete firstpass;
  }
  if ( secondpass ){
    delete secondpass;
  }
  free(movie);
}



int
TrainScanner::update()
{
  if ( stage == 0 ){
    if ( verbosity == 2 ) cout << "Stage 0" << endl;
    firstpass = new FirstPass( movie, dx, dy, vx, vy, fr, offset, vanishx, vanishy, verbosity, angle );
    stage = 1;
  }
  else if ( stage == 1 ){
    if ( verbosity == 2 ) cout << "Stage 1" << endl;
    int finished = firstpass->update();
    if ( finished ){
      stage = 2;
      scale = firstpass->scale;
      delete firstpass;
      firstpass = 0;
    }
  }
  else if ( stage == 2 ){
    if ( verbosity == 2 ) cout << "Stage 2" << endl;
    horiz = repairvectors( vx, vy, verbosity );
    stage = 3;
  }
  else if ( stage == 3 ){
    if ( verbosity == 2 ) cout << "Stage 3" << endl;
    secondpass = new SecondPass( movie, vx,vy,fr, scale, horiz, offset, split, straighten, vanishx, vanishy, verbosity, angle );
    stage = 4;
  }
  else if ( stage == 4 ){
    if ( verbosity == 2 ) cout << "Stage 4" << endl;
    int finished = secondpass->update();
    if ( finished ){
      char filename[1000];
      sprintf(filename, "%s.tif", movie );
      cvSaveImage( filename, secondpass->canvas->getImage() );
      delete secondpass;
      secondpass = 0;
      return 1; // finish
    }
  }
  return 0; // continue
}

