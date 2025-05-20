
from .clearmine import ClearMine
from typing import Dict, List, Tuple, Optional
from .databaseOperator import sqlOperator
from typing import Tuple
import threading
import json
import time
import re

class Server:
    def __init__(self) -> None:
        #self.__data_queue = []
        #self.__lock = threading.Lock()
        self.__CM = ClearMine()
        self.__SQL = sqlOperator()
        self.__SQL.active()
        self.__ready = 0


    def login(self, username : str, password : str) -> bool:
        '''用于用户登录时,判断收到的账号密码是否匹配'''
        data = self.__SQL.select_by_user(username)
        if data == None: return False
        return password == data['passwd']

    
    def register(self, invitecode : str, username : str, password : str) -> Optional[bool]:
        '''用于用户注册'''

        # 防止用户将script脚本进行sql注入
        test_text = re.sub(r'\s', '', username.lower()) 
        if r'<script>' in test_text or r'</script>' in test_text: return None

        return self.__SQL.register(invitecode, username, password)


    def click(self, x : int , y : int, username : str) -> Tuple[bool, str, bool, int]:
        '''
        收到用户点击消息时执行, 返回值为:
        1.是否是有效点击 2.颜色 3.游戏是否结束 4.本次点击的时间戳
        '''
        color_number = self.__CM.get_user_color_num(username)
        color_string = self.__CM.get_user_color_str(color_number)

        click_status = self.__CM.click(x, y, username)

        finish = self.__CM.judge_win()

        bool_ret = False
        if click_status >= 0:
            clearCount = self.__SQL.select_userInfo_clearCount(username)
            self.__SQL.update_userInfo_clearCount(username, clearCount + click_status)
            bool_ret = True
        elif click_status == -1:
            boomCount = self.__SQL.select_userInfo_boomCount(username)
            self.__SQL.update_userInfo_boomCount(username, boomCount + 1)
            bool_ret = True

        return bool_ret, color_string, finish, self.__CM.get_timmer()

    def timmer(self) -> int:
        '''从扫雷对象中那到时间戳并返回'''
        return self.__CM.get_timmer()

    def history(self) -> List[Tuple[int ,int, str]]:
        '''从扫雷对象中那到本局历史点击记录并返回'''
        return self.__CM.get_click_history()

    def args(self) -> dict:
        '''从扫雷对象中拿到本局地图参数并返回'''
        return self.__CM.get_args()

    def restart(self, waittime = -5) -> None:
        '''游戏需要重启时调用, 若需要等一会才进入下一局, 填写waittime表示等待时长, 小于0不等待'''
        self.__ready = time.time() + waittime
        self.__CM.restart(True)

    def ready(self) -> None:
        '''判断游戏是否可以进行'''
        return time.time() > self.__ready

    def give_color(self, username : str) -> None:
        '''为没有颜色的用户尽量随机分配一个不同的颜色'''
        self.__CM.give_color(username)

    def rank(self) -> dict:
        '''获取本局战绩'''
        return self.__CM.get_rank()

    def total_rank(self) -> List[dict]:
        '''查询历史积累战绩'''
        return self.__SQL.get_totalRank_data()

    def set_flag(self, x: int, y: int, flag: int) -> None:
        '''设置某个格子的flag状态'''
        self.__CM.set_flag(x, y, flag)
        # 如需持久化到数据库，可在这里调用数据库操作

    def get_flag(self, x: int, y: int) -> int:
        '''获取某个格子的flag状态'''
        return self.__CM.get_flag(x, y)

    def get_all_flags(self) -> List[Tuple[int, int, int]]:
        '''获取所有有标记的格子的flag状态'''
        return self.__CM.get_all_flags()