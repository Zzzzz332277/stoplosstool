from datetime import datetime,timedelta

import futuoder
import pandas as pd
from sqlalchemy import text
import futu as ft
from futu import *
import database
import stoploss
import multiprocessing
import time
import os

'''
数据库中订单状态：
Untriggerd(包含ongoing，即有效状态）
Triggered（触发状态，包含有效状态）
Submited(已提交, 包含有效状态）
Executed(已执行, 失效）
Canceled(撤销，失效）
'''
#线程锁，保证数据库修改不受回调影响
lock = threading.RLock()




class HoldStock():
    def __init__(self,code,name,qty,hasorder,orderID,stopLossState,stopLossPriceAux,stopLossPriceBid,stopLossQty,orderDirection,stopLossDirection,triggerTime):
        self.code=code
        self.qty=qty
        self.name =name
        self.lastPrice=0
        self.hasOrder=hasorder
        self.orderID=orderID
        self.lastPriceTime=None
        self.stopLossPriceAux=stopLossPriceAux
        self.stopLossPriceBid=stopLossPriceBid
        self.stopLossQty=stopLossQty
        #多空方向：’Long‘ 'Short'
        self.orderDirection=orderDirection
        #止损方向
        self.stopLossDirection=stopLossDirection
        #记录打出止损的事件,默认空值
        self.triggerTime=triggerTime
        #默认unTriggered 触发为Triggered
        self.stopLossState=stopLossState



