from fx import *
import fx
import sys
import os

project_save = fx.activeProject()

class SessionBuilder:
    def __init__(self, session=None, layer=None):
        self.session = session
        self.last_node = None
        self.source_nodes = []
        project = fx.activeProject()

        for source in project.sources:
            self.build(source, sources=project.sources, nodes=["RotoNode"], layer=layer)

    def build(self, source, depth=Depth_Float16, sources=None, nodes=None, layer=None):
        self.session = fx.activeSession()
        self.session.size = source.size
        self.session.duration = source.duration
        self.session.pixelAspect = source.pixelAspect
        self.session.depth = depth
        self.session.startFrame = source.startFrame
        
        if sources:
            for source in sources:
                self.addSource(source)
            self.last_node = self.source_nodes[0]

        if nodes:
            for i in range(int(layer)):
                for node in nodes:
                    self.addNodeToSource(node)

        return self

    def refreshUI(self):
        """Force a UI refresh."""
        if hasattr(self.session, "validate"):
            self.session.validate(self.session.workRange)  # Pass valid range

    def findSource(self, id):
        for source in self.session.project.sources:
            if source.id == id:
                return source
        return None

    def createOutput(self):
        return Node("OutputNode")

    def addSource(self, source, label=None):
        node = Node("SourceNode")
        node.property("stream.primary").setValue(source)
        node.property("alpha.type").value = source.alphaType

        dataWindow = source.dataWindow()
        displayWindow = self.session.displayWindow
        if dataWindow.valid:
            node.property("center").value = dataWindow == self.session.displayWindow

        node.label = source.label
        self.session.addNode(node)
        if not self.last_node:
            self.last_node = node
        self.source_nodes.append(node)
        return self

    def addNode(self, node):
        if not isinstance(node, Node):
            node = Node(node)
        self.session.addNode(node)
        if self.last_node:
            self.connect(self.last_node, node)
        self.last_node = node
        return self

    def connect(self, prev_node, new_node):
        output = prev_node.getOutput(0)
        input = new_node.primaryInput
        if output and input:
            output.connect(input)
        return self

    def create_layer(self, label, node):
        layer = Layer(uniqueLabel(label))
        layer_pos = layer.property("transform.position")
        layer_pos.constant = False
        print(activeNode())
        node.property("objects").addObjects([layer])
        select([layer])

    def addNodeToSource(self, node):
        """
        Adds a node and connects it to the first SourceNode in the session.
        """
        if not isinstance(node, Node):
            node = Node(node)  # Ensure the node is a Node instance
        if node.type == "RotoNode":
            roto_node_name = self.get_latest_roto_node_name(node.label)  # Fixed indentation
            node.label = roto_node_name

        self.session.addNode(node)

        # Connect the new node to the first SourceNode
        if self.source_nodes:
            source_node = self.source_nodes[0]  # First SourceNode
            self.connect(source_node, node)
            label = ["nb", "nmb"]
            for i in label:
                self.create_layer(i, node)

        else:
            print("No SourceNode available to connect to.")
        return self
    
    def get_latest_roto_node_name(self, roto_label):
        """Collect all RotoNode objects and generate the next name based on the label."""
        roto_nodes = []  # List to collect all RotoNodes
        
        # Get the active session
        session = fx.activeSession()
        if not session:
            print("No active session found.")
            return None
        
        # Loop through all nodes in the session to find RotoNodes
        for node in session.nodes:
            if node.type == "RotoNode":
                roto_nodes.append(node)
        
        # Filter for RotoNodes that start with the roto_label
        matching_roto_nodes = [node for node in roto_nodes if node.label.startswith(roto_label)]
        print("Matching RotoNodes:")
        
        # Print the actual RotoNodes
        for node in matching_roto_nodes:
            print(f"RotoNode label: {node.label}, Node object: {node}")
        
        # Handling naming for RotoNodes
        if matching_roto_nodes:
            # Extract numeric suffixes safely
            suffixes = []
            for node in matching_roto_nodes:
                suffix = node.label[len(roto_label):].strip()  # Get the part after the base label
                if suffix.isdigit():  # Check if it's numeric
                    suffixes.append(int(suffix))
                else:
                    suffixes.append(0)  # Treat nodes without a number as 0
            
            # Determine the next suffix
            next_suffix = max(suffixes) + 1
            node_name = roto_label + str(next_suffix)
        else:
            # If no matching RotoNodes, start with "roto_label1"
            node_name = roto_label + "1"
        
        print("Next RotoNode name:", node_name)
        return node_name
