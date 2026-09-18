################create mate snippet channel ################################

import nuke
import sys 
sys.path.append("/tools/common/scripts/BFS_DEV/support_script/nuke_sg_integration/scripts/my_task/Baction/")
import b_action_read_node
from importlib import reload
reload(b_action_read_node)
list_value = nuke.toNode("context_knobs").knob("mate_paths").value()
mate_snippet_path = nuke.toNode("context_knobs").knob("matte_snippet_path").value()
mate_out_path = nuke.toNode("context_knobs").knob("matte_out_path").value()
print(list_value)
connect_dot_name = "matte_connect"
b_action_read_node.create_matte_snippet(list_value,connect_dot_name,mate_snippet_path,mate_out_path)

#############################################################################


