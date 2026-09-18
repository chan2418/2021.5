
import fx
import sys

try:
    session = fx.activeSession()
    if session:
        print("Active Session Information:")
        print(f"Session Name: {session.name}")
        print(f"FPS: {session.fps}")
        print(f"Resolution: {session.width}x{session.height}")
        
        # Print available nodes
        print("\nNodes in session:")
        for node in session.nodes:
            print(f"- {node.name} (Type: {node.type})")
    else:
        print("No active session found.")
except Exception as e:
    print(f"Error accessing session information: {e}")
    sys.exit(1)
