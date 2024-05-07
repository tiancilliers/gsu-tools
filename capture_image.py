from time import sleep
from picamera2 import Picamera2
from rich.console import Console
import numpy as np
import cv2
from scipy.spatial.transform import Rotation

def pose_estimation(frame):
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
    parameters = cv2.aruco.DetectorParameters()
    parameters.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    parameters.relativeCornerRefinmentWinSize = 0.1
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    corners, ids, rejected = detector.detectMarkers(image)

    for markerCorner, markerId in zip(corners, ids.get().flatten()):
        (topLeft, topRight, bottomRight, bottomLeft) = markerCorner.get().reshape((4, 2))
        cX, cY = int((topLeft[0] + bottomRight[0]) / 2), int((topLeft[1] + bottomRight[1]) / 2)
        marker_points = np.array([[-0.025, 0.025, 0], [0.025, 0.025, 0], [0.025, -0.025, 0], [-0.025, -0.025, 0]], dtype=np.float32)
        _, R, t = cv2.solvePnP(marker_points, 
                               markerCorner.get()[0], 
                               np.array(((2700, 0, 0), (0, 2700, 0), (0, 0, 1))), 
                               np.array((0.0, -0.0, 0, 0)), 
                               False, 
                               cv2.SOLVEPNP_IPPE_SQUARE)
        mat = cv2.Rodrigues(R)[0]
        r = Rotation.from_matrix(mat.T@np.array([[0,-1,0],[-1,0,0],[0,0,-1]]))
        console.log(r.as_euler('zyx', degrees=True))
            

console = Console()

console.log("Initialising camera...")
camera = Picamera2()
config = camera.create_still_configuration(buffer_count=2,main={"size":(2000,2000)})
camera.configure(config)
camera.start()
console.log("Camera started.")

for i in range(10):
    image = camera.capture_array()
    console.log(f"Captured {image.shape}")
    pose_estimation(image)

console.log("Stopping...")
camera.stop()
console.log("Done")