#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram图床机器人 - 云存储版 (简化版，无统计系统)
支持自定义CDN域名、智能路由、缓存预热等高级功能
后端CDN缓存监控版本 - 修复重定向循环和文件路径过期问题
新增群组图片监听功能
"""
import logging
import hashlib
import time
import asyncio
import base64
import socket
import json
import os
import threading
import sqlite3
import sys
import atexit
import queue
import subprocess
import shutil
import signal
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv 未安装，将使用系统环境变量

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, render_template, jsonify, request, Response, send_file, make_response, redirect
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
import aiohttp
import requests

# 导入管理模块
import admin_module

# ===================== 配置参数 (支持环境变量) =====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
STORAGE_CHAT_ID = int(os.getenv("STORAGE_CHAT_ID", ""))
SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key_2024")
PORT = int(os.getenv("PORT", "18793"))

# 前端自动启动配置
FRONTEND_AUTOSTART = os.getenv("FRONTEND_AUTOSTART", "true").lower() == "true"
FRONTEND_DIR = os.path.join(os.getcwd(), "frontend")
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "3000"))
# 可自定义命令，如: "pnpm dev" 或 "yarn dev"
FRONTEND_DEV_CMD = os.getenv("FRONTEND_DEV_CMD", "npm run dev")

# 群组上传功能配置
ENABLE_GROUP_UPLOAD = os.getenv("ENABLE_GROUP_UPLOAD", "true").lower() == "true"
GROUP_UPLOAD_ADMIN_ONLY = os.getenv("GROUP_UPLOAD_ADMIN_ONLY", "false").lower() == "true"
GROUP_ADMIN_IDS = os.getenv("GROUP_ADMIN_IDS", "")  # 逗号分隔的管理员ID列表
GROUP_UPLOAD_REPLY = os.getenv("GROUP_UPLOAD_REPLY", "true").lower() == "true"  # 是否回复消息
GROUP_UPLOAD_DELETE_DELAY = int(os.getenv("GROUP_UPLOAD_DELETE_DELAY", "0"))  # 删除回复的延迟（秒），0表示不删除

# CDN 相关配置
CDN_ENABLED = os.getenv("CDN_ENABLED", "true").lower() == "true"
CDN_CACHE_TTL = int(os.getenv("CDN_CACHE_TTL", "31536000"))  # 默认一年
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")

# CDN重定向配置（新增）
CDN_REDIRECT_ENABLED = os.getenv("CDN_REDIRECT_ENABLED", "true").lower() == "true"  # 是否启用CDN重定向
CDN_REDIRECT_MAX_COUNT = int(os.getenv("CDN_REDIRECT_MAX_COUNT", "2"))  # 最大重定向次数
CDN_REDIRECT_CACHE_TIME = int(os.getenv("CDN_REDIRECT_CACHE_TIME", "300"))  # 重定向缓存时间（秒）
CDN_REDIRECT_DELAY = int(os.getenv("CDN_REDIRECT_DELAY", "10"))  # 新上传文件延迟重定向时间（秒）

# Cloudflare CDN 特定配置
CLOUDFLARE_CDN_DOMAIN = os.getenv("CLOUDFLARE_CDN_DOMAIN", "")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID", "")
CLOUDFLARE_CACHE_LEVEL = os.getenv("CLOUDFLARE_CACHE_LEVEL", "aggressive")
CLOUDFLARE_BROWSER_TTL = int(os.getenv("CLOUDFLARE_BROWSER_TTL", "14400"))
CLOUDFLARE_EDGE_TTL = int(os.getenv("CLOUDFLARE_EDGE_TTL", "2592000"))

# 智能路由配置
ENABLE_SMART_ROUTING = os.getenv("ENABLE_SMART_ROUTING", "true").lower() == "true"
FALLBACK_TO_ORIGIN = os.getenv("FALLBACK_TO_ORIGIN", "true").lower() == "true"

# 缓存预热配置
ENABLE_CACHE_WARMING = os.getenv("ENABLE_CACHE_WARMING", "true").lower() == "true"
CACHE_WARMING_DELAY = int(os.getenv("CACHE_WARMING_DELAY", "5"))

# CDN缓存监控配置
CDN_MONITOR_ENABLED = os.getenv("CDN_MONITOR_ENABLED", "true").lower() == "true"
CDN_MONITOR_INTERVAL = int(os.getenv("CDN_MONITOR_INTERVAL", "5"))  # 检查间隔（秒）
CDN_MONITOR_MAX_RETRIES = int(os.getenv("CDN_MONITOR_MAX_RETRIES", "15"))  # 最大重试次数
CDN_MONITOR_QUEUE_SIZE = int(os.getenv("CDN_MONITOR_QUEUE_SIZE", "1000"))  # 队列大小

# 版本控制
STATIC_VERSION = os.getenv("STATIC_VERSION", str(int(time.time())))
FORCE_REFRESH = os.getenv("FORCE_REFRESH", "false").lower() == "true"

# 数据库路径
DEFAULT_DB_PATH = os.path.join(os.getcwd(), "telegram_imagebed.db")
DATABASE_PATH = os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)

# 确保数据库目录存在
db_dir = os.path.dirname(DATABASE_PATH)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "telegram_imagebed.log")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=getattr(logging, LOG_LEVEL.upper()),
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 单实例锁文件
if sys.platform == 'win32':
    LOCK_FILE = os.path.join(os.environ.get('TEMP', '.'), 'telegram_imagebed.lock')
else:
    LOCK_FILE = '/tmp/telegram_imagebed.lock'

# 打印配置信息
logger.info("=" * 60)
logger.info("Telegram 图床机器人 - 简化版（后端CDN监控）")
logger.info("=" * 60)
logger.info(f"BOT_TOKEN: {'已配置' if BOT_TOKEN else '未配置'}")
logger.info(f"STORAGE_CHAT_ID: {STORAGE_CHAT_ID}")
logger.info(f"PORT: {PORT}")
logger.info(f"DATABASE_PATH: {DATABASE_PATH}")
logger.info(f"CDN_ENABLED: {CDN_ENABLED}")
logger.info(f"群组上传功能: {ENABLE_GROUP_UPLOAD}")
if ENABLE_GROUP_UPLOAD:
    logger.info(f"仅管理员: {GROUP_UPLOAD_ADMIN_ONLY}")
    logger.info(f"管理员ID: {GROUP_ADMIN_IDS or '未配置'}")
    logger.info(f"回复消息: {GROUP_UPLOAD_REPLY}")
if CDN_ENABLED:
    logger.info(f"CLOUDFLARE_CDN_DOMAIN: {CLOUDFLARE_CDN_DOMAIN or '未配置'}")
    logger.info(f"智能路由: {ENABLE_SMART_ROUTING}")
    logger.info(f"缓存预热: {ENABLE_CACHE_WARMING}")
    logger.info(f"CDN监控: {CDN_MONITOR_ENABLED}")
    logger.info(f"CDN重定向: {CDN_REDIRECT_ENABLED}")
    logger.info(f"最大重定向次数: {CDN_REDIRECT_MAX_COUNT}")
    logger.info(f"新文件重定向延迟: {CDN_REDIRECT_DELAY}秒")
logger.info("=" * 60)

# 解析管理员ID列表
GROUP_ADMIN_ID_LIST = []
if GROUP_ADMIN_IDS:
    try:
        GROUP_ADMIN_ID_LIST = [int(id.strip()) for id in GROUP_ADMIN_IDS.split(',') if id.strip()]
        logger.info(f"已配置 {len(GROUP_ADMIN_ID_LIST)} 个群组管理员ID")
    except Exception as e:
        logger.error(f"解析管理员ID列表失败: {e}")

# ===================== 单实例锁 =====================
def acquire_lock():
    """获取锁以确保只有一个实例在运行"""
    try:
        if sys.platform == 'win32':
            import msvcrt
            global lock_file_handle
            lock_file_handle = open(LOCK_FILE, 'w')
            try:
                msvcrt.locking(lock_file_handle.fileno(), msvcrt.LK_NBLCK, 1)
                return True
            except IOError:
                logger.error("另一个实例正在运行")
                return False
        else:
            import fcntl
            global lock_fd
            lock_fd = open(LOCK_FILE, 'w')
            try:
                fcntl.lockf(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except IOError:
                logger.error("另一个实例正在运行")
                return False
    except Exception as e:
        logger.error(f"获取锁失败: {e}")
        return False

def release_lock():
    """释放锁"""
    try:
        if sys.platform == 'win32':
            if 'lock_file_handle' in globals():
                lock_file_handle.close()
                if os.path.exists(LOCK_FILE):
                    os.remove(LOCK_FILE)
        else:
            if 'lock_fd' in globals():
                lock_fd.close()
                if os.path.exists(LOCK_FILE):
                    os.remove(LOCK_FILE)
    except Exception as e:
        logger.error(f"释放锁失败: {e}")

atexit.register(release_lock)

# ===================== 获取本机IPv4地址 =====================
def get_local_ip():
    """获取本机IPv4地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except Exception:
            return "127.0.0.1"

LOCAL_IP = get_local_ip()

# ===================== Flask应用和数据存储 =====================
# 注意：前端静态文件已内置到Flask中，统一端口服务
STATIC_FOLDER = os.path.join(os.getcwd(), "frontend", ".output", "public")
# 禁用Flask自动静态文件处理，改用catch_all路由手动处理
app = Flask(__name__, static_folder=None)

