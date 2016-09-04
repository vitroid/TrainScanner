UNAME := $(shell uname)
ifeq "Darwin" "$(UNAME)"
LDFLAGS=-L/usr/local/Cellar/opencv3/3.1.0_3/lib -lopencv_core -lopencv_highgui -lopencv_imgproc -lopencv_calib3d -lopencv_features2d -lopencv_imgproc 
endif
ifeq "Linux" "$(UNAME)"
LDFLAGS=-lcv -lhighgui
endif
CXX=g++
CXXFLAGS=-g -I/usr/local/Cellar/opencv3/3.1.0_3/include
TARGETS=trainscanner append
all: $(TARGETS)
app:
	cd TrainScannerX && xcodebuild
install: $(TARGETS)
	install -m 0755 $(TARGETS) /usr/local/bin
samples: sample.mov.tif sample.mov_append.tif
samples: sample2.mov.tif 
samples: sample3.mov.tif sample3.mov_append.tif
sample.mov.tif: sample.mov trainscanner
	./trainscanner -s 1280 sample.mov
sample2.mov.tif: sample2.mov trainscanner
	./trainscanner -S -o 30 -d0,-86 sample2.mov
sample3.mov.tif: sample3.mov trainscanner
	./trainscanner -v -s 2000 -o 45 sample3.mov
sample.mov_append.tif: sample.mov.tif append
	./append -d 3 $<
sample3.mov_append.tif: sample3.mov.tif append
	./append -d 3 $<
trainscanner.o: tscanvas.hpp
trainscanner: trainscanner.o tscanvas.o tsmain.o
	$(CXX) $(CXXFLAGS) $^ -o $@ $(LDFLAGS)
append.o: tscanvas.hpp
append: append.o tscanvas.o
	$(CXX) $(CXXFLAGS) $^ -o $@ $(LDFLAGS)
test_surf_mov: test_surf_mov.o
	$(CXX) $(CXXFLAGS) $^ -o $@ $(LDFLAGS)
test_surf_interframe: test_surf_interframe.o
	$(CXX) $(CXXFLAGS) $^ -o $@ $(LDFLAGS)
package: trainscanner.cpp map.cpp map.hpp gut.cpp spiral.cpp README Makefile append.cpp tsmain.cpp trainscanner.hpp tscanvas.hpp tscanvas.cpp
	pwd=`pwd`; \
	bn=`basename $$pwd`; \
	tar zcvf trainscanner-$$bn.tgz $^
binpackage: trainscanner README Makefile sample.mov
	tar zcvf trainscanner-bin.tgz $^
clean:
	-rm $(TARGETS) *.o *~
memo:
	#svn copy https://trainscanner.svn.sourceforge.net/svnroot/trainscanner https://trainscanner.svn.sourceforge.net/svnroot/trainscanner/beta0.01 -m "Tagging the Beta 0.01 release of the trainscanner project."

