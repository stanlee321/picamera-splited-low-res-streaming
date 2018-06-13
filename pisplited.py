import picamera.array
from picamera import PiCamera
from picamera.exc import PiCameraValueError
import time
import cv2
import numpy as np

import os
import multiprocessing
import collections
import datetime
import time

from threading import Thread
class PiRGBAArray(picamera.array.PiRGBArray):
    ''' PiCamera module doesn't have 4 byte per pixel RGBA/BGRA version equivalent, so this inherits from the 3-bpp/RGBA/BGRA version to provide it
    '''

    def flush(self):
        self.array = self.bytes_to_rgba(self.getvalue(), self.size or self.camera.resolution)

    def bytes_to_rgba(self, data, resolution):
        ''' Converts a bytes objects containing RGBA/BGRA data to a `numpy`_ array.  i.e. this is the 4 byte per pixel version.
            It's here as a class method to keep things neat - the 3-byte-per-pixel version is a module function. i.e. picamera.array.bytes_to_rgb()
        '''
        width, height = resolution
        fwidth, fheight = picamera.array.raw_resolution(resolution)
        # Workaround: output from the video splitter is rounded to 16x16 instead
        # of 32x16 (but only for RGB, and only when a resizer is not used)
        bpp = 4
        if len(data) != (fwidth * fheight * bpp):
            fwidth, fheight = picamera.array.raw_resolution(resolution, splitter=True)
            if len(data) != (fwidth * fheight * bpp):
                raise PiCameraValueError('Incorrect buffer length for resolution %dx%d' % (width, height))
        # Crop to the actual resolution
        return np.frombuffer(data, dtype=np.uint8).reshape((fheight, fwidth, bpp))[:height, :width, :]


class CameraWriter(multiprocessing.Process):

	def __init__(self,camera):
		super(CameraWriter, self).__init__()
		self.camera = camera
		print('CAMERA WRITER INIT')
	def run(self):
		while True:
			print('HERE IS WRITER')
			_date = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-4]
			write_names_as = "{}.jpg".format(_date)

			# Write to disk as sequence
			self.camera.capture_sequence([write_names_as],
					format='jpeg',
					use_video_port=True)



class Capturador(multiprocessing.Process):

	"""
	Capture jpg images into PiCameraPaths.path_to_work
	:param:
	:return:  I / O

	5MP
	width: int:  2592
	height: int: 1944

	8MP
	width: int:  3280
	height: int: 2464

	"""

	def __init__(self, video_source=0, width=2592, height=1944, pipe = None):
		super(Capturador, self).__init__()
		# Initial parameters
		self.video_source = video_source
		self.width = width  # Integer Like
		self.height = height  # Integer Like
		self.pipe = pipe
		# Variable para marcar paquete de frames
		print('EXITOSAMENTE CREE LA CLASE Capturador!!!')


	def run(self):

		camera = picamera.PiCamera()
		camera.resolution = (self.width, self.height)  # self.camera.MAX_RESOLUTION
		camera.framerate = 2  # original 1

		camera.exposure_mode = 'sports'

		# highResCap = PiRGBAArray(camera)  # new 4-byte-per-pixel version above
		lowResCap = PiRGBAArray(camera, size=(320, 240))

		# self.camera.shutter_speed      = 190000
		# self.camera.iso                = 800
		lowResStream = camera.capture_continuous(lowResCap, format="bgra", use_video_port=True,
												splitter_port=2, resize=(320, 240))
		camera.start_preview()


		time.sleep(2.0)
		print("done warming up")

		# Run Image Writer in parallel
		#camera_writer = CameraWriter(camera)
		#camera_writer.start()
		fvs = FileVideoStream(camera).start()

		while True:
			tic = time.time()

			# Pi Camera Hyperparameters init

			lrs = lowResStream.__next__()
			lrFrame = lrs.array
			lowResCap.truncate(0)

			tac = time.time()
			print('time is', tac-tic)
			self.pipe.send(lrFrame)





class FileVideoStream:
	def __init__(self, camera):
		# initialize the file video stream along with the boolean
		# used to indicate if the thread should be stopped or not
		self.camera = camera
		self.stopped = False
 
		# initialize the queue used to store frames read from
		# the video file

	def start(self):
		# start a thread to read frames from the file video stream
		t = Thread(target=self.update, args=())
		t.daemon = True
		t.start()
		return self

	def update(self):
		# keep looping infinitely
		while True:
			# if the thread indicator variable is set, stop the
			# thread

			# otherwise, ensure the queue has room in it
			# read the next frame from the file
			_date = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-4]
			write_names_as = "{}.jpg".format(_date)

			# Write to disk as sequence
			self.camera.capture_sequence([write_names_as], 	format='jpeg', 	use_video_port=True)

			if self.stopped:
				break
	def stop(self):
		# indicate that the thread should be stopped
		self.stopped = True



if __name__ == '__main__':

	out_pipe, in_pipe = multiprocessing.Pipe(duplex=False)
	camera_ = Capturador(pipe = in_pipe)
	camera_.start()
	while True:
		lrFrame = out_pipe.recv()
		cv2.imshow('lores', lrFrame)
		ch = 0xFF & cv2.waitKey(5)
		if ch == ord('q'):
			camera_.stop()
			break
