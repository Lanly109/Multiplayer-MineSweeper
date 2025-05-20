import threading
from flask import session, request
from flask_socketio import emit, join_room, leave_room, disconnect
from .objects import (
    CM_server, 
    clearmind_socketio, 
    cookie_user_dict, 
    DISCONNECT_TIME,
    print_and_log, 
    user_cookie, 
    gen_cookie,
    SERVER_WAIT_TIME,
    CM_logger,
)
import time
import json

@clearmind_socketio.on('connect', namespace='/wslogin')
def login_connect():
    '''
    收到登录请求,进行身份识别, 
    为用户生成cookie,
    发送cookie或拒绝信息
    '''
    print_and_log('收到登录请求...')
    try:
        username = request.args['username']
        password = request.args['password']
        print_and_log(f'name = {username}')

        # 先判断账号密码是否正确
        if CM_server.login(username, password) == True:
            # 生成cookie
            cookie = None
            while True:
                cookie = str(gen_cookie())
                if cookie not in cookie_user_dict:
                    break
            print_and_log('cookie生成完成...')

            # 如果用户多次登录, 撤销用户先前的cookie, 设置cookie, 并设置最近活跃时间
            if username in user_cookie:
                del cookie_user_dict[user_cookie[username]]
            user_cookie[username] = cookie
            cookie_user_dict[cookie] = (username, time.time())
            print_and_log('cookie重置完成...')

            emit('reply', cookie)
            print_and_log('emit cookie 完成...')
        else:
            emit('reply', 'deny')
            print_and_log('emit deny 完成...')
        
    except Exception as e:
        print_and_log('>>> error ' +  str(type(e)) + ' ' + str(e))
        disconnect()
        return False

@clearmind_socketio.on('disconnect', namespace='/wslogin')
def login_disconnect():
    '''登录连接断开时执行'''
    extra = ''
    try : 
        username = request.args['username']
        password = request.args['password']
        extra = username
    except:
        pass
    print_and_log(f'登录连接断开...   {username}')


@clearmind_socketio.on('connect', namespace='/wsregister')
def register_connect():
    '''
    收到注册请求后, 进行注册操作, 并发送事务结果
    回复报文:
        ok : 成功
        deny : 失败
        script : 用户涉嫌在数据库中注入script命令
    '''
    print_and_log('注册登录请求')
    try:
        invitecode = request.args['invitecode']
        username = request.args['username']
        password = request.args['password']
        register_ret = CM_server.register(invitecode, username, password)
        if register_ret == True:
            emit('reply', 'ok')
            print_and_log('emit ok 完成...')
        elif register_ret == None:
            emit('reply', 'script')
            print_and_log('emit script 完成...')
        else:
            emit('reply', 'deny')
            print_and_log('emit deny 完成...')

    except Exception as e:
        print_and_log('>>> error ' +  str(type(e)) + ' ' + str(e))
        disconnect()
        return False

@clearmind_socketio.on('disconnect', namespace='/wsregister')
def register_disconnect():
    '''登录链接断开后执行'''
    print_and_log('注册连接断开...')


@clearmind_socketio.on('connect', namespace='/wsmine')
def mine_connect():
    print_and_log('===> 扫雷连接成功...')
    try:
        judge = False
        cookie = request.args['cookie']
        username = ''
        if cookie in cookie_user_dict:
            username, tm = cookie_user_dict[cookie]
            if time.time() - tm < DISCONNECT_TIME:
                judge = True
            else:
                del user_cookie[username]
                del cookie_user_dict[cookie]
        if not judge: 
            raise Exception('身份过期')

        emit('args', json.dumps(CM_server.args()))
        print_and_log('emit args 完成')
        
        emit('history', json.dumps(CM_server.history()))
        print_and_log('emit history 完成')

        emit('all_flags', json.dumps(CM_server.get_all_flags()))
        print_and_log('emit all_flags 完成')

    except Exception as e:
        print_and_log('>>> error ' +  str(type(e)) + ' ' + str(e))
        disconnect()
        return False


@clearmind_socketio.on('disconnect', namespace='/wsmine')
def mine_disconnect():
    '''扫雷链接断开时, 注销用户cookie'''
    try:
        cookie = request.args['cookie']
        username, tm = cookie_user_dict[cookie]
        del user_cookie[username]
        del cookie_user_dict[cookie]
        print_and_log('cookie信息成功杀掉...')
    except:
        pass
    print_and_log('扫雷连接断开...')



