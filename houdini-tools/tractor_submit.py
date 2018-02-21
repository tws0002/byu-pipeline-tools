from PySide2 import QtGui, QtWidgets, QtCore
import datetime
import os
import re
import shutil
import hou
from byugui import message_gui
from byugui.assemble_gui import AssembleWindow
from byuam import Project, Environment
import tractor.api.author as author

# Creates the dialog box
class ExportDialog(QtWidgets.QWidget):

	finished = QtCore.Signal()

	def __init__(self, parent, renderNodes):
		super(ExportDialog, self).__init__()
		self.parent = parent
		self.project = Project()
		self.environment = Environment()
		self.renderNodes = renderNodes
		self.initUI()

	def initUI(self):
		# Window layout
		self.setFixedSize(360, 420)
		self.setWindowTitle('Confirm Export')
		main_layout = QtWidgets.QVBoxLayout()
		self.setLayout(main_layout)

		# Job Name Input Widget
		self.jobName = QtWidgets.QLineEdit('JobName')
		self.jobName.selectAll()
		name_layout = QtWidgets.QHBoxLayout()
		name_layout.addWidget(QtWidgets.QLabel('Job Name:'))
		name_layout.addWidget(self.jobName)
		main_layout.addLayout(name_layout)

		# Priority and Start Time
		# Priority
		self.priority = QtWidgets.QComboBox()
		priority_opt = ['Very Low', 'Low', 'Medium', 'High', 'Very High']
		for opt in priority_opt:
			self.priority.addItem(opt)
		self.priority.setCurrentIndex(2)
		# Begin time
		self.delay = QtWidgets.QComboBox()
		delay_opts = ['Immediate', 'Manual', 'Delayed']
		for opt in delay_opts:
			self.delay.addItem(opt)
		self.delay.currentIndexChanged.connect(self.delaytime)
		# Combo box options layout
		opts_layout = QtWidgets.QHBoxLayout()
		opts_layout.addWidget(QtWidgets.QLabel('Priority:'))
		opts_layout.addWidget(self.priority)
		opts_layout.addWidget(QtWidgets.QLabel('Begin:'))
		opts_layout.addWidget(self.delay)
		opts_layout.addStretch()
		main_layout.addLayout(opts_layout)

		# Time-frame selection for delayed jobs
		self.delay_time = QtWidgets.QLineEdit('5')
		self.delay_unit = QtWidgets.QComboBox()
		delay_unit_opts = ['mins','hours','days']
		for opt in delay_unit_opts:
			self.delay_unit.addItem(opt)
		self.delay_unit.setCurrentIndex(0)
		# Delay time layout
		self.delay_layout = QtWidgets.QHBoxLayout()
		self.delay_layout.addWidget(QtWidgets.QLabel('Delay time:'))
		self.delay_layout.addWidget(self.delay_time)
		self.delay_layout.addWidget(self.delay_unit)
		self.delay_layout.addStretch()
		self.delaytime(0)
		main_layout.addLayout(self.delay_layout)

		# Mantra node selection list
		self.select = QtWidgets.QListWidget()
		self.select.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
		for node in self.renderNodes:
			item = QtWidgets.QListWidgetItem(node.name())
			self.select.addItem(item)
			# must come after adding to widget
			item.setSelected(True)
		main_layout.addWidget(self.select)

		# Buttons
		self.export_btn = QtWidgets.QPushButton('Export')
		self.export_btn.clicked.connect(self.export)
		self.cancel_btn = QtWidgets.QPushButton('Cancel')
		self.cancel_btn.clicked.connect(self.close)
		btn_layout = QtWidgets.QHBoxLayout()
		btn_layout.addWidget(self.cancel_btn)
		btn_layout.addWidget(self.export_btn)
		main_layout.addLayout(btn_layout)


	# Show/Hide the delay-time options
	def delaytime(self, index):
		i = 0
		items = self.delay_layout.count()
		while i<items:
			 item = self.delay_layout.itemAt(i).widget()
			 if item:
				 item.setVisible(index == 2)
			 i = i+1

	# Export selected mantra nodes for rendering
	def export(self):
		self.close()

		# Get user, project, and time info so we can make a temp folder
		user = self.environment.get_current_username()
		projectName = self.project.get_name().lower()
		time_now = datetime.datetime.now()

		#Make a temp folder for the rib files based on the user and the current time
		ribDir = self.project.get_project_dir()+'/ribs/'+user+'_'+time_now.strftime('%m%d%y_%H%M%S')
		print 'ribDir', ribDir, ' renderNodes size: ', len(self.renderNodes)
		os.makedirs(ribDir)

		# Sanitize job title
		title = re.sub(r'[{}"\']', '', str(self.jobName.text())).strip(' \t\n\r')
		if len(title) == 0:
			title = self.empty_text

		# This job we send to tractor
		job = author.Job()
		job.title = title + ' python job'
		job.priority = self.priority.currentIndex()
		path = '/opt/pixar/RenderManProServer-21.5/bin/'
		job.envkey = ['setenv PATH=' + path + ' RMANTREE=/opt/pixar/RenderManProServer-21.5']
		job.service = 'PixarRender'
		job.comment = 'Spooled by ' + user

		# Loop through each frame of our nodes and create frame tasks and append it to the job script
		for index, node in enumerate(self.renderNodes):
			# Make sure this node was selected for export
			print node.name();
			if self.select.item(index).isSelected():
				name = node.name()
				frameRange = getFrameRange(node)

				#TODO it seems a little weird that we are returning the old mode so that we can set it back later. Maybe there is a better way to do this... at the very least I should make it consistant with the code that changes it back down bellow.
				old = setUpRibOutput(name, node, ribDir)
				oldOutputMode = old[0]
				useExpression = old[1]
				oldDiskFile = old[2]

				print "We are staring the prerender"
				job.addChild(createPreRenderTask(name, node, frameRange))
				print "We are starting the render"
				job.addChild(createRenderTask(name, ribDir, frameRange))

				# Restore rib output
				node.parm('soho_outputmode').set(oldOutputMode)
				if useExpression:
					node.parm('soho_diskfile').setExpression(oldDiskFile)
				else:
					node.parm('soho_diskfile').set(oldDiskFile)

		command = author.Command()
		command.argv = ['rm', '-rf', ribDir]
		job.addCleanup(command)

		# print 'This is the new job script \n', job.asTcl()

		# Attempt to spool job, with the option to keep trying
		choice = True
		while choice:
			try:
				job.spool()
				message_gui.info('Job sent to Tractor!')
				break
			except Exception as err:
				choice = message_gui.yes_or_no('We ran into this problem while spooling the job:\nWould you like to try again?', details=str(err), title='Continue?')
		#Cleanup ifd files, if they didn't want to retry
		if not choice:
			shutil.rmtree(ribDir)

