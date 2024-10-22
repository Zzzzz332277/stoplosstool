# -*- coding: utf-8 -*-
import functools
from datetime import date, timedelta
import multiprocessing
import time
import os
import matplotlib.pyplot as plt
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidget, QGraphicsWidget, QGraphicsView, QGraphicsScene, \
    QMenu
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

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
        self.pushButton_cancelOrder.clicked.connect(self.CancelOrder)
        self.pushButton_setorder.clicked.connect(self.SetOrderMainWindow)
        self.pushButton_quickSet.clicked.connect(self.quickSet)

        #self.pushButtonGetOrder.clicked.connect(self.GetOrder)
        #self.tableWidget_hold.setContextMenuPolicy(Qt.DefaultContextMenu)

        #self.tableWidget_hold.customContextMenuRequested.connect(functools.partial(self.GenerateMenu,0))


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

        self.UpdateOrderTable()
        self.UpdateHoldTable()

        #报价推送以及订单状态回调
        self.SubscribeRealTimePrice()
        self.SetOrderStateCB()
        #time.sleep(35)  # 设置脚本接收 OpenD 的推送持续时间为15秒
        #while 1 :
        #    pass

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
        self.stp.SetOrderStopLoss(code=code,qty=qty,trd_side=trd_side,order_type=order_type,aux_price=aux_price,price=price)
        #更新订单的联系
        self.stp.RefreshProgram()
        self.RefreshProgram()

    def CancelOrder(self):
        selectedRow= self.tableWidget_order.selectedItems()[0].row()             #获取选中文本所在的行
        #获取oderID
        orderID=self.tableWidget_order.item(selectedRow, 0).text()
        #转化为数字
        orderID=int(orderID)
        self.stp.CancleOrder(orderID)
        self.RefreshProgram()

    def RefreshProgram(self):
        self.UpdateOrderTable()
        self.UpdateHoldTable()

    #持仓变动后，重新订阅
    def RebootProgram(self):
        self.UpdateOrderTable()
        self.UpdateHoldTable()
        # 重新订阅推送
        self.SubscribeRealTimePrice()

    def UpdateOrderTable(self):
        orderListDF=self.stp.orderListDataframe
        table=self.tableWidget_order
        table.setRowCount(0)

        for i in range(0,orderListDF.shape[0]):
            #持仓信息
            id=orderListDF['ID'].iloc[i]
            code=orderListDF['CODE'].iloc[i]
            name=orderListDF['NAME'].iloc[i]
            quanty=orderListDF['QUANTITY'].iloc[i]
            direction=orderListDF['DIRECTION'].iloc[i]
            type=orderListDF['TYPE'].iloc[i]
            status=orderListDF['STATE'].iloc[i]
            bidPrice=orderListDF['BIDPRICE'].iloc[i]
            auxPrice=orderListDF['AUXPRICE'].iloc[i]
            setDate=orderListDF['SETDATE'].iloc[i]
            TriggerTime=orderListDF['TRIGGERTIME'].iloc[i]
            operationDate=orderListDF['OPERATIONDATE'].iloc[i]
            futuOrderID=orderListDF['FUTUORDERID'].iloc[i]

            row_count = table.rowCount()  # 返回当前行数(尾部)
            table.insertRow(row_count)  # 尾部插入一行
            table.setItem(row_count, 0, QtWidgets.QTableWidgetItem(str(id)))
            table.setItem(row_count, 1, QtWidgets.QTableWidgetItem(str(code)))
            table.setItem(row_count , 2, QtWidgets.QTableWidgetItem(str(name)))
            table.setItem(row_count, 3, QtWidgets.QTableWidgetItem(str(direction)))
            table.setItem(row_count, 4, QtWidgets.QTableWidgetItem(str(type)))
            table.setItem(row_count, 5, QtWidgets.QTableWidgetItem(str(status)))
            table.setItem(row_count, 6, QtWidgets.QTableWidgetItem(str(quanty)))
            table.setItem(row_count, 7, QtWidgets.QTableWidgetItem(str(bidPrice)))
            table.setItem(row_count, 8, QtWidgets.QTableWidgetItem(str(auxPrice)))
            table.setItem(row_count, 9, QtWidgets.QTableWidgetItem(str(setDate)))
            table.setItem(row_count, 10, QtWidgets.QTableWidgetItem(str(TriggerTime)))
            table.setItem(row_count, 11, QtWidgets.QTableWidgetItem(str(operationDate)))
            table.setItem(row_count, 12, QtWidgets.QTableWidgetItem(str(futuOrderID)))

    def UpdateHoldTable(self):
        holdStockList=self.stp.holdStockList
        table=self.tableWidget_hold
        table.setRowCount(0)

        for i in range(0,len(holdStockList)):
            holdStock=holdStockList[i]

            #持仓信息
            code=holdStock.code
            name=holdStock.name
            quanty=holdStock.qty
            orderDirection=holdStock.orderDirection
            hasOrder=holdStock.hasOrder
            direction=holdStock.stopLossDirection
            stopLossPriceAux=holdStock.stopLossPriceAux
            stopLossPriceBid=holdStock.stopLossPriceBid
            stopLossQty=holdStock.stopLossQty

            state=holdStock.stopLossState
            row_count = table.rowCount()  # 返回当前行数(尾部)
            table.insertRow(row_count)  # 尾部插入一行
            table.setItem(row_count , 0, QtWidgets.QTableWidgetItem(str(code)))
            table.setItem(row_count , 1, QtWidgets.QTableWidgetItem(str(name)))
            table.setItem(row_count , 2, QtWidgets.QTableWidgetItem(str(quanty)))

            table.setItem(row_count , 4, QtWidgets.QTableWidgetItem(str(orderDirection)))
            table.setItem(row_count , 5, QtWidgets.QTableWidgetItem(str(hasOrder)))
            table.setItem(row_count , 6, QtWidgets.QTableWidgetItem(str(direction)))
            table.setItem(row_count , 7, QtWidgets.QTableWidgetItem(str(stopLossPriceAux)))
            table.setItem(row_count , 8, QtWidgets.QTableWidgetItem(str(stopLossPriceBid)))
            table.setItem(row_count , 9, QtWidgets.QTableWidgetItem(str(stopLossQty)))

            table.setItem(row_count , 10, QtWidgets.QTableWidgetItem(str(state)))

    def UpdatePrice(self,pos,price):
        #需要全部更新一遍
        table = self.tableWidget_hold
        #获取行数
        rowCount=table.rowCount()
        columnCount=table.columnCount()
        #声明一个用于存储数据的二维列表
        tableCopy = [[0 for _ in range(columnCount)] for _ in range(rowCount)]
        for i in range(0, rowCount):
            for j in range(0, columnCount):
                if table.item(i,j)==None:
                    tableCopy[i][j] = ''
                else:
                    tableCopy[i][j]=table.item(i,j).text()

        table.clearContents()

        for i in range(0,rowCount):
            for j in range(0, columnCount):
                if i==pos and j==3:
                    table.setItem(i, j, QtWidgets.QTableWidgetItem(str(price)))
                else:
                    table.setItem(i, j, QtWidgets.QTableWidgetItem(str(tableCopy[i][j])))

            '''    
            table.setItem(i, 0, QtWidgets.QTableWidgetItem(table.item(i,0)))
            table.setItem(i, 1, QtWidgets.QTableWidgetItem(table.item(i,1)))
            table.setItem(i, 2, QtWidgets.QTableWidgetItem(table.item(i,2)))

            table.setItem(i, 4, QtWidgets.QTableWidgetItem(table.item(i,4)))
            table.setItem(i, 5, QtWidgets.QTableWidgetItem(table.item(i,5)))
            table.setItem(i, 6, QtWidgets.QTableWidgetItem(table.item(i,6)))
            table.setItem(i, 7, QtWidgets.QTableWidgetItem(table.item(i,7)))
            table.setItem(i, 8, QtWidgets.QTableWidgetItem(table.item(i,8)))

            #只刷新对应的行，否则填写原数据
            if i==pos:
                table.setItem(pos, 3, QtWidgets.QTableWidgetItem(str(price)))
            else:
                table.setItem(i, 3, QtWidgets.QTableWidgetItem(table.item(i,3)))

        #table.setItem(pos, 3, QtWidgets.QTableWidgetItem(str(price)))
        table.update()
            '''

    #一键填充订单信息
    def quickSet(self):
        table = self.tableWidget_hold
        #判断没有选中的情况
        if len(table.selectedItems())==0:
            return
        else:
            row=table.selectedItems()[0].row()
            code = table.item(row, 0).text()
            qty = table.item(row, 2).text()
            direction = table.item(row, 4).text()
            self.textEdit_code.setPlainText(code)
            self.textEdit_qty.setPlainText(qty)

            if direction == 'Long':
                #多单对应卖出止损
                self.DirectionSelction.setCurrentIndex(1)
            elif direction == 'Short':
                #空单对应买入止损
                self.DirectionSelction.setCurrentIndex(2)


    #通过订阅获取实时报价并显示
    def SubscribeRealTimePrice(self):
        holdStockList=self.stp.holdStockList
        #没有持仓，list为0的情况，直接返回
        if len(holdStockList)==0:
            return
        #获取订阅名单,从类列表里获取
        subscribeList=[]
        for i in range(0,len(holdStockList)):
            subscribeList.append(holdStockList[i].code)
        #报价回调
        #handler = futuoder.StockQuoteTest(self.RenewRealTimePrice)
        #分时回调
        #handler = futuoder.RTDataTest(self.RenewRealTimePrice)
        #逐步回调
        handler = futuoder.TickerTest(self.RenewRealTimePrice)

        futuoder.quote_ctx.set_handler(handler)
        # 设置实时报价回调
        #ret, data = futuoder.quote_ctx.subscribe(subscribeList, [SubType.QUOTE])
        #订阅分时回调
        #ret, data = futuoder.quote_ctx.subscribe(subscribeList, [SubType.RT_DATA])
        #订阅逐笔回调
        ret, data = futuoder.quote_ctx.subscribe(subscribeList,[SubType.TICKER],is_first_push=False)

        if ret == RET_OK:
            print(data)
        else:
            print('error:', data)
        #time.sleep(15)  # 设置脚本接收 OpenD 的推送持续时间为15秒

    #接收到推送的回调处理逻辑
    def RenewRealTimePrice(self,pushdata):
        ''''
        print("更新价格进程编号:", os.getpid())
        print("更新价格进程编号:", multiprocessing.current_process())
        print("更新价格父进程编号:", os.getppid())
        print("当前线程信息", threading.current_thread())
        print("当前所有线程信息", threading.enumerate())  # 返回值类型为数组
        '''
        table = self.tableWidget_hold
        holdCodeList = []
        for i in range(0, len(self.stp.holdStockList)):
            holdCodeList.append(self.stp.holdStockList[i].code)

        code= pushdata['code'].iloc[0]
        #找到在dataframe中对应位置
        #判断该code是否存在
        if code in holdCodeList:
            pos=holdCodeList.index(code)
        else:
            return
        #实时
        #lastPrice = pushdata['last_price'].iloc[0]
        #分时
        #lastPrice=pushdata['cur_price'].iloc[0]
        #逐笔
        lastPrice=pushdata['price'].iloc[0]

        #table.setItem(pos, 3, QtWidgets.QTableWidgetItem(str(lastPrice)))
        self.UpdatePrice(pos,lastPrice)

        #调用止损判断程序：
        result=self.stp.StopLossProcess(pos,pushdata)
        if result=='NeedRefresh':
            self.RefreshProgram()

        if result=='HoldChange':
            self.RebootProgram()


    #根据富途回调函数推送修改订单状态
    def RenewOrderState(self, orderID):
        #print('接受订单执行回调推送')
        result = self.stp.RenewState(orderID)
        if result == 'NeedRefresh':
            self.RefreshProgram()

    #设置订单执行状态回调函数
    def SetOrderStateCB(self):
        futuoder.trd_ctx.set_handler(futuoder.TradeOrderTest(self.RenewOrderState))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)

    MainWindow = QtWidgets.QMainWindow()
    myWin = MyMainWindow(MainWindow)
    MainWindow.show()

    sys.exit(app.exec_())