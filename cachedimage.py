import tilecache
import tiledimage
import logging
import cv2
import numpy as np

class CachedImage(tiledimage.TiledImage):
    def __init__(self, mode, dir="image.pngs", tilesize=128, cachesize=10, fileext="png", bgcolor=(0,0,0), hook=None):
        """
        if mode == "new", flush the dir.
        hook is a function like put_image, that is called then a tile is rewritten.
        """
        logger = logging.getLogger()
        super(CachedImage, self).__init__(tilesize)
        self.fileext = fileext
        self.bgcolor = bgcolor
        if mode == "inherit":
            #read the info.txt in the dir.
            self.region = [None, None]
            with open(dir + "/info.txt", "r") as file:
                self.region[0] = [int(x) for x in file.readline().split()[:2]]
                self.region[1] = [int(x) for x in file.readline().split()[:2]]
                self.tilesize  = [int(x) for x in file.readline().split()[:2]]
                self.bgcolor   = [int(x) for x in file.readline().split()[:3]]
                self.fileext   = file.readline().split()[0]
        defaulttile = np.zeros((self.tilesize[1],self.tilesize[0],3), dtype=np.uint8)
        self.bgcolor = np.array(self.bgcolor)
        #logger.info("Color: {0}".format(self.bgcolor))
        defaulttile[:,:,:] = self.bgcolor[:3]
        #logger.info("Tile: {0}".format(defaulttile))
        self.tiles = tilecache.TileCache(mode, dir=dir,
                                             cachesize=cachesize,
                                             fileext=self.fileext,
                                             default=defaulttile,
                                             hook = hook)
        #just for done()
        self.dir   = dir   
        
    def done(self):
        """
        Call it explicitly.
        """
        with open(self.dir + "/info.txt", "w") as file:
            file.write("{0} {1} xrange\n".format(*self.region[0]))
            file.write("{0} {1} yrange\n".format(*self.region[1]))
            file.write("{0} {1} tilesize\n".format(*self.tilesize))
            file.write("{0} {1} {2} background\n".format(*self.bgcolor))   #0..255, black
            file.write("{0} filetype\n".format(self.fileext))       #image type by file extension
        self.tiles.done()

    def put_image(self, pos, img, linear_alpha=None):
        super(CachedImage, self).put_image(pos, img, linear_alpha)
        logger = logging.getLogger()
        nmiss, naccess, cachesize = self.tiles.cachemiss()
        logger.info("Cache miss {0}% @ {1} tiles".format(nmiss*100//naccess, cachesize))
        self.tiles.adjust_cache_size()
        
    def set_hook(self, hook):
        self.tiles.set_hook(hook)
        
        
def test():
    debug = True
    if debug:
        logging.basicConfig(level=logging.DEBUG,
                            #filename='log.txt',
                            format="%(asctime)s %(levelname)s %(message)s")
    else:
        logging.basicConfig(level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(message)s")
    image = CachedImage("new", tilesize=(64,64), cachesize=10, bgcolor=(100,200,0), fileext="jpg")
    img = cv2.imread("sample.png")
    image.put_image((-10,-10), img)
    image.put_image((100,120), img)
    logger = logging.getLogger()
    logger.debug("start showing.")
    c = image.get_image()
    cv2.imshow("image",c)
    cv2.waitKey(0)
    image.done()
    image = CachedImage("inherit", cachesize=100)
    c = image.get_image()
    cv2.imshow("image",c)
    cv2.waitKey(0)
    image.done()

if __name__ == "__main__":
    test()
