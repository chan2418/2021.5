from fx import *
import fx 

layer = Layer(uniqueLabel("chan"))
layer_pos = layer.property("transform.position")
layer_pos.constant = False
print(activeNode())
output_node = fx.Node("RotoNode")
session = fx.activeSession()
session.addNode(output_node)

output_node.property("objects").addObjects([layer])
select([layer])