import time

import chardet
import futu as ft
from futu import *

# 实例化行情上下文对象
quote_ctx = ft.OpenQuoteContext(host="127.0.0.1", port=11111)
# 上下文控制
quote_ctx.start()  # 开启异步数据接收
quote_ctx.set_handler(ft.TickerHandlerBase())  # 设置用于异步处理数据的回调对象(可派生支持自定义)
#处理数据并与富途进行通信的类
trd_ctx = OpenSecTradeContext(filter_trdmarket=TrdMarket.US, host='127.0.0.1', port=11111, is_encrypt=None, security_firm=SecurityFirm.FUTUSECURITIES)
#解锁密码
password_md5 = 'a4664cc82ff5767f5bb8cb31a1b39d9b'
password='927301'

############测试自选股功能#####################
'''
codeList=['HK.03678','HK.02291']
ret, data = quote_ctx.modify_user_security('ztrade', ModifyUserSecurityOp.MOVE_OUT, codeList)
if ret == RET_OK:
    print(data)  # 返回 success
else:
    print('error:', data)
'''



#用于转化单个code的函数
def CodeTransWind2FUTU(code):
    codebuff = code.split('.')
    codeNew = codebuff[1] + '.' + '0' + codebuff[0]
    return codeNew

def CodeTransWind2FUTU_US(codelist):
    codelistNew = list()
    for code in codelist:
        codebuff = code.split('.')
        codeNew = 'US' + '.' + codebuff[0]
        codelistNew.append(codeNew)
    return codelistNew

class StockQuoteTest(StockQuoteHandlerBase):
    def __init__(self,callbackfunc):
        #声明回调函数，调用 更新显示
        self.callbackfunc=callbackfunc
    def on_recv_rsp(self, rsp_pb):
        ret_code, data = super(StockQuoteTest, self).on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            print("StockQuoteTest: error, msg: %s" % data)
            return RET_ERROR, data
        self.callbackfunc(data)
        #打印输出收到的信息
        code=data['code'].iloc[0]
        time=data['data_time'].iloc[0]
        price=data['last_price'].iloc[0]
        print(f"报价推送：{code} 时间：{time} 价格：{price}")  # StockQuoteTest 自己的处理逻辑
        return RET_OK, data

class Zfutu():
    def __init__(self):
        #self.market=market
        #ema diffusion先不做
        '''
        if market=='HK':
            self.listNameList=['backstepemaHK', 'EmaDiffusionHK','EMAUpCrossHK', 'MoneyFlowHK', 'EMA5BottomArcHK','EMA5TOPArcHK','MACDTopArcHK','MACDBottomArcHK','EMADownCrossHK']
        elif market=='US':
            self.listNameList= ['backstepemaUS', 'EmaDiffusionUS','EMAUpCrossUS', 'MoneyFlowUS', 'EMA5BottomArcUS','EMA5TOPArcUS','MACDBottomArcUS','MACDTopArcUS','EMADownCrossUS']
        else:
            print('市场输入错误')
            return
        '''
    #获取持仓
    def GetHoldStock(self):
        ret, data = trd_ctx.position_list_query()
        if ret == RET_OK:
            print(data)
            if data.shape[0] > 0:  # 如果持仓列表不为空
                print(data['stock_name'][0])  # 获取持仓第一个股票名称
                print(data['stock_name'].values.tolist())  # 转为 list
        else:
            print('position_list_query error: ', data)
        #trd_ctx.close()  # 关闭当条连接
        return data

    #获取订单
    def GetOrderList(self):
        ret, data = trd_ctx.order_list_query()
        if ret == RET_OK:
            print(data)
            if data.shape[0] > 0:  # 如果订单列表不为空
                print(data['order_id'][0])  # 获取未完成订单的第一个订单号
                print(data['order_id'].values.tolist())  # 转为 list
        else:
            print('order_list_query error: ', data)
        #trd_ctx.close()
        return data
    #解锁
    def UnlockTrade(self):
        ret, data = trd_ctx.unlock_trade(password)
        if ret == RET_OK:
            print('unlock success!')
        else:
            print('unlock_trade failed: ', data)
        #trd_ctx.close()

    #下单,
    def SetLimitOrder(self,code,price,qty,trd_side,order_type,aux_price):
        ret, data = trd_ctx.place_order(price=price, qty=qty, code=code, trd_side=trd_side,order_type=order_type,aux_price=aux_price,trd_env=TrdEnv.REAL)
        if ret == RET_OK:
            print('限价单下单成功')

            print(data)
            print(data['order_id'][0])  # 获取下单的订单号
            orderID=data['order_id'].values.tolist()
            print(data['order_id'].values.tolist())  # 转为 list
            #返回list第一个
            return orderID[0]
        else:
            print('place_order error: ', data)

        #trd_ctx.close()
    #取消订单
    def CancleOrder(self,orderID):

        order_id = "orderID"
        ret, data = trd_ctx.modify_order(ModifyOrderOp.CANCEL, order_id, 0, 0)
        if ret == RET_OK:
            print(data)
            print(data['order_id'][0])  # 获取改单的订单号
            print(data['order_id'].values.tolist())  # 转为 list
        else:
            print('modify_order error: ', data)

    def FutuDisConnect(self):
        quote_ctx.close()  # 结束后记得关闭当条连接，防止连接条数用尽

    def ModifyFutuStockList(self,resultTable):
        codelist=list()
        #########################这里需要注意，对每日关注的列表进行保留操作，以免删除ztrade时候也删除了自选股###########################################

        if self.market=='HK':
            watchList='每日关注'
        elif self.market=='US':
            watchList='美股关注'
        else:
            print('市场输入错误')
            return

        ret, everyDayWatchData = quote_ctx.get_user_security(watchList)
        if ret == RET_OK:
            pass
            # print(data)  # 返回 success
        else:
            print('error:', everyDayWatchData)
        codeListEveryDayWatch = everyDayWatchData['code'].tolist()

        ##################################################先讲原先的list清除########################
        self.CleanOutFUTUList(self.listNameList)
        print('等待30S，防止调用futu接口过于频繁')
        time.sleep(30)

        #将resulttable中的结果按识别内容分类，并清除为0的行
        for index,recogName in enumerate(self.recogList):
            resultTableSliced=resultTable[['code',recogName]]
            resultTableSliced=resultTableSliced.loc[~((resultTableSliced[recogName] == 0) )]
            codeList=resultTableSliced['code'].tolist()
            codelistNew=self.CodeTransferWind2FUTU(codeList)
            self.AddFutuList(listname=self.listNameList[index],list=codelistNew)
            time.sleep(1)
            #这里加入等待避免超出接口限制
        ###################################再恢复每日关注的股票#####################################
        self.AddFutuList(listname=watchList, list=codeListEveryDayWatch)



#zfutu=Zfutu()
#zfutu.GetHoldStock()
