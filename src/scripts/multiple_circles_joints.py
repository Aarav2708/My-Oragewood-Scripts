#!/usr/bin/env python3


from __future__ import print_function


import sys
import numpy as np
import math
import copy
import rospy
import moveit_commander
import moveit_msgs.msg
from geometry_msgs.msg import Point
import geometry_msgs.msg
import tf.transformations

try:
    from math import pi, tau, dist, fabs, cos
except:  # For Python 2 compatibility
    from math import pi, fabs, cos, sqrt

    tau = 2.0 * pi

    def dist(p, q):
        return sqrt(sum((p_i - q_i) ** 2.0 for p_i, q_i in zip(p, q)))


from std_msgs.msg import String
from moveit_commander.conversions import pose_to_list

## END_SUB_TUTORIAL


def all_close(goal, actual, tolerance):
    """
    Convenience method for testing if the values in two lists are within a tolerance of each other.
    For Pose and PoseStamped inputs, the angle between the two quaternions is compared (the angle
    between the identical orientations q and -q is calculated correctly).
    @param: goal       A list of floats, a Pose or a PoseStamped
    @param: actual     A list of floats, a Pose or a PoseStamped
    @param: tolerance  A float
    @returns: bool
    """
    if type(goal) is list:
        for index in range(len(goal)):
            if abs(actual[index] - goal[index]) > tolerance:
                return False

    elif type(goal) is geometry_msgs.msg.PoseStamped:
        return all_close(goal.pose, actual.pose, tolerance)

    elif type(goal) is geometry_msgs.msg.Pose:
        x0, y0, z0, qx0, qy0, qz0, qw0 = pose_to_list(actual)
        x1, y1, z1, qx1, qy1, qz1, qw1 = pose_to_list(goal)
        # Euclidean distance
        d = dist((x1, y1, z1), (x0, y0, z0))
        # phi = angle between orientations
        cos_phi_half = fabs(qx0 * qx1 + qy0 * qy1 + qz0 * qz1 + qw0 * qw1)
        return d <= tolerance and cos_phi_half >= cos(tolerance / 2.0)

    return True


