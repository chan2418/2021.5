
import fx

def create_motion_blur():
    # Get the current project
    project = fx.activeProject()
    
    # Create a new Motion Blur node
    motion_blur = project.create("MotionBlur", "MotionBlur1")
    
    # You can set parameters on the motion blur node if needed
    # motion_blur.setParam("samples", 16)
    # motion_blur.setParam("shutterAngle", 180)
    
    # Connect the node to the existing workflow if needed
    # For example, you might connect it to the output of another node:
    # source_node = project.node("YourSourceNode")
    # if source_node:
    #     motion_blur.setInput(0, source_node)
    
    # Save the project
    project.save()
    
    print("Motion Blur node created successfully")

# Run the function
create_motion_blur()