# 应用ProxyFix中间件
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# CORS配置 - 更完善的配置
CORS(app, resources={
    r"/api/*": {
        "origins": ALLOWED_ORIGINS.split(',') if ALLOWED_ORIGINS != "*" else "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
        "supports_credentials": True,
        "max_age": 3600
    },
    r"/image/*": {
        "origins": "*",
        "methods": ["GET", "HEAD", "OPTIONS"],
        "allow_headers": ["Content-Type", "Range", "Cache-Control"],
        "expose_headers": ["Content-Length", "Content-Range", "Accept-Ranges", "ETag", "Cache-Control"],
        "max_age": 86400
    },
    r"/static/*": {
        "origins": "*",
        "methods": ["GET", "HEAD", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "max_age": 86400
    }
})

app.secret_key = SECRET_KEY

# 配置管理员会话
admin_module.configure_admin_session(app)

# 全局变量
start_time = time.time()
telegram_app = None
bot_info = None  # 存储机器人信息

# CDN缓存监控队列
cdn_monitor_queue = queue.Queue(maxsize=CDN_MONITOR_QUEUE_SIZE)
cdn_monitor_thread = None
cdn_monitor_running = False

# ===================== 静态文件版本管理 =====================
def get_static_file_version(filename):
    """获取静态文件版本号"""
    if FORCE_REFRESH:
        return str(int(time.time()))
    return STATIC_VERSION

app.jinja_env.globals.update(get_static_file_version=get_static_file_version)

# ===================== Cloudflare CDN 集成 =====================
class CloudflareCDN:
    """Cloudflare CDN 管理类"""
    
    def __init__(self):
        self.api_token = CLOUDFLARE_API_TOKEN
        self.zone_id = CLOUDFLARE_ZONE_ID
        self.cdn_domain = CLOUDFLARE_CDN_DOMAIN
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
        self.base_url = 'https://api.cloudflare.com/client/v4'
    
    def purge_cache(self, urls: List[str]) -> bool:
        """清除指定URL的缓存"""
        if not self.api_token or not self.zone_id:
            return False
        
        try:
            response = requests.post(
                f'{self.base_url}/zones/{self.zone_id}/purge_cache',
                headers=self.headers,
                json={'files': urls}
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Cloudflare缓存清除失败: {e}")
            return False
    
    def check_cdn_status(self, encrypted_id: str) -> bool:
        """检查图片是否被CDN缓存 - 修复版"""
        if not self.cdn_domain:
            return False
        
        try:
            cdn_url = f"https://{self.cdn_domain}/image/{encrypted_id}"
            
            # 发送HEAD请求检查，添加特殊头部避免触发重定向
            headers = {
                'User-Agent': 'CDN-Status-Checker/1.0',
                'X-CDN-Check': 'true',
                'X-Skip-Redirect': 'true'
            }
            
            response = requests.head(
                cdn_url, 
                timeout=10, 
                allow_redirects=False,  # 不跟随重定向
                headers=headers
            )
            
            # 如果返回302重定向，说明还未缓存
            if response.status_code == 302:
                logger.debug(f"图片 {encrypted_id} 返回302重定向，未被CDN缓存")
                return False
            
            # 检查CF-Cache-Status头部
            cache_status = response.headers.get('CF-Cache-Status', '')
            
            # HIT、STALE、UPDATING、REVALIDATED都认为是已缓存
            cached = cache_status in ['HIT', 'STALE', 'UPDATING', 'REVALIDATED']
            
            # 如果状态码是200且有缓存状态，也认为是已缓存
            if response.status_code == 200 and cache_status:
                cached = True
            
            if cached:
                logger.info(f"图片 {encrypted_id} CDN缓存状态: {cache_status}")
            else:
                logger.debug(f"图片 {encrypted_id} CDN缓存状态: {cache_status or 'MISS'}")
            
            return cached
            
        except requests.exceptions.Timeout:
            logger.warning(f"检查CDN状态超时 {encrypted_id}")
            return False
        except Exception as e:
            logger.debug(f"检查CDN状态失败 {encrypted_id}: {e}")
            return False
    
    async def warm_cache(self, url: str, encrypted_id: str = None):
        """预热缓存 - 修复版"""
        if not ENABLE_CACHE_WARMING:
            return
        
        if not encrypted_id and '/image/' in url:
            encrypted_id = url.split('/image/')[-1].split('?')[0]
        
        await asyncio.sleep(CACHE_WARMING_DELAY)
        
        try:
            edge_locations = ['sfo', 'lax', 'ord', 'dfw', 'iad', 'lhr', 'fra', 'nrt', 'sin']
            
            async with aiohttp.ClientSession() as session:
                tasks = []
                for location in edge_locations:
                    headers = {
                        'CF-IPCountry': location.upper(),
                        'User-Agent': 'Cloudflare-Cache-Warmer/1.0',
                        'X-Cache-Warming': 'true'
                    }
                    task = session.get(url, headers=headers, timeout=10, allow_redirects=True)
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                success_count = sum(1 for r in results if not isinstance(r, Exception) and r.status in [200, 304])
                logger.info(f"缓存预热完成: {url}, 成功: {success_count}/{len(edge_locations)}")
                
                if success_count > 0 and encrypted_id:
                    update_cdn_cache_status(encrypted_id, True)
                
        except Exception as e:
            logger.error(f"缓存预热失败: {e}")

cloudflare_cdn = CloudflareCDN()

# ===================== CDN缓存监控线程 =====================
def cdn_cache_monitor_worker():
    """CDN缓存监控工作线程"""
    global cdn_monitor_running
    
    logger.info("CDN缓存监控线程启动")
    
    while cdn_monitor_running:
        try:
            # 从队列获取任务（阻塞最多5秒）
            try:
                task = cdn_monitor_queue.get(timeout=5)
            except queue.Empty:
                continue
            
            if task is None:  # 停止信号
                break
            
            encrypted_id = task['encrypted_id']
            retries = task.get('retries', 0)
            upload_time = task.get('upload_time', time.time())
            
            # 检查是否已经缓存
            file_info = get_file_info(encrypted_id)
            if file_info and file_info.get('cdn_cached'):
                logger.debug(f"图片 {encrypted_id} 已标记为缓存，跳过检查")
                continue
            
            # 检查CDN缓存状态
            is_cached = cloudflare_cdn.check_cdn_status(encrypted_id)
            
            if is_cached:
                # 更新数据库
                update_cdn_cache_status(encrypted_id, True)
                logger.info(f"✅ 图片 {encrypted_id} 已被CDN缓存（第{retries + 1}次检查）")
            else:
                # 未缓存，检查是否需要重试
                if retries < CDN_MONITOR_MAX_RETRIES:
                    # 重新加入队列
                    time.sleep(CDN_MONITOR_INTERVAL)
                    task['retries'] = retries + 1
                    
                    try:
                        cdn_monitor_queue.put(task, block=False)
                        logger.debug(f"图片 {encrypted_id} 第{retries + 1}次检查未缓存，继续监测...")
                    except queue.Full:
                        logger.warning(f"CDN监控队列已满，放弃监控 {encrypted_id}")
                else:
                    # 超过最大重试次数
                    logger.warning(f"图片 {encrypted_id} 在{CDN_MONITOR_MAX_RETRIES * CDN_MONITOR_INTERVAL}秒内未被缓存")
                    
                    # 尝试主动预热
                    if ENABLE_CACHE_WARMING and CLOUDFLARE_CDN_DOMAIN:
                        cdn_url = f"https://{CLOUDFLARE_CDN_DOMAIN}/image/{encrypted_id}"
                        logger.info(f"尝试主动预热CDN: {encrypted_id}")
                        
                        try:
                            # 同步预热请求
                            response = requests.get(cdn_url, timeout=30)
                            if response.status_code == 200:
                                logger.info(f"CDN预热成功: {encrypted_id}")
                                # 稍后再检查一次
                                time.sleep(5)
                                if cloudflare_cdn.check_cdn_status(encrypted_id):
                                    update_cdn_cache_status(encrypted_id, True)
                        except Exception as e:
                            logger.error(f"CDN预热失败: {e}")
            
        except Exception as e:
            logger.error(f"CDN监控线程错误: {e}")
            time.sleep(1)
    
    logger.info("CDN缓存监控线程已停止")

def start_cdn_monitor():
    """启动CDN监控线程"""
    global cdn_monitor_thread, cdn_monitor_running
    
    if not CDN_ENABLED or not CLOUDFLARE_CDN_DOMAIN or not CDN_MONITOR_ENABLED:
        logger.info("CDN监控未启用")
        return
    
    if cdn_monitor_thread and cdn_monitor_thread.is_alive():
        logger.warning("CDN监控线程已在运行")
        return
    
    cdn_monitor_running = True
    cdn_monitor_thread = threading.Thread(target=cdn_cache_monitor_worker, daemon=True)
    cdn_monitor_thread.start()
    logger.info("CDN监控已启动")

def stop_cdn_monitor():
    """停止CDN监控线程"""
    global cdn_monitor_running
    
    if not cdn_monitor_thread:
        return
    
    logger.info("正在停止CDN监控...")
    cdn_monitor_running = False
    
    # 发送停止信号
    try:
        cdn_monitor_queue.put(None, block=False)
    except:
        pass
    
    # 等待线程结束
    if cdn_monitor_thread.is_alive():
        cdn_monitor_thread.join(timeout=10)
    
    logger.info("CDN监控已停止")

def add_to_cdn_monitor(encrypted_id: str, upload_time: int = None):
    """添加图片到CDN监控队列"""
    if not CDN_MONITOR_ENABLED or not CLOUDFLARE_CDN_DOMAIN:
        return
    
    task = {
        'encrypted_id': encrypted_id,
        'upload_time': upload_time or int(time.time()),
        'retries': 0
    }
    
    try:
        cdn_monitor_queue.put(task, block=False)
        logger.info(f"图片 {encrypted_id} 已加入CDN监控队列")
    except queue.Full:
        logger.warning(f"CDN监控队列已满，无法添加 {encrypted_id}")

# ===================== 数据库初始化 =====================
def init_database():
    """初始化数据库 - 简化版，无统计表"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # 创建主表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_storage (
                encrypted_id TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                upload_time INTEGER NOT NULL,
                user_id INTEGER,
                username TEXT,
                file_size INTEGER,
                source TEXT,
                original_filename TEXT,
                mime_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                etag TEXT,
                file_hash TEXT,
                cdn_url TEXT,
                cdn_cached BOOLEAN DEFAULT 0,
                cdn_cache_time TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP,
                last_file_path_update TIMESTAMP,
                is_group_upload BOOLEAN DEFAULT 0,
                group_message_id INTEGER,
                auth_token TEXT
            )
        ''')

        # 创建auth_tokens表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auth_tokens (
                token TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                last_used TIMESTAMP,
                upload_count INTEGER DEFAULT 0,
                upload_limit INTEGER DEFAULT 100,
                is_active BOOLEAN DEFAULT 1,
                ip_address TEXT,
                user_agent TEXT,
                description TEXT
            )
        ''')

        # 创建公告表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enabled BOOLEAN DEFAULT 1,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 插入默认公告（如果表为空）
        cursor.execute('SELECT COUNT(*) FROM announcements')
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO announcements (enabled, content) VALUES (?, ?)
            ''', (1, '''
                <div class="space-y-4">
                    <h3 class="text-xl font-bold text-gray-900 dark:text-white">欢迎使用 Telegram 云图床</h3>
                    <div class="space-y-2 text-gray-700 dark:text-gray-300">
                        <p>🎉 <strong>无限制使用：</strong>无上传数量限制，无时间限制</p>
                        <p>🚀 <strong>CDN加速：</strong>全球CDN加速，访问更快</p>
                        <p>🔒 <strong>安全可靠：</strong>基于Telegram云存储，永久保存</p>
                        <p>💎 <strong>Token模式：</strong>生成专属Token，管理您的图片</p>
                    </div>
                </div>
            '''))

        # 创建管理员配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 插入默认管理员配置（如果表为空）
        cursor.execute("SELECT COUNT(*) FROM admin_config")
        if cursor.fetchone()[0] == 0:
            import hashlib
            default_username = os.getenv("ADMIN_USERNAME", "admin")
            default_password = os.getenv("ADMIN_PASSWORD", "admin123")
            password_hash = hashlib.sha256(default_password.encode()).hexdigest()

            cursor.execute("INSERT INTO admin_config (key, value) VALUES (?, ?)",
                          ('username', default_username))
            cursor.execute("INSERT INTO admin_config (key, value) VALUES (?, ?)",
                          ('password_hash', password_hash))
            logger.info(f"已初始化管理员配置: 用户名={default_username}")
        
        # 检查并添加新列（用于升级现有数据库）
        cursor.execute("PRAGMA table_info(file_storage)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # 添加缺失的列
        if 'is_group_upload' not in columns:
            logger.info("添加 is_group_upload 列")
            cursor.execute('ALTER TABLE file_storage ADD COLUMN is_group_upload BOOLEAN DEFAULT 0')
        
        if 'group_message_id' not in columns:
            logger.info("添加 group_message_id 列")
            cursor.execute('ALTER TABLE file_storage ADD COLUMN group_message_id INTEGER')
        
        if 'last_file_path_update' not in columns:
            logger.info("添加 last_file_path_update 列")
            cursor.execute('ALTER TABLE file_storage ADD COLUMN last_file_path_update TIMESTAMP')
        
        if 'etag' not in columns:
            logger.info("添加 etag 列")
            cursor.execute('ALTER TABLE file_storage ADD COLUMN etag TEXT')
        
        if 'file_hash' not in columns:
            logger.info("添加 file_hash 列")
            cursor.execute('ALTER TABLE file_storage ADD COLUMN file_hash TEXT')
        
        if 'cdn_url' not in columns:
            logger.info("添加 cdn_url 列")
            cursor.execute('ALTER TABLE file_storage ADD COLUMN cdn_url TEXT')
        
        if 'cdn_cached' not in columns:
            logger.info("添加 cdn_cached 列")
            cursor.execute('ALTER TABLE file_storage ADD COLUMN cdn_cached BOOLEAN DEFAULT 0')
        
        if 'cdn_cache_time' not in columns:
            logger.info("添加 cdn_cache_time 列")
            cursor.execute('ALTER TABLE file_storage ADD COLUMN cdn_cache_time TIMESTAMP')
        
        if 'access_count' not in columns:
            logger.info("添加 access_count 列")
            cursor.execute('ALTER TABLE file_storage ADD COLUMN access_count INTEGER DEFAULT 0')
        
        if 'last_accessed' not in columns:
            logger.info("添加 last_accessed 列")
            cursor.execute('ALTER TABLE file_storage ADD COLUMN last_accessed TIMESTAMP')

        if 'auth_token' not in columns:
            logger.info("添加 auth_token 列")
            cursor.execute('ALTER TABLE file_storage ADD COLUMN auth_token TEXT')

        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_storage_created ON file_storage(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_original_filename ON file_storage(original_filename)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_size ON file_storage(file_size)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cdn_cached ON file_storage(cdn_cached)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_group_upload ON file_storage(is_group_upload)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_auth_token ON file_storage(auth_token)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_auth_tokens_expires ON auth_tokens(expires_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_auth_tokens_active ON auth_tokens(is_active)')
        
        conn.commit()
        conn.close()
        logger.info(f"数据库初始化完成: {DATABASE_PATH}")
        
        # 恢复未完成的CDN监控任务
        if CDN_MONITOR_ENABLED:
            restore_cdn_monitor_tasks()
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise

def restore_cdn_monitor_tasks():
    """恢复未完成的CDN监控任务"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # 查找未缓存的近期图片（24小时内）
        cursor.execute('''
            SELECT encrypted_id, upload_time FROM file_storage 
            WHERE cdn_cached = 0 
            AND upload_time > ? 
            AND cdn_url IS NOT NULL
            ORDER BY upload_time DESC
            LIMIT 100
        ''', (int(time.time()) - 86400,))
        
        rows = cursor.fetchall()
        conn.close()
        
        if rows:
            logger.info(f"恢复 {len(rows)} 个CDN监控任务")
            for encrypted_id, upload_time in rows:
                add_to_cdn_monitor(encrypted_id, upload_time)
        
    except Exception as e:
        logger.error(f"恢复CDN监控任务失败: {e}")

# ===================== 获取域名函数 =====================
def get_domain(request):
    """根据请求动态获取域名"""
    if request:
        if CDN_ENABLED and CLOUDFLARE_CDN_DOMAIN:
            if request.path.startswith('/api/'):
                pass
            else:
                return f"https://{CLOUDFLARE_CDN_DOMAIN}"
        
        cf_visitor = request.headers.get('CF-Visitor')
        if cf_visitor:
            try:
                visitor_data = json.loads(cf_visitor)
                scheme = visitor_data.get('scheme', 'https')
            except:
                scheme = 'https'
        else:
            scheme = request.headers.get('X-Forwarded-Proto', 'http')
        
        host = (request.headers.get('X-Forwarded-Host') or 
                request.headers.get('Host') or 
                request.host)
        
        base_url = f"{scheme}://{host}"
        
        forwarded_prefix = request.headers.get('X-Forwarded-Prefix', '')
        if forwarded_prefix:
            base_url += forwarded_prefix.rstrip('/')
            
        return base_url
    
    return f"http://{LOCAL_IP}:{PORT}"

# ===================== 基础函数 =====================
def get_fresh_file_path(file_id: str) -> Optional[str]:
    """通过Telegram API获取最新的文件路径"""
    if not BOT_TOKEN or not file_id:
        return None
    
    try:
        # 调用getFile API获取最新的file_path
        response = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
            params={'file_id': file_id},
            timeout=10
        )
        
        if response.ok:
            result = response.json()
            if result.get('ok') and result.get('result'):
                file_path = result['result'].get('file_path')
                logger.debug(f"获取最新file_path成功: {file_id} -> {file_path}")
                return file_path
        
        logger.error(f"获取文件路径失败: {response.text}")
        return None
        
    except Exception as e:
        logger.error(f"获取文件路径异常: {e}")
        return None

def update_file_path_in_db(encrypted_id: str, new_file_path: str):
    """更新数据库中的文件路径"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE file_storage 
            SET file_path = ?, last_file_path_update = CURRENT_TIMESTAMP
            WHERE encrypted_id = ?
        ''', (new_file_path, encrypted_id))
        conn.commit()
        logger.debug(f"更新file_path: {encrypted_id} -> {new_file_path}")
    except Exception as e:
        logger.error(f"更新file_path失败: {e}")
    finally:
        conn.close()

def update_cdn_cache_status(encrypted_id: str, cached: bool):
    """更新CDN缓存状态"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE file_storage 
            SET cdn_cached = ?, cdn_cache_time = CURRENT_TIMESTAMP
            WHERE encrypted_id = ?
        ''', (1 if cached else 0, encrypted_id))
        conn.commit()
        logger.info(f"更新CDN缓存状态: {encrypted_id} -> {'已缓存' if cached else '未缓存'}")
    except Exception as e:
        logger.error(f"更新CDN缓存状态失败: {e}")
    finally:
        conn.close()

def update_access_count(encrypted_id: str):
    """更新访问计数"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE file_storage 
            SET access_count = access_count + 1,
                last_accessed = CURRENT_TIMESTAMP
            WHERE encrypted_id = ?
        ''', (encrypted_id,))
        conn.commit()
    except Exception as e:
        logger.error(f"更新访问计数失败: {e}")
    finally:
        conn.close()

