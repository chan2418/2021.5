# from fx import *
# from tools.objectIterator import getObjects

# class SelectChildren(Action):
# 	"""Selects all children of selected objects."""

# 	def __init__(self):
# 		Action.__init__(self, "Select|Children")

# 	def available(self):
# 		assert len(selection()) > 0, "Select one or more objects"

# 	def execute(self):
# 		children_value = None
# 		objects = selection()
		
# 		for s in selection():
# 			children = getObjects(s.children)
# 			children_value = children
# 			print("______________",children)
# 			for child in children:
# 				if child not in objects:
# 					objects.append(child)
		
# 		beginUndo("Select Children")
# 		select(objects)
# 		endUndo()
# 		return children_value


from fx import *
from tools.objectIterator import getObjects

class SelectChildren(Action):
    """Selects all children of a specific RotoNode by name."""

    def __init__(self, roto_node_name):
        Action.__init__(self, "Select|Children")
        self.roto_node_name = roto_node_name  # Store the RotoNode name

    def available(self):
        assert len(selection()) > 0, "Select one or more objects"

    def execute(self):
        children_value = None
        objects = selection()

        for s in selection():
            # Check if the selected object is a RotoNode and matches the name
            
            children = getObjects(s.children)
            children_value = children
            print("______________", children)
            for child in children:
                # Only add the child if it is a RotoNode
                objects.append(child)

        # If we found the RotoNode and its children, select them
        if children_value:
            beginUndo("Select RotoNode Children")
            select(objects)  # Select the RotoNode and its children
            endUndo()
        else:
            print(f"No RotoNode found with name: {self.roto_node_name}")
        
        return children_value


# roto_node_name = "Roto1 1"  # Replace with your actual RotoNode name

# Execute the action
# action.execute()


