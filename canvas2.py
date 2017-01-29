import cachedcanvas as cc
#Automatically extensible canvas.
class Canvas(cc.CachedCanvas):
    def __init__(self, dir="canvas.pngs", tilesize=512, cachesize=100, image=None, position=None, clean=True):
        super(Canvas, self).__init__(dir=dir, tilesize=tilesize, cachesize=cachesize, clean=clean)
        if image is not None:
            self.put_image(position, image)

    def abs_merge(self, image, x, y, alpha=None ):
        self.put_image((x,y), image, linear_alpha=alpha)
