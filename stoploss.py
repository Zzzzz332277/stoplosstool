from datetime import datetime,timedelta

import futuoder
import pandas as pd
from sqlalchemy import text
import futu as ft
from futu import *
import database
import stoploss
class HoldStock():
    def __init__(self,code,name,qty,hasorder,stopLossPrice,orderDirection,stopLossDirection):
        self.code=code
        self.qty=qty
        self.name =name
        self.lastPrice=0
        self.hasOrder=hasorder
        self.lastPriceTime=None
        self.stopLossPrice=stopLossPrice
        #多空方向：’Long‘ 'Short'
        self.orderDirection=orderDirection
        #止损方向
        self.stopLossDirection=stopLossDirection
        #记录打出止损的事件,默认空值
        self.triggerTime=None
        #默认unTriggered 触发为Triggered
        self.stopLossState='UnTriggered'



class StopLossTool():
    def __init__(self):
        #运行时存储订单
        self.orderListDataframe=pd.DataFrame(columns=['ID','CODE','NAME','DIRECTION','TYPE','STATE','QUANTITY','BIDPRICE','AUXPRICE','SETDATE','OPERATIONDATE','FUTUORDERID'])
        #富途持仓获取
        #self.orderListDataframe=pd.DataFrame(columns=['CODE','NAME','DIRECTION','TYPE','STATE','QUANTITY','BIDPRICE','AUXPRICE','SETDATE','OPERATIONDATE'])
        #用来记录止损状态的dataframe
        #self.StateDataframe=pd.DataFrame(columns=['CODE','HASORDER','ORDERSTATE','LASTTIME'])

        self.zfutu=futuoder.Zfutu()
        #订单状态：alive,canceled,upgoing

    def InitProgram(self):
        print('初始化止损工具')
        print('获取订单信息')

        self.ReadOrderFromDB()
        #建立联系
        self.ConnectHoldAndOrder()

    def RefreshProgram(self):
        self.ReadOrderFromDB()
        # 建立联系
        self.ConnectHoldAndOrder()

    #根据富途持仓和订单dataframe联系，包括是否有SLT订单，以及SLT订单具体信息
    def ConnectHoldAndOrder(self):
        # 根据订单列表，获取持仓信息，并
        self.holdStockDataframe = self.zfutu.GetHoldStock()
        holdDFLenth = self.holdStockDataframe.shape[0]
        #建立持股信息的对象列表
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
            #通过持仓正负判断多空方向
            if qty>0:
                orderDirection='Long'
            elif qty<0:
                orderDirection = 'Short'
            stopLossDirection = ''
            stopLossPrice = 0
            if hasOrder:
                pos = testSeries[testSeries.values == code].index[0]
                stopLossDirection = self.orderListDataframe['DIRECTION'].iloc[pos]
                stopLossPrice = self.orderListDataframe['AUXPRICE'].iloc[pos]

            holdStockBuff = stoploss.HoldStock(code=code, name=name, qty=qty, hasorder=hasOrder,
                                               stopLossDirection=stopLossDirection, stopLossPrice=stopLossPrice,orderDirection=orderDirection)
            self.holdStockList[holdStockListIndex] = holdStockBuff
            holdStockListIndex = holdStockListIndex + 1


    #根据推送的位置，获取代码，进行订单判断
    def StopLossProcess(self,pos,pushdata):
        # 时间阈值，默认5秒
        timeThreshold = timedelta(seconds=5)
        lastPrice = pushdata['last_price'].iloc[0]
        lastTimeStr = pushdata['data_time'].iloc[0]
        lastTime=time.strptime(lastTimeStr,'%H:%M:%S')
        # 更新该条信息
        self.holdStockList[pos].lastPrice = lastPrice
        self.holdStockList[pos].lastPriceTime = lastTime
        #return outData
        # 进行判断，是否有订单触发
        # 没有订单，只更新直接返回
        if self.holdStockList[pos].hasOrder == False:
            return 'NoOrder'

        # 未触发状态时：
        if self.holdStockList[pos].stopLossState == 'UnTriggered':
            # 多空两种方向判断
            if self.holdStockList[pos].orderDirection == 'Long':
                # 做多时，跌破止损价,触发状态
                if self.holdStockList[pos].stopLossPrice > lastPrice:
                    self.holdStockList[pos].stopLossState = 'Triggered'
                    # 修改触发时间
                    self.holdStockList[pos].triggerTime = lastTime
                    return 'NeedRefresh'
            elif self.holdStockList[pos].orderDirection == 'Short':
                # 做空时，涨破止损价,触发状态
                if self.holdStockList[pos].stopLossPrice < lastPrice:
                    self.holdStockList[pos].stopLossState = 'Triggered'
                    self.holdStockList[pos].triggerTime = lastTime
                    return 'NeedRefresh'

        elif self.holdStockList[pos].stopLossState == 'Triggered':
            if self.holdStockList[pos].orderDirection == 'Long':
                # 做多时，跌破止损价,触发状态
                if self.holdStockList[pos].stopLossPrice >= lastPrice:
                    # 检查时间长度是否超过超过执行订单，进入订单执行逻辑
                    timeDuration = lastTime - self.holdStockList[pos].triggerTime
                    if timeDuration >= timeThreshold:
                        self.ExecuteStopLoss(pos)
                        return 'NeedRefresh'
                        # 下订单，执行逻辑
                else:
                    # 新的价格不满足止损条件，修改触发状态，改为未触发，时间清0
                    self.holdStockList[pos].stopLossState = 'UnTriggered'
                    self.holdStockList[pos].triggerTime = 0
                    return 'NeedRefresh'



            elif self.holdStockList[pos].orderDirection == 'Short':
                # 做空时，涨破止损价,触发状态
                if self.holdStockList[pos].stopLossPrice <= lastPrice:
                    # 检查时间长度是否超过超过执行订单
                    timeDuration = lastTime - self.holdStockList[pos].triggerTime
                    if timeDuration >= timeThreshold:
                        self.ExecuteStopLoss(pos)
                        return 'NeedRefresh'
                        # 下订单，执行逻辑
                else:
                    # 新的价格不满足止损条件，修改触发状态，改为未触发，时间清0
                    self.holdStockList[pos].stopLossState = 'UnTriggered'
                    self.holdStockList[pos].triggerTime = 0
                    return 'NeedRefresh'

    #根据对应的富途订单ID，修改订单状态
    def RenewState(self,futuorderID):
        table = self.tableWidget_hold
        orderList = []
        for i in range(0, len(self.orderListDataframe)):
            orderList.append(self.orderListDataframe.FutuOrderID)

        # 找到在dataframe中对应位置
        pos = orderList.index(futuorderID)
        #根据位置找出程序中的ID
        orderID = self.orderListDataframe['ID'].iloc[pos]
        self.ModifyOrderState(orderID, 'excuted')
        self.RefreshProgram()
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
        sql = 'select * from orderslist where STATE = "ongoing"'
        outData = pd.DataFrame()
        # 和tosql不一樣，一個用con用，egine，一個用con，
        #新建连接，查询后关闭
        con = database.engine.connect()
        outData = pd.read_sql(text(sql), con=con)
        outData = outData.sort_values(by="SETDATE", ascending=True)
        con.close()
        self.orderListDataframe=outData

    #执行止损订单的过程
    def ExecuteStopLoss(self,pos):
        code=self.holdStockList[pos].code
        qty=self.holdStockList[pos].qty
        price = self.holdStockList[pos].stopLossPrice
        # 多空方向：’Long‘ 'Short'
        if self.holdStockList[pos].stopLossDirection=='Long':
            trd_side=TrdSide.SELL
        elif self.holdStockList[pos].stopLossDirection=='Short':
            trd_side = TrdSide.BUY

        #调用富途接口下单
        result=self.zfutu.SetLimitOrder(code=code,qyt=qty,price=price,trd_side=trd_side,order_type=OrderType.NORMAL)
        if result:
            print('执行下单成功')
            #从holdstock中删除
            self.holdStockList.remove(pos)
            #从orderdataframe删除
            self.orderListDataframe.drop(self.orderListDataframe[self.orderListDataframe['CODE'] == code].index)

    #同步订单信息到数据库
    def SaveNewOrder(self,code,qty,trd_side,order_type,aux_price,price):
        orderDataframe = pd.DataFrame(
            columns=['CODE', 'NAME', 'DIRECTION', 'TYPE', 'STATE', 'QUANTITY', 'BIDPRICE', 'AUXPRICE', 'SETDATE',
                     'OPERATIONDATE','FUTUORDERID'])
        state='ongoing'
        #时间格式
        fmt = '%d-%m-%y %H:%M:%S'

        setDateTime=datetime.now()
        operationDateTime=None
        orderDataframe.loc[len(orderDataframe.index)] = [code,'', trd_side, order_type,state, qty,price,aux_price,setDateTime,operationDateTime,'']
        orderDataframe.to_sql(name='OrdersList', con=database.engine, if_exists="append", index=False)
        database.session.commit()

    def CancleOrder(self, orderID):
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

        # 修改数据
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