@clearmind_socketio.on('click', namespace='/wsmine')
def mine_click(info):
    '''收到点击地图时间, 把数据中的参数抛给后端处理'''

    # # 若服务器ready码为假, 发送拒绝信息
    # if not CM_server.ready():
    #     emit('error', 'not ready')
    #     return False

    try :
        cookie = request.args['cookie']
        data = json.loads(info)
        x, y = data['x'], data['y']
        username, tm = cookie_user_dict[cookie]
    except Exception as e:
        print_and_log('>>> error ' +  str(type(e)) + ' ' + str(e))
        disconnect()
        return False

    print_and_log('点击信息解析完成...')

    # 判断身份是否过期
    if time.time() - tm > DISCONNECT_TIME: 
        emit('error', 'gone too long')
        disconnect()
        return False

    print_and_log('身份过期验证完成...')

    CM_server.give_color(username)
    snd, color, finish, timmer = CM_server.click(x, y, username)

    print_and_log('扫雷操作服务器执行成功...')

    # 更新最近活跃时间
    cookie_user_dict[cookie] = (username, time.time())

    if snd:
        print_and_log(f'广播坐标({x} {y}) {color} {username}' )
        emit('broadcast', json.dumps({'x' : x, 'y' : y, 'color' : color, 'timmer' : timmer, 'username' : username}), broadcast = True)
        print_and_log('广播坐标发完')

    if finish:
        emit('broadcast finish', 'finish', broadcast = True)
        print_and_log('emit 游戏结束 完成')

        emit('game end', json.dumps(CM_server.rank()), broadcast = True)
        print_and_log('本局最终战绩发送完成')

        # 可能在架构原理上存在一些问题, 暂时不开启一局结束后等待一段时间的功能
        # CM_server.restart(SERVER_WAIT_TIME)
        CM_server.restart()
        print_and_log('游戏成功重启...')

        while not CM_server.ready(): pass

        emit('args', json.dumps(CM_server.args()), broadcast = True)
        print_and_log('地图数据发送完成')


@clearmind_socketio.on('rank', namespace='/wsmine')
def getrank(info):
    '''发送查询到的本局战绩信息'''
    print_and_log('收到 查看本局榜 请求...')
    try :
        if info != 'query rank': return False
        cookie = request.args['cookie']
        username, tm = cookie_user_dict[cookie]

        # 判断身份是否过期
        if time.time() - tm > DISCONNECT_TIME: 
            emit('error', 'gone too long')
            raise Exception('身份过期')
        
        print_and_log(f'{username} 身份未过期')

        cookie_user_dict[cookie] = (username, time.time())
    except Exception as e:
        print_and_log('>>> error ' +  str(type(e)) + ' ' + str(e))
        disconnect()
        return False

    emit('rank_rev', json.dumps(CM_server.rank()))
    print_and_log('rank_rev 本局榜发送完成')

@clearmind_socketio.on('flag', namespace='/wsmine')
def handle_flag(info):
    '''同步旗子/问号标记到所有客户端'''
    print_and_log('收到 flag 标记同步请求...')
    try:
        cookie = request.args['cookie']
        username, tm = cookie_user_dict[cookie]
        # 判断身份是否过期
        if time.time() - tm > DISCONNECT_TIME:
            emit('error', 'gone too long')
            disconnect()
            return False
        # 更新最近活跃时间
        cookie_user_dict[cookie] = (username, time.time())

        # 解析前端发来的标记信息
        data = json.loads(info)
        x = data['x']
        y = data['y']
        flag = data['flag']
        # 存储flag到后端
        CM_server.set_flag(x, y, flag)

        # 直接广播标记变更
        emit('flag_broadcast', info, broadcast=True)
        print_and_log(f'flag 广播完成: {info}')
    except Exception as e:
        print_and_log('>>> error ' +  str(type(e)) + ' ' + str(e))
        disconnect()
        return False

@clearmind_socketio.on('connect', namespace='/wsrank')
def rank_connect():
    print_and_log('查看总榜链接成功...')

@clearmind_socketio.on('disconnect', namespace='/wsrank')
def rank_connect():
    print_and_log('查看总榜链接断开...')

@clearmind_socketio.on('total_rank', namespace='/wsrank')
def get_total_rank(info):
    '''发送查询到的战绩总榜信息'''
    try : 
        if info != 'query rank': return False
        cookie = request.args['cookie']
        username, tm = cookie_user_dict[cookie]

        # 判断身份是否过期
        if time.time() - tm > DISCONNECT_TIME: 
            emit('error', 'gone too long')
            raise Exception('身份过期')

        print_and_log(f'{username} 身份未过期')

        cookie_user_dict[cookie] = (username, time.time())
        emit('total_rank', json.dumps(CM_server.total_rank()))
        print_and_log('总榜信息发送完成...')

    except Exception as e:
        print_and_log('>>> error ' +  str(type(e)) + ' ' + str(e))
        disconnect()