"""	SilhouetteFX 6 - Nuke v9+ exporter
	Version 3

	NOTES

	Open spline flags:
		osbe	0 rounded 1 square
		osee	0 rounded 1 square
		Silhouette's values are the opposite.
				0 is square
				1 is rounded

	Skew Handling:
		After Export() is initialized, the first act is to determine ANY skew terms are present
		in the selected shape hierarchies.
		EmitPreamble() is called - skew handling has no impact on this.
		EmitRotoNode() called next. This dives into Curves() which returns if anything
		"important" needs writing.
		AnimTreeRoot() is next. It seems to be only needed for legacy reasons as this drops into
		directly into AnimLayer(). This will be the root layer. AnimLayer() emits the layer
		transforms which has no impact on skew handling. AnimLayer() calls itself 
		recursively as needed for nested layers. Alternatively, it calls EmitShape() for any
		shapes contained in the present layer.
		In EmitShape()
		--- Potential clue to 06/14/18 bug - purity is false and has_skew is true.
		Open shapes are converted to Bezier, then Bezier() is called with purity as a parameter.
		As we enter Bezier() we're getting close to the descision point... at the bottom of the function
		we get to the call to ShapeTransforms(). As purity is false, ShapeTransforms() calls 
		EmitLayerTransforms() serving double duty here for shapes as well. purity is no longer passed
		along so here is one fork. If mocha perspective were OFF, Shape Transforms() would return
		immediately.
		EmitLayerTransforms() must check has_skew. Ahh. If has_skew is set and this is a layer and
		the layer is not pure we're returning. This is NOT the path the 06/14/18 bug is taking as
		we're an open shape not a layer. Note the variable 'layer' in this case is a shape not a
		layer. PrepareMatrices() is called.
		In PrepareMatrices() there is a per-frame check for has_skew. The first part of the if
		statement is skipped (has_skew == false).
		---------
		The W2I is compounded here. BUT - there is an if statement that says if the shape has
		transform, then use an identity - this can explain the bug because the identity * W2I
		is W2I. 
		06/14/18 bug found - add optional argument to Bezier() - the problem was that the shape
		transform of a converted shape is empty. Damn. I fixed this in an entirely different
		context years ago and did not remember this as an issue to consider.
"""

from fx import *
try:
    from StringIO import StringIO ## for Python 2
except ImportError:
    from io import StringIO ## for Python 3
import struct
import math
import os
# from inspect import currentframe, getframeinfo



#	This is a development flag. This value should be set to True when it is
#	to behave in release mode. When set to false, the exporter can be run
#	from the "Execute" button in the Silhouette script editor.

function_as_exporter = True

#	When running in release mode, these values specify the tags by which
#	the exporter will sync up with the user controllable parameters presented
#	in File -> Preferences -> Input / Output

# This UI preference decides if a color (RGB) is to be filled into shapes
# in addition to the alpha channel. Historically, we have only rendered
# to the alpha channel but some other products (mocha for example) will
# also render to the RGB channels. This makes it easier for users to see
# the shapes immediately after import.
render_four_channels_string = "io.nuke_9.four_channels"

#	This UI preference allows the user to write shapes fully baked where every
#	frame in the work range is treated as a keyframe.
fully_baked_string = "io.nuke_9.fully_baked"

# pretty_print (merged into file_size)
#	This UI preference allows the user to write more human readable exported
#	files. These are slightly larger but make SO MUCH MORE SENSE. The written
#	structure of Nuke exported files made understanding the file structure
#	incredibly difficult.

# export_in_hex (merged into file_size)
#	This UI preference allows the user to write more human readable exported
#	files. Nuke numbers are written in ASCII encoded binary. Numbers written
#	in this way are completely unreadable by humans but take up less space.
#	A major stroke of luck for me was to find that Nuke would also read human
#	readable numbers if they were not preceeded by '0x'.
file_size_string = "io.nuke_9.file_size"

#	This UI preference allows the user to include the Silhouette's project path
#	In the Nuke node's title. This can be helpful but makes for ugly nodes when
#	the Silhouette path name is long.

include_project_path_string = "io.nuke_9.include_project_name"

#	This UI preference allows the user to make use of the Nuke 'lifetime' feature
#	or not. When this feature is used, shapes do not "exist" in Nuke when outside
#	their lifetime. We use the Silhouette opacity value to drive this value. With
#	the special values of 0 and 100 percent, if the first opacity key value is a
#	special value as well as the second, and this feature is enabled, those frames
#	define the shape's lifetime.

use_lifetime_string = "io.nuke_9.use_lifetime"

#	This preference is a scalar multiplied by shape widths to allow the user to match
#	open shape widths in Nuke better.

width_multiplier_string = "io.nuke_9.width_multiplier"

#	These are symbols for modes of shapes found in Silhouette. Legacy feather means
#	there will not be the Silhouette 6.0 data structures associated with shapes.

LegacyFeather = 0
PerPointFeather = 1

#	These are symbols for the file_size preference.
#	SmallerFiles means hex-formatted numbers and less formatting.
#	LargerFiles means decimal-formatted numbers and more formatting for better human-readability.

SmallerFiles = 0
LargerFiles = 1

#	The following code is global and therefore execute the first time this module is
#	executed. It is used to install the File -> Preference -> Input / Output controls
#	into the Silhouette UI.
#
#	If new preference UI components are added, they must be added here to ensure they
#	are activated / registered with Silhouette at least once.

if render_four_channels_string not in prefs.keys():
	prefs.add(render_four_channels_string, False)

if use_lifetime_string not in prefs.keys():
	prefs.add(use_lifetime_string, False)

if fully_baked_string not in prefs.keys():
	prefs.add(fully_baked_string, False)

if file_size_string not in prefs.keys():
	prefs.add(file_size_string, value=SmallerFiles, items=["Smaller (hexidecimal numbers)", "Larger (human readable)"])

if include_project_path_string not in prefs.keys():
	prefs.add(include_project_path_string, False)

if width_multiplier_string not in prefs.keys():
	prefs.add(width_multiplier_string, value=1.0, min=0.0, max=100.0)

#	GLOBAL DEBUGGING AIDS

#	gf2h - GLOBAL float to hex converter
#	gh2f - GLOBAL hex to float converter
#
#	This is used when developing / debugging to figure out what the heck Nuke number strings
#	actually means. These functions are mimics of the functions found in the exporter class
#	itself. Those functions implement more features not needed in the debugging context.

def gf2h(x):
	"""f2h converts a float value into the hex format
	used by Nuke.
	"""
	if x == 0:
		return "0"
	if x == 1:
		return "1"

	p = struct.pack("!f", x)
	i = struct.unpack("!I", p)
	s = "%08X" % (int(i[0]))
	return "x" + s

def gh2f(x):
	"""h2f converts a hex string used by Nuke back into
	a float. This function isn't needed by an exporter
	but is here for symmetry and for someday.
	"""
	if x[0] == 'x':
		x = x[1:]
	s = struct.unpack('!f', x.decode('hex'))[0]
	return s

#	NUKE EXPORTER CLASS

