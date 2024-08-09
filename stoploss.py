from datetime import datetime

import futuoder
import pandas as pd
from sqlalchemy import text

import database
import stoploss
class HoldStock():
    def __init__(self,code,name,qty,hasorder,stopLossPrice,stopLossDirection):
        self.code=code
        self.qty=qty
        self.name =name
        self.lastPrice=0
        self.hasOrder=hasorder
        self.lastPriceTime=0
        self.stopLossPrice=stopLossPrice
        self.stopLossDirection=stopLossDirection
        #记录打出止损的事件
        self.stopLossTimeDuration=0
        self.stopLossState='UnTrigger'



class StopLossTool():
    def __init__(self):
        #运行时存储订单
        self.orderListDataframe=pd.DataFrame(columns=['CODE','NAME','DIRECTION','TYPE','STATE','QUANTITY','BIDPRICE','AUXPRICE','SETDATE','OPERATIONDATE'])
        #富途持仓获取
        #self.orderListDataframe=pd.DataFrame(columns=['CODE','NAME','DIRECTION','TYPE','STATE','QUANTITY','BIDPRICE','AUXPRICE','SETDATE','OPERATIONDATE'])
        #用来记录止损状态的dataframe
        self.StateDataframe=pd.DataFrame(columns=['CODE','HASORDER','ORDERSTATE','LASTTIME'])

        self.zfutu=futuoder.Zfutu()
        #订单状态：alive,canceled,upgoing

    def InitProgram(self):
        print('初始化止损工具')
        print('获取订单信息')

        #按状态获取
        #start_time = time.time()
        sql = 'select * from orderslist where STATE = "ongoing"'
        outData = pd.DataFrame()
        # 和tosql不一樣，一個用con用，egine，一個用con，

        outData = pd.read_sql(text(sql), con=database.con)
        #end_time = time.time()

        #print("耗时: {:.2f}秒".format(end_time - start_time))
        outData = outData.sort_values(by="SETDATE", ascending=True)
        outData=outData[outData.columns.drop('ID')]
        self.orderListDataframe=outData

        #根据订单列表，获取持仓信息，并
        self.holdStockDataframe=self.zfutu.GetHoldStock()
        holdDFLenth=self.holdStockDataframe.shape[0]
        self.holdStockList = [stoploss.HoldStock for i in range(holdDFLenth)]
        holdStockListIndex = 0
        for i in range(holdDFLenth):
            code=self.holdStockDataframe['code'].iloc[i]
            qty=self.holdStockDataframe['qty'].iloc[i]
            name=self.holdStockDataframe['stock_name'].iloc[i]
            # 是否有止损订单
            testSeries = self.orderListDataframe['CODE']
            hasOrder = code in testSeries.values
            direction=''
            stopLossPrice=0
            if hasOrder:
                direction=self.orderListDataframe['DIRECTION'].iloc[i]
                stopLossPrice=self.orderListDataframe['AUXPRICE'].iloc[i]

            holdStockBuff=stoploss.HoldStock(code=code,name=name,qty=qty,hasorder=hasOrder,stopLossDirection=direction,stopLossPrice=stopLossPrice)
            self.holdStockList[holdStockListIndex] = holdStockBuff
            holdStockListIndex = holdStockListIndex + 1



        #return outData

    #通过字典传入订单信息，下订单,并添加到orderListDataframe
    def SetOrderStopLoss(self,code,qty,trd_side,order_type,aux_price,price):
        #解锁
        self.zfutu.UnlockTrade()
        #调用接口下单，返回list
        orderID=self.zfutu.SetLimitOrder(code=code,qty=qty,trd_side=trd_side,order_type=order_type,aux_price=aux_price,price=price)

        print(f'orderid {orderID}')
        self.SaveNewOrder(code=code,qty=qty,trd_side=trd_side,order_type=order_type,aux_price=aux_price,price=price,orderID=orderID)

    #同步订单信息到数据库
    def SaveNewOrder(self,code,qty,trd_side,order_type,aux_price,price,orderID):
        orderDataframe = pd.DataFrame(
            columns=['CODE', 'NAME', 'DIRECTION', 'TYPE', 'STATE', 'QUANTITY', 'BIDPRICE', 'AUXPRICE', 'SETDATE',
                     'OPERATIONDATE','ORDERID'])
        state='ongoing'
        #时间格式
        fmt = '%d-%m-%y %H:%M:%S'

        setDateTime=datetime.now()

        orderDataframe.loc[len(orderDataframe.index)] = [code,'', trd_side, order_type,state, qty,price,aux_price,setDateTime,setDateTime,orderID]
        orderDataframe.to_sql(name='OrdersList', con=database.engine, if_exists="append", index=False)

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
        orderDataframe.to_sql(name='OrdersList', con=database.engine, if_exists="append", index=False)





        #sql = text(f'insert into orderslist (CODE,DIRECTION,TYPE,STATE,QUANTITY,BIDPRICE,AUXPRICE,SETDATE,ORDERID) values ("{code}","{trd_side}","{order_type}","{state}","{qty}","{price}","{aux_price}","{setDateTime}","{orderID}")')

        #with database.con as conn:
        #database.session.execute(sql)


    #解锁交易接口
