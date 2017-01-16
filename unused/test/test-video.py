import sys
import gi
gi.require_version('Gst', '1.0')
#gi.require_version('Gtk', '3.0')
#gi.require_version('GdkX11', '3.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import GObject, Gst, Gtk, GdkX11, GstVideo, Gdk

GObject.threads_init()
Gst.init(None)

testGrab = "testRAW.mkv"

class VideoDec(Gst.Bin):
    def __init__(self):
        super().__init__()

        # elements
        q1 = Gst.ElementFactory.make('queue', None)
        videoparse = Gst.ElementFactory.make('videoparse', None)
        q2 = Gst.ElementFactory.make('queue', None)

        self.add(q1)
        self.add(videoparse)
        self.add(q2)

        videoparse.set_property('width', 720)
        videoparse.set_property('height', 576)
        videoparse.set_property('format', 4)

        # link
        q1.link(videoparse)
        videoparse.link(q2)

        # Add Ghost Pads
        self.add_pad(
            Gst.GhostPad.new('sink', q1.get_static_pad('sink'))
        )
        self.add_pad(
            Gst.GhostPad.new('src', q2.get_static_pad('src'))
        )

class AudioDec(Gst.Bin):
    def __init__(self):
        super().__init__()

        # elements
        q1 = Gst.ElementFactory.make('queue', None)
        audioparse = Gst.ElementFactory.make('audioparse', None)
        q2 = Gst.ElementFactory.make('queue', None)
        #sink = Gst.ElementFactory.make('autoaudiosink', None)

        self.add(q1)
        self.add(audioparse)
        self.add(q2)
        #self.add(sink)

        # link
        q1.link(audioparse)
        audioparse.link(q2)
        #audioparse.link(sink)

        # Add Ghost Pads
        self.add_pad(
            Gst.GhostPad.new('sink', q1.get_static_pad('sink'))
        )
        self.add_pad(
            Gst.GhostPad.new('src', q2.get_static_pad('src'))
        )

