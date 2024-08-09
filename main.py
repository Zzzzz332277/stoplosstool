# -*- coding: utf-8 -*-
import functools
from datetime import date, timedelta

import matplotlib.pyplot as plt
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidget, QGraphicsWidget, QGraphicsView, QGraphicsScene, \
    QMenu
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5 import QtCore, QtGui, QtWidgets

from qtwindow import Ui_MainWindow
import pandas as pd

from talib import EMA
from futu import *

import futuoder
import stoploss

class Signal(QObject):
    text_update = pyqtSignal(str)

    def write(self, text):
        self.text_update.emit(str(text))
        # loop = QEventLoop()
        # QTimer.singleShot(100, loop.quit)
        # loop.exec_()
        QApplication.processEvents()

class MyMainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, MainWindow,parent=None):
        super(MyMainWindow, self).__init__(parent)
        self.setupUi(MainWindow)

        #图像显示，在graphicview中添加scene
        #self.scene = QGraphicsScene(self)
        #self.graphicsView.setScene(self.scene)

        #############################
        #self.pushButton.clicked.connect(self.ZtradeUS)
        #显示K线的逻辑
        #self.showCandle.clicked.connect(self.ShowCandle)
        #传递table值进去
        self.pushButtonStart.clicked.connect(self.InitProgram)
        self.pushButton_setorder.clicked.connect(self.SetOrderMainWindow)

        #self.pushButtonGetOrder.clicked.connect(self.GetOrder)

        '''
        self.tableWidget_backstepema.itemDoubleClicked.connect(functools.partial(self.ShowCandle, 0))
        self.tableWidget_EmaDiffusion.itemDoubleClicked.connect(functools.partial(self.ShowCandle, 1))
        self.tableWidget_EMAUpCross.itemDoubleClicked.connect(functools.partial(self.ShowCandle, 2))
        self.tableWidget_MoneyFlow.itemDoubleClicked.connect(functools.partial(self.ShowCandle, 3))
        self.tableWidget_EMA5BottomArc.itemDoubleClicked.connect(functools.partial(self.ShowCandle, 4))
        self.tableWidget_EMA5TOPArc.itemDoubleClicked.connect(functools.partial(self.ShowCandle, 5))
        self.tableWidget_EMADownCross.itemDoubleClicked.connect(functools.partial(self.ShowCandle, 6))
        self.tableWidget_MACDBottomArc.itemDoubleClicked.connect(functools.partial(self.ShowCandle, 7))
        self.tableWidget_MACDTopArc.itemDoubleClicked.connect(functools.partial(self.ShowCandle, 8))
        
    

        self.tableWidget_backstepema.customContextMenuRequested.connect(functools.partial(self.GenerateMenu,0))
        self.tableWidget_EmaDiffusion.customContextMenuRequested.connect(functools.partial(self.GenerateMenu,1))
        self.tableWidget_EMAUpCross.customContextMenuRequested.connect(functools.partial(self.GenerateMenu,2))
        self.tableWidget_MoneyFlow.customContextMenuRequested.connect(functools.partial(self.GenerateMenu,3))
        self.tableWidget_EMA5BottomArc.customContextMenuRequested.connect(functools.partial(self.GenerateMenu,4))
        self.tableWidget_EMA5TOPArc.customContextMenuRequested.connect(functools.partial(self.GenerateMenu,5))
        self.tableWidget_EMADownCross.customContextMenuRequested.connect(functools.partial(self.GenerateMenu,6))
        self.tableWidget_MACDBottomArc.customContextMenuRequested.connect(functools.partial(self.GenerateMenu, 7))
        self.tableWidget_MACDTopArc.customContextMenuRequested.connect(functools.partial(self.GenerateMenu, 8))
        '''
        #self.pushButton.clicked.connect(self.UpdateTable)
        sys.stdout = Signal()

        sys.stdout.text_update.connect(self.updatetext)

        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def updatetext(self, text):
        """
            更新textBrowser
        """
        cursor = self.textBrowser.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.textBrowser.append(text)
        self.textBrowser.setTextCursor(cursor)
        self.textBrowser.ensureCursorVisible()
    #def StartAnalyze(self):
    #    zmain.ZtradeUS()

    def SetOrderMainWindow(self):
        code=self.textEdit_code.toPlainText()
        qty=float(self.textEdit_qty.toPlainText())

        #根据下拉菜单判断方向
        side=self.DirectionSelction.currentText()
        if side== 'BUY':
            trd_side=TrdSide.BUY
        else:
            trd_side=TrdSide.SELL

        aux_price=float(self.textEdit_auxprice.toPlainText())
        price=float(self.textEdit_bidprice.toPlainText())
        order_type=OrderType.STOP_LIMIT
        #ordertype写死
        print('执行下单')
        stp=stoploss.StopLossTool()
        stp.SetOrderStopLoss(code=code,qty=qty,trd_side=trd_side,order_type=order_type,aux_price=aux_price,price=price)



    def GetHold(self):
        """
            更新textBrowser
        """
        futu=futuoder.Zfutu()
        holdData=futu.GetHoldStock()
        table=self.tableWidget_hold
        for i in range(0,holdData.shape[0]):
            #持仓信息
            code=holdData['code'].iloc[i]
            name=holdData['stock_name'].iloc[i]
            quanty=holdData['qty'].iloc[i]

            row_count = table.rowCount()  # 返回当前行数(尾部)
            table.insertRow(row_count)  # 尾部插入一行
            table.setItem(row_count - 1, 0, QtWidgets.QTableWidgetItem(str(code)))
            table.setItem(row_count - 1, 1, QtWidgets.QTableWidgetItem(str(name)))
            table.setItem(row_count - 1, 2, QtWidgets.QTableWidgetItem(str(quanty)))




    def GetOrder(self):
        """
            更新textBrowser
        """
        futu=futuoder.Zfutu()
        OrderData=futu.GetOrderList()
        table=self.tableWidget_order
        for i in range(0,OrderData.shape[0]):
            #持仓信息
            code=OrderData['code'].iloc[i]
            name=OrderData['stock_name'].iloc[i]
            quanty=OrderData['qty'].iloc[i]
            direction=OrderData['trd_side'].iloc[i]
            type=OrderData['order_type'].iloc[i]
            status=OrderData['order_status'].iloc[i]
            bidPrice=OrderData['price'].iloc[i]
            auxPrice=OrderData['aux_price'].iloc[i]


            row_count = table.rowCount()  # 返回当前行数(尾部)
            table.insertRow(row_count)  # 尾部插入一行
            table.setItem(row_count - 1, 0, QtWidgets.QTableWidgetItem(str(code)))
            table.setItem(row_count - 1, 1, QtWidgets.QTableWidgetItem(str(name)))
            table.setItem(row_count - 1, 2, QtWidgets.QTableWidgetItem(str(direction)))
            table.setItem(row_count - 1, 3, QtWidgets.QTableWidgetItem(str(type)))
            table.setItem(row_count - 1, 4, QtWidgets.QTableWidgetItem(str(status)))
            table.setItem(row_count - 1, 5, QtWidgets.QTableWidgetItem(str(quanty)))
            table.setItem(row_count - 1, 6, QtWidgets.QTableWidgetItem(str(bidPrice)))
            table.setItem(row_count - 1, 7, QtWidgets.QTableWidgetItem(str(auxPrice)))

            '''
            table.setItem(row_count - 1, 1, QtWidgets.QTableWidgetItem(str(code)))
            table.setItem(row_count - 1, 2, QtWidgets.QTableWidgetItem(str(close)))
            table.setItem(row_count - 1, 3, QtWidgets.QTableWidgetItem(changePctStr))
            table.setItem(row_count - 1, 4, QtWidgets.QTableWidgetItem(str(volume)))
            table.setItem(row_count - 1, 5, QtWidgets.QTableWidgetItem(str(vol60)))
            table.setItem(row_count - 1, 6, QtWidgets.QTableWidgetItem(CorrelationUS))
            '''

    def InitProgram(self):
        #声明一个stoplosstool类为成员，所有止损相关操作在类中进行，更好封装
        self.stp=stoploss.StopLossTool()
        self.stp.InitProgram()

        self.UpdateOrderTable(self.stp.orderListDataframe)
        self.UpdateHoldTable()
        self.SubscribeRealTimePrice(self.stp.holdStockList)
        #time.sleep(35)  # 设置脚本接收 OpenD 的推送持续时间为15秒
        #while 1 :
        #    pass

    def UpdateOrderTable(self,orderListDF):
        table=self.tableWidget_order
        for i in range(0,orderListDF.shape[0]):
            #持仓信息
            code=orderListDF['CODE'].iloc[i]
            name=orderListDF['NAME'].iloc[i]
            quanty=orderListDF['QUANTITY'].iloc[i]
            direction=orderListDF['DIRECTION'].iloc[i]
            type=orderListDF['TYPE'].iloc[i]
            status=orderListDF['STATE'].iloc[i]
            bidPrice=orderListDF['BIDPRICE'].iloc[i]
            auxPrice=orderListDF['AUXPRICE'].iloc[i]
            setDate=orderListDF['SETDATE'].iloc[i]
            operationDate=orderListDF['OPERATIONDATE'].iloc[i]


            row_count = table.rowCount()  # 返回当前行数(尾部)
            table.insertRow(row_count)  # 尾部插入一行
            table.setItem(row_count, 0, QtWidgets.QTableWidgetItem(str(code)))
            table.setItem(row_count , 1, QtWidgets.QTableWidgetItem(str(name)))
            table.setItem(row_count, 2, QtWidgets.QTableWidgetItem(str(direction)))
            table.setItem(row_count, 3, QtWidgets.QTableWidgetItem(str(type)))
            table.setItem(row_count, 4, QtWidgets.QTableWidgetItem(str(status)))
            table.setItem(row_count, 5, QtWidgets.QTableWidgetItem(str(quanty)))
            table.setItem(row_count, 6, QtWidgets.QTableWidgetItem(str(bidPrice)))
            table.setItem(row_count, 7, QtWidgets.QTableWidgetItem(str(auxPrice)))
            table.setItem(row_count, 8, QtWidgets.QTableWidgetItem(str(setDate)))
            table.setItem(row_count, 9, QtWidgets.QTableWidgetItem(str(operationDate)))

    def UpdateHoldTable(self):
        holdStockList=self.stp.holdStockList
        holdListDF=self.stp.holdStockDataframe
        stateDF=self.stp.StateDataframe
        table=self.tableWidget_hold
        for i in range(0,len(holdStockList)):
            holdStock=holdStockList[i]

            #持仓信息
            code=holdStock.code
            name=holdStock.name
            quanty=holdStock.qty
            hasOrder=holdStock.hasOrder
            direction=holdStock.stopLossDirection
            stopLossPrice=holdStock.stopLossPrice
            state=holdStock.stopLossState
            row_count = table.rowCount()  # 返回当前行数(尾部)
            table.insertRow(row_count)  # 尾部插入一行
            table.setItem(row_count , 0, QtWidgets.QTableWidgetItem(str(code)))
            table.setItem(row_count , 1, QtWidgets.QTableWidgetItem(str(name)))
            table.setItem(row_count , 2, QtWidgets.QTableWidgetItem(str(quanty)))
            table.setItem(row_count , 4, QtWidgets.QTableWidgetItem(str(hasOrder)))
            table.setItem(row_count , 5, QtWidgets.QTableWidgetItem(str(direction)))
            table.setItem(row_count , 6, QtWidgets.QTableWidgetItem(str(stopLossPrice)))
            table.setItem(row_count , 7, QtWidgets.QTableWidgetItem(str(state)))




    #获取实时报价并显示
    def SubscribeRealTimePrice(self,holdStockList):
        #获取订阅名单,从类列表里获取
        subscribeList=[]
        for i in range(0,len(holdStockList)):
            subscribeList.append(holdStockList[i].code)
        handler = futuoder.StockQuoteTest(self.RenewRealTimePrice)
        futuoder.quote_ctx.set_handler(handler)  # 设置实时报价回调
        ret, data = futuoder.quote_ctx.subscribe(subscribeList, [SubType.QUOTE])  # 订阅实时报价类型，OpenD 开始持续收到服务器的推送
        if ret == RET_OK:
            print(data)
        else:
            print('error:', data)
        #time.sleep(15)  # 设置脚本接收 OpenD 的推送持续时间为15秒

    #接收到推送的回调处理逻辑
    def RenewRealTimePrice(self,pushdata):
        table = self.tableWidget_hold
        holdCodeList = []
        for i in range(0, len(self.stp.holdStockList)):
            holdCodeList.append(self.stp.holdStockList[i].code)

        code= pushdata['code'].iloc[0]
        #找到在dataframe中对应位置
        pos=holdCodeList.index(code)
        lastprice = pushdata['last_price'].iloc[0]
        table.setItem(pos, 3, QtWidgets.QTableWidgetItem(str(lastprice)))

        '''
        #更新数据并进行判断
        stateDF=self.stp.StateDataframe
        #是否有止损
        if stateDF['HASORDER'].iloc[pos] == True:
            if lastprice<
        '''

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)

    MainWindow = QtWidgets.QMainWindow()
    myWin = MyMainWindow(MainWindow)
    MainWindow.show()

    sys.exit(app.exec_())