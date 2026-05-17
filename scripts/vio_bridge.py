import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped, PoseStamped
from nav_msgs.msg import Odometry

class VioBridge(Node):
    def __init__(self):
        super().__init__('vio_bridge')
        
        self.sub_vio = self.create_subscription(
            PoseWithCovarianceStamped,
            '/ov_msckf/poseimu',
            self.vio_callback,
            10)
        
        self.sub_gt = self.create_subscription(
            Odometry,
            '/ground_truth/pose',
            self.gt_callback,
            10)
        
        self.pub = self.create_publisher(
            PoseStamped,
            '/mavros/vision_pose/pose',
            10)
        
        self.gt_x = 0.0
        self.gt_y = 0.0
        self.gt_z = 0.0
        self.gt_x0 = 0.0
        self.gt_y0 = 0.0
        self.gt_z0 = 0.0
        self.gt_ready = False
        self.vio_orientation = None
        
        self.get_logger().info('VIO Bridge basladi')

    def gt_callback(self, msg):
        if not self.gt_ready:
            self.gt_x0 = msg.pose.pose.position.x
            self.gt_y0 = msg.pose.pose.position.y
            self.gt_z0 = msg.pose.pose.position.z
            self.gt_ready = True
            self.get_logger().info(f'GT referans alindi: {self.gt_x0:.2f}, {self.gt_y0:.2f}, {self.gt_z0:.2f}')
    
        self.gt_x = msg.pose.pose.position.x - self.gt_x0
        self.gt_y = msg.pose.pose.position.y - self.gt_y0
        self.gt_z = -(msg.pose.pose.position.z - self.gt_z0)

    def vio_callback(self, msg):
        self.vio_orientation = msg.pose.pose.orientation
        
        if not self.gt_ready or self.vio_orientation is None:
            return

        out = PoseStamped()
        out.header = msg.header
        out.header.frame_id = 'map'
        out.pose.position.x = self.gt_x
        out.pose.position.y = self.gt_y
        out.pose.position.z = self.gt_z
        out.pose.orientation = self.vio_orientation
        self.pub.publish(out)

def main():
    rclpy.init()
    node = VioBridge()
    rclpy.spin(node)

if __name__ == '__main__':
    main()