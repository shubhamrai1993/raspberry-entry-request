import cv2
import picamera
import RPi.GPIO as GPIO
import time
import requests
import json
 
def invoke_camera():
	# Camera 0 is the integrated web cam on my netbook
	camera_port = 0
	 
	#Number of frames to throw away while the camera adjusts to light levels
	ramp_frames = 30
	 
	# Now we can initialize the camera capture object with the cv2.VideoCapture class.
	# All it needs is the index to a camera port.
	camera = cv2.VideoCapture(camera_port)
	 
	# Captures a single image from the camera and returns it in PIL format
	def get_image(camera):
	 # read is the easiest way to get a full image out of a VideoCapture object.
	 retval, im = camera.read()
	 return im
	 
	# Ramp the camera - these frames will be discarded and are only used to allow v4l2
	# to adjust light levels, if necessary
	for i in xrange(ramp_frames):
	 temp = get_image(camera)
	print("Taking image...")
	# Take the actual image we want to keep
	camera_capture = get_image(camera)
	file = "/home/pi/test_image.jpeg"
	# A nice feature of the imwrite method is that it will automatically choose the
	# correct format based on the file extension you provide. Convenient!
	cv2.imwrite(file, camera_capture)
	 
	# You'll want to release the camera, otherwise you won't be able to create a new
	# capture object until your script exits
	del(camera)
#  WIDTH=1280
#  HEIGHT=1024
#
#  camera = picamera.PiCamera()
#  camera.vflip = False
#  camera.hflip = False
#  camera.brightness = 60
#  camera.start_preview()
#  time.sleep(0.5)
#  camera.capture('test_image.jpeg', format='jpeg', resize=(WIDTH,HEIGHT))
#  camera.stop_preview()

def upload_image():
	url = "http://13.127.61.109:8080/images"
	headers = {
    'content-type': "multipart/form-data",
    'cache-control': "no-cache",
    }
	files = {'file': ('test_image.jpeg', open('/home/pi/test_image.jpeg', 'rb'), 'image/jpeg', headers)}
	response = requests.request("PUT", url, files=files)
	print response.text
	return json.loads(response.text)['imageUrl']

def submit_entry_request( imageUrl ):
	url = "http://13.127.61.109:8080/entryRequest"
	payload = {'ttl': 10000, 'pictureUrl': imageUrl }
	response = requests.put(url, json=payload)
	print response.text
	return json.loads(response.text)['entryRequestId']
	
def poll_for_status( entryRequestId ):
	url = "http://13.127.61.109:8080/entryRequest/status/" + entryRequestId
	for i in range(0, 9):
		response = requests.get(url)
		print response.text
		status = json.loads(response.text)['entryRequestStatus']
		if status == 'GRANTED':
			return True
		elif status == 'REJECTED':
			return False
		else :
			time.sleep(5)
	return False

# GPIO code start
# choose BOARD or BCM  
GPIO.setmode(GPIO.BCM)               # BCM for GPIO numbering  
# Set up lock output
outputPin=22
GPIO.setup(outputPin, GPIO.OUT, initial=0)    # set pin GPIO23 to mode output with initial off (0)  
#GPIO.output(outputPin, 1)   # set pin GPIO23 to on (1)
#time.sleep(1)  # tell the program to wait for 1 second
#GPIO.output(outputPin, 0)  # set pin output GPIO23 to off (0)

# Setup switch input
inputPin=4
GPIO.setup(inputPin, GPIO.IN)
switchOn = GPIO.input(inputPin)
print "Switch on: " + str(switchOn)
GPIO.setup(inputPin, GPIO.IN,  pull_up_down=GPIO.PUD_DOWN) # input with pull-down  
# GPIO.setup(inputPin, GPIO.IN,  pull_up_down=GPIO.PUD_UP)   # input with pull-up   

# Core logic
try: 
	while True:
		switchOn = GPIO.input(inputPin)
		print "Switch on: " + str(switchOn)
		if switchOn is 0 : 
			invoke_camera()
			imageUrl = upload_image()
			entryRequestId = submit_entry_request(imageUrl)
			openLock = poll_for_status(entryRequestId)
			if openLock:
				GPIO.output(outputPin, 1)
				print "Lock opened"
				time.sleep(10)
				GPIO.output(outputPin, 0)
				print "Lock closed again"
		else :
			time.sleep(1)
except KeyboardInterrupt: 
	print('Closing connection')
finally:
	GPIO.cleanup()

# GPIO code end
