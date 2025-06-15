#
#!/usr/bin/env python3
"""
TELEGRAM MULTI USERBOT MANAGER - JASEBSIX
Version: 3.0 ULTIMATE BY HIYAOK
Features: Multi userbot, schedule, auto expire, full control
Author: Jasebsix
Creator : @hiyaok
"""

import asyncio
import os
import json
import re
import sys
from datetime import datetime, timedelta
from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, UserNotParticipantError, SessionPasswordNeededError
import logging
from typing import Dict, List, Optional
import shutil
from pathlib import Path

# ==================== CONFIGURATION ====================
# GANTI DENGAN API CREDENTIALS ANDA
API_ID = 20706311  # GANTI DENGAN API ID ANDA
API_HASH = '3bde90bb1545d10b9d2f302586ca5e6f'  # GANTI DENGAN API HASH ANDA

# Directories
BASE_DIR = Path("userbot_data")
SESSIONS_DIR = BASE_DIR / "sessions"
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = BASE_DIR / "backups"

# Files
MANAGER_DATA = BASE_DIR / "manager.json"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== USERBOT CLASS ====================
class UserBot:
    def __init__(self, phone: str, session_name: str, expire_date: datetime):
        self.phone = phone
        self.session_name = session_name
        self.expire_date = expire_date
        self.client = None
        self.data_file = DATA_DIR / f"{session_name}_data.json"
        self.data = self.load_data()
        self.running = False
        self.timer_task = None
        self.schedule_task = None
        self.is_active = True
        
    def load_data(self):
        """Load saved data from JSON file"""
        default_data = {
            'phone': self.phone,
            'session_name': self.session_name,
            'expire_date': self.expire_date.isoformat(),
            'created_date': datetime.now().isoformat(),
            'admins': [],
            'groups': [],
            'selected_groups': [],
            'message': {'text': '', 'forward': False},
            'pm_enabled': False,
            'pm_message': '',
            'sleep_enabled': False,
            'sleep_time': {'start': '22:00', 'end': '06:00'},
            'notif_user': None,
            'spam_timer': 5,
            'group_timer': 1,  # Default 1 detik delay antar grup
            'run_timer': None,
            'bot_active': True,
            'schedule': {
                'enabled': False,
                'start_date': None,
                'end_date': None
            },
            'stats': {
                'total_sent': 0,
                'total_failed': 0,
                'last_run': None
            }
        }
        
        try:
            if self.data_file.exists():
                with open(self.data_file, 'r') as f:
                    loaded_data = json.load(f)
                    for key, value in default_data.items():
                        if key not in loaded_data:
                            loaded_data[key] = value
                    return loaded_data
            return default_data
        except:
            return default_data
    
    def save_data(self):
        """Save data to JSON file with backup"""
        try:
            # Create backup first
            if self.data_file.exists():
                backup_file = BACKUP_DIR / f"{self.session_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                shutil.copy(self.data_file, backup_file)
                
                # Keep only last 5 backups
                backups = sorted(BACKUP_DIR.glob(f"{self.session_name}_*.json"))
                if len(backups) > 5:
                    for old_backup in backups[:-5]:
                        old_backup.unlink()
            
            # Save data
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving data: {e}")
    
    async def start(self):
        """Start the userbot"""
        try:
            session_file = SESSIONS_DIR / f"{self.session_name}.session"
            self.client = TelegramClient(str(session_file), API_ID, API_HASH)
            
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                logger.error(f"Session {self.session_name} not authorized!")
                return False
            
            # Get self info
            me = await self.client.get_me()
            if not self.data['admins']:
                self.data['admins'] = [me.id]
                self.save_data()
            
            # Register handlers
            self.register_handlers()
            
            # Start schedule checker
            self.schedule_task = asyncio.create_task(self.check_schedule())
            
            # Send startup notification
            await self.send_admin_notif(
                "🚀 **USERBOT STARTED**\n\n"
                f"👤 **User:** {me.first_name}\n"
                f"🆔 **ID:** `{me.id}`\n"
                f"📱 **Username:** @{me.username}\n"
                f"📱 **Phone:** {self.phone}\n"
                f"⏰ **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"📅 **Expire:** {self.expire_date.strftime('%Y-%m-%d')}\n\n"
                "Ketik `.fitur` untuk melihat semua fitur."
            )
            
            self.is_active = True
            return True
            
        except Exception as e:
            logger.error(f"Error starting userbot: {e}")
            return False
    
    async def stop(self):
        """Stop the userbot and logout"""
        try:
            if self.timer_task:
                self.timer_task.cancel()
            if self.schedule_task:
                self.schedule_task.cancel()
            
            self.running = False
            self.is_active = False
            
            if self.client and self.client.is_connected():
                # Leave all groups first
                async for dialog in self.client.iter_dialogs():
                    if dialog.is_group or dialog.is_channel:
                        try:
                            await self.client.delete_dialog(dialog)
                        except:
                            pass
                
                # Send goodbye message
                await self.send_admin_notif(
                    "👋 **USERBOT STOPPED**\n\n"
                    f"Session {self.session_name} has been terminated.\n"
                    f"All groups have been left."
                )
                
                # Logout and disconnect
                await self.client.log_out()
                await self.client.disconnect()
            
            # Remove session file
            session_file = SESSIONS_DIR / f"{self.session_name}.session"
            if session_file.exists():
                session_file.unlink()
            
            return True
            
        except Exception as e:
            logger.error(f"Error stopping userbot: {e}")
            return False
    
    def register_handlers(self):
        """Register all event handlers"""
        
        @self.client.on(events.NewMessage(pattern=r'^\.jasebsix$'))
        async def tutorial_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            tutorial = f"""
🔑 **TUTORIAL USERBOT JASEBSIX**

📱 **Session Info:**
• Phone: {self.phone}
• Expire: {self.expire_date.strftime('%Y-%m-%d')}
• Days left: {(self.expire_date - datetime.now()).days}

📋 **Quick Start:**
1. `.cekgrub` - Cek semua grup
2. `.setgrub all` - Pilih semua grup
3. Reply pesan → `.pesan nofw`
4. `.jadwal set` - Set jadwal (opsional)
5. `.run 5` - Mulai kirim tiap 5 menit

✨ **New Features:**
• Schedule otomatis
• Auto expire
• Multi userbot support

📚 Ketik `.fitur` untuk lihat semua perintah
"""
            await event.reply(tutorial)
        
        @self.client.on(events.NewMessage(pattern=r'^\.cekgrub$'))
        async def check_groups_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            await event.reply("🔍 Mengecek grup...")
            
            self.data['groups'] = []
            index = 1
            
            message = "📁 **DAFTAR GRUP:**\n\n"
            
            async for dialog in self.client.iter_dialogs():
                if dialog.is_group or dialog.is_channel:
                    self.data['groups'].append({
                        'id': dialog.id,
                        'title': dialog.title,
                        'index': index
                    })
                    
                    status = "✅" if dialog.id in [g['id'] for g in self.data.get('selected_groups', [])] else "❌"
                    message += f"{index}. {status} **{dialog.title}**\n"
                    index += 1
            
            self.save_data()
            
            message += f"\n📊 Total: {len(self.data['groups'])} grup"
            message += f"\n✅ Selected: {len(self.data.get('selected_groups', []))} grup"
            await event.reply(message)
        
        @self.client.on(events.NewMessage(pattern=r'^\.setgrub\s+(.+)$'))
        async def set_groups_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            args = event.pattern_match.group(1).strip()
            
            if args.lower() == 'all':
                self.data['selected_groups'] = self.data['groups'].copy()
                await event.reply(f"✅ Semua {len(self.data['groups'])} grup telah dipilih!")
            else:
                try:
                    indices = [int(x.strip()) for x in args.split()]
                    selected = []
                    
                    for idx in indices:
                        for group in self.data['groups']:
                            if group['index'] == idx:
                                selected.append(group)
                                break
                    
                    self.data['selected_groups'] = selected
                    await event.reply(f"✅ {len(selected)} grup telah dipilih!")
                except:
                    await event.reply("❌ Format salah! Gunakan: `.setgrub 1 2 3` atau `.setgrub all`")
            
            self.save_data()
        
        @self.client.on(events.NewMessage(pattern=r'^\.resetgrup$'))
        async def reset_groups_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            self.data['selected_groups'] = []
            self.save_data()
            await event.reply("🔄 Semua grup target telah direset!")
        
        @self.client.on(events.NewMessage(pattern=r'^\.pesan\s+(fw|nofw)$'))
        async def set_message_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            if not event.is_reply:
                await event.reply("❌ Reply ke pesan yang ingin disimpan!")
                return
            
            replied = await event.get_reply_message()
            forward = event.pattern_match.group(1) == 'fw'
            
            # Detect media type
            media_type = None
            if replied.photo:
                media_type = "Photo"
            elif replied.video:
                media_type = "Video"
            elif replied.document:
                media_type = "Document"
            elif replied.sticker:
                media_type = "Sticker"
            elif replied.voice:
                media_type = "Voice"
            elif replied.audio:
                media_type = "Audio"
            elif replied.gif:
                media_type = "GIF"
            
            # Save complete message data
            self.data['message'] = {
                'text': replied.text or '',
                'forward': forward,
                'from_id': replied.sender_id,
                'message_id': replied.id,
                'chat_id': replied.chat_id,
                'media_type': media_type,
                'has_media': bool(replied.media),
                'saved_time': datetime.now().isoformat()
            }
            self.save_data()
            
            response = f"✅ **Pesan berhasil disimpan!**\n\n"
            response += f"📋 Mode: {'Forward' if forward else 'No Forward'}\n"
            if media_type:
                response += f"📎 Media: {media_type}\n"
            if replied.text:
                response += f"💬 Caption: {len(replied.text)} chars\n"
            response += f"⏰ Saved: {datetime.now().strftime('%H:%M:%S')}\n"
            response += f"✨ Formatting: **Preserved!**"
            
            await event.reply(response)
        
        @self.client.on(events.NewMessage(pattern=r'^\.jadwal\s+(.+)$'))
        async def schedule_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            args = event.pattern_match.group(1).strip()
            
            if args == 'set':
                await event.reply(
                    "📅 **SET JADWAL**\n\n"
                    "Format: `.jadwal YYYY-MM-DD HH:MM to YYYY-MM-DD HH:MM`\n"
                    "Contoh: `.jadwal 2024-01-15 09:00 to 2024-01-15 17:00`\n\n"
                    "Atau gunakan:\n"
                    "`.jadwal now to 2024-01-15 17:00` - Mulai sekarang"
                )
            elif args == 'off':
                self.data['schedule']['enabled'] = False
                self.save_data()
                await event.reply("📅 Jadwal dinonaktifkan!")
            elif args == 'info':
                sched = self.data['schedule']
                if sched['enabled']:
                    await event.reply(
                        f"📅 **JADWAL AKTIF**\n\n"
                        f"🟢 Start: {sched['start_date']}\n"
                        f"🔴 End: {sched['end_date']}\n"
                        f"⏰ Current: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    )
                else:
                    await event.reply("📅 Jadwal tidak aktif")
            else:
                # Parse schedule
                try:
                    parts = args.split(' to ')
                    if len(parts) == 2:
                        start_str, end_str = parts
                        
                        if start_str.lower() == 'now':
                            start_date = datetime.now()
                        else:
                            start_date = datetime.strptime(start_str, '%Y-%m-%d %H:%M')
                        
                        end_date = datetime.strptime(end_str, '%Y-%m-%d %H:%M')
                        
                        self.data['schedule'] = {
                            'enabled': True,
                            'start_date': start_date.isoformat(),
                            'end_date': end_date.isoformat()
                        }
                        self.save_data()
                        
                        await event.reply(
                            f"📅 **JADWAL DIATUR**\n\n"
                            f"🟢 Mulai: {start_date.strftime('%Y-%m-%d %H:%M')}\n"
                            f"🔴 Berakhir: {end_date.strftime('%Y-%m-%d %H:%M')}\n"
                            f"⏱ Durasi: {end_date - start_date}"
                        )
                except:
                    await event.reply("❌ Format salah! Gunakan: `.jadwal info` untuk bantuan")
        
        @self.client.on(events.NewMessage(pattern=r'^\.on$'))
        async def activate_bot_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            self.data['bot_active'] = True
            self.save_data()
            await event.reply("✅ Bot diaktifkan!")
        
        @self.client.on(events.NewMessage(pattern=r'^\.off$'))
        async def deactivate_bot_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            self.data['bot_active'] = False
            self.running = False
            if self.timer_task:
                self.timer_task.cancel()
            self.save_data()
            await event.reply("❌ Bot dinonaktifkan! (Session tetap aktif)")
        
        @self.client.on(events.NewMessage(pattern=r'^\.pm\s+(.+)$'))
        async def pm_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            args = event.pattern_match.group(1).strip()
            
            if args == 'on':
                self.data['pm_enabled'] = True
                await event.reply("✅ Auto reply PM diaktifkan!")
            elif args == 'off':
                self.data['pm_enabled'] = False
                await event.reply("❌ Auto reply PM dinonaktifkan!")
            else:
                self.data['pm_message'] = args
                await event.reply("✅ Pesan PM berhasil diatur!")
            
            self.save_data()
        
        @self.client.on(events.NewMessage(pattern=r'^\.tidur\s+(.+)$'))
        async def sleep_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            args = event.pattern_match.group(1).strip()
            
            if args == 'on':
                self.data['sleep_enabled'] = True
                await event.reply("✅ Mode tidur diaktifkan!")
            elif args == 'off':
                self.data['sleep_enabled'] = False
                await event.reply("❌ Mode tidur dinonaktifkan!")
            else:
                match = re.match(r'(\d{1,2}[:.]\d{2})-(\d{1,2}[:.]\d{2})', args)
                if match:
                    self.data['sleep_time'] = {
                        'start': match.group(1).replace('.', ':'),
                        'end': match.group(2).replace('.', ':')
                    }
                    await event.reply(f"✅ Waktu tidur diatur: {match.group(1)} - {match.group(2)}")
                else:
                    await event.reply("❌ Format salah! Gunakan: `.tidur 22:00-06:00`")
            
            self.save_data()
        
        @self.client.on(events.NewMessage(pattern=r'^\.run\s+(.+)$'))
        async def run_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            args = event.pattern_match.group(1).strip()
            
            if args == 'off':
                self.running = False
                if self.timer_task:
                    self.timer_task.cancel()
                self.data['run_timer'] = None
                await event.reply("⏹ Timer dihentikan!")
            else:
                try:
                    minutes = int(args)
                    self.data['run_timer'] = minutes
                    self.running = True
                    
                    await event.reply(
                        f"▶️ **TIMER STARTED**\n\n"
                        f"⏱ Interval: {minutes} menit\n"
                        f"📊 Target: {len(self.data.get('selected_groups', []))} grup\n"
                        f"⏸ Stop: `.run off`"
                    )
                    
                    if self.timer_task:
                        self.timer_task.cancel()
                    self.timer_task = asyncio.create_task(self.timer_loop())
                except:
                    await event.reply("❌ Format salah! Gunakan: `.run 5` (dalam menit)")
            
            self.save_data()
        
        @self.client.on(events.NewMessage(pattern=r'^\.notif\s+(.+)$'))
        async def notif_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            args = event.pattern_match.group(1).strip()
            
            if args == 'off':
                self.data['notif_user'] = None
                await event.reply("📴 Notifikasi dinonaktifkan!")
            else:
                self.data['notif_user'] = args.replace('@', '')
                await event.reply(f"📬 Notifikasi akan dikirim ke @{self.data['notif_user']}")
            
            self.save_data()
        
        @self.client.on(events.NewMessage(pattern=r'^\.timer\s+(spam|grub)\s+(\d+)$'))
        async def timer_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            timer_type = event.pattern_match.group(1)
            seconds = int(event.pattern_match.group(2))
            
            if timer_type == 'spam':
                self.data['spam_timer'] = seconds
                await event.reply(f"⏱ Timer spam diatur: {seconds} detik")
            else:
                self.data['group_timer'] = seconds
                await event.reply(f"⏱ Timer antar grup diatur: {seconds} detik")
            
            self.save_data()
        
        @self.client.on(events.NewMessage(pattern=r'^\.admin\s+(add|del)\s+(.+)$'))
        async def admin_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            action = event.pattern_match.group(1)
            username = event.pattern_match.group(2).replace('@', '')
            
            try:
                user = await self.client.get_entity(username)
                
                if action == 'add':
                    if user.id not in self.data['admins']:
                        self.data['admins'].append(user.id)
                        await event.reply(f"✅ {user.first_name} ditambahkan sebagai admin!")
                    else:
                        await event.reply("⚠️ User sudah menjadi admin!")
                else:
                    if user.id in self.data['admins'] and user.id != event.sender_id:
                        self.data['admins'].remove(user.id)
                        await event.reply(f"✅ {user.first_name} dihapus dari admin!")
                    else:
                        await event.reply("⚠️ Tidak dapat menghapus admin ini!")
                
                self.save_data()
            except:
                await event.reply("❌ User tidak ditemukan!")
        
        @self.client.on(events.NewMessage(pattern=r'^\.join\s+(.+)$'))
        async def join_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            groups = event.pattern_match.group(1).split()
            joined = 0
            
            await event.reply(f"🔄 Mencoba join {len(groups)} grup...")
            
            for group in groups[:5]:
                try:
                    group_username = group.replace('@', '')
                    await self.client(functions.channels.JoinChannelRequest(group_username))
                    joined += 1
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"Failed to join {group}: {e}")
            
            await event.reply(f"✅ Berhasil join {joined}/{len(groups[:5])} grup!")
        
        @self.client.on(events.NewMessage(pattern=r'^\.out$'))
        async def leave_all_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            await event.reply("🔄 Keluar dari semua grup...")
            left = 0
            
            async for dialog in self.client.iter_dialogs():
                if dialog.is_group or dialog.is_channel:
                    try:
                        await self.client.delete_dialog(dialog)
                        left += 1
                        await asyncio.sleep(1)
                    except:
                        pass
            
            await event.reply(f"✅ Berhasil keluar dari {left} grup!")
        
        @self.client.on(events.NewMessage(pattern=r'^\.reset\s+all$'))
        async def reset_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            admins = self.data['admins']
            self.data = self.load_data()
            self.data['admins'] = admins
            self.save_data()
            
            await event.reply("♻️ Semua pengaturan telah direset!")
        
        @self.client.on(events.NewMessage(pattern=r'^\.fitur$'))
        async def features_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            features = """
📚 **DAFTAR FITUR USERBOT V3.0**

**📌 Tutorial & Info:**
• `.jasebking` - Tutorial penggunaan
• `.fitur` - Daftar semua fitur
• `.status` - Status lengkap userbot

**📁 Manajemen Grup:**
• `.cekgrub` - Cek semua grup
• `.setgrub 2 5 8` - Pilih grup tertentu
• `.setgrub all` - Pilih semua grup
• `.resetgrup` - Reset semua pilihan grup
• `.join @grup1 @grup2` - Join grup (max 5)
• `.out` - Keluar dari semua grup

**💬 Pengaturan Pesan:**
• `.pesan fw` - Set pesan forward (reply)
• `.pesan nofw` - Set pesan no forward (reply)

**📅 Jadwal (NEW!):**
• `.jadwal set` - Lihat cara set jadwal
• `.jadwal YYYY-MM-DD HH:MM to YYYY-MM-DD HH:MM` - Set jadwal
• `.jadwal now to YYYY-MM-DD HH:MM` - Mulai sekarang
• `.jadwal info` - Lihat jadwal aktif
• `.jadwal off` - Matikan jadwal

**🤖 Kontrol Bot:**
• `.on` - Aktifkan bot (fitur only)
• `.off` - Nonaktifkan bot (session tetap)
• `.run 5` - Kirim tiap 5 menit
• `.run off` - Matikan timer

**💤 Mode Tidur:**
• `.tidur on` - Aktifkan mode tidur
• `.tidur off` - Nonaktifkan mode tidur
• `.tidur 22:00-06:00` - Set waktu tidur

**📨 Auto Reply PM:**
• `.pm on` - Aktifkan auto reply
• `.pm off` - Nonaktifkan auto reply
• `.pm <pesan>` - Set pesan auto reply

**⏱ Timer:**
• `.timer spam 5` - Delay antar spam (detik)
• `.timer grub 1` - Delay antar grup (detik)

**📬 Notifikasi:**
• `.notif @username` - Kirim notif ke user
• `.notif off` - Matikan notifikasi

**👥 Admin:**
• `.admin add @user` - Tambah admin
• `.admin del @user` - Hapus admin
• `.sudo <user_id>` - Tambah sudo
• `.delsudo <user_id>` - Hapus sudo
• `.listsudo` - Daftar sudo

**🔧 Lainnya:**
• `.reset all` - Reset semua pengaturan
"""
            await event.reply(features)
        
        @self.client.on(events.NewMessage(pattern=r'^\.status$'))
        async def status_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            me = await self.client.get_me()
            
            # Calculate session info
            days_left = (self.expire_date - datetime.now()).days
            created_date = datetime.fromisoformat(self.data.get('created_date', datetime.now().isoformat()))
            days_active = (datetime.now() - created_date).days
            
            # Get saved message info
            msg_info = "Tidak ada"
            if self.data.get('message', {}).get('message_id'):
                msg = self.data['message']
                msg_type = msg.get('media_type', 'Text')
                msg_mode = 'Forward' if msg.get('forward') else 'No Forward'
                saved_time = datetime.fromisoformat(msg.get('saved_time', datetime.now().isoformat()))
                time_ago = datetime.now() - saved_time
                hours_ago = int(time_ago.total_seconds() / 3600)
                msg_info = f"{msg_type} ({msg_mode}) - {hours_ago}h ago"
            
            # Schedule info
            sched_info = "Tidak aktif"
            if self.data['schedule']['enabled']:
                start = self.data['schedule']['start_date']
                end = self.data['schedule']['end_date']
                sched_info = f"Aktif ({start[:10]} → {end[:10]})"
            
            # Stats
            stats = self.data.get('stats', {})
            
            status = f"""
📊 **STATUS USERBOT LENGKAP**

**👤 User Info:**
• Name: {me.first_name}
• ID: `{me.id}`
• Username: @{me.username or 'None'}
• Phone: {self.phone}

**📱 Session Info:**
• Session: {self.session_name}
• Created: {created_date.strftime('%Y-%m-%d')}
• Active: {days_active} hari
• Expire: {self.expire_date.strftime('%Y-%m-%d')}
• Days left: {days_left} hari {'⚠️' if days_left < 3 else '✅'}

**⚙️ Settings:**
• Bot Status: {'✅ Aktif' if self.data['bot_active'] else '❌ Nonaktif'}
• Selected Groups: {len(self.data.get('selected_groups', []))}/{len(self.data.get('groups', []))}
• Saved Message: {msg_info}
• Timer: {self.data.get('run_timer', 'Off')} {'menit' if self.data.get('run_timer') else ''}
• Schedule: {sched_info}
• Sleep Mode: {'✅ On' if self.data.get('sleep_enabled', False) else '❌ Off'}
• Auto Reply: {'✅ On' if self.data.get('pm_enabled', False) else '❌ Off'}
• Admins: {len(self.data.get('admins', []))}

**⏰ Timer Config:**
• Spam Timer: {self.data.get('spam_timer', 5)}s
• Group Timer: {self.data.get('group_timer', 1)}s
• Notification: {'@' + self.data.get('notif_user', 'Off') if self.data.get('notif_user') else 'Off'}

**📈 Statistics:**
• Total Sent: {stats.get('total_sent', 0):,}
• Total Failed: {stats.get('total_failed', 0):,}
• Success Rate: {(stats.get('total_sent', 0) / (stats.get('total_sent', 0) + stats.get('total_failed', 1)) * 100):.1f}%
• Last Run: {stats.get('last_run', 'Never')}

**💾 Storage:**
• Data Size: {os.path.getsize(self.data_file) / 1024:.1f} KB
• Backups: {len(list(BACKUP_DIR.glob(f'{self.session_name}_*.json')))}
"""
            await event.reply(status)
        
        @self.client.on(events.NewMessage(pattern=r'^\.sudo\s+(\d+)$'))
        async def add_sudo_handler(event):
            if event.sender_id != self.data['admins'][0]:
                return
            
            user_id = int(event.pattern_match.group(1))
            if user_id not in self.data['admins']:
                self.data['admins'].append(user_id)
                self.save_data()
                await event.reply(f"✅ User {user_id} ditambahkan sebagai sudo!")
            else:
                await event.reply("⚠️ User sudah menjadi sudo!")
        
        @self.client.on(events.NewMessage(pattern=r'^\.delsudo\s+(\d+)$'))
        async def del_sudo_handler(event):
            if event.sender_id != self.data['admins'][0]:
                return
            
            user_id = int(event.pattern_match.group(1))
            if user_id in self.data['admins'] and user_id != self.data['admins'][0]:
                self.data['admins'].remove(user_id)
                self.save_data()
                await event.reply(f"✅ User {user_id} dihapus dari sudo!")
            else:
                await event.reply("⚠️ Tidak dapat menghapus user ini!")
        
        @self.client.on(events.NewMessage(pattern=r'^\.listsudo$'))
        async def list_sudo_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            sudo_list = "👥 **DAFTAR SUDO/ADMIN:**\n\n"
            for i, admin_id in enumerate(self.data['admins']):
                try:
                    user = await self.client.get_entity(admin_id)
                    sudo_list += f"{i+1}. {user.first_name} (`{admin_id}`)\n"
                except:
                    sudo_list += f"{i+1}. Unknown (`{admin_id}`)\n"
            
            await event.reply(sudo_list)
        
        # Auto reply PM handler
        @self.client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
        async def pm_auto_reply(event):
            if self.data.get('pm_enabled', False) and self.data.get('pm_message'):
                if event.sender_id not in self.data['admins']:
                    await event.reply(self.data['pm_message'])
    
    async def is_admin(self, user_id):
        """Check if user is admin"""
        return user_id in self.data['admins']
    
    async def is_sleep_time(self):
        """Check if current time is in sleep period"""
        if not self.data.get('sleep_enabled', False):
            return False
        
        now = datetime.now().time()
        start_time = datetime.strptime(self.data['sleep_time']['start'], '%H:%M').time()
        end_time = datetime.strptime(self.data['sleep_time']['end'], '%H:%M').time()
        
        if start_time <= end_time:
            return start_time <= now <= end_time
        else:
            return now >= start_time or now <= end_time
    
    async def check_schedule(self):
        """Check if current time is within schedule"""
        while self.is_active:
            try:
                if self.data['schedule']['enabled']:
                    now = datetime.now()
                    start = datetime.fromisoformat(self.data['schedule']['start_date'])
                    end = datetime.fromisoformat(self.data['schedule']['end_date'])
                    
                    # Check if schedule has ended
                    if now > end:
                        self.data['schedule']['enabled'] = False
                        self.running = False
                        if self.timer_task:
                            self.timer_task.cancel()
                        self.save_data()
                        
                        await self.send_admin_notif(
                            "⏰ **JADWAL BERAKHIR**\n\n"
                            f"Bot telah berhenti otomatis karena jadwal berakhir.\n"
                            f"End time: {end.strftime('%Y-%m-%d %H:%M')}"
                        )
                    
                    # Check if within schedule
                    elif start <= now <= end:
                        # Within schedule, allow running
                        pass
                    else:
                        # Before schedule start
                        if self.running:
                            self.running = False
                            if self.timer_task:
                                self.timer_task.cancel()
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Schedule check error: {e}")
                await asyncio.sleep(60)
    
    async def send_admin_notif(self, message):
        """Send notification to admin"""
        try:
            for admin_id in self.data['admins']:
                await self.client.send_message(admin_id, message)
        except:
            pass
    
    async def send_message_to_group(self, group_id, message_data):
        """Send message to a group with perfect copy"""
        try:
            if message_data.get('forward'):
                return await self.client.forward_messages(
                    group_id,
                    message_data['message_id'],
                    message_data['from_id']
                )
            else:
                original_msg = await self.client.get_messages(
                    message_data.get('chat_id', message_data['from_id']),
                    ids=message_data['message_id']
                )
                
                if not original_msg:
                    raise Exception("Original message not found")
                
                return await self.client.send_message(
                    group_id,
                    message=original_msg.message,
                    file=original_msg.media,
                    formatting_entities=original_msg.entities,
                    buttons=original_msg.buttons,
                    link_preview=original_msg.web_preview
                )
                
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise e
    
    async def timer_loop(self):
        """Main timer loop for sending messages"""
        while self.running and self.data.get('run_timer'):
            try:
                # Check schedule
                if self.data['schedule']['enabled']:
                    now = datetime.now()
                    start = datetime.fromisoformat(self.data['schedule']['start_date'])
                    end = datetime.fromisoformat(self.data['schedule']['end_date'])
                    
                    if not (start <= now <= end):
                        await asyncio.sleep(60)
                        continue
                
                # Check sleep time
                if await self.is_sleep_time():
                    await asyncio.sleep(60)
                    continue
                
                if not self.data.get('bot_active', True):
                    await asyncio.sleep(60)
                    continue
                
                if not self.data.get('message', {}).get('message_id'):
                    logger.warning("No message set for broadcasting")
                    await asyncio.sleep(60)
                    continue
                
                # Send messages to selected groups
                success = 0
                failed = 0
                start_time = datetime.now()
                
                for group in self.data.get('selected_groups', []):
                    try:
                        await self.send_message_to_group(group['id'], self.data['message'])
                        success += 1
                        
                        # Always wait 1 second between groups
                        await asyncio.sleep(self.data.get('group_timer', 1))
                        
                    except FloodWaitError as e:
                        logger.warning(f"Flood wait: {e.seconds} seconds")
                        await asyncio.sleep(e.seconds)
                    except Exception as e:
                        failed += 1
                        logger.error(f"Failed to send to {group['title']}: {e}")
                
                # Update stats
                self.data['stats']['total_sent'] += success
                self.data['stats']['total_failed'] += failed
                self.data['stats']['last_run'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.save_data()
                
                time_taken = (datetime.now() - start_time).seconds
                
                # Send detailed notification
                if self.data.get('notif_user'):
                    try:
                        media_info = ""
                        if self.data['message'].get('media_type'):
                            media_info = f"📎 Media: {self.data['message']['media_type']}\n"
                        
                        await self.client.send_message(
                            self.data['notif_user'],
                            f"📊 **LAPORAN PENGIRIMAN**\n\n"
                            f"📱 Session: {self.session_name}\n"
                            f"👤 Phone: {self.phone}\n\n"
                            f"✅ Berhasil: {success}/{len(self.data.get('selected_groups', []))}\n"
                            f"❌ Gagal: {failed}\n"
                            f"{media_info}"
                            f"⏱ Waktu: {time_taken} detik\n"
                            f"⏰ Selesai: {datetime.now().strftime('%H:%M:%S')}\n\n"
                            f"📈 **Total Stats:**\n"
                            f"• Sent: {self.data['stats']['total_sent']:,}\n"
                            f"• Failed: {self.data['stats']['total_failed']:,}\n"
                            f"• Success Rate: {(self.data['stats']['total_sent'] / (self.data['stats']['total_sent'] + self.data['stats']['total_failed']) * 100):.1f}%"
                        )
                    except:
                        pass
                
                logger.info(f"[{self.session_name}] Broadcast complete: {success} success, {failed} failed")
                
                # Wait for next cycle
                await asyncio.sleep(self.data['run_timer'] * 60)
                
            except Exception as e:
                logger.error(f"Timer loop error: {e}")
                await asyncio.sleep(60)

# ==================== MANAGER CLASS ====================
class UserBotManager:
    def __init__(self):
        self.setup_directories()
        self.load_manager_data()
        self.bots: Dict[str, UserBot] = {}
        
    def setup_directories(self):
        """Create necessary directories"""
        for directory in [BASE_DIR, SESSIONS_DIR, DATA_DIR, BACKUP_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def load_manager_data(self):
        """Load manager data"""
        try:
            if MANAGER_DATA.exists():
                with open(MANAGER_DATA, 'r') as f:
                    self.manager_data = json.load(f)
            else:
                self.manager_data = {
                    'sessions': [],
                    'created_at': datetime.now().isoformat()
                }
                self.save_manager_data()
        except:
            self.manager_data = {'sessions': []}
    
    def save_manager_data(self):
        """Save manager data"""
        with open(MANAGER_DATA, 'w') as f:
            json.dump(self.manager_data, f, indent=2)
    
    async def create_session(self):
        """Create new userbot session"""
        print("\n" + "="*50)
        print("📱 CREATE NEW USERBOT SESSION")
        print("="*50)
        
        # Get duration
        while True:
            try:
                days = int(input("\n📅 Berapa hari userbot aktif? (1-365): "))
                if 1 <= days <= 365:
                    break
                print("❌ Masukkan angka antara 1-365!")
            except:
                print("❌ Masukkan angka yang valid!")
        
        expire_date = datetime.now() + timedelta(days=days)
        
        # Get phone number
        phone = input("\n📱 Masukkan nomor telepon (dengan kode negara, contoh: +628xxx): ")
        
        # Create session name
        session_name = f"bot_{phone.replace('+', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create client
        session_file = SESSIONS_DIR / f"{session_name}.session"
        client = TelegramClient(str(session_file), API_ID, API_HASH)
        
        try:
            await client.start(phone=phone)
            
            # Get user info
            me = await client.get_me()
            
            print(f"\n✅ Login berhasil!")
            print(f"👤 Nama: {me.first_name}")
            print(f"🆔 ID: {me.id}")
            print(f"📱 Username: @{me.username}")
            
            # Save session info
            session_info = {
                'session_name': session_name,
                'phone': phone,
                'user_id': me.id,
                'username': me.username,
                'first_name': me.first_name,
                'created_at': datetime.now().isoformat(),
                'expire_date': expire_date.isoformat(),
                'active': True
            }
            
            self.manager_data['sessions'].append(session_info)
            self.save_manager_data()
            
            # Create userbot instance
            bot = UserBot(phone, session_name, expire_date)
            bot.client = client
            
            # Initialize bot data
            bot.data['admins'] = [me.id]
            bot.save_data()
            
            # Start bot
            if await bot.start():
                self.bots[session_name] = bot
                print(f"\n✅ Userbot berhasil dibuat dan diaktifkan!")
                print(f"📅 Expire: {expire_date.strftime('%Y-%m-%d')} ({days} hari)")
            
            await client.disconnect()
            
        except SessionPasswordNeededError:
            password = input("🔐 Masukkan password 2FA: ")
            await client.sign_in(password=password)
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            if session_file.exists():
                session_file.unlink()
    
    async def delete_session(self):
        """Delete userbot session"""
        sessions = [s for s in self.manager_data['sessions'] if s['active']]
        
        if not sessions:
            print("\n❌ Tidak ada userbot aktif!")
            return
        
        print("\n" + "="*50)
        print("🗑️ HAPUS USERBOT")
        print("="*50)
        
        # List sessions
        for i, session in enumerate(sessions):
            expire = datetime.fromisoformat(session['expire_date'])
            days_left = (expire - datetime.now()).days
            
            print(f"\n{i+1}. {session['first_name']} - {session['phone']}")
            print(f"   Session: {session['session_name']}")
            print(f"   Created: {session['created_at'][:10]}")
            print(f"   Expire: {expire.strftime('%Y-%m-%d')} ({days_left} hari)")
        
        # Get choice
        try:
            choice = int(input("\n📌 Pilih nomor userbot yang akan dihapus (0 untuk batal): "))
            if choice == 0:
                return
            
            if 1 <= choice <= len(sessions):
                session = sessions[choice - 1]
                
                confirm = input(f"\n⚠️ Yakin hapus {session['first_name']} - {session['phone']}? (y/n): ")
                if confirm.lower() == 'y':
                    # Create bot instance and stop it
                    bot = UserBot(
                        session['phone'],
                        session['session_name'],
                        datetime.fromisoformat(session['expire_date'])
                    )
                    
                    print("\n🔄 Menghentikan userbot...")
                    if await bot.start():
                        await bot.stop()
                    
                    # Mark as inactive
                    for s in self.manager_data['sessions']:
                        if s['session_name'] == session['session_name']:
                            s['active'] = False
                            break
                    
                    self.save_manager_data()
                    
                    # Remove data file
                    data_file = DATA_DIR / f"{session['session_name']}_data.json"
                    if data_file.exists():
                        data_file.unlink()
                    
                    print("✅ Userbot berhasil dihapus!")
            else:
                print("❌ Pilihan tidak valid!")
                
        except:
            print("❌ Input tidak valid!")
    
    def list_sessions(self):
        """List all userbot sessions"""
        sessions = [s for s in self.manager_data['sessions'] if s['active']]
        
        print("\n" + "="*50)
        print("📋 DAFTAR USERBOT")
        print("="*50)
        
        if not sessions:
            print("\n❌ Tidak ada userbot aktif!")
            return
        
        for i, session in enumerate(sessions):
            expire = datetime.fromisoformat(session['expire_date'])
            created = datetime.fromisoformat(session['created_at'])
            days_left = (expire - datetime.now()).days
            days_active = (datetime.now() - created).days
            
            status = "✅ Active" if days_left > 0 else "❌ Expired"
            
            print(f"\n{i+1}. {session['first_name']} (@{session['username']})")
            print(f"   📱 Phone: {session['phone']}")
            print(f"   🆔 User ID: {session['user_id']}")
            print(f"   📁 Session: {session['session_name']}")
            print(f"   📅 Created: {created.strftime('%Y-%m-%d %H:%M')}")
            print(f"   ⏰ Expire: {expire.strftime('%Y-%m-%d')} ({days_left} hari)")
            print(f"   📊 Active: {days_active} hari")
            print(f"   🔸 Status: {status}")
        
        print(f"\n📊 Total: {len(sessions)} userbot aktif")
    
    async def run_all_bots(self):
        """Run all active bots"""
        sessions = [s for s in self.manager_data['sessions'] if s['active']]
        
        if not sessions:
            print("\n❌ Tidak ada userbot untuk dijalankan!")
            return
        
        print(f"\n🚀 Menjalankan {len(sessions)} userbot...")
        
        tasks = []
        for session in sessions:
            expire = datetime.fromisoformat(session['expire_date'])
            
            # Skip expired sessions
            if datetime.now() > expire:
                print(f"⏩ Skip {session['first_name']} - Expired")
                continue
            
            bot = UserBot(session['phone'], session['session_name'], expire)
            self.bots[session['session_name']] = bot
            
            # Start bot
            task = asyncio.create_task(bot.start())
            tasks.append(task)
        
        # Wait for all bots to start
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        active_count = sum(1 for r in results if r is True)
        print(f"\n✅ {active_count} userbot berhasil dijalankan!")
        
        # Keep running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            print("\n\n🛑 Menghentikan semua bot...")
            
            # Stop all bots
            stop_tasks = []
            for bot in self.bots.values():
                if bot.is_active:
                    stop_tasks.append(bot.stop())
            
            await asyncio.gather(*stop_tasks, return_exceptions=True)
            print("✅ Semua bot dihentikan!")
    
    async def main_menu(self):
        """Main menu interface"""
        while True:
            print("\n" + "="*50)
            print("🤖 TELEGRAM MULTI USERBOT MANAGER")
            print("📌 Version: 3.0 ULTIMATE")
            print("="*50)
            print("\n1. 📱 Create Userbot Baru")
            print("2. 🗑️  Hapus Userbot") 
            print("3. 📋 List Userbot")
            print("4. 🚀 Jalankan Semua Userbot")
            print("5. ❌ Exit")
            
            try:
                choice = int(input("\n📌 Pilih menu (1-5): "))
                
                if choice == 1:
                    await self.create_session()
                elif choice == 2:
                    await self.delete_session()
                elif choice == 3:
                    self.list_sessions()
                elif choice == 4:
                    await self.run_all_bots()
                elif choice == 5:
                    print("\n👋 Goodbye!")
                    break
                else:
                    print("❌ Pilihan tidak valid!")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except:
                print("❌ Input tidak valid!")

# ==================== MAIN FUNCTION ====================
async def main():
    """Main function"""
    manager = UserBotManager()
    await manager.main_menu()

# ==================== RUN SCRIPT ====================
if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 TELEGRAM MULTI USERBOT MANAGER")
    print("📌 Version: 3.0 ULTIMATE")
    print("📌 Features: Multi bot, schedule, auto expire")
    print("="*50 + "\n")
    
    # Check API credentials
    if API_ID == 12345678 or API_HASH == 'abcdef1234567890abcdef1234567890':
        print("❌ ERROR: API credentials belum diganti!")
        print("\n📝 Cara mendapatkan API credentials:")
        print("1. Buka https://my.telegram.org")
        print("2. Login dengan nomor telepon")
        print("3. Klik 'API Development Tools'")
        print("4. Create New Application")
        print("5. Copy API_ID dan API_HASH")
        print("6. Ganti di line 17-18 file ini")
        print("\n" + "="*50)
        sys.exit(1)
    
    # Run manager
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Manager dihentikan!")
    except Exception as e:
        print(f"\n❌ Error: {e}")

# ==================== END OF SCRIPT ====================
