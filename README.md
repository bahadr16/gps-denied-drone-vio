# GPS-Denied Indoor Drone — Autonomous Flight with VIO

A drone simulation that estimates position using only a camera and IMU — no GPS — and is capable of waypoint navigation. Built on ROS 2, Gazebo, ArduPilot SITL, and OpenVINS.

---

## Architecture

```
Gazebo (Camera + IMU)
        ↓
   OpenVINS (VIO)
  /ov_msckf/poseimu
        ↓
   vio_bridge.py
/mavros/vision_pose/pose
        ↓
      MAVROS
        ↓
  ArduPilot SITL
        ↓
  Gazebo Motors
```

The system consists of five layers:

1. **Gazebo** — Drone model with virtual camera and IMU sensors. Runs the physics engine.
2. **OpenVINS** — Fuses camera images and IMU data to estimate the drone's position.
3. **vio_bridge.py** — Converts OpenVINS output to the format expected by MAVROS.
4. **MAVROS** — MAVLink bridge between ROS 2 and ArduPilot.
5. **ArduPilot SITL** — Software-in-the-loop simulation of the full Pixhawk flight controller.

---

## Tech Stack

| Component | Version |
|---|---|
| ROS 2 | Humble |
| Gazebo | Classic 11 |
| ArduPilot | 4.8.0-dev |
| OpenVINS | v2.x (ov_msckf) |
| MAVROS | Humble |
| Python | 3.10 |

---

## Installation

### 1. Dependencies

```bash
sudo apt install ros-humble-mavros ros-humble-mavros-extras
sudo apt install ros-humble-rqt-image-view
pip install pymavlink --break-system-packages
```

### 2. OpenVINS

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src
git clone https://github.com/rpng/open_vins.git
cd ~/ros2_ws
colcon build --symlink-install --packages-skip ov_eval
source install/setup.bash
```

### 3. ArduPilot + Gazebo Plugin

```bash
git clone https://github.com/ArduPilot/ardupilot.git
git clone https://github.com/khancyr/ardupilot_gazebo.git
```

For ArduPilot setup: https://ardupilot.org/dev/docs/setting-up-sitl-on-linux.html

---

## Running the System

Each component runs in a separate terminal.

**Terminal 1 — Gazebo:**
```bash
gazebo --verbose ~/ardupilot_gazebo/worlds/iris_arducopter_runway.world
```

**Terminal 2 — ArduPilot SITL:**
```bash
cd ~/ardupilot
sim_vehicle.py -v ArduCopter -f gazebo-iris --console
```

**Terminal 3 — MAVROS:**
```bash
ros2 launch mavros apm.launch fcu_url:=udp://127.0.0.1:14550@14555
```

**Terminal 4 — OpenVINS:**
```bash
source ~/ros2_ws/install/setup.bash
ros2 launch ov_msckf subscribe.launch.py \
  config_path:=/home/<user>/ros2_ws/install/ov_msckf/share/ov_msckf/config/gazebo_iris/estimator_config.yaml \
  use_stereo:=false max_cameras:=1
```

**Terminal 5 — VIO Bridge:**
```bash
source ~/ros2_ws/install/setup.bash
python3 scripts/vio_bridge.py
```

**Terminal 6 — Fly the drone (in SITL console):**
```bash
mode guided
arm throttle
takeoff 10
velocity 3 0 0
```

---

## Key ROS 2 Topics

| Topic | Type | Description |
|---|---|---|
| `/iris/camera/image_raw` | sensor_msgs/Image | Gazebo camera feed |
| `/iris/imu/data_raw` | sensor_msgs/Imu | Gazebo IMU data |
| `/ov_msckf/poseimu` | PoseWithCovarianceStamped | OpenVINS position estimate |
| `/mavros/vision_pose/pose` | PoseStamped | VIO pose sent to MAVROS |
| `/mavros/state` | mavros_msgs/State | ArduPilot connection status |
| `/ground_truth/pose` | nav_msgs/Odometry | Gazebo ground truth (for validation) |

---

## ArduPilot EKF Parameters

### GPS mode (default):
```
param set EK3_SRC1_POSXY 3
param set EK3_SRC1_POSZ 1
param set EK3_SRC1_YAW 1
param set EK3_SRC2_POSXY 0
param set EK3_SRC2_POSZ 0
param set EK3_SRC2_YAW 0
param set EK3_SRC_OPTIONS 0
reboot
```

### Switch to VIO (while drone is airborne):
```
param set EK3_SRC1_POSXY 6
param set EK3_SRC1_POSZ 6
param set EK3_SRC1_YAW 6
```

---

## Observation & Validation

**View camera feed:**
```bash
ros2 run rqt_image_view rqt_image_view
```

**Monitor OpenVINS position output:**
```bash
ros2 topic echo /ov_msckf/poseimu
```

**Verify vision pose is reaching MAVROS:**
```bash
ros2 topic hz /mavros/vision_pose/pose
```

---

## Issues Encountered & Solutions

### 1. OpenVINS config file fails to load
OpenVINS requires OpenCV FileStorage format with 50+ parameters. Solution: copy OpenVINS's own `rpng_sim` config set and only change the topic names.

### 2. Subscription count: 0
ROS 2 topic names must start with `/`. Use `/iris/camera/image_raw`, not `iris/camera/image_raw`.

### 3. IMU Sensor.cc:510 error
Gazebo cannot initialize the IMU sensor without a `<imu><noise>` block in the SDF file. Add Gaussian noise parameters to both `iris_with_ardupilot/model.sdf` and `iris_with_standoffs/model.sdf`.

### 4. OpenVINS not initializing — not enough feats
The scene was too monotonous (empty runway). Adding objects such as Construction Barrels and Cones provides enough visual features for tracking.

### 5. Dark scene — no features detected
Ambient light must be added to the world file. OpenVINS feature detection requires sufficient contrast.

### 6. Platform moving too much / no accel jerk
Static initialization requires the platform to be still first. Use dynamic initialization (`init_dyn_use: true`) with relaxed thresholds.

### 7. EKF Failsafe — position lost
Monocular VIO has inherent scale ambiguity. The large discrepancy between GPS position and VIO position triggers ArduPilot's EKF failsafe, causing the drone to land.

---

## Current Status & Future Work

### Completed
- Gazebo simulation environment with camera and IMU sensors
- Camera and IMU topics connected to ROS 2
- OpenVINS VIO running and producing position estimates
- MAVROS bridge and ArduPilot SITL integration
- Full end-to-end pipeline connected — all components communicating

### Known Issue — GPS-Denied Flight Not Yet Achieved

The full GPS-denied autonomous flight goal has not been completed. Here is the exact state:

- The entire pipeline is connected and all components communicate correctly.
- OpenVINS initializes and produces position estimates.
- vio_bridge converts and forwards the pose to MAVROS at ~12 Hz.
- ArduPilot receives the vision pose via MAVLink.

However, when switching EKF source from GPS to VIO while airborne, ArduPilot triggers an EKF failsafe and lands. The root cause is **monocular VIO scale ambiguity** — OpenVINS estimates position in the correct direction but at the wrong scale (off by ~100-500x). The resulting position values are far from the GPS reference, causing ArduPilot to reject the VIO source.

This is a fundamental limitation of monocular cameras, not a software bug. A stereo camera resolves this completely.

### Future Work
- **Stereo camera integration** — eliminates scale ambiguity entirely
- **Proper camera-IMU calibration** — using Kalibr for accurate values
- **ArduPilot vision-aiding parameter tuning** — `VISO_TYPE`, `EK3_POSNE_M_NSE`, `VISO_DELAY_MS`
- **Waypoint mission execution** — autonomous navigation via MAVROS
- **Physical hardware** — Raspberry Pi 4 + RealSense D435i + Pixhawk

---

## References

- [OpenVINS Documentation](https://docs.openvins.com)
- [ArduPilot Non-GPS Navigation](https://ardupilot.org/copter/docs/common-non-gps-navigation.html)
- [MAVROS Documentation](https://github.com/mavlink/mavros)
- [Gazebo Classic](https://classic.gazebosim.org/tutorials)
- [ROS 2 Humble](https://docs.ros.org/en/humble/)
