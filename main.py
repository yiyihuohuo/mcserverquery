from pkg.plugin.context import register, handler, llm_func, BasePlugin, APIHost, EventContext # type: ignore
from pkg.plugin.events import * # type: ignore
import requests
import json
import asyncio

def query_minecraft_server(host, port):
    """查询Minecraft Java版服务器状态"""
    api_url = f"https://ping.lvjia.cc/mcapi.php?host={host}&port={port}"
    
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get('status') == 'success':
            return {
                'status': 'online',
                'version': result['data']['version'],
                'players': f"{result['data']['online']}/{result['data']['max']}",
                'motd': result['data']['description'],
                'query_time': result['data']['queryTime']
            }
        return {'status': 'error', 'message': '服务器返回错误状态'}
            
    except requests.exceptions.RequestException:
        return {'status': 'error', 'message': '服务器未响应或不可用'}
    except json.JSONDecodeError:
        return {'status': 'error', 'message': '服务器返回无效数据格式'}
    except KeyError as e:
        return {'status': 'error', 'message': f'数据字段缺失：{e}'}

@register(name="MC服务器查询", description="Minecraft服务器状态查询插件", version="1.1", author="RockChinQ")
class MinecraftQueryPlugin(BasePlugin):

    def __init__(self, host: APIHost):
        self.default_server = ("103.205.253.14", 23007)  # 默认服务器地址

    @handler(PersonNormalMessageReceived) # type: ignore
    @handler(GroupNormalMessageReceived) # type: ignore
    async def handle_message(self, ctx: EventContext):
        msg = ctx.event.text_message.strip()
        
        if msg.startswith("查询服务器"):
            args = msg.split()
            
            # 解析参数
            if len(args) == 1:  # 使用默认服务器
                host, port = self.default_server
            elif len(args) == 3:  # 自定义服务器
                try:
                    host = args[1]
                    port = int(args[2])
                except ValueError:
                    ctx.add_return("reply", ["⚠️ 端口号必须是数字！"])
                    ctx.prevent_default()
                    return
            else:
                ctx.add_return("reply", [
                    "⚠️ 指令格式错误！正确格式：\n",
                    "查询服务器 [IP] [端口]\n",
                    "示例：查询服务器 103.205.253.14 23007"
                ])
                ctx.prevent_default()
                return

            # 使用线程池执行阻塞操作
            try:
                # 通过事件循环托管阻塞调用
                result = await asyncio.get_event_loop().run_in_executor(
                    None,  # 使用默认线程池
                    query_minecraft_server,  # 要执行的函数
                    host, port  # 函数参数
                )
            except Exception as e:
                ctx.add_return("reply", [f"🔴 查询发生意外错误: {str(e)}"])
                ctx.prevent_default()
                return

            # 构建响应
            if result['status'] == 'online':
                reply = [
                    "🟢 我的世界服务器在线\n",
                    f"▫️ ip:{host}:{port}\n"
                    f"▫️ 版本: {result['version']}\n",
                    f"▫️ 玩家: {result['players']}\n",
                    f"▫️ MOTD: {result['motd']}\n",
                    f"▫️ 查询时间: {result['query_time']}"
                ]
            else:
                reply = [
                    "🔴 查询失败",
                    f"原因: {result['message']}"
                ]
                
            ctx.add_return("reply", reply)
            ctx.prevent_default()