class StopLossTool():
    def __init__(self):
        #运行时存储订单
        self.orderListDataframe=pd.DataFrame(columns=['ID','CODE','NAME','DIRECTION','TYPE','STATE','QUANTITY','BIDPRICE','AUXPRICE','SETDATE','TRIGGERTIME','OPERATIONDATE','FUTUORDERID'])
        #富途持仓获取
        #self.orderListDataframe=pd.DataFrame(columns=['CODE','NAME','DIRECTION','TYPE','STATE','QUANTITY','BIDPRICE','AUXPRICE','SETDATE','OPERATIONDATE'])
        #用来记录止损状态的dataframe
        #self.StateDataframe=pd.DataFrame(columns=['CODE','HASORDER','ORDERSTATE','LASTTIME'])

        self.zfutu=futuoder.Zfutu()
        #订单状态：alive,canceled,upgoing
        #用于控制线程间通信的变量，再数据更新完毕后置1
        self.dataUpdateFlag=0

    def InitProgram(self):
        print('初始化止损工具')
        print('获取订单信息')
        #所有正在运行数据库订单trigertime清零
        self.CleanTriggerTime()

        self.ReadOrderFromDB()
        #建立联系
        self.ConnectHoldAndOrder()

    def RefreshProgram(self):
        print('刷新程序')
        self.ReadOrderFromDB()
        # 建立联系
        self.ConnectHoldAndOrder()

    #根据富途持仓和订单dataframe联系，包括是否有SLT订单，以及SLT订单具体信息
    def ConnectHoldAndOrder(self):
        print('连接持仓与订单')

        '''
        print('绑定持仓与订单列表')
        print("获取持仓进程编号:", os.getpid())
        print("获取持仓进程名称:", multiprocessing.current_process())
        print("获取持仓父进程名称:", os.getppid())
        print("当前线程信息", threading.current_thread())
        print("当前所有线程信息", threading.enumerate())  # 返回值类型为数组
        '''
        # 根据订单列表，获取持仓信息，并
        self.holdStockDataframe = self.zfutu.GetHoldStock()
        self.holdStockDataframe = self.holdStockDataframe[self.holdStockDataframe["qty"] != 0]

        holdDFLenth = self.holdStockDataframe.shape[0]
        if holdDFLenth==0:
            pass
            #return
        #建立持股信息的对象列表,如果为空，则建立空的list
        self.holdStockList = [stoploss.HoldStock for i in range(holdDFLenth)]
        holdStockListIndex = 0
        for i in range(holdDFLenth):
            code = self.holdStockDataframe['code'].iloc[i]
            qty = self.holdStockDataframe['qty'].iloc[i]
            name = self.holdStockDataframe['stock_name'].iloc[i]
            # 是否有止损订单
            testSeries = self.orderListDataframe['CODE']
            testList=testSeries.tolist()
            #判断是否有订单及获取订单位置
            hasOrder = code in testSeries.values

            #已经卖出无实际持仓的情况
            if qty==0:
                continue
            #通过持仓正负判断多空方向
            if qty>0:
                orderDirection='Long'
            elif qty<0:
                orderDirection = 'Short'

            stopLossDirection = ''
            stopLossPriceAux = 0
            stopLossPriceBid=0
            stopLossQty=0
            stopLossState=''
            orderID=None
            triggerTime=None
            if hasOrder:
                pos = testSeries[testSeries.values == code].index[0]
                stopLossDirection = self.orderListDataframe['DIRECTION'].iloc[pos]
                stopLossPriceAux = self.orderListDataframe['AUXPRICE'].iloc[pos]
                stopLossPriceBid = self.orderListDataframe['BIDPRICE'].iloc[pos]
                stopLossQty=self.orderListDataframe['QUANTITY'].iloc[pos]
                stopLossState=self.orderListDataframe['STATE'].iloc[pos]
                #对应的数据库中的订单ID,这里要注意持仓和数据库订单要对应，一个持仓不能有多个订单
                orderID= self.orderListDataframe['ID'].iloc[pos]
                triggerTime=self.orderListDataframe['TRIGGERTIME'].iloc[pos]
            holdStockBuff = stoploss.HoldStock(code=code, name=name, qty=qty, hasorder=hasOrder,stopLossState=stopLossState,orderID=orderID,
                                               stopLossDirection=stopLossDirection, stopLossPriceAux=stopLossPriceAux,stopLossPriceBid=stopLossPriceBid,stopLossQty=stopLossQty,orderDirection=orderDirection,triggerTime=triggerTime)
            self.holdStockList[holdStockListIndex] = holdStockBuff
            holdStockListIndex = holdStockListIndex + 1

    #根据推送的位置，获取代码，进行订单判断
    def StopLossProcess(self,pos,pushdata):
        #print('止损判断过程')
        '''
        print("止损过程进程编号:", os.getpid())
        print("止损过程进程名称:", multiprocessing.current_process())
        print("止损过程父进程名称:", os.getppid())
        print("当前线程信息", threading.current_thread())
        print("当前所有线程信息", threading.enumerate())  # 返回值类型为数组
        '''
        code=self.holdStockList[pos].code
        # 时间阈值，默认5秒
        timeThreshold = timedelta(seconds=10)
        #lastPrice = pushdata['last_price'].iloc[0]
        lastPrice=pushdata['price'].iloc[0]

        #lastTimeStr = pushdata['data_time'].iloc[0]
        lastTimeStr = pushdata['time'].iloc[0]
        lastTimeStrLen=len(lastTimeStr)
        #print(lastTimeStr,lastTimeStrLen)

        #根据传来的字符串长度确定是否带有毫秒
        if lastTimeStrLen==23:
            lastTime=datetime.strptime(lastTimeStr,"%Y-%m-%d %H:%M:%S.%f")
        elif lastTimeStrLen==19:
            lastTime=datetime.strptime(lastTimeStr,"%Y-%m-%d %H:%M:%S")

        # 更新该条信息
        self.holdStockList[pos].lastPrice = lastPrice
        self.holdStockList[pos].lastPriceTime = lastTime
        orderID=self.holdStockList[pos].orderID
        #return outData
        # 进行判断，是否有订单触发
        # 没有订单，只更新直接返回
        if self.holdStockList[pos].hasOrder == False:
            return 'NoOrder'

        # 未触发状态时：
        if self.holdStockList[pos].stopLossState == 'Untriggered':
            # 多空两种方向判断
            if self.holdStockList[pos].orderDirection == 'Long':
                # 做多时，跌破止损价,触发状态
                if self.holdStockList[pos].stopLossPriceAux > lastPrice:
                    self.ModifyTriggerTime(orderID,lastTime)
                    self.ModifyOrderState(id=orderID, state='Triggered')
                    self.RefreshProgram()
                    # 修改触发时间
                    #return 'NeedRefresh'
                    return 'Triggered'

            elif self.holdStockList[pos].orderDirection == 'Short':
                # 做空时，涨破止损价,触发状态
                if self.holdStockList[pos].stopLossPriceAux < lastPrice:
                    self.ModifyTriggerTime(orderID, lastTime)
                    self.ModifyOrderState(id=orderID, state='Triggered')
                    self.RefreshProgram()
                    #return 'NeedRefresh'
                    return 'Triggered'

        elif self.holdStockList[pos].stopLossState == 'Triggered':
            if self.holdStockList[pos].orderDirection == 'Long':
                # 做多时，跌破止损价,触发状态
                if self.holdStockList[pos].stopLossPriceAux >= lastPrice:
                    # 检查时间长度是否超过超过执行订单，进入订单执行逻辑
                    timeDuration = lastTime - self.holdStockList[pos].triggerTime
                    if timeDuration >= timeThreshold:
                        #加线程锁
                        self.ExecuteStopLoss(pos,orderID)
                        #修改数据库状态
                        self.ModifyOrderState(id=orderID,state='Submited')
                        self.RefreshProgram()
                        #flag
                        self.dataUpdateFlag=1
                        return 'HoldChange,Submited'
                        # 下订单，执行逻辑
                else:
                    # 新的价格不满足止损条件，修改触发状态，改为未触发，时间清0
                    self.ModifyTriggerTime(orderID, None)
                    self.ModifyOrderState(id=orderID, state='Untriggered')
                    self.RefreshProgram()

                    return 'NeedRefresh'



            elif self.holdStockList[pos].orderDirection == 'Short':
                # 做空时，涨破止损价,触发状态
                if self.holdStockList[pos].stopLossPriceAux <= lastPrice:
                    # 检查时间长度是否超过超过执行订单
                    timeDuration = lastTime - self.holdStockList[pos].triggerTime
                    if timeDuration >= timeThreshold:
                        #加线程锁
                        self.ExecuteStopLoss(pos,orderID)
                        self.ModifyOrderState(id=orderID,state='Submited')
                        self.RefreshProgram()
                        self.dataUpdateFlag=1

                        #return 'HoldChange'
                        return 'HoldChange,Submited'

                        # 下订单，执行逻辑
                else:
                    # 新的价格不满足止损条件，修改触发状态，改为未触发，时间清0
                    self.ModifyTriggerTime(orderID, None)
                    self.ModifyOrderState(id=orderID, state='Untriggered')
                    self.RefreshProgram()
                    return 'NeedRefresh'

    #根据对应的富途订单ID，修改订单状态
    def RenewState(self,futuorderID,futuorderTime):

        #print("订单回调进程编号:", os.getpid())
        #print("订单回调进程名称:", multiprocessing.current_process())
        #print("订单回调父进程名称:", os.getppid())
        #print("当前线程信息", threading.current_thread())
        #print("当前所有线程信息", threading.enumerate())  # 返回值类型为数组
        #回调后等待flag置1
        while self.dataUpdateFlag==0:
            pass

        futuorderIDSeris=self.orderListDataframe['FUTUORDERID']
        # 找到在dataframe中对应位置
        pos = futuorderIDSeris[futuorderIDSeris.values == futuorderID[0]].index[0]

        #pos = orderList.index(futuorderID[0])
        #根据位置找出程序中的ID
        orderID = self.orderListDataframe['ID'].iloc[pos]
        self.ModifyOrderState(orderID, 'Executed')
        self.ModifyOrderTime(orderID, futuorderTime[0])
        self.RefreshProgram()
        #FLAG置1
        self.dataUpdateFlag = 1
        return 'NeedRefresh'

    #通过字典传入订单信息，下订单,并添加到orderListDataframe
    def SetOrderStopLoss(self,code,qty,trd_side,order_type,aux_price,price):
              # self.orderListDataframe.loc[len(self.orderListDataframe.index)] = [code, '', trd_side, order_type, state, qty, price,#aux_price, setDateTime, setDateTime, orderID]
        self.SaveNewOrder(code=code,qty=qty,trd_side=trd_side,order_type=order_type,aux_price=aux_price,price=price)
        self.ReadOrderFromDB()

    #从数据库中获取订单df信息
    def ReadOrderFromDB(self):
        # 按状态获取
        # start_time = time.time()


        sql = 'select * from orderslist where STATE in ("Untriggered","Triggered","Submited")'
        outData = pd.DataFrame()
        # 和tosql不一樣，一個用con用，egine，一個用con，
        #新建连接，查询后关闭
        con = database.engine.connect()
        outData = pd.read_sql(text(sql), con=con)
        outData = outData.sort_values(by="SETDATE", ascending=True)
        con.close()
        self.orderListDataframe=outData

    #执行止损订单的过程
    def ExecuteStopLoss(self,pos,orderID):
        print(f'执行下单，订单ID:{orderID}')

        code=self.holdStockList[pos].code
        qty=self.holdStockList[pos].stopLossQty
        price = self.holdStockList[pos].stopLossPriceBid
        # 多空方向：’Long‘ 'Short'
        if self.holdStockList[pos].orderDirection=='Long':
            trd_side=TrdSide.SELL
        elif self.holdStockList[pos].orderDirection=='Short':
            trd_side = TrdSide.BUY

        #调用富途接口下单
        result,futuOrderID=self.zfutu.SetLimitOrder(code=code,qty=qty,price=price,trd_side=trd_side,order_type=OrderType.NORMAL)
        #市价单
        #result,futuOrderID=self.zfutu.SetMarketOrder(code=code,price=price,qty=qty,trd_side=trd_side)

        if result:
            print(f'执行下单成功，返回富途ID：{futuOrderID}')
            #从holdstock中删除
            #self.holdStockList.remove(self.holdStockList[pos])
            #从orderdataframe删除
            #self.orderListDataframe.drop(self.orderListDataframe[self.orderListDataframe['CODE'] == code].index)
            #更新对应订单对应的futuID
            self.ModifyFutuOrderID(orderID, futuOrderID)

    #同步订单信息到数据库
    def SaveNewOrder(self,code,qty,trd_side,order_type,aux_price,price):
        orderDataframe = pd.DataFrame(
            columns=['CODE', 'NAME', 'DIRECTION', 'TYPE', 'STATE', 'QUANTITY', 'BIDPRICE', 'AUXPRICE', 'SETDATE','TRIGGERTIME',
                     'OPERATIONDATE','FUTUORDERID'])
        state='Untriggered'
        #时间格式
        fmt = '%d-%m-%y %H:%M:%S'

        setDateTime=datetime.now()
        operationDateTime=None
        orderDataframe.loc[len(orderDataframe.index)] = [code,'', trd_side, order_type,state, qty,price,aux_price,setDateTime,None,operationDateTime,'']
        orderDataframe.to_sql(name='OrdersList', con=database.engine, if_exists="append", index=False)
        database.session.commit()

    def CancleOrder(self, orderID):
        # 解锁
        testSeries = self.orderListDataframe['ID']
        testList = testSeries.tolist()
        pos = testSeries[testSeries.values == orderID].index[0]
        orderState=self.orderListDataframe['STATE'].iloc[pos]
        if orderState in ['Submited','Excuted']:
            print('订单已提交，无法取消')
            return
        state='cancled'
        self.ModifyOrderState(orderID, state)
        self.RefreshProgram()


    def CancleOrderFutu(self, orderID):
        # 解锁
        self.zfutu.UnlockTrade()
        orderID=self.zfutu.SetLimitOrder(code=code,qty=qty,trd_side=trd_side,order_type=order_type,aux_price=aux_price,price=price)

        orderDataframe = pd.DataFrame(
            columns=['CODE', 'NAME', 'DIRECTION', 'TYPE', 'STATE', 'QUANTITY', 'BIDPRICE', 'AUXPRICE', 'SETDATE',
                     'OPERATIONDATE', 'ORDERID'])
        state = 'ongoing'
        # 时间格式
        fmt = '%d-%m-%y %H:%M:%S'

        setDateTime = datetime.now()

        orderDataframe.loc[len(orderDataframe.index)] = [code, '', trd_side, order_type, state, qty, price,
                                                         aux_price, setDateTime, setDateTime, orderID]
        orderDataframe.to_sql(name='orderslist', con=database.engine, if_exists="append", index=False)
        database.session.commit()

    #修改数据库中订单状态
    def ModifyOrderState(self,id,state):
        #print("更新订单状态进程编号:", os.getpid())
        #print("更新订单状态进程编号:", multiprocessing.current_process())
        #print("更新订单状态进程编号:", os.getppid())
        #print("当前线程信息", threading.current_thread())
        #print("当前所有线程信息", threading.enumerate())  # 返回值类型为数组
        #print('更新订单状态')
        # 修改数据
        #锁定线程
        print('更新订单状态')
        order = database.session.query(database.OdersList).filter_by(ID=id).first()
        if order:
            order.STATE = state
            database.session.commit()
            print("updated success.")
            print(order.ID, order.STATE)
        else:
            print("not found.")


        #sql = text(f'insert into orderslist (CODE,DIRECTION,TYPE,STATE,QUANTITY,BIDPRICE,AUXPRICE,SETDATE,ORDERID) values ("{code}","{trd_side}","{order_type}","{state}","{qty}","{price}","{aux_price}","{setDateTime}","{orderID}")')

        #with database.con as conn:
        #database.session.execute(sql)
    # 修改数据库中订单状态
    def ModifyOrderTime(self, id, time):
        # print("更新订单状态进程编号:", os.getpid())
        # print("更新订单状态进程编号:", multiprocessing.current_process())
        # print("更新订单状态进程编号:", os.getppid())
        # print("当前线程信息", threading.current_thread())
        # print("当前所有线程信息", threading.enumerate())  # 返回值类型为数组
        # print('更新订单状态')
        # 修改数据
        # 锁定线程
        print('更新订单状态')
        order = database.session.query(database.OdersList).filter_by(ID=id).first()
        if order:
            order.OPERATIONDATE = time
            database.session.commit()
            print("updated success.")
            print(order.ID, order.OPERATIONDATE)
        else:
            print("not found.")

    #修改订单里面的futuID
    def ModifyFutuOrderID(self, id, futuoderID):
        print('更新订单ID与富途ID')

        # 修改数据
        order = database.session.query(database.OdersList).filter_by(ID=id).first()
        if order:
            order.FUTUORDERID = futuoderID
            database.session.commit()
            print("updated success.")
            print(order.ID, order.FUTUORDERID)
        else:
            print("not found.")

    def ModifyTriggerTime(self, id, triggertime):
        print('更新触发时间')

        # 修改数据
        order = database.session.query(database.OdersList).filter_by(ID=id).first()
        if order:
            order.TRIGGERTIME = triggertime
            database.session.commit()
            print("updated success.")
            print(order.ID, order.TRIGGERTIME)
        else:
            print("not found.")

    def CleanTriggerTime(self):
        print('重置订单触发状态和时间')
        # 修改数据
        order = database.session.query(database.OdersList).filter_by(STATE='Triggered').update({'STATE':'Untriggered','TRIGGERTIME':None})
        database.session.commit()
'''
slt=StopLossTool()
slt.CleanTriggerTime()
'''