def getFrameRange(node):
	validFrameRange = node.parm('trange').eval()
	if validFrameRange == 0:
		start = int(hou.frame())
		end = int(hou.frame())
		step = 1
	else:
		start = int(node.parm('f1').eval())
		end = int(node.parm('f2').eval())
		step = int(node.parm('f3').eval())
	return FrameRange(start, end, step)

class FrameRange():
	def __init__(self, start, end, step):
		self.start = start
		self.end = end
		self.step = step

def setUpRibOutput(name, node, ribDir):
	oldOutputMode = node.parm('rib_outputmode').eval()
	try:
		oldDiskFile = node.parm('soho_diskfile').expression()
		useExpression = True
		print 'We are getting rid of expressiion'
	except:
		oldDiskFile = node.parm('soho_diskfile').eval()
		useExpression = False
		print 'we didn\'t get rid of them'
	# Activate rib output
	node.parm('rib_outputmode').set(True)
	node.parm('soho_diskfile').deleteAllKeyframes()
	node.parm('soho_diskfile').set(ribDir+('/%s_$F04.rib' % name))
	return [oldOutputMode, useExpression, oldDiskFile]

def createPreRenderTask(name, renderNode, frameRange):
	return createTask(saveHipRenderCopy(), name, renderNode, frameRange)

def saveHipRenderCopy():
	import shutil
	src = hou.hipFile.path()
	proj = Project()
	projDir = proj.get_project_dir()
	renderCache = os.path.join(projDir, 'renderCache')
	if not os.path.exists(renderCache):
		os.makedirs(renderCache)
	dstFile = 'preRender' + hou.hipFile.basename()
	dst = os.path.join(renderCache, dstFile)
	shutil.copyfile(src, dst)
	return dst

def createRenderTask(name, ribDir, fRange):
	task = author.Task()
	task.title = '%s [%d-%d]' % (name, fRange.start, fRange.end)
	# Loop through every frame in framerange
	for frame in range(fRange.start, fRange.end+1, fRange.step):
		subtask = author.Task()
		subtask.title = 'Frame %04d' % (frame)
		ribFile = '%s/%s_%04d.rib' % (ribDir, name, frame)
		print 'Here is the rib file ', ribFile

		# Commands for Debugging
		cmdPATH = author.Command()
		cmdPATH.argv = ['echo', '${PATH}']
		cmdRMANTREE = author.Command()
		cmdRMANTREE.argv = ['echo', '${RMANTREE}']
		printenv = author.Command()
		printenv.argv = ['printenv']
		# subtask.addCommand(cmdPATH)
		# subtask.addCommand(cmdRMANTREE)
		# subtask.addCommand(printenv)

		# Real Commands
		command = author.Command()
		command.argv = ['prman', '-progress', ribFile]
		command.service = 'PixarRender'
		subtask.addCommand(command)
		task.addChild(subtask)
	return task

def createTask(preRenderFile, name, renderNode, fRange):
	preRenderTask = author.Task()
	preRenderTask.title = 'preRender-%s [%d-%d]' % (name, fRange.start, fRange.end)
	for frame in range(fRange.start, fRange.end+1, fRange.step):
		subtask = author.Task()
		subtask.title = 'PreRender Frame %04d' % (frame)

		command = author.Command()
		command.argv = ['sh', 'houdiniInstructions.sh', fRange.start, fRange.end, renderNode, preRenderFile]
		# command.argv = ['/opt/hfs.current/bin/hbatch', preRenderFile, scriptFile]
		subtask.addCommand(command)
		preRenderTask.addChild(subtask)
	return preRenderTask

def go(renderNodes):
	# Then show the dialog
	global dialog
	dialog = ExportDialog(hou.ui.mainQtWindow(), renderNodes)
	dialog.show()