def get_file_info(encrypted_id: str) -> Optional[Dict[str, Any]]:
    """获取文件信息"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT * FROM file_storage 
            WHERE encrypted_id = ?
        ''', (encrypted_id,))
        
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"获取文件信息失败: {e}")
        return None
    finally:
        conn.close()

def save_file_info(encrypted_id: str, file_info: Dict[str, Any]):
    """保存文件信息到数据库"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        etag = f'W/"{encrypted_id}-{file_info.get("file_size", 0)}"'
        
        cdn_url = None
        if CDN_ENABLED and CLOUDFLARE_CDN_DOMAIN:
            cdn_url = f"https://{CLOUDFLARE_CDN_DOMAIN}/image/{encrypted_id}"
        
        # 检查表结构，动态构建INSERT语句
        cursor.execute("PRAGMA table_info(file_storage)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # 基础字段（所有版本都有的）
        insert_columns = ['encrypted_id', 'file_id', 'file_path', 'upload_time',
                         'username', 'file_size', 'source',
                         'original_filename', 'mime_type']
        insert_values = [
            encrypted_id,
            file_info['file_id'],
            file_info.get('file_path', ''),  # 添加file_path字段
            file_info['upload_time'],
            file_info.get('username', 'unknown'),
            file_info.get('file_size', 0),
            file_info.get('source', 'unknown'),
            file_info.get('original_filename', ''),
            file_info.get('mime_type', 'image/jpeg')
        ]
        
        # 可选字段（新版本添加的）
        optional_fields = {
            'etag': etag,
            'file_hash': file_info.get('file_hash', ''),
            'cdn_url': cdn_url,
            'cdn_cached': 0,
            'created_at': datetime.now().isoformat(),  # 添加创建时间用于今日上传统计
            'is_group_upload': file_info.get('is_group_upload', 0),
            'group_message_id': file_info.get('group_message_id', None),
            'auth_token': file_info.get('auth_token', None)  # 添加Token字段
        }
        
        # 只添加存在的列
        for col, val in optional_fields.items():
            if col in columns:
                insert_columns.append(col)
                insert_values.append(val)
        
        # 构建SQL语句
        placeholders = ','.join(['?' for _ in insert_columns])
        columns_str = ','.join(insert_columns)
        
        cursor.execute(f'''
            INSERT INTO file_storage ({columns_str}) 
            VALUES ({placeholders})
        ''', insert_values)
        
        conn.commit()
        logger.info(f"文件信息已保存: {encrypted_id}")
        
        # 添加到CDN监控队列
        if CDN_ENABLED and CLOUDFLARE_CDN_DOMAIN and CDN_MONITOR_ENABLED:
            add_to_cdn_monitor(encrypted_id, file_info['upload_time'])
        
        # 触发异步缓存预热
        if CDN_ENABLED and ENABLE_CACHE_WARMING and cdn_url:
            asyncio.create_task(cloudflare_cdn.warm_cache(cdn_url, encrypted_id))
        
    except Exception as e:
        logger.error(f"保存文件信息失败: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_stats() -> Dict[str, Any]:
    """获取基础统计信息"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # 获取总文件数和大小
        cursor.execute('SELECT COUNT(*), SUM(file_size) FROM file_storage')
        total_files, total_size = cursor.fetchone()
        total_size = total_size or 0

        # 获取今日上传数 - 修复日期查询
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)

        # 使用时间戳范围查询，兼容不同的日期格式
        today_start_ts = int(today_start.timestamp())
        today_end_ts = int(today_end.timestamp())

        cursor.execute('''
            SELECT COUNT(*) FROM file_storage
            WHERE upload_time >= ? AND upload_time <= ?
        ''', (today_start_ts, today_end_ts))
        today_uploads = cursor.fetchone()[0]
        
        # 获取CDN缓存的文件数
        cursor.execute('SELECT COUNT(*) FROM file_storage WHERE cdn_cached = 1')
        cached_files = cursor.fetchone()[0]
        
        # 获取待缓存数
        cursor.execute('SELECT COUNT(*) FROM file_storage WHERE cdn_cached = 0 AND cdn_url IS NOT NULL')
        pending_cache = cursor.fetchone()[0]
        
        # 获取群组上传数（检查列是否存在）
        group_uploads = 0
        cursor.execute("PRAGMA table_info(file_storage)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_group_upload' in columns:
            cursor.execute('SELECT COUNT(*) FROM file_storage WHERE is_group_upload = 1')
            group_uploads = cursor.fetchone()[0]
        
        return {
            'total_files': total_files,
            'total_size': total_size,
            'today_uploads': today_uploads,
            'group_uploads': group_uploads,
            'cdn_stats': {
                'cached_files': cached_files,
                'pending_cache': pending_cache,
                'monitor_queue_size': cdn_monitor_queue.qsize() if CDN_MONITOR_ENABLED else 0
            }
        }
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return {
            'total_files': 0,
            'total_size': 0,
            'today_uploads': 0,
            'group_uploads': 0,
            'cdn_stats': {
                'cached_files': 0,
                'pending_cache': 0,
                'monitor_queue_size': 0
            }
        }
    finally:
        conn.close()

def get_recent_uploads(limit: int = 10, page: int = 1) -> list:
    """获取最近上传的文件"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        offset = (page - 1) * limit
        
        # 检查列是否存在
        cursor.execute("PRAGMA table_info(file_storage)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # 构建SELECT语句
        select_columns = ['encrypted_id', 'original_filename', 'file_size', 
                         'created_at', 'username', 'cdn_cached']
        
        if 'is_group_upload' in columns:
            select_columns.append('is_group_upload')
        
        columns_str = ', '.join(select_columns)
        
        cursor.execute(f'''
            SELECT {columns_str}
            FROM file_storage
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        results = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            # 如果没有 is_group_upload 列，默认为 0
            if 'is_group_upload' not in row_dict:
                row_dict['is_group_upload'] = 0
            results.append(row_dict)
        
        return results
    except:
        return []
    finally:
        conn.close()

# ===================== CDN缓存装饰器 =====================
def add_cache_headers(response, cache_type='public', max_age=None):
    """添加CDN缓存头部"""
    
    if 'Cache-Control' in response.headers and cache_type == 'public':
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response
    
    if not CDN_ENABLED:
        if cache_type == 'static':
            response.headers['Cache-Control'] = 'public, max-age=3600'
        else:
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
    
    if max_age is None:
        max_age = CDN_CACHE_TTL
    
    if cache_type == 'public':
        response.headers['Cache-Control'] = f'public, max-age={max_age}, s-maxage={CLOUDFLARE_EDGE_TTL}, stale-while-revalidate=86400, stale-if-error=604800'
        response.headers['Cloudflare-CDN-Cache-Control'] = f'max-age={CLOUDFLARE_EDGE_TTL}'
        response.headers['CDN-Cache-Control'] = f'max-age={CLOUDFLARE_EDGE_TTL}'
    elif cache_type == 'private':
        response.headers['Cache-Control'] = f'private, max-age={max_age}'
    elif cache_type == 'no-cache':
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    elif cache_type == 'static':
        response.headers['Cache-Control'] = f'public, max-age={CLOUDFLARE_BROWSER_TTL}, s-maxage={CLOUDFLARE_EDGE_TTL}'
    
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    if cache_type in ['public', 'static']:
        response.headers['CF-Cache-Tag'] = 'imagebed'
    
    return response

# ===================== Flask路由 =====================
@app.route('/')
def index():
    """返回主页 - 服务前端静态文件"""
    index_path = os.path.join(STATIC_FOLDER, 'index.html')
    if os.path.exists(index_path):
        return send_file(index_path)
    else:
        return jsonify({
            'error': '前端文件未找到',
            'message': '请先运行 cd frontend && npm run generate 构建前端',
            'api_base': get_domain(request)
        }), 404

@app.route('/image/<encrypted_id>', methods=['GET', 'HEAD', 'OPTIONS'])
def serve_image(encrypted_id):
    """代理提供Telegram图片服务 - 修复文件路径过期和加载问题"""
    
    # 处理OPTIONS预检请求
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, HEAD, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Range, Content-Type, Cache-Control'
        response.headers['Access-Control-Max-Age'] = '86400'
        return response
    
    # 获取文件信息
    file_info = get_file_info(encrypted_id)
    
    if not file_info:
        logger.warning(f"图片未找到: {encrypted_id}")
        response = Response(b'Image not found', status=404, mimetype='text/plain')
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache')
    
    # 检查是否是CDN回源请求
    cf_headers = {k: v for k, v in request.headers.items() if k.startswith('CF-')}
    is_cdn_request = bool(cf_headers.get('CF-Connecting-IP'))
    
    # 检查是否来自CDN域名（避免重定向循环）
    host = request.headers.get('Host', '')
    is_from_cdn_domain = CLOUDFLARE_CDN_DOMAIN and host == CLOUDFLARE_CDN_DOMAIN
    
    # 检查Referer是否来自CDN（额外的循环检测）
    referer = request.headers.get('Referer', '')
    is_referer_from_cdn = CLOUDFLARE_CDN_DOMAIN and CLOUDFLARE_CDN_DOMAIN in referer
    
    # 检查是否有重定向循环标记
    redirect_count = request.headers.get('X-Redirect-Count', '0')
    try:
        redirect_count = int(redirect_count)
    except:
        redirect_count = 0
    
    # 检查文件是否是新上传的（用于避免立即重定向）
    is_new_file = False
    if file_info.get('upload_time'):
        time_since_upload = time.time() - file_info['upload_time']
        is_new_file = time_since_upload < CDN_REDIRECT_DELAY
    
    # 如果不是CDN回源请求，不是来自CDN域名，文件不是新上传的，且没有重定向循环
    if (CDN_REDIRECT_ENABLED and  # 检查是否启用重定向
        not is_cdn_request and 
        not is_from_cdn_domain and 
        not is_referer_from_cdn and
        not is_new_file and  # 新文件不立即重定向
        redirect_count < CDN_REDIRECT_MAX_COUNT and  # 使用配置的最大重定向次数
        CDN_ENABLED and 
        CLOUDFLARE_CDN_DOMAIN):
        
        # 检查文件是否已被CDN缓存
        if file_info.get('cdn_cached'):
            # 构建CDN URL
            cdn_url = f"https://{CLOUDFLARE_CDN_DOMAIN}/image/{encrypted_id}"
            
            # 检查请求URL是否已经是CDN URL（避免循环）
            request_url = request.url
            if cdn_url not in request_url:
                logger.info(f"图片已缓存，重定向到CDN: {encrypted_id} -> {cdn_url}")
                
                # 更新访问计数
                update_access_count(encrypted_id)
                
                # 返回302重定向，添加重定向计数头部
                response = redirect(cdn_url, code=302)
                response.headers['Cache-Control'] = f'public, max-age={CDN_REDIRECT_CACHE_TIME}'
                response.headers['X-CDN-Redirect'] = 'true'
                response.headers['X-Redirect-Count'] = str(redirect_count + 1)
                return response
            else:
                logger.warning(f"检测到可能的重定向循环，直接提供图片: {encrypted_id}")
        else:
            # 如果还未缓存，检查是否需要更新缓存状态
            if cloudflare_cdn.check_cdn_status(encrypted_id):
                update_cdn_cache_status(encrypted_id, True)
                logger.info(f"更新CDN缓存状态并直接提供图片: {encrypted_id}")
    
    # 以下是CDN回源请求或直接提供图片的处理
    cache_status = cf_headers.get('CF-Cache-Status', '')
    
    # 更新访问计数
    update_access_count(encrypted_id)
    
    # 如果是CDN请求且状态为HIT，更新缓存状态
    if is_cdn_request and cache_status in ['HIT', 'STALE', 'UPDATING'] and not file_info.get('cdn_cached'):
        update_cdn_cache_status(encrypted_id, True)
    
    # 生成ETag
    etag = file_info.get('etag') or f'W/"{encrypted_id}-{file_info.get("file_size", 0)}"'
    
    # 检查条件请求
    if_none_match = request.headers.get('If-None-Match')
    if if_none_match and if_none_match == etag:
        # 304响应
        response = Response(status=304)
        response.headers['ETag'] = etag
        response.headers['Cache-Control'] = 'public, max-age=31536000, s-maxage=2592000, immutable'
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    # 需要从Telegram获取图片
    try:
        # 获取最新的file_path
        fresh_file_path = get_fresh_file_path(file_info['file_id'])
        if not fresh_file_path:
            logger.error(f"无法获取最新的file_path: {file_info['file_id']}")
            response = Response(b'Image not found', status=404, mimetype='text/plain')
            response.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(response, 'no-cache')
        
        # 如果file_path有变化，更新数据库
        if fresh_file_path != file_info['file_path']:
            update_file_path_in_db(encrypted_id, fresh_file_path)
        
        # 构建文件URL
        if fresh_file_path.startswith('https://'):
            file_url = fresh_file_path
        else:
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fresh_file_path}"
        
        access_type = 'cdn_pull' if is_cdn_request else 'direct_access'
        logger.info(f"从Telegram获取图片: {encrypted_id} (访问类型: {access_type}, CDN状态: {cache_status})")
        
        # 支持范围请求
        headers = {}
        range_header = request.headers.get('Range')
        if range_header:
            headers['Range'] = range_header
        
        # 从Telegram获取图片
        response = requests.get(file_url, stream=True, timeout=30, headers=headers)
        
        if response.status_code in [200, 206]:
            content_type = file_info.get('mime_type') or response.headers.get('content-type', 'image/jpeg')
            
            file_ext = Path(fresh_file_path).suffix or '.jpg'
            filename = f"image_{encrypted_id[:12]}{file_ext}"
            
            def generate():
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            
            resp_headers = {
                'Content-Disposition': f'inline; filename="{filename}"',
                'X-Content-Type-Options': 'nosniff',
                'Accept-Ranges': 'bytes',
                'ETag': etag,
                'X-Access-Type': access_type,
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
                'Access-Control-Allow-Headers': 'Range, Cache-Control',
                'Access-Control-Expose-Headers': 'Content-Length, Content-Range, Accept-Ranges, ETag'
            }
            
            if 'content-length' in response.headers:
                resp_headers['Content-Length'] = response.headers['content-length']
            if 'content-range' in response.headers:
                resp_headers['Content-Range'] = response.headers['content-range']
            
            if file_info.get('created_at'):
                try:
                    created_at = datetime.fromisoformat(file_info['created_at'].replace('Z', '+00:00'))
                    resp_headers['Last-Modified'] = created_at.strftime('%a, %d %b %Y %H:%M:%S GMT')
                except:
                    pass
            
            resp = Response(
                generate(), 
                status=response.status_code,
                mimetype=content_type,
                headers=resp_headers
            )
            
            # 设置缓存头部
            if CDN_ENABLED:
                # 对于新文件，使用较短的缓存时间
                if is_new_file:
                    resp.headers['Cache-Control'] = 'public, max-age=300, s-maxage=300'
                else:
                    resp.headers['Cache-Control'] = 'public, max-age=31536000, s-maxage=2592000, immutable'
                resp.headers.pop('Set-Cookie', None)
                resp.headers.pop('Cookie', None)
                resp.headers['Vary'] = 'Accept-Encoding'
                resp.headers['CF-Cache-Tag'] = f'image-{encrypted_id[:8]},imagebed,static'
            else:
                resp.headers['Cache-Control'] = 'public, max-age=3600'
            
            return resp
            
        else:
            logger.warning(f"Telegram文件获取失败: {file_url}, status: {response.status_code}")
            response = Response(b'Image not found', status=404, mimetype='text/plain')
            response.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(response, 'no-cache')
            
    except Exception as e:
        logger.error(f"代理图片失败: {e}")
        response = Response(b'Error loading image', status=500, mimetype='text/plain')
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache')

@app.route('/api/upload', methods=['POST', 'OPTIONS'])
def upload_file():
    """处理前端文件上传"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return add_cache_headers(response, 'no-cache')
    
    global telegram_app
    
    if not telegram_app:
        response = jsonify({'error': 'Telegram bot not initialized'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 500
    
    if 'file' not in request.files:
        response = jsonify({'error': 'No file provided'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 400
    
    file = request.files['file']
    if file.filename == '':
        response = jsonify({'error': 'No file selected'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 400
    
    if not file.content_type.startswith('image/'):
        response = jsonify({'error': 'Only image files are allowed'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 400
    
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > 20 * 1024 * 1024:
        response = jsonify({'error': 'File size exceeds 20MB limit'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 400
    
    try:
        file_content = file.read()
        file.seek(0)
        
        # 计算文件哈希
        file_hash = hashlib.md5(file_content).hexdigest()
        
        # 判断文件大小，选择合适的上传方法
        if file_size <= 10 * 1024 * 1024:  # 10MB以下使用sendPhoto
            files = {
                'photo': (file.filename, file_content, file.content_type)
            }
            data = {
                'chat_id': STORAGE_CHAT_ID,
                'caption': f"Web上传 | 文件名: {file.filename} | 大小: {file_size} bytes | 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"
            }
            
            response = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                files=files,
                data=data,
                timeout=30
            )
        else:  # 10MB以上使用sendDocument
            files = {
                'document': (file.filename, file_content, file.content_type)
            }
            data = {
                'chat_id': STORAGE_CHAT_ID,
                'caption': f"Web上传(大文件) | 文件名: {file.filename} | 大小: {file_size} bytes | 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"
            }
            
            response = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                files=files,
                data=data,
                timeout=60
            )
        
        if not response.ok:
            logger.error(f"Telegram API error: {response.text}")
            resp = jsonify({'error': 'Failed to upload to Telegram'})
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(resp, 'no-cache'), 500
        
        result = response.json()
        if not result.get('ok'):
            logger.error(f"Telegram API failed: {result}")
            resp = jsonify({'error': 'Telegram API failed'})
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(resp, 'no-cache'), 500
        
        # 获取文件信息
        if file_size <= 10 * 1024 * 1024:
            photos = result['result']['photo']
            if not photos:
                resp = jsonify({'error': 'No photo in response'})
                resp.headers['Access-Control-Allow-Origin'] = '*'
                return add_cache_headers(resp, 'no-cache'), 500
            
            photo = photos[-1]
            file_id = photo['file_id']
        else:
            document = result['result']['document']
            if not document:
                resp = jsonify({'error': 'No document in response'})
                resp.headers['Access-Control-Allow-Origin'] = '*'
                return add_cache_headers(resp, 'no-cache'), 500
            
            file_id = document['file_id']
        
        file_response = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
            params={'file_id': file_id},
            timeout=30
        )
        
        if not file_response.ok:
            logger.error(f"Failed to get file info: {file_response.text}")
            resp = jsonify({'error': 'Failed to get file info'})
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(resp, 'no-cache'), 500
        
        file_result = file_response.json()
        if not file_result.get('ok'):
            logger.error(f"Get file API failed: {file_result}")
            resp = jsonify({'error': 'Get file API failed'})
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(resp, 'no-cache'), 500
        
        file_path = file_result['result']['file_path']
        tg_file_size = file_result['result'].get('file_size', file_size)
        
        logger.info(f"Telegram上传成功: file_id={file_id}, file_path={file_path}, size={tg_file_size}")
        
        encrypted_id = encrypt_file_id(file_id, file_path)
        
        mime_type = get_mime_type(file.filename)
        
        file_data = {
            'file_id': file_id,
            'file_path': file_path,
            'upload_time': int(time.time()),
            'user_id': 0,
            'username': 'web_user',
            'file_size': tg_file_size,
            'source': 'web_upload',
            'original_filename': file.filename,
            'mime_type': mime_type,
            'file_hash': file_hash,
            'is_group_upload': 0
        }
        save_file_info(encrypted_id, file_data)
        
        # 生成URL
        base_url = get_domain(request)
        permanent_url = f"{base_url}/image/{encrypted_id}"
        
        logger.info(f"Web上传完成: {file.filename} -> {encrypted_id}")
        
        # 格式化文件大小
        def format_size(size_bytes):
            if size_bytes < 1024:
                return f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.1f} KB"
            elif size_bytes < 1024 * 1024 * 1024:
                return f"{size_bytes / 1024 / 1024:.1f} MB"
            else:
                return f"{size_bytes / 1024 / 1024 / 1024:.1f} GB"

        resp = jsonify({
            'success': True,
            'data': {
                'url': permanent_url,
                'filename': file.filename,
                'size': format_size(tg_file_size),
                'upload_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
        
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(resp, 'no-cache')
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        resp = jsonify({'error': str(e)})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(resp, 'no-cache'), 500

@app.route('/api/stats')
def get_stats_api():
    """获取统计信息API"""
    stats = get_stats()

    # 格式化文件大小
    def format_size(size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / 1024 / 1024:.1f} MB"
        else:
            return f"{size_bytes / 1024 / 1024 / 1024:.1f} GB"

    # 格式化运行时间
    uptime_seconds = int(time.time() - start_time)
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60

    if days > 0:
        uptime_str = f"{days}天"
    elif hours > 0:
        uptime_str = f"{hours}小时"
    else:
        uptime_str = f"{minutes}分钟"

    response = jsonify({
        'success': True,
        'data': {
            'totalFiles': str(stats['total_files']),
            'totalSize': format_size(stats['total_size']),
            'todayUploads': str(stats['today_uploads']),
            'uptime': uptime_str
        }
    })

    response.headers['Access-Control-Allow-Origin'] = '*'
    # 统计数据需要实时更新,禁用缓存
    return add_cache_headers(response, 'no-cache')

@app.route('/api/recent')
def get_recent_api():
    """获取最近上传的文件"""
    limit = request.args.get('limit', 12, type=int)
    page = request.args.get('page', 1, type=int)
    
    try:
        recent_files = get_recent_uploads(limit, page)
        
        for file in recent_files:
            if file['created_at']:
                try:
                    dt = datetime.fromisoformat(file['created_at'].replace('Z', '+00:00'))
                    file['created_at'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass
            
            base_url = get_domain(request)
            file['image_url'] = f"{base_url}/image/{file['encrypted_id']}"
            file['cdn_url'] = f"https://{CLOUDFLARE_CDN_DOMAIN}/image/{file['encrypted_id']}" if CLOUDFLARE_CDN_DOMAIN else None
            file['cdn_cached'] = file.get('cdn_cached', 0)
            file['is_group_upload'] = file.get('is_group_upload', 0)
        
        response = jsonify({
            'success': True,
            'files': recent_files,
            'page': page,
            'limit': limit,
            'has_more': len(recent_files) == limit
        })

        response.headers['Access-Control-Allow-Origin'] = '*'
        # 最近上传数据需要实时更新,禁用缓存
        return add_cache_headers(response, 'no-cache')
    
    except Exception as e:
        logger.error(f"Failed to get recent files: {e}")
        response = jsonify({
            'success': False,
            'error': 'Failed to load gallery',
            'files': [],
            'page': page,
            'limit': limit,
            'has_more': False
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 500

@app.route('/api/images')
def get_images_api():
    """获取图片列表（支持分页/搜索/排序）"""
    limit = request.args.get('limit', 24, type=int)
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str).strip()
    sort = request.args.get('sort', 'newest', type=str)

    offset = (page - 1) * limit

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        where_clauses = []
        params = []
        if search:
            where_clauses.append("(original_filename LIKE ? OR username LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like])
        where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # 统计总数
        cursor.execute(f"SELECT COUNT(*) FROM file_storage{where_sql}", params)
        total = cursor.fetchone()[0] or 0

        # 排序
        if sort == 'oldest':
            order_by = 'created_at ASC'
        elif sort == 'name':
            order_by = 'original_filename COLLATE NOCASE ASC'
        elif sort == 'size':
            order_by = 'file_size DESC'
        else:
            order_by = 'created_at DESC'

        # 查询数据
        cursor.execute(
            f"""
            SELECT encrypted_id, original_filename, file_size, created_at
            FROM file_storage
            {where_sql}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset]
        )

        rows = cursor.fetchall()
        images = []
        base_url = get_domain(request)

        def format_size(size_bytes: int) -> str:
            if size_bytes < 1024:
                return f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.1f} KB"
            else:
                return f"{size_bytes / 1024 / 1024:.1f} MB"

        for row in rows:
            encrypted_id = row['encrypted_id']
            filename = row['original_filename'] or f"image_{encrypted_id[:8]}.jpg"
            size_str = format_size(row['file_size'] or 0)

            created_raw = row['created_at'] or ''
            upload_time = created_raw
            try:
                upload_time = datetime.fromisoformat(created_raw.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                pass

            images.append({
                'id': encrypted_id,
                'url': f"{base_url}/image/{encrypted_id}",
                'filename': filename,
                'size': size_str,
                'uploadTime': upload_time
            })

        total_pages = (total + limit - 1) // limit or 1

        response = jsonify({
            'success': True,
            'data': {
                'images': images,
                'totalPages': total_pages
            }
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'private', 120)

    except Exception as e:
        logger.error(f"获取图片列表失败: {e}")
        response = jsonify({
            'success': False,
            'error': 'Failed to load images',
            'data': {
                'images': [],
                'totalPages': 1
            }
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 500

    finally:
        conn.close()

@app.route('/api/info')
def get_info():
    """获取服务器信息"""
    stats = get_stats()
    
    response = jsonify({
        'server_ip': LOCAL_IP,
        'domain': get_domain(request),
        'cdn_domain': f"https://{CLOUDFLARE_CDN_DOMAIN}" if CLOUDFLARE_CDN_DOMAIN else None,
        'port': PORT,
        'storage_type': 'telegram_cloud + sqlite',
        'database_path': DATABASE_PATH,
        'bot_configured': bool(BOT_TOKEN),
        'storage_chat_configured': STORAGE_CHAT_ID != 0,
        'uptime': int(time.time() - start_time),
        'total_files': stats['total_files'],
        'group_uploads': stats['group_uploads'],
        'cdn_enabled': CDN_ENABLED,
        'cloudflare_cdn': bool(CLOUDFLARE_CDN_DOMAIN),
        'cdn_cache_ttl': CDN_CACHE_TTL if CDN_ENABLED else 0,
        'cloudflare_cache_level': CLOUDFLARE_CACHE_LEVEL,
        'smart_routing': ENABLE_SMART_ROUTING,
        'cache_warming': ENABLE_CACHE_WARMING,
        'cdn_monitor_enabled': CDN_MONITOR_ENABLED,
        'cdn_monitor_queue': stats['cdn_stats']['monitor_queue_size'],
        'cdn_redirect_enabled': CDN_REDIRECT_ENABLED,
        'cdn_redirect_max_count': CDN_REDIRECT_MAX_COUNT,
        'cdn_redirect_delay': CDN_REDIRECT_DELAY,
        'group_upload_enabled': ENABLE_GROUP_UPLOAD,
        'group_upload_admin_only': GROUP_UPLOAD_ADMIN_ONLY,
        'group_upload_reply': GROUP_UPLOAD_REPLY,
        'max_file_size': 20 * 1024 * 1024,
        'static_version': STATIC_VERSION,
        'features': [
            'telegram_cloud_storage',
            'web_upload',
            'drag_and_drop',
            'encrypted_links',
            'permanent_urls',
            'inline_image_viewing',
            'database_persistence',
            'multiple_copy_formats',
            'proxy_support',
            'cdn_support',
            'cloudflare_cdn_integration',
            'smart_routing',
            'cache_warming',
            'cache_optimization',
            'etag_support',
            'range_request_support',
            'large_file_support_20mb',
            'admin_dashboard',
            'version_control',
            'backend_cdn_monitoring',
            'automatic_cache_detection',
            'smart_cdn_redirect',
            'redirect_loop_prevention',
            'automatic_file_path_refresh',
            'telegram_file_expiry_handling',
            'new_file_redirect_delay',
            'improved_cors_support',
            'group_upload_support',
            'group_admin_control',
            'auto_reply_with_cdn_link'
        ]
    })

    response.headers['Access-Control-Allow-Origin'] = '*'
    # 服务器信息可以短时间缓存,但不应过长
    return add_cache_headers(response, 'private', 60)

@app.route('/api/health')
def health_check():
    """健康检查端点"""
    response = jsonify({
        'status': 'healthy',
        'timestamp': int(time.time()),
        'base_url': get_domain(request),
        'cdn_enabled': CDN_ENABLED,
        'cloudflare_cdn': bool(CLOUDFLARE_CDN_DOMAIN),
        'cdn_monitor_active': cdn_monitor_thread and cdn_monitor_thread.is_alive() if CDN_MONITOR_ENABLED else False,
        'cdn_redirect_enabled': CDN_REDIRECT_ENABLED,
        'group_upload_enabled': ENABLE_GROUP_UPLOAD,
        'version': STATIC_VERSION
    })
    response.headers['Access-Control-Allow-Origin'] = '*'
    return add_cache_headers(response, 'no-cache')

@app.route('/api/admin/check')
def check_admin_status():
    """检查管理员登录状态"""
    from flask import session
    is_authenticated = session.get('admin_authenticated', False)
    username = session.get('admin_username', '')
    
    response = jsonify({
        'authenticated': is_authenticated,
        'username': username
    })
    response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return add_cache_headers(response, 'no-cache')

@app.route('/robots.txt')
def robots():
    """提供robots.txt"""
    robots_content = f"""User-agent: *
Allow: /
Disallow: /api/
Disallow: /admin

# Cloudflare
User-agent: Cloudflare-*
Allow: /

Sitemap: {get_domain(request)}/sitemap.xml
"""
    response = Response(robots_content, mimetype='text/plain')
    return add_cache_headers(response, 'public', 86400)

@app.route('/manifest.json')
def manifest():
    """提供PWA manifest"""
    manifest_data = {
        "name": "Telegram 云图床",
        "short_name": "云图床",
        "description": "基于Telegram云存储的免费图床服务，Cloudflare CDN全球加速",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#6366f1",
        "orientation": "portrait-primary"
    }
    response = jsonify(manifest_data)
    return add_cache_headers(response, 'public', 86400)

@app.route('/sw.js')
def service_worker():
    """提供Service Worker脚本"""
    # 从templates/sw.js读取内容
    sw_path = os.path.join(app.root_path, 'templates', 'sw.js')
    if os.path.exists(sw_path):
        with open(sw_path, 'r', encoding='utf-8') as f:
            sw_content = f.read()
    else:
        # 使用默认内容
        sw_content = f"""
// Service Worker for offline support and cache management
const CACHE_VERSION = 'telegram-imagebed-v{STATIC_VERSION}';
const STATIC_CACHE = CACHE_VERSION + '-static';
const IMAGE_CACHE = CACHE_VERSION + '-images';
const API_CACHE = CACHE_VERSION + '-api';
const CDN_DOMAIN = '{CLOUDFLARE_CDN_DOMAIN or ""}';

const urlsToCache = [
    '/',
    '/static/js/main.js?v={STATIC_VERSION}',
    '/static/css/styles.css?v={STATIC_VERSION}',
    '/static/css/admin.css?v={STATIC_VERSION}'
];

// 省略其他Service Worker代码...
"""
    
    # 替换变量
    sw_content = sw_content.replace('{STATIC_VERSION}', STATIC_VERSION)
    sw_content = sw_content.replace('{CLOUDFLARE_CDN_DOMAIN or ""}', CLOUDFLARE_CDN_DOMAIN or '')
    
    response = Response(sw_content, mimetype='application/javascript')
    return add_cache_headers(response, 'private', 3600)

# CDN管理API
@app.route('/api/admin/cdn/purge', methods=['POST', 'OPTIONS'])
@admin_module.login_required
def purge_cdn_cache():
    """清除CDN缓存（管理员）"""
    data = request.get_json()
    urls = data.get('urls', [])
    
    if not urls:
        response = jsonify({'error': 'No URLs provided'})
        return add_cache_headers(response, 'no-cache'), 400
    
    cdn_urls = []
    for url in urls:
        if '/image/' in url:
            encrypted_id = url.split('/image/')[-1]
            if CLOUDFLARE_CDN_DOMAIN:
                cdn_urls.append(f"https://{CLOUDFLARE_CDN_DOMAIN}/image/{encrypted_id}")
    
    if cdn_urls and cloudflare_cdn.purge_cache(cdn_urls):
        response = jsonify({
            'success': True,
            'message': f'已清除 {len(cdn_urls)} 个URL的缓存'
        })
    else:
        response = jsonify({
            'success': False,
            'error': '缓存清除失败'
        })
    
    return add_cache_headers(response, 'no-cache')

@app.route('/api/admin/clear_cache', methods=['POST', 'OPTIONS'])
@admin_module.login_required
def clear_cache():
    """清理CDN缓存（仅限管理员）"""
    global STATIC_VERSION
    old_version = STATIC_VERSION
    STATIC_VERSION = str(int(time.time()))

    cloudflare_success = False
    if CLOUDFLARE_CDN_DOMAIN and cloudflare_cdn.zone_id:
        try:
            response = requests.post(
                f'{cloudflare_cdn.base_url}/zones/{cloudflare_cdn.zone_id}/purge_cache',
                headers=cloudflare_cdn.headers,
                json={'purge_everything': True}
            )

            if response.status_code == 200:
                message = '缓存已清理，Cloudflare缓存已清除'
                cloudflare_success = True
            else:
                message = '缓存已清理，但Cloudflare缓存清除失败'
        except:
            message = '缓存已清理'
    else:
        message = '缓存已清理'

    return jsonify({
        'success': True,
        'message': message
    })

# 添加 /upload 别名路由（兼容前端）
@app.route('/upload', methods=['POST', 'OPTIONS'])
def upload_file_alias():
    """上传文件的别名路由"""
    return upload_file()

# 添加管理员设置更新 API
@app.route('/api/admin/settings', methods=['POST', 'OPTIONS'])
@admin_module.login_required
def admin_update_settings():
    """更新管理员设置"""
    data = request.get_json()
    new_username = data.get('username', '').strip()
    new_password = data.get('password', '').strip()

    if not new_username and not new_password:
        return jsonify({'success': False, 'message': '请提供新的用户名或密码'}), 400

    if new_username and len(new_username) < 3:
        return jsonify({'success': False, 'message': '用户名至少需要3个字符'}), 400

    if new_password and len(new_password) < 6:
        return jsonify({'success': False, 'message': '密码至少需要6个字符'}), 400

    if admin_module.update_admin_credentials(new_username, new_password):
        if new_username:
            session['admin_username'] = new_username

        return jsonify({
            'success': True,
            'message': '设置更新成功'
        })

    return jsonify({'success': False, 'message': '更新失败'}), 500

# 添加清理缓存别名（兼容前端）
@app.route('/api/admin/clear-cache', methods=['POST', 'OPTIONS'])
@admin_module.login_required
def clear_cache_alias():
    """清理缓存的别名路由"""
    return clear_cache()

# ===================== Auth Token API路由 =====================
@app.route('/api/auth/token/generate', methods=['POST', 'OPTIONS'])
def generate_guest_token():
    """生成游客token"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return add_cache_headers(response, 'no-cache')

    try:
        # 获取请求信息
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent', '')

        # 从请求体获取可选参数
        data = request.get_json() or {}
        upload_limit = data.get('upload_limit', 999999)  # 默认无限制
        expires_days = data.get('expires_days', 36500)  # 默认100年
        description = data.get('description', '游客Token')

        # 移除参数范围限制
        # upload_limit = min(max(upload_limit, 1), 1000)  # 1-1000张
        # expires_days = min(max(expires_days, 1), 365)   # 1-365天

        # 创建token
        token = create_auth_token(
            ip_address=ip_address,
            user_agent=user_agent,
            description=description,
            upload_limit=upload_limit,
            expires_days=expires_days
        )

        if not token:
            response = jsonify({
                'success': False,
                'error': '生成Token失败'
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(response, 'no-cache'), 500

        # 获取token信息
        token_info = get_token_info(token)

        response = jsonify({
            'success': True,
            'data': {
                'token': token,
                'upload_limit': upload_limit,
                'expires_days': expires_days,
                'expires_at': token_info['expires_at'] if token_info else None,
                'message': f'Token已生成，可上传{upload_limit}张图片，有效期{expires_days}天'
            }
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"生成token失败: {e}")
        response = jsonify({
            'success': False,
            'error': str(e)
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 500

@app.route('/api/auth/token/verify', methods=['POST', 'OPTIONS'])
def verify_guest_token():
    """验证token是否有效"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return add_cache_headers(response, 'no-cache')

    try:
        # 从请求头或请求体获取token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            data = request.get_json() or {}
            token = data.get('token', '')

        if not token:
            response = jsonify({
                'success': False,
                'valid': False,
                'error': '未提供Token'
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(response, 'no-cache'), 400

        # 验证token
        verification = verify_auth_token(token)

        if verification['valid']:
            token_data = verification['token_data']
            response = jsonify({
                'success': True,
                'valid': True,
                'data': {
                    'upload_count': token_data['upload_count'],
                    'upload_limit': token_data['upload_limit'],
                    'remaining_uploads': verification['remaining_uploads'],
                    'expires_at': token_data['expires_at'],
                    'created_at': token_data['created_at'],
                    'last_used': token_data['last_used']
                }
            })
        else:
            response = jsonify({
                'success': False,
                'valid': False,
                'reason': verification['reason']
            })

        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"验证token失败: {e}")
        response = jsonify({
            'success': False,
            'valid': False,
            'error': str(e)
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 500

@app.route('/api/auth/upload', methods=['POST', 'OPTIONS'])
def upload_with_token():
    """使用token上传图片"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return add_cache_headers(response, 'no-cache')

    global telegram_app

    if not telegram_app:
        response = jsonify({'success': False, 'error': 'Telegram bot未初始化'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 500

    # 获取token
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        response = jsonify({'success': False, 'error': '未提供Token'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 401

    # 验证token
    verification = verify_auth_token(token)
    if not verification['valid']:
        response = jsonify({
            'success': False,
            'error': f"Token无效: {verification['reason']}"
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 401

    # 检查文件
    if 'file' not in request.files:
        response = jsonify({'success': False, 'error': '未提供文件'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 400

    file = request.files['file']
    if file.filename == '':
        response = jsonify({'success': False, 'error': '未选择文件'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 400

    if not file.content_type.startswith('image/'):
        response = jsonify({'success': False, 'error': '只允许上传图片文件'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 400

    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)

    if file_size > 20 * 1024 * 1024:
        response = jsonify({'success': False, 'error': '文件大小超过20MB限制'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 400

    try:
        file_content = file.read()
        file.seek(0)

        # 计算文件哈希
        file_hash = hashlib.md5(file_content).hexdigest()

        # 上传到Telegram
        if file_size <= 10 * 1024 * 1024:
            files = {'photo': (file.filename, file_content, file.content_type)}
            data = {
                'chat_id': STORAGE_CHAT_ID,
                'caption': f"游客上传 | Token: {token[:20]}... | 文件名: {file.filename} | 大小: {file_size} bytes | 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"
            }
            response_tg = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                files=files, data=data, timeout=30
            )
        else:
            files = {'document': (file.filename, file_content, file.content_type)}
            data = {
                'chat_id': STORAGE_CHAT_ID,
                'caption': f"游客上传(大文件) | Token: {token[:20]}... | 文件名: {file.filename} | 大小: {file_size} bytes | 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"
            }
            response_tg = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                files=files, data=data, timeout=60
            )

        if not response_tg.ok:
            logger.error(f"Telegram API错误: {response_tg.text}")
            resp = jsonify({'success': False, 'error': '上传到Telegram失败'})
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(resp, 'no-cache'), 500

        result = response_tg.json()
        if not result.get('ok'):
            logger.error(f"Telegram API失败: {result}")
            resp = jsonify({'success': False, 'error': 'Telegram API失败'})
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(resp, 'no-cache'), 500

        # 获取文件信息
        if file_size <= 10 * 1024 * 1024:
            photos = result['result']['photo']
            if not photos:
                resp = jsonify({'success': False, 'error': '响应中无图片'})
                resp.headers['Access-Control-Allow-Origin'] = '*'
                return add_cache_headers(resp, 'no-cache'), 500
            photo = photos[-1]
            file_id = photo['file_id']
        else:
            document = result['result']['document']
            if not document:
                resp = jsonify({'success': False, 'error': '响应中无文档'})
                resp.headers['Access-Control-Allow-Origin'] = '*'
                return add_cache_headers(resp, 'no-cache'), 500
            file_id = document['file_id']

        file_response = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
            params={'file_id': file_id}, timeout=30
        )

        if not file_response.ok:
            logger.error(f"获取文件信息失败: {file_response.text}")
            resp = jsonify({'success': False, 'error': '获取文件信息失败'})
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(resp, 'no-cache'), 500

        file_result = file_response.json()
        if not file_result.get('ok'):
            logger.error(f"获取文件API失败: {file_result}")
            resp = jsonify({'success': False, 'error': '获取文件API失败'})
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(resp, 'no-cache'), 500

        file_path = file_result['result']['file_path']
        tg_file_size = file_result['result'].get('file_size', file_size)

        logger.info(f"Token上传成功: file_id={file_id}, token={token[:20]}..., size={tg_file_size}")

        encrypted_id = encrypt_file_id(file_id, file_path)
        mime_type = get_mime_type(file.filename)

        file_data = {
            'file_id': file_id,
            'file_path': file_path,
            'upload_time': int(time.time()),
            'user_id': 0,
            'username': 'guest_user',
            'file_size': tg_file_size,
            'source': 'guest_token',
            'original_filename': file.filename,
            'mime_type': mime_type,
            'file_hash': file_hash,
            'is_group_upload': 0,
            'auth_token': token
        }
        save_file_info(encrypted_id, file_data)

        # 更新token使用次数
        update_token_usage(token)

        # 生成URL
        base_url = get_domain(request)
        permanent_url = f"{base_url}/image/{encrypted_id}"

        # 获取剩余上传次数
        verification_after = verify_auth_token(token)
        remaining = verification_after.get('remaining_uploads', 0) if verification_after['valid'] else 0

        logger.info(f"游客上传完成: {file.filename} -> {encrypted_id}, 剩余: {remaining}次")

        def format_size(size_bytes):
            if size_bytes < 1024:
                return f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.1f} KB"
            elif size_bytes < 1024 * 1024 * 1024:
                return f"{size_bytes / 1024 / 1024:.1f} MB"
            else:
                return f"{size_bytes / 1024 / 1024 / 1024:.1f} GB"

        resp = jsonify({
            'success': True,
            'data': {
                'url': permanent_url,
                'filename': file.filename,
                'size': format_size(tg_file_size),
                'upload_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'remaining_uploads': remaining
            }
        })

        resp.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(resp, 'no-cache')

    except Exception as e:
        logger.error(f"Token上传错误: {e}")
        resp = jsonify({'success': False, 'error': str(e)})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(resp, 'no-cache'), 500

@app.route('/api/auth/uploads', methods=['GET', 'OPTIONS'])
def get_token_uploads_api():
    """获取token上传的图片列表"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return add_cache_headers(response, 'no-cache')

    try:
        # 获取token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            token = request.args.get('token', '')

        if not token:
            response = jsonify({
                'success': False,
                'error': '未提供Token'
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(response, 'no-cache'), 401

        # 验证token
        verification = verify_auth_token(token)
        if not verification['valid']:
            response = jsonify({
                'success': False,
                'error': f"Token无效: {verification['reason']}"
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return add_cache_headers(response, 'no-cache'), 401

        # 获取分页参数
        limit = request.args.get('limit', 50, type=int)
        page = request.args.get('page', 1, type=int)

        # 获取上传列表
        uploads = get_token_uploads(token, limit, page)

        # 格式化数据
        base_url = get_domain(request)
        for upload in uploads:
            upload['image_url'] = f"{base_url}/image/{upload['encrypted_id']}"
            if upload.get('created_at'):
                try:
                    dt = datetime.fromisoformat(upload['created_at'].replace('Z', '+00:00'))
                    upload['created_at'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass

        # 获取token信息
        token_info = get_token_info(token)

        response = jsonify({
            'success': True,
            'data': {
                'uploads': uploads,
                'total_uploads': token_info['upload_count'] if token_info else 0,
                'upload_limit': token_info['upload_limit'] if token_info else 0,
                'remaining_uploads': verification['remaining_uploads'],
                'page': page,
                'limit': limit,
                'has_more': len(uploads) == limit
            }
        })

        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'private', 60)

    except Exception as e:
        logger.error(f"获取token上传列表失败: {e}")
        response = jsonify({
            'success': False,
            'error': str(e)
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 500

# ===================== 公告管理API =====================
@app.route('/api/announcement', methods=['GET', 'OPTIONS'])
def get_announcement():
    """获取当前公告"""
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return add_cache_headers(response, 'no-cache')

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 获取最新的公告
        cursor.execute('''
            SELECT id, enabled, content, created_at, updated_at
            FROM announcements
            ORDER BY id DESC
            LIMIT 1
        ''')

        announcement = cursor.fetchone()
        conn.close()

        if announcement:
            response = jsonify({
                'success': True,
                'data': {
                    'id': announcement['id'],
                    'enabled': bool(announcement['enabled']),
                    'content': announcement['content'],
                    'created_at': announcement['created_at'],
                    'updated_at': announcement['updated_at']
                }
            })
        else:
            response = jsonify({
                'success': True,
                'data': {
                    'id': 0,
                    'enabled': False,
                    'content': '',
                    'created_at': None,
                    'updated_at': None
                }
            })

        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"获取公告失败: {e}")
        response = jsonify({
            'success': False,
            'error': str(e)
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return add_cache_headers(response, 'no-cache'), 500

@app.route('/api/admin/announcement', methods=['GET', 'POST', 'OPTIONS'])
@admin_module.login_required
def admin_announcement():
    """管理员公告管理"""
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if request.method == 'GET':
            # 获取公告
            cursor.execute('''
                SELECT id, enabled, content, created_at, updated_at
                FROM announcements
                ORDER BY id DESC
                LIMIT 1
            ''')

            announcement = cursor.fetchone()
            conn.close()

            if announcement:
                response = jsonify({
                    'success': True,
                    'data': {
                        'id': announcement['id'],
                        'enabled': bool(announcement['enabled']),
                        'content': announcement['content'],
                        'created_at': announcement['created_at'],
                        'updated_at': announcement['updated_at']
                    }
                })
            else:
                response = jsonify({
                    'success': True,
                    'data': {
                        'id': 0,
                        'enabled': False,
                        'content': '',
                        'created_at': None,
                        'updated_at': None
                    }
                })

        elif request.method == 'POST':
            # 更新公告
            data = request.get_json()
            enabled = data.get('enabled', True)
            content = data.get('content', '')

            # 获取当前公告
            cursor.execute('SELECT id, content FROM announcements ORDER BY id DESC LIMIT 1')
            result = cursor.fetchone()

            # 检查内容是否有变化
            content_changed = False
            if result:
                old_content = result['content']
                content_changed = (old_content != content)

            if result and not content_changed:
                # 内容没有变化，只更新启用状态
                announcement_id = result['id']
                cursor.execute('''
                    UPDATE announcements
                    SET enabled = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (enabled, announcement_id))
            else:
                # 内容有变化或没有公告，创建新公告
                # 先禁用所有旧公告
                if result:
                    cursor.execute('UPDATE announcements SET enabled = 0')

                # 创建新公告
                cursor.execute('''
                    INSERT INTO announcements (enabled, content)
                    VALUES (?, ?)
                ''', (enabled, content))
                announcement_id = cursor.lastrowid

            conn.commit()
            conn.close()

            response = jsonify({
                'success': True,
                'message': '公告更新成功',
                'data': {
                    'id': announcement_id,
                    'enabled': enabled,
                    'content': content
                }
            })

        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache')

    except Exception as e:
        logger.error(f"公告管理失败: {e}")
        response = jsonify({
            'success': False,
            'error': str(e)
        })
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return add_cache_headers(response, 'no-cache'), 500

# 注册管理员路由
admin_module.register_admin_routes(app, DATABASE_PATH, lambda: get_stats()['total_files'],
                                 lambda: get_stats()['total_size'], add_cache_headers)

# ===================== SPA路由（必须在所有其他路由之后注册） =====================
# 捕获所有前端路由（SPA路由）
@app.route('/<path:path>')
def catch_all(path):
    """捕获所有路由，优先返回静态文件，否则返回200.html（SPA）"""
    logger.info(f"[SPA路由] 请求路径: {path}")

    # 如果是API路由，跳过
    if path.startswith('api/') or path.startswith('image/') or path.startswith('upload'):
        logger.info(f"[SPA路由] API路由，跳过: {path}")
        return jsonify({'error': 'Not found'}), 404

    # 尝试返回静态文件
    file_path = os.path.join(STATIC_FOLDER, path)
    logger.info(f"[SPA路由] 检查文件路径: {file_path}")

    # 如果是文件，直接返回
    if os.path.exists(file_path) and os.path.isfile(file_path):
        logger.info(f"[SPA路由] 找到文件，返回: {file_path}")
        return send_file(file_path)

    # 如果是目录，尝试返回目录下的index.html
    if os.path.exists(file_path) and os.path.isdir(file_path):
        index_in_dir = os.path.join(file_path, 'index.html')
        logger.info(f"[SPA路由] 检查目录index.html: {index_in_dir}")
        if os.path.exists(index_in_dir):
            logger.info(f"[SPA路由] 找到目录index.html，返回: {index_in_dir}")
            return send_file(index_in_dir)

    # 否则返回200.html（Nuxt生成的SPA回退页面）
    fallback_path = os.path.join(STATIC_FOLDER, '200.html')
    logger.info(f"[SPA路由] 尝试返回200.html: {fallback_path}")
    if os.path.exists(fallback_path):
        logger.info(f"[SPA路由] 返回200.html作为SPA回退")
        return send_file(fallback_path)

    # 如果200.html不存在，尝试返回index.html
    index_path = os.path.join(STATIC_FOLDER, 'index.html')
    logger.info(f"[SPA路由] 尝试返回index.html: {index_path}")
    if os.path.exists(index_path):
        logger.info(f"[SPA路由] 返回index.html")
        return send_file(index_path)

    logger.warning(f"[SPA路由] 未找到任何匹配文件，返回404: {path}")
    return jsonify({'error': 'Not found'}), 404

# ===================== 辅助函数 =====================
def encrypt_file_id(file_id: str, file_path: str) -> str:
    """加密文件ID，隐藏敏感信息"""
    data = f"{file_id}:{file_path}:{int(time.time())}"
    encoded = base64.b64encode(data.encode()).decode()
    hash_obj = hashlib.md5(f"{encoded}{SECRET_KEY}".encode())
    return f"{encoded[:16]}{hash_obj.hexdigest()[:8]}"

def get_mime_type(file_path: str) -> str:
    """根据文件扩展名获取MIME类型"""
    ext = Path(file_path).suffix.lower()
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.bmp': 'image/bmp',
        '.svg': 'image/svg+xml',
        '.ico': 'image/x-icon',
        '.tiff': 'image/tiff',
        '.tif': 'image/tiff'
    }
    return mime_types.get(ext, 'image/jpeg')

# ===================== Auth Token 管理函数 =====================
def generate_auth_token() -> str:
    """生成唯一的auth_token"""
    import secrets
    # 生成32字节的随机token，转换为64字符的十六进制字符串
    token = secrets.token_hex(32)
    return f"guest_{token}"

def create_auth_token(ip_address: str = None, user_agent: str = None,
                     description: str = None, upload_limit: int = 100,
                     expires_days: int = 30) -> Optional[str]:
    """创建新的auth_token"""
    try:
        token = generate_auth_token()
        expires_at = datetime.now() + timedelta(days=expires_days)

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO auth_tokens
            (token, expires_at, upload_limit, ip_address, user_agent, description)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (token, expires_at, upload_limit, ip_address, user_agent, description or '游客Token'))

        conn.commit()
        conn.close()

        logger.info(f"创建新的auth_token: {token[:20]}... (限制: {upload_limit}张, 有效期: {expires_days}天)")
        return token

    except Exception as e:
        logger.error(f"创建auth_token失败: {e}")
        return None

def verify_auth_token(token: str) -> Dict[str, Any]:
    """验证auth_token是否有效"""
    if not token:
        return {'valid': False, 'reason': 'Token为空'}

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM auth_tokens WHERE token = ?
        ''', (token,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return {'valid': False, 'reason': 'Token不存在'}

        token_data = dict(row)

        # 检查是否激活
        if not token_data['is_active']:
            return {'valid': False, 'reason': 'Token已被禁用'}

        # 检查是否过期（已移除时间限制检查）
        # if token_data['expires_at']:
        #     expires_at = datetime.fromisoformat(token_data['expires_at'])
        #     if datetime.now() > expires_at:
        #         return {'valid': False, 'reason': 'Token已过期'}

        # 检查上传限制（已移除上传数量限制检查）
        # if token_data['upload_count'] >= token_data['upload_limit']:
        #     return {'valid': False, 'reason': f"已达到上传限制({token_data['upload_limit']}张)"}

        return {
            'valid': True,
            'token_data': token_data,
            'remaining_uploads': -1  # -1 表示无限制
        }

    except Exception as e:
        logger.error(f"验证auth_token失败: {e}")
        return {'valid': False, 'reason': '验证失败'}

def update_token_usage(token: str):
    """更新token使用记录"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE auth_tokens
            SET upload_count = upload_count + 1,
                last_used = CURRENT_TIMESTAMP
            WHERE token = ?
        ''', (token,))

        conn.commit()
        conn.close()

    except Exception as e:
        logger.error(f"更新token使用记录失败: {e}")

