from fx import *
from gui import undo

def deleteController():
    s = activeSession()

    if not s:
        print("No active session found.")
        return

    # Find the Motion Blur Controller node
    controller_node = None
    for n in s.nodes:
        print(n.type)
        if n.type == "ControllerNode":  # Assuming the controller is labeled "Motion Blur"
            controller_node = n
            break

    if not controller_node:
        print("Motion Blur Controller not found.")
        return

    # Iterate through nodes to remove expressions linked to the controller
    for n in s.nodes:
        mb_enable = n.property("motionBlur.enable")
        if mb_enable and mb_enable.expression and controller_node.sid in mb_enable.expression:
            mb_enable.expression = ""
            mb_enable.expressionEnabled = False

        mb_angle = n.property("motionBlur.shutterAngle")
        if mb_angle and mb_angle.expression and controller_node.sid in mb_angle.expression:
            mb_angle.expression = ""
            mb_angle.expressionEnabled = False

        mb_phase = n.property("motionBlur.shutterPhase")
        if mb_phase and mb_phase.expression and controller_node.sid in mb_phase.expression:
            mb_phase.expression = ""
            mb_phase.expressionEnabled = False

        mb_samples = n.property("motionBlur.samples")
        if mb_samples and mb_samples.expression and controller_node.sid in mb_samples.expression:
            mb_samples.expression = ""
            mb_samples.expressionEnabled = False

    # Remove the controller node from the session
    s.removeNode(controller_node)
    print("Motion Blur Controller deleted successfully.")


class DeleteMotionBlurControllerAction(Action):
    """Deletes the Motion Blur Controller."""

    def __init__(self):
        Action.__init__(self, "Delete|Motion Blur Controller")

    def available(self):
        assert activeSession(), "Select a Session"

    def execute(self):
        undo.run(deleteController, "Delete Motion Blur Controller")


def main_exe():
    DeleteMotionBlurControllerAction().execute()