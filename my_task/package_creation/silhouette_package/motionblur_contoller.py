import fx

def test ():
# Get the current session

	session = fx.activeSession()
	
	# Find the Roto node by name or access it directly
	roto_node = session.nodes
	for i in roto_node:
		if i.type == "RotoNode":
			i.property("motionBlur.enable")
		



from fx import *
from gui import undo

def createControllerNode(defaults):
    n = Node("ControllerNode")

    # Create motion blur parameters with same ranges as in motion blur enabled nodes
    enable_mb = Property("enable", "Enable", defaults["enable"])
    angle = Property("angle", "Shutter Angle", defaults["angle"], info={"min": 0.0, "max": 720.0})
    phase = Property("phase", "Shutter Phase", defaults["phase"], info={"min": -360.0, "max": 360.0})
    n_samples = Property("samples", "Samples", defaults["samples"], info={"min": 1, "max": 256})

    # Add the properties
    n.addProperty(enable_mb)
    n.addProperty(angle)
    n.addProperty(phase)
    n.addProperty(n_samples)

    return n


def createController(disable_motion_blur=False):
    s = activeSession()
    nodes = []

    # Default motion blur settings
    defaults = {
        "enable": not disable_motion_blur,  # Enable or disable based on argument
        "samples": 16,
        "angle": prefs['node.shutterAngle'],
        "phase": prefs['node.shutterPhase']
    }

    # Look through all nodes for ones with motion blur controls
    for n in s.nodes:
        mb_enable = n.property("motionBlur.enable")
        if mb_enable:
            nodes.append(n)
            # Use default values from the first node found if motion blur is enabled
            if len(nodes) == 1 and not disable_motion_blur:
                defaults["enable"] = mb_enable.value
                defaults["samples"] = int(n.motionBlur_samples.value)
                defaults["angle"] = n.motionBlur_shutterAngle.value
                defaults["phase"] = n.motionBlur_shutterPhase.value

    # Create the controller node and add it to the session
    label = uniqueLabel("Motion Blur", parent=s)
    controller = createControllerNode(defaults)
    controller.label = label
    s.addNode(controller)

    # Position the controller node near the active node or at the top-right of the graph
    if True:
        n = activeNode()
        if n:
            pos = trees.nextPos(n)
        else:
            bounds = trees.bounds
            size = trees.nodeSize(controller)
            pos = Point3D(bounds.right - size.x / 2, bounds.top + size.y / 2)
        controller.setState("graph.pos", pos)

    activate(controller)

    # Assign expressions to connected nodes
    for n in nodes:
        mb_enable = n.property("motionBlur.enable")
        mb_enable.expression = f'{controller.sid}.enable'
        mb_enable.expressionEnabled = True

        mb_angle = n.property("motionBlur.shutterAngle")
        mb_angle.expression = f'{controller.sid}.angle'
        mb_angle.expressionEnabled = not disable_motion_blur

        mb_phase = n.property("motionBlur.shutterPhase")
        mb_phase.expression = f'{controller.sid}.phase'
        mb_phase.expressionEnabled = not disable_motion_blur

        mb_samples = n.property("motionBlur.samples")
        mb_samples.expression = f'{controller.sid}.samples'
        mb_samples.expressionEnabled = not disable_motion_blur


class CreateMotionBlurControllerAction(Action):
    """Creates a controller node for global motion blur."""

    def __init__(self, disable_motion_blur=False):
        Action.__init__(self, "Create|Motion Blur Controller")
        self.disable_motion_blur = disable_motion_blur

    def available(self):
        assert activeSession(), "Select a Session"

    def execute(self):
        undo.run(lambda: createController(self.disable_motion_blur), "Create Motion Blur Controller")


# Add the action to Silhouette
def main_exe():
    disable_mb = True  # Set this to False to enable motion blur by default
    CreateMotionBlurControllerAction(disable_motion_blur=disable_mb).execute()