class MoveGroupPythonInterfaceTutorial(object):
    """MoveGroupPythonInterfaceTutorial"""

    def __init__(self):
        super(MoveGroupPythonInterfaceTutorial, self).__init__()

        ## BEGIN_SUB_TUTORIAL setup
        ##
        ## First initialize `moveit_commander`_ and a `rospy`_ node:
        moveit_commander.roscpp_initialize(sys.argv)
        rospy.init_node("move_group_python_interface_tutorial", anonymous=True)

        ## Instantiate a `RobotCommander`_ object. Provides information such as the robot's
        ## kinematic model and the robot's current joint states
        robot = moveit_commander.RobotCommander()

        ## Instantiate a `PlanningSceneInterface`_ object.  This provides a remote interface
        ## for getting, setting, and updating the robot's internal understanding of the
        ## surrounding world:
        scene = moveit_commander.PlanningSceneInterface()

        
        group_name = "arm"
        move_group = moveit_commander.MoveGroupCommander(group_name)

        ## Create a `DisplayTrajectory`_ ROS publisher which is used to display
        ## trajectories in Rviz:
        display_trajectory_publisher = rospy.Publisher(
            "/move_group/display_planned_path",
            moveit_msgs.msg.DisplayTrajectory,
            queue_size=20,
        )

        ## END_SUB_TUTORIAL

        ## BEGIN_SUB_TUTORIAL basic_info
        ##
        ## Getting Basic Information
        ## ^^^^^^^^^^^^^^^^^^^^^^^^^
        # We can get the name of the reference frame for this robot:
        planning_frame = move_group.get_planning_frame()
        print("============ Planning frame: %s" % planning_frame)

        # We can also print the name of the end-effector link for this group:
        eef_link = move_group.get_end_effector_link()
        print("============ End effector link: %s" % eef_link)

        # We can get a list of all the groups in the robot:
        group_names = robot.get_group_names()
        print("============ Available Planning Groups:", robot.get_group_names())

        # Sometimes for debugging it is useful to print the entire state of the
        # robot:
        print("============ Printing robot state")
        print(robot.get_current_state())
        print("")
        ## END_SUB_TUTORIAL

        # Misc variables
        self.box_name = ""
        self.robot = robot
        self.scene = scene
        self.move_group = move_group
        self.display_trajectory_publisher = display_trajectory_publisher
        self.planning_frame = planning_frame
        self.eef_link = eef_link
        self.group_names = group_names

    

    def go_to_pose_goal(self):
        # Copy class variables to local variables to make the web tutorials more clear.
        # In practice, you should use the class variables directly unless you have a good
        # reason not to.
        move_group = self.move_group

        
        pose_goal = geometry_msgs.msg.Pose()

        # Define position for the end-effector
        pose_goal.position.x = 0.5
        pose_goal.position.y = 0.1
        pose_goal.position.z = 0.4

        # Define the RPY angles for the wrist orientation
        roll = np.pi   # Replace with desired roll in radians
        pitch = 0.0 # Replace with desired pitch in radians
        yaw = 0.0    # Replace with desired yaw in radians

        # Convert RPY to quaternion
        q = tf.transformations.quaternion_from_euler(roll, pitch, yaw)

        # Set the orientation with the quaternion values
        pose_goal.orientation.x = q[0]
        pose_goal.orientation.y = q[1]
        pose_goal.orientation.z = q[2]
        pose_goal.orientation.w = q[3]

        # Set the pose target with both position and orientation
        move_group.set_pose_target(pose_goal)

        ## Now, we call the planner to compute the plan and execute it.
        # `go()` returns a boolean indicating whether the planning and execution were successful.
        success = move_group.go(wait=True)

        # Calling `stop()` ensures there is no residual movement
        move_group.stop()

        # It is always good to clear your targets after planning with poses.
        # Note: there is no equivalent function for clear_joint_value_targets().
        move_group.clear_pose_targets()
    
    def plan_cartesian_path(self, center: Point, radius: float):
        # Copy class variables to local variables to make the web tutorials clearer.
        # In practice, you should use the class variables directly unless you have a good reason not to.
        move_group = self.move_group
        waypoints = []

        # Start at the current pose of the end-effector to keep the initial z-coordinate
        wpose = move_group.get_current_pose().pose
        wpose.position.z = wpose.position.z  # Keep the z-coordinate constant

        steps = 72  # Number of waypoints to approximate the circle (5-degree increments)

        # Generate waypoints around the circle in the x-y plane at the given center
        for i in range(steps + 1):
            angle = 2 * math.pi * i / steps  # Angle in radians for each waypoint
            wpose.position.x = center.x + radius * math.cos(angle)
            wpose.position.y = center.y + radius * math.sin(angle)
            waypoints.append(copy.deepcopy(wpose))

        # Generate the plan with the specified waypoints
        (plan, fraction) = move_group.compute_cartesian_path(
            waypoints, 0.01  # eef_step
        )

        # Return the computed plan and fraction of the path achieved
        return plan, fraction




    def display_trajectory(self, plan):
        # Copy class variables to local variables to make the web tutorials more clear.
        # In practice, you should use the class variables directly unless you have a good
        # reason not to.
        robot = self.robot
        display_trajectory_publisher = self.display_trajectory_publisher

        ## BEGIN_SUB_TUTORIAL display_trajectory
        ##
        ## Displaying a Trajectory
        ## ^^^^^^^^^^^^^^^^^^^^^^^
        ## You can ask RViz to visualize a plan (aka trajectory) for you. But the
        ## group.plan() method does this automatically so this is not that useful
        ## here (it just displays the same trajectory again):
        ##
        ## A `DisplayTrajectory`_ msg has two primary fields, trajectory_start and trajectory.
        ## We populate the trajectory_start with our current robot state to copy over
        ## any AttachedCollisionObjects and add our plan to the trajectory.
        display_trajectory = moveit_msgs.msg.DisplayTrajectory()
        display_trajectory.trajectory_start = robot.get_current_state()
        display_trajectory.trajectory.append(plan)
        # Publish
        display_trajectory_publisher.publish(display_trajectory)

        ## END_SUB_TUTORIAL

    def execute_plan(self, plan):
        # Copy class variables to local variables to make the web tutorials more clear.
        # In practice, you should use the class variables directly unless you have a good
        # reason not to.
        move_group = self.move_group

        ## BEGIN_SUB_TUTORIAL execute_plan
        ##
        ## Executing a Plan
        ## ^^^^^^^^^^^^^^^^
        ## Use execute if you would like the robot to follow
        ## the plan that has already been computed:
        move_group.execute(plan, wait=True)

        ## **Note:** The robot's current joint state must be within some tolerance of the
        ## first waypoint in the `RobotTrajectory`_ or ``execute()`` will fail
        ## END_SUB_TUTORIAL

    

    
def main():
    try:
        tutorial = MoveGroupPythonInterfaceTutorial()
        
        # Define the center of the circle
        center = geometry_msgs.msg.Point()
        center.x = 0.5  # Set the desired x-coordinate for the center
        center.y = 0.1  # Set the desired y-coordinate for the center
        center.z = 0.4  # Set the z-coordinate (will remain unchanged in the path)

        # Define the radius of the circle
        radius = 0.1

        tutorial.go_to_pose_goal()
        print("============ Reached Pose Goal")
        
        # Call the modified plan_cartesian_path function with center and radius
        cartesian_plan, fraction = tutorial.plan_cartesian_path(center, radius)

        # Check if the fraction is less than 1
        if fraction < 1.0:
            rospy.logerr(f"Cartesian path planning failed: only {fraction*100}% of the path could be planned.")
            raise ValueError("Insufficient trajectory planning: unable to calculate the full path.")
        
        # If the fraction is 1, continue to display and execute the trajectory
        tutorial.display_trajectory(cartesian_plan)
        print("============ Displayed Cartesian Path")
        
        tutorial.execute_plan(cartesian_plan)
        print(f"============ Executed Cartesian Path with fraction={fraction}")

        # Print task complete only if the entire path was planned
        if fraction == 1.0:
            print("============ Task Complete")

    except rospy.ROSInterruptException:
        return
    except KeyboardInterrupt:
        return
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()




