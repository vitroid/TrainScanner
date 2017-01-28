import cachedcanvas as cc
#Automatically extensible canvas.
class Canvas(cc.CachedCanvas):
    def __init__(self, image=None, position=None):
        super(Canvas, self).__init__(tilesize=512, cachesize=100)
        if image is not None:
            self.put_image(position, image)

    def abs_merge(self, image, x, y, alpha=None ):
        self.put_image((x,y), image, linear_alpha=alpha)
