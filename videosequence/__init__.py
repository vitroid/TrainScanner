from __future__ import division
from builtins import range

import collections
import contextlib
import logging
import os

import gi
import PIL.Image as Image

gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
from gi.repository import Gst, GstApp

# Initialise GStreamer
Gst.init()

LOG = logging.getLogger()
STATE_CHANGE_TIMEOUT = 1 * Gst.SECOND

class VideoError(IOError):
    pass

class VideoSequence(collections.Sequence):
    """
    A sequence of video frames.

    """
    def __init__(self, path):
        abs_uri = "file://" + os.path.abspath(path)
        LOG.info("Opening file at %s", abs_uri)

        pipeline = Gst.ElementFactory.make("playbin", "playbin")
        self.pipeline = pipeline
        pipeline.set_property("uri", abs_uri)
        pipeline.set_property(
            "audio-sink", Gst.ElementFactory.make("fakesink", "fakeaudio"))

        videocaps = Gst.Caps.new_empty_simple("video/x-raw")
        videocaps.set_value("format", "RGB")
        appsink = GstApp.AppSink()
        self.appsink = appsink
        appsink.set_property("caps", videocaps)
        pipeline.set_property("video-sink", appsink)

        state = self._timeout_set_state(Gst.State.PAUSED)

        sample = appsink.pull_preroll()
        if sample is None:
            raise VideoError("No data in video")

        self.caps = sample.get_caps()
        ok, num, denom = self.caps.get_structure(0).get_fraction("framerate")
        if not ok:
            raise VideoError("Could not determine frame rate for seeking")
        self.ns_per_frame = (denom * Gst.SECOND) / num

        self.width = self.caps.get_structure(0).get_value("width")
        self.height = self.caps.get_structure(0).get_value("height")

        ok, duration = pipeline.query_duration(Gst.Format.TIME)
        if not ok:
            raise VideoError("Could not determine duration of video")

        self.duration = int(duration / self.ns_per_frame)

        self.current_index = None
        self._seek(0)

    def close(self):
        self.pipeline.set_state(Gst.State.NULL)

    def _wait_async_done(self):
        while True:
            msg = self.pipeline.bus.timed_pop(STATE_CHANGE_TIMEOUT)
            if msg is None:
                raise VideoError("Timed out waiting for ASYNC_DONE message")
            elif msg.type == Gst.MessageType.ASYNC_DONE:
                return
            elif msg.type == Gst.MessageType.ERROR:
                error, debug = msg.parse_error()
                if debug is not None:
                    LOG.debug(debug)
                raise VideoError(error.message)

    def _timeout_set_state(self, state):
        ret = self.pipeline.set_state(state)
        if ret == Gst.StateChangeReturn.ASYNC:
            self._wait_async_done()
        if ret == Gst.StateChangeReturn.FAILURE:
            raise VideoError("Failed to open video")
        elif ret == Gst.StateChangeReturn.NO_PREROLL:
            raise VideoError("Live sources not supported")

    def _seek(self, index):
        assert index >= 0 and index < self.duration
        ts = index * self.ns_per_frame
        flags = Gst.SeekFlags.ACCURATE | Gst.SeekFlags.FLUSH
        ok = self.pipeline.seek(1.0, Gst.Format.TIME, flags,
                                Gst.SeekType.SET, ts,
                                Gst.SeekType.NONE, 0)
        if not ok:
            raise VideoError("Seek event not handled")

        self._wait_async_done()

        self.current_index = index

    def _step(self, frame_count):
        assert frame_count > 0

        step_amount = frame_count * self.ns_per_frame
        event = Gst.Event.new_step(Gst.Format.BUFFERS, frame_count, 1.0,
                                   True, False)
        ok = self.pipeline.send_event(event)
        if not ok:
            raise VideoError("Step event not handled")

        self._wait_async_done()

        self.current_index += frame_count

    def _get_frame(self, index):
        cur_idx = self.current_index
        max_delta = 1

        if index < cur_idx:
            self._seek(index)
        elif index > cur_idx:
            delta = index - cur_idx
            if delta > max_delta:
                self._seek(index)
            else:
                self._step(delta)

        assert self.current_index == index

        sample = self.appsink.pull_preroll()
        if sample is None:
            LOG.warn("Returning empty frame since no preroll available")
            return Image.new("RGB", (self.width, self.height))
        return _sample_to_image(sample)

    def _get_slice(self, slc):
        for idx in range(*slc.indices(self.duration)):
            yield self._get_frame(idx)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self._get_slice(key)
        key = int(key)
        if key < 0:
            key += self.duration
        if key < 0 or key >= self.duration:
            raise IndexError("Invalid frame index: {}".format(key))
        return self._get_frame(key)

    def __len__(self):
        return self.duration

def _sample_to_image(sample):
    caps = sample.get_caps()
    format_ = caps.get_structure(0).get_string("format")
    if format_ != "RGB":
        raise ValueError("Need RGB frame sample to convert to image")

    buf = sample.get_buffer()
    data = buf.extract_dup(0, buf.get_size())
    w = caps.get_structure(0).get_value("width")
    h = caps.get_structure(0).get_value("height")
    return Image.frombytes("RGB", (w, h), data)
