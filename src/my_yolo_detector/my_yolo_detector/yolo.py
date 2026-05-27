#file that contains the yolo algorithm model
from ultralytics import YOLO
import rclpy 
from rclpy.node import Node
#used to subscribe to camera for image
from sensor_msgs.msg import Image
#Allows for opencv images from ros
from cv_bridge import CvBridge

#getting the raw value data type from vision msg
from vision_msgs.msg import *

'''
This class represents the yolo node that will be used for ros2.
Purpose: Initailize the node, and connect the connection between this node and camera.
Inheritance: This node inherits from the ROS2 Node class, which servers as the single point of entry for essiantal communication features.
output: annotated image and raw detection data

'''
class YoloNode(Node):
    #initialize the node
    def __init__(self):
        super().__init__("YOLO_NODE")

        #parameter for the yolo, and path to subscribe to which is camera path you get from using cmd ros2 topic list in terminal
        self.model_name = 'yolo11n.pt'

        self.topic_in = '/robot/camera/image'
        #publisher paths
        self.topic_out = '/detections/image_annotated'
        self.topic_out_detection = '/detections/raw'

        #loading in the model. This will also give a message to the user that model is being loaded
        self.get_logger().info(f"Yolo model is being loaded: {self.model_name}.")
        try:
            self.model = YOLO(self.model_name)
            self.class_names = self.model.names
            self.get_logger().info("Model was successfully loaded.")
        except Exception as e:
            self.get_logger().error(f"failed to load in model: {e}.")
            rclpy.shutdown()
            return

        # intialize cv bridge. This helps turn ros2 output into cv images j
        self.bridge = CvBridge()

        #creating the subscriber to the path of the camera
        self.subscription = self.create_subscription(
            Image,
            self.topic_in,
            #nonblocking allows to run in parrellel with other program
            self.image_callback,
            10
        )

        self.get_logger().info(f"Node intialized and subrcribe to: {self.topic_in}")

        #creating the published
        self.image_pub = self.create_publisher(Image,self.topic_out,10)

        #creating the detection publish which is a list of 2d arrays
        self.detection_pub = self.create_publisher(Detection2DArray,self.topic_out_detection,10)


    def image_callback(self,msg):
        '''
        Purpose: that will recieve data and will take care of handling
        Input: self, and msg which is data recieved which is type Image as shown in subscriber specified above
        Ouput: Display a image in a window
        '''
        #will not show by default.. Extra steps required for this to work
        self.get_logger().debug("Recieved Image")

        try:
            #convert ros image to opencv image
            cv_image = self.bridge.imgmsg_to_cv2(msg,'bgr8')
        except Exception as e:
            self.get_logger().error(f"failed to convert image {e}")
            return

        #preform yolo detection
        results = self.model(cv_image, verbose=False)
        result = results[0] #get the first result

        #visualize the result
        pub_frame = result.plot()

        #this is for the publisher that will help nodes talk with each other.
        #converts cv image back to ros image
        try:
            annotated_msg = self.bridge.cv2_to_imgmsg(pub_frame,"bgr8")
            annotated_msg.header = msg.header
            self.image_pub.publish(annotated_msg)
        except Exception as e:
            self.get_logger().error(f"failed to convert image: {e}")
            return

        #publish the raw detection
        detections_array = Detection2DArray()
        #Creating a new message, the header is the original header from the camera. Essentially the frame from camera
        detections_array.header = msg.header

        #logic that will iterater through each object detected throught the current trip
        if result.boxes is not None:
            boxes = result.boxes.xyxy.cpu().numpy() #(N,4)
            confs = result.boxes.conf.cpu().numpy() #(N,)
            classes = result.boxes.cls.cpu().numpy() #(N,)

            for i in range(len(boxes)):
                xmin,ymin,xmax,ymax = boxes[i]

                #create Detection2D
                detection = Detection2D()
                detection.header = msg.header #syncing the timeframe with original image data

                #Getting the bounding box
                bbox = BoundingBox2D()

                #using Point2d for center
                center_point = Point2D()
                center_point.x = (xmin + xmax) / 2.0 #getting the width
                center_point.y = (ymin + ymax) / 2.0 #getting the height

                bbox.center.position = center_point
                bbox.size_x = float(xmax - xmin)
                bbox.size_y = float(ymax - ymin)

                detection.bbox = bbox                

                #getting the object class and score
                obj_hyp = ObjectHypothesisWithPose()
                obj_hyp.hypothesis.class_id = str(self.class_names[int(classes[i])])
                class_n = self.class_names[(classes[i])]
                obj_hyp.hypothesis.score = float(confs[i])
                score = float(confs[i])
                detection.results.append(obj_hyp)

                #logic that will check for object found that user wants. Not yet implement
                '''
                if(class_name == to_find and score >= 0.85)
                    object is found return
                        probably send a signal flag that alex can then connect to.. maybe publish something
                        return and terminate the project
                '''
                #else add to array of object found
                detections_array.detections.append(detection)

        #publishing the complete array
        self.detection_pub.publish(detections_array)


def main(args=None):
    #initailizing ros2 communication
    rclpy.init(args=args)

    #creating a ros2 Node
    node = YoloNode()

    try:

        #node will run,until killed
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Keyboard interrupt, shutting down")
    finally:
        #cleaning up
        node.destroy_node()
        #shutdown ros2 communication
        rclpy.shutdown()



if __name__ == "__main__":
    main()