def get_token_info(token: str) -> Optional[Dict[str, Any]]:
    """获取token详细信息"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM auth_tokens WHERE token = ?
        ''', (token,))

        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    except Exception as e:
        logger.error(f"获取token信息失败: {e}")
        return None

def get_token_uploads(token: str, limit: int = 50, page: int = 1) -> List[Dict[str, Any]]:
    """获取token上传的所有图片"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        offset = (page - 1) * limit

        cursor.execute('''
            SELECT encrypted_id, original_filename, file_size, created_at,
                   cdn_cached, cdn_url, mime_type
            FROM file_storage
            WHERE auth_token = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (token, limit, offset))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    except Exception as e:
        logger.error(f"获取token上传记录失败: {e}")
        return []

# ===================== Telegram处理函数 =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    stats = get_stats()
    
    cdn_info = ""
    if CDN_ENABLED and CLOUDFLARE_CDN_DOMAIN:
        cdn_info = f"\n🌐 *CDN域名:* `{CLOUDFLARE_CDN_DOMAIN}`"
    
    monitor_info = ""
    if CDN_MONITOR_ENABLED:
        monitor_info = f"\n📊 *CDN监控:* 已启用 (队列: {stats['cdn_stats']['monitor_queue_size']})"
    
    redirect_info = ""
    if CDN_REDIRECT_ENABLED:
        redirect_info = f"\n🔄 *智能重定向:* 已启用 (最大{CDN_REDIRECT_MAX_COUNT}次)"
    
    group_upload_info = ""
    if ENABLE_GROUP_UPLOAD:
        group_upload_info = f"\n📸 *群组上传:* 已启用 (已上传: {stats['group_uploads']}张)"
        if GROUP_UPLOAD_ADMIN_ONLY:
            group_upload_info += f"\n👮 *权限控制:* 仅管理员"
    
    await update.message.reply_text(
        "☁️ *Telegram 云图床机器人*\n\n"
        "✨ *功能特点:*\n"
        "• 直接发送图片获取永久直链\n"
        "• 基于Telegram云存储，无需本地磁盘\n"
        "• 支持Web界面拖拽上传\n"
        "• 支持最大20MB的图片文件\n"
        "• 安全加密的链接地址\n"
        "• 数据库持久化存储\n"
        "• Cloudflare CDN全球加速\n"
        "• 后端自动CDN缓存检测\n"
        "• 智能CDN重定向优化\n"
        "• 重定向循环保护\n"
        "• 自动刷新过期文件路径\n"
        "• 新文件延迟重定向保护\n"
        "• 群组图片自动收录\n\n"
        f"🌐 *Web界面:* {get_domain(None)}\n"
        f"🔧 *管理后台:* {get_domain(None)}/admin\n"
        f"📡 *服务器IP:* {LOCAL_IP}:{PORT}\n"
        f"{cdn_info}\n"
        f"{monitor_info}\n"
        f"{redirect_info}\n"
        f"{group_upload_info}\n"
        f"📊 *已存储:* {stats['total_files']} 个文件\n"
        f"💾 *总大小:* {stats['total_size'] / 1024 / 1024:.1f} MB\n"
        f"🚀 *CDN状态:* {'Cloudflare已启用' if CLOUDFLARE_CDN_DOMAIN else ('已启用' if CDN_ENABLED else '未启用')}\n"
        f"📦 *最大文件:* 20MB\n\n"
        "直接发送图片即可开始使用！",
        parse_mode='Markdown'
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理图片上传"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "未知用户"
    
    msg = await update.message.reply_text("⏳ 正在处理图片...")
    
    try:
        # 检查是否是文档（大图片）
        if update.message.document and update.message.document.mime_type.startswith('image/'):
            # 处理作为文档发送的大图片
            document = update.message.document
            file_info = await context.bot.get_file(document.file_id)
            
            logger.info(f"用户 {username}({user_id}) 上传大图片: file_id={document.file_id}, file_path={file_info.file_path}, size={document.file_size}")
            
            try:
                await context.bot.send_document(
                    chat_id=STORAGE_CHAT_ID,
                    document=document.file_id,
                    caption=f"用户: {username}({user_id}) | 时间: {time.strftime('%Y-%m-%d %H:%M:%S')} | 来源: 机器人 | 大文件"
                )
                logger.info(f"大图片已备份到存储群组: {document.file_id}")
            except Exception as e:
                logger.warning(f"Failed to backup to storage chat: {e}")
            
            encrypted_id = encrypt_file_id(document.file_id, file_info.file_path)
            
            file_data = {
                'file_id': document.file_id,
                'file_path': file_info.file_path,
                'upload_time': int(time.time()),
                'user_id': user_id,
                'username': username,
                'file_size': document.file_size,
                'source': 'telegram_bot',
                'original_filename': document.file_name or 'large_image.jpg',
                'mime_type': document.mime_type or 'image/jpeg',
                'is_group_upload': 0
            }
            save_file_info(encrypted_id, file_data)
            
            permanent_url = f"{get_domain(None)}/image/{encrypted_id}"
            cdn_url = f"https://{CLOUDFLARE_CDN_DOMAIN}/image/{encrypted_id}" if CLOUDFLARE_CDN_DOMAIN else None
            
            message_text = (
                f"✅ *上传成功！*\n\n"
                f"🔗 *永久直链:*\n`{permanent_url}`\n"
            )
            
            if cdn_url:
                message_text += f"\n🌐 *CDN加速:*\n`{cdn_url}`\n"
            
            message_text += (
                f"\n📊 *文件信息:*\n"
                f"• 大小: {document.file_size} bytes ({document.file_size / 1024 / 1024:.1f} MB)\n"
                f"• 格式: {Path(document.file_name or 'image').suffix.upper()}\n"
                f"• ID: `{encrypted_id[:12]}...`\n"
                f"• 存储: Telegram云端 + 数据库\n"
                f"• CDN: {'监控中' if CDN_MONITOR_ENABLED else ('已缓存' if CDN_ENABLED else '未启用')}\n"
                f"• 类型: 大文件\n\n"
                f"💡 *提示:* 链接永久有效，CDN正在后台自动缓存"
            )
            
            await msg.edit_text(message_text, parse_mode='Markdown')
            
        elif update.message.photo:
            # 处理普通图片（10MB以下）
            photo = update.message.photo[-1]
            file_info = await context.bot.get_file(photo.file_id)
            
            logger.info(f"用户 {username}({user_id}) 上传图片: file_id={photo.file_id}, file_path={file_info.file_path}")
            
            try:
                await context.bot.send_photo(
                    chat_id=STORAGE_CHAT_ID,
                    photo=photo.file_id,
                    caption=f"用户: {username}({user_id}) | 时间: {time.strftime('%Y-%m-%d %H:%M:%S')} | 来源: 机器人"
                )
                logger.info(f"图片已备份到存储群组: {photo.file_id}")
            except Exception as e:
                logger.warning(f"Failed to backup to storage chat: {e}")
            
            encrypted_id = encrypt_file_id(photo.file_id, file_info.file_path)
            
            file_data = {
                'file_id': photo.file_id,
                'file_path': file_info.file_path,
                'upload_time': int(time.time()),
                'user_id': user_id,
                'username': username,
                'file_size': file_info.file_size,
                'source': 'telegram_bot',
                'mime_type': get_mime_type(file_info.file_path),
                'is_group_upload': 0
            }
            save_file_info(encrypted_id, file_data)
            
            permanent_url = f"{get_domain(None)}/image/{encrypted_id}"
            cdn_url = f"https://{CLOUDFLARE_CDN_DOMAIN}/image/{encrypted_id}" if CLOUDFLARE_CDN_DOMAIN else None
            
            message_text = (
                f"✅ *上传成功！*\n\n"
                f"🔗 *永久直链:*\n`{permanent_url}`\n"
            )
            
            if cdn_url:
                message_text += f"\n🌐 *CDN加速:*\n`{cdn_url}`\n"
            
            message_text += (
                f"\n📊 *文件信息:*\n"
                f"• 大小: {file_info.file_size} bytes\n"
                f"• 格式: {Path(file_info.file_path).suffix.upper()}\n"
                f"• ID: `{encrypted_id[:12]}...`\n"
                f"• 存储: Telegram云端 + 数据库\n"
                f"• CDN: {'监控中' if CDN_MONITOR_ENABLED else ('已缓存' if CDN_ENABLED else '未启用')}\n\n"
                f"💡 *提示:* 链接永久有效，CDN正在后台自动缓存"
            )
            
            await msg.edit_text(message_text, parse_mode='Markdown')
        else:
            await msg.edit_text("❌ 请发送图片文件")
            return
            
        logger.info(f"图片处理完成: {encrypted_id}")
        
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await msg.edit_text("❌ 处理失败，请重试")

async def handle_group_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理群组中的图片（非机器人发送）"""
    if not ENABLE_GROUP_UPLOAD:
        return
    
    # 检查是否在存储群组中
    if update.effective_chat.id != STORAGE_CHAT_ID:
        return
    
    # 检查是否是机器人自己发的消息（避免处理自己发送的备份图片）
    if update.effective_user.is_bot:
        return
    
    # 检查是否是机器人自己
    global bot_info
    if bot_info and update.effective_user.id == bot_info.id:
        return
    
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or "未知用户"
    
    # 检查权限
    if GROUP_UPLOAD_ADMIN_ONLY and GROUP_ADMIN_ID_LIST:
        if user_id not in GROUP_ADMIN_ID_LIST:
            logger.info(f"非管理员用户 {username}({user_id}) 在群组中发送图片，跳过处理")
            return
    
    try:
        # 检查是否是文档（大图片）
        if update.message.document and update.message.document.mime_type.startswith('image/'):
            # 处理作为文档发送的大图片
            document = update.message.document
            file_info = await context.bot.get_file(document.file_id)
            
            logger.info(f"群组用户 {username}({user_id}) 上传大图片: file_id={document.file_id}, size={document.file_size}")
            
            encrypted_id = encrypt_file_id(document.file_id, file_info.file_path)
            
            file_data = {
                'file_id': document.file_id,
                'file_path': file_info.file_path,
                'upload_time': int(time.time()),
                'user_id': user_id,
                'username': username,
                'file_size': document.file_size,
                'source': 'telegram_group',
                'original_filename': document.file_name or f'group_image_{int(time.time())}.jpg',
                'mime_type': document.mime_type or 'image/jpeg',
                'is_group_upload': 1,
                'group_message_id': update.message.message_id
            }
            save_file_info(encrypted_id, file_data)
            
            # 生成链接
            permanent_url = f"{get_domain(None)}/image/{encrypted_id}"
            cdn_url = f"https://{CLOUDFLARE_CDN_DOMAIN}/image/{encrypted_id}" if CLOUDFLARE_CDN_DOMAIN else None
            
            # 如果启用了回复
            if GROUP_UPLOAD_REPLY:
                reply_text = f"✅ *图片已收录*\n\n"
                
                if cdn_url and file_data.get('cdn_cached'):
                    reply_text += f"🌐 *CDN链接:*\n`{cdn_url}`\n"
                else:
                    reply_text += f"🔗 *直链:*\n`{permanent_url}`\n"
                    if cdn_url:
                        reply_text += f"\n⏳ *CDN缓存中...*"
                
                reply_text += (
                    f"\n📊 *文件信息:*\n"
                    f"• 大小: {document.file_size / 1024 / 1024:.1f} MB\n"
                    f"• ID: `{encrypted_id[:12]}...`\n"
                )
                
                reply_msg = await update.message.reply_text(
                    reply_text,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
                
                # 如果设置了删除延迟
                if GROUP_UPLOAD_DELETE_DELAY > 0:
                    await asyncio.sleep(GROUP_UPLOAD_DELETE_DELAY)
                    try:
                        await reply_msg.delete()
                    except:
                        pass
            
            logger.info(f"群组大图片处理完成: {encrypted_id}")
            
        elif update.message.photo:
            # 处理普通图片
            photo = update.message.photo[-1]
            file_info = await context.bot.get_file(photo.file_id)
            
            logger.info(f"群组用户 {username}({user_id}) 上传图片: file_id={photo.file_id}")
            
            encrypted_id = encrypt_file_id(photo.file_id, file_info.file_path)
            
            file_data = {
                'file_id': photo.file_id,
                'file_path': file_info.file_path,
                'upload_time': int(time.time()),
                'user_id': user_id,
                'username': username,
                'file_size': file_info.file_size,
                'source': 'telegram_group',
                'original_filename': f'group_image_{int(time.time())}.jpg',
                'mime_type': get_mime_type(file_info.file_path),
                'is_group_upload': 1,
                'group_message_id': update.message.message_id
            }
            save_file_info(encrypted_id, file_data)
            
            # 生成链接
            permanent_url = f"{get_domain(None)}/image/{encrypted_id}"
            cdn_url = f"https://{CLOUDFLARE_CDN_DOMAIN}/image/{encrypted_id}" if CLOUDFLARE_CDN_DOMAIN else None
            
            # 如果启用了回复
            if GROUP_UPLOAD_REPLY:
                reply_text = f"✅ *图片已收录*\n\n"
                
                if cdn_url and file_data.get('cdn_cached'):
                    reply_text += f"🌐 *CDN链接:*\n`{cdn_url}`\n"
                else:
                    reply_text += f"🔗 *直链:*\n`{permanent_url}`\n"
                    if cdn_url:
                        reply_text += f"\n⏳ *CDN缓存中...*"
                
                reply_text += (
                    f"\n📊 *文件信息:*\n"
                    f"• 大小: {file_info.file_size / 1024:.1f} KB\n"
                    f"• ID: `{encrypted_id[:12]}...`\n"
                )
                
                reply_msg = await update.message.reply_text(
                    reply_text,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
                
                # 如果设置了删除延迟
                if GROUP_UPLOAD_DELETE_DELAY > 0:
                    await asyncio.sleep(GROUP_UPLOAD_DELETE_DELAY)
                    try:
                        await reply_msg.delete()
                    except:
                        pass
            
            logger.info(f"群组图片处理完成: {encrypted_id}")
            
    except Exception as e:
        logger.error(f"处理群组图片失败: {e}")
        import traceback
        traceback.print_exc()

async def wait_for_cdn_cache(encrypted_id: str, cdn_url: str, timeout: int = 30) -> bool:
    """等待CDN缓存完成"""
    if not CLOUDFLARE_CDN_DOMAIN:
        return False
    
    # 触发CDN预热
    if ENABLE_CACHE_WARMING:
        logger.info(f"开始CDN预热: {encrypted_id}")
        await asyncio.sleep(CACHE_WARMING_DELAY)
        await cloudflare_cdn.warm_cache(cdn_url, encrypted_id)
        await asyncio.sleep(3)  # 给CDN一点时间处理
    
    # 等待缓存完成
    start_time = time.time()
    check_interval = 2
    check_count = 0
    
    while time.time() - start_time < timeout:
        if cloudflare_cdn.check_cdn_status(encrypted_id):
            update_cdn_cache_status(encrypted_id, True)
            logger.info(f"CDN缓存成功: {encrypted_id} (第{check_count + 1}次检查)")
            return True
        
        check_count += 1
        await asyncio.sleep(check_interval)
        logger.debug(f"等待CDN缓存: {encrypted_id} (第{check_count}次检查)")
    
    logger.warning(f"CDN缓存超时: {encrypted_id} (共检查{check_count}次)")
    return False

async def handle_group_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理群组中的图片（非机器人发送）"""
    if not ENABLE_GROUP_UPLOAD:
        return
    
    # 检查是否在存储群组中
    if update.effective_chat.id != STORAGE_CHAT_ID:
        return
    
    # 检查是否是机器人自己发的消息（避免处理自己发送的备份图片）
    if update.effective_user.is_bot:
        return
    
    # 检查是否是机器人自己
    global bot_info
    if bot_info and update.effective_user.id == bot_info.id:
        return
    
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or "未知用户"
    
    # 检查权限
    if GROUP_UPLOAD_ADMIN_ONLY and GROUP_ADMIN_ID_LIST:
        if user_id not in GROUP_ADMIN_ID_LIST:
            logger.info(f"非管理员用户 {username}({user_id}) 在群组中发送图片，跳过处理")
            return
    
    try:
        file_id = None
        file_path = None
        file_size = 0
        file_name = None
        mime_type = None
        is_document = False
        
        # 判断是文档还是图片
        if update.message.document and update.message.document.mime_type.startswith('image/'):
            # 处理作为文档发送的大图片
            document = update.message.document
            file_info = await context.bot.get_file(document.file_id)
            file_id = document.file_id
            file_path = file_info.file_path
            file_size = document.file_size
            file_name = document.file_name
            mime_type = document.mime_type
            is_document = True
            logger.info(f"群组用户 {username}({user_id}) 上传大图片: file_id={file_id}, size={file_size}")
        elif update.message.photo:
            # 处理普通图片
            photo = update.message.photo[-1]
            file_info = await context.bot.get_file(photo.file_id)
            file_id = photo.file_id
            file_path = file_info.file_path
            file_size = file_info.file_size
            mime_type = get_mime_type(file_path)
            logger.info(f"群组用户 {username}({user_id}) 上传图片: file_id={file_id}")
        else:
            return
        
        # 生成加密ID
        encrypted_id = encrypt_file_id(file_id, file_path)
        
        # 保存文件信息
        file_data = {
            'file_id': file_id,
            'file_path': file_path,
            'upload_time': int(time.time()),
            'user_id': user_id,
            'username': username,
            'file_size': file_size,
            'source': 'telegram_group',
            'original_filename': file_name or f'group_image_{int(time.time())}.jpg',
            'mime_type': mime_type or 'image/jpeg',
            'is_group_upload': 1,
            'group_message_id': update.message.message_id
        }
        save_file_info(encrypted_id, file_data)
        
        # 生成链接
        cdn_url = f"https://{CLOUDFLARE_CDN_DOMAIN}/image/{encrypted_id}" if CLOUDFLARE_CDN_DOMAIN else None
        
        # 如果启用了回复且有CDN
        if GROUP_UPLOAD_REPLY and cdn_url:
            # 等待CDN缓存完成
            is_cached = await wait_for_cdn_cache(encrypted_id, cdn_url, timeout=30)
            
            # 只有在CDN缓存成功后才发送回复
            if is_cached:
                # 构建回复文本
                reply_text = f"✅ 图片已收录\n\n🌐 {cdn_url}"
                
                # 发送回复
                reply_msg = await update.message.reply_text(
                    reply_text,
                    disable_web_page_preview=False  # 显示链接预览
                )
                
                # 如果设置了删除延迟
                if GROUP_UPLOAD_DELETE_DELAY > 0:
                    await asyncio.sleep(GROUP_UPLOAD_DELETE_DELAY)
                    try:
                        await reply_msg.delete()
                    except Exception as e:
                        logger.debug(f"删除回复消息失败: {e}")
                
                # 记录成功信息
                file_type = "大图片" if is_document else "图片"
                logger.info(f"群组{file_type}处理完成并已缓存: {encrypted_id}")
            else:
                # CDN预热失败
                logger.warning(f"CDN预热失败，不发送回复: {encrypted_id}")
                # 如果CDN预热失败，仍然将任务加入监控队列
                if CDN_MONITOR_ENABLED:
                    add_to_cdn_monitor(encrypted_id, file_data['upload_time'])
                    logger.info(f"已将 {encrypted_id} 加入CDN监控队列")
        else:
            # 没有启用回复或没有CDN
            if not GROUP_UPLOAD_REPLY:
                logger.info(f"群组图片处理完成(未启用回复): {encrypted_id}")
            elif not cdn_url:
                logger.info(f"群组图片处理完成(无CDN配置): {encrypted_id}")
            
            # 即使不回复，也要加入CDN监控
            if CDN_MONITOR_ENABLED and CLOUDFLARE_CDN_DOMAIN:
                add_to_cdn_monitor(encrypted_id, file_data['upload_time'])
            
    except Exception as e:
        logger.error(f"处理群组图片失败: {e}")
        import traceback
        traceback.print_exc()
        
# ===================== 前端自动启动（开发） =====================
frontend_process = None

def is_port_in_use(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except Exception:
        return False

def wait_for_port(port: int, timeout: int = 30) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        if is_port_in_use(port):
            return True
        time.sleep(0.5)
    return is_port_in_use(port)

def ensure_frontend_dependencies() -> bool:
    if not os.path.isdir(FRONTEND_DIR):
        logger.warning(f"未找到前端目录: {FRONTEND_DIR}")
        return False
    npm_path = shutil.which("npm")
    if npm_path is None:
        logger.warning("未检测到 npm，跳过自动启动前端。请安装 Node.js 或手动运行 npm run dev")
        return False
    node_modules_dir = os.path.join(FRONTEND_DIR, "node_modules")
    need_install = not os.path.isdir(node_modules_dir)

    # 检查必须的图标包是否存在
    required_pkgs = [
        os.path.join(node_modules_dir, "@iconify-json", "heroicons"),
        os.path.join(node_modules_dir, "@iconify-json", "heroicons-outline"),
        os.path.join(node_modules_dir, "@iconify-json", "heroicons-solid"),
        os.path.join(node_modules_dir, "@iconify-json", "lucide")
    ]
    for pkg in required_pkgs:
        if not os.path.isdir(pkg):
            need_install = True
            break

    if need_install:
        logger.info("正在安装/修复前端依赖 (npm install)...")
        try:
            subprocess.check_call([npm_path, "install"], cwd=FRONTEND_DIR)
        except subprocess.CalledProcessError as e:
            logger.error(f"前端依赖安装失败: {e}")
            return False
    return True

def check_and_fix_icon_format():
    """检查并修复前端Vue文件中的图标格式问题"""
    import re

    logger.info("正在检查前端图标格式...")

    # 需要检查的目录
    check_dirs = [
        os.path.join(FRONTEND_DIR, "pages"),
        os.path.join(FRONTEND_DIR, "layouts"),
        os.path.join(FRONTEND_DIR, "components")
    ]

    fixed_files = []
    total_fixes = 0

    # 错误的图标格式模式
    wrong_patterns = [
        (r'name="i-heroicons-([^"]+)"', r'name="heroicons:\1"'),  # UIcon组件
        (r"name='i-heroicons-([^']+)'", r"name='heroicons:\1'"),  # UIcon组件（单引号）
        (r'icon="i-heroicons-([^"]+)"', r'icon="heroicons:\1"'),  # UButton/UInput的icon属性
        (r"icon='i-heroicons-([^']+)'", r"icon='heroicons:\1'"),  # UButton/UInput的icon属性（单引号）
    ]

    for check_dir in check_dirs:
        if not os.path.exists(check_dir):
            continue

        # 递归查找所有.vue文件
        for root, dirs, files in os.walk(check_dir):
            for file in files:
                if not file.endswith('.vue'):
                    continue

                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    original_content = content
                    file_fixed = False
                    fixes_in_file = 0

                    # 应用所有修复模式
                    for wrong_pattern, correct_pattern in wrong_patterns:
                        matches = re.findall(wrong_pattern, content)
                        if matches:
                            content = re.sub(wrong_pattern, correct_pattern, content)
                            fixes_in_file += len(matches)
                            file_fixed = True

                    # 如果有修改，写回文件
                    if file_fixed and content != original_content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)

                        relative_path = os.path.relpath(file_path, FRONTEND_DIR)
                        fixed_files.append(relative_path)
                        total_fixes += fixes_in_file
                        logger.info(f"  ✓ 修复 {relative_path} ({fixes_in_file}处)")

                except Exception as e:
                    logger.warning(f"检查文件 {file_path} 时出错: {e}")

    if fixed_files:
        logger.info(f"图标格式检查完成: 修复了 {len(fixed_files)} 个文件，共 {total_fixes} 处图标格式问题")
        return True
    else:
        logger.info("图标格式检查完成: 未发现需要修复的问题")
        return True

def start_frontend():
    global frontend_process
    if frontend_process is not None and frontend_process.poll() is None:
        logger.info("前端开发服务器已在运行")
        return
    if is_port_in_use(FRONTEND_PORT):
        logger.info(f"检测到前端端口 {FRONTEND_PORT} 已被占用，假定 Nuxt 开发服务已运行，跳过启动")
        return
    if not ensure_frontend_dependencies():
        return

    # 检查并修复图标格式
    check_and_fix_icon_format()
    logger.info(f"启动前端开发服务器: {FRONTEND_DEV_CMD} (cwd={FRONTEND_DIR})")
    creationflags = 0
    preexec_fn = None
    if sys.platform == 'win32':
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        import os as _os
        preexec_fn = _os.setsid
    try:
        frontend_process = subprocess.Popen(
            FRONTEND_DEV_CMD,
            cwd=FRONTEND_DIR,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
            preexec_fn=preexec_fn,
            text=True,
            bufsize=1
        )
        atexit.register(stop_frontend)
        # 异步读取部分输出，便于调试
        threading.Thread(target=_stream_frontend_output, args=(frontend_process,), daemon=True).start()
        if wait_for_port(FRONTEND_PORT, timeout=40):
            logger.info(f"前端已就绪: http://localhost:{FRONTEND_PORT}")
        else:
            logger.warning("前端端口未在预期时间内就绪，请手动检查")
    except Exception as e:
        logger.error(f"启动前端失败: {e}")


def _stream_frontend_output(proc: subprocess.Popen):
    try:
        if proc.stdout is None:
            return
        for line in proc.stdout:
            if not line:
                break
            # 降噪：仅记录关键信息
            if any(key in line.lower() for key in ["ready in", "listening on", "error", "warn", "vite", "nuxt"]):
                logger.info(f"[frontend] {line.strip()}")
    except Exception:
        pass


def stop_frontend():
    global frontend_process
    if frontend_process is None:
        return
    if frontend_process.poll() is not None:
        frontend_process = None
        return
    logger.info("正在停止前端开发服务器...")
    try:
        if sys.platform == 'win32':
            try:
                frontend_process.send_signal(signal.CTRL_BREAK_EVENT)
            except Exception:
                frontend_process.terminate()
        else:
            import os as _os
            _os.killpg(_os.getpgid(frontend_process.pid), signal.SIGTERM)
        try:
            frontend_process.wait(timeout=10)
        except Exception:
            logger.warning("前端进程未按时退出，尝试强制结束")
            if sys.platform == 'win32':
                frontend_process.kill()
            else:
                import os as _os
                _os.killpg(_os.getpgid(frontend_process.pid), signal.SIGKILL)
    finally:
        frontend_process = None

# ===================== 主函数 =====================
def run_flask():
    """运行Flask应用"""
    logger.info(f"Flask服务器启动在: {LOCAL_IP}:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)

def run_telegram_bot():
    """运行Telegram机器人"""
    global telegram_app, bot_info
    
    if not BOT_TOKEN:
        logger.error("请先配置BOT_TOKEN！")
        return
    
    async def start_bot():
        """异步启动机器人"""
        global telegram_app, bot_info
        
        try:
            telegram_app = Application.builder().token(BOT_TOKEN).build()
            
            # 添加处理器
            telegram_app.add_handler(CommandHandler("start", start))
            telegram_app.add_handler(MessageHandler(filters.PHOTO & ~filters.ChatType.GROUP, handle_photo))
            telegram_app.add_handler(MessageHandler(filters.Document.IMAGE & ~filters.ChatType.GROUP, handle_photo))
            
            # 群组图片处理器（仅在存储群组中生效）
            if ENABLE_GROUP_UPLOAD:
                # 群组中的图片
                telegram_app.add_handler(MessageHandler(
                    filters.PHOTO & filters.Chat(STORAGE_CHAT_ID),
                    handle_group_photo
                ))
                # 群组中的图片文档
                telegram_app.add_handler(MessageHandler(
                    filters.Document.IMAGE & filters.Chat(STORAGE_CHAT_ID),
                    handle_group_photo
                ))
            
            logger.info("Telegram机器人启动中...")
            
            # 获取机器人信息
            bot_info = await telegram_app.bot.get_me()
            logger.info(f"机器人信息: @{bot_info.username} (ID: {bot_info.id})")
            
            # 启动机器人
            await telegram_app.initialize()
            await telegram_app.start()
            await telegram_app.updater.start_polling(drop_pending_updates=True)
            
            logger.info("Telegram机器人已成功启动")
            
            # 保持运行
            await asyncio.Event().wait()
            
        except Exception as e:
            logger.error(f"Telegram机器人启动失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if telegram_app:
                await telegram_app.stop()
    
    # 使用 asyncio.run 运行异步函数
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        logger.info("Telegram机器人收到停止信号")
    except Exception as e:
        logger.error(f"运行Telegram机器人时发生错误: {e}")

def main():
    """主函数"""
    # 检查是否已有实例在运行
    if not acquire_lock():
        logger.error("程序已在运行中，请勿重复启动")
        sys.exit(1)
    
    init_database()
    
    # 启动CDN监控
    if CDN_ENABLED and CLOUDFLARE_CDN_DOMAIN and CDN_MONITOR_ENABLED:
        start_cdn_monitor()
    
    logger.info("启动Telegram云图床服务...")

    # 检查前端静态文件是否存在
    if not os.path.exists(STATIC_FOLDER):
        logger.warning("=" * 60)
        logger.warning("前端静态文件未找到！")
        logger.warning("请运行以下命令构建前端：")
        logger.warning("  cd frontend && npm run generate")
        logger.warning("=" * 60)
    else:
        logger.info(f"前端静态文件已就绪: {STATIC_FOLDER}")

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # 前端已内置，不再需要单独启动开发服务器
    logger.info("前端已内置到Flask中，统一端口服务")

    time.sleep(2)
    
    try:
        if BOT_TOKEN:
            run_telegram_bot()
        else:
            logger.warning("Telegram机器人未启动，请配置Token后重启")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("服务已停止")
    finally:
        stop_frontend()
        stop_cdn_monitor()
        release_lock()

if __name__ == '__main__':
    main()