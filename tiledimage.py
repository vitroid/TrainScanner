import cv2
import numpy as np
import logging

#a range is always spacified with the min and max=min+width
#2d region consists of two ranges.

def overlap(r1, r2):
    """
    True if the give regions (1D) overlap

    there are 6 possible orders
    ( ) [ ] x
    ( [ ) ] o 
    ( [ ] ) o
    [ ( ) ] o
    [ ( ] ) o
    [ ] ( ) x
    ! { ) [ | ] ( }
    ie [ ) && ( ]
    """
    if r1[0] < r2[1] and r2[0] < r1[1]:
        return max(r1[0],r2[0]), min(r1[1], r2[1])
    return None


#It should also return the overlapping region
def overlap2D(r1, r2):
    x = overlap(r1[0], r2[0])
    if x is not None:
        y = overlap(r1[1], r2[1])
        if y is not None:
            return x,y
    return None


class TiledImage():
    """
    it has no size.
    size is determined by the tiles.
    !!!   it is better to fix the tile size. (128x128, for example)
    """
    def __init__(self, tilesize=128, bgcolor=(100,100,100)):
        self.tiles = dict()
        if type(tilesize) is int:
            self.tilesize = (tilesize, tilesize)
        else:
            assert type(tilesize) is tuple
            self.tilesize = tilesize
        self.region = None
        self.bgcolor = np.array(bgcolor)
        
    def tiles_containing(self, region, includeempty=False):
        """
        return the tiles containing the given region
        """
        logger = logging.getLogger()
        t = []
        xran, yran = region
        xran = xran[0]//self.tilesize[0], (xran[1]+self.tilesize[0]-1)//self.tilesize[0]
        yran = yran[0]//self.tilesize[1], (yran[1]+self.tilesize[1]-1)//self.tilesize[1]
        for ix in range(xran[0],xran[1]):
            for iy in range(yran[0],yran[1]):
                tile = (ix*self.tilesize[0], iy*self.tilesize[1])
                logger.debug("Tile: {0}".format(tile))
                if (tile in self.tiles) or includeempty:
                    tregion = ((tile[0], tile[0]+self.tilesize[0]), (tile[1], tile[1]+self.tilesize[1]))
                    o = overlap2D(tregion, region)
                    t.append((tile, o))
        return t

    def get_region(self, region):
        logger = logging.getLogger()
        #logger.debug("Get region {0} {1}".format(region,self.tiles))
        xrange, yrange = region
        image = np.zeros((yrange[1]-yrange[0], xrange[1] - xrange[0], 3), dtype=np.uint8)
        image[:,:] = self.bgcolor
        for tile, overlap in self.tiles_containing(region):
            #logger.debug("Should get a tile at {0} {1}".format(tile,self.tiles))
            src = self.tiles[tile]
            originx, originy = tile
            xr, yr = overlap
            image[yr[0]-yrange[0]:yr[1]-yrange[0], xr[0]-xrange[0]:xr[1]-xrange[0], :] = src[yr[0]-originy:yr[1]-originy, xr[0]-originx:xr[1]-originx, :]
        return image

    def put_image(self, position, image, linear_alpha=None):
        """
        split the existent tiles
        and put a big single tile.
        the image must be larger than a single tile.
        otherwise, a different algorithm is required.
        """
        h,w = image.shape[:2]
        xrange, yrange = (position[0], position[0]+w), (position[1], position[1]+h)
        region = (xrange,yrange)
        for tile, overlap in self.tiles_containing(region, includeempty=True):
            if tile not in self.tiles:
                self.tiles[tile] = np.zeros((self.tilesize[1], self.tilesize[0], 3), dtype=np.uint8)
                self.tiles[tile][:,:] = self.bgcolor
            src = self.tiles[tile]
            originx, originy = tile
            xr, yr = overlap
            if linear_alpha is None:
                src[yr[0]-originy:yr[1]-originy, xr[0]-originx:xr[1]-originx, :] = image[yr[0]-yrange[0]:yr[1]-yrange[0], xr[0]-xrange[0]:xr[1]-xrange[0], :]
            else:
                src[yr[0]-originy:yr[1]-originy, xr[0]-originx:xr[1]-originx, :] = linear_alpha[xr[0]-xrange[0]:xr[1]-xrange[0], :]*image[yr[0]-yrange[0]:yr[1]-yrange[0], xr[0]-xrange[0]:xr[1]-xrange[0], :] + (1-linear_alpha[xr[0]-xrange[0]:xr[1]-xrange[0], :])*src[yr[0]-originy:yr[1]-originy, xr[0]-originx:xr[1]-originx, :]
                
            #rewrite the item explicitly (for caching)
            self.tiles[tile] = src
        if self.region is None:
            self.region = ((position[0], position[0]+w), (position[1], position[1]+h))
        else:
            self.region = ((min(self.region[0][0], position[0]),
                           max(self.region[0][1], position[0]+w)),
                          (min(self.region[1][0], position[1]),
                           max(self.region[1][1], position[1]+h)))

    def get_image(self):
        return self.get_region(self.region)

def test():
    image = TiledImage(tilesize=(8,24))
    img = cv2.imread("sample.png")
    image.put_image((-10,-10), img)
    image.put_image((100,120), img)
    c = image.get_image()
    cv2.imshow("image",c)
    cv2.waitKey(0)

if __name__ == "__main__":
    test()
