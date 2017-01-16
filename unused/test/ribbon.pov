// -*- povray -*-

#include "colors.inc"


#declare folds = array[13] {0,2587/30000,4994/30000,7439/30000,9799/30000,12261/30000,14727/30000,17217/30000,19708/30000,22221/30000,24744/30000,27294/30000,30000/30000};
#declare w    = 30000;
#declare h    = 598;
#declare image = "/Users/matto/Shared/ArtsAndIllustrations/Stitch tmp2/Kanazawa/test.png";
#declare R = w/12/sqrt(2);
#declare ang = 3.5;

camera {
    spherical
    angle 360
      right x*image_width/image_height
}

#declare spins = 0;
#declare i = 0;
#while(i<12)
#declare fold = folds[i];
#declare xfold = fold * w;
#declare center = (folds[i] + folds[i+1]) / 2;
#declare xcenter = center * w;
#declare section = folds[i+1] - folds[i];
#declare wsection = section * w * cos(ang*pi/180);
#declare halfsec  = wsection / 2;
#declare zcenter = (center-0.5) * w * sin(ang*pi/180);
#declare rsection = sqrt(R*R - halfsec*halfsec);
#declare spin = 2*atan2(halfsec,rsection)*180/pi;

box {
    <-w/2,-h/2,0>, <w/2,h/2,0.01>
//    finish {
        pigment {
            image_map {
                png image
                map_type 0
            }
            translate <-0.5,-0.5,0>
            scale <w,h,1>
        }
        finish {ambient 1 diffuse 0}
//    }
    translate <w/2-xcenter,zcenter,rsection>
    rotate <0,0,1>*ang
      rotate <0,1,0>*(spins + spin*0.5)
}

#declare spins  = spins + spin;
#declare i = i + 1;
#end


    