class NukeExporterV3(Action):

	#	class initialization - installs the exporter into Silhouette with the
	#	specified string and file extension to be used.

	def __init__(self):
		Action.__init__(self, "Nuke 9+ Shapes", type=Action.ShapeExporter, extension="nk")
		self.curves_version = 1.2
		self.labels = {}
	
	# getLabel handles de-duplication of labels
	def getLabel(self, label):
		label = label.replace(' ', '_').replace('*', '')

		if label in self.labels:
			count = self.labels[label]
			count = count + 1
			self.labels[label] = count
			return label + "_" + str(count)
		
		self.labels[label] = 1
		return label

	# This function is used during older-style exports when a skew term is
	# found in any of the exported shapes.
	#
	def testAgainstEpsilon(self, v, target):
			# If a value is sufficiently close to another (typically close to 0 or 1)
			# return true. Some values like 0 and 1 are used so frequently that this is
			# a worthwhile trade of exporter execution time for file size reduction.
			if (abs(v - target) < 0.0000001):
					return True
			else:
					return False

	# This function is used during older-style exports when a skew term is
	# found in any of the exported shapes.
	#
	# If given a shape, it looks at it's parent. If given a layer, it looks
	# to see if there are any sublayers. This way it can be called from emitting
	# layer transforms AND from emitting shapes.

	def IsLayerPure(self, object):
			# If this object is a shape, we're trying to find out if it's parent
			# contains only shapes (is pure). If the object is a layer, then we
			# are checking it itself.
			if object.type == "Shape":
					object = object.parent
			layer_found = False
			for child in object.children:
					if child.type == 'Layer':
							layer_found = True
							break
			return not layer_found

	#	Initialization for each export operation.
	#
	#	A place within the exporter class to store shorthands of values to be used
	#	during each export.

	def Initialize(self):
		node = activeNode()
		self.node = node
		self.labels = {}

		# Debugging note - if during debugging a failure occurs, the exported file
		# remains open. To avoid confusion - type "exporter.file.close()" after failures.
		self.session = node.session
		self.session_start_frame = self.session.startFrame
		self.session_end_frame = self.session.startFrame + (self.session.workRange[1] - self.session.workRange[0])
		self.session_work_range = self.session.workRange
		self.session_size = self.session.size
		self.session_pixel_aspect = self.session.pixelAspect
		self.world_to_image_transform = self.DivideByW(self.node.worldToImageTransform)
		self.width_multiplier = prefs[width_multiplier_string]
		# this is a fudge factor for outline widths based on scene height
		# this is plugged into the shape's "overall width" parameter in Nuke
		session_height = self.session_size[1]
		self.width_multiplier = self.width_multiplier * (session_height / 1000.0) * 2.25

	def DivideByW(self, m):
		# Ensures the given matrix has a value of 1.0 in the [3][3] slot.
		w = m.value(3, 3)
		for y in range(4):
			for x in range(4):
				v = m.value(y, x) / w
				m.setValue(y, x, v)
		return m

	def SessionTimeToSilhouetteTime(self, session_time):
		# This function is frequently used. There is a grossly different sense of time
		# between logical and "physical" frame numbers. Frame numbers must be converted
		# for use in Nuke (as well).
		#
		# All frames in Silhouette are zero based. Frame 0 is always the first frame. This is Silhouette time.
		# If you want session time, add session.startFrame to it. This is session time.
		# Work range is always in session time.
		# To go from work range to Silhouette time, subtract session.startFrame.

		return session_time - self.session_start_frame


	def AdjustFrameNumber(self, silhouette_frame_number):
		# This is the function which converts Silhouette frame numbers into the number
		# space used by Nuke. Anywhere a frame number is written to the exported file
		# it should be run through this function.
		return silhouette_frame_number + self.session_start_frame

	def f2h(self, x):
		# f2h converts a float value into the hex format used by Nuke.
		# The hex / non-hex feature is implemented here.
		if self.print_in_hex == False:
			return str(x)

		p = struct.pack("!f", x)
		i = struct.unpack("!I", p)
		s = "%08X" % (int(i[0]))
		return "x" + s

	#	NOTE ABOUT PRETTY PRINTING
	#	self.pretty_print is either 0 or 1 and is used as a convenent scaler for printing
	#	tabs. I multiply this value by the number of tabs to be printed. If self.pretty_print
	#	is zero, no tabs are produced.

	#
	#	BEGIN AND END
	#	The pretty printing feature is run by Begin and End to a large degree.
	#	Begin and End are the most frequently called functions in the exporter.
	#

	def Begin(self, sb, new_line=False, tabs=0):
		# This function emits the opening brace used to introduce all Nuke blocks.
		# If the argument new_line is given and is True the opening brace is followed by a new line.
		sb.write(self.Tab(tabs))
		sb.write("{")
		if new_line == True:
			sb.write("\n")

	def End(self, sb, new_line=False, tabs=0):
		# This function emits the closing brace used to end all Nuke blocks. If the
		# argument new_line is given and is True the closing brace is followed by a new line.
		sb.write(self.Tab(tabs))
		sb.write("}")
		if new_line == True:
			sb.write("\n")

	def Tab(self, tabs=1):
		# This is a handy abstraction of tab printing.
		return "\t" * tabs * self.pretty_print

	#
	#	BOILER PLATE OUTPUT
	#

	def VersionBlock(self, sb, tabs=0):
		# The specific value printed here in the 'v' block is arbitrary from my perspective.
		# It is the value I find in every example .nk file so is parroted here.
		#
		# CRITICALLY IMPORTANT - IF A NEW LINE IS FOUND IN THE "{" PRECEEDING THIS
		# 'v' TAG, NUKE WILL CRASH CRASH CRASH CRASH - SEE NOTE DEMARKED BY #######
		sb.write(self.Tab(tabs))
		self.Begin(sb)
		sb.write("v ")
		sb.write(self.f2h(self.curves_version))
		self.End(sb, True)

	def EmitCurvesFlagBlock(self, sb, tabs=0):
		# The specific value printed here in the 'f' block is arbitrary from my perspective.
		# It is the value I find in every example .nk file so is parroted here. Note this is
		# a global flags value. There are other 'f' blocks that have non-zero values.
		sb.write(self.Tab(tabs) + "{f 0}\n")

	def EmitPreamble(self, sb):
		# This function emits the few lines of boiler plate appearing as front matter in Nuke scripts.
		sb.write("set cut_paste_input [stack 0]\nversion 9.0 v1\npush $cut_paste_input\n")

	def OutputBlock(self, sb):
		# The node we're writing sends its output to the alpha channel. Therefore, if you want to
		# see the output in Nuke, you have to view alpha specifically.
		# New feature 5/17 - user can elect to render into all channels not just alpha. This
		# is accimplished by NOT writing anything.
		if self.render_four_channels == False:
			sb.write(self.Tab() + "output alpha\n")

	def FormatBlock(self, sb, node_number):
		# The node number is no longer used and is a hold over from our support of multiple output
		# modes such as every shape in its own node. We don't need this mode any longer because
		# Foundry has sped up Nuke to be usable.
		#
		# NOTE: Occasionally Nuke will throw a warning that multiple SFX_WORLD_RECTs are defined.
		# This is a benign warning and can be ignored by the user. All will be well.
		sb.write(self.Tab() + "format " + "\"" + str(self.session.size[0]) + " " + str(self.session.size[1]) + " 0 0 " + str(self.session.size[0]) + " " + str(self.session.size[1]) + " " + str(self.session.pixelAspect))
		sb.write(" SFX_WORLD_RECT" + str(node_number) + "\"\n")

	#	ADJUSTEDKEYFRAMELIST
	#
	#	This function is a critical piece of the exporter. Given a property as a parameter
	#	and work range as globals, return a list of keys that have been properly clipped against
	#	the work range. The beginning and end of the work range are added as well to completely
	#	pin down the beginning and ending values.
	#
	#	This function is used for
	#		the 'px' list by passing s['path'] and,
	#		shape attributes such as s['opacity'] and
	#	but NOT for control point based attributes as any changes to these force a path keyframe
	#	so these changes would be picked up in the 'px' frames.

	def AdjustedKeyFrameList(self, property):
		# Building keyframe lists has been centralized here to include the
		# fully baked case. This removes the conditional statement from each
		# of the shape emission functions.
		if self.fully_baked == True:
			# Build an enumeration of the work range from start to end (inclusive)
			return range(int(self.SessionTimeToSilhouetteTime(self.session_work_range[0])), int(self.SessionTimeToSilhouetteTime(self.session_work_range[1])) + 1)

		number_of_keys = len(property.keys)
		if number_of_keys == 1:
			# This is a new short circuit. It comes about because I am eliminating the
			# distinction between keyed and constant splines.
			return [property.keys[0]]
		active_keyframe_index_at_start_of_work_range = -1
		active_keyframe_index_at_end_of_work_range = -1
		index = 0

		# Determine which key frame index is active when the workRangeStart frame is hit.
		for index in range(number_of_keys):
			if property.keys[index] > self.session_work_range[0]:
				break
			active_keyframe_index_at_start_of_work_range = index

		# Determine which key frame index is active when the workRangeEnd frame is hit.
		for index in range(number_of_keys):
			if property.keys[index] <= self.session_work_range[1]:
				active_keyframe_index_at_end_of_work_range = index
				continue
			if property.keys[index] > self.session_work_range[1]:
				break

		#print "Active keyframe index at start: " + str(active_keyframe_index_at_start_of_work_range)
		#print "Active keyframe index at end: " + str(active_keyframe_index_at_end_of_work_range)

		# All frames in Silhouette are zero based. Frame 0 is always the first frame. This is Silhouette time.
		# If you want session time, add session.startFrame to it. This is session time.
		# Work range is always in session time.
		# To go from work range to Silhouette time, subtract session.startFrame.
		
		# In v6 Silhouette would only export keys within the session work range, and write
		# additional keys at the head/tail of the work range, to better control the motion at
		# the ends of the work range. In V7, now that Silhouette has extrapolation and better
		# matches Nuke's interpolation, we always write all keys.

		key_frame_set = set()
		key_frame_list = []
		for f in property.keys:
			key_frame_set.add(f)

		key_frame_list = list(key_frame_set)
		key_frame_list.sort()

		#print "Returning: " + str(key_frame_list)
		return key_frame_list

	def BuildActualKeyFrameList(self, p):
		return p.keys

	def ReturnActiveKeyIndex(self, actual_key_frame_list, desired_frame):
		# In the processing of interpolation types, it is necessary to find previous
		# and next keyframes to inspect their interpolation types.
		length = len(actual_key_frame_list)
		if length == 0:
			return 0
		# test for short circuit.
		if desired_frame <= actual_key_frame_list[0]:
			return 0
		elif desired_frame >= actual_key_frame_list[length - 1]:
			return length - 1
		# length must be greater than 1
		if length <= 1:
			displayError("Impossible condition: ReturnActiveKeyIndex()", "Nuke exporter")
			return 0
		# handle slow case.
		for index in range(length - 1):
			if desired_frame >= actual_key_frame_list[index] and desired_frame < actual_key_frame_list[index + 1]:
				return index
		return length -1

	def EmitAnySingleValuedParameter(self, o, sb, silhouette_parameter_name, nuke_parameter_name, m=1, tabs=0):
		# THIS NEEDS ALL THE OPTIONS FROM THE C++ VERSION
		#	{x41e00000 x3e4ccccd xbcf2b9d6 1 x3d0e7835 1 258}
		#	{28        0.2       -0.02962  1 0.0347826 1 258}
		#	{fnum      value     in dy     1 }
		#	dy - positive is down
		# {fnum val - } is "SMOOTH"
		# Interoplation values:
		# 0	Hold
		# 1 Linear
		# 2 Ease In/Out
		# 3 Ease In
		# 4 Ease Out
		# 515 is catmul_rom
		# 516 is "cubic"
		# 276 is "HORIZONTAL"
		# 257 is HOLD - after			0x101
		# 258 is LINEAR - BOTH			0x102
		# THERE IS A BREAK FLAG 274 is linear in and something out.
		# UNSUPPORTED AS YET
		#	There seems there might be an incompatibility. Nuke has a way of taking into account previous
		#	and next key frame values. Silhouette interpolation types affect from here to the next key frame
		#	only. Hold will work fine. Linear will work fine. But after that, I am fudging all with "smooth"
		p = o[silhouette_parameter_name]
		#print o.label, silhouette_parameter_name, isinstance(o, Node), p.constant
		if p.constant == True:
			sb.write(" " + nuke_parameter_name + " ")
			sb.write(self.f2h(p.getValue(0) / 100.0 * m))
		else:
			sb.write("\n" + self.Tab(tabs) + nuke_parameter_name + "\n")
			actual_key_frames = self.BuildActualKeyFrameList(p)
			if len(actual_key_frames) == 0:
				return
			# begins outer block
			key_frame_list = self.AdjustedKeyFrameList(p)
			self.Begin(sb, True, tabs)
			for key_frame_index in range(len(key_frame_list)):
				active_key_index = self.ReturnActiveKeyIndex(actual_key_frames, key_frame_list[key_frame_index])
				interpolation = p.interpolation(active_key_index)
				# begins inner block
				self.Begin(sb, tabs=tabs+1)
				sb.write(self.f2h(self.AdjustFrameNumber(key_frame_list[key_frame_index])) + " " + self.f2h(p.getValue(key_frame_list[key_frame_index]) / 100.0 * m))
				if interpolation == Property.Hold:
					sb.write(" 0 1 0 1 257")
				elif interpolation == Property.Linear:
					sb.write(" 0 1 0 1 258")
				elif interpolation == Property.CatmullRom:
					sb.write(" 0 1 0 1 515")
				else:
					sb.write(" -")
				# ends inner block
				self.End(sb, True)
			# ends outer block
			self.End(sb, False, tabs)
			sb.write(self.Tab(tabs))

	#
	#	BEZIERS
	#

	def BezierPath(self, s, original_shape, sb, feather=False, tabs=0):
		multiplier = self.session_size[1]
		if self.has_skew == False:
			multiplier = 1.0

		if not original_shape:
			original_shape = s
			
		self.Begin(sb, tabs=tabs+1)
		sb.write("cc\n")
		if s.closed == True:
			sb.write(self.Tab(tabs+2) + "{f 8192}\n")
		else:
			sb.write(self.Tab(tabs+2) + "{f 1056800}\n")
		path = s['path']
		stroke_width = s['strokeWidth']
		number_of_points = len(path.getValue(path.keys[0]).points)
		key_frame_list = self.AdjustedKeyFrameList(path)
		actual_key_frames = self.BuildActualKeyFrameList(path)
		# Emit the 'px' block. This establishes the keyframes for the path keys.
		# Thereafter, path keyframe numbers are not printed, rather they are assumed.
		self.Begin(sb, tabs=tabs+2)
		sb.write("px\n")
		self.Begin(sb, tabs=tabs+3)
		for index in range(len(key_frame_list)):
			sb.write(self.f2h(self.AdjustFrameNumber(key_frame_list[index])))
			if index < len(key_frame_list) - 1:
				sb.write(" ")
		self.End(sb, True)
		# Initialize four lists.
		# lts = left tangents
		# cps = control points
		# rts = right tangents
		# its = interpolation types
		# ws = weights if open - seems to affect thickness.
		# fs = feathers if open
		# sws = stroke widths if open (from Silhouette)
		# These lists are needed to convert, in essence, from row major to column major.
		# Silhouette does this:
		#	for each key frame get the path
		#		for each point in the path
		#			define control points
		# Nuke does this:
		#	for each control point in path
		#		for each key frame
		#			define the x values
		#			define the y values
		lts = [None] * len(key_frame_list)
		cps = [None] * len(key_frame_list)
		rts = [None] * len(key_frame_list)
		its = [None] * len(key_frame_list)
		sws = [None] * len(key_frame_list)
		ws = [None] * len(key_frame_list)
		fs = [None] * len(key_frame_list)

		for key_frame_index in range(len(key_frame_list)):
			lts[key_frame_index] = []
			cps[key_frame_index] = []
			rts[key_frame_index] = []
			sws[key_frame_index] = []
			ws[key_frame_index] = []
			fs[key_frame_index] = []
			its[key_frame_index] = path.interpolation(self.ReturnActiveKeyIndex(actual_key_frames, key_frame_list[key_frame_index]))
			sws[key_frame_index] = stroke_width.getValue(key_frame_list[key_frame_index])

		for key_frame_index in range(len(key_frame_list)):
			# Get the path points on this frame. This is valid baked or not.
			#
			# 5/17 - place points into expanded Silhouette space - This
			# is only done if there are no perspective transformations
			# to be exported. This is a merge of two different export
			# methods - prompted by Legend.
			m = Matrix()
			if self.has_skew == False:
				m.scale(self.session_size[1], self.session_size[1])
			
			pl = Matrix()
			key_time = key_frame_list[key_frame_index]
			points = path.getValue(key_time)
			point_counter = -1
			for bp in points.points:
				point_counter = point_counter + 1
				if feather == False:
					if self.fully_baked == True:
						pl = original_shape.getTransform(key_time, True)
						if pl == None:
							pl = Matrix()
						pl.scale(1.0 / self.session_pixel_aspect, 1)

					# Process base control point data.
					# The apporach we are trying here is relative to the idea of writing all W * p
					# then writing homographies of the layer transforms. Please dear magic muffin
					# person in the magical sky, please let this work.
					cp = pl * bp[1]
					rt = m * (pl * bp[2] - cp)
					if rt.x == 0 and rt.y == 0:
						rt.x = 0.001
					lt = m * (pl * bp[0] - cp)
					cp = m * cp

					# Open shape width and feather values
					if s.closed == False:
						if len(bp) >= 5:
							# There are arbitrary calculations here which may be appropriate as we're matching
							# arbitrary methods on the Nuke side.
							w = bp[3] * 100 * 2 / 0.9
							f = bp[4] * 100 * 2 / 0.9
							#print "Shape: " + s.label + " Frame: " + str(key_frame_list[key_frame_index]) + " bp[3] " + str(bp[3]) + " sws: " + str(sws[key_frame_index])
							ws[key_frame_index].append(w)
							fs[key_frame_index].append(f)
						else:
							ws[key_frame_index].append(0)
							fs[key_frame_index].append(0)
							# Addison bug: the point I am investigating is the last point. Implement this hack only if the original shape was not already a bezier.
							# The emitted final point must have non-zero tangents.
							#if point_counter == number_of_points - 1 and self.is_converted_shape:
								#rt.x += 0.1
								#rt.y += 0.1
								#lt.x -= 0.1
								#lt.y -= 0.1
								#temp = lt
								#lt = rt
								#rt = temp
								#print "*Frame: " + str(key_frame_list[key_frame_index]) + " Point counter: " + str(point_counter)
					#if key_frame_index == 0:
					#	print lt, cp, rt
				else:
					if self.fully_baked == True:
						pl = original_shape.getTransform(key_time, True)
						if pl == None:
							pl = Matrix()
						pl.scale(1.0 / self.session_pixel_aspect, 1)
				
					cp = pl * bp[1]
					# process feathering - this is a little complicated as their are two
					# types of point structs in Silhouette corresponding to legacy and modern.
					# Legacy points possess only 3 memebers. If other than that, the point
					# is a modern struct.
					if len(bp) == 3:
						rt = m * (pl * bp[2] - cp)
						lt = m * (pl * bp[0] - cp)
						cp = Point3D()
					else:
						cp = m * (pl * bp[3])
						rt = m * (pl * bp[5])
						lt = m * (pl * bp[4])
					if rt.x == 0 and rt.y == 0:
						rt.x = 0.001

				cps[key_frame_index].append(cp)
				lts[key_frame_index].append(lt)
				rts[key_frame_index].append(rt)
		lists = (lts, cps, rts)
		for i in range(number_of_points):
			for list in lists:
				xsb = StringIO()
				ysb = StringIO()
				self.Begin(xsb, True)
				self.Begin(ysb, True)
				if s.closed == False and list is cps:
					wsb = StringIO()
					fsb = StringIO()
					wsb.write(self.Tab(tabs+5) + "osw\n")
					fsb.write(self.Tab(tabs+5) + "osf\n")
					self.Begin(fsb, True, tabs=tabs+5)
					self.Begin(wsb, True, tabs=tabs+5)
				for j in range(len(key_frame_list)):
					# The multiplication here is our work around for the horrendous
					# and illogical bugs found in the Nuke feather UI.
					xsb.write(self.Tab(tabs+5) + "{" + self.f2h(list[j][i].x * multiplier))
					ysb.write(self.Tab(tabs+5) + "{" + self.f2h(list[j][i].y * multiplier))
					if its[j] == Property.Hold:
						xsb.write(" 0 1 0 1 257")
						ysb.write(" 0 1 0 1 257")
					elif its[j] == Property.Linear:
						xsb.write(" 0 1 0 1 258")
						ysb.write(" 0 1 0 1 258")
					elif its[j] == Property.CatmullRom:
						xsb.write(" 0 1 0 1 515")
						ysb.write(" 0 1 0 1 515")
					else:
						xsb.write(" -")
						ysb.write(" -")
					xsb.write("}\n")
					ysb.write("}\n")
					if s.closed == False and list is cps:
						# There are arbitrary calculations here which may be appropriate as we're matching
						# arbitrary methods on the Nuke side.
						fsb.write(self.Tab(tabs+6) + "{" + str(self.AdjustFrameNumber(key_frame_list[j])) + " " + self.f2h(2 * fs[j][i] / 0.9))
						wsb.write(self.Tab(tabs+6) + "{" + str(self.AdjustFrameNumber(key_frame_list[j])) + " " + self.f2h(2 * (ws[j][i] + sws[j]) / 0.9))
						if its[j] == Property.Hold:
							fsb.write(" 0 1 0 1 257")
							wsb.write(" 0 1 0 1 257")
						elif its[j] == Property.Linear:
							fsb.write(" 0 1 0 1 258")
							wsb.write(" 0 1 0 1 258")
						elif its[j] == Property.CatmullRom:
							fsb.write(" 0 1 0 1 515")
							wsb.write(" 0 1 0 1 515")
						else:
							fsb.write(" -")
							wsb.write(" -")
						fsb.write("}\n")
						wsb.write("}\n")

				self.End(xsb, True, tabs=tabs+4)
				self.End(ysb, True, tabs=tabs+4)
				# Emit both X and Y from component strings.
				self.Begin(sb, True, tabs=tabs+3)
				if s.closed == False and list is cps:
					self.End(wsb, True, tabs=tabs+5)
					self.End(fsb, True, tabs=tabs+5)
					sb.write(self.Tab(tabs+4) + "{a\n")
					sb.write(fsb.getvalue())
					sb.write(wsb.getvalue())
					self.End(sb, True, tabs=tabs+4)
				# Here is X
				sb.write(self.Tab(tabs+4) + xsb.getvalue())
				# Here is Y
				sb.write(self.Tab(tabs+4) + ysb.getvalue())
				# End combined.
				self.End(sb, True, tabs=tabs+3)
		self.End(sb, True, tabs=tabs+2)
		self.End(sb, True, tabs=tabs+1)

	def BSplinePath(self, s, sb, feather=False, tabs=0):
		# Begin the inner cc
		self.Begin(sb, tabs=tabs)
		sb.write("cc\n")
		t = tabs + 1
		sb.write(self.Tab(t) + "{f 8192}\n")
		path = s['path']
		number_of_points = len(path.getValue(path.keys[0]).points)
		key_frame_list = self.AdjustedKeyFrameList(s['path'])
		actual_key_frames = self.BuildActualKeyFrameList(path)
		it = [None] * len(key_frame_list)

		# Begin PX
		self.Begin(sb, tabs=t)
		t = t + 1
		sb.write("px\n")
		self.Begin(sb, tabs=t) # Begin key frame list
		for index in range(len(key_frame_list)):
			sb.write(self.f2h(self.AdjustFrameNumber(key_frame_list[index])))
			if index < len(key_frame_list) - 1:
				sb.write(" ")
			# While we are enumerating key frames, pick up and store interpolation types.
			it[index] = path.interpolation(self.ReturnActiveKeyIndex(actual_key_frames, key_frame_list[index]))

		self.End(sb, True) # End key frame list
		xs = [None] * number_of_points
		ys = [None] * number_of_points
		ts = [None] * number_of_points
		rs = [None] * number_of_points
		for point_index in range(number_of_points):
			xs[point_index] = []
			ys[point_index] = []
			ts[point_index] = []
			rs[point_index] = []

		for key_frame_index in range(len(key_frame_list)):
			key_time = key_frame_list[key_frame_index]
			points = path.getValue(key_time).points
			for point_index in range(number_of_points):
				# Interestingly, even though they're using our code, they store tension as the square root of our value.
				m = Matrix()
				if self.has_skew == False:
					m.scale(self.session_size[1], self.session_size[1])

				weight = math.sqrt(points[point_index][2])
				if feather == False:
					if self.fully_baked == True:
						m = s.parent.getTransform(key_time)
						if m == None:
							m = Matrix()
						m.scale(1.0 / self.session_pixel_aspect, 1)

					cp = m * points[point_index][0]
				else:
					if len(points[point_index]) == 3:
						cp = Point3D()
					else:
						#print points[point_index]
						cp = m * points[point_index][3]
						weight = math.sqrt(points[point_index][4])

				xs[point_index].append(cp.x)
				ys[point_index].append(cp.y)
				ts[point_index].append(weight)
				rs[point_index].append(points[point_index][1])

		for point_index in range(number_of_points):
			# Begin of one point's data - the outer "a t"
			self.Begin(sb, True, tabs=t)
			# begins inner "a t"
			t = t + 1
			self.Begin(sb, tabs=t)
			sb.write("a\n")
			t = t + 1
			sb.write(self.Tab(tabs=t) + "t\n")
			# Begin Tension
			self.Begin(sb, True, tabs=t)
			for key_frame_index in range(len(key_frame_list)):
				self.Begin(sb, tabs=t+1)
				sb.write(self.f2h(self.AdjustFrameNumber(key_frame_list[key_frame_index])) + " " + self.f2h(ts[point_index][key_frame_index]))
				self.End(sb, True)
			# End tension
			self.End(sb, True, tabs=t)
			t = t - 1

			t = t + 1
			sb.write(self.Tab(tabs=t) + "rp\n")
			# Begin Repeat
			self.Begin(sb, True, tabs=t)
			for key_frame_index in range(len(key_frame_list)):
				self.Begin(sb, tabs=t+1)
				sb.write(self.f2h(self.AdjustFrameNumber(key_frame_list[key_frame_index])) + " " + self.f2h(rs[point_index][key_frame_index]))
				self.End(sb, True)
			# End repeat
			self.End(sb, True, tabs=t)

			# What the hell is this?
			sb.write(self.Tab(tabs=t) + "te\n")
			t = t - 1
			# ends the inner "a t"
			self.End(sb, True, tabs=t)

			multiplier = 1
			if self.has_skew == True:
				multiplier = self.session_size[1]

			# Begin the x coordinates
			self.Begin(sb, True, tabs=t)
			for key_frame_index in range(len(key_frame_list)):
				self.Begin(sb, tabs=t+1)
				sb.write(self.f2h(xs[point_index][key_frame_index] * multiplier) + " ")
				sb.write("0 1 0 1 ")
				if it[key_frame_index] == Property.Hold or key_frame_index == len(key_frame_list) - 1:
					sb.write("257")
				elif it[key_frame_index] == Property.Linear:
					sb.write("258")
				else:
					sb.write("515")
				self.End(sb, True)

			self.End(sb, True, tabs=t)
			# End the x coordinates

			# Begin the y coordinates
			#self.Begin(sb, tabs=t)
			self.Begin(sb, True, tabs=t)
			for key_frame_index in range(len(key_frame_list)):
				self.Begin(sb, tabs=t+1)
				sb.write(self.f2h(ys[point_index][key_frame_index] * multiplier) + " ")
				sb.write("0 1 0 1 ")
				if it[key_frame_index] == Property.Hold or key_frame_index == len(key_frame_list) - 1:
					sb.write("257")
				elif it[key_frame_index] == Property.Linear:
					sb.write("258")
				else:
					sb.write("515")
				self.End(sb, True)

			# End the y coordinates
			self.End(sb, True, tabs=t)
			t = t - 1
			# End of one point's data - the outer "a t"
			self.End(sb, True, tabs=t)

		t = t - 1
		# End "px"
		self.End(sb, True, tabs=t)
		t = t - 1
		# End "cc"
		self.End(sb, True, tabs=t)

	def BSpline(self, s, sb, purity, tabs=0):
		self.Begin(sb, tabs=tabs)
		sb.write("curvegroup " + self.getLabel(s.label) + " 512 bspline\n")
		# begins outer cc
		self.Begin(sb, True, tabs=tabs+1)
		self.BSplinePath(s, sb, tabs=tabs+2)
		self.BSplinePath(s, sb, feather=True, tabs=tabs+2)
		# ends outer cc
		self.End(sb, True, tabs=tabs+1)
		self.ShapeSettings(s, sb, tabs=tabs+1)
		self.ShapeTransforms(s, sb, purity, tabs=tabs+1)
		# ends curvegroup
		self.End(sb, True, tabs=tabs)

	def Bezier(self, s, sb, purity, tabs=0, original_shape = None):
		self.Begin(sb, tabs=tabs)
		sb.write("curvegroup " + self.getLabel(s.label))
		# As the difference between open and closed shapes are the flag value
		# and, of course, which functions are called I'm absracting these here
		# and joining up at the bottom of the shape.
		if s.closed:
			sb.write(" 512 bezier\n")
			# begins outer cc
			self.Begin(sb, True, tabs=tabs+1)
			self.BezierPath(s, original_shape, sb, tabs=tabs+1)
			self.BezierPath(s, original_shape, sb, True, tabs=tabs+1)
		else:
			sb.write(" 1049088 bezier\n")
			# begins outer cc
			self.Begin(sb, True, tabs=tabs+1)
			self.BezierPath(s, original_shape, sb, tabs=tabs+1)
			sb.write("idem\n")
		# Both code paths sync up here.
		# ends outer cc
		self.End(sb, True, tabs=tabs+1)
		self.ShapeSettings(s, sb, tabs=tabs+1)
		if original_shape == None:
			self.ShapeTransforms(s, sb, purity, tabs=tabs+1)
		else:
			self.ShapeTransforms(original_shape, sb, purity, tabs=tabs+1)
		# ends curvegroup
		self.End(sb, True, tabs=tabs)

	#
	#	SHAPE ATTRIBUTES
	#

	def Eye(self, s, sb):
		sb.write(" view1 " + str(s.stream + 1) + " ")

	def FeatherFallOff(self, s, sb):
		sb.write(" ff 1 ft 0 ")

	def FillColor(self, s, sb):
		# In support of the 5/17 feature addition of user choice
		# of what channels to output to, we either choose 0 or
		# 1. True, the exact color could become a user choice in
		# the future.
		sb.write("r ")
		sb.write("1 " if self.render_four_channels else "0 ")
		sb.write("g ")
		sb.write("1 " if self.render_four_channels else "0 ")
		sb.write("b ")
		sb.write("1 " if self.render_four_channels else "0 ")

	def OutlineColor(self, s, sb):
		oc = s.property("outlineColor").getValue()
		sb.write("ro " + self.f2h(oc.r) + " ")
		sb.write("go " + self.f2h(oc.g) + " ")
		sb.write("bo " + self.f2h(oc.b) + " ")
		sb.write("ao " + self.f2h(oc.a))

	def ShapeVisibility(self, s, sb):
		sb.write(" vis " + ("1" if s.visible == True else "0"))

	def ShapeMotionBlur(self, s, sb):
		sb.write(" mbo " + ("1" if s['motionBlur'].getValue(0) == True else "0"))

	def ShapeInverted(self, s, sb):
		sb.write(" inv " + ("1" if s['invert'].getValue(0) == True else "0"))

	def ShapeBlendMode(self, s, sb):
		# Silhouette					Nuke ("bm")
		# Add		0					Plus		x40e00000	or their Over (null string)?
		# Subtract	1					Minus		x41400000
		# Multiply	2					Multiply	x40000000
		# XOR		3					Exclusion	x41600000
		# MAX		4					Max			1
		if s.blendMode == 0:
			# When blend mode is "over" Nuke outputs nothing.
			pass
		elif s.blendMode == 1:
			sb.write(" bm x41400000 ")
		elif s.blendMode == 2:
			sb.write(" bm x40000000 ")
		elif s.blendMode == 3:
			sb.write(" bm x41600000 ")
		elif s.blendMode == 4:
			sb.write(" bm 1 ")

	def Lifetime(self, s, sb):
		# If we're not to use the lifetime feature at all, simply return.
		if self.use_lifetime == False:
			return
		# In Nuke, a shape can live for the entire project or it can have a shorter
		# lifetime. In Silhouette, a user might elect to emulate this feature of Nuke
		# by using a shape only once - as defined by its opacity. For example, if the
		# shape begins at zero opacity, flips on (hold interpolation) to full on, then
		# flips off again, we use this to mean the "lifetime" intent.

		p = s['opacity']
		# This is a short circuit case. If the opacity is constant, the lifetime
		# can be set quickly. Note: I just thought about eliminating shapes completely
		# if their opacity is constant at 0. But I discounted this because the shape
		# might be used in an inverted fashion. Including such shapes cannot be wrong.
		if p.constant == True:
			sb.write(" ltn " + self.f2h(self.session_start_frame) + " ltm " + self.f2h(self.session_end_frame) + " ltt " + self.f2h(4) + " ")
			return

		# We are to attempt to use the feature. We can if, and only if, there are
		# no intermediate values in the opacity during the proposed lifetime. The
		# returned key_frame_list already accounts for any work ranges by forcing
		# the beginning and ending frames to be present.

		key_frame_list = self.AdjustedKeyFrameList(p)
		#print key_frame_list
		beginning_of_life = key_frame_list[0]
		#print "Beginning_of_life: " + str(beginning_of_life)
		end_of_life = key_frame_list[-1]
		#print "End_of_life: " + str(end_of_life)
		initial_value = p.getValue(beginning_of_life)
		#print "Initial_value: " + str(initial_value)

		# We are guaranteed that the values are not constant because of test of short circuit case.
		# If start at 1, there must be a keyframe at f where it goes to zero
		# If start at 0, there must be a keyframe where it goes to not zero

		for f in key_frame_list:
			value = p.getValue(f)
			#print "value at frame: " + str(f) + " is: " + str(value)
			# If anything except 0 or 1, we cannot use lifetime
			if value != math.floor(value):
				#print "taking short cut"
				return
			if initial_value == 100 and value == 0:
				end_of_life = f
				#print "breaking"
				break
			if initial_value == 0 and value == 100:
				beginning_of_life = f
				initial_value = 100
				#print "Frame: " + str(f) + " set beginning_of_life"
			#print "looping"

		#print beginning_of_life, end_of_life

		sb.write(" ltn " + self.f2h(self.AdjustFrameNumber(beginning_of_life)) + " ltm " + self.f2h(self.AdjustFrameNumber(end_of_life)) + " ltt " + self.f2h(4) + " ")

	def OverallStrokeWidth(self, s, sb, tabs=0):
		# This function handles the emission of open shape width. This has been
		# a confusing journey. Nuke supports width per point (also "osw") and a
		# stroke overall width. They are written seperately and formatted differently.
		# This function writes the overall stroke width and is a shape attribute.
		#
		# This value is definitely multipled into the per point stroke width PLUS there seems
		# to be a bug in Nuke which establishes a MINIMUM value - zero is not zero.
		t = tabs
		if s.closed == True:
			# This function is called always but used only for open shapes.
			return
		# Use a constant value of 1 for the shape overall stroke width. This will
		# be multipled into the per point width. Do all the math there.
		sb.write("osw {0} ".format(self.width_multiplier))

	def EndCaps(self, s, sb):
		if s.closed == True:
		# This function is always called but is used only on open shapes.
			return
		# Nuke 0 and 1 values are inverted from ours. I knowingly did not use the simpler
		# nuke = 1 - silhouette because I don't want a latent bug in the future if a third
		# endcap style is introduced.
		capstyle = 0
		if s.capStyle == 0:
			capstyle = 1
		elif s.capStyle == 1:
			capstyle = 0
		else:
			# The "impossible else" defined for defensive programming purposes.
			print("Unhandled capstyle of "	+ str(s.capStyle))
		# Silhouette only supports the same cap style on both ends. Nuke supports selecting
		# the cap style separately on either end.
		sb.write(" osbe " + str(capstyle) + " osee " + str(capstyle))

	def ShapeSettings(self, s, sb, tabs=0):
		t = tabs
		self.Begin(sb, tabs=t)
		sb.write("a ")
		self.OverallStrokeWidth(s, sb, tabs=t)
		self.ShapeBlendMode(s, sb)
		self.Lifetime(s, sb)
		self.FillColor(s, sb)
		self.OutlineColor(s, sb)
		self.ShapeVisibility(s, sb)
		self.ShapeMotionBlur(s, sb)
		self.ShapeInverted(s, sb)
		self.EndCaps(s, sb)
		self.FeatherFallOff(s, sb)
		self.Eye(s, sb)
		self.EmitAnySingleValuedParameter(s, sb, 'opacity', 'opc', tabs=t+1)
		# Nuke shape blur is faked with feathering, apparently. First, it means they
		# blur incorrectly. Second, it means the cannot do centered blurring. A blur
		# size is either positive or negative. If zero, there is no blur. We emit
		# a positve value for all but inner. Best we can do. We rule.
		inner_outer = 1
		if s.blurType == 1:
			inner_outer = -1
		self.EmitAnySingleValuedParameter(s, sb, 'blur', 'fx', tabs=tabs+1, m=(self.session_size[1] * inner_outer / self.session_pixel_aspect))
		self.EmitAnySingleValuedParameter(s, sb, 'blur', 'fy', tabs=tabs+1, m=(self.session_size[1] * inner_outer))
		sb.write("\n")
		self.End(sb, True, tabs=t)

	def ShapeTransforms(self, s, sb, purity, tabs=0):
		# All our transforms are housed in Nuke layers now. In previous versions of Nuke,
		# layers were nothing more than folders. Now, layers actually serve a Silhouette-like
		# purpose.
		#
		# And then again, Nuke sez no. Now "impure" shapes must have their own transforms.
		if purity == True and s.parent.type == "Layer":
			#print "Pure shape: " + s.label
			return
		#print "IMPURE shape: " + s.label
		self.EmitLayerTransforms(sb, s, tabs=tabs)

	def EmitShape(self, s, sb, tabs=0):
		# This is the shape type dispatcher. If the shape is not selected, simply return.
		# Otherwise decode which type the shape is and call the appropriate subfunction.
		# Note that X-splines are emitted as Beziers.
		if not s.selected:
			return False
			
		# won't work if we only have 1 point
		if s.numPoints == 1:
			return False

		#print "Shape output"
		purity = self.IsLayerPure(s)
		#print "Results of purity test: " + str(purity) + " has_skew: " + str(self.has_skew)		# 06/14/18 bug
		# Addison bug: Record whether or not the original shape has been converted to a Bezier.
		self.is_converted_shape = False
		if s.shapeType == Shape.Bezier:
			self.Bezier(s, sb, purity, tabs=tabs)
		elif (s.shapeType == Shape.Xspline) or (s.shapeType == Shape.Bspline and s.closed == False):
			self.is_converted_shape = True
			b = s.convertToBezier()
			self.Bezier(b, sb, purity, tabs=tabs, original_shape=s)
		elif s.shapeType == Shape.Bspline:
			self.BSpline(s, sb, purity, tabs=tabs)
		else:
			return False
		return True

	def EmitPoint2D(self, sb, p):
		sb.write(self.f2h(p.x) + " " + self.f2h(p.y))

	def PrepareMatrices(self, layer):
		matrices = [ Matrix() ] * int(self.session_work_range[1] - self.session_work_range[0] + 1)
		frame_index = 0
		#print str(self.has_skew)
		for f in range(int(self.session_work_range[0] - self.session_start_frame) - 1, int(self.session_work_range[1] - self.session_start_frame)):
			if self.has_skew == False and self.fully_baked == False:
				l = layer.getTransform(f + 1, False)
				if l == None:
					# If l is None, there is no transform (it is an identity).
					l = Matrix()
				
				l.setValue(0, 3, l.value(0, 3) * self.session_size[1])
				l.setValue(1, 3, l.value(1, 3) * self.session_size[1])

				matrices[frame_index] = l
				frame_index = frame_index + 1
			else:
				m = Matrix()
				m.scale(1, -1, 1)                                                                                                    # 2210
				l = layer.getTransform(f + 1, True)                                               	# 2214
				if (l == None):
					# print str(getframeinfo(currentframe()).lineno) + " Name: " + layer.label + " l is None" 									# 06/14/18
					l = Matrix()
				else:
					#print str(getframeinfo(currentframe()).lineno) + " Name: " + layer.label + " " + str(l.identity)							# 06/14/18
					pass
				m = m * l                                                                                                                       # 2214 (cont)
				m = self.DivideByW(m)                                                       	# 2216
				m = self.world_to_image_transform * m                                       	# 2219
				m.scale(1.0 / float(self.session_size[1]), 1.0 / float(self.session_size[1]))   # 2120
				matrices[frame_index] = m
				frame_index = frame_index + 1
		#print "---------"
		#print "returning"
		#print "---------"
		return matrices

	def EmitLayerTransforms(self, sb, layer, tabs=0):
		aspect = float(self.session_size[0]) / float(self.session_size[1]) / 2.0

		if isinstance(layer, Node):
			#print "Node output"
			m = Matrix()
			# Points passing through here are in expanded Silhouette space, as
			# they were written that way. This avoids a massive scale in the
			# nuke matrices - avoiding their crippling stupid UI bug which they
			# have known about for years and refuse to fix.
			#
			# Shapes in the root layer need the translation of a/2, h/2. This
			# would complete the world-to-image transform.

			if self.has_skew == False:
				m.translate(self.session_size[0]/2.0, self.session_size[1]/2.0)
				m.scale(1.0 / self.session_pixel_aspect, -1)
			
			if self.fully_baked == True:
				m = Matrix()
				m.translate(self.session_size[0] / 2.0, self.session_size[1] / 2.0)
				m.scale(1, -1)

			# After this, the origin of coordinate system is the center of
			# the IMAGE.

			self.Begin(sb, tabs=tabs)
			sb.write("t 0 0 0  0 0 0  0 0 0  1 1 1  0 0 0  0 0 0  0\n")

			for y in range(4):
				for x in range(4):
					self.Begin(sb, True, tabs=tabs+1)
					self.Begin(sb, tabs=tabs+2)
					v = m.value(y, x)
					sb.write(self.f2h(self.session_work_range[0]) + " " + self.f2h(v) + " - ")
					self.End(sb, True)
					self.End(sb, True, tabs=tabs+1)
			self.End(sb, True, tabs=tabs)
			return

		if self.has_skew:
			# Here comes the next kludge. Does this layer contain only shapes?
			# Optimization - also calling this function with an impure shape.
			if (layer.type == 'Layer') and (self.IsLayerPure(layer) == False):
					#print "MIXED LAYER " + layer.label
					return

		#print "Layer output"
		matrices = self.PrepareMatrices(layer)

		self.Begin(sb, tabs=tabs)
		sb.write("t 0 0 0  0 0 0  0 0 0  1 1 1  0 0 0  0 0 0  0\n")

		#print self.session_work_range[0], self.session_work_range[1]

		session_height = self.session_size[1]
		for y in range(4):
			for x in range(4):
				self.Begin(sb, True, tabs=tabs+1)
				for index in range(len(matrices)):
					m = Matrix()
					if self.fully_baked == False:
						m = matrices[index]
					self.Begin(sb, tabs=tabs+2)
					v = m.value(y, x)
					# this frame number seems to be wrong.
					sb.write(self.f2h(index + self.session_work_range[0]) + " " + self.f2h(v) + " - ")
					self.End(sb, True)
				self.End(sb, True, tabs=tabs+1)
		self.End(sb, True, tabs=tabs)

	def LayerProperties(self, sb, layer, tabs=0):
		# Nuke layers cannot be inverted so this will have to be addressed in a far more complicated way.
		# And the above comment doesn't indicate what they more complicated way is, so even though I wrote
		# that comment, I have no memory of what it means. Thanks, self.
		# Silhouette layers don't have motion blur controls but the node does.
		self.Begin(sb, tabs=tabs)
		sb.write("a ")
		sb.write("opc 1")
		sb.write(" vis " + "1" if layer.visible else "0")
		motion_blur = self.node.properties.get("motionBlur.enable", False)
		sb.write(" mbo " + ("1" if motion_blur else "0"))
		sb.write(" ft 1")

		if isinstance(layer, Layer):
			self.ShapeBlendMode(layer, sb)

		inner_outer = 1
		if layer != None:
			if isinstance(layer, Node) == False and layer.blurType == 1:
				inner_outer = -1
		# Why isn't this checking into git?
		if "blur" in layer.properties:
			self.EmitAnySingleValuedParameter(layer, sb, 'blur', 'fx', tabs=tabs, m=self.session_size[1] * inner_outer / self.session_pixel_aspect)
			self.EmitAnySingleValuedParameter(layer, sb, 'blur', 'fy', tabs=tabs, m=self.session_size[1] * inner_outer)

		self.End(sb, True, tabs=tabs)

	def AnimLayer(self, layer, parent_sb, tabs=0):
		sb = StringIO()
		self.Begin(sb, False, tabs=tabs)
		sb.write("layer " + self.getLabel(layer.label) + "\n")
		sb.write(self.Tab(tabs+1) + "{f 512}\n")
		self.EmitLayerTransforms(sb, layer, tabs=tabs+1)
		self.LayerProperties(sb, layer, tabs=tabs+1)
		selected_shapes_found = False

		for index in range(len(layer.children) - 1, -1, -1):
			c = layer.children[index]
			if isinstance(c, Layer):
				selected_shapes_found = self.AnimLayer(c, sb, tabs=tabs+1) or selected_shapes_found
			elif isinstance(c, Shape):
				selected_shapes_found = self.EmitShape(c, sb, tabs=tabs+1) or selected_shapes_found
		if selected_shapes_found == True:
			# Nuke seems to support only one note whereas Silhouette supports note per
			# object. This will have to be addressed some time later.
			self.End(sb, True, tabs=tabs)
			parent_sb.write(sb.getvalue())
		else:
			#print "Dumping Empty Layer"
			pass

		return selected_shapes_found

	def AnimTreeRoot(self, sb, tabs=0):
		#self.Begin(sb, True, tabs=tabs)
		self.AnimLayer(self.node, sb, tabs=tabs)
		#self.End(sb, True, tabs=tabs)

	# With respect to this function, there are preamble, AnimTreeRoot() then postamble.
	def Curves(self, sb, tabs=0):
		t = tabs
		sb.write(self.Tab(t) + "curves\n")
		# begin outer curves
		self.Begin(sb, False, tabs=t)
		# begin inner curves
		#########
		######### If there is a new line between the { and the {v, Nuke will CRASH - OR ANY SPACE AT ALL
		#########
		self.Begin(sb, False)
		self.VersionBlock(sb)
		self.EmitCurvesFlagBlock(sb, tabs=t+1)
		# begin n
		self.Begin(sb, tabs=t+1)
		sb.write("n\n")
		length_before = len(sb.getvalue())
		self.AnimTreeRoot(sb, tabs=t+2)
		length_after = len(sb.getvalue())
		# end n
		self.End(sb, True, tabs=t+1)
		# end inner curves
		self.End(sb, False, tabs=t)
		# end outer curves
		self.End(sb, True)
		return length_before != length_after


	def GetProjectName(self):
		# This function is used to fill in the project name if the user has enabled that
		# feature of the exporter. The string is returned up to the first '.'
		s = os.path.basename(activeProject().bundlePath)
		return s[:s.find('.')]

	def EmitRotoNode(self, sb):
		# The omnibus object in an exported file is the roto node. This corresponds to the node
		# used within Nuke to implement the shapes. There is a bit of boilerplate text which prepends
		# and appends the live data.
		sb.write("Roto ")
		self.Begin(sb, True)
		self.OutputBlock(sb)
		# The second argument in FormatBlock is a legacy.
		self.FormatBlock(sb, 0)
		# All the live data is added to the in-memory string buffer here. The return of the function
		# is True if there is anything worthwhile to say.
		return_value = self.Curves(sb, tabs=1)
		motion_blur = self.node.properties.get("motionBlur.enable", False)
		sb.write(self.Tab() + "motionblur_on " + ("true\n" if motion_blur else "false\n"))
		if "motionBlur.enable" in self.node.properties:
			if motion_blur:
				sb.write(self.Tab() + "motionblur_mode global\n")
			sb.write(self.Tab() + "motionblur " + str(self.node.properties["motionBlur.samples"].getValue()) + "\n")
			sb.write(self.Tab() + "global_motionblur " + str(self.node.properties["motionBlur.samples"].getValue()) + "\n")
			sb.write(self.Tab() + "motionblur_shutter " + str(self.node.properties["motionBlur.shutterAngle"].getValue() / 360.0) + "\n")
			sb.write(self.Tab() + "global_motionblur_shutter " + str(self.node.properties["motionBlur.shutterAngle"].getValue() / 360.0) + "\n")
			sb.write(self.Tab() + "motionblur_shutter_offset " + str(self.node.properties["motionBlur.shutterPhase"].getValue() / 360.0) + "\n")
			sb.write(self.Tab() + "global_motionblur_shutter_offset " + str(self.node.properties["motionBlur.shutterPhase"].getValue() / 360.0) + "\n")
			sb.write(self.Tab() + "motionblur_shutter_offset_type custom\n")
			sb.write(self.Tab() + "global_motionblur_shutter_offset_type custom\n")
			
		sb.write(self.Tab() + "name " + self.GetProjectName() + "\n")
		if self.include_project_path:
			sb.write(self.Tab() + "label \"" + activeProject().bundlePath + "\"\n")
		self.End(sb)
		return return_value

	def Export(self):
		self.Initialize()

		self.has_skew = self.SkewTermsPresent()

		# self.pretty_print may be 0 or 1. 0 disables pretty printing.
		self.pretty_print = 0
		if prefs[file_size_string] == LargerFiles:
			self.pretty_print = 1

		# Set various behaviors. If we are operating like an exporter, then use prefs. 
		# If we are not, hard code the values.
		if function_as_exporter:
			self.print_in_hex = prefs[file_size_string] == SmallerFiles
			self.fully_baked = prefs[fully_baked_string]
			self.include_project_path = prefs[include_project_path_string]
			self.use_lifetime = prefs[use_lifetime_string]
			self.render_four_channels = prefs[render_four_channels_string]
		else:
			self.print_in_hex = False
			self.fully_baked = False
			self.include_project_path = False
			self.use_lifetime = False
			self.render_four_channels = False

		sb = StringIO()
		self.EmitPreamble(sb)
		return_value = self.EmitRotoNode(sb)
		sb.write("\n")
		
		self.file.write(sb.getvalue())
		return return_value

	def AnyShapesSelected(self):
		# Collect and enumerate all "selected" objects. These may include layers, trackers and more so
		# the list is enumerated and, at the first "Shape", a true value is returned. If the list of
		# selected objects does not include a shape, an answer of False is returned, which will halt
		# the export.
		s = selection()
		for o in s:
			if o.type == "Shape":
				return True
		return False

	#
	#	MAIN ENTRY POINT
	#

	def execute(self, path):
		# This is the main entry point for export. It bails if there are no shapes are selected
		# or the output file fails to open for writing. If all successful, the actual export is
		# attempted.
		if self.AnyShapesSelected() == False:
			displayError("No shapes selected.", "Nuke exporter")
			return False
		try:
			self.file = open(path, "w")
		except:
			displayError("File: " + path + " failed to open for writing.", "Nuke exporter")
			return
		print("....................",path)
		export_data = self.Export()
		print(export_data)
		self.file.close()
		return True

	'''	Look for any skew terms in THE ENTIRE EXPORT. This is
		costly but required due to an inability to match transforms
		such as thos produced by mocha when its perspective mode
		is enabled.

		Algorithm:
			For each selected shape:
				Get its parent layer.
				If Layer is None:
					continue
				For every frame:
					Get the transform.
					On first skew term, return True
	'''
	def HasASkewTerm(self, s):
		return True

	def SkewTermsPresent(self):
		selected_shapes = selection()
		for s in selected_shapes:
			if s.type == "Shape" and self.HasASkewTerm(s):
				return True
		return False

# The bool function_as_exporter can be considered a debugging flag. The true case is the production value.

def main_exe(path= None):
	exporter = NukeExporterV3()
	exporter.execute(path)

