from byugui.reference_gui import ReferenceWindow
from byuam.environment import Department
from byuam import byuutil
import pymel.core as pm
from PySide2 import QtWidgets
import maya.OpenMayaUI as omu
import os

maya_reference_dialog = None

def maya_main_window():
	"""Return Maya's main window"""
	for obj in QtWidgets.qApp.topLevelWidgets():
		if obj.objectName() == 'MayaWindow':
			return obj
	raise RuntimeError('Could not find MayaWindow instance')

def post_reference(dialog, useNamespace=False):
	file_paths = dialog.filePaths
	done = dialog.done
	isReferenced = dialog.reference

	print "The filePaths are", file_paths
	print "The reference is", isReferenced
	reference(file_paths, isReferenced=isReferenced, useNamespace=True)

def reference(filePaths, isReferenced=True, useNamespace=False):
	if filePaths is not None and isReferenced:
		empty = []
		for path in filePaths:
			print "This is the path that we are working with", path
			if os.path.exists(path):
				print path, "exists"
				#TODO do we want to add multiple references in with different namespaces? You know to get rid of conflicts? Or is our current system for handling that good enough?
				# pm.system.createReference(path, namespace="HelloWorld1")
				basename = os.path.basename(path)
				millis = byuutil.timestampThisYear()
				refNamespace = basename + str(millis)
				print basename
				print str(millis)
				print refNamespace
				if useNamespace:
					pm.system.createReference(path, namespace=refNamespace)
				else:
					pm.system.createReference(path)
			else:
				print path, "don't exist"
				empty.append(path)

		if empty:
			empty_str = '\n'.join(empty)
			error_dialog = QtWidgets.QErrorMessage(maya_main_window())
			error_dialog.showMessage("The following elements are empty. Nothing has been published to them, so they can't be referenced.\n"+empty_str)
	# if not done:
	#	 go()

def go(useNamespace=False):
	parent = maya_main_window()
	# filePath = pm.file(q=True, sceneName=True)
	filePath = pm.system.sceneName()
	maya_reference_dialog = ReferenceWindow(parent, filePath, [Department.MODEL, Department.RIG], Department.CYLCES)
	maya_reference_dialog.finished.connect(lambda: post_reference(maya_reference_dialog, useNamespace=useNamespace))
