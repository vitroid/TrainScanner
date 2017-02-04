import cv2
import pylru #"Least Recent Used" type cache
import os
import logging
import shutil

def remove_folder(path):
    # check if folder exists
    if os.path.exists(path):
        # remove if exists
        shutil.rmtree(path)
    
class TileCache():
    """
    A tile of images that are mostly stored in files
    It does not care the integrity of the image.
    """
    def __init__(self, mode, dir="tileimage", cachesize=10, default=None, fileext="png", hook=None):
        """
        Hook is a function like put_image, that is called when a tile is rewritten
        """
        if mode == "new":
            remove_folder(dir)
            os.mkdir(dir)
        self.dir = dir
        self.cache = pylru.lrucache(cachesize, callback=self.writeback)
        self.nget = 0
        self.nmiss = 0
        self.fileext = fileext
        self.default = default
        self.hook = hook

    def set_hook(self, hook):
        self.hook = hook
        
    def key_to_filename(self, key):
        return "{0}/{1},{2}.{3}".format(self.dir, *key, self.fileext)
    
    def __getitem__(self, key):
        logger = logging.getLogger()
        logger.debug("getitem key:{0}".format(key))
        self.nget += 1
        try:
            modified, value = self.cache[key]
        except KeyError:
            filename = self.key_to_filename(key)
            if os.path.exists(filename):
                value = cv2.imread(filename)
                self.nmiss += 1
                #logger.info("cache miss key:{0}".format(key))
            else:
                #first access is not a "miss"
                logger.info("blank key:{0}".format(key))
                value = self.default
            self.cache[key] = [False, value]
        return value

    def __setitem__(self, key, value):
        logger = logging.getLogger()
        logger.debug("update key:{0}".format(key))
        self.cache[key] = [True, value]
            
    def writeback(self, key, value):
        """
        write back when it is purged from cache
        """
        logger = logging.getLogger()
        if value[0]:
            #logger.info("purge key:{0}".format(key))
            filename = self.key_to_filename(key)
            cv2.imwrite(filename, value[1])
            if self.hook is not None:
                self.hook(key, value[1])
        
    def __contains__(self, key):
        #logger = logging.getLogger()
        #logger.debug("Query: {0}".format(key))
        if key in self.cache:
            #logger.debug("On cache: {0}".format(key))
            return True
        filename = self.key_to_filename(key)
        #logger.debug("On file: {0}".format(filename))
        return os.path.exists(filename)
        
    def done(self):
        #purge the cached images to disk
        for k in self.cache:
            self.writeback(k, self.cache.peek(k))  #peek do not affect the order

    def cachemiss(self):
        """
        report cache miss ratio
        """
        return self.nmiss, self.nget, self.cache.size()

    def adjust_cache_size(self):
        """
        Automatically optimize the cache size
        Should not be adjusted in the final merging process
        """
        percent = self.nmiss*100//self.nget
        if percent > 50:
            self.cache.addTailNode(10)
        elif percent > 20:
            self.cache.addTailNode(1)
