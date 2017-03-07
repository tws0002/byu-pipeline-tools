# Author: Ben DeMann

import sys
import os
import traceback
import json
import random
from PyQt4 import QtGui, QtCore

WINDOW_WIDTH = 400
WINDOW_HEIGHT = 200
    
class QuoteWindow(QtGui.QWidget):

    finished = QtCore.pyqtSignal()

    def __init__(self):
        super(QuoteWindow, self).__init__()
        quote_json = file(os.environ['BYU_TOOLS_DIR'] + '/byugui/assets/inspire-quotes.json')
        self.quoteData = json.loads(quote_json.read())['quotes']
        self.initUI()

    def initUI(self):
        #define gui elements
        self.setGeometry(300,300,WINDOW_WIDTH,WINDOW_HEIGHT)
        self.setWindowTitle('Inspirational Quotes')
        
        self.quote = QtGui.QTextEdit()
        self.quote.setReadOnly(True)
        self.img = QtGui.QLabel()
        self.returnBtn = QtGui.QPushButton('Return to Work')
        self.returnBtn.setEnabled(True)
        self.moreBtn = QtGui.QPushButton('Be More Inspired')
        self.moreBtn.setEnabled(True)
        
        self.returnBtn.clicked.connect(self.close)
	self.moreBtn.clicked.connect(self.populateQuote)

        self.populateQuote()
        
        #set gui layout
        self.grid = QtGui.QGridLayout(self)
        self.setLayout(self.grid)
  
        self.grid.addWidget(self.img, 0, 0)
        self.grid.addWidget(self.quote, 0, 1)
        self.grid.addWidget(self.moreBtn, 1, 0)
        self.grid.addWidget(self.returnBtn, 1, 1)
        
        self.show()
    
    def getQuote(self):
        index = random.randrange(0,len(self.quoteData))
        return self.quoteData[index]

    def populateQuote(self):
	quoteInfo = self.getQuote()

        self.quote.setText(quoteInfo["quote"] + "\n\t-" + quoteInfo["author"])# + "\n\n\n Submitted by: " + quoteInfo["contributor"])
        pixmap = QtGui.QPixmap(os.environ['BYU_TOOLS_DIR'] + '/byugui/assets/images/' + quoteInfo['image'])
        scaled = pixmap.scaledToWidth(self.size().width()/2)
        print scaled
        print "\n" + str(self.size()) + " " + str(self.size().width())
        self.img.setPixmap(scaled)

    def closeEvent(self, event):
        self.finished.emit()
        event.accept()

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    ex = PublishWindow(os.environ['BYU_TOOLS_DIR'] + '/byu_gui/test.txt', app)
    sys.exit(app.exec_())
