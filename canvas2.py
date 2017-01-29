import cachedimage as ci
#Automatically extensible canvas.
class Canvas(ci.CachedImage):
    def __init__(self, dir="canvas.pngs", tilesize=512, cachesize=100, image=None, position=None):
        super(Canvas, self).__init__("new", dir=dir, tilesize=tilesize, cachesize=cachesize)
        if image is not None:
            self.put_image(position, image)

    def abs_merge(self, image, x, y, alpha=None ):
        self.put_image((x,y), image, linear_alpha=alpha)
