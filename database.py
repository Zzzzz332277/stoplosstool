import datetime
#from WindPy import *
import sqlalchemy
#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import text, create_engine, Table, Column, Integer, String, Float, Date, DateTime, MetaData, ForeignKey, \
    desc, inspect, Index, UniqueConstraint
import pymysql
from sqlalchemy.orm import sessionmaker,declarative_base
import pandas as pd
import numpy as np


import time
from futu import *
import futu as ft


# 数据库的地址:HK市場
DataBaseAddr = {'hostNAME': '127.0.0.1',
                'PORT': '3306',
                'database': 'stoplosstool',
                'username': 'root',
                'password': 'mysqlzph'}


#####################################数据库的连接######################################
engine = sqlalchemy.create_engine(f"mysql+pymysql://{DataBaseAddr['username']}:{DataBaseAddr['password']}@localhost:3306/{DataBaseAddr['database']}")
#con = engine.connect()



#这里要分析下con和engine的区别
Session = sessionmaker(bind=engine)
session=Session()


#metadata = MetaData(bind=engine)
#用于获取到标的字段数据
insp = inspect(engine)
Base = declarative_base()

#####################################数据库的连接######################################

##########################定义sqlalchemy映射的类####################################
class OdersList(Base):
    __tablename__ = 'OrdersList'
    ID = Column(Integer, primary_key=True)
    CODE=Column(String(60),index=True)
    NAME=Column(String(60))
    DIRECTION=Column(String(60))
    TYPE=Column(String(60))
    STATE=Column(String(60))
    QUANTITY=Column(Float)
    #执行价格与触发价格
    BIDPRICE= Column(Float)
    AUXPRICE= Column(Float)
    #下单时间
    SETDATE=Column(DateTime)
    #执行动作时间
    OPERATIONDATE=Column(DateTime)
    #futu的订单ID
    FUTUORDERID = Column(String(60),index=True)
    '''
    __table_args__ = (
        UniqueConstraint('CODE', 'FUTUORDERID', name='CODE_FUTUORDERID'),  # code和date唯一
    )
    '''
####################################创建表格###############################################################
Base.metadata.create_all(engine)
#######################################################################################################################



