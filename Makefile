UNAME := $(shell uname)
ifeq "Darwin" "$(UNAME)"
LDFLAGS=-L/usr/local/Cellar/opencv/2.2/lib -lopencv_core -lopencv_highgui -lopencv_imgproc -lopencv_calib3d -lopencv_contrib -lopencv_features2d -lopencv_imgproc 
endif
ifeq "Linux" "$(UNAME)"
LDFLAGS=-lcv -lhighgui
endif
CXX=g++ -O6
TARGETS=trainscanner append
all: $(TARGETS)
app:
	cd TrainScannerX && xcodebuild
install: $(TARGETS)
	install -m 0755 $(TARGETS) /usr/local/bin
samples: sample.mov.tif  sample.mov.tif_gut.jpg sample.mov.tif_spiral.jpg
samples: sample2.mov.tif 
samples: sample3.mov.tif sample3.mov_append.tif
sample.mov.tif: sample.mov trainscanner
	./trainscanner sample.mov
sample2.mov.tif: sample2.mov trainscanner
	./trainscanner -S -o 30 -d0,-86 sample2.mov
sample3.mov.tif: sample3.mov trainscanner
	./trainscanner -v -s 2000 -o 45 -M mask.png sample3.mov
%_gut.jpg: % gut
	./gut --size=1000 --height=0.59 $<
%_spiral.jpg: % spiral
	./spiral --size=1000 $<
sample3.mov_append.tif: sample3.mov.tif append
	./append -d 3 $<
trainscanner.o: tscanvas.hpp
trainscanner: trainscanner.o tscanvas.o tsmain.o
	$(CXX) $(CXXFLAGS) $^ -o $@ $(LDFLAGS)
append.o: tscanvas.hpp
append: append.o tscanvas.o
	$(CXX) $(CXXFLAGS) $^ -o $@ $(LDFLAGS)
package: trainscanner.cpp map.cpp map.hpp gut.cpp spiral.cpp README Makefile append.cpp tsmain.cpp trainscanner.hpp tscanvas.hpp tscanvas.cpp
	pwd=`pwd`; \
	bn=`basename $$pwd`; \
	tar zcvf trainscanner-$$bn.tgz $^
binpackage: trainscanner gut spiral README Makefile sample.mov
	tar zcvf trainscanner-bin.tgz $^
clean:
	-rm $(TARGETS) *.o *~
memo:
	#svn copy https://trainscanner.svn.sourceforge.net/svnroot/trainscanner https://trainscanner.svn.sourceforge.net/svnroot/trainscanner/beta0.01 -m "Tagging the Beta 0.01 release of the trainscanner project."