class Player(object):
    def __init__(self):
        self.fps = 25
        self.window = Gtk.Window()
        self.window.connect('destroy', self.quit)
        self.window.set_default_size(800, 600)

        self.drawingarea = Gtk.DrawingArea()

        #hbox
        self.hbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.window.add(self.hbox)
        Gtk.Box.pack_start(self.hbox, self.drawingarea, True, True, 0)

        self.setPipeline()

        self.setGUI()
        self.setShortcuts()

        self.playing = False

    def setPipeline(self):
        self.pipe = Gst.Pipeline.new('player')

        # Create bus to get events from GStreamer pipeline
        self.bus = self.pipe.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::eos', self.on_eos)
        self.bus.connect('message::error', self.on_error)

        # This is needed to make the video output in our DrawingArea:
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self.on_sync_message)

        self.src = Gst.ElementFactory.make('filesrc', None)
        self.src.set_property("location", testGrab)
        self.dec = Gst.ElementFactory.make('decodebin', None)
        self.video = VideoDec()
        self.audio = AudioDec()
        self.glimagesink = Gst.ElementFactory.make('glimagesink', None)
        self.audiosink = Gst.ElementFactory.make('autoaudiosink', None)

        self.pipe.add(self.src)
        self.pipe.add(self.dec)
        self.pipe.add(self.video)
        self.pipe.add(self.audio)
        self.pipe.add(self.glimagesink)
        self.pipe.add(self.audiosink)
        #self.pipe.add(self.autovideosink)

        # Connect signal handlers
        self.dec.connect('pad-added', self.on_pad_added)

        # link
        self.src.link(self.dec)
        self.video.link(self.glimagesink)
        self.audio.link(self.audiosink)

    def on_pad_added(self, element, pad):
        string = pad.query_caps(None).to_string()
        print('on_pad_added():', string)
        if string.startswith('audio/'):
            pad.link(self.audio.get_static_pad('sink'))
        elif string.startswith('video/'):
            pad.link(self.video.get_static_pad('sink'))

    def setGUI(self):
        vbox = Gtk.Box(Gtk.Orientation.HORIZONTAL, 0)
        vbox.set_margin_top(3)
        vbox.set_margin_bottom(3)
        Gtk.Box.pack_start(self.hbox, vbox, False, False, 0)

        self.playButtonImage = Gtk.Image()
        self.playButtonImage.set_from_stock("gtk-media-play", Gtk.IconSize.BUTTON)
        self.playButton = Gtk.Button.new()
        self.playButton.add(self.playButtonImage)
        self.playButton.connect("clicked", self.playToggled)
        Gtk.Box.pack_start(vbox, self.playButton, False, False, 0)

        self.slider = Gtk.HScale()
        self.slider.set_margin_left(6)
        self.slider.set_margin_right(6)
        self.slider.set_draw_value(False)
        self.slider.set_range(0, 100)
        self.slider.set_increments(1, 10)

        Gtk.Box.pack_start(vbox, self.slider, True, True, 0)


        self.label = Gtk.Label(label='0:00')
        self.label.set_margin_left(6)
        self.label.set_margin_right(6)
        Gtk.Box.pack_start(vbox, self.label, False, False, 0)

    def setShortcuts(self):
        accel = Gtk.AccelGroup()
        accel.connect(Gdk.KEY_space, Gdk.ModifierType.CONTROL_MASK, 0, self.playToggled)
        accel.connect(Gdk.KEY_Right, Gdk.ModifierType.CONTROL_MASK, 0, self.seekFW0)
        accel.connect(Gdk.KEY_Right, Gdk.ModifierType.CONTROL_MASK|Gdk.ModifierType.SHIFT_MASK, 0, self.seekFW10s)
        accel.connect(Gdk.KEY_Right, Gdk.ModifierType.SHIFT_MASK, 0, self.seekFW2)
        accel.connect(Gdk.KEY_Right, Gdk.ModifierType.MOD1_MASK, 0, self.seekFW10) # alt key
        self.window.add_accel_group(accel)

    def seekFW0(self, *args):
        self.seekTime = 2 * Gst.SECOND // self.fps
        self.seekFW()

    def seekFW10s(self, *args):
        self.seekTime = Gst.SECOND * 10
        self.seekFW()

    def seekFW2(self, *args):
        self.seekTime = Gst.SECOND * 60 * 2
        self.seekFW()

    def seekFW10(self, *args):
        self.seekTime = Gst.SECOND * 60 * 10
        self.seekFW()

    def seekFW(self, *args):
        nanosecs = self.pipe.query_position(Gst.Format.TIME)[1]
        destSeek = nanosecs + self.seekTime
        self.pipe.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            destSeek
        )

    def play(self):
        self.pipe.set_state(Gst.State.PLAYING)
        GObject.timeout_add(1000, self.updateSlider)


    def stop(self):
        self.pipe.set_state(Gst.State.PAUSED)


    def playToggled(self, *w):

        if(self.playing == False):
            self.play()
        else:
            self.stop()


        self.playing=not(self.playing)
        self.updateButtons()

    def updateSlider(self):
        try:
            nanosecs = self.pipe.query_position(Gst.Format.TIME)[1]
            duration_nanosecs = self.pipe.query_duration(Gst.Format.TIME)[1]


            # block seek handler so we don't seek when we set_value()
            # self.slider.handler_block_by_func(self.on_slider_change)


            duration = float(duration_nanosecs) / Gst.SECOND
            position = float(nanosecs) / Gst.SECOND
            self.slider.set_range(0, duration)
            self.slider.set_value(position)
            self.label.set_text ("%d" % (position / 60) + ":%02d" % (position % 60))


            #self.slider.handler_unblock_by_func(self.on_slider_change)


        except Exception as e:
            # pipeline must not be ready and does not know position
            print(e)
            pass


        return True

    def updateButtons(self):
        if(self.playing == False):
            self.playButtonImage.set_from_stock("gtk-media-play", Gtk.IconSize.BUTTON)
        else:
            self.playButtonImage.set_from_stock("gtk-media-pause", Gtk.IconSize.BUTTON)

    def run(self):
        self.window.show_all()
        # You need to get the XID after window.show_all().  You shouldn't get it
        # in the on_sync_message() handler because threading issues will cause
        # segfaults there.
        self.xid = self.drawingarea.get_property('window').get_xid()
        #self.pipeline.set_state(Gst.State.PLAYING)
        Gtk.main()

    def quit(self, window):
        self.pipe.set_state(Gst.State.NULL)
        Gtk.main_quit()

    def on_sync_message(self, bus, msg):
        if msg.get_structure().get_name() == 'prepare-window-handle':
            print('prepare-window-handle')
            msg.src.set_window_handle(self.xid)

    def on_eos(self, bus, msg):
        #print('on_eos(): seeking to start of video')
        print('on_eos(): pausing video')
        self.stop()
        #self.pipeline.seek_simple(
        #    Gst.Format.TIME,        
        #    Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
        #    0
        #)
        #self.playing = False
        #self.slider.set_value(0)
        #self.label.set_text("0:00")
        #self.updateButtons()

    def on_error(self, bus, msg):
        print('on_error():', msg.parse_error())


p = Player()
p.run()
