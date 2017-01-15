#Automatically extensible canvas.
class Canvas():

    def __init__(self, image=None, position=None):
        self.image  = image
        self.origin = position
        self.first = True


    def abs_merge(self, add_image, x, y, alpha=None ):
        if self.image is None:
            self.image  = add_image.copy()
            self.origin = x, y
            return
        if self.first:
            self.first = False
        absx, absy = self.origin   #absolute coordinate of the top left of the canvas
        cxmin = absx
        cymin = absy
        cxmax = self.image.shape[1] + absx
        cymax = self.image.shape[0] + absy
        ixmin = x
        iymin = y
        ixmax = add_image.shape[1] + x
        iymax = add_image.shape[0] + y

        xmin = min(cxmin,ixmin)
        xmax = max(cxmax,ixmax)
        ymin = min(cymin,iymin)
        ymax = max(cymax,iymax)
        if (xmax-xmin, ymax-ymin) != (self.image.shape[1], self.image.shape[0]):
            newcanvas = np.zeros((ymax-ymin, xmax-xmin,3), np.uint8)
            newcanvas[cymin-ymin:cymax-ymin, cxmin-xmin:cxmax-xmin, :] = self.image[:,:,:]
        else:
            newcanvas = self.image
        if alpha is None:
            newcanvas[iymin-ymin:iymax-ymin,ixmin-xmin:ixmax-xmin,:] = add_image[:,:,:]
        else:
            newcanvas[iymin-ymin:iymax-ymin,ixmin-xmin:ixmax-xmin,:] = add_image[:,:,:]*alpha[:,:] + newcanvas[iymin-ymin:iymax-ymin,ixmin-xmin:ixmax-xmin,:]*(1-alpha[:,:])
        self.image  = newcanvas
        self.origin = (xmin,ymin)
        

    def save(self, filename):
        cv2.imwrite(filename, self.image)
