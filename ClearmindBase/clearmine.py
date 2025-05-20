import time
import numpy as np
from random import randint
from typing import Tuple, Dict, Optional, List
from .colorrander import ColorRander
from .config import (
    DEFAULT_PART_SIZE, 
    DEFAULT_COL_SIZE, 
    DEFAULT_MOD, 
    DEFAULT_PART_MINE_NUM, 
    DEFAULT_ROW_SIZE, 
    DEFAULT_SEED,
)

class ClearMine:
    '''
    1.实例化对象后游戏自动开始
    2.收到点击请求后调用click方法, 返回得分或错误信息
    3.每次调用click方法后, 需要手动调用judge_win方法判断游戏是否结束
    4.若游戏结束, 调用restart方法重开游戏
    '''
    MINE = 9
    CELLTYPE = np.int16
    Dir = tuple(zip(
        (-1, -1, -1,  0,  1,  1,  1,  0),
        (-1,  0,  1,  1,  1,  0, -1, -1),
    ))
    def __init__(
        self, 
        size_row : int = DEFAULT_ROW_SIZE, 
        size_col : int = DEFAULT_COL_SIZE,
        part_size: int = DEFAULT_PART_SIZE, # 每一子块边长, 保证不要超过numpy.int16
        part_mine_num : int = DEFAULT_PART_MINE_NUM, # 每一子块的雷数, 保证不要超过子块大小
        seed : int = DEFAULT_SEED,
        mod : int = DEFAULT_MOD,
    ) -> None:
        '''初始化'''

        # 种子, 模数
        self.__seed, self.__mod = seed, mod

        # 雷区子块边长
        self.__part_size = part_size

        self.cfg(size_row, size_col, part_mine_num)
        self.restart()

    def judge_win(self) -> bool:
        '''检查游戏是否结束'''
        return self.__safe >= self.__safe_target

    def restart(self, change_game = False) -> None:
        '''重置游戏数据, 若参数change_game为True, 更换游戏种子'''
        func_start_time = time.time()

        # 统计真实雷数
        self.__real_mine_num = 0

        # 时间戳
        self.__timmer = 0

        # 点击历史 和 本局战绩
        self.__click_history = []
        self.__rank = {}

        # 随机颜色生成器, 用户编号
        self.__ColorRander = ColorRander()
        self.__userIter = 0

        # [用户 - 编号 - 颜色]映射表
        self.__dict_user2number : Dict[str, int] = {}
        self.__dict_number2color : Dict[int, str] = {}

        # 用种子重置随机数
        if change_game: self.__seed = randint(297, 998244352)
        self.__fib1, self.__fib2, self.__delta = 1, 2, self.__seed

        # 生成雷区地图
        self.__distribute()
        self.__flags = np.zeros([self.__size_row, self.__size_col], dtype=np.int8)

        # 已经扫开的非雷格子数量
        self.__safe = 0 
        self.__safe_target = self.__size_row * self.__size_col - self.__real_mine_num

        print(f'Game restarted, use time: {time.time() - func_start_time}s')

    def cfg(self, new_row : int, new_col : int, new_mine_num : int) -> None:
        '''改变雷区大小、雷数等基础配置'''
        self.__size_row = new_row
        self.__size_col = new_col
        self.__part_mine_num = new_mine_num

    def __judgeEdge(self, x : int, y : int) -> bool:
        '''判断一个点是否超出雷区范围'''
        return x >= 0 and x < self.__size_row and y >= 0 and y < self.__size_col

    def __iter_get_position(self, row_size : int, col_size : int) -> Tuple[int, int]:
        '''更新用于制造雷区子块的随机数, 并获得交换坐标'''
        # 迭代更新随机数
        self.__fib1, self.__fib2 = self.__fib2, (self.__fib1 + self.__fib2) % self.__mod
        while True:
            self.__delta = (self.__delta * self.__fib1) % self.__mod
            if self.__delta > row_size * col_size: break

        # 获取要交换的坐标
        delta = self.__delta
        x = delta % row_size
        delta //= row_size
        y = delta % col_size

        return x, y

    def __distribute(self) -> None:
        '''构造雷区, 对象的属性board和color在这里面定义/重置'''

        # 雷区地图
        self.__board = np.zeros([self.__size_row, self.__size_col], dtype = ClearMine.CELLTYPE)
        
        # 雷区格子颜色(为0时表示状态格子掩盖)
        self.__color = np.zeros([self.__size_row, self.__size_col], dtype = ClearMine.CELLTYPE)

        def sub_block(row_size : int, col_size : int, mine_num : int) -> np.ndarray:
            '''构造雷区子块'''

            array = np.array([i for i in range(row_size * col_size)], dtype = ClearMine.CELLTYPE).reshape(row_size, col_size)
            for i in range(row_size):
                for j in range(col_size):
                    x, y = self.__iter_get_position(row_size, col_size)
                    array[i][j], array[x][y] = array[x][y], array[i][j]

            ret = np.zeros([row, col], dtype = ClearMine.CELLTYPE)
            ret[array < mine_num] = ClearMine.MINE

            return ret

        # 生成雷
        for i in range(0, self.__size_row, self.__part_size):
            for j in range(0, self.__size_col, self.__part_size):

                # 动态判断得到雷区子块形状以及雷的个数
                row, col, num, tag = self.__part_size, self.__part_size, self.__part_mine_num, False 
                if i + row > self.__size_row:
                    row = self.__size_row - i
                    tag = True
                if j + col > self.__size_col:
                    col = self.__size_col - j
                    tag = True
                if tag:
                    num = row * col * num // (self.__part_size * self.__part_size)

                # 构造雷区子块
                self.__real_mine_num += num
                self.__board[i : i + row, j : j + col] = sub_block(row, col, num)

        # 为雷区格子算数
        for i in range(self.__size_row):
            for j in range(self.__size_col):
                if self.__board[i][j] == ClearMine.MINE:
                    for dir in ClearMine.Dir:
                        xx, yy = i + dir[0], j + dir[1]
                        if self.__judgeEdge(xx, yy) and self.__board[xx][yy] != ClearMine.MINE:
                            self.__board[xx][yy] += 1
                    


    def __updateMask(self, x : int, y : int, color : int, F : bool = True) -> None:
        '''扫雷的DFS部分'''

        if self.__color[x][y] == 0:
            self.__color[x][y] = color
            self.__safe += 1
            self.__score_counter += 1
            print(f'open ({x}, {y})  color_number:{color}')
        else:
            return None

        if self.__board[x][y] == 0:
            for dir in ClearMine.Dir:
                xx, yy = x + dir[0], y + dir[1]
                if self.__judgeEdge(xx, yy) == False: continue
                if self.__color[xx][yy] == 0: 
                    self.__updateMask(xx, yy, color, False)
        elif F == True:
            for dir in ClearMine.Dir:
                xx, yy = x + dir[0], y + dir[1]
                if self.__judgeEdge(xx, yy) == False: continue
                if self.__color[xx][yy] == 0 and self.__board[xx][yy] == 0: 
                    self.__updateMask(xx, yy, color, False)

    def click(self, x : int, y : int, username : str) -> int:
        '''
        用户点击事件, 正数代表得分, 负数代表一些问题:
        -5: 越界, -2: 格子已经被扫开 -1: 点到雷
        '''
        if not self.__judgeEdge(x, y): return -5 # 越界
        if self.__color[x][y] != 0: return -2   # 格子已经被扫开

        color = self.__dict_user2number[username]

        self.__click_history.append((x, y, self.get_user_color_str(color)))
        self.__timmer += 1

        if username not in self.__rank:
            self.__rank[username] = {
                'boom' : 0, 
                'score' : 0,
                'color' : self.__dict_number2color[color],
                'username' : username,
            }

        if self.__board[x][y] == ClearMine.MINE: # 点到雷
            self.__color[x][y] = color
            self.__rank[username]['boom'] += 1
            return -1

        self.__score_counter = 0
        self.__updateMask(x, y, color)
        self.__rank[username]['score'] += self.__score_counter

        return self.__score_counter

    def set_flag(self, x: int, y: int, flag: int) -> None:
        '''设置某个格子的flag状态'''
        if self.__judgeEdge(x, y):
            self.__flags[x][y] = flag

    def get_flag(self, x: int, y: int) -> int:
        '''获取某个格子的flag状态'''
        if self.__judgeEdge(x, y):
            return int(self.__flags[x][y])
        return 0

    def get_all_flags(self) -> List[Tuple[int, int, int]]:
        '''获取所有格子的flag状态，返回(x, y, flag)列表'''
        result = []
        for i in range(self.__size_row):
            for j in range(self.__size_col):
                if self.__flags[i][j] != 0:
                    result.append((i, j, int(self.__flags[i][j])))
        return result

    def give_color(self, username : str) -> None:
        '''给新用户随机分配一个颜色'''
        if username not in self.__dict_user2number:
            self.__userIter += 1
            iter = self.__userIter

            self.__dict_user2number[username] = iter

            self.__dict_number2color[iter] = self.__ColorRander.rand_color()

    def get_user_color_num(self, username : str) -> Optional[int]:
        '''根据用户名获取用户的颜色数字'''
        if username not in self.__dict_user2number: return None
        return self.__dict_user2number[username]

    def get_user_color_str(self, color_id : int) -> Optional[str]:
        '''根据颜色数字获取用户颜色字符串'''
        if color_id not in self.__dict_number2color: return None
        return self.__dict_number2color[color_id]

    def get_click_history(self) -> List[Tuple[int, int, str]]:
        '''返回点击历史'''
        return self.__click_history

    def get_timmer(self) -> int:
        '''获取时间戳'''
        return self.__timmer

    def get_args(self) -> dict:
        '''获取游戏地图参数'''
        return {
            'row' : self.__size_row,
            'col' : self.__size_col,
            'partsize' : self.__part_size,
            'mine' : self.__part_mine_num,
            'mod' : self.__mod,
            'seed' : self.__seed,
        }

    def get_rank(self) -> dict:
        '''获取本局战绩'''
        return self.__rank

if __name__ == '__main__':
    pass